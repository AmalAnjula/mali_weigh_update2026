import serial
import select

ser = serial.Serial("/dev/ttyUSB0",9600)

while True:
    r, _, _ = select.select([ser], [], [])
    if ser in r:
        data = ser.read(ser.in_waiting)
        print(data.decode(errors="ignore"), end="")