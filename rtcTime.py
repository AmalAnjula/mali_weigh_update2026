import board
import busio
import adafruit_ds3231
from datetime import datetime

# Connect
i2c = busio.I2C(board.SCL, board.SDA)
rtc = adafruit_ds3231.DS3231(i2c)

# ── Write time (set once) ──────────────────────────
now = datetime(2026, 3, 13, 14, 30, 0)   # year, month, day, hour, min, sec
rtc.datetime = now.timetuple()
print("RTC time set to:", now)

# ── Read time ──────────────────────────────────────
t = rtc.datetime
print(f"RTC time: {t.tm_year}-{t.tm_mon:02d}-{t.tm_mday:02d} "
      f"{t.tm_hour:02d}:{t.tm_min:02d}:{t.tm_sec:02d}")



'''
sudo hwclock -s        # set system time FROM RTC
sudo hwclock -w        # write system time TO RTC
sudo i2cdetect -y 1
pip install adafruit-circuitpython-ds3231 adafruit-blinka --break-system-packages
# You should see 0x68 in the grid
'''