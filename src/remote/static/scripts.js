let coords = null;

////////////////////////////////////
// Get and format Date and Time
////////////////////////////////////
function getCurrentDateTime() {
    function get_dig(a) {
        if (a<10) {
            secs = "0"+a;}
        else {
            secs = a;}
        return secs;}
        
    let now = new Date();
    month = now.getMonth()+1
    day = now.getDate()
    year = now.getFullYear()
    hours = get_dig(now.getHours())
    minutes = get_dig(now.getMinutes())
    
    if (now.getSeconds()<10) {
        secs = "0"+now.getSeconds();}
    else {
        secs = now.getSeconds();}
        
    formattedTime = hours +":"+minutes+":"+secs;
    formattedDate = month+"/"+day+"/"+year;
    return formattedDate+"      "+formattedTime;
    }

////////////////////////////////////
// Get feed from DB - generic
////////////////////////////////////
async function getFeed(url) {
    const res = await fetch(url);
    const obj = await res.json();
    return obj;
    }

//////////////////////////////////////////////
// Ger OpenWeather location and weather data
//////////////////////////////////////////////
async function getCoords(zipcode, country, ow_api_key) {
    geo_url = "https://api.openweathermap.org/geo/1.0/zip?zip="+zipcode+","+country+"&appid="+ow_api_key;
    let data = (await getFeed(geo_url));
    return [data["lat"], data["lon"]];
    }

async function getOM(coords) {
    DEFAULT_MISSING = "--";
    
    aqi_om_url = "https://air-quality-api.open-meteo.com/v1/air-quality?latitude="+coords[0]+"&longitude="+coords[1];
    
    let omNowData = (await getFeed(aqi_om_url+"&current=us_aqi,pm10,pm2_5,uv_index,ozone,carbon_dioxide,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ammonia,methane"))
    
    let omNextData = (await getFeed(aqi_om_url+"&forecast_days=2&hourly=us_aqi,pm10,pm2_5,uv_index,ozone,carbon_dioxide,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ammonia,methane"))

    let r = {};
    r.aqi_now = omNowData["current"]["us_aqi"];
    r.uvi_now = omNowData["current"]["uv_index"];
    r.co = omNowData["current"]["carbon_monoxide"];
    r.co2 = omNowData["current"]["carbon_dioxide"];
    r.no2 = omNowData["current"]["nitrogen_dioxide"];
    r.o3 = omNowData["current"]["ozone"];
    r.so2 = omNowData["current"]["sulphur_dioxide"];
    r.pm2_5 = omNowData["current"]["pm2_5"];
    r.pm10 = omNowData["current"]["pm10"];
    r.nh3 = omNowData["current"]["ammonia"];
    r.ch4 = omNowData["current"]["methane"];
    r.dust = omNowData["current"]["dust"];
    r.aqi_next = omNextData["hourly"]["us_aqi"][36];
    r.uvi_next = omNextData["hourly"]["uv_index"][36];
    r.co_next = omNextData["hourly"]["carbon_monoxide"][36];
    r.co2_next = omNextData["hourly"]["carbon_dioxide"][36];
    r.no2_next = omNextData["hourly"]["nitrogen_dioxide"][36];
    r.o3_next = omNextData["hourly"]["ozone"][36];
    r.so2_next = omNextData["hourly"]["sulphur_dioxide"][36];
    r.pm2_5_next = omNextData["hourly"]["pm2_5"][36];
    r.pm10_next = omNextData["hourly"]["pm10"][36];
    r.nh3_next = omNextData["hourly"]["ammonia"][36]
    r.ch4_next = omNextData["hourly"]["methane"][36];
    
    const keys = Object.keys(r);
    for (var i = 0; i < keys.length; i++) {
        if (typeof r[keys[i]] !== 'number' || r[keys[i]] === null || r[keys[i]] === undefined) {
            r[keys[i]] = DEFAULT_MISSING;
        }}
    console.log("Open-meteo: ");
    console.log(r);
    return r;
    }
    
////////////////////////////////////
// Get NWS data
////////////////////////////////////
async function getNWS(coords) {
    om_weather_url = "https://api.open-meteo.com/v1/forecast?latitude="+coords[0]+"&longitude="+coords[1];
    
    let omNowData = (await getFeed(om_weather_url+"&current=temperature_2m,relative_humidity_2m,dew_point_2m,apparent_temperature,wet_bulb_temperature_2m,weather_code,surface_pressure,visibility"))
    nws_coords_url = "https://api.weather.gov/points/"+coords[0]+","+coords[1]
    let coordData = (await getFeed(nws_coords_url));
    nws_stations_url = coordData["properties"]["observationStations"]
    console.log(nws_stations_url);
    let stationData = (await getFeed(nws_stations_url));
    console.log(stationData["features"][0]["id"]);
    nws_url = stationData["features"][0]["id"]+"/observations/latest/";

    let data = (await getFeed(nws_url));
    let r = {};
    
    let keys = [
            'temperature',
            'heatIndex',
            'relativeHumidity',
            'seaLevelPressure',
            'dewpoint',
            'visibility',
        ];
    
    let om_keys = [
            'temperature_2m',
            'apparent_temperature',
            'relative_humidity_2m',
            'surface_pressure',
            'dew_point_2m',
            'visibility',
        ];
    
    DEFAULT_MISSING = "--";
    let full_defaults_list = [DEFAULT_MISSING] * keys.length;
        
    let formats_map = {
            'temperature': 1,
            'heatIndex': 1,
            'relativeHumidity': 0,
            'seaLevelPressure': 0,
            'dewpoint': 1,
            'visibility': 0,
        };
    
    let units_map = {
            'temperature': 1,
            'heatIndex': 1,
            'relativeHumidity': 1,
            'seaLevelPressure': 100,
            'dewpoint': 1,
            'visibility': 1,
        };
    
    for (var i = 0; i < keys.length; i++) {
        var format_str = formats_map[keys[i]];
        var units_str = units_map[keys[i]];
        var d = data['properties'][keys[i]]['value'];
        var d_om = omNowData['current'][om_keys[i]];
        if (typeof d === 'number' && d !== null && d !== undefined) {
            r[keys[i]] = (d/units_str).toFixed(format_str);
            }
        else{
            r[keys[i]] = (d_om).toFixed(format_str);
        }}
    r.wetbulb = omNowData['current']['wet_bulb_temperature_2m'];
    r.stationName = data['properties']['stationName'];
    let weather_list = data['properties']['presentWeather'];

    if (weather_list && weather_list.length > 0) {
        weather_value = weather_list[0]['weather'];
            if (weather_value != null) {
                r.presentWeather = weather_value;
                }
            else {
                r.presentWeather = getWeatherDescription(omNowData['current']['weather_code']);
                }
        }
    else {
        r.presentWeather = getWeatherDescription(omNowData['current']['weather_code']);
        }
    return r;
    }

//////////////////////////////////////////////
// Ger Local Data from Pico
//////////////////////////////////////////////
async function fetchData() {
    try {
        const response = await fetch('/api/status');
        const data = await response.json();
        return data;
        
    } catch (error) {
        console.error('Error fetching status:', error);
        document.getElementById("warnLabel").textContent = "Error: Check connection.";
        // Re-enable buttons even on error, so user can try again
        document.getElementById("Submit").disabled = false;
        document.getElementById("Status").disabled = false;
    }
}
//////////////////////////////////////////////
// Logic when pushing Update Status button
//////////////////////////////////////////////
async function updateStatus(getCoordsFlag) {
    document.getElementById("Submit").value = "Door \n\n Loading...";
    document.getElementById("Status").value = "Loading...";
    //document.getElementById("warnLabel").textContent = "Testing";
    
    datetime = getCurrentDateTime();
    data = await fetchData();
    console.log(data);
    
    let coords = await getCoords(data.zipcode, data.country, data.ow_api_key);
    
    base_forecast_url = "https://forecast.weather.gov/MapClick.php?lat="+coords[0]+"&lon="+coords[1];
    nws = await getNWS(coords);
    //aqi = await getOW(coords, data.ow_api_key);
    aqi = await getOM(coords);
    
    
    //document.getElementById("door_status").textContent = data.state;
    document.getElementById("Submit").value = "Door \n\n" + data.state;
    document.getElementById("Submit").style.backgroundColor = data.button_color;
    document.getElementById("Status").style.backgroundColor = "navy";

    document.getElementById("locTemp").textContent = data.locTemp;
    document.getElementById("remoteTemp").textContent = data.remoteTemp;
    document.getElementById("locRH").textContent = "--";
    document.getElementById("remoteRH").textContent = data.remoteRH;

    document.getElementById("station").innerHTML = "<a href='"+base_forecast_url+"'>"+nws.stationName+"</a>";
    
    document.getElementById("ext_temperature").textContent = nws.temperature+" \u00b0C";
    document.getElementById("ext_RH").textContent = nws.relativeHumidity+" %";
    
    const pollutantMap = [
    { idSuffix: "aqi_now", aqiProp: "aqi_now", colorRanges: aqiColorRanges },
    { idSuffix: "aqi_next", aqiProp: "aqi_next", colorRanges: aqiColorRanges },
    { idSuffix: "uvi_now", aqiProp: "uvi_now", colorRanges: uvColorRanges },
    { idSuffix: "uvi_next", aqiProp: "uvi_next", colorRanges: uvColorRanges },
    { idSuffix: "co", aqiProp: "co", colorRanges: coColorRanges },
    { idSuffix: "co2", aqiProp: "co2" }, // co2 does not appear to have a color change
    { idSuffix: "no2", aqiProp: "no2", colorRanges: no2ColorRanges },
    { idSuffix: "o3", aqiProp: "o3", colorRanges: o3ColorRanges },
    { idSuffix: "so2", aqiProp: "so2", colorRanges: so2ColorRanges },
    { idSuffix: "pm2_5", aqiProp: "pm2_5", colorRanges: pm2_5ColorRanges },
    { idSuffix: "pm10", aqiProp: "pm10", colorRanges: pm10ColorRanges },
    { idSuffix: "nh3", aqiProp: "nh3", colorRanges: null },
    { idSuffix: "ch4", aqiProp: "ch4", colorRanges: null },
    { idSuffix: "dust", aqiProp: "dust", colorRanges: null },
    ];
    
    pollutantMap.forEach(pollutant => {
    const element = document.getElementById("ext_" + pollutant.idSuffix);
    if (element && aqi[pollutant.aqiProp] !== undefined) {
        element.textContent = aqi[pollutant.aqiProp];

        if (pollutant.colorRanges) {
            if (typeof getColor === 'function') {
                element.style.color = getColor(aqi[pollutant.aqiProp], pollutant.colorRanges);
            }
        }
    } else if (element) {
        element.textContent = 'N/A';
    }
    });
    
    document.getElementById("ext_pressure").textContent = nws.seaLevelPressure+" mbar";
    document.getElementById("ext_heatindex").textContent = nws.heatIndex+" \u00b0C";
    document.getElementById("ext_weather").textContent = nws.presentWeather;
    document.getElementById("ext_visibility").textContent = nws.visibility+" m";
    document.getElementById("ext_dewpoint").textContent = nws.dewpoint+" \u00b0C";
    document.getElementById("ext_wetbulb").textContent = nws.wetbulb+" \u00b0C";

    document.getElementById("datetime").textContent = datetime;
    document.getElementById("ip_address").textContent = data.ip;
    document.getElementById("version").textContent = data.version;

    //document.getElementById("warnLabel").textContent = "Update Status: \n Ready";
    document.getElementById("Status").value = "Update";
    document.getElementById("warnLabel").textContent = "";
    document.getElementById("Submit").disabled = false;
    document.getElementById("Status").disabled = false;
}

//////////////////////////////////////////////
// Logic when pushing Door Status
//////////////////////////////////////////////
function waitWarn(a) {
    //document.getElementById("warnLabel").innerHTML = "Please wait...";
    document.getElementById("Status").disabled = true;
    document.getElementById("Status").style.backgroundColor = "#155084";

    if (a === 0) {
        document.getElementById("Submit").disabled = true;
        document.getElementById("Submit").style.backgroundColor = "#155084";
        fetch('./run') // Use fetch for the run command
            .then(response => {
                if (response.ok) {
                    console.log("Run control successful.");
                    setTimeout(updateStatus, 1000, "True");
                } else {
                    throw new Error('Run command failed.');
                }
            })
            .catch(error => {
                console.error('Run Error:', error);
                document.getElementById("warnLabel").textContent = "Error during RUN.";
                updateStatus(); // Re-enable buttons
            });
    } else if (a === 1) {
        updateStatus("True");
    }
}
document.addEventListener('DOMContentLoaded', updateStatus);
setInterval(updateStatus, 30000, "False");

//////////////////////////////////////////////
// Utilities
//////////////////////////////////////////////
function getColor(value, ranges, defaultColor = 'white') {
    // Iterate through the array of range definitions
    for (const range of ranges) {
        if (value >= range.min && value <= range.max) {
            return range.color; // Return the color for the first matching range
        }
    }
    return defaultColor;
}

const aqiColorRanges = [
    { min: 0, max: 50, color: "green" },
    { min: 51, max: 100, color: "yellow" },
    { min: 101, max: 150, color: "orange" },
    { min: 151, max: 200, color: "red" },
    { min: 201, max: 300, color: "brown" },
    { min: 301, max: 1000, color: "purple" }
];

const coColorRanges = [
    { min: 0, max: 4500, color: "green" },
    { min: 4500, max: 9500, color: "yellow" },
    { min: 9500, max: 12500, color: "orange" },
    { min: 12500, max: 15500, color: "red" },
    { min: 15500, max: 30500, color: "brown" },
    { min: 30500, max: 1e8, color: "purple" }
];

const no2ColorRanges = [
    { min: 0, max: 54, color: "green" },
    { min: 54, max: 100, color: "yellow" },
    { min: 100, max: 360, color: "orange" },
    { min: 360, max: 650, color: "red" },
    { min: 650, max: 1250, color: "brown" },
    { min: 1250, max: 1e8, color: "purple" }
];

const o3ColorRanges = [
    { min: 0, max: 55, color: "green" },
    { min: 55, max: 70, color: "yellow" },
    { min: 70, max: 85, color: "orange" },
    { min: 85, max: 105, color: "red" },
    { min: 105, max: 200, color: "brown" },
    { min: 200, max: 1e8, color: "purple" }
];

const so2ColorRanges = [
    { min: 0, max: 35, color: "green" },
    { min: 35, max: 75, color: "yellow" },
    { min: 75, max: 185, color: "orange" },
    { min: 185, max: 305, color: "red" },
    { min: 305, max: 350, color: "brown" },
    { min: 350, max: 1e8, color: "purple" }
];

const pm2_5ColorRanges = [
    { min: 0, max: 12, color: "green" },
    { min: 12, max: 35.5, color: "yellow" },
    { min: 35.5, max: 55.5, color: "orange" },
    { min: 55.5, max: 150.5, color: "red" },
    { min: 150.5, max: 250.5, color: "brown" },
    { min: 250.5, max: 1e8, color: "purple" }
];

const pm10ColorRanges = [
    { min: 0, max: 55, color: "green" },
    { min: 55, max: 155, color: "yellow" },
    { min: 155, max: 255, color: "orange" },
    { min: 255, max: 355, color: "red" },
    { min: 355, max: 425, color: "brown" },
    { min: 435, max: 1e8, color: "purple" }
];

const uvColorRanges = [
    { min: 0, max: 2.5, color: "green" },
    { min: 2.5, max: 3.5, color: "yellow" },
    { min: 3.5, max: 5.5, color: "orange" },
    { min: 5.5, max: 7.5, color: "red" },
    { min: 7.5, max: 10.5, color: "brown" },
    { min: 10.5, max: 1e8, color: "purple" }
];

/**
 * Converts a numerical weather code into a descriptive weather string.
 * This is based on the WMO (World Meteorological Organization) weather codes.
 */
function getWeatherDescription(code) {
  if (typeof code !== 'number') {
    return 'Invalid input: Code must be a number.';
  }
  switch (code) {
    case 0: return 'Clear sky';
    case 1: return 'Mainly clear';
    case 2: return 'Partly cloudy';
    case 3: return 'Overcast';
    case 45: return 'Fog';
    case 48: return 'Depositing rime fog';
    case 51: return 'Light drizzle';
    case 53: return 'Moderate drizzle';
    case 55: return 'Dense drizzle';
    case 56: return 'Light freezing drizzle';
    case 57: return 'Dense freezing drizzle';
    case 61: return 'Slight rain';
    case 63: return 'Moderate rain';
    case 65: return 'Heavy rain';
    case 66: return 'Light freezing rain';
    case 67: return 'Heavy freezing rain';
    case 71: return 'Slight snow fall';
    case 73: return 'Moderate snow fall';
    case 75: return 'Heavy snow fall';
    case 77: return 'Snow grains';
    case 80: return 'Slight rain showers';
    case 81: return 'Moderate rain showers';
    case 82: return 'Violent rain showers';
    case 85: return 'Slight snow showers';
    case 86: return 'Heavy snow showers';
    case 95: return 'Thunderstorm: Slight or moderate';
    case 96: return 'Thunderstorm with slight hail';
    case 99: return 'Thunderstorm with heavy hail';
    default: return 'Unknown weather code';
  }
}
