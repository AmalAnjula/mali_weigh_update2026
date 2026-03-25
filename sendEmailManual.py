import  emailsend  as em
import time
import queue

latest_file = em.get_latest_csv("/home/palmoil/stuff/logs")
print("Latest file:", latest_file)
 
body=em.build_body(latest_file)            
            
   
time.sleep(5)
em.send_email(
    "PLANT_01_PALM_OLEIN_SPRAYER",
    body,
    "amalanjula@gmail.com",
    latest_file
    )

