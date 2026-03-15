import re
import serial  # pip install pyserial

# --- Option 1: From a real serial port ---
ser = serial.Serial('/dev/ttyUSB0', 1200, timeout=1)  # adjust port/baud

buffer = ""
while True:
    chunk = ser.read(64).decode('utf-8', errors='ignore')
    buffer += chunk

    # Extract all numbers from the buffer
    numbers = re.findall(r'=\s*([\d.]+)', buffer)
    for n in numbers:
        print(float(n))  # e.g. 99.8

    # Keep only the last partial token (in case it's mid-stream)
    buffer = re.split(r'=\s*[\d.]+', buffer)[-1]