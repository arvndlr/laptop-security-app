import asyncio
import time
import requests
import json
import RPi.GPIO as GPIO
import serial
from bleak import BleakScanner

# --- CONFIGURATION ---
FLASK_DATA_API_URL = "http://192.168.100.36:5000/api/sensor_data"
FLASK_STATUS_API_URL = "http://192.168.100.36:5000/api/laptop_status"

IBEACON_TO_LAPTOP_MAP = {
    "D7:6F:22:D8:59:C9": "00032072025",
    "C0:2F:AE:A5:B9:45": "00001082025",
}

# --- ULTRASONIC SENSOR MAPPING ---
# This maps each laptop's serial number to a specific ultrasonic sensor.
# The index corresponds to the position in the Arduino's output (0 for sensor 1, 1 for sensor 2, etc.)
ULTRASONIC_SENSOR_TO_LAPTOP_MAP = {
    "00032072025": 0,  # Laptop 1 is associated with sensor 1 (index 0)
    "00001082025": 1,  # Laptop 2 is associated with sensor 2 (index 1)
    # Add more laptops and their sensor indices here
}

# --- ALARM THRESHOLD ---
# If a laptop's associated ultrasonic sensor reads a distance below this value,
# it will also trigger the stolen alarm.
MIN_DISTANCE_CM = 5.0 # Set this to a value that works for your setup

# Arduino Serial Port Configuration
SERIAL_PORT = '/dev/ttyUSB0'
SERIAL_BAUDRATE = 9600

# --- BUZZER CONFIGURATION ---
BUZZER_PIN = 18 
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

alarm_task = None
stolen_laptops_status = {serial: False for serial in IBEACON_TO_LAPTOP_MAP.values()}

async def beeping_alarm():
    """An async task that makes the buzzer beep continuously."""
    try:
        while True:
            GPIO.output(BUZZER_PIN, GPIO.HIGH)
            await asyncio.sleep(0.5)
            GPIO.output(BUZZER_PIN, GPIO.LOW)
            await asyncio.sleep(0.5)
    except asyncio.CancelledError:
        GPIO.output(BUZZER_PIN, GPIO.LOW)
        print("Beeping alarm stopped.")

def update_stolen_status(laptop_serial, is_stolen):
    """Sends an API request to update a laptop's stolen status."""
    global stolen_laptops_status
    
    if stolen_laptops_status.get(laptop_serial) != is_stolen:
        url = f"{FLASK_STATUS_API_URL}/{laptop_serial}"
        payload = {"is_stolen": is_stolen}
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            stolen_laptops_status[laptop_serial] = is_stolen
            print(f"Laptop {laptop_serial} status updated to is_stolen={is_stolen} in the database.")
        except requests.exceptions.RequestException as e:
            print(f"Error updating laptop status for {laptop_serial}: {e}")

def get_ultrasonic_distances(ser):
    """Reads all available lines from the Arduino and returns the last valid one."""
    last_valid_distances = [0.0, 0.0, 0.0, 0.0]
    try:
        while ser.in_waiting > 0:
            line = ser.readline().decode('utf-8').strip()
            if line:
                try:
                    distances = [float(d) for d in line.split(',')]
                    if len(distances) == 4:
                        print(f"Read distances from Arduino: {distances} cm")
                        last_valid_distances = distances
                except ValueError:
                    pass
        return last_valid_distances
    except Exception as e:
        print(f"Error reading from Arduino: {e}")
        return last_valid_distances

async def scan_and_send_data():
    global alarm_task
    print("Starting iBeacon scanner...")
    
    found_devices = {}
    ser = None
    
    def detection_callback(device, advertisement_data):
        if device.address in IBEACON_TO_LAPTOP_MAP:
            rssi = advertisement_data.rssi
            found_devices[device.address] = {
                "rssi": rssi
            }
            print(f"Found target iBeacon ({device.address}) with RSSI: {rssi}")

    scanner = BleakScanner(detection_callback)
    await scanner.start()

    try:
        try:
            ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=1)
            ser.flushInput()
        except serial.SerialException as e:
            print(f"Error: Could not open serial port '{SERIAL_PORT}'. Is the Arduino connected? Exiting.")
            return

        while True:
            await asyncio.sleep(2)
            
            ultrasonic_distances = get_ultrasonic_distances(ser)
            
            laptops_in_danger = set()
            found_mac_addresses = found_devices.keys()
            
            # Check for missing iBeacons
            all_target_macs = IBEACON_TO_LAPTOP_MAP.keys()
            for mac in all_target_macs:
                if mac not in found_mac_addresses:
                    laptop_serial = IBEACON_TO_LAPTOP_MAP.get(mac)
                    if laptop_serial:
                        laptops_in_danger.add(laptop_serial)

            # Check for ultrasonic distance below threshold
            for laptop_serial, sensor_index in ULTRASONIC_SENSOR_TO_LAPTOP_MAP.items():
                if 0 <= sensor_index < len(ultrasonic_distances):
                    distance = ultrasonic_distances[sensor_index]
                    if 0 < distance < MIN_DISTANCE_CM:
                        print(f"Laptop {laptop_serial} is too close! Distance: {distance} cm")
                        laptops_in_danger.add(laptop_serial)

            if laptops_in_danger:
                if not alarm_task:
                    alarm_task = asyncio.create_task(beeping_alarm())
                    print(f"ALARM ACTIVATED! The following laptops are in danger: {', '.join(laptops_in_danger)}")
                
                for serial in laptops_in_danger:
                    update_stolen_status(serial, True)
            else:
                if alarm_task:
                    alarm_task.cancel()
                    alarm_task = None
                    print("All laptops are safe. Alarm deactivated.")
            
            for mac_address, beacon_data in found_devices.items():
                laptop_serial = IBEACON_TO_LAPTOP_MAP.get(mac_address)
                
                if laptop_serial:
                    if laptop_serial not in laptops_in_danger:
                        update_stolen_status(laptop_serial, False)

                    payload = {
                        "serial_number": laptop_serial,
                        "ibeacon_rssi": beacon_data['rssi'],
                        "ultrasonic_distances": ultrasonic_distances
                    }
                    
                    try:
                        response = requests.post(FLASK_DATA_API_URL, json=payload, timeout=5)
                        response.raise_for_status()
                        print(f"Data for {laptop_serial} sent successfully.")
                    except requests.exceptions.RequestException as e:
                        print(f"Error sending data for {laptop_serial}: {e}")
            
            found_devices.clear()
            
    except asyncio.CancelledError:
        print("Scanner stopped.")
    finally:
        if alarm_task:
            alarm_task.cancel()
            try:
                await alarm_task
            except asyncio.CancelledError:
                pass
        await scanner.stop()
        if ser:
            ser.close()
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(scan_and_send_data())
    except KeyboardInterrupt:
        print("Script terminated by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        GPIO.cleanup()