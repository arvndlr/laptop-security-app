import asyncio
import time
from bleak import BleakScanner

async def scan_for_ibeacons(scan_duration=10):
    """
    Scans for iBeacons using the bleak library for a specified duration,
    returning the MAC address and RSSI.
    """
    found_beacons = {}
    
    def detection_callback(device, advertisement_data):
        # iBeacon data is typically found in the manufacturer_data field
        # Apple's manufacturer ID is 0x004c
        apple_id = 0x004c
        if apple_id in advertisement_data.manufacturer_data:
            data = advertisement_data.manufacturer_data[apple_id]
            # iBeacon data starts with bytes [0x02, 0x15]
            if data[0:2] == bytes([0x02, 0x15]):
                # Get the MAC address from the device object
                mac_address = device.address
                
                # Get other beacon data
                uuid = data[2:18].hex()
                major = int.from_bytes(data[18:20], byteorder='big')
                minor = int.from_bytes(data[20:22], byteorder='big')
                rssi = advertisement_data.rssi

                # Use the MAC address as the unique key
                if mac_address not in found_beacons:
                    found_beacons[mac_address] = {
                        'mac_address': mac_address,
                        'uuid': uuid,
                        'major': major,
                        'minor': minor,
                        'rssi': rssi
                    }

    scanner = BleakScanner(detection_callback)
    
    print("Scanning for iBeacons...")
    
    start_time = time.time()
    
    await scanner.start()
    
    await asyncio.sleep(scan_duration)
    
    await scanner.stop()
    
    return list(found_beacons.values())

if __name__ == '__main__':
    async def main():
        beacons = await scan_for_ibeacons()
        if beacons:
            print("Found iBeacons:")
            for beacon in beacons:
                print(f"MAC: {beacon['mac_address']}, UUID: {beacon['uuid']}, Major: {beacon['major']}, Minor: {beacon['minor']}, RSSI: {beacon['rssi']}")
        else:
            print("No iBeacons found.")

    asyncio.run(main())