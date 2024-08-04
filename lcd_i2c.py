from RPLCD.i2c import CharLCD
print('writing!')
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8,
              backlight_enabled=True)
lcd.clear()


import os
import glob
import time
 
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')
 
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'
 
def read_temp_raw():
    f = open(device_file, 'r')
    lines = f.readlines()
    f.close()
    return lines
 
def read_temp():
    lines = read_temp_raw()
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        temp_f = temp_c * 9.0 / 5.0 + 32.0
        return temp_c, temp_f
	
while True:

    temp_c, temp_f = read_temp()	
    temp_c, temp_f = round(temp_c,1), round(temp_f,1)
    if temp_c is not None:
        lcd.cursor_pos = (0, 0)
        lcd.write_string(f'Temp C: {temp_c}C')
        lcd.cursor_pos = (1, 0)
        lcd.write_string(f'Temp F: {temp_f}F')
    else:
        lcd.cursor_pos = (0, 0)
        lcd.write_string('Temp sensor error')
        lcd.cursor_pos = (1, 0)
        lcd.write_string('Check connection')

    time.sleep(1)




