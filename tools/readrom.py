import sys
import struct
import os

def decode_capacity(byte):
    capacity_dict = {
        0x08: "single 8 kByte ROM",
        0x88: "double 8 kByte ROMs",
        0x10: "single 16 kByte ROM",
        0x90: "double ROMs, first part 16 kByte",
        0x20: "single 32 kByte ROM",
        0xA0: "double ROMs, first part 32 kByte"
    }
    return capacity_dict.get(byte, "Unknown capacity")

def decode_rom_header(filename):
    file_size = os.path.getsize(filename)
    offset = 0x4000 if file_size == 32768 else 0x00

    with open(filename, 'rb') as f:
        f.seek(offset)
        header = f.read(32)
    
    # Check header length
    if len(header) < 32:
        print("Header is too short!")
        return

    # Decode header fields
    always_e5 = header[0x00]
    format_byte = header[0x01]
    capacity_byte = header[0x02]
    checksum = struct.unpack('>H', header[0x03:0x05])[0]
    system_name = header[0x05:0x08].decode('ascii', errors='ignore')
    rom_name = header[0x08:0x16].decode('ascii', errors='ignore').strip()
    num_directory_entries = header[0x16]
    always_56 = header[0x17]
    version_number = struct.unpack('>H', header[0x18:0x1A])[0]
    rom_production_date = header[0x1A:0x20].decode('ascii', errors='ignore')

    # Check always fields
    if always_e5 != 0xE5:
        print("Error: Expected 0xE5 at byte 0x00, but found 0x{:02X}".format(always_e5))
        sys.exit(1)
    if always_56 != 0x56:
        print("Error: Expected 0x56 at byte 0x17, but found 0x{:02X}".format(always_56))
        sys.exit(1)

    # Decode format
    format_str = 'P' if format_byte == 0x50 else 'M' if format_byte == 0x37 else 'Unknown format'

    # Decode capacity
    capacity_str = decode_capacity(capacity_byte)

    # Decode ROM production date
    try:
        month = rom_production_date[0:2]
        day = rom_production_date[2:4]
        year = rom_production_date[4:6]
        rom_production_date_str = f"{month}/{day}/{year}"
    except:
        rom_production_date_str = "Invalid date format"

    # Print decoded header
    print(f"Format: {format_str}")
    print(f"Capacity: {capacity_str} (0x{capacity_byte:02X})")
    print(f"Checksum: {checksum}")
    print(f"System Name: {system_name}")
    print(f"ROM Name: {rom_name}")
    print(f"Number of Directory Entries: {num_directory_entries}")
    print(f"Version Number: {version_number}")
    print(f"ROM Production Date: {rom_production_date_str}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_rom_header.py <binary_file>")
        sys.exit(1)

    binary_file = sys.argv[1]
    decode_rom_header(binary_file)
