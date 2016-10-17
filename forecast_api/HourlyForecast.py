import forecastio

api_key = "bc9ae0f9d78df618dad04b8b95410a5a"
lat = 30.2672
lng = -97.7431

forecast = forecastio.load_forecast(api_key, lat, lng)

byHour = forecast.hourly()
hourlySummary = ["" for x in range(24)]

for i in range(0, 24):
	hourlySummary[i] = byHour.data[i].summary
	print byHour.data[i].summary


