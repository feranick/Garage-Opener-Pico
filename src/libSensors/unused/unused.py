# **********************************************
# * libSensors - unused - Rasperry Pico W
# * v2025.11.13.3
# * By: Nicola Ferralis <feranick@hotmail.com>
# **********************************************

libSensors_version = "2025.11.13.3"

import time
import busio
import board
import digitalio
import microcontroller
import math

############################
# Sensors
############################
class UnusedSensorDevices:
    def __init__(self):
        self.version = libSensors_version
        pass

    def initSensor(self, envSensorName, pins):
        try:
            elif envSensorName == "BMP280":
                envSensor = self.initBMP280(pins)
            elif envSensorName == "BMP3XX":
                envSensor = self.initBMP3XX(pins)
            elif envSensorName == "BMP5XX":
                envSensor = self.initBMP5XX(pins)
            else:
                envSensor = None
            print(f"Temperature sensor ({envSensorName}) found and initialized.")
            return envSensor
        except Exception as e:
            print(f"Failed to initialize enironmental sensor ({envSensorName}): {e}")
            
    ##############################################
    # Sensors: Initialization and Data collection
    ##############################################
        
    ##############################################
    # BMP280
    ##############################################
    def initBMP280(self, pins):
        import adafruit_bmp280
        CLK = getattr(board, "GP" + str(pins[0]))
        MOSI = getattr(board, "GP" + str(pins[1]))
        MISO = getattr(board, "GP" + str(pins[2]))
        OUT = getattr(board, "GP" + str(pins[3]))
        spi = busio.SPI(CLK, MISO=MISO, MOSI=MOSI)
        cs = digitalio.DigitalInOut(OUT)
        envSensor = adafruit_bmp280.Adafruit_BMP280_SPI(spi, cs)
        return envSensor

    def getEnvDataBMP280(self, envSensor, correctTemp):
        t_envSensor = float(envSensor.temperature)
        rh_envSensor = float(envSensor.humidity)
        p_envSensor = int(float(envSensor.pressure))
        if correctTemp.lower() == 'true':
            t_envSensor = self.correctTempBMP280(t_envSensor)
        return {'temperature': f"{round(t_envSensor,1)}",
                'RH': '--',
                'pressure': f"{p_envSensor}",
                'gas': '--',
                'IAQ': '--',
                'HI': '--',
                'type': 'sensor',
                'libSensors_version': self.version}
                
    # Temperature correction for BMP280
    def correctTempBMP280(self, mt):
        return mt
                
    ##############################################
    # BMP3XX
    ##############################################
    def initBMP3XX(self, pins):
        import adafruit_bmp3xx
        CLK = getattr(board, "GP" + str(pins[0]))
        MOSI = getattr(board, "GP" + str(pins[1]))
        MISO = getattr(board, "GP" + str(pins[2]))
        OUT = getattr(board, "GP" + str(pins[3]))
        spi = busio.SPI(CLK, MISO=MISO, MOSI=MOSI)
        cs = digitalio.DigitalInOut(OUT)
        envSensor = adafruit_bmp3xx.Adafruit_BMP3XX_SPI(spi, cs)
        return envSensor

    def getEnvDataBMP3XX(self, envSensor, correctTemp):
        t_envSensor = float(envSensor.temperature)
        rh_envSensor = float(envSensor.humidity)
        p_envSensor = int(float(envSensor.pressure))
        if correctTemp.lower() == 'true':
            t_envSensor = self.correctTempBMP3XX(t_envSensor)
        return {'temperature': f"{round(t_envSensor,1)}",
                'RH': '--',
                'pressure': f"{p_envSensor}",
                'gas': '--',
                'IAQ': '--',
                'HI': '--',
                'type': 'sensor',
                'libSensors_version': self.version}
                
    # Temperature correction for BMP3XX
    def correctTempBMP3XX(self, mt):
        return mt
    
    ##############################################
    # BMP5XX
    ##############################################
    def initBMP5XX(self, pins):
        import adafruit_bmp5xx
        CLK = getattr(board, "GP" + str(pins[0]))
        MOSI = getattr(board, "GP" + str(pins[1]))
        MISO = getattr(board, "GP" + str(pins[2]))
        OUT = getattr(board, "GP" + str(pins[3]))
        spi = busio.SPI(CLK, MISO=MISO, MOSI=MOSI)
        cs = digitalio.DigitalInOut(OUT)
        envSensor = adafruit_bmp5xx.Adafruit_BMP5XX_SPI(spi, cs)
        return envSensor

    def getEnvDataBMP5XX(self, envSensor, correctTemp):
        t_envSensor = float(envSensor.temperature)
        rh_envSensor = float(envSensor.humidity)
        p_envSensor = int(float(envSensor.pressure))
        if correctTemp.lower() == 'true':
            t_envSensor = self.correctTempBMP5XX(t_envSensor)
        return {'temperature': f"{round(t_envSensor,1)}",
                'RH': '--',
                'pressure': f"{p_envSensor}",
                'gas': '--',
                'IAQ': '--',
                'HI': '--',
                'type': 'sensor',
                'libSensors_version': self.version}
                
    # Temperature correction for BMP5XX
    def correctTempBMP5XX(self, mt):
        return mt
                
    def getSensorData(self, envSensor, envSensorName, correctTemp):
        if envSensorName == "BMP280":
            sensorData = self.getEnvDataBMP280(envSensor, correctTemp)
        elif envSensorName == "BMP3XX":
            sensorData = self.getEnvDataBMP3XX(envSensor, correctTemp)
        elif envSensorName == "BMP5XX":
            sensorData = self.getEnvDataBMP5XX(envSensor, correctTemp)
        return sensorData

