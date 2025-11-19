# **********************************************
# * Garage Opener - Rasperry Pico W
# * Environmental and remote sonar only
# * v2025.11.18.1
# * By: Nicola Ferralis <feranick@hotmail.com>
# **********************************************

version = "2025.11.18.1"

import wifi
import time
import microcontroller
import supervisor
import os
import busio
import board
import digitalio
import socketpool
import ssl
import json

#import adafruit_requests
#import adafruit_ntp
from adafruit_httpserver import Server, MIMETypes, Response

from libSensors import SensorDevices

# HCSR04 - SONAR
import adafruit_hcsr04
SONAR_TRIGGER = board.GP15
SONAR_ECHO = board.GP13

############################
# Initial WiFi/Safe Mode Check
############################
if supervisor.runtime.safe_mode_reason is not None:
    try:
        print("Performing initial WiFi radio state check/reset...")
        if wifi.radio.connected:
            print("Radio was connected, disconnecting first.")
            wifi.radio.stop_station()
            time.sleep(0.5)
            wifi.radio.start_station()

        print("Toggling WiFi radio enabled state...")
        wifi.radio.enabled = False
        time.sleep(1.0)
        wifi.radio.enabled = True
        time.sleep(1.0)
        print("Initial WiFi radio toggle complete.")
    except Exception as e:
        print(f"Error during initial WiFi radio toggle: {e}")

############################
# User variable definitions
############################
class Conf:
    def __init__(self):
        try:
            self.trigger_distance = float(os.getenv("trigger_distance"))
        except ValueError:
            self.trigger_distance = 20.0
            print(f"Warning: Invalid trigger_distance '{trig_dist_env}' in settings.toml. Using default.")

        try:
            self.sensor1_name = os.getenv("sensor1_name")
            self.sensor1_pins = stringToArray(os.getenv("sensor1_pins"))
            self.sensor1_correct_temp = os.getenv("sensor1_correct_temp")
        except ValueError:
            self.sensor1_name = None
            self.sensor1_pins = None
            self.sensor1_correct_temp = "False"
            print(f"Warning: Invalid settings.toml. Using default.")

############################
# Server
############################
class GarageServer:
    def __init__(self, sensors):

        self.sensors = sensors
        self.server = None
        self.ip = "0.0.0.0"

        try:
            self.connect_wifi()

            self.setup_server()
            print("\nDevice IP:", self.ip, "\nListening...")
        except RuntimeError as err:
            print(f"Initialization error: {err}")
            self.fail_reboot()
        except Exception as e:
            print(f"Unexpected critical error: {e}")
            self.fail_reboot()

    def fail_reboot(self):
        print("Rebooting in 5 seconds due to error...")
        time.sleep(5)
        self.reboot()

    def connect_wifi(self):
        ssid = os.getenv('CIRCUITPY_WIFI_SSID')
        password = os.getenv('CIRCUITPY_WIFI_PASSWORD')
        if ssid is None or password is None:
            raise RuntimeError("WiFi credentials not found.")

        MAX_WIFI_ATTEMPTS = 5
        attempt_count = 0
        time.sleep(5)
        while not wifi.radio.connected:
            if attempt_count >= MAX_WIFI_ATTEMPTS:
                raise RuntimeError("Failed to connect to WiFi after multiple attempts.")
            print(f"\nConnecting to WiFi (attempt {attempt_count + 1}/{MAX_WIFI_ATTEMPTS})...")
            try:
                wifi.radio.connect(ssid, password)
                time.sleep(2)
            except ConnectionError as e:
                print(f"WiFi Connection Error: {e}")
                time.sleep(5)
            except Exception as e:
                print(f"WiFi other connect error: {e}")
                time.sleep(3)
            attempt_count += 1

        if wifi.radio.connected:
            self.ip = str(wifi.radio.ipv4_address)
            print("WiFi Connected!")
        else:
            raise RuntimeError("Failed to connect to WiFi.")

    def setup_server(self):
        pool = socketpool.SocketPool(wifi.radio)
        self.server = Server(pool, debug=False)

        # --- Routes ---
        @self.server.route("/api/status")
        def api_status(request):
            state = self.sensors.checkStatusSonar()
            #label = self.sensors.setLabel(state)
            #temperature = self.sensors.getTemperature()
            envData = self.sensors.getEnvData(self.sensors.envSensor1, self.sensors.envSensor1_name, self.sensors.sensor1_correct_temp)

            data_dict = {
                "state": state,
                "temperature": envData['temperature'],
                "RH": envData['RH'],
                "pressure": envData['pressure'],
                "HI": envData['HI'],
                "gas": envData['gas'],
                "IAQ": envData['IAQ'],
                "TVOC": envData['TVOC'],
                "eCO2": envData['eCO2'],
                "type": envData['type'],
                "libSensors_version": self.sensors.sensDev.version,
            }
            json_content = json.dumps(data_dict)

            print(json_content)

            headers = {"Content-Type": "application/json"}

            # Return the response using the compatible Response constructor
            return Response(request, json_content, headers=headers)


        # Start the server
        self.server.start(host=self.ip, port=80)

    def _serve_static_file(self, request, filepath, content_type="text/html"):
        """Manually reads a file and returns an HTTP response with a customizable content type."""

        # Determine if the file should be read in binary mode
        is_binary = filepath.endswith(('.ico', '.png'))
        mode = "rb" if is_binary else "r"
        encoding = None if is_binary else 'utf-8'

        try:
            with open(filepath, mode, encoding=encoding) as f:
                content = f.read()

            headers = {"Content-Type": content_type}

            # The Response object handles both text (str) and binary (bytes) content
            return Response(request, content, headers=headers)

        except OSError as e:
            # Handle File Not Found or other OS errors
            print(f"Error opening or reading file {filepath}: {e}")
            try:
                # The response content here should be simple text
                return Response(request, "File Not Found", {}, 404)
            except Exception as e2:
                print(f"Could not set 404 status: {e2}")
                return Response(request, "File Not Found. Check console.")

    def serve_forever(self):
        while True:
            if not wifi.radio.connected:
                print("WiFi connection lost. Rebooting...")
                self.reboot()

            try:
                self.server.poll()
            except (BrokenPipeError, OSError) as e:
                if isinstance(e, OSError) and e.args[0] not in (32, 104):
                    print(f"Unexpected OSError in server poll: {e}")
                elif isinstance(e, BrokenPipeError):
                    pass
            except Exception as e:
                print(f"Unexpected critical error in server poll: {e}")

            time.sleep(0.01)

    def reboot(self):
        time.sleep(2)
        microcontroller.reset()


############################
# Sensors
############################
class Sensors:
    def __init__(self, conf):
        self.sensDev = SensorDevices()
        
        # Sonar initialization
        self.sonar = None
        try:
            self.sonar = adafruit_hcsr04.HCSR04(trigger_pin=SONAR_TRIGGER, echo_pin=SONAR_ECHO)
        except Exception as e:
            print(f"Failed to initialize HCSR04: {e}")

        self.trigger_distance = conf.trigger_distance
        
        # Sensor initialization
        self.envSensor1 = None
        self.envSensor1_name = conf.sensor1_name
        self.envSensor1_pins = conf.sensor1_pins
        self.sensor1_correct_temp = conf.sensor1_correct_temp

        try:
            self.sonar = adafruit_hcsr04.HCSR04(trigger_pin=SONAR_TRIGGER, echo_pin=SONAR_ECHO)
        except Exception as e:
            print(f"Failed to initialize HCSR04: {e}")

        self.trigger_distance = conf.trigger_distance
        
        self.envSensor1 = self.sensDev.initSensor(conf.sensor1_name, conf.sensor1_pins)

        if self.envSensor1 != None:
            if isinstance(self.envSensor1, list):
                sens1_temp = self.envSensor1[0].temperature
            else:
                sens1_temp = self.envSensor1.temperature
            self.avDeltaT = microcontroller.cpu.temperature - sens1_temp
        else:
            self.avDeltaT = 0

        self.numTimes = 1
        
    def getEnvData(self, envSensor, envSensor_name, correct_temp):
        t_cpu = microcontroller.cpu.temperature
        if not envSensor:
            print(f"{envSensor_name} not initialized. Using CPU temp with estimated offset.")
            if self.numTimes > 1 and self.avDeltaT != 0 :
                return {'temperature': f"{round(t_cpu - self.avDeltaT, 1)}",
                        'RH': '--', 
                        'pressure': '--',
                        'gas': '--',
                        'IAQ': '--',
                        'TVOC': '--',
                        'eCO2': '--',
                        'HI': '--',
                        'type': 'CPU adj.'}
            else:
                return {'temperature': f"{round(t_cpu, 1)}",
                        'RH': '--', 
                        'pressure': '--',
                        'gas': '--',
                        'IAQ': '--',
                        'TVOC': '--',
                        'eCO2': '--',
                        'HI': '--',
                        'type': 'CPU raw'}
        try:
            envSensorData = self.sensDev.getSensorData(envSensor, envSensor_name, correct_temp)
            delta_t = t_cpu - float(envSensorData['temperature'])
            if self.numTimes >= 2e+1:
                self.numTimes = int(1e+1)
            self.avDeltaT = (self.avDeltaT * self.numTimes + delta_t)/(self.numTimes+1)
            self.numTimes += 1
            print(f"Av. CPU/MCP T diff: {self.avDeltaT} {self.numTimes}")
            time.sleep(0.5)
            return envSensorData
        except:
            print(f"{envSensor_name} not available. Av CPU/MCP T diff: {self.avDeltaT}")
            time.sleep(0.5)
            return {'temperature': f"{round(t_cpu-self.avDeltaT, 1)}",
                    'RH': '--', 
                    'pressure': '--',  
                    'gas': '--',
                    'IAQ': '--',
                    'TVOC': '--',
                    'eCO2': '--',
                    'HI': '--',
                    'type': 'CPU adj'}
                    
    def checkStatusSonar(self):
        if not self.sonar:
            print("Sonar not initialized.")
            return "N/A"
        nt = 0
        while nt < 2:
            try:
                dist = self.sonar.distance
                print("Distance: "+str(dist))
                if dist < self.trigger_distance:
                    return "OPEN"
                else:
                    return "CLOSED"
                time.sleep(0.5)
                return st
            except RuntimeError as err:
                print(f" Check Sonar Status: Retrying! Error: {err}")
                nt += 1
                time.sleep(0.5)
        print(" Sonar status not available")
        return "N/A"

############################
# Utilities
############################
def stringToArray(string):
    if string is not None:
        number_strings = (
        string.replace(" ", "")
            .split(',')
        )
        array = [int(p) for p in number_strings]
        return array
    else:
        print("Warning: Initial string-array not found in settings.toml")
        return []
        
############################
# Main
############################
def main():
    conf = Conf()
    sensors = Sensors(conf)
    server = GarageServer(sensors)
    server.serve_forever()

main()
