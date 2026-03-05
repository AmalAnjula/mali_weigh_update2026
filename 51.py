#!/usr/bin/env python

#sudo chown :pi /etc/dhcpcd.conf
#ls /etc/dhcpcd.conf -l


import RPi.GPIO as GPIO
import Tkinter
from Tkinter import*
import ttk
import PIL
import thread
import time,datetime

import serial
import os
from decimal import Decimal
import csv
import datetime 
import tkMessageBox
import subprocess
import os


#time.sleep(5)


width=640
hight=width*9.0/16.0
print hight
win = Tkinter.Tk()
win.geometry("640x480")

 
n = ttk.Notebook(win)
n.pack(expand=1, fill="both")

f1 = ttk.Frame(n)   # first page, which would get widgets gridded into it
f2 = ttk.Frame(n)   # second page
f3 = ttk.Frame(n)   # second page
n.add(f1, text='Processing Diagram')
n.add(f2, text='Waringns')
n.add(f3, text='Log')
 


w = Canvas(f1, width=width/4, height=hight*95/100)
w.pack()
w.configure( )

gif1 = PhotoImage(file = '/home/pi/Desktop/stuff/1.PNG')

ser_data="0000"

w.create_image(0, 0, image = gif1, anchor = NW)
S=Scrollbar(f3)
t=Text(f3,height=18,width=100)
S.pack(side=RIGHT,fill=Y)
t.pack(side=RIGHT,anchor="s")
S.config(command=t.yview) 
t.config(yscrollcommand=S.set,font=("Helvetica ", 10))


sen_up_icon=w.create_oval(110, 30,140, 60,fill='LAWN GREEN')
sen_lwr_icon=w.create_oval(110, 280,140, 310,fill='LAWN GREEN')

in_pipe=w.create_line(0,40,35,40,fill="GRAY",width=10)
out_pipe=w.create_line(130,320,500,320,fill="GRAY",width=10)

fill_per=0.00
fil_bar_up=w.create_line(80,25,80,(fill_per)*3.1+25,fill="SNOW2",width=10)
fil_bar_lwr=w.create_line(80,335,80,(100-fill_per)*3.1+25,fill="GREEN4",width=10)



ser_flag=0
ke_counter=0
xcl_data=""
counter=0
old_counter=0

time_out=0

work_in_count=0
work_out_count=0

mode_intake_txt="Auto"
intk_ctrl_txt="Local"
mode_intake_txt2="Manual"
intk_mode_flag=True

intk_ctrl_txt="Local"
intk_ctrl_flag=True
intk_ctrl_txt_2="Remote"

int_act_txt="Start"
int_act_flag=1
int_act_txt_2="Stop"

mode_outtake_txt="Auto"
outk_ctrl_txt="Local"

outk_ctrl_txt_2="Remote"
 
mode_outtake_txt="Auto"
mode_outtake_txt_2="False"
outtake_mode_flag=True
out_act_txt_2="Stop"
out_act_txt="Start"
outk_ctrl_flag=True

 
out_act_flag=False
up_sns_flag=True
lowr_sns_flag=True
sen_lwr_icon=False

intake_ctrl_flag=False 

lock_ser_data_flag=False

work_in=False
work_out=False

out_still_con=False

ser_time=0
item_name="none"

indata=""
old_indata="0"
we_data=0.00
req_val=0.00
req_val_out=0.00

last_date="0"

password="0"

err_f=False
old_time_out="0"
last_date_in="0"
emil_flag="0"
log_last_time=""
remot_out_thrd_flag=False

try:
    ser=serial.Serial('/dev/ttyUSB0',1200,timeout=0.05)
except:
    ser=serial.Serial('/dev/ttyUSB1',1200,timeout=0.05)
     
# ---------------------------------- pinset --------------------------------
lowr_sns_pin=10
up_sns_pin=22
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

GPIO.setmode(GPIO.BCM)
time.sleep(0.01)
GPIO.cleanup()
GPIO.setmode(GPIO.BCM)


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


#GPIO.setup(emg_up_sns_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
#GPIO.setup(alm_stp_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)

GPIO.setup(lock_btn_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)


GPIO.setup(outk_remot_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(pwr_pin,GPIO.IN,pull_up_down=GPIO.PUD_DOWN)


GPIO.setup(timer_pin,GPIO.OUT)
GPIO.output(timer_pin,0)

GPIO.setup(in_wei_led,GPIO.OUT)
GPIO.setup(out_wei_led,GPIO.OUT)

GPIO.setup(myrelay,GPIO.OUT)
GPIO.setup(alm_led,GPIO.OUT)
GPIO.setup(pwr_led,GPIO.OUT)
GPIO.setup(out_solv,GPIO.OUT)
GPIO.setup(in_solv,GPIO.OUT)

GPIO.setup(ind_led_in,GPIO.OUT)
GPIO.setup(ind_led_out,GPIO.OUT)


GPIO.output(myrelay,1)
GPIO.setup(out_wei_led,GPIO.OUT)
GPIO.output(alm_led,0)
GPIO.output(pwr_led,0)
GPIO.output(out_solv,0)
GPIO.output(in_solv,0)

GPIO.output(in_wei_led,0)
GPIO.output(out_wei_led,0)
GPIO.setup(b_led,GPIO.OUT)


GPIO.output(ind_led_in,0)
GPIO.output(ind_led_out,0)



GPIO.setup(lowr_sns_pin,GPIO.IN)
GPIO.setup(up_sns_pin,GPIO.IN)




def bull_start(name,dely):
    time.sleep(dely)
    auto_remot_in_thrd("noe",0.001)
    
    
#GPIO.output(pwr_led,1)

#--------------------------------auto_remot_out_thread --------------------------------

def remot_out_thrd(name,delay):
    delay=0.001
    global we_data
    global req_val_out
    global outk_ctrl_flag
    global lowr_sns_pin
    global req_val_out
    global out_pipe

    global w
    global outk_remot_pin
    global pwr_pin
    global work_out
    global work_in
    global work_out_count
    global ser_data
    global err_f
    global int_act_flag
    global out_still_con
    global old_time_out
    global out_act_flag
    global remot_out_thrd_flag
    global relay_normal_off_pin
    
    if(remot_out_thrd_flag==True):
        print "outfeed begin.but return"    
        return
    print "outfeed begin"
    
    remot_out_thrd_flag=True
    out_still_con=True
    
    datenw=datetime.datetime.today().strftime('%Y-%m-%d')
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    wrt_master_log([str(datenw),str(timenw),"start auto remote thread"])

         
    GPIO.output(ind_led_out,1)
    if(work_in==True):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_master_log([str(datenw),str(timenw),"wait untill intake process.outfeed pending"])
            
        while(work_in==True):
            #print "ghg"    
            time.sleep(1)
            
    datenw=datetime.datetime.today().strftime('%Y-%m-%d')
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    wrt_master_log([str(datenw),str(timenw),"outfeed need.intake not prceoss. going down"])
        
    print "wada karnne meka"
    req_val_out=float(out_enty.get())-float(tol_enty2.get()) 
    mode_btn_out.config(state=DISABLED)
    outk_ctrl_btn.config(state=DISABLED)

    
    
    out_act_btn.config(text="Start",bg="RED")
    out_act_btn_lbl.config( text="Stop")
    work_out_count=0

    time.sleep(5)    

    te_val=we_data
    w.delete(out_pipe)
    out_pipe=w.create_line(0,320,35,320,fill="GREEN4",width=10)
    out_enty.config(state=DISABLED)
    if(work_out==False and GPIO.input(val_up_pin)==False) :
        print("cannot opn lower val")
        
    
        #sts_lbl.config( text="Cannot open outfeed valve")
        #wrt_log([datetime.datetime.now().date(),datetime.datetime.now().time(),"outfeed valve not open","*","*","*"])
        #GPIO.output(alm_led,1)
     
         
    
    #while(GPIO.input(relay_normal_off_pin)==False and out_act_flag==True and we_data>te_val-req_val_out  and te_val-req_val_out>0.00 and  GPIO.input(pwr_pin)==True and work_in==False  and len(ser_data)>0):       
    while(GPIO.input(relay_normal_off_pin)==False and out_act_flag==True    and te_val-req_val_out>0.00 and  GPIO.input(pwr_pin)==True and work_in==False  and len(ser_data)>0):       

  
        time.sleep(delay)
        GPIO.output(out_solv,1)
        out_act_btn.config(text="Start")
        out_act_btn_lbl.config(text="Stop")
        #work_out=True
 
        
     
    
    datenw=datetime.datetime.today().strftime('%Y-%m-%d')
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    wrt_master_log([str(datenw),str(timenw),"ending outfeed prcess "])

    wrt_master_log([str(datenw),str(timenw),"outfeed conditions",GPIO.input(relay_normal_off_pin),out_act_flag,te_val-req_val_out,GPIO.input(pwr_pin), work_in, len(ser_data)])       

    
    work_out_count=0    
    #work_out=False
    GPIO.output(out_solv,0)
    w.delete(out_pipe)
    out_pipe=w.create_line(0,320,35,320,fill="GRAY",width=10)
   

  
    time.sleep(5)
    GPIO.output(ind_led_out,0)

     #intk_start_event("after out trig")
    
    if(we_data<=te_val-req_val_out or GPIO.input(relay_normal_off_pin)==True  ):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        gap=float(te_val)-float(we_data)
        try:
            if(int_act_flag==0):
                wrt_master_log([str(datenw),str(timenw),"pushing bull start for intake"])
                thread.start_new_thread( bull_start, ("Thread-1", 0.1, ) )

        except:
            pass
    
        if(GPIO.input(outk_remot_pin)==0 and abs(gap)>2 and old_time_out != timenw):
            old_time_out = timenw
            wrt_log([str(datenw),str(timenw),"auto_outfeed_ok",str(te_val),str(out_enty.get()),str(we_data)])
        elif(GPIO.input(outk_remot_pin)==1 and abs(gap)>2 and old_time_out != timenw ):  
            wrt_log([str(datenw),str(timenw),"manual_outfeed_ok",str(te_val),str(out_enty.get()),str(we_data)])
            old_time_out = timenw
             
        print "remote_out_ok"
    elif(len(ser_data)==0):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_halt_no_data",str(te_val),str(out_enty.get()),str(we_data)])
        
        print("out_remote_halt_no_data")
        err_f=True

    elif(GPIO.input(lowr_sns_pin)==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"no_more_oil",str(te_val),str(out_enty.get()),str(we_data)])
        print "no more  oil"
        err_f=True
    elif(GPIO.input(pwr_pin)==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_halt_relay_limit",str(te_val),str(out_enty.get()),str(we_data)])
        print("out_remote_halt_relay_limit")
        err_f=True

    elif(out_act_flag==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_halt_act_flag changed",str(te_val),str(out_enty.get()),str(we_data)])
         
        err_f=True
    elif(te_val-req_val_out<0.00):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_halt_val_error",str(te_val),str(out_enty.get()),str(we_data)])
         
        err_f=True
    elif(work_in==True ):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_halt_workInStart",str(te_val),str(out_enty.get()),str(we_data)])
         
        err_f=True      
      
        
    else:
        print "remote out halt"
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"remote_outfeed_halt",str(te_val),str(out_enty.get()),str(we_data)])


    out_act_btn.config(text="Stop")
    out_act_btn_lbl.config(text="Start")
           
 #   mode_btn_out.config(state=NORMAL)
    outk_ctrl_btn.config(state=NORMAL)
    out_enty.config(state=NORMAL)
    out_act_btn.config(text="Stop",bg="cyan2")
    out_act_btn_lbl.config( text="Start")
    
    out_still_con=False
    remot_out_thrd_flag=False
    #auto_remot_in_thrd("bul_start",0.001)

   
 
    if(GPIO.input(outtk_start_pin)==True):
        outtk_start_event("bul")
        
        



#-------------------------------- out control flag--------------------------------
def outtk_start_event(ch1):
    global out_act_flag
    global outk_ctrl_flag
    global req_val_out
    
    global outtk_start_pin
    time.sleep(0.7)
     
    if(GPIO.input(outtk_start_pin)==False):
        
     return
          
          
    out_act_flag=1
    if(outk_ctrl_flag==0):        
        try:
            
            req_val_out=float(out_enty.get())
            thread.start_new_thread( remot_out_thrd, ("Thread-1", 0.001, ) )
            print("auto_remot_out_thread ok ")
            out_act_btn.config(text="Stop")
        except:
        
            #tkMessageBox.showinfo("Error","remote out not start")
            print "Error: unable to start thread1"

                      
    print "out start" ,out_act_flag
    
#-------------------------------- out control flag--------------------------------
def outtk_stop_event(ch1):
    global out_act_flag
    global err_f
    out_act_flag=0
    print "out stop" ,out_act_flag
    err_f=False

     
#--------------------------------out thrd meka wada naa.uda eka wada  --------------------------------

def remote_out_thrd(thrd,delay):
    global we_data
    global req_val_out
    global out_pipe
    global w
    global lowr_sns_pin
    global out_act_flag
    global pwr_pin
    global te_val
    global req_val_out
    global work_out
    global work_in
    global work_out_count
    global ser_data
    global err_f
    #print "sdf236ewferf"
    w.delete(out_pipe)
    out_pipe=w.create_line(0,320,35,320,fill="GREEN4",width=10)
    te_val=we_data
     
     
    out_act_btn.config(text="Stop",bg="RED")
    out_act_btn_lbl.config( text="Start")
    work_out_count=0

    if(work_out==False and GPIO.input(val_up_pin)==False) :
        print("cannot opn lower val") 
        #sts_lbl.config( text="Cannot open outfeed valve")
        #wrt_log([datetime.datetime.now().date(),datetime.datetime.now().time(),"outfeed valve not open","*","*","*"])
        GPIO.output(alm_led,1)

             
            
    
    while(te_val-req_val_out<we_data and out_act_flag==1 and  work_in==False  and GPIO.input(pwr_pin)==True  and len(ser_data)>0):
        time.sleep(delay) 
        GPIO.output(out_solv,1)
        #work_out=True
        GPIO.output(ind_led_out,1)

    
    GPIO.output(ind_led_out,0)
        
    work_out_count=0 
    #work_out=False
    GPIO.output(out_solv,0)  
    w.delete(out_pipe)
    out_pipe=w.create_line(0,320,35,320,fill="GRAY",width=10)
     
    mode_btn_out.config(state=NORMAL)
    outk_ctrl_btn.config(state=NORMAL)
    out_enty.config(state=NORMAL)
    out_act_btn.config(text="Stop")
    out_act_btn_lbl.config( text="Start")

    #print we_data,te_val-req_val_out,out_act_flag,GPIO.input(lowr_sns_pin)
    if(te_val-req_val_out<=we_data  and out_act_flag==1  ):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_ok",str(te_val),str(req_val_out),str(we_data)])
        print(" out local ok")
    elif(len(ser_data)==0):
            
        out_act_btn.config( text="Stop")
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_ok",str(te_val),str(req_val_out),str(we_data)])
        print("halt_auto_in_local_no_data")
        err_f=True


    elif(  GPIO.input(lowr_sns_pin)==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_ok",str(te_val),str(req_val_out),str(we_data)])
        print("tank emty. outfeed halt")
        err_f=True
    elif(GPIO.input(pwr_pin)==False):
            
        out_act_btn.config( text="Stop")
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_ok",str(te_val),str(req_val_out),str(we_data)])
        print("halt_auto_in_localrelay_limit")
        err_f=True
    else:
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"out_remote_ok",str(te_val),str(req_val_out),str(we_data)])
        print(" out local halt")
   
     
    #tkMessageBox.showinfo("Error","Input value error")
    mode_btn_out.config(state=NORMAL)
    outk_ctrl_btn.config(state=NORMAL)
    out_enty.config(state=NORMAL)
    out_act_btn.config(text="Start",bg="cyan2")
    out_act_flag=0
    out_act_btn_lbl.config( text="Stop")
     

#--------------------------------auto_local_in_thread --------------------------------
       
def auto_local_in_thrd(thrd_name,delay):
    global we_data
    global req_val
    global lowr_sns_pin
    global up_sns_pin
     
    global in_pipe
    global int_act_flag
    global pwr_pin
    global req_val
    global lowr_sns_pin
    global up_sns_pin
    global work_in
    global work_out
    global intk_mode_flag
    global work_in_count
    global ser_data
    global err_f
    
    while(int_act_flag==0  ):
        time.sleep(delay)
        
         
        #print int_act_flag,GPIO.input(up_sns_pin)

            
        low_v=float(low_entry.get())
        
        while(GPIO.input(lowr_sns_pin)==True and we_data> low_v):
            time.sleep(delay)
             
             
        while( work_out==True):
            time.sleep(delay)
             
        GPIO.output(ind_led_in,1)    
        req_val=float(int_enty.get()) -float(tol_enty.get())
        te_val=we_data
        w.delete(in_pipe)
        in_pipe=w.create_line(0,40,35,40,fill="GREEN4",width=10)
        mode_btn_out.config(state=DISABLED)
        outk_ctrl_btn.config(state=DISABLED)
        out_enty.config(state=DISABLED)
        out_act_btn.config(state=DISABLED)

        int_act_btn.config(bg="RED")
        work_in_count=0

        if(work_in==False and GPIO.input(val_up_pin)==False) :
            print("cannot opn upper val") 
            #sts_lbl.config( text="Cannot open intake valve")
            #wrt_log([datetime.datetime.now().date(),datetime.datetime.now().time(),"Intake valve not open","*","*","*"])
            #GPIO.output(alm_led,1)

        
        while(we_data<req_val and int_act_flag==0 and work_out==False and GPIO.input(up_sns_pin)==False and GPIO.input(pwr_pin)==True and len(ser_data)>0):
            time.sleep(delay)
            GPIO.output(in_solv,1)
            #work_in=True
            print intk_mode_flag
        work_in_count=0
        #work_in=False
        int_act_btn.config(bg="cyan2")     
        GPIO.output(in_solv,0)    
        w.delete(in_pipe)
        in_pipe=w.create_line(0,40,35,40,fill="GRAY",width=10)
        mode_btn_out.config(state=NORMAL)
        outk_ctrl_btn.config(state=NORMAL)
        out_enty.config(state=NORMAL)
        out_act_btn.config(state=NORMAL)
        time.sleep(5)
        if(we_data>=req_val and  GPIO.input(up_sns_pin)==False ):                    
            print("auto_in_ok")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"auto_in_ok",str(te_val),str(int_enty.get()),str(we_data)])
        elif(len(ser_data)==0):
            int_act_flag=1
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"halt_auto_in_local_no_data",str(te_val),str(int_enty.get()),str(we_data)])

            print("halt_auto_in_local_no_data")
            err_f=True

        elif( GPIO.input(up_sns_pin)==True):
            int_act_flag=1
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"halt_auto_in_local_limit_over",str(te_val),str(int_enty.get()),str(we_data)])
            print("halt_auto_in_local_limit_over")
            err_f=True
        elif(GPIO.input(pwr_pin)==False):
            int_act_flag=1
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"halt_auto_in_local_relay_limit",str(te_val),str(int_enty.get()),str(we_data)])
            print("halt_auto_in_local_relay_limit")
            err_f=True
        elif(we_data<req_val and GPIO.input(up_sns_pin)==False ):
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"auto_in_halt",str(te_val),str(int_enty.get()),str(we_data)])
            print("auto_in_halt")
            
        '''while(GPIO.input(lowr_sns_pin)==False):
            time.sleep(delay)'''

             
    int_act_txt="Start"
    int_act_txt_2="Stop"
    int_act_btn.config(text=int_act_txt)
    int_act_lbl.config(text=int_act_txt_2)
    mode_btn_in.config(state=NORMAL)
    intk_ctrl_btn.config(state=NORMAL)
    int_enty.config(state=NORMAL)
    GPIO.output(ind_led_in,0)
     
#********************************* intake manual remote thrd  ***********************************************
def manual_remot_in_thrd(thrd,delay):    
    global we_data
    global req_val
    global in_pipe
    global up_sns_pin
    global pwr_pin
    global te_val
    global int_act_flag
    global intake_ctrl_flag
    global work_in
    global work_out
    global intk_mode_flag
    global work_in_count
    global ser_data
    global err_f 
     
    int_act_btn.config( bg="RED")
    te_val=we_data
    w.delete(in_pipe)
    in_pipe=w.create_line(0,40,35,40,fill="GREEN4",width=10)
    mode_btn_out.config(state=DISABLED)
    outk_ctrl_btn.config(state=DISABLED)
    out_enty.config(state=DISABLED)
    out_act_btn.config(state=DISABLED)
        
    int_act_txt="Start"
    int_act_txt_2="Stop"
    int_act_btn.config( text="Start")
    int_act_lbl.config( text="Stop")    

    work_in_count=0
    datenw=datetime.datetime.today().strftime('%Y-%m-%d')
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    wrt_master_log([str(datenw),str(timenw),"begin inthae manual remote "])
    
    if(work_in==False and GPIO.input(val_up_pin)==False) :
        print("cannot opn upper val") 
        #sts_lbl.config( text="Cannot open intake valve")
        #wrt_log([datetime.datetime.now().date(),datetime.datetime.now().time(),"Intake valve not open","*","*","*"])
        #GPIO.output(alm_led,1)
        
    while(len(ser_data)>0 and we_data<te_val+req_val and intk_mode_flag==False and int_act_flag==1 and work_out==False and intake_ctrl_flag==0 and GPIO.input(up_sns_pin)==False and GPIO.input(pwr_pin)==True):
        time.sleep(delay)
        GPIO.output(in_solv,1)
        #work_in=True
        GPIO.output(ind_led_in,1)
      
    work_in_count=0
    #work_in=False
    GPIO.output(in_solv,0)
    GPIO.output(ind_led_in,0)
    
    datenw=datetime.datetime.today().strftime('%Y-%m-%d')
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    wrt_master_log([str(datenw),str(timenw),"ending intake manual remote "])

    
    w.delete(in_pipe)
    in_pipe=w.create_line(0,40,35,40,fill="GRAY",width=10)
    time.sleep(5)
    if(we_data>=te_val+req_val and  GPIO.input(up_sns_pin)==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_in_ok",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_in_ok")
    elif( len(ser_data)==0):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_In__no_data",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_In__no_data")
        err_f=True
        
    elif(GPIO.input(pwr_pin)==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_In_halt_relay_limit",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_In_halt_relay_limit")
        err_f=True
    elif(  GPIO.input(up_sns_pin)==True):
        
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_In_limit_over",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_In_limit_over")
        err_f=True
    else:
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_in_halt",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_in_halt")

    int_act_btn.config( bg="cyan2")
    intk_ctrl_btn.config(state=NORMAL)
    int_enty.config(state=NORMAL)
    mode_btn_out.config(state=NORMAL)
    outk_ctrl_btn.config(state=NORMAL)
    out_enty.config(state=NORMAL)
    out_act_btn.config(state=NORMAL)
    int_act_txt="Stop"
    int_act_txt_2="Start"
    int_act_btn.config( text="Stop")
    int_act_lbl.config( text="Start")
    int_act_flag=1
    
    
    
    
#********************************* intake auto thrd  remote ***********************************************

def auto_remot_in_thrd(thrd,delay):
    global we_data
    global req_val
    global lowr_sns_pin
    global up_sns_pin
     
    global in_pipe
    global int_act_flag
    global pwr_pin
    global req_val
    global lowr_sns_pin
    global up_sns_pin
    global work_in
    global work_out
    global  intk_mode_flag
    global intake_ctrl_flag
    global work_in_count
    global ser_data
    global err_f 
    global out_still_con
    global err_f
    global last_date_in
    global intk_ctrl_flag
    
    int_act_btn.config(text="Start")
    int_act_lbl.config(text="Stop")

    datenw=datetime.datetime.today().strftime('%Y-%m-%d')
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    wrt_master_log([str(datenw),str(timenw),"begin intake auto remote "])
    int_act_flag=1
    while(int_act_flag  ):

        
        time.sleep(delay)
        
        GPIO.output(ind_led_in,1)
             
        while(out_still_con==True):
            time.sleep(1)
        
        low_v=float(low_entry.get())

        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_master_log([str(datenw),str(timenw),"now wait for lower sens or value "])
    
        while(GPIO.input(lowr_sns_pin)==True and we_data>  low_v):
            time.sleep(delay)             
      

        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_master_log([str(datenw),str(timenw),"wait for outfeed in process.next is intake auto "])
    
        while(work_out==True):
            time.sleep(1)
            
            
        
        wrt_master_log([str(datenw),str(timenw),"wait seconds now"])    
        time.sleep(10)
        wrt_master_log([str(datenw),str(timenw),"wait untill out stabale"])
        while(out_still_con==True):
            time.sleep(1)
        int_act_btn.config(bg="RED")
    
        req_val=float(int_enty.get()) -float(tol_enty.get())
        te_val=we_data
        w.delete(in_pipe)
        in_pipe=w.create_line(0,40,35,40,fill="GREEN4",width=10)
        mode_btn_out.config(state=DISABLED)
        outk_ctrl_btn.config(state=DISABLED)
        out_enty.config(state=DISABLED)
        out_act_btn.config(state=DISABLED)

        work_in_count=0

        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        
    
        if(work_in==False and GPIO.input(val_up_pin)==False) :
            print("cannot opn upper val") 
            #sts_lbl.config( text="Cannot open intake valve")
            #wrt_log([datetime.datetime.now().date(),datetime.datetime.now().time(),"Intake valve not open","*","*","*"])
            #GPIO.output(alm_led,1)
        wrt_master_log([str(datenw),str(timenw),"again wait untill u outfeed stable"])
        while(out_still_con==True):
            time.sleep(1)
        wrt_master_log([str(datenw),str(timenw),"stating valve intake auto remote "])    
        while(len(ser_data)>0 and we_data<req_val and intk_ctrl_flag==False and int_act_flag==1 and intk_mode_flag==True   and GPIO.input(up_sns_pin)==False and GPIO.input(pwr_pin)==True):
            time.sleep(delay)
            GPIO.output(in_solv,1)
            #work_in=True
        work_in_count=0
        #work_in=False    
        GPIO.output(in_solv,0)    
        w.delete(in_pipe)
        in_pipe=w.create_line(0,40,35,40,fill="GRAY",width=10)
        mode_btn_out.config(state=NORMAL)
        outk_ctrl_btn.config(state=NORMAL)
        out_enty.config(state=NORMAL)
        out_act_btn.config(state=NORMAL)
        int_act_btn.config(bg="cyan2")
        time.sleep(5)

        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_master_log([str(datenw),str(timenw),"ending intake auto remote "])
        wrt_master_log([str(datenw),str(timenw),"intake conditions",GPIO.input(relay_normal_off_pin),out_act_flag,te_val-req_val_out,GPIO.input(pwr_pin), work_in, len(ser_data)])       

        gap=float(te_val)-float(we_data)
        
         

         
         
        if(we_data>=req_val and  GPIO.input(up_sns_pin)==False and abs(gap)>2 and last_date_in!=timenw):                    
            print("auto_in_ok")
            last_date_in=timenw
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"auto_in_ok",str(te_val),str(int_enty.get()),str(we_data)])
        elif(len(ser_data)==0):
            int_act_flag=0
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"halt_auto_in_local_no_data",str(te_val),str(int_enty.get()),str(we_data)])
            print("halt_auto_in_local_no_data")
            err_f=True

        elif( GPIO.input(up_sns_pin)==True):
            int_act_flag=0
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"halt_auto_in_local_limit_over",str(te_val),str(int_enty.get()),str(we_data)])
            print("halt_auto_in_local_limit_over")
            err_f=True
        elif(GPIO.input(pwr_pin)==False):
            int_act_flag=0
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"halt_auto_in_local_relay_limit",str(te_val),str(int_enty.get()),str(we_data)])
            print("halt_auto_in_local_relay_limit")
            err_f=True

        elif(intk_ctrl_flag==True):
            int_act_flag=0
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"remote_local_isr",str(te_val),str(int_enty.get()),str(we_data)])
            #print("halt_auto_in_local_relay_limit")
            err_f=True

        elif(intk_mode_flag==False):
            int_act_flag=0
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"auto_manual_chng_intake",str(te_val),str(int_enty.get()),str(we_data)])
            #print("halt_auto_in_local_relay_limit")
            err_f=True
            
            
        elif(int_act_flag==0):
            int_act_flag=0
            int_act_btn.config( text="Stop")
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            #wrt_log([str(datenw),str(timenw),"int_act_flag set to 0 ",str(te_val),str(int_enty.get()),str(we_data)])
            #print("halt_auto_in_local_relay_limit")
            #err_f=True

              

              
        elif(we_data<req_val and GPIO.input(up_sns_pin)==False ):
            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_log([str(datenw),str(timenw),"auto_in_halt",str(te_val),str(int_enty.get()),str(we_data)])
            print("auto_in_halt")
            int_act_flag=0
        '''while(GPIO.input(lowr_sns_pin)==False):
            time.sleep(delay)'''
    GPIO.output(ind_led_in,0)
    
    if( intk_ctrl_flag==True):

            datenw=datetime.datetime.today().strftime('%Y-%m-%d')
            timenw=datetime.datetime.today().strftime('%H:%M:%S')
            wrt_master_log([str(datenw),str(timenw),"intk_ctrl_flag true. return "])
    
            int_act_txt="Stop"
            int_act_txt_2="Start"
            int_act_btn.config(text=int_act_txt)
            int_act_lbl.config(text=int_act_txt_2)
            mode_btn_in.config(state=NORMAL)
            intk_ctrl_btn.config(state=NORMAL)
            int_enty.config(state=NORMAL)
            int_act_btn.config(state=NORMAL)

        
    
    
#********************************* intake manual thrd  local ***********************************************

def manual_local_in_thrd(thrd,delay):
    global we_data
    global req_val
    global in_pipe
    global up_sns_pin
    global pwr_pin
    global te_val
    global int_act_flag
    global intk_ctrl_flag
    global work_in
    global work_out
    global work_in_count
    global ser_data
    global err_f 
    te_val=we_data
    w.delete(in_pipe)
    in_pipe=w.create_line(0,40,35,40,fill="GREEN4",width=10)
      
    w.delete(in_pipe)
    in_pipe=w.create_line(0,40,35,40,fill="GREEN4",width=10)
    mode_btn_out.config(state=DISABLED)
    outk_ctrl_btn.config(state=DISABLED)
    out_enty.config(state=DISABLED)
    out_act_btn.config(state=DISABLED)
    int_act_btn.config( bg="RED")
     
    work_in_count=0
    
    req_val=float(int_enty.get()) -float(tol_enty.get())

    datenw=datetime.datetime.today().strftime('%Y-%m-%d')
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    wrt_master_log([str(datenw),str(timenw),"intake manual local begin "])
    if(work_in==False and GPIO.input(val_up_pin)==False) :
        print("cannot opn upper val") 
        sts_lbl.config( text="Cannot open intake valve")
        #wrt_log([datetime.datetime.now().date(),datetime.datetime.now().time(),"Intake valve not open","*","*","*"])
        #GPIO.output(alm_led,1)
        
    while(we_data<te_val+req_val and int_act_flag==0 and work_out==False and GPIO.input(up_sns_pin)==False and GPIO.input(pwr_pin)==True and len(ser_data)>0):
          time.sleep(delay)
          GPIO.output(in_solv,1)
          #work_in=True
          GPIO.output(ind_led_in,1)
          
    work_in_count=0
    #work_in=False
    GPIO.output(in_solv,0)        
    w.delete(in_pipe)
    GPIO.output(ind_led_in,0)
     
    in_pipe=w.create_line(0,40,35,40,fill="GRAY",width=10)

    if(we_data>=te_val+req_val and  GPIO.input(up_sns_pin)==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_in_ok",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_in_ok")
    elif( len(ser_data)==0):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_In_no_data",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_In_no_data")
        err_f=True
         
        
    elif(GPIO.input(pwr_pin)==False):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_In_halt_relay_limit",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_In_halt_relay_limit")
        err_f=True 
         
    elif(  GPIO.input(up_sns_pin)==True):
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_In_limit_over",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_In_limit_over")
        err_f=True 
    else:
        datenw=datetime.datetime.today().strftime('%Y-%m-%d')
        timenw=datetime.datetime.today().strftime('%H:%M:%S')
        wrt_log([str(datenw),str(timenw),"manual_in_halt",str(te_val),str(int_enty.get()),str(we_data)])
        print("manual_in_halt")
        
    int_act_flag=1   
    int_act_btn.config( bg="cyan2")
    mode_btn_in.config(state=NORMAL)
    intk_ctrl_btn.config(state=NORMAL)
    int_enty.config(state=NORMAL)
    mode_btn_out.config(state=NORMAL)
    outk_ctrl_btn.config(state=NORMAL)
    out_enty.config(state=NORMAL)
    out_act_btn.config(state=NORMAL)
    int_act_txt="Start"
    int_act_txt_2="Stop"
    int_act_btn.config( text="Start")
    int_act_lbl.config( text="Stop")
    

    

#********************************* intaje start event  ***********************************************
def intk_start_event(name ):

    time.sleep(0.7)
     
     
    global  int_act_flag
    global intke_remot_pin
    global int_act_flag
    global req_val
    global intke_start_pin
    
    if(GPIO.input(intke_start_pin)==False):
        
        
     return
    
     
    int_act_flag=1
    print int_act_flag

             #remote eke manual in 
    if(intk_ctrl_flag==0 and GPIO.input(intke_remot_pin)==True and int_act_flag==1):

        try:
             
            req_val=float(int_enty.get())- float(tol_enty.get()) 
            thread.start_new_thread( manual_remot_in_thrd, ("Thread-1", 0.001, ) )               
        except:
         
            #tkMessageBox.showinfo("error","manual remote not start")
            print "Error: unable to start thread1"
            int_act_flag=0

    elif(intk_ctrl_flag==0 and GPIO.input(intke_remot_pin)==False and int_act_flag==1):

        try:
             
            req_val=float(int_enty.get())-float(tol_enty.get()) 
            thread.start_new_thread( auto_remot_in_thrd, ("Thread-1", 0.001, ) )
            print("auto remote in")
        except:
            tkMessageBox.showinfo("error,auto remote in not start")
               
            print "Error: unable to start thread1"
            int_act_flag=0
        


#********************************* intaje stop event  ***********************************************
def intk_stop_event(name ):
    global  int_act_flag
    global err_f
    
    int_act_flag=0
    print int_act_flag
    err_f=False


#********************************* clock update  *************************************************************
def clock_hz(name,delay):
    
    
    while(1):
       
        time.sleep(60)
        try:
            
            os.system('sudo hwclock -w')
        except:
            print "error set clock"
            
        
         
            


#********************************* 1 hz *************************************************************
def one_hz(name,delay):
    global counter
    global work_in_count
    global work_out_count
    
    while(1):
        counter=counter+1
        time.sleep(1)
        '''try:
            
            os.system('sudo hwclock -w')
        except:
            pass'''
        
        work_in_count=work_in_count+1
        work_out_count=work_out_count+1
        if(counter>60):
            GPIO.output(timer_pin,1)


#******************************************* read xml ***********************************************
def txt_read(): 
    global xcl_data
    with open("/home/pi/Desktop/log.csv") as rd:        
        rdcsv=csv.reader(rd,delimiter=',')
        for row in rdcsv:
           
            xcl_data+=row[0]+"---\t"+row[1]+"---\t"+row[2]+"---\t"+row[3]+"---\t"+row[4]+"---\t"+row[5]+"\n"

        t.delete(1.0,END)
        t.insert(END,xcl_data)
        xcl_data=""
        t.see(Tkinter.END)

#----------------------------- tec log --------------------------------------

def wrt_master_log( log_d):
    global item_name
    
    
        
   
    try:        
        with open("/home/pi/Desktop/master_log.csv","a") as fp:
              wr=csv.writer(fp,dialect='excel')
              wr.writerow(log_d)
    except:
        print "error write log"

        

#--------------------------------canvas update --------------------------------
def wrt_log( data):
    global item_name
    
    global log_last_time
    
    timenw=datetime.datetime.today().strftime('%H:%M:%S')
    if( timenw == log_last_time):
        return
    else:
        log_last_time=timenw
        
    
    data.append(item_name)
   
    try:        
        with open("/home/pi/Desktop/log.csv","a") as fp:
              wr=csv.writer(fp,dialect='excel')
              wr.writerow(data)
    except:
        print "error write log"


    try:        
        with open("/home/pi/Desktop/log_ind.csv","a") as fp:
              wr=csv.writer(fp,dialect='excel')
              wr.writerow(data)
    except:
        print "error write log"
        
        

    '''var=datetime.datetime.now().hour
    print "time is ",var
    if(var>=6 and var<14  ):
        try:           
            with open("/home/pi/Desktop/log_1.csv","a") as fp:               
                wr=csv.writer(fp,dialect='excel')
                wr.writerow(data)
        except:
            print "error write log1"
        
    elif(var>=14 and var<22  ):
        try:           
            with open("/home/pi/Desktop/log_2.csv","a") as fp:               
                wr=csv.writer(fp,dialect='excel')
                wr.writerow(data)
        except:
            print "error write log2"
    elif((var>=22 and var<23 ) or var<=5 ):
        try:           
            with open("/home/pi/Desktop/log_3.csv","a") as fp:               
                wr=csv.writer(fp,dialect='excel')
                wr.writerow(data)
        except:
            print "error write log3"'''
        
        
    

#--------------------------------infity loop-------------------------------
def inf_loop(threadName, delay):
  global indata
  tem_indata=""
  global  sen_up_icon
  global  sen_lwr_icon

  global up_sns_flag
  global lowr_sns_flag
    
  global  w
  global  we_data
  global mode_intake_txt_2 
  global fil_bar_up
  global fil_bar_lwr
  global fill_per
  global up_sns_pin
  global lowr_sns_pin
  global pwr_flag
  global counter
  global old_counter
  global intk_ctrl_flag
  global intke_remot_pin
  global mode_intake_txt
  global intake_ctrl_flag
  global int_act_txt
  global int_act_txt_2
  global int_act_flag
  global intake_ctrl_flag
  global req_val
  global in_wei_led
  global out_wei_led
  global ke_counter
  global intk_mode_flag
  global work_in
  global work_out
  global work_in_count
  global work_out_count
  global val_up_pin
  global val_down_pin
  global ser_flag
  global ser_data
  global item_name
  global ser_time
  global password
  global err_flg
  global outk_ctrl_flag
  global time_out
  global out_solv
  global err_f
  global outk_remot_pin
  global old_indata
  global lock_ser_data_flag
 
  global emil_flag
  while(1):
    #print counter 
         
    #time.sleep(delay)  
    pwr_flag=GPIO.input(pwr_pin)
    #GPIO.output(pwr_led,pwr_flag^1)



    GPIO.output(in_wei_led,GPIO.input(out_solv))
    GPIO.output(out_wei_led,GPIO.input(in_solv))



    '''if(work_in==True  and GPIO.input(val_up_pin)==False and work_in_count>10 and work_in_count<20) :
        print("cannot opn upper val") 
        sts_lbl.config( text="Cannot open intake valve")
        wrt_log([datetime.datetime.now(),"Intake valve not open","*","*","*"])
        GPIO.output(alm_led,1)  
        work_in_count=50

    elif(work_out==True  and GPIO.input(val_down_pin)==False and work_out_count>10 and work_out_count<20) :
        print("cannot opn lower val")
        sts_lbl.config( text="Cannot open outfeed valve")
        wrt_log([datetime.datetime.now(),"Outfeed valve not open","*","*","*"])
        GPIO.output(alm_led,1)
        work_out_count=50'''

    
    if(GPIO.input(lock_btn_pin)==0 ):       
        outk_ctrl_btn.config(state=DISABLED)
        out_act_btn.config(state=DISABLED)
        mode_btn_out.config(state=DISABLED)
        mode_btn_in.config(state=DISABLED)
        intk_ctrl_btn.config(state=DISABLED)
        int_act_btn.config(state=DISABLED)
        
        
    else :
        outk_ctrl_btn.config(state=NORMAL)
        out_act_btn.config(state=NORMAL)
        mode_btn_out.config(state=NORMAL)
        mode_btn_in.config(state=NORMAL)
        intk_ctrl_btn.config(state=NORMAL)  
        int_act_btn.config(state=NORMAL)
        

    if(GPIO.input(outk_remot_pin)==0 and outk_ctrl_flag==False ):
        #mode_btn_out_lbl = Tkinter.Label(f1,text="Manual")
        mode_btn_out.config(text="Auto")
         
    elif(GPIO.input(outk_remot_pin)==1 and outk_ctrl_flag==False ):
        #mode_btn_out_lbl = Tkinter.Label(f1,text="Auto")
        mode_btn_out.config(text="Manual")
         
        


        
    if(GPIO.input(in_solv)==1):
        work_in=True
    else:
        work_in=False


    if(GPIO.input(out_solv)==1):
        work_out=True
    else:
        work_out=False    
         
    

    bb=int(time_entry.get())
           
    if( time_out>bb):
        #err_f=True   // time out eke alarm eka
        pass

        
        
        
    if(work_in==False  and work_out==False ) :
        #print(" opn upper val") 
        sts_lbl.config( text=" ")
        GPIO.output(alm_led,0)  
        #work_in_count=50

    
            
    '''else:
        GPIO.output(alm_led,0)
        #sts_lbl.config( text="Ready")'''
        
    
    
    try:            
        if(pwr_flag):            
            supply_lbl.config( text="Power OK")
        else:
            supply_lbl.config( text="Power Down")
    except:
        pass
         


        
   
    
    #ser.flush()
    
    dt=ser.readline()  
    ser.flushInput()
    
    
    '''dt=dt.replace("ST,GS,","")
    dt=dt.replace("US,GS,","")       
    dt=dt.replace("kg","")
    dt=dt.replace(" ","")
    dt=dt.replace(" ","")'''
    dt=dt.replace("=","")
    dt=dt.replace(" ","")
    print dt   
    if(len(dt)>1):
           ser_time=0
           
    
        
    #print(ser_data)
    '''if(lock_ser_data_flag==False    ):
        old_indata=float(dt)
        lock_ser_data_flag=True
        print "sdf"
        
    try:
                
        #we_data=float(dt)
        if(abs(float(old_indata)-float(dt))<3):
           old_indata=float(dt)
           we_data=float(dt)
           
           
        w_lbl.config(text=str(we_data) +" Kg" )
            
    except:
        pass'''

        
        

  
    try:
        
        
        ss=float(dt) 
        dif=ss-float(old_indata)
        old_indata=str(ss)
        #print ss
        if(abs(dif)<3 and float(dt)>-1):
            we_data=float(dt)
            w_lbl.config(text=str(we_data) +" Kg" )
            
        

    except:
        pass
    
    fill_per=we_data/92.00*100.00

    if(fill_per>100):
        fill_per=100
    if(fill_per<0):
        fill_per=0

    if(counter!=old_counter):
        
        
        GPIO.output(b_led,GPIO.input(b_led)^1)

        if(err_f==False):
            
            GPIO.output(pwr_led,0)
        else:
            GPIO.output(pwr_led,GPIO.input(pwr_led)^1)
            
        if(GPIO.input(out_solv)==1):
            time_out=time_out+1
        else:
            time_out=0
            
        
        if(len(dt)==0):
           ser_time=ser_time+1

        else:
            ser_time=0
            ser_data="0000"
            

        if(ser_time>8):
            ser_data=""
            
         
        old_counter=counter
        #print(dt)
        #ser.flushInput()   edited today


        file=open("/home/pi/Desktop/stuff/today.txt","r")
        last_day=file.read()
        today=time.strftime("%H")
        
        
        if(today!="06" and emil_flag=="1"):
             emil_flag="0"

            
        if(today=="06" and emil_flag=="0"):
            emil_flag="1"
            print "Sending email"
            print today
             
            '''file=open("/home/pi/Desktop/stuff/today.txt","w")
            file.write(today)
            file.close()'''

            command= "sudo python /home/pi/Desktop/stuff/mail.py"                         
            process=subprocess.Popen(command.split(),stdout=subprocess.PIPE)
            #output=process.communicate()[0]
            #print output

            
            
    
         
        
        file=open("/home/pi/Desktop/stuff/1.txt","r")
        int_enty.delete(0,END)
        int_enty.insert(0,file.read())

        file=open("/home/pi/Desktop/stuff/2.txt","r")
        out_enty.delete(0,END)
        out_enty.insert(0,file.read())

        file=open("/home/pi/Desktop/stuff/3.txt","r")
        tol_enty.delete(0,END)
        tol_enty.insert(0,file.read())

        file=open("/home/pi/Desktop/stuff/4.txt","r")
        tol_enty2.delete(0,END)
        tol_enty2.insert(0,file.read())

       

        file=open("/home/pi/Desktop/stuff/pass.txt","r")
        pass_entry.delete(0,END)
        seek=file.read()
        pass_entry.insert(0,seek)

        file=open("/home/pi/Desktop/stuff/password.txt","r")
        password=file.read()
        
        file=open("/home/pi/Desktop/stuff/5.txt","r")
        itm_enty.delete(0,END)
        seek=file.read()
        itm_enty.insert(0,seek)

        file=open("/home/pi/Desktop/stuff/time.txt","r")
        time_entry.delete(0,END)
        time_entry.insert(0,file.read())

       
        file=open("/home/pi/Desktop/stuff/low_val.txt","r")
        low_entry.delete(0,END)
        low_entry.insert(0,file.read())

        
        f=open("/home/pi/Desktop/items.csv")
        csv_f=csv.reader(f)
        
        try:
            
            for row in csv_f:                 
                if(seek==row[0]):
                    itm_lbl.config(text=str(row[2])  )
                    item_name=row[1]
                    #print item_name

                
        except:
            pass
        '''seek=i
        itm_lbl.config(text=str(item_name) +" Kg" )'''
        

         
         
         
        w.delete(fil_bar_up)
        w.delete(fil_bar_lwr)               

        fil_bar_lwr=w.create_line(80,335,80,(100-fill_per)*3.1+25,fill="GREEN4",width=10)
        fill_per=100-fill_per

                    
        fil_bar_up=w.create_line(80,25,80,(fill_per)*3.1+25,fill="SNOW2",width=10) 

#sen_up_icon=w.create_oval(110, 30,140, 60,fill='LAWN GREEN')
#sen_lwr_icon=w.create_oval(110, 280,140, 310,fill='LAWN GREEN')



    #uda sensr eka 
    if(GPIO.input(up_sns_pin)!=up_sns_flag):
    
        w.delete(sen_up_icon)
        up_sns_flag=GPIO.input(up_sns_pin)
        if(GPIO.input(up_sns_pin)==False):
            
            sen_up_icon=w.create_oval(110, 30,140, 60,fill='SNOW')
        else:              
            sen_up_icon=w.create_oval(110, 30,140, 60,fill='GOLD2')
            
         #pahala sensor eka    
    if(GPIO.input(lowr_sns_pin)!=lowr_sns_flag):
        lowr_sns_flag= GPIO.input(lowr_sns_pin) 
        w.delete(sen_lwr_icon)
        if(GPIO.input(lowr_sns_pin)==False):       
            sen_lwr_icon=w.create_oval(110, 280,140, 310,fill='SNOW')
        else:
                 
            sen_lwr_icon=w.create_oval(110, 280,140, 310,fill='LAWN GREEN')


    if(intk_ctrl_flag==0 and GPIO.input(intke_remot_pin)==0 ):
        intk_mode_flag=True
        mode_intake_txt="Auto"
        mode_intake_txt_2="Manual"
        mode_btn_in.config(text=mode_intake_txt,bg="purple4")
        mode_btn_lbl.config( text=mode_intake_txt_2)
        #GPIO.output(ind_led_in,1)
             
            
       
    elif(intk_ctrl_flag==0 and GPIO.input(intke_remot_pin)==1 ):
        intk_mode_flag=False
        mode_intake_txt="Manual"
        mode_intake_txt_2="Auto"
        mode_btn_in.config(text=mode_intake_txt)
        mode_btn_lbl.config( text=mode_intake_txt_2)
        GPIO.output(ind_led_in,0)
    
    if(intk_ctrl_flag==0 and   int_act_flag==0):       
         
        int_act_txt="Stop"
        int_act_txt_2="Start"
        int_act_btn.config(text=int_act_txt)
        int_act_lbl.config(text=int_act_txt_2)

   

        
    elif(intk_ctrl_flag==0   and int_act_flag==0):
        
        int_act_txt="Start"
        int_act_txt_2="Stop"
        int_act_btn.config(text=int_act_txt)
        int_act_lbl.config(text=int_act_txt_2)
        



#--------------------------------keybard  1 call--------------------------------

def callback1(event):
    global ke_counter
    global counter
    global password

    try:       
        inpt=int(pass_entry.get())
        inpt=inpt+1111
        
    except:
        pass
    
    
    print "keybrd need"
    ke_counter=counter
    print counter
    '''com="xvkbd"
    import subprocess
    process.subprocess.Popen(com.split(),stdout=subprocess.PIPE)
    output=process.communicate()[0]'''
    
    try:
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xvkbd ')
        #os.system('xvkbd -minimizable')
        if(int(password)==inpt):          
            os.system('sudo python /home/pi/Desktop/stuff/1_key.pyc')
        else:
            tkMessageBox.showinfo("Error","password not matched!!!")

                
    except:
        print "error"


#--------------------------------keybard  2 call--------------------------------

def callback2(event):
    global ke_counter
    global counter
    global password

    try:       
        inpt=int(pass_entry.get())
        inpt=inpt+1111
        
    except:
        pass
    
    print "keybrd need"
    ke_counter=counter
    print counter
    '''com="xvkbd"
    import subprocess
    process.subprocess.Popen(com.split(),stdout=subprocess.PIPE)
    output=process.communicate()[0]'''
    
    try:
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xv kbd ')
        #os.system('xvkbd -minimizable')

        if(int(password)==inpt):           
            os.system('sudo python /home/pi/Desktop/stuff/2_key.pyc')
        else:
            tkMessageBox.showinfo("Error","password not matched!!!")
   
    except:
        pass

#--------------------------------keybard  3 call--------------------------------

def callback3(event):
    
    global ke_counter
    global counter
    global password

    try:       
        inpt=int(pass_entry.get())
        inpt=inpt+1111
        
    except:
        pass

    print "keybrd need"
    ke_counter=counter
    print counter
    '''com="xvkbd"
    import subprocess
    process.subprocess.Popen(com.split(),stdout=subprocess.PIPE)
    output=process.communicate()[0]'''
    
    try:
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xvkbd ')
        #os.system('xvkbd -minimizable')
        if(int(password)==inpt):            
            os.system('sudo python /home/pi/Desktop/stuff/3_key.pyc')
        else:
            tkMessageBox.showinfo("Error","password not matched!!!")
   
    except:
        pass

#--------------------------------keybard 4 call--------------------------------

def callback4(event):
    
    global ke_counter
    global counter
    global password

    try:       
        inpt=int(pass_entry.get())
        inpt=inpt+1111
        
    except:
        pass
    
    print "keybrd need"
    ke_counter=counter
    print counter
    '''com="xvkbd"
    import subprocess
    process.subprocess.Popen(com.split(),stdout=subprocess.PIPE)
    output=process.communicate()[0]'''
    
    try:
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xvkbd ')
        #os.system('xvkbd -minimizable')
        if(int(password)==inpt):         
            os.system('sudo python /home/pi/Desktop/stuff/4_key.pyc')
        else:
            tkMessageBox.showinfo("Error","password not matched!!!")
    except:
        pass
        
        
#--------------------------------keybard 5 call--------------------------------

def callback5(event):
    
    global ke_counter
    global counter
    
    print "keybrd need fgjf"
    
     
    '''com="xvkbd"
    import subprocess
    process.subprocess.Popen(com.split(),stdout=subprocess.PIPE)
    output=process.communicate()[0]'''
    
    try:
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xvkbd ')
        #os.system('xvkbd -minimizable')
        os.system('sudo python /home/pi/Desktop/stuff/5_key.pyc')
    except:
        pass
        
#--------------------------------keybard 6 call--------------------------------

def callback6(event):
    
    global ke_counter
    global counter
    
     
     
    '''com="xvkbd"
    import subprocess
    process.subprocess.Popen(com.split(),stdout=subprocess.PIPE)
    output=process.communicate()[0]'''
    
    try:
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xvkbd ')
        #os.system('xvkbd -minimizable')
        os.system('sudo python /home/pi/Desktop/stuff/6_key.pyc')
    except:
        pass


#--------------------------------keybard 7 call--------------------------------

def callback7(event):
    
    global ke_counter
    global counter
    
    try:
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xvkbd ')
        #os.system('xvkbd -minimizable')
        os.system('sudo python /home/pi/Desktop/stuff/time_key.pyc')
    except:
        pass
 

#--------------------------------keybard 7 call--------------------------------

def callback8(event):
    
    global ke_counter
    global counter
    global password
    try:       
        inpt=int(pass_entry.get())
        inpt=inpt+1111
        
    except:
        pass
    
    try:

        if(int(password)==inpt):          
            os.system('sudo python /home/pi/Desktop/stuff/low_val_key.pyc')
        else:
            tkMessageBox.showinfo("Error","password not matched!!!")
            
        #os.system('killall xvkbd')
        #time.sleep(0.01)
         
        #os.system('xvkbd ')
        #os.system('xvkbd -minimizable')
        
    except:
        pass
 

    

#--------------------------------mode_itnk--------------------------------
def mode_intk():
    global intk_mode_flag  
    global mode_intake_txt_2
    intk_mode_flag=intk_mode_flag^1
    if(intk_mode_flag):
        mode_intake_txt="Auto"
        mode_intake_txt_2="Manual"
    else:
        mode_intake_txt="Manual"
        mode_intake_txt_2="Auto"
        
    mode_btn_in.config(text=mode_intake_txt)
    mode_btn_lbl.config( text=mode_intake_txt_2)
   
  
  
#--------------------------------mode_ctrl_intake--------------------------------
def in_mode_ctrl():
  
    global intk_ctrl_flag 
    global intk_ctrl_txt_2
    global int_act_flag
    global mode_btn_in
    
    intk_ctrl_flag=intk_ctrl_flag^1   
    
    if(intk_ctrl_flag):
        intk_ctrl_txt="Local"
        intk_ctrl_txt_2="Remote"
        int_act_btn.config(state=NORMAL )
        mode_btn_in.config(bg="cyan2")
        mode_btn_in.config(state=NORMAL)
    else:
        intk_ctrl_txt="Remote"
        intk_ctrl_txt_2="Local"
        mode_btn_in.config(bg="purple4")
        int_act_btn.config(state=DISABLED)
        mode_btn_in.config(state=DISABLED)
        int_act_flag=0
        
    
    intk_ctrl_lbl.config( text=intk_ctrl_txt_2)   
    intk_ctrl_btn.config(text=intk_ctrl_txt)




#--------------------------------intake action --------------------------------
def int_act_thrd():
    global int_act_flag
    global int_act_txt
    global intk_mode_flag
    global req_val
    global we_data
    global in_pipe
    global int_act

    int_act=False
    
    int_act_flag=int_act_flag^1
    

    if(intk_mode_flag==False):
        try:
            
            req_val=float(int_enty.get())- float(tol_enty.get())
            if(int_act_flag):
                int_act_txt="Start"
                int_act_txt_2="Stop"
                #intk_ctrl_txt_2="Remote"
                intk_ctrl_btn.config(state=NORMAL)
                mode_btn_in.config(state=NORMAL)
                int_enty.config(state=NORMAL)
            else:
                int_act_txt="Stop"
                int_act_txt_2="Start"
                int_enty.config(state=DISABLED)
                mode_btn_in.config(state=DISABLED)
                intk_ctrl_btn.config(state=DISABLED)
                
                try:                                        
                    print("manual_local_in")
                    thread.start_new_thread( manual_local_in_thrd, ("Thread-1", 0.001, ) )
               
                except:
                     
                     print "Error: unable to start thread1"

            int_act_btn.config(text=int_act_txt)
            int_act_lbl.config(text=int_act_txt_2)



        except:
            pass
            #tkMessageBox.showinfo("Error","Value intake input Error")

    if(intk_mode_flag==True):
        try:                                        
            
            req_val=float(int_enty.get())-float(tol_enty.get())
            print("auto_local_in")
            if(int_act_flag):
                int_act_txt="Start"
                int_act_txt_2="Stop"
                #intk_ctrl_txt_2="Remote"
                intk_ctrl_btn.config(state=NORMAL)
                mode_btn_in.config(state=NORMAL)
                int_enty.config(state=NORMAL)
            else:
                int_act_txt="Stop"
                int_act_txt_2="Start"
                int_enty.config(state=DISABLED)
                mode_btn_in.config(state=DISABLED)
                intk_ctrl_btn.config(state=DISABLED)

            
            int_act_btn.config(text=int_act_txt)
            int_act_lbl.config(text=int_act_txt_2)

            thread.start_new_thread( auto_local_in_thrd, ("Thread-1", 0.001, ) )               
        except:                     
            print "Error: unable to start thread1"


#**********************in *************************************************
mode_btn_in = Tkinter.Button(f1,text=mode_intake_txt, fg="black",bg="cyan2",command = mode_intk)
mode_btn_in.pack()
mode_btn_in.config( height = 1, width = 5,font=("Helvetica 16 bold italic", 25))
mode_btn_in.place( x=width/40,y=hight/10)

mode_btn_lbl = Tkinter.Label(f1,text="Manual")
mode_btn_lbl.config(font=("Helvetica bold ",15),fg="PINK3",justify="left")
mode_btn_lbl.place(x=width/4.3 ,y=hight/10)
  
 


intk_ctrl_btn = Tkinter.Button(f1,text=intk_ctrl_txt, fg="black",bg="cyan2",command = in_mode_ctrl)
intk_ctrl_btn.pack()
intk_ctrl_btn.config( height = 1, width = 5,font=("Helvetica 16 bold italic", 25))
intk_ctrl_btn.place(x=width/40,y=hight/10*3)


intk_ctrl_lbl = Tkinter.Label(f1,text="Remote")
intk_ctrl_lbl.config(font=("Helvetica bold ",15),fg="PINK3",justify="left")
intk_ctrl_lbl.place(x=width/4.3 ,y=hight/10*3)




int_enty = Tkinter.Entry(f1)
int_enty.pack()
int_enty.config( justify="center" ,fg="black",font=("Helvetica 16 bold italic", 25),width=7)
int_enty.place(x=width/40,y=hight/10*5)
int_enty.bind("<Button-1>",callback1)






int_act_btn = Tkinter.Button(f1, text="Start", fg="black",bg="cyan2",command = int_act_thrd)
int_act_btn.pack()
int_act_btn.config( height = 1, width = 5,font=("Helvetica 16 bold italic", 25))
int_act_btn.place( x=width/40,y=hight/10*7)

int_act_lbl = Tkinter.Label(f1,text="Stop")
int_act_lbl.config(font=("Helvetica bold ",15),fg="PINK3",justify="left")
int_act_lbl.place(x=width/4.3 ,y=hight/10*7)

w_lbl = Tkinter.Label(f1,text="00.00")
w_lbl.config(font=("Helvetica bold ",20),fg="purple4",justify="left")
w_lbl.place(x=280,y=340)

sts_lbl = Tkinter.Label(f1,text="Ok")
sts_lbl.config(font=("Helvetica bold ",18),fg="red",justify="left")
sts_lbl.place(x=10,y=350)








def mode_outtake():
    global mode_outtake_txt
    global outtake_mode_flag
    global mode_outtake_txt_2
    
    outtake_mode_flag=outtake_mode_flag^1
    if(outtake_mode_flag):
        mode_outtake_txt="Auto"
        mode_outtake_txt_2="Manual"
    else:
        mode_outtake_txt="Manual"
        mode_outtake_txt_2="Auto"
    mode_btn_out_lbl.config(text=mode_outtake_txt_2)   
    mode_btn_out.config(text=mode_outtake_txt)


# *************************************  out mode control local remote ******************************
def out_mode_ctrl():
    global outk_ctrl_flag
    global outk_ctrl_txt
    global outk_ctrl_txt_2
    global mode_btn_out 
    
    outk_ctrl_flag=outk_ctrl_flag^1
    if(outk_ctrl_flag):
        outk_ctrl_txt="Local"
        outk_ctrl_txt_2="Remote"
        mode_btn_out.config(state=NORMAL)
        out_act_btn.config(state=NORMAL)
        mode_btn_out.config(bg="cyan")
    else:
        outk_ctrl_txt="Remote"
        outk_ctrl_txt_2="Local"
        mode_btn_out.config(bg="purple4")
        mode_btn_out.config(state=DISABLED)
        out_act_btn.config(state=DISABLED)
        
    outk_ctrl_btn.config(text=outk_ctrl_txt)
    outk_ctrl_lbl.config(text=outk_ctrl_txt_2)


# *******************************************  out action  *******************************************

def out_act():
    global out_act_flag
    global out_act_txt
    global outtake_mode_flag
    global outk_ctrl_flag
    global out_act_txt_2
    global req_val_out
    global err_f
    
    out_act_flag=out_act_flag^1

    err_f=False
    if(out_act_flag):
        try:
            req_val_out=float(out_enty.get())-float(tol_enty2.get())
            #ererer
            print("local out thred ok")
            thread.start_new_thread( remote_out_thrd, ("Thread-1", 0.001, ) )
            out_act_txt="Start"
            out_act_txt_2="Stop"
            mode_btn_out.config(state=DISABLED)
            outk_ctrl_btn.config(state=DISABLED)
            out_enty.config(state=DISABLED)
            
        except:
            out_act_flag=0
            out_act_txt="Start"
            out_act_txt_2="Stop"
            mode_btn_out.config(state=NORMAL)
            outk_ctrl_btn.config(state=NORMAL)
            out_enty.config(state=NORMAL)
            #tkMessageBox.showinfo("Error","Value for outfeed input Error")
            
    else:
         out_act_txt="Stop"
         out_act_txt_2="Start"
         mode_btn_out.config(state=NORMAL)
         outk_ctrl_btn.config(state=NORMAL)
         out_enty.config(state=NORMAL)
         
    out_act_btn_lbl.config(text=out_act_txt_2)
    out_act_btn.config(text=out_act_txt)
  
#--------------------------------outk--------------------------------

mode_btn_out = Tkinter.Button(f1,text=mode_outtake_txt, fg="black",bg="cyan2",command = mode_outtake)
mode_btn_out.pack()
mode_btn_out.config( height = 1, width = 5 ,font=("Helvetica 16 bold italic", 25))
mode_btn_out.place( x=width/20*12.7,y=hight/10)

mode_btn_out_lbl = Tkinter.Label(f1,text="Manual")
mode_btn_out_lbl.config(font=("Helvetica bold ",15),fg="PINK3",justify="left")
mode_btn_out_lbl.place(x=width/20*17 ,y=hight/10)



outk_ctrl_btn = Tkinter.Button(f1,text=outk_ctrl_txt, fg="black",bg="cyan2",command = out_mode_ctrl)
outk_ctrl_btn.pack()
outk_ctrl_btn.config( height = 1, width = 5 ,font=("Helvetica 16 bold italic", 25))
outk_ctrl_btn.place(  x=width/20*12.7,y=hight/10*3)

outk_ctrl_lbl = Tkinter.Label(f1,text="Remote")
outk_ctrl_lbl.config(font=("Helvetica bold ",15),fg="PINK3",justify="left")
outk_ctrl_lbl.place(x=width/20*17 ,y=hight/10*3)




out_enty = Tkinter.Entry(f1)
out_enty.pack()
out_enty.config( justify="center" ,fg="black",font=("Helvetica 16 bold italic", 25),width=7)
out_enty.place(x=width/20*12.7,y=hight/10*5)
out_enty.bind("<Button-1>",callback2)

out_act_btn = Tkinter.Button(f1,text=out_act_txt, fg="black",bg="cyan2",command = out_act)
out_act_btn.pack()
out_act_btn.config( height = 1, width = 5,font=("Helvetica 16 bold italic", 25))
out_act_btn.place( x=width/20*12.7,y=hight/10*7)

out_act_btn_lbl = Tkinter.Label(f1,text="Stop")
out_act_btn_lbl.config(font=("Helvetica bold ",15),fg="PINK3",justify="left")
out_act_btn_lbl.place(x=width/20*17 ,y=hight/10*7)


itm_lbl = Tkinter.Label(f1,text=item_name)
itm_lbl.config(font=("Helvetica bold ",15),fg="blue",justify="left")
itm_lbl.place(x=width/20*15,y=350)


itm_enty = Tkinter.Entry(f1)
itm_enty.pack()
itm_enty.config( justify="center" ,fg="black",font=("Helvetica 16 bold italic", 18),width=4)
itm_enty.place(x=width/20*12.7,y=350)
itm_enty.bind("<Button-1>",callback5)



#********************************* second tab ***********************************************

tol_lbl = Tkinter.Label(f2,text="INTAKE INFLIGHT", fg="black")
tol_lbl.pack()
tol_lbl.config( font=("Helvetica 16 bold italic", 20),fg="purple1")
tol_lbl.place( x=0,y=hight/10) 

tol_enty = Tkinter.Entry(f2)
tol_enty.pack()
tol_enty.config(justify="center" ,fg="black",font=("Helvetica 16 bold italic", 25),width=7)
tol_enty.place( x=width/10*5,y=hight/10)
tol_enty.insert(0, "0")
tol_enty.bind("<Button-1>",callback3)


tol_lbl2 = Tkinter.Label(f2,text="OUTFEED INFLIGHT", fg="black")
tol_lbl2.pack()
tol_lbl2.config( font=("Helvetica 16 bold italic", 20),fg="purple1")
tol_lbl2.place( x=0,y=hight/4) 



tol_enty2 = Tkinter.Entry(f2)
tol_enty2.pack()
tol_enty2.config(justify="center" ,fg="black",font=("Helvetica 16 bold italic", 25),width=7)
tol_enty2.place( x=width/10*5,y=hight/4)
tol_enty2.insert(0, "0")
tol_enty2.bind("<Button-1>",callback4)


supply_lbl = Tkinter.Label(f2,text="Password", fg="black")
supply_lbl.pack()
supply_lbl.config( font=("Helvetica ", 18),fg="purple1")
supply_lbl.place( x=0,y=hight/10*7)
supply_lbl.place( x=0,y=hight/2)


pass_entry = Tkinter.Entry(f2)
pass_entry.pack()
pass_entry.config(show="*",justify="center" ,fg="black",font=("Helvetica 16 bold italic", 25),width=7)
pass_entry.place( x=width/10*5,y=hight/2)
pass_entry.insert(0, "****")
pass_entry.bind("<Button-1>",callback6)



time_lbl = Tkinter.Label(f2,text="Time", fg="black")
time_lbl.pack()
time_lbl.config( font=("Helvetica ", 18),fg="purple1")
 
time_lbl.place( x=0,y=hight/10*7)

time_entry = Tkinter.Entry(f2)
time_entry.pack()
time_entry.config(justify="center" ,fg="black",font=("Helvetica 16 bold italic", 25),width=7)
time_entry.place( x=width/10*5,y=hight/10*7)
time_entry.insert(0, "5")
time_entry.bind("<Button-1>",callback7)


L_val_lbl = Tkinter.Label(f2,text="Low value", fg="black")
L_val_lbl.pack()
L_val_lbl.config( font=("Helvetica ", 18),fg="purple1")
 
L_val_lbl.place( x=0,y=hight/10.00*9.99)


low_entry = Tkinter.Entry(f2)
low_entry.pack()
low_entry.config(justify="center" ,fg="black",font=("Helvetica 16 bold italic", 25),width=7)
low_entry.place( x=width/10*5,y=hight/10*9.99)
low_entry.insert(0, "5")
low_entry.bind("<Button-1>",callback8)


supply_lbl = Tkinter.Label(f2,text="Main Supply", fg="black")
supply_lbl.pack()
supply_lbl.config( font=("Helvetica ", 18),fg="purple1")
supply_lbl.place( x=0,y=hight/10*9)

#********************************* third tab ***********************************************

refre_btn = Tkinter.Button(f3,text="Refresh", fg="black",bg="cyan2",command = txt_read)
refre_btn.pack()
refre_btn.config( height = 2, width = 20 ,font=("Helvetica 16 bold italic", 12),state=ACTIVE)
refre_btn.place( x=width/20,y=hight/10)


datenw=datetime.datetime.today().strftime('%Y-%m-%d')
timenw=datetime.datetime.today().strftime('%H:%M:%S')
wrt_master_log([str(datenw),str(timenw),"starting unit"])




 

try:
   thread.start_new_thread( inf_loop, ("Thread-1", 0.00001, ) )
   thread.start_new_thread( one_hz, ("Thread-1", 0.001, ) )
   thread.start_new_thread( clock_hz, ("Thread-1", 0.001, ) )
   
except:
   print "Error: unable to start thread1"

#****************************** alarm on ********************************************
def alm_on(ch1):
    global alm_led
    GPIO.output(alm_led,1)
    print "alm_on"

#****************************** alarm off ********************************************
def alm_off(ch1):
    global alm_led
    GPIO.output(alm_led,0)
    print "alm_off"
    
def power_off(ch1):
    print "power of pending"
    global counter
    global pwr_pin
    te_counter=counter
    time.sleep(1)

    if(GPIO.input(pwr_pin)==True ):
        pass
        #tkMessageBox.showinfo("Ready","Ready to use now")
        
    while(GPIO.input(pwr_pin)==False and counter-te_counter<10):
        print counter
        
    if(counter-te_counter>=10):
        print "power off"
        GPIO.output(myrelay,0)
        '''try:
            #wrt_log([datetime.datetime.now().date(),datetime.datetime.now().time(),"System is shutting down","","","",""])
            #os.system('shutdown now -h')
        except:
            print "er"'''
    else:
        
        print "power not off"

GPIO.add_event_detect(intke_start_pin,GPIO.RISING,callback=intk_start_event,bouncetime=1000)
GPIO.add_event_detect(intke_stop_pin,GPIO.RISING,callback=intk_stop_event,bouncetime=1000)

GPIO.add_event_detect(outtk_start_pin,GPIO.RISING,callback=outtk_start_event,bouncetime=1000)
GPIO.add_event_detect(outtk_stop_pin,GPIO.RISING,callback=outtk_stop_event,bouncetime=1000)

#GPIO.add_event_detect(emg_up_sns_pin,GPIO.RISING,callback=alm_on,bouncetime=500)
#GPIO.add_event_detect(alm_stp_pin,GPIO.RISING,callback=alm_off,bouncetime=500)


GPIO.add_event_detect(pwr_pin,GPIO.BOTH,callback=power_off,bouncetime=500)

 
intk_mode_flag=0
mode_intake_txt="Manual"
mode_intake_txt_2="Auto"
mode_btn_in.config(text=mode_intake_txt)
mode_btn_lbl.config( text=mode_intake_txt_2)
intk_ctrl_flag=0
intk_ctrl_txt="Remote"
intk_ctrl_txt_2="Local"
mode_btn_in.config(bg="purple4")
int_act_btn.config(state=DISABLED)
mode_btn_in.config(state=DISABLED)
int_act_flag=0
intk_ctrl_lbl.config( text=intk_ctrl_txt_2)   
intk_ctrl_btn.config(text=intk_ctrl_txt)



outtake_mode_flag=0
outk_ctrl_flag=0
outk_ctrl_txt="Remote"
outk_ctrl_txt_2="Local"
mode_btn_out.config(bg="purple4")
mode_btn_out.config(state=DISABLED)
out_act_btn.config(state=DISABLED)
        
outk_ctrl_btn.config(text=outk_ctrl_txt)
outk_ctrl_lbl.config(text=outk_ctrl_txt_2)

datenw=datetime.datetime.today().strftime('%Y-%m-%d')
timenw=datetime.datetime.today().strftime('%H:%M:%S')
wrt_master_log([str(datenw),str(timenw),"waking up unit  "])

  
        


win.mainloop()

