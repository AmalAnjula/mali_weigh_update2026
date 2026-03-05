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
            dt=ser.read_until(b'\n').decode("utf-8").strip() 
            ser.flushInput()
            dt=dt.replace("=","")
            dt=dt.replace(" ","")   
            nowval=float(dt)
             
            if abs(nowval - oldval) > MAX_ALLOWED_JUMP and oldval!=-200:
                tech_log.warning("Weight jump detected: %.2f kg (from %.2f to %.2f)", abs(nowval - oldval), oldval, nowval)
                time.sleep(1)  # brief pause to allow for stabilization
                ser.flushInput()    
            else:
                weiVal=nowval
            oldval=nowval
            serial_error=False
        except ValueError:
            tech_log.warning("Received non-integer data from serial: %s", dt)
            
            time.sleep(1)  # brief pause before next read   
            ser.flushInput()    
            print(dt)
            continue
        except serial.SerialException as e:
            tech_log.error("Serial communication error: %s", str(e))
            serial_error=True
            continue

        #time.sleep(my_delay)
        #print("Current weight value:", weiVal)


 
t = threading.Thread(
    target=my_serial_read,
    args=("Thread-1", 0.001),
)
t.start()

 