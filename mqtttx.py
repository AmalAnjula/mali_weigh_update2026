import time

import serial
import paho.mqtt.client as mqtt

ser = serial.Serial("/dev/ttyUSB0",9600)

client = mqtt.Client()
client.connect("localhost",1883)

while True:
    
    try:
        
        data = ser.readline().decode(errors="ignore").strip()
    
        if data:
            client.publish("serial/weight", data,qos=0,retain=False)
            print(time.strftime("%Y-%m-%d %H:%M:%S") + " - Published to MQTT:", data)
            
        else:
            client.publish("serial/weight", "#null")
    except Exception as e:
        client.publish("serial/weight", "#"+str(e))
        print("Error reading from serial or publishing to MQTT:", str(e))
        time.sleep(10)  # Wait before retrying
        continue


         