import serial
import time

# Configuration for the serial port
SERIAL_PORT = '/dev/ttyUSB0'  # Adjust this to your serial port
BAUD_RATE = 38400
TIMEOUT = 1  # Timeout for reading from the serial port

# Function to process incoming EPSP packets
def process_packet(header, data):
    print(f"DEBUG: Received packet: header={header.hex()} data={data.hex()}")
    
    # Extract header fields
    sender = header[0]
    master_id = header[1]
    slave_id = header[2]
    function_code = header[3]
    data_length = header[4] + 1
    
    # Swap master and slave IDs in the response
    response_header = bytearray([0x01, slave_id, master_id, function_code, header[4]])
    
    # Dispatch on function code
    if function_code == 0x01:
        # Example function code handler (add your own logic)
        response_data = b"Function 01 response"
    else:
        # Unknown function code, respond with an error
        response_header[3] = 0xFF  # Error function code
        response_data = b"Unknown function code"

    response = response_header + response_data
    print(f"DEBUG: Sending response: header={response_header.hex()} data={response_data.hex()}")
    return response

def main():
    # Open the serial port
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
    
    if ser.isOpen():
        print(f"Serial port {SERIAL_PORT} opened successfully.")
    else:
        print(f"Failed to open serial port {SERIAL_PORT}.")
        return

    try:
        while True:
            # Read the header (5 bytes)
            header = ser.read(5)
            
            if len(header) == 5:
                # Calculate the length of the data to follow
                data_length = header[4] + 1
                
                # Read the data
                data = ser.read(data_length)
                
                if len(data) == data_length:
                    # Process the packet
                    response = process_packet(header, data)
                    
                    # Send the response
                    ser.write(response)
                    print(f"DEBUG: Sent response: {response.hex()}")
            time.sleep(0.1)  # Small delay to avoid high CPU usage
    except KeyboardInterrupt:
        print("Server stopped by user.")
    finally:
        # Close the serial port
        ser.close()
        print(f"Serial port {SERIAL_PORT} closed.")

if __name__ == '__main__':
    main()
