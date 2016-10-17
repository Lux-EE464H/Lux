import forecastio
import datetime

api_key = "bc9ae0f9d78df618dad04b8b95410a5a"
lat = 30.2672
lng = -97.7431

forecast = forecastio.load_forecast(api_key, lat, lng)
byDay = forecast.daily()

# subtract offset from GMT to CST
print byDay.data[0].sunsetTime - datetime.timedelta(hours=5)
return byDay.data[0].sunsetTime - datetime.timedelta(hours=5)