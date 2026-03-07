
 
import threading

from logger import setup_loggers
import time
from serialHand import give_me_weight,serial_error
from datetime import datetime, timezone
import yaml
import os
import json


 
tech_log, prod_log = setup_loggers()
infeed_timeout=0

# globals for json data
DATA = {}
timestamp = None
product = None
product_code = None
tank = {}
infeed = {}
outfeed = {}
log_data = []


infeed_now_control_mode =  None
infeed_now_operation_mode = None
infeed_now_running = None
outfeed_now_control_mode = None
outfeed_now_operation_mode = None
outfeed_now_running = None
 
 
# Track previous state for change detection
prev_infeed_mode = None
prev_infeed_operation = None
prev_outfeed_mode = None
prev_outfeed_operation = None

remote_stop=False
local_stop=False
infeed_mode_change=False
infeed_local_remote_change=False

# ---------------------------------- erad yml data --------------------------------

with open("config.yml") as f:
    CONFIG = yaml.safe_load(f)

infeed_timeout = CONFIG["infeed"]["filling_time"]

# ---------------------------------- pinset --------------------------------

lowr_sns_pin=10
up_sns_pin=22
#remote control pins
intke_remot_pin=26
intke_start_pin=13
intke_stop_pin=19
outtk_start_pin=11
outtk_stop_pin=5

b_led =20

lock_btn_pin=21


#emg_up_sns_pin=17
#alm_stp_pin=4

relay_normal_off_pin=4
outk_remot_pin=6
pwr_pin=9
myrelay =12


alm_led=1  #25
pwr_led=14

out_solv=23#14
in_solv=24  #15
out_wei_led=18 #25
in_wei_led=15


ind_led_in=7
ind_led_out=8

val_down_pin=27
val_up_pin=17

timer_pin=25



def oil_add(now_weight ,required_weight):
    tech_log.info("Oil addition process started")
    # Simulate oil addition logic here
    start_time = time.time()
    done=False
    global infeed_timeout
    global remote_stop
    global local_stop
    global serial_error
    global infeed_mode_change
    global infeed_local_remote_change
    intial_weight=now_weight


    while(not done):
        current_time = time.time()
        elapsed_time = current_time - start_time

        if elapsed_time > infeed_timeout:  # Simulate a 10-second oil addition process
            done=True
            tech_log.warning("Oil add timed out after %d seconds for required weight %f. now val %f", infeed_timeout, required_weight,now_weight)
            print("Oil add timed out after %d seconds for required weight %f. now val %f", infeed_timeout, required_weight,now_weight)
            
            break
        elif now_weight >= required_weight+intial_weight:
            done=True
            tech_log.info("Required weight reached.start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            print("Required weight reached.start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)  
             
        elif serial_error:
            done=True
            tech_log.error("Serial error detected during oil addition. Aborting process.")
            print("Serial error detected during oil addition. Aborting process.")
            break
        elif remote_stop:
            done=True
            tech_log.warning("Remote stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            print("Remote stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            break
        elif local_stop:
            done=True
            tech_log.warning("Local stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            print("Local stop. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            break
        elif infeed_mode_change:
            done=True
            tech_log.warning("Infeed mode change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            print("Infeed mode change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            break
        elif infeed_local_remote_change:
            done=True
            tech_log.warning("Infeed local/remote change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            print("Infeed local/remote change. start at %.2f kg . Required %.2f kg Final: %.2f kg)",intial_weight,required_weight, now_weight)
            break





    time.sleep(2)  # Simulating time taken for oil addition
     


def check_infeed_mode_change(src):
    """Check if infeed mode changed and log it."""
    global prev_infeed_mode
    current_mode = src.get("mode")
    if prev_infeed_mode is not None and current_mode != prev_infeed_mode:
        tech_log.warning("INFEED MODE CHANGE: %s -> %s", prev_infeed_mode, current_mode)
        print("INFEED MODE CHANGE: %s -> %s", prev_infeed_mode, current_mode)
    prev_infeed_mode = current_mode

def check_infeed_operation_change(src):
    """Check if infeed operation changed and log it."""
    global prev_infeed_operation
    current_operation = src.get("operation")
    if prev_infeed_operation is not None and current_operation != prev_infeed_operation:
        tech_log.warning("INFEED OPERATION CHANGE: %s -> %s", prev_infeed_operation, current_operation)
        print("INFEED OPERATION CHANGE: %s -> %s", prev_infeed_operation, current_operation)    
    prev_infeed_operation = current_operation

def check_outfeed_mode_change(src):
    """Check if outfeed mode changed and log it."""
    global prev_outfeed_mode
    current_mode = src.get("mode")
    if prev_outfeed_mode is not None and current_mode != prev_outfeed_mode:
        tech_log.warning("OUTFEED MODE CHANGE: %s -> %s", prev_outfeed_mode, current_mode)
        print("OUTFEED MODE CHANGE: %s -> %s", prev_outfeed_mode, current_mode) 
    prev_outfeed_mode = current_mode

def check_outfeed_operation_change(src):
    """Check if outfeed operation changed and log it."""
    global prev_outfeed_operation
    current_operation = src.get("operation")
    if prev_outfeed_operation is not None and current_operation != prev_outfeed_operation:
        tech_log.warning("OUTFEED OPERATION CHANGE: %s -> %s", prev_outfeed_operation, current_operation)
        print ("OUTFEED OPERATION CHANGE: %s -> %s", prev_outfeed_operation, current_operation)
    prev_outfeed_operation = current_operation
def check_infeed_running_change(src):
    """Check if infeed running state changed and log it."""
    global prev_infeed_running
    current_running = src.get("running")
    if prev_infeed_running is not None and current_running != prev_infeed_running:
        tech_log.warning("INFEED RUNNING CHANGE: %s -> %s", prev_infeed_running, current_running)
        print("INFEED RUNNING CHANGE: %s -> %s", prev_infeed_running, current_running)    
    prev_infeed_running = current_running

def check_outfeed_running_change(src):  
    """Check if outfeed running state changed and log it."""
    global prev_outfeed_running
    current_running = src.get("running")
    if prev_outfeed_running is not None and current_running != prev_outfeed_running:
        tech_log.warning("OUTFEED RUNNING CHANGE: %s -> %s", prev_outfeed_running, current_running)
        print("OUTFEED RUNNING CHANGE: %s -> %s", prev_outfeed_running, current_running)    
    prev_outfeed_running = current_running

def load_data_json():
    """Read data.json and populate module-level variables.
    
    Detects state changes in infeed/outfeed mode and operation.
    Call this periodically or once at startup. Any errors are logged.
    """
    global DATA, timestamp, product, product_code, tank, infeed, outfeed, log_data,infeed_now_control_mode,infeed_now_operation_mode,infeed_now_running,outfeed_now_control_mode,outfeed_now_operation_mode,outfeed_now_running
    try:
        with open("data.json") as f:
            DATA = json.load(f)
        
        
       
        infeed = DATA.get("infeed", {})
        outfeed = DATA.get("outfeed", {})
         

        
        infeed_now_control_mode = infeed.get("mode")
        infeed_now_operation_mode = infeed.get("operation") 
        infeed_now_running = infeed.get("running")

        outfeed_now_control_mode = outfeed.get("mode")
        outfeed_now_operation_mode = outfeed.get("operation")
        outfeed_now_running = outfeed.get("running")


        
        # Check for state changes
        check_infeed_mode_change(infeed)
        check_infeed_operation_change(infeed)
        check_infeed_running_change(infeed)

        check_outfeed_mode_change(outfeed)
        check_outfeed_operation_change(outfeed)
        check_outfeed_running_change(outfeed)
        
        #tech_log.debug("Loaded data.json: %s", DATA)
    except Exception as e:
        tech_log.error("Error loading data.json: %s", e)
        time.sleep(5)  # Wait before retrying to avoid log flooding


def check_button_change(thread_name,my_delay):
    global remote_stop
    global local_stop
    global infeed_mode_change
    global infeed_local_remote_change

    while True:
        time.sleep(my_delay)
        load_data_json()  # Refresh data to get latest button states
        
        # Update flags based on current infeed state
        infeed_mode_change = (infeed.get("mode") != prev_infeed_mode)
        infeed_local_remote_change = (infeed.get("operation") != prev_infeed_operation)
         
        remote_stop = (infeed.get("operation") == "REMOTE" and infeed.get("running") == False)
        local_stop = (infeed.get("operation") == "LOCAL" and infeed.get("running") == False)
        

 

def update_weight_in_json():
    """Read weight from sensor and update data.json."""
    try:
        weight = give_me_weight()
        if weight is None:
            tech_log.debug("No weight reading available from sensor")
            return False

        # Load current data
        with open("data.json", "r") as f:
            data = json.load(f)

        # Ensure tank structure exists
        tank_obj = data.setdefault("tank", {})
        tank_obj["weight_kg"] = weight

        # Compute level percentage from tank.max_kg when available
        max_kg = tank_obj.get("max_kg")
        level_pct = None
        try:
            if isinstance(max_kg, (int, float)) and max_kg > 0:
                level_pct = (float(weight) / float(max_kg)) * 100.0
                # Clamp between 0 and 100
                if level_pct < 0:
                    level_pct = 0.0
                elif level_pct > 100:
                    level_pct = 100.0
                tank_obj["level_pct"] = round(level_pct, 2)
            else:
                tech_log.warning("tank.max_kg missing or invalid: %s", max_kg)
                # keep existing level_pct if present
        except Exception:
            tech_log.exception("Failed computing level_pct from max_kg: %s", max_kg)

        # Update timestamp to current UTC ISO format
        data["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Write atomically: write to temp file and replace
        tmp_path = "data.json.tmp"
        with open(tmp_path, "w") as f:
            json.dump(data, f, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, "data.json")

        #tech_log.debug("Updated data.json weight %.2f kg level_pct %s", weight, tank_obj.get("level_pct"))
        return True
    except Exception as e:
        tech_log.error("Error updating weight in data.json: %s", e)
        return False


def main():
    global weiVal
    # read initial JSON data into variables
    load_data_json()

    

    # ---- Technical logs ----
    '''tech_log.debug("DB connection started")
    tech_log.error("Stack trace example")

    # ---- Production logs ----
    prod_log.info("User login success")
    prod_log.warning("Payment delay detected")'''


def do_work(thread_name,my_delay):
    global infeed_now_control_mode,infeed_now_operation_mode,infeed_now_running,outfeed_now_control_mode,outfeed_now_operation_mode,outfeed_now_running
  
    while True:
        #oil_add(58, 50.0)  # Example: Add oil until we reach 50 kg
       
        time.sleep(1)
        # Update weight from sensor into data.json
        update_weight_in_json()
        # Reload JSON data periodically to detect state changes
        load_data_json()
        print("Weight:", give_me_weight())
        print("Infeed mode:", infeed_now_control_mode, "operation:", infeed_now_operation_mode, "running:", infeed_now_running)
        print("Outfeed mode:", outfeed_now_control_mode, "operation:", outfeed_now_operation_mode, "running:", outfeed_now_running)

        # You can add more periodic tasks here as needed


t = threading.Thread(
    target=check_button_change,
    args=("btnChnageEvent", 0.001),
)
t.daemon = True
t.start()


t = threading.Thread(
    target=do_work,
    args=("do_work_thead", 0.001),
)
t.daemon = True
t.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        tech_log.info("Main loop interrupted")
        print("Shutting down...")





