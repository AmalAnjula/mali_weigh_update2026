import serial
import re
import time

ser = serial.Serial('/dev/ttyUSB0', 1200, timeout=1)  # adjust port/baud

pattern = re.compile(r'([A-Z]{2}),([A-Z]{2})\s+([\d.]+)\s*KG')

while True:
    try:
        line = ser.readline().decode('utf-8', errors='ignore').strip()
        if not line:
            continue

        match = pattern.search(line)
        if not match:
            continue

        status, mode, raw = match.groups()

        if status != "ST":
            continue  # skip unstable readings

        weight = float(raw)
        print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} >> Stable weight: {weight} KG")

    except Exception as e:
        print(e)