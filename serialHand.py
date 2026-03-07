import time
from queue import Queue
import yaml
import threading
import os
import serial
from logger import setup_loggers


tech_log, prod_log = setup_loggers()
weiVal=0
serial_error=False


weight_queue = Queue()
MAX_ALLOWED_JUMP = 3.0   # kg

last_weight = None




with open("config.yml") as f:
    CONFIG = yaml.safe_load(f)

port = CONFIG["serial"]["port"]
baudrate = CONFIG["serial"]["baudrate"]
timeout = CONFIG["serial"]["timeout"]
print(port, baudrate)


try:
    ser=serial.Serial(port,baudrate,timeout=timeout)
except:
    tech_log.error("Failed to connect to serial port: %s", port)
    raise
     

def give_me_weight():
    global weiVal
    return weiVal
     

def my_serial_read(thread_name,my_delay):
    tech_log.info("Starting serial read thread: %s", thread_name)
    global weiVal
    global serial_error
    nowval=0
    oldval=-200

    ser.flushInput()
    while(True):
        try:
            # Read 20 characters
             
            data = ser.readline().decode('utf-8', errors='ignore').strip()
            #print(data)
            #data = ser.readline().decode('utf-8', errors='ignore')[:20]
            
            
            # Split data between two newlines
            
            
            # Process the data
            dt = data.strip()
            dt = dt.replace("=", "")
            dt = dt.replace(" ", "")
            dt = dt.replace("\n", "")
            dt = dt.replace("\r", "")
            
            if dt:  # Only process if not empty
                nowval = float(dt)
                
                if abs(nowval - oldval) > MAX_ALLOWED_JUMP and oldval != -200:
                    #tech_log.warning("Weight jump detected: %.2f kg (from %.2f to %.2f)", abs(nowval - oldval), oldval, nowval)
                    time.sleep(1)
                    ser.flushInput()
                else:
                    weiVal = nowval
                    #print("Current weight value:", weiVal)
                oldval = nowval
                serial_error = False
        except ValueError:
            tech_log.warning("Received non-numeric data from serial: %s", data)
            time.sleep(1)
            ser.flushInput()
            continue
        except serial.SerialException as e:
            tech_log.error("Serial communication error: %s", str(e))
            serial_error = True
            continue
        except Exception as e:
            tech_log.error("Error reading serial data: %s", str(e))
            time.sleep(1)
            ser.flushInput()
            continue


 
t = threading.Thread(
    target=my_serial_read,
    args=("Thread-1", 0.001),
)
t.start()

 