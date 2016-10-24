from prediction_api import predict as p_api
from lifx_api import lifx_api_lib as lifx
from forecast_api import hourly_forecast as w_api
import datetime
import math
import sys
import os
import json
import logging
import pprint
import colorsys
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

FORMAT = "%(asctime)-15s - %(levelname)s - %(module)20s:%(lineno)-5d - %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FORMAT)
LOG = logging.getLogger(__name__)

# totalMins = 24*60
#
# currentTime = datetime.datetime.now()
# hours = currentTime.strftime('%H')
# hours = int(hours)
# minutes = currentTime.strftime('%M')
# minutes = int(minutes)
#
# print("------ cycle -------")
# print("")
# minutesAfterMidnight = hours*60 + minutes
# minutesPastNoon = (minutesAfterMidnight + (60*12)) % (24*60)
# print("Timestamp:" + str(currentTime))
# print("Minutes Past Noon: " + str(minutesPastNoon))
#
# timeCosValue = math.cos(minutesPastNoon*(2*math.pi/totalMins))
# timeSinValue = math.sin(minutesPastNoon*(2*math.pi/totalMins))
# if(abs(timeCosValue) < 0.0000000001):
#     timeCosValue = 0.0
# if(abs(timeSinValue) < 0.0000000001):
#     timeSinValue = 0.0
#
# if(minutesPastNoon > 720):
#     meridiem = "AM"
# else:
#     meridiem = "PM"
#
# print ('Cos: ' + str(timeCosValue))
# print ('Sin: ' + str(timeSinValue))
# print ('AM or PM: ' + meridiem)
#
# args = [114.36, -0.9396926, 0.3420202, "PM"]
# #args = [0, timeCosValue, timeSinValue, meridiem]
# #lifx.set_color("c3c602e1e2bff14e7889f9f442d685d81abc184b232f10d63a36bcf4a616c9c6", p_api.predict(args))
# print(p_api.update(args))
#
# print("")
# print("------ endcycle -------")
# print("")

resources_dir_path = os.path.join(os.getcwd(), "resources")
config = os.path.join(resources_dir_path, "config.json")
user_input = os.path.join(resources_dir_path, "user_input.json")
last_input = os.path.join(resources_dir_path, "last_input.json")

min_in_day = 24 * 60
de_threshold = 20.0
decay = 0.1


def init_resources():
    LOG.info("Initializing resource directory and files")
    if not os.path.isdir(resources_dir_path):
        os.makedirs(resources_dir_path)

    if not os.path.exists(config):
        with open(config, "w") as f:
            f.write('{ "lifx_token" : "" }')
        raise FileNotFoundError("Must have config file. Creating it now.")

    if not os.path.exists(user_input):
        LOG.info("Creating user_input.json")
        with open(user_input, 'w') as f:
            f.write('{ "r" : 0.0, "g" : 0.0, "b" : 0.0, "weight" : 0.0 }')

    if not os.path.exists(last_input):
        LOG.info("Creating last_input.json")
        with open(last_input, 'w') as f:
            f.write('{ "r" : 0.0, "g" : 0.0, "b" : 0.0 }')

    with open(config, "r") as f:
        data = json.load(f)
        if "lifx_token" not in data or not data["lifx_token"]:
            raise ValueError("Must have LIFX token in config")
        return data["lifx_token"]


def parse_time():
    LOG.info("Parsing time for cos, sin and meridiem")
    t = datetime.datetime.now()
    hours = int(t.strftime('%H'))
    minutes = int(t.strftime('%M'))

    minutes_after_midnight = hours * 60 + minutes
    minutes_past_noon = (minutes_after_midnight + (60 * 12)) % min_in_day

    t_cos = math.cos(minutes_past_noon * (2 * math.pi / min_in_day))
    t_sin = math.sin(minutes_past_noon * (2 * math.pi / min_in_day))
    if abs(t_cos) < 0.0000000001:
        t_cos = 0.0
    if abs(t_sin) < 0.0000000001:
        t_sin = 0.0

    if minutes_past_noon > 720:
        meridiem = "AM"
    else:
        meridiem = "PM"

    return [t_cos, t_sin, meridiem]


def get_prediction():
    LOG.info("Getting MLS prediction")
    t = parse_time()
    return p_api.predict([0] + t)


def update_mls(rgb):
    LOG.info("Updating MLS models with {}".format(rgb))
    t = parse_time()
    p_api.update([rgb] + t)


def get_lighting(token):
    LOG.info("Getting current lighting configuration")
    res = lifx.get_lights(token)
    lights = [{
                "hue": l['color']['hue'],
                "saturation": l['color']['saturation'],
                "brightness": l['brightness'],
                "id": l['id']
              } for l in res['data']]

    majority = {}
    maximum = ('', 0)
    for light in lights:
        if light['id'] in majority:
            majority[light['id']] += 1
        else:
            majority[light['id']] = 1

        if majority[light['id']] > maximum[1]:
            maximum = (light, majority[light['id']])

    rgb = colorsys.hsv_to_rgb(maximum[0]['hue'] / 360.0,
                              maximum[0]['saturation'],
                              maximum[0]['brightness'])
    return [c * 255 for c in rgb]


def validate_lighting(predicted, current):
    LOG.info("Validating current: {} with predicted: {}".format(current, predicted))
    p_rgb = predicted.split(',')
    p_rgb = [float(p) / 255 for p in p_rgb]

    c1 = sRGBColor(p_rgb[0], p_rgb[1], p_rgb[2])
    c2 = sRGBColor(current[0] / 255, current[1] / 255, current[2] / 255)

    de = delta_e_cie2000(convert_color(c1, LabColor), convert_color(c2, LabColor))
    LOG.info("delta_e: {}".format(de))
    return de < de_threshold


def check_last(rgb):
    LOG.info("Comparing previous CCH input with current")
    with open(last_input, 'r') as f:
        data = json.load(f)
        r = rgb[0] == data['r']
        g = rgb[1] == data['g']
        b = rgb[2] == data['b']
    return r and g and b


def get_user_input():
    with open(user_input, 'r') as f:
        return json.load(f)


def get_weather():
    None


def incorporate(mls, weather, user):
    None


def main():
    # get lighting config
    # validate lighting (threshold & outlier)
    #   if valid, update MLS
    # if lighting same as previous cycle
    #   if user input does not exist
    #       get and incorporate MLS prediction and weather data
    #       save to last_input.json
    #       post to bulbs
    #           exponential back off if failed
    #   else user input exists
    #       get value from user_input.json
    #       get and incorporate MLS prediction, weather data, and user input
    #       decay if not 0 then save to user_input.json
    #       else decay is 0, then clear user_input.json
    #       save to last_input.json
    #       post to bulbs
    #           exponential back off if failed
    # else user just changed lights
    #   initialize user_input.json with color and 0.9 weight
    #   get and incorporate MLS prediction, weather data, and user input
    #   save to last_input.json
    #   post to bulbs
    #       exponential back off if failed

    lifx_token = init_resources()
    rgb = get_lighting(lifx_token)
    p = get_prediction()
    valid = validate_lighting(p.split(':')[1], rgb)

    if valid:
        update_mls(rgb)

    # user did not change lighting last cycle
    if check_last(rgb):
        u_input = get_user_input()
        w_data = w_api.get_current_weather()

    # user changed lighting last cycle
    else:
        w_data = w_api.get_current_weather()


if __name__ == '__main__':
    main()
