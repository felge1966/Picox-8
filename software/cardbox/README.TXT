This not the original CARDBOX rom, but a reconstructed one. The files are found somewhere on the internet, and the 
executable converted to a ROM image with the PROMFORM utility.

According to the documentation, the CARDBOX.COM was delivered on a ROM and the other files on a micro-cassette tape.

CARDBOX.COM - the executable
cardbox.hex - the ROM image in intel-hex format for programmers)
cardbox.rom - the ROM image in binary form for the emulator

the files from tape:
LABELOUT.FMT
SALESMAN.FIL
SALESMAN.FMT
SALESTEL.FMT
WSOUT.FMT

 
Usage:
The CARDBOX.COM program always needs an argument, otherwise it will exit with the message 'BAD FILENAME'.
From the documentation (somewhere on the site you found this file):

CARDBOX MYFILE.FMT *  - This creates a Format file.
CARDBOX MYFILE.FIL *  - This creates a Datafile.
CARDBOX MYFILE.FMT    - This means Edit the Format file.
CARDBOX MYFILE.FIL    - This means Use the database.
The * symbol means CREATE files.