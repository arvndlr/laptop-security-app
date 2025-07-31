import RPi.GPIO as GPIO
import time

BUZZER_PIN = 18  # Make sure this is your correct pin
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

print("Testing buzzer. It should beep twice.")
try:
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
    time.sleep(1)
    GPIO.output(BUZZER_PIN, GPIO.HIGH)
    time.sleep(1)
    GPIO.output(BUZZER_PIN, GPIO.LOW)
finally:
    GPIO.cleanup()