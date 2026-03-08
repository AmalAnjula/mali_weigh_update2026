import RPi.GPIO as GPIO
import time


GPIO.setmode(GPIO.BCM)
time.sleep(0.01)
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)


relay_normal_off_pin=4
outk_remot_pin=6
pwr_pin=9
myrelay =12


 

val_down_pin=27
val_up_pin=17
lowr_sns_pin=10
up_sns_pin=22
intke_remot_pin=26
intke_start_pin=13
intke_stop_pin=19

outtk_start_pin=11
outtk_stop_pin=5


 
GPIO.setup(val_down_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(val_up_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)


GPIO.setup(lowr_sns_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(up_sns_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(intke_remot_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(intke_start_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(intke_stop_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(outtk_start_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(outtk_stop_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(relay_normal_off_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)


while True:
    time.sleep(0.5)
    print("\n\n\n-------val_down_pin:",GPIO.input(val_down_pin)
          ,"\nval_up_pin:",GPIO.input(val_up_pin)
          ,"\nlowr_sns_pin:",GPIO.input(lowr_sns_pin)
          ,"\nup_sns_pin:",GPIO.input(up_sns_pin)
          ,"\nintke_remot_pin:",GPIO.input(intke_remot_pin)
          ,"\nintke_start_pin:",GPIO.input(intke_start_pin)
          ,"\nintke_stop_pin:",GPIO.input(intke_stop_pin)
          ,"\nouttk_start_pin:",GPIO.input(outtk_start_pin)
          ,"\nouttk_stop_pin:",GPIO.input(outtk_stop_pin)
          ,"\nrelay_normal_off_pin:",GPIO.input(relay_normal_off_pin) )