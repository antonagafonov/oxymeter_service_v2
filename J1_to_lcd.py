import datetime
import os
import glob
import time
import threading
from bluepy import btle
import paho.mqtt.client as mqtt
from RPLCD.i2c import CharLCD

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
        return round(temp_c, 1)
    return None

class LCD:
    """
    Manages the LCD display, showing temperature and BPM data.
    """
    def __init__(self):
        """
        Initializes the LCD object.
        """
        self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2,charmap='A00', dotsize=8, backlight_enabled=True)
        # self.lcd = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=20, rows=4,charmap='A00', dotsize=8, backlight_enabled=True)
        self.lcd.clear()
        self.cached_temp = 'N/A'
        self.bpm = 'XX'
        self.connected = True
        self.lock = threading.Lock()

        # Start a thread to update the display periodically
        self.update_thread = threading.Thread(target=self.update_display)
        self.update_thread.daemon = True
        self.update_thread.start()

    def update_display(self):
        while True:
            # Read temperature
            self.cached_temp = read_temp()
            if self.cached_temp is None:
                self.cached_temp = 'n/a'
            if not self.connected:
                self.bpm = 'XX'

            # Write to LCD
            self.write_lcd()

            time.sleep(1)  # Update display every second

    def write_lcd(self):
        """
        Writes the heart rate (HR) and temperature value to an LCD display.

        Args:
            bpm (str): Heart rate value (bpm) to be displayed on the LCD. Default is 'XX'.

        Returns:
            None
        """
        try:
            with self.lock:
                current_time = datetime.datetime.now().strftime('%H:%M:%S')
                bpm = self.bpm
                line1 = f"    {current_time}"
                
                if float(self.cached_temp)<10.0:
                    if float(bpm)<10.0:
                        line2 = f" {self.cached_temp} C HR: {bpm} bpm"
                    elif float(bpm)>99.0:
                        line2 = f" {self.cached_temp} C HR:{bpm}bpm"
                    else:
                        line2 = f" {self.cached_temp} C HR:{bpm} bpm"
                else:
                    if float(bpm)<10.0:
                        line2 = f"{self.cached_temp} C HR: {bpm} bpm"
                    elif float(bpm)>99.0:
                        line2 = f"{self.cached_temp} C HR:{bpm}bpm"
                    else:
                        line2 = f"{self.cached_temp} C HR:{bpm} bpm"

                # Write each line separately without clearing the screen
                self.lcd.cursor_pos = (0, 0)
                self.lcd.write_string(line1)
                self.lcd.cursor_pos = (1, 0)
                self.lcd.write_string(line2)
        except Exception as e:
            print(f"Error writing to LCD: {e}")

    def update_bpm(self, bpm):
        """
        Updates the BPM value and refreshes the display.

        Args:
            bpm (str): The BPM value to be updated.

        Returns:
            None
        """
        
        self.bpm = bpm
        self.write_lcd()

class Delegate(btle.DefaultDelegate):
    """
    Handles notifications received from the peripheral device.
    """
    def __init__(self, lcd_display):
        """
        Initializes the Delegate object.

        Args:
            lcd_display (LCD): The LCD display object.
        """
        btle.DefaultDelegate.__init__(self)
        self.lcd_display = lcd_display

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
<<<<<<< HEAD
        self.lcd_display.update_bpm(bpm)
=======
            # hrv = databytes[14]
            # spo2 = 0
            # pi = 0
        self.write_lcd(bpm=bpm)
        print("bpm:", bpm)

    def write_lcd(self, bpm='XX'):
        """
        Writes the heart rate (HR) value to an LCD display.

        Args:
            bpm (str): Heart rate value (bpm) to be displayed on the LCD. Default is 'XX'.

        Returns:
            None
        """
>>>>>>> 560dd19b8e4e0b0e65c89547026f10a6706ce167

class OxymeterService:
    """
    Manages the oxymeter service including connecting to MQTT broker and handling notifications.
    """
    def __init__(self):
        """
        Initializes the OxymeterService object.
        """
        self.client = mqtt.Client(client_id="", protocol=mqtt.MQTTv5)
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        self.DEVICEID = "J1"
        self.LOC = "7736"

        try:
            self.client.connect("mqtt.eclipseprojects.io", 1883, 60)
        except Exception as e:
            print(e)

        self.lcd_display = LCD()
        self.address = 'C8:32:B4:ED:79:AD'
        self.p = None
        self.connect_ble()

    def connect_ble(self):
        try:
            self.p = btle.Peripheral(self.address, btle.ADDR_TYPE_RANDOM)
            self.p.setDelegate(Delegate(self.lcd_display))
        except btle.BTLEException as e:
            print(f"BLE connection error: {e}")
            self.p = None

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

    def on_disconnect(self, client, userdata, reason_code, properties):
        """
        Callback function executed when the MQTT client disconnects from the broker.

        Args:
            client: MQTT client instance.
            userdata: The private user data as set in Client() or user_data_set().
            reason_code: The disconnection result.
            properties: MQTT properties returned by the broker.

        Returns:
            None
        """
        print("Disconnected with reason code " + str(reason_code))

    def enable_notifications(self, service_uuid, characteristic_uuid):
        """
        Enables notifications for a specific characteristic of the peripheral device.

        Args:
            service_uuid (str): UUID of the service containing the characteristic.
            characteristic_uuid (str): UUID of the characteristic for which notifications are to be enabled.

        Returns:
            None
        """
        if self.p is None:
            print("Peripheral not connected, cannot enable notifications.")
            return
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
        if self.p is None:
            print("Peripheral not connected, cannot run service.")
        
        self.client.loop_start()
        try:
            while True:
                if self.p.waitForNotifications(60.0):
                    # Reset the connected flag if a notification is received
                    self.p.delegate.lcd_display.connected = True
                else:
                    # If no notification is received in the timeout period, set the connected flag to False
                    self.p.delegate.lcd_display.connected = False
        except Exception as e:
            print(e)
        finally:
            self.client.disconnect()
            if self.p is not None:
                self.p.disconnect()

if __name__ == "__main__":
    oxymeter_service = OxymeterService()
    service_uuid = '0000180a-0000-1000-8000-00805f9b34fb'
    characteristic_uuid = '00002a29-0000-1000-8000-00805f9b34fb'
    oxymeter_service.run(service_uuid, characteristic_uuid)
