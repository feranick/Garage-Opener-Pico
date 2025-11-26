# **********************************************
# * Garage Opener - Rasperry Pico W
# * v2025.11.26.1
# * By: Nicola Ferralis <feranick@hotmail.com>
# **********************************************

version = "2025.11.26.1"

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

import adafruit_requests
from adafruit_httpserver import Server, MIMETypes, Response

import adafruit_ntp

from libSensors import SensorDevices, overclock

DOOR_SIGNAL = board.GP22

# HCSR04 - SONAR
import adafruit_hcsr04
SONAR_TRIGGER = board.GP15
SONAR_ECHO = board.GP14

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
            overclock(os.getenv("overclock"))
        except:
            overclock("False")
        
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
    def __init__(self, control, sensors):
        try:
            self.remote_sensor_ip = os.getenv("remote_sensor_ip").split(',')
            self.station = os.getenv("station")
            self.zipcode = os.getenv("zipcode")
            self.country = os.getenv("country")
            self.ow_api_key = os.getenv("ow_api_key")
            print(f"\nRemote sensors IP: {self.remote_sensor_ip}")
        except KeyError: # If a key is not in os.environ (e.g. missing in settings.toml)
            print("A required setting was not found in settings.toml, using defaults.")
            self.remote_sensor_ip = ["192.168.1.206","192.168.1.208"]
            self.station = "kbos"
            self.zipcode = "02139"
            self.country = "US"
            self.ow_api_key = "e11595e5e85bcf80302889e0f669b370"
        except Exception as e:
            print(f"Error reading settings: {e}")

        self.control = control
        self.sensors = sensors
        self.ntp = None
        self.server = None
        self.ip = "0.0.0.0"

        try:
            self.connect_wifi()
            self.setup_server()
            self.setup_ntp()
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
        self.requests = adafruit_requests.Session(pool, ssl.create_default_context())

        # --- Routes ---

        # Root Route: Serves static/index.html
        @self.server.route("/")
        def base_route(request):
            return self._serve_static_file(request, 'static/index.html')

        # Run Control Route
        @self.server.route("/api/run")
        def run_control(request):
            print("Run Control via HTTP request")
            self.control.runControl()
            # Use simplified Response for 200 OK
            return Response(request, "OK")

        # Status Check Route (Placeholder)
        #@self.server.route("/status")
        #def update_status(request):
        #    # Use simplified Response for 200 OK
        #   return Response(request, "OK")

        @self.server.route("/api/status")
        def api_status(request):
            #device_id = request.args.get("device_id")
            device_id = request.query_params.get("device_id")

            if device_id == "loc":
                data = self.sensors.getEnvData(self.sensors.envSensor1, self.sensors.envSensor1_name, self.sensors.sensor1_correct_temp)
                remote_sensor_ip = "local"
                state = "N/A"
            else:
                if device_id[:-1] == "remote":
                    dev_type = device_id[:-1]
                    dev_num = int(device_id[-1])
                else:
                    print("\n\nTEST\n")
                    dev_type = "remote"
                    dev_num = 0
                data = self.getStatusRemoteSonar(dev_num)
                remote_sensor_ip = self.remote_sensor_ip[dev_num]
                state = data['state']

            UTC = self.getUTC()

            data_dict = {
                "state" : state,
                "remote_sensor_ip" : remote_sensor_ip,
                "libSensors_version": self.sensors.sensDev.version,
                "ip": self.ip,
                "ow_api_key": self.ow_api_key,
                "station": self.station,
                "zipcode": self.zipcode,
                "country": self.country,
                "version": version,
                "UTC": UTC,
            }

            data_dict[f"{device_id}Temp"] = data['temperature']
            data_dict[f"{device_id}RH"] = data['RH']
            data_dict[f"{device_id}HI"] = data['HI']
            data_dict[f"{device_id}IAQ"] = data['IAQ']
            data_dict[f"{device_id}TVOC"] = data['TVOC']
            data_dict[f"{device_id}eCO2"] = data['eCO2']
            data_dict[f"{device_id}Sens"] = data['type']

            json_content = json.dumps(data_dict)

            print(f"\n{json_content}")

            headers = {"Content-Type": "application/json"}

            # Return the response using the compatible Response constructor
            return Response(request, json_content, headers=headers)

        @self.server.route("/scripts.js")
        def icon_route(request):
            return self._serve_static_file(request, 'static/scripts.js')

        @self.server.route("/manifest.json")
        def icon_route(request):
            return self._serve_static_file(request, 'static/manifest.json')

        @self.server.route("/favicon.ico")
        def favicon_route(request):
            return self._serve_static_file(request, 'static/favicon.ico', content_type="image/x-icon")

        # If using a PNG for an app icon:
        @self.server.route("/icon192.png")
        def icon_route(request):
            return self._serve_static_file(request, 'static/icon192.png', content_type="image/png")

        @self.server.route("/icon.png")
        def icon_route(request):
            return self._serve_static_file(request, 'static/icon.png', content_type="image/png")

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

    def getStatusRemoteSonar(self, dev):
        try:
            r = self.requests.get("http://"+self.remote_sensor_ip[dev]+"/api/status", timeout=3.0)
            data = r.json()
            r.close()
            return data
        except Exception as e:
            print(f"Sonar not available: {e}")
            return {'state': 'N/A',
                    'temperature': '--',
                    'pressure': '--',
                    'RH': '--',
                    'HI': '--',
                    'IAQ': '--',
                    'TVOC': '--',
                    'eCO2': '--',
                    'type': '--'}

    def setup_ntp(self):
        try:
            self.ntp = adafruit_ntp.NTP(socketpool.SocketPool(wifi.radio), tz_offset=0)
        except Exception as e:
            print(f"Failed to setup NTP: {e}")

    def getUTC(self):
        try:
            return self.ntp.utc_ns
        except Exception as e:
            print(f"Error converting NTP time: {e}")
            return 0

    def reboot(self):
        time.sleep(2)
        microcontroller.reset()

############################
# Control
############################
class Control:
    def __init__(self):
        self.btn = digitalio.DigitalInOut(DOOR_SIGNAL)
        self.btn.direction = digitalio.Direction.OUTPUT
        self.btn.value = False

    def runControl(self):
        self.btn.value = True
        time.sleep(2)
        self.btn.value = False
        time.sleep(1)

############################
# Sensors
############################
class Sensors:
    def __init__(self, conf):
        self.sensDev = SensorDevices()

        '''
        # Enable for the use of Sonar in main device
        self.sonar = None
        try:
            self.sonar = adafruit_hcsr04.HCSR04(trigger_pin=SONAR_TRIGGER, echo_pin=SONAR_ECHO)
        except Exception as e:
            print(f"Failed to initialize HCSR04: {e}")

        self.trigger_distance = conf.trigger_distance
        '''

        self.envSensor1 = None
        self.envSensor1_name = conf.sensor1_name
        self.envSensor1_pins = conf.sensor1_pins
        self.sensor1_correct_temp = conf.sensor1_correct_temp

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
                    'IAQ': '--',
                    'TVOC': '--',
                    'eCO2': '--',
                    'HI': '--',
                    'type': 'CPU adj.'}
            else:
                return {'temperature': f"{round(t_cpu, 1)}",
                    'RH': '--',
                    'pressure': '--',
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
                    'IAQ': '--',
                    'TVOC': '--',
                    'eCO2': '--',
                    'HI': '--',
                    'type': 'CPU adj'}
    '''
    # Enable for Sonar in main device
    def checkStatusSonar(self):
        if not self.sonar:
            print("Sonar not initialized.")
            return "N/A"
        nt = 0
        while nt < 2:
            try:
                dist = self.sonar.distance
                print("Distance: "+str(dist))
                if dist < self.trigDist:
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
    '''

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
    control = Control()
    sensors = Sensors(conf)
    server = GarageServer(control, sensors)

    server.serve_forever()

main()
