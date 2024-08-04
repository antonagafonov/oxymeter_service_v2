from RPLCD.i2c import CharLCD
import os
import glob
import time

# Initialize and clear the LCD
print('Initializing LCD...')
lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8, backlight_enabled=True)
lcd.clear()

# Load the GPIO modules
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folders = glob.glob(base_dir + '28*')

if device_folders:
    device_folder = device_folders[0]
    device_file = device_folder + '/w1_slave'
else:
    device_folder = None
    device_file = None

def read_temp_raw():
    if device_file is None:
        return None
    with open(device_file, 'r') as f:
        lines = f.readlines()
    return lines

def read_temp():
    if device_file is None:
        return None
    lines = read_temp_raw()
    if lines is None:
        return None
    while lines[0].strip()[-3:] != 'YES':
        time.sleep(0.2)
        lines = read_temp_raw()
    equals_pos = lines[1].find('t=')
    if equals_pos != -1:
        temp_string = lines[1][equals_pos+2:]
        temp_c = float(temp_string) / 1000.0
        return temp_c
    return None

while True:
    temp_c = read_temp()
    if temp_c is not None:
        lcd.clear()
        lcd.cursor_position(0, 0)
        lcd.write_string(f'Temp C: {temp_c}C')
        lcd.cursor_position(0, 1)
        lcd.write_string(f'The day is Gray')
    else:
        lcd.clear()
        lcd.cursor_position(0, 0)
        lcd.write_string('Temp sensor error')
        lcd.cursor_position(0, 1)
        lcd.write_string(f'The day is Gray')
    time.sleep(1)
