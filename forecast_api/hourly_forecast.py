import forecastio

api_key = "bc9ae0f9d78df618dad04b8b95410a5a"
lat = 30.2672
lng = -97.7431

forecast = forecastio.load_forecast(api_key, lat, lng)


def get_forecast():
    hourly = forecast.hourly()
    return [hourly.data[x].summary for x in range(0, 24)]


def get_current_weather():
    wf = forecast.currently()
    print(wf.icon)
    return wf.icon
