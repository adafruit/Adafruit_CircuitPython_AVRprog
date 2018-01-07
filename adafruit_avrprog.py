# The MIT License (MIT)
#
# Copyright (c) 2017 ladyada for adafruit industries
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
"""
`adafruit_AVRprog`
====================================================

TODO(description)

* Author(s): ladyada
"""

# imports

__version__ = "0.0.0-auto.0"
__repo__ = "https://github.com/adafruit/Adafruit_CircuitPython_AVRprog.git"

import busio
from digitalio import Direction, DigitalInOut

_SLOW_CLOCK = 100000
_FAST_CLOCK = 2000000

class AVRprog:
    """
    Program your favorite AVR chips directly from CircuitPython with this
    handy helper class that will let you make stand-alone programmers right
    from your REPL
    """
    _spi = None
    _rst = None
    _mosi = None
    _miso = None
    _sck = None

    def init(self, sck_pin, mosi_pin, miso_pin, rst_pin):
        """
        Initialize the programmer with SPI pins that will be used to
        communicate with the chip. Currently only hardware-SPI pins are
        supported!
        """
        self._spi = busio.SPI(sck_pin, mosi_pin, miso_pin)
        #except:
        #    pins = [DigitalInOut(p) for p in (sck_pin, mosi_pin, miso_pin)]
        #    self._sck, self._mosi, self._miso = pins
        #    self._sck.direction = Direction.OUTPUT
        #    self._sck.value = False
        #    self._mosi.direction = Direction.OUTPUT
        #    self._miso.direction = Direction.INPUT

        self._rst = DigitalInOut(rst_pin)
        self._rst.direction = Direction.OUTPUT
        self._rst.value = True


    def verify_sig(self, chip, verbose=False):
        """
        Verify that the chip is connected properly, responds to commands,
        and has the correct signature. Returns True/False based on success
        """
        self.begin(clock=_SLOW_CLOCK)
        sig = self.read_signature()
        self.end()
        if verbose:
            print("Found signature: %s" % [hex(i) for i in sig])
        if sig != chip['sig']:
            return False
        return True

    def program_file(self, chip, file_name, verbose=False, verify=True):
        """
        Perform a chip erase and program from a file that
        contains Intel HEX data. Returns true on verify-success, False on
        verify-failure. If 'verify' is False, return will always be True
        """
        if not self.verify_sig(chip):
            raise RuntimeError("Signature read failure")

        if verbose:
            print("Erasing chip....")
        self.erase_chip()

        self.begin()
        hexfile = open(file_name, 'r')

        page_size = chip['page_size']

        for page_addr in range(0, chip['flash_size'], page_size):
            #print("Programming page $%04X" % page_addr)
            page_buffer = bytearray(page_size)
            for b in range(page_size):
                page_buffer[b] = 0xFF     # make an empty page

            read_hex_page(hexfile, page_addr, page_size, page_buffer)

            if all([v == 0xFF for v in page_buffer]):
                #print("Skipping empty page")
                continue

            if verbose:
                print("Programming page @ $%04X" % (page_addr))
            #print("From HEX file: ", page_buffer)
            self._flash_page(bytearray(page_buffer), page_addr, page_size)

            if not verify:
                continue

            if verbose:
                print("Verifying page @ $%04X" % page_addr)
            read_buffer = bytearray(page_size)
            self.read(page_addr, read_buffer)
            #print("From memory: ", read_buffer)

            if page_buffer != read_buffer:
                if verbose:
                    # pylint: disable=line-too-long
                    print("Verify fail at address %04X\nPage should be: %s\nBut contains: %s" % (page_addr, page_buffer, read_buffer))
                    # pylint: enable=line-too-long
                self.end()
                return False

        hexfile.close()
        self.end()
        return True

    def verify_file(self, chip, file_name, verbose=False):
        """
        Perform a chip full-flash verification from a file that
        contains Intel HEX data. Returns True/False on success/fail.
        """
        if not self.verify_sig(chip):
            raise RuntimeError("Signature read failure")

        hexfile = open(file_name, 'r')
        page_size = chip['page_size']
        self.begin()
        for page_addr in range(0, chip['flash_size'], page_size):
            page_buffer = bytearray(page_size)
            for b in range(page_size):
                page_buffer[b] = 0xFF     # make an empty page

            read_hex_page(hexfile, page_addr, page_size, page_buffer)

            if verbose:
                print("Verifying page @ $%04X" % page_addr)
            read_buffer = bytearray(page_size)
            self.read(page_addr, read_buffer)
            #print("From memory: ", read_buffer)

            if page_buffer != read_buffer:
                if verbose:
                    # pylint: disable=line-too-long
                    print("Verify fail at address %04X\nPage should be: %s\nBut contains: %s" % (page_addr, page_buffer, read_buffer))
                    # pylint: enable=line-too-long
                self.end()
                return False
        hexfile.close()
        self.end()
        return True

    def read_fuses(self, chip):
        """
        Read the 4 fuses and return them in a list (low, high, ext, lock)
        Each fuse is bitwise-&'s with the chip's fuse mask for simplicity
        """
        mask = chip['fuse_mask']
        self.begin(clock=_SLOW_CLOCK)
        low = self._transaction((0x50, 0, 0, 0))[2] & mask[0]
        high = self._transaction((0x58, 0x08, 0, 0))[2] & mask[1]
        ext = self._transaction((0x50, 0x08, 0, 0))[2] & mask[2]
        lock = self._transaction((0x58, 0, 0, 0))[2] & mask[3]
        self.end()
        return (low, high, ext, lock)

    # pylint: disable=unused-argument,expression-not-assigned
    def write_fuses(self, chip, low=None, high=None, ext=None, lock=None):
        """
        Write any of the 4 fuses. If the kwarg low/high/ext/lock is not
        passed in or is None, that fuse is skipped
        """
        self.begin(clock=_SLOW_CLOCK)
        lock and self._transaction((0xAC, 0xE0, 0, lock))
        low  and self._transaction((0xAC, 0xA0, 0, low))
        high and self._transaction((0xAC, 0xA8, 0, high))
        ext  and self._transaction((0xAC, 0xA4, 0, ext))
        self.end()
    # pylint: enable=unused-argument,expression-not-assigned

    def verify_fuses(self, chip, low=None, high=None, ext=None, lock=None):
        """
        Verify the 4 fuses. If the kwarg low/high/ext/lock is not
        passed in or is None, that fuse is not checked.
        Each fuse is bitwise-&'s with the chip's fuse mask.
        Returns True on success, False on a fuse verification failure
        """
        fuses = self.read_fuses(chip)
        verify = (low, high, ext, lock)
        for i in range(4):
            # check each fuse if we requested to check it!
            if verify[i] and verify[i] != fuses[i]:
                return False
        return True


    def erase_chip(self):
        """
        Fully erases the chip.
        """
        self.begin(clock=_SLOW_CLOCK)
        self._transaction((0xAC, 0x80, 0, 0))
        self._busy_wait()
        self.end()

    #################### Mid level

    def begin(self, clock=_FAST_CLOCK):
        """
        Begin programming mode: pull reset pin low, initialize SPI, and
        send the initialization command to get the AVR's attention.
        """
        self._rst.value = False
        if self._spi:
            while self._spi and not self._spi.try_lock():
                pass
            self._spi.configure(baudrate=clock)
        self._transaction((0xAC, 0x53, 0, 0))

    def end(self):
        """
        End programming mode: SPI is released, and reset pin set high.
        """
        if self._spi:
            self._spi.unlock()
        self._rst.value = True

    def read_signature(self):
        """
        Read and return the signature of the chip as two bytes in an array.
        Requires calling begin() beforehand to put in programming mode.
        """
        # signature is last byte of two transactions:
        sig = []
        for i in range(3):
            sig.append(self._transaction((0x30, 0, i, 0))[2])
        return sig

    def read(self, addr, read_buffer):
        """
        Read a chunk of memory from address 'addr'. The amount read is the
        same as the size of the bytearray 'read_buffer'. Data read is placed
        directly into 'read_buffer'
        Requires calling begin() beforehand to put in programming mode.
        """
        for i in range(len(read_buffer)//2):
            read_addr = addr//2 + i # read 'words' so address is half
            high = self._transaction((0x28, read_addr >> 8, read_addr, 0))[2]
            low = self._transaction((0x20, read_addr >> 8, read_addr, 0))[2]
            #print("%04X: %02X %02X" % (read_addr*2, low, high))
            read_buffer[i*2] = low
            read_buffer[i*2+1] = high

    #################### Low level
    def _flash_word(self, addr, low, high):
        self._transaction((0x40, addr >> 8, addr, low))
        self._transaction((0x48, addr >> 8, addr, high))

    def _flash_page(self, page_buffer, page_addr, page_size):
        for i in range(page_size/2):
            lo_byte, hi_byte = page_buffer[2*i:2*i+2]
            self._flash_word(i, lo_byte, hi_byte)
        page_addr //= 2
        commit_reply = self._transaction((0x4C, page_addr >> 8, page_addr, 0))
        if ((commit_reply[1] << 8) + commit_reply[2]) != page_addr:
            raise RuntimeError("Failed to commit page to flash")
        self._busy_wait()

    def _transaction(self, command):
        reply = bytearray(4)
        command = bytearray([i & 0xFF for i in command])

        if self._spi:
            self._spi.write_readinto(command, reply)
        #s = [hex(i) for i in command]
        #print("Sending %s reply %s" % (command, reply))
        if reply[2] != command[1]:
            raise RuntimeError("SPI transaction failed")
        return reply[1:] # first byte is ignored

    def _busy_wait(self):
        while self._transaction((0xF0, 0, 0, 0))[2] & 0x01:
            pass

def read_hex_page(hexfile, page_addr, page_size, page_buffer):
    """
    Helper function that does the Intel Hex parsing. Given an open file
    'hexfile' and our desired buffer address start (page_addr), size
    (page_size) and an allocated bytearray. This function will try to
    read the file and fill the page_buffer. If the next line has data
    that is beyond the size of the page_address, it will return without
    changing the buffer, so pre-fill it with 0xFF (for sparsely-defined
    HEX files.
    Returns False if the file has no more data to read. Returns True if
    we've done the best job we can with filling the buffer and the next
    line does not contain any more data we can use.
    """
    while True:     # read until our page_buff is full!
        orig_loc = hexfile.tell()  # in case we have to 'back up'
        line = hexfile.readline()      # read one line from the HEX file
        if not line:
            return False
        #print(line)
        if line[0] != ':':       # lines must start with ':'
            raise RuntimeError("HEX line doesn't start with :")

        # Try to parse the line length, address, and record type
        try:
            hex_len = int(line[1:3], 16)
            line_addr = int(line[3:7], 16)
            rec_type = int(line[7:9], 16)
        except ValueError:
            raise RuntimeError("Could not parse HEX line addr")

        #print("Hex len: %d, addr %04X, record type %d " % (hex_len, line_addr, rec_type))

        # We should only look for data type records (0x00)
        if rec_type == 0x01:
            return False  # reached end of file
        elif rec_type != 0x00:
            raise RuntimeError("Unsupported record type %d" % rec_type)

        # check if this file file is either after the current page
        # (in which case, we've read all we can for this page and should
        # commence flashing...)
        if line_addr >= (page_addr + page_size):
            #print("Hex is past page address range")
            hexfile.seek(orig_loc)  # back up!
            return True
        # or, this line does not yet reach the current page address, in which
        # case which should just keep reading in hopes we reach the address
        # we're looking for next time!
        if (line_addr + hex_len) <= page_addr:
            #print("Hex is prior to page address range")
            continue

        # parse out all remaining hex bytes including the checksum
        byte_buffer = []
        for i in range(hex_len + 1):
            byte_buffer.append(int(line[9+i*2:11+i*2], 16))

        # check chksum now!
        chksum = hex_len + (line_addr >> 8) + (line_addr & 0xFF) + rec_type + sum(byte_buffer)
        #print("checksum: "+hex(chksum))
        if (chksum & 0xFF) != 0:
            raise RuntimeError("HEX Checksum fail")

        # get rid of that checksum byte
        byte_buffer.pop()
        #print([hex(i) for i in byte_buffer])

        #print("line addr $%04X page addr $%04X" % (line_addr, page_addr))
        page_idx = line_addr - page_addr
        line_idx = 0
        while (page_idx < page_size) and (line_idx < hex_len):
            #print("page_idx = %d, line_idx = %d" % (page_idx, line_idx))
            page_buffer[page_idx] = byte_buffer[line_idx]
            line_idx += 1
            page_idx += 1
        if page_idx == page_size:
            return True # ok we've read a full page, can bail now!

    return False # we...shouldn't get here?
