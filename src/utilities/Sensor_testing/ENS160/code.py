import time
import os
import busio
import board
import digitalio
import microcontroller
import math

import adafruit_ahtx0
import adafruit_ens160

pins = [17,16]

I2C_SCL = getattr(board, "GP" + str(pins[0]))
I2C_SDA = getattr(board, "GP" + str(pins[1]))
i2c = busio.I2C(I2C_SCL, I2C_SDA)
envSensor0 = adafruit_ahtx0.AHTx0(i2c)
envSensor1 = adafruit_ens160.ENS160(i2c)

t_envSensor = float(envSensor0.temperature)
rh_envSensor = float(envSensor0.relative_humidity)
envSensor1.temperature_compensation = t_envSensor
envSensor1.humidity_compensation = rh_envSensor

while True:
    print(f"Temp: {round(t_envSensor,1)}")
    print(f"RH: {round(rh_envSensor, 1)}")
    print(f"AQI: {envSensor1.AQI}")
    print(f"TVOC: {envSensor1.TVOC}")
    print(f"eCO2: {envSensor1.eCO2}\n")
    print(f"mode: {envSensor1.mode}\n")
    print(f"firmware_version: {envSensor1.firmware_version}")

    time.sleep(2)

    print(f"read_all_sensors(): {envSensor1.read_all_sensors()}")

    time.sleep(2)

