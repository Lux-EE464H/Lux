from prediction_api import predict as p_api
from lifx_api import lifx_api_lib as lifx
import datetime
import math

totalMins = 24*60

currentTime = datetime.datetime.now()
hours = currentTime.strftime('%H')
hours = int(hours)
minutes = currentTime.strftime('%M')
minutes = int(minutes)

print("------ cycle -------")
print("")
minutesAfterMidnight = hours*60 + minutes
minutesPastNoon = (minutesAfterMidnight + (60*12)) % (24*60)
print("Timestamp:" + str(currentTime))
print("Minutes Past Noon: " + str(minutesPastNoon))

timeCosValue = math.cos(minutesPastNoon*(2*math.pi/totalMins))
timeSinValue = math.sin(minutesPastNoon*(2*math.pi/totalMins))
if(abs(timeCosValue) < 0.0000000001):
    timeCosValue = 0.0
if(abs(timeSinValue) < 0.0000000001):
    timeSinValue = 0.0

if(minutesPastNoon > 720):
    meridiem = "AM"
else:
    meridiem = "PM"

print ('Cos: ' + str(timeCosValue))
print ('Sin: ' + str(timeSinValue))
print ('AM or PM: ' + meridiem)

args = [114.36, -0.9396926, 0.3420202, "PM"]
#args = [0, timeCosValue, timeSinValue, meridiem]
#lifx.set_color("c3c602e1e2bff14e7889f9f442d685d81abc184b232f10d63a36bcf4a616c9c6", p_api.predict(args))
print(p_api.update(args))

print("")
print("------ endcycle -------")
print("")
