# Original Trinket or Gemma (ATtiny85) programming example

import board
import adafruit_avrprog

avrprog = adafruit_avrprog.AVRprog()
avrprog.init(board.SCK, board.MOSI, board.MISO, board.D5)

# Each chip has to have a definition so the script knows how to find it
attiny85 = {'name': "ATtiny85"}
attiny85['sig'] = [0x1E, 0x93, 0x0B]
attiny85['flash_size'] = 8192
attiny85['page_size'] = 64
attiny85['fuse_mask'] = (0xFF, 0xFF, 0x07, 0x3F)

# Helper to print out errors for us
def error(err):
    print("ERROR: "+err)
    avrprog.end()
    while True:
        pass

if not avrprog.verify_sig(attiny85):
    error("Signature read failure")
print("Found", attiny85['name'])
 
avrprog.write_fuses(attiny85, low=0xF1, high=0xD5, ext=0x06, lock=0x3F)
if not avrprog.verify_fuses(attiny85, low=0xF1, high=0xD5, ext=0x06, lock=0x3F):
    error("Failure verifying fuses!")

print("Programming flash from file")
avrprog.program_file(attiny85, "trinket.hex", verbose=True, verify=True)

print("Done!")
