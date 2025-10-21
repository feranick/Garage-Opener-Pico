# **********************************************
# * Garage Opener - Rasperry Pico W
# * v2025.10.21.1
# * By: Nicola Ferralis <feranick@hotmail.com>
# **********************************************

version = "2025.10.21.1"

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

#from adafruit_datetime import datetime
#import adafruit_ntp

DOOR_SIGNAL = board.GP22

# HCSR04 - SONAR
import adafruit_hcsr04
SONAR_TRIGGER = board.GP15
SONAR_ECHO = board.GP14

# MCP9808 ONLY
#import adafruit_mcp9808
#MCP_I2C_SCL = board.GP17
#MCP_I2C_SDA = board.GP16

# BME680 NS BME280 ONLY
import adafruit_bme680
#from adafruit_bme280 import basic as adafruit_bme280
BME_CLK = board.GP18
BME_MOSI = board.GP19
BME_MISO = board.GP16
BME_OUT = board.GP17

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
        self.triggerDistance = 20.0
        self.sensorTemperatureOffset = 0
        try:
            trig_dist_env = os.getenv("triggerDistance")
            if trig_dist_env is not None:
                self.triggerDistance = float(trig_dist_env)
            else:
                print("Warning: 'triggerDistance' not found in settings.toml. Using default.")
        except ValueError:
            print(f"Warning: Invalid triggerDistance '{trig_dist_env}' in settings.toml. Using default.")
        
        try:
            temperature_offset = os.getenv("sensorTemperatureOffset")
            if temperature_offset is not None:
                self.sensorTemperatureOffset = float(temperature_offset)
            else:
                print("Warning: 'sensorTemperatureOffset' not found in settings.toml. Using default.")
        except ValueError:
            print(f"Warning: Invalid triggerDistance '{sensorTemperatureOffset}' in settings.toml. Using default.")

############################
# Server
############################
class GarageServer:
    def __init__(self, control, sensors):
        try:
            self.sonarURL = os.getenv("sensorURL")
            self.station = os.getenv("station")
            self.zipcode = os.getenv("zipcode")
            self.country = os.getenv("country")
            self.ow_api_key = os.getenv("ow_api_key")
        except KeyError: # If a key is not in os.environ (e.g. missing in settings.toml)
            print("A required setting was not found in settings.toml, using defaults.")
            self.sonarURL = "192.168.1.206"
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

            #this is now handled cliet side in javascript
            #self.lat, self.lon = self.get_openweather_geoloc()

            self.setup_server()
            #self.setup_ntp()
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
        self.server = Server(pool, debug=True)
        self.requests = adafruit_requests.Session(pool, ssl.create_default_context())

        # --- Routes ---

        # Root Route: Serves static/index.html
        @self.server.route("/")
        def base_route(request):
            return self._serve_static_file(request, 'static/index.html')

        # Run Control Route
        @self.server.route("/run")
        def run_control(request):
            print("Run Control via HTTP request")
            self.control.runControl()
            # Use simplified Response for 200 OK
            return Response(request, "OK")

        # Status Check Route (Placeholder)
        @self.server.route("/status")
        def update_status(request):
            # Use simplified Response for 200 OK
            return Response(request, "OK")

        @self.server.route("/api/status")
        def api_status(request):
            #state = self.sensors.checkStatusSonar()
            remoteData = self.getStatusRemoteSonar()
            localData = self.sensors.getEnvData()

            data_dict = {
                "state": remoteData['state'],
                "button_color": remoteData['button_color'],
                "locTemp": localData['temperature'],
                "locRH": localData['RH'],
                "locGas": localData['gas'],
                "remoteTemp": remoteData['temperature'],
                "remoteRH": remoteData['RH'],
                "remoteURL" : self.sonarURL,
                "ip": self.ip,
                "ow_api_key": self.ow_api_key,
                "station": self.station,
                "zipcode": self.zipcode,
                "country": self.country,
                "version": version,
            }
            json_content = json.dumps(data_dict)

            print(json_content)

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

    def getStatusRemoteSonar(self):
        try:
            r = self.requests.get("http://"+self.sonarURL+"/api/status")
            data = r.json()
            r.close()
            return data
        except Exception as e:
            print(f"Sonar not available: {e}")
            return {'pressure': '--', 'button_color': 'orange', 'state': 'N/A', 'RH': '--', 'temperature': '--'}

    '''
    def setup_ntp(self):
        try:
            self.ntp = adafruit_ntp.NTP(socketpool.SocketPool(wifi.radio), tz_offset=-5)
        except Exception as e:
            print(f"Failed to setup NTP: {e}")
    '''

    def reboot(self):
        time.sleep(2)
        microcontroller.reset()

############################
# Control, Sensors
############################
class Control:
    def __init__(self):
        self.btn = digitalio.DigitalInOut(DOOR_SIGNAL)
        self.btn.direction = digitalio.Direction.OUTPUT
        self.btn.value = False

    def runControl(self):
        self.btn.value = True
        time.sleep(1)
        self.btn.value = False
        time.sleep(1)

class Sensors:
    def __init__(self, conf):
        self.sonar = None
        self.envSensor = None
        self.envSensorName = None
        try:
            self.sonar = adafruit_hcsr04.HCSR04(trigger_pin=SONAR_TRIGGER, echo_pin=SONAR_ECHO)
        except Exception as e:
            print(f"Failed to initialize HCSR04: {e}")

        self.trigDist = conf.triggerDistance
        self.temp_offset = conf.sensorTemperatureOffset

        try:
            #self.envSensorName = self.initMCP9808()
            #self.envSensorName = self.initBME280()
            self.envSensorName = self.initBME680()
            self.avDeltaT = microcontroller.cpu.temperature - self.envSensor.temperature
            print(f"Temperature sensor ({self.envSensorName}) found and initialized.")
        except Exception as e:
            self.avDeltaT = 0
            print(f"Failed to initialize enironmental sensor: {e}")
        self.numTimes = 1
        
    def initMCP9808(self):
        i2c = busio.I2C(MCP_I2C_SCL, MCP_I2C_SDA)
        self.envSensor = adafruit_mcp9808.MCP9808(i2c)
        return "MCP9808"
        
    def getEnvDataMCP9808(self):
        return {'temperature': str(self.envSensor.temperature), 'RH': '--', 'gas': '--'}
        
    def initBME280(self):
        spi = busio.SPI(BME_CLK, MISO=BME_MISO, MOSI=BME_MOSI)
        bme_cs = digitalio.DigitalInOut(BME_OUT)
        self.envSensor = adafruit_bme680.Adafruit_BME280_SPI(spi, bme_cs)
        return "BME280"
        
    def getEnvDataBME280(self):
        return {'temperature': str(self.envSensor.temperature), 'RH': str(self.envSensor.relative_humidity), 'gas': '--'}
        
    def initBME680(self):
        spi = busio.SPI(BME_CLK, MISO=BME_MISO, MOSI=BME_MOSI)
        bme_cs = digitalio.DigitalInOut(BME_OUT)
        self.envSensor = adafruit_bme680.Adafruit_BME680_SPI(spi, bme_cs)
        return "BME680"
    
    def getEnvDataBME680(self):
        return {'temperature': str(self.envSensor.temperature), 'RH': str(self.envSensor.humidity), 'gas': str(self.envSensor.gas)}

    def getEnvData(self):
        t_cpu = microcontroller.cpu.temperature
        if not self.envSensor:
            print(f"{self.envSensorName} not initialized. Using CPU temp with estimated offset.")
            if self.numTimes > 1 and self.avDeltaT != 0 :
                return {'temperature': f"{round(t_cpu - self.avDeltaT, 1)} \u00b0C (CPU adj.)", 'RH': '--', 'gas': '--'}
            else:
                return {'temperature': f"{round(t_cpu, 1)} \u00b0C (CPU raw)", 'RH': '--', 'gas': '--'}
        try:
            #envSensor = self.getEnvDataMCP9808()
            envSensor = self.getEnvDataBME680()
            #envSensor = self.getEnvDataBME280()
            t_envSensor = float(envSensor['temperature']) + self.temp_offset
            rh_envSensor = envSensor['RH']
            gas_envSensor = envSensor['gas']
            delta_t = t_cpu - t_envSensor
            if self.numTimes >= 2e+1:
                self.numTimes = int(1e+1)
            self.avDeltaT = (self.avDeltaT * self.numTimes + delta_t)/(self.numTimes+1)
            self.numTimes += 1
            print(f"Av. CPU/MCP T diff: {self.avDeltaT} {self.numTimes}")
            time.sleep(1)
            return {'temperature': f"{round(t_envSensor,1)} \u00b0C", 'RH': f"{int(float(rh_envSensor))} %", 'gas': f"{int(float(gas_envSensor))}"}
        except:
            print(f"{self.envSensorName} not available. Av CPU/MCP T diff: {self.avDeltaT}")
            time.sleep(1)
            return {'temperature': f"{round(t_cpu-self.avDeltaT, 1)} \u00b0C (CPU)", 'RH': '--', 'gas': '--'}

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
