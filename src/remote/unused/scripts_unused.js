let coords = null;

//////////////////////////////////////////////
// Ger OpenWeather location and weather data
//////////////////////////////////////////////
async function getOW(coords, ow_api_key) {
    DEFAULT_MISSING = "--";
    
    aqi_current_url = "https://api.openweathermap.org/data/2.5/air_pollution?lat="+coords[0]+"&lon="+coords[1]+"&appid="+ow_api_key;
        aqi_forecast_url = "https://api.openweathermap.org/data/2.5/air_pollution/forecast?lat="+coords[0]+"&lon="+coords[1]+"&appid="+ow_api_key;
    
    let data = (await getFeed(aqi_current_url))["list"][0];
    
    let r = {};
    r.aqi_now = data["main"]["aqi"];
    r.uvi = DEFAULT_MISSING;
    r.co = data["components"]["co"];
    r.co2 = DEFAULT_MISSING;
    r.no = data["components"]["no"];
    r.no2 = data["components"]["no2"];
    r.o3 = data["components"]["o3"];
    r.so2 = data["components"]["so2"];
    r.pm2_5 = data["components"]["pm2_5"];
    r.pm10 = data["components"]["pm10"];
    r.nh3 = data["components"]["bh3"];
    r.ch4 = DEFAULT_MISSING;
    r.dust = DEFAULT_MISSING;
    r.aqi_pred = (await getFeed(aqi_forecast_url))["list"][24]["main"]["aqi"];
    
    const keys = Object.keys(r);
    for (var i = 0; i < keys.length; i++) {
        if (typeof r[keys[i]] !== 'number' || r[keys[i]] === null || r[keys[i]] === undefined) {
            r[keys[i]] = DEFAULT_MISSING;
        }}
    console.log("Openweathermap: ");
    console.log(r);
    return r;
    }


