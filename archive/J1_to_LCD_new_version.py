import datetime
import os
import glob
import time
import threading
from RPLCD.i2c import CharLCD

# Load the necessary kernel modules
os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

# Set up the path to the temperature sensor device file
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
        return round(temp_c, 1)
    return None

class LCD:
    """
    Manages the LCD display, showing temperature data.
    """
    def __init__(self):
        """
        Initializes the LCD object.
        """
        self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2, dotsize=8, backlight_enabled=True)
        self.lcd.clear()
        self.cached_temp = 'N/A'

        # Start a thread to update the display periodically
        self.update_thread = threading.Thread(target=self.update_display)
        self.update_thread.daemon = True
        self.update_thread.start()

    def update_display(self):
        while True:
            self.cached_temp = read_temp()
            if self.cached_temp is None:
                self.cached_temp = 'N/A'
            self.write_lcd()
            time.sleep(1)  # Update display every 5 seconds

    def write_lcd(self):
        """
        Writes the current time and temperature value to the LCD display.

        Returns:
            None
        """
        current_time = datetime.datetime.now().strftime('%H:%M:%S')

        line1 = f"    {current_time}"
        line2 = f"Temp: {self.cached_temp}C"

        # Write each line separately without clearing the screen
        self.lcd.cursor_pos = (0, 0)
        self.lcd.write_string(line1)
        self.lcd.cursor_pos = (1, 0)
        self.lcd.write_string(line2)

if __name__ == "__main__":
    lcd_display = LCD()
    # The LCD display will now continuously update with the current temperature
