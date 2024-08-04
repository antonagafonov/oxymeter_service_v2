import datetime
import os
import glob
import time
import threading
from bluepy import btle
import paho.mqtt.client as mqtt
import board
from digitalio import DigitalInOut
from adafruit_character_lcd.character_lcd import Character_LCD_Mono
from RPLCD.i2c import CharLCD

os.system('modprobe w1-gpio')
os.system('modprobe w1-therm')

base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

def read_temp_raw():
    with open(device_file, 'r') as f:
        lines = f.readlines()
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
        return round(temp_c, 1)
    return None

class Deligate(btle.DefaultDelegate):
    """
    Handles notifications received from the peripheral device.
    """
    def __init__(self, client, deviceid, location):
        """
        Initializes the Deligate object.

        Args:
            client (mqtt.Client): MQTT client object.
            deviceid (str): ID of the device.
            location (str): Location of the device.
        """
        btle.DefaultDelegate.__init__(self)
        self.client = client
        self.DEVICEID = deviceid
        self.LOC = location
        self.cached_temp = 'N/A'

        # Initialize the LCD once
        lcd_columns = 16
        lcd_rows = 2

        lcd_rs = DigitalInOut(board.D26)
        lcd_en = DigitalInOut(board.D19)
        lcd_d4 = DigitalInOut(board.D13)
        lcd_d5 = DigitalInOut(board.D6)
        lcd_d6 = DigitalInOut(board.D5)
        lcd_d7 = DigitalInOut(board.D11)

        self.lcd = Character_LCD_Mono(
            lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7, lcd_columns, lcd_rows
        )

        # Start a thread to update the temperature periodically
        self.temp_update_thread = threading.Thread(target=self.update_temperature)
        self.temp_update_thread.daemon = True
        self.temp_update_thread.start()

    def update_temperature(self):
        while True:
            self.cached_temp = read_temp()
            if self.cached_temp is None:
                self.cached_temp = 'N/A'
            time.sleep(5)  # Update temperature every 5 seconds

    def handleNotification(self, cHandle, data):
        """
        Processes notifications received from the peripheral device.

        Args:
            cHandle (int): Notification handle.
            data (bytearray): Data received in the notification.

        Returns:
            None
        """
        databytes = bytearray(data)
        if databytes[2] == 0x03:
            bpm = databytes[5]
        else:
            bpm = databytes[7]
        self.write_lcd(bpm=bpm)
        print("bpm:", bpm)

    def write_lcd(self, bpm='XX'):
        """
        Writes the heart rate (HR) and temperature value to an LCD display.

        Args:
            bpm (str): Heart rate value (bpm) to be displayed on the LCD. Default is 'XX'.

        Returns:
            None
        """
        current_time = datetime.datetime.now().strftime('%H:%M:%S')

        if bpm == 0:
            line1 = f"    {current_time}"
            line2 = f"{self.cached_temp}C HR: None  "
        else:
            line1 = f"    {current_time}"
            line2 = f"{self.cached_temp}C HR: {bpm} bpm"

        # Write each line separately without clearing the screen
        self.lcd.cursor_position(0, 0)
        self.lcd.message = line1
        self.lcd.cursor_position(0, 1)
        self.lcd.message = line2

class OxymeterService:
    """
    Manages the oxymeter service including connecting to MQTT broker and handling notifications.
    """
    def __init__(self):
        """
        Initializes the OxymeterService object.
        """
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect

        self.DEVICEID = "J1"
        self.LOC = "7736"

        try:
            self.client.connect("mqtt.eclipseprojects.io", 1883, 60)
        except Exception as e:
            print(e)

        self.address = 'C8:32:B4:ED:79:AD'
        self.p = btle.Peripheral(self.address, btle.ADDR_TYPE_RANDOM)
        self.p.setDelegate(Deligate(self.client, self.DEVICEID, self.LOC))

    def on_connect(self, client, userdata, flags, reason_code, properties):
        """
        Callback function executed when the MQTT client connects to the broker.

        Args:
            client: MQTT client instance.
            userdata: The private user data as set in Client() or user_data_set().
            flags: Response flags sent by the broker.
            reason_code: The connection result.
            properties: MQTT properties returned by the broker.

        Returns:
            None
        """
        print("Connected with result code " + str(reason_code))

    def enable_notifications(self, service_uuid, characteristic_uuid):
        """
        Enables notifications for a specific characteristic of the peripheral device.

        Args:
            service_uuid (str): UUID of the service containing the characteristic.
            characteristic_uuid (str): UUID of the characteristic for which notifications are to be enabled.

        Returns:
            None
        """
        try:
            service = self.p.getServiceByUUID(service_uuid)
            characteristic = service.getCharacteristics(characteristic_uuid)[0]
            cccd = characteristic.getDescriptors(forUUID=0x2902)[0]
            cccd.write(b"\x01\x00", True)
        except Exception as e:
            print("Error enabling notifications:", e)

    def run(self, service_uuid, characteristic_uuid):
        """
        Starts the oxymeter service.

        Args:
            service_uuid (str): UUID of the service containing the characteristic.
            characteristic_uuid (str): UUID of the characteristic for which notifications are to be enabled.

        Returns:
            None
        """
        self.enable_notifications(service_uuid, characteristic_uuid)
        self.client.loop_start()
        try:
            while True:
                self.p.waitForNotifications(120.0)
        except Exception as e:
            print(e)
        finally:
            self.client.disconnect()
            self.p.disconnect()

if __name__ == "__main__":
    oxymeter_service = OxymeterService()
    service_uuid = '0000180a-0000-1000-8000-00805f9b34fb'
    characteristic_uuid = '00002a29-0000-1000-8000-00805f9b34fb'
    oxymeter_service.run(service_uuid, characteristic_uuid)
