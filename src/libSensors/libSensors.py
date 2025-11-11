# **********************************************
# * libSensors - Rasperry Pico W
# * v2025.11.10.2
# * By: Nicola Ferralis <feranick@hotmail.com>
# **********************************************

libSensors_version = "2025.11.10.2"

import time
import busio
import board
import digitalio
import microcontroller
import math

############################
# Sensors
############################
class SensorDevices:
    def __init__(self):
        self.version = libSensors_version
        pass

    def initSensor(self, envSensorName, pins):
        try:
            if envSensorName == "MCP9808":
                envSensor = self.initMCP9808(pins)
            elif envSensorName == "BME280":
                envSensor = self.initBME280(pins)
            elif envSensorName == "BME680":
                envSensor = self.initBME680(pins)
            elif envSensorName == "MAX31865":
                envSensor = self.initMAX31865(pins)
            else:
                envSensor = None
            print(f"Temperature sensor ({envSensorName}) found and initialized.")
            return envSensor
        except Exception as e:
            print(f"Failed to initialize enironmental sensor ({envSensorName}): {e}")
            
    ##############################################
    # Sensors: Initialization and Data collection
    ##############################################
    def initMCP9808(self, pins):
        import adafruit_mcp9808
        MCP_I2C_SCL = getattr(board, "GP" + str(pins[0]))
        MCP_I2C_SDA = getattr(board, "GP" + str(pins[1]))
        i2c = busio.I2C(MCP_I2C_SCL, MCP_I2C_SDA)
        envSensor = adafruit_mcp9808.MCP9808(i2c)
        return envSensor

    def getEnvDataMCP9808(self, envSensor, correctTemp):
        t_envSensor = float(envSensor.temperature)
        if correctTemp.lower() == 'true':
            t_envSensor = self.correctTempMCP9808(t_envSensor)
        return {'temperature': f"{round(t_envSensor,1)}",
                'RH': "--",
                'pressure': "--",
                'gas': '--',
                'IAQ': '--',
                'HI': '--',
                'type': 'sensor',
                'libSensors_version': libSensors_version}
        
    def initBME280(self, pins):
        from adafruit_bme280 import basic as adafruit_bme280
        BME_CLK = getattr(board, "GP" + str(pins[0]))
        BME_MOSI = getattr(board, "GP" + str(pins[1]))
        BME_MISO = getattr(board, "GP" + str(pins[2]))
        BME_OUT = getattr(board, "GP" + str(pins[3]))
        spi = busio.SPI(BME_CLK, MISO=BME_MISO, MOSI=BME_MOSI)
        bme_cs = digitalio.DigitalInOut(BME_OUT)
        envSensor = adafruit_bme280.Adafruit_BME280_SPI(spi, bme_cs)
        return envSensor

    def getEnvDataBME280(self, envSensor, correctTemp):
        t_envSensor = float(envSensor.temperature)
        rh_envSensor = float(envSensor.humidity)
        p_envSensor = int(float(envSensor.pressure))
        if correctTemp.lower() == 'true':
            t_envSensor = self.correctTempBME280(t_envSensor,rh_envSensor)
        return {'temperature': f"{round(t_envSensor,1)}",
                'RH': f"{round(rh_envSensor, 1)}",
                'pressure': f"{p_envSensor}",
                'gas': '--',
                'IAQ': '--',
                'HI': f"{self.calctHI(t_envSensor,rh_envSensor)}",
                'type': 'sensor',
                'libSensors_version': self.version}

    def initBME680(self, pins):
        import adafruit_bme680
        BME_CLK = getattr(board, "GP" + str(pins[0]))
        BME_MOSI = getattr(board, "GP" + str(pins[1]))
        BME_MISO = getattr(board, "GP" + str(pins[2]))
        BME_OUT = getattr(board, "GP" + str(pins[3]))
        spi = busio.SPI(BME_CLK, MISO=BME_MISO, MOSI=BME_MOSI)
        bme_cs = digitalio.DigitalInOut(BME_OUT)
        envSensor = adafruit_bme680.Adafruit_BME680_SPI(spi, bme_cs)
        return envSensor
        
    def getEnvDataBME680(self, envSensor, correctTemp):
        t_envSensor = float(envSensor.temperature)
        rh_envSensor = float(envSensor.humidity)
        p_envSensor = int(float(envSensor.pressure))
        gas_envSensor = int(envSensor.gas)
        
        if correctTemp.lower() == 'true':
            t_envSensor = self.correctTempBME680(t_envSensor,rh_envSensor)
        aqi_envSensor = self.getIAQBME680(rh_envSensor, gas_envSensor)
        return {'temperature': f"{round(t_envSensor,1)}",
                'RH': f"{round(rh_envSensor,1)}",
                'pressure': f"{p_envSensor}",
                'gas': f"{gas_envSensor}",
                'IAQ': f"{aqi_envSensor}",
                'HI': f"{self.calctHI(t_envSensor,rh_envSensor)}",
                'type': 'sensor',
                'libSensors_version': self.version}
        
    def initMAX31865(self, pins):
        import adafruit_max31865
        BME_CLK = getattr(board, "GP" + str(pins[0]))
        BME_MOSI = getattr(board, "GP" + str(pins[1]))
        BME_MISO = getattr(board, "GP" + str(pins[2]))
        BME_OUT = getattr(board, "GP" + str(pins[3]))
        spi = busio.SPI(BME_CLK, MISO=BME_MISO, MOSI=BME_MOSI)
        bme_cs = digitalio.DigitalInOut(BME_OUT)
        envSensor = adafruit_max31865.MAX31865(spi, bme_cs)
        return envSensor
        
    def getEnvDataMAX31865(self, envSensor):
        t_envSensor = float(envSensor.temperature)
        if correctTemp.lower() == 'true':
            t_envSensor = self.correctTempMAX31865(t_envSensor)
        return {'temperature': f"{round(t_envSensor,1)}",
                'RH': "--",
                'pressure': "--",
                'gas': '--',
                'aqi': '--',
                'IAQ': '--',
                'type': 'sensor',
                'libSensors_version': self.version}

    def getData(self, envSensor, envSensorName, correctTemp):
        t_cpu = microcontroller.cpu.temperature
        if not envSensor:
            print(f"{envSensorName} not initialized. Using CPU temp with estimated offset.")
            if self.numTimes > 1 and self.avDeltaT != 0 :
                return {'temperature': f"{round(t_cpu - self.avDeltaT, 1)}",
                        'RH': '--',
                        'pressure': '--',
                        'gas': '--',
                        'aqi': '--',
                        'IAQ': '--',
                        'type': 'CPU adj.',
                        'libSensors_version': version}
            else:
                return {'temperature': f"{round(t_cpu, 1)} ",
                        'RH': '--',
                        'pressure': '--',
                        'gas': '--',
                        'IAQ': '--',
                        'HI': '--',
                        'type': 'CPU raw',
                        'libSensors_version': self.version}
        try:
            envSensorData = self.getSensorData(envSensor, envSensorName, correctTemp)
            delta_t = t_cpu - float(envSensorData['temperature'])
            if self.numTimes >= 2e+1:
                self.numTimes = int(1e+1)
            self.avDeltaT = (self.avDeltaT * self.numTimes + delta_t)/(self.numTimes+1)
            self.numTimes += 1
            print(f"Av. CPU/MCP T diff: {self.avDeltaT} {self.numTimes}")
            time.sleep(0.5)
            return envSensorData
        except:
            print(f"{envSensorName} not available. Av CPU/MCP T diff: {self.avDeltaT}")
            time.sleep(0.5)
            return {'temperature': f"{round(t_cpu-self.avDeltaT, 1)}",
                    'RH': '--',
                    'pressure': '--',
                    'gas': '--',
                    'IAQ': '--',
                    'HI': '--',
                    'type': 'CPU adj',
                    'libSensors_version': self.version}

    def getSensorData(self, envSensor, envSensorName, correctTemp):
        if envSensorName == "MCP9808":
            sensorData = self.getEnvDataMCP9808(envSensor, correctTemp)
        elif envSensorName == "BME280":
            sensorData = self.getEnvDataBME280(envSensor, correctTemp)
        elif envSensorName == "BME680":
            sensorData = self.getEnvDataBME680(envSensor, correctTemp)
        elif envSensorName == "MAX31865":
            sensorData = self.getEnvDataMAX31865(envSensor, correctTemp)
        return sensorData
    
    ##############################################
    # Sensors: Heat Index
    ##############################################
    # Caluclulate heat index
    def calctHI(self, t, rh):
        if t == "--" or rh == "--":
            return "--"
    
        tf = t*9/5 + 32
        
        if tf >= 80:
            C1 = -42.379
            C2 = 2.04901523
            C3 = 10.14333127
            C4 = -0.22475541
            C5 = -0.00683783
            C6 = -0.05481717
            C7 = 0.00122874
            C8 = 0.00085282
            C9 = -0.00000199
            hi = C1 + \
                C2 * tf + \
                C3 * rh + \
                C4 * tf * rh + \
                C5 * (tf**2) + \
                C6 * (rh**2) + \
                C7 * (tf**2) * rh + \
                C8 * (rh**2) * tf + \
                C7 * (tf**2) * (rh**2)
        else:
            C1 = 0.5
            C2 = 61.0
            C3 = 68.0
            C4 = 1.2
            C5 = 0.094
        
            hi = C1 * (tf + C2 + \
                ((tf - C3) * C4) + (rh * C5))
                
        return round((hi - 32) * 5/9 , 1)
    
    ##############################################
    # Sensors: Temperature Calibration
    ##############################################
    # Temperature correction for BME280
    def correctTempBME280(self, mt, mh):
        C_INTERCEPT     = -22.378940
        C_MT            = 3.497112
        C_MH            = -0.267584
        C_MT_P2         = -0.060241
        C_MT_MH         = 0.000282
        C_MH_P2         = 0.003162
        
        rt_pred = C_INTERCEPT + \
                  (C_MT * mt) + \
                  (C_MH * mh) + \
                  (C_MT_P2 * (mt**2)) + \
                  (C_MT_MH * (mt * mh)) + \
                  (C_MH_P2 * (mh**2))
                  
        return rt_pred
        
    # Temperature correction for BME680
    def correctTempBME680(self, mt, mh):
        C_INTERCEPT     = -27.800990
        C_MT            = 2.686044
        C_MH            = 0.577078
        C_MT_P2         = -0.026907
        C_MT_MH         = -0.018497
        C_MH_P2         = -0.003123
        
        rt_pred = C_INTERCEPT + \
                  (C_MT * mt) + \
                  (C_MH * mh) + \
                  (C_MT_P2 * (mt**2)) + \
                  (C_MT_MH * (mt * mh)) + \
                  (C_MH_P2 * (mh**2))
        return rt_pred
        
    # Temperature correction for BME280
    def correctTempMCP9808(self, mt):
        return mt
        
    # Temperature correction for MAX31865
    def correctTempMax31865(self, mt):
        return mt
        
    ##############################################
    # Sensors: AQI score estimator
    ##############################################
    def getIAQBME680(self, RH, R_gas):
        S_max = 400
    
        SG_max = 0.75 * S_max
        R_min = 750 # This is the saturation value in Ohm
        R_max = 80000  # This is the baseline that needs to be measured in clean air
        SG = SG_max * ((log10(R_gas)-log10(R_min))/(log10(R_max)-log10(R_min)))
         
        SH_max = 0.25 * S_max
        SH_opt = 40
        SH_range = 60
        SH = SH_max * (1 - (abs(RH - SH_opt))/SH_range)
        
        # We are using the reversed scale 0 -> 100
        IAQ = int(S_max-(SG + SH))
        return IAQ

##############################################
# Math Utilities
##############################################
def log10(x):
    try:
        # for board with math processor (RP2350)
        log10 = math.log10(x)
    except:
        # for board without math processor (RP2040)
        log10 = math.log(x) / math.log(10)
    return log10
        
        
