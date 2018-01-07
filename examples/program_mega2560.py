# Mega STK500 Bootloader programming example

import board
import busio
import adafruit_avrprog

spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
avrprog = adafruit_avrprog.AVRprog()
avrprog.init(spi, board.D5)

# Each chip has to have a definition so the script knows how to find it
atmega2560 = {'name': "ATmega2560"}
atmega2560['sig'] = [0x1E, 0x98, 0x01]
atmega2560['flash_size'] = 262144
atmega2560['page_size'] = 256
atmega2560['fuse_mask'] = (0xFF, 0xFF, 0x07, 0x3F)

# Helper to print out errors for us
def error(err):
    print("ERROR: "+err)
    avrprog.end()
    while True:
        pass

if not avrprog.verify_sig(atmega2560, verbose=True):
    error("Signature read failure")
print("Found", atmega2560['name'])

# Since we are unsetting the lock fuse, an erase is required!
avrprog.erase_chip()

avrprog.write_fuses(atmega2560, low=0xFF, high=0xD8, ext=0x05, lock=0x3F)
if not avrprog.verify_fuses(atmega2560, low=0xFF, high=0xD8, ext=0x05, lock=0x3F):
    error("Failure programming fuses: "+str([hex(i) for i in avrprog.read_fuses(atmega2560)]))

print("Programming flash from file")
avrprog.program_file(atmega2560, "stk500boot_v2_mega2560.hex", verbose=True, verify=True)

avrprog.write_fuses(atmega2560, lock=0x0F)
if not avrprog.verify_fuses(atmega2560,lock=0x0F):
    error("Failure verifying fuses!")

print("Done!")
