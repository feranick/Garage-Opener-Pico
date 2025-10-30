# **********************************************
# * Garage Opener - Rasperry Pico W
# * v2025.10.19.1
# * By: Nicola Ferralis <feranick@hotmail.com>
# **********************************************

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

#from adafruit_datetime import datetime
#import adafruit_ntp

import adafruit_hcsr04
import adafruit_mcp9808
from adafruit_httpserver import Server, MIMETypes, Response

version = "2025.10.19.1"

I2C_SCL = board.GP17
I2C_SDA = board.GP16
DOOR_SIGNAL = board.GP18
SONAR_TRIGGER = board.GP15
SONAR_ECHO = board.GP14

############################
# Server
############################
class GarageServer:

    def setup_server(self):
        pool = socketpool.SocketPool(wifi.radio)
        self.server = Server(pool, debug=True)
        self.requests = adafruit_requests.Session(pool, ssl.create_default_context())

        # --- Routes ---

        @self.server.route("/api/status")
        def api_status(request):
            state = self.sensors.checkStatusSonar()
            label = self.control.setLabel(state)
            temperature = self.sensors.getTemperature()
            date_time = self.getDateTime()
            nws = self.get_nws_data()
            aqi = self.get_openweather_aq()

            data_dict = {
                "state": state,
                "button_color": label[1],
                "temperature": temperature,
                "datetime": date_time,
                "ip": self.ip,
                "station": nws[6],
                "ext_temperature": f"{nws[0]} \u00b0C",
                "ext_heatindex": f"{nws[1]} \u00b0C",
                "ext_RH": f"{nws[2]} %",
                "ext_aqi": f"{aqi[0]}",
                "ext_aqi_color": f"{aqi[1]}",
                "ext_next_aqi": f"{aqi[2]}",
                "ext_next_aqi_color": f"{aqi[3]}",
                "ext_pressure": f"{nws[3]} mbar",
                #"ext_dewpoint": f"{nws[4]} \u00b0C",
                "ext_visibility": f"{nws[5]} m",
                "ext_weather": nws[7],
                "version": version,
            }
            json_content = json.dumps(data_dict)

            print(json_content)

            headers = {"Content-Type": "application/json"}

            # Return the response using the compatible Response constructor
            return Response(request, json_content, headers=headers)

    
    def setup_ntp(self):
        try:
            self.ntp = adafruit_ntp.NTP(socketpool.SocketPool(wifi.radio), tz_offset=-5)
        except Exception as e:
            print(f"Failed to setup NTP: {e}")

    ########################################################
    # This is now done in javascript, client-side.
    ########################################################
    def getDateTime(self):
        if self.ntp and self.ntp.datetime:
            try:
                st = self.ntp.datetime
                return f"{st.tm_year:04}-{st.tm_mon:02}-{st.tm_mday:02} {st.tm_hour:02}:{st.tm_min:02}:{st.tm_sec:02}"
            except Exception as e:
                print(f"Error converting NTP time: {e}")
                return "Time N/A"
        return "Time N/A"

    ############################
    # Retrieve NVS data
    ############################
    def get_nws_data(self):
        nws_url = "https://api.weather.gov/stations/"+self.station+"/observations/latest/"
        user_agent = "(feranick, feranick@hotmail.com)"
        headers = {'Accept': 'application/geo+json',
            'User-Agent' : user_agent}

        DEFAULT_MISSING = "--"

        # 1. Define the order, property keys, and format strings
        keys = [
            'temperature',
            'heatIndex',
            'relativeHumidity',
            'seaLevelPressure',
            'dewpoint',
            'visibility',
        ]

        # Map each key to its required format string
        # We only care about 'format' here, as the 'default' will be DEFAULT_MISSING ("--")
        formats_map = {
            'temperature':        '{:.1f}',
            'heatIndex':          '{:.1f}',
            'relativeHumidity':   '{:.0f}',
            'seaLevelPressure':   '{:.0f}',
            'dewpoint':           '{:.1f}',
            'visibility':         '{:.0f}',
            # 'presentWeather' is a special case handled separately
        }
        data = []

        # Pre-calculate the full list of missing defaults for use in the final 'except' block.
        full_defaults_list = [DEFAULT_MISSING] * len(keys)

        try:
            self.r = self.requests.get(nws_url, headers=headers)
            # self.r.raise_for_status() # Optional: Add to catch bad HTTP responses
            response_json = self.r.json()
            properties = response_json['properties']

            for key in keys:
                format_str = formats_map[key]
                raw_value = properties.get(key, {}).get('value')

                if raw_value is None:
                    formatted_value = DEFAULT_MISSING
                else:
                    try:
                        # Cast to float, apply the format, which results in a string.
                        formatted_value = format_str.format(float(raw_value))
                    except (ValueError, TypeError):
                        # Fallback to the uniform default if the value isn't a valid number
                        formatted_value = DEFAULT_MISSING

                data.append(formatted_value)

            stationName = properties.get('stationName')
            data.append(str(stationName))

            weather_list = properties.get('presentWeather', [])
            weather_value = None

            if weather_list and len(weather_list) > 0:
                weather_value = weather_list[0].get('weather')

            if weather_value is None:
                data.append(DEFAULT_MISSING)
            else:
                data.append(str(weather_value))

            self.r.close()
            return data

        except adafruit_requests.OutOfRetries:
            print("NWS: Too many retries (likely network issue)")
            return full_defaults_list
        except RuntimeError as e: # Covers socket errors, etc.
            print(f"NWS: Network error: {e}")
            return full_defaults_list
        except (KeyError, TypeError, ValueError) as e: # Problems with JSON structure or content
            print(f"NWS: Error parsing data: {e}")
            return full_defaults_list
        except Exception as e:
            print(f"NWS: An unexpected error occurred: {e}")
            return full_defaults_list
        finally:
            if hasattr(self, 'r') and self.r:
                self.r.close()

    def get_openweather_geoloc(self):
        pool = socketpool.SocketPool(wifi.radio)
        server = Server(pool, debug=True)
        requests = adafruit_requests.Session(pool, ssl.create_default_context())
        geo_url = "http://api.openweathermap.org/geo/1.0/zip?zip="+self.zipcode+","+self.country+"&appid="+self.ow_api_key
        r = requests.get(geo_url)
        lat = str(r.json()["lat"])
        lon = str(r.json()["lon"])
        r.close()
        return lat, lon

    def get_openweather_aq(self):
        aqi_current_url = "http://api.openweathermap.org/data/2.5/air_pollution?lat="+self.lat+"&lon="+self.lon+"&appid="+self.ow_api_key
        aqi_forecast_url = "http://api.openweathermap.org/data/2.5/air_pollution/forecast?lat="+self.lat+"&lon="+self.lon+"&appid="+self.ow_api_key
        r = self.requests.get(aqi_current_url)
        aqi = r.json()["list"][0]["main"]["aqi"]
        r.close()

        r = self.requests.get(aqi_forecast_url)
        next_aqi = r.json()["list"][24]["main"]["aqi"]
        r.close()

        return aqi, self.col_aqi(aqi), next_aqi, self.col_aqi(next_aqi)

    def col_aqi(self, aqi):
        if aqi == 1:
            col = "green"
        elif aqi == 2:
            col = "yellow"
        elif aqi == 3:
            col = "orange"
        elif aqi == 4:
            col = "red"
        elif aqi == 5:
            col = "purple"
        else:
            col = "white"
        return col
    

############################
# Control, Sensors
############################
class Sensors:
    # This is only needed if using on device sonar
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
                    return ["OPEN", "green"]
                else:
                    return ["CLOSE", "red"]
                time.sleep(0.5)
                return st
            except RuntimeError as err:
                print(f" Check Sonar Status: Retrying! Error: {err}")
                nt += 1
                time.sleep(0.5)
        print(" Sonar status not available")
        return ["N/A", "orange"]

