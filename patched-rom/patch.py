import os
import sys

def patch_binary(input_file, output_file):
    # Verify that the output file does not already exist
    if os.path.exists(output_file):
        print(f"Output file '{output_file}' already exists. Please provide a non-existing file name.")
        return

    # Read the input file
    with open(input_file, 'rb') as f:
        data = bytearray(f.read())

    # Verify the length of the file
    if len(data) != 32768:
        print("Cannot patch file, expected file size of 32768 bytes.")
        return

    # Verify the presence of the specific bytes at offset 0x31dc
    offset = 0x31dc
    expected_sequence = bytearray([0x21, 0xe0, 0x01])
    if data[offset:offset+3] != expected_sequence:
        print("Cannot patch file, expected instructions not found.")
        return

    # Replace the bytes 0xe0 0x01 with 0x00 0x40
    data[offset+1] = 0x00
    data[offset+2] = 0x40

    # Write the patched data to the output file
    with open(output_file, 'wb') as f:
        f.write(data)

    print(f"File '{input_file}' has been successfully patched and saved as '{output_file}'.")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python patch_binary.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    patch_binary(input_file, output_file)
