import datetime
import time

while True:
  # delay of 1 second
  time.sleep(1)
  current_time = datetime.datetime.now().strftime('%H:%M:%S')
  print(current_time)
