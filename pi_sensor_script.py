import asyncio
import time
import requests
import json
import RPi.GPIO as GPIO
from bleak import BleakScanner

# --- CONFIGURATION ---
FLASK_DATA_API_URL = "http://192.168.100.36:5000/api/sensor_data"
# New endpoint for updating a laptop's stolen status
FLASK_STATUS_API_URL = "http://192.168.100.36:5000/api/laptop_status"

IBEACON_TO_LAPTOP_MAP = {
    "D7:6F:22:D8:59:C9": "00032072025",
    "C0:2F:AE:A5:B9:45": "00001082025",
}

ULTRASONIC_DISTANCE_CM_PLACEHOLDER = 0.0

# --- BUZZER CONFIGURATION ---
BUZZER_PIN = 18 
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

# Global task variable for the alarm
alarm_task = None
# New dictionary to track stolen status to avoid repeated API calls
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
    
    # Only send the API call if the status has changed
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

# --- SCANNING AND DATA SENDING LOGIC ---
async def scan_and_send_data():
    global alarm_task
    print("Starting iBeacon scanner...")
    
    found_devices = {}

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
        while True:
            await asyncio.sleep(5)
            
            found_mac_addresses = found_devices.keys()
            all_target_macs = IBEACON_TO_LAPTOP_MAP.keys()
            
            # Check for missing beacons
            missing_beacons = [mac for mac in all_target_macs if mac not in found_mac_addresses]
            
            if missing_beacons:
                if not alarm_task:
                    alarm_task = asyncio.create_task(beeping_alarm())
                    print(f"ALARM ACTIVATED! The following beacons are missing: {', '.join(missing_beacons)}")
                
                # Update status for all missing beacons
                for mac in missing_beacons:
                    laptop_serial = IBEACON_TO_LAPTOP_MAP.get(mac)
                    if laptop_serial:
                        update_stolen_status(laptop_serial, True)
            else:
                # If all beacons were found, stop the alarm
                if alarm_task:
                    alarm_task.cancel()
                    alarm_task = None
                    print("All beacons found. Alarm deactivated.")
            
            # Send data for all beacons that were found and reset their stolen status if it was set
            for mac_address, beacon_data in found_devices.items():
                laptop_serial = IBEACON_TO_LAPTOP_MAP.get(mac_address)
                
                if laptop_serial:
                    # Reset stolen status if the beacon is now found
                    update_stolen_status(laptop_serial, False)

                    payload = {
                        "serial_number": laptop_serial,
                        "ibeacon_rssi": beacon_data['rssi'],
                        "ultrasonic_distance_cm": ULTRASONIC_DISTANCE_CM_PLACEHOLDER
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
        GPIO.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(scan_and_send_data())
    except KeyboardInterrupt:
        print("Script terminated by user.")
    except Exception as e:
        print(f"An error occurred: {e}")
        GPIO.cleanup()