import sys
import struct
import os
import subprocess
from tempfile import NamedTemporaryFile
from pathlib import Path

def decode_capacity(capacity_byte):
    capacity_dict = {
        0x08: "single 8 kByte ROM",
        0x88: "double 8 kByte ROMs",
        0x10: "single 16 kByte ROM",
        0x90: "double ROMs, first part 16 kByte",
        0x20: "single 32 kByte ROM",
        0xA0: "double ROMs, first part 32 kByte"
    }
    return capacity_dict.get(capacity_byte, "Unknown capacity")

def capacity_kb(capacity_byte):
    capacity_dict = {
        0x08: 8,
        0x88: 8,
        0x10: 16,
        0x90: 16,
        0x20: 32,
        0xA0: 16
    }
    return capacity_dict.get(capacity_byte, "Unknown capacity")

def decode_rom_header(filename, as_format_code=False):
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
    format_code = f'px8rom{capacity_kb(capacity_byte)}d{num_directory_entries}'
    print(f"cpmtools format code: px8rom{capacity_kb(capacity_byte)}d{num_directory_entries}")
    return capacity_kb(capacity_byte), format_code

def extract(file, dir, format):
    subprocess.run(['cpmcp', '-f', format, '-p', file, '0:*.*', dir])

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python decode_rom_header.py <binary_file>")
        sys.exit(1)
    binary_file = sys.argv[1]
    print(f'ROM file {binary_file}')
    capacity_kb, format_code = decode_rom_header(binary_file)
    dir_name = str(Path(binary_file).with_suffix(''))
    os.makedirs(dir_name, exist_ok=True)
    print(f'Created directory {dir_name}')
    if capacity_kb == 32:
        print(f'Dealing with 32k ROM')
        with open(binary_file, 'rb') as f:
            buf = f.read()
        assert(len(buf) == 32768)
        with NamedTemporaryFile('wb', delete=False) as temp_file:
            temp_file.write(buf[16384:])
            temp_file.write(buf[:16384])
        extract(temp_file.name, dir_name, format_code)
    else:
        temp_file = None
        extract(binary_file, dir_name, format_code)
    if temp_file:
        os.remove(temp_file.name)
