# UNO Optiboot programming example

import board
import adafruit_avrprog

avrprog = adafruit_avrprog.AVRprog()
avrprog.init(board.SCK, board.MOSI, board.MISO, board.D5)

# Each chip has to have a definition so the script knows how to find it
atmega328p = {'name': "ATmega328P"}
atmega328p['sig'] = [0x1E, 0x95, 0x0F]
atmega328p['flash_size'] = 32768
atmega328p['page_size'] = 128
atmega328p['fuse_mask'] = (0xFF, 0xFF, 0x07, 0x3F)

# Helper to print out errors for us
def error(err):
    print("ERROR: "+err)
    avrprog.end()
    while True:
        pass

if not avrprog.verify_sig(atmega328p, verbose=True):
    error("Signature read failure")
print("Found", atmega328p['name'])

# Since we are unsetting the lock fuse, an erase is required!
avrprog.erase_chip()

avrprog.write_fuses(atmega328p, low=0xFF, high=0xDE, ext=0x05, lock=0x3F)
if not avrprog.verify_fuses(atmega328p, low=0xFF, high=0xDE, ext=0x05, lock=0x3F):
    error("Failure programming fuses: "+str([hex(i) for i in avrprog.read_fuses(atmega328p)]))

print("Programming flash from file")
avrprog.program_file(atmega328p, "optiboot_atmega328.hex", verbose=True, verify=True)

avrprog.write_fuses(atmega328p, lock=0x0F)
if not avrprog.verify_fuses(atmega328p,lock=0x0F):
    error("Failure verifying fuses!")

print("Done!")
