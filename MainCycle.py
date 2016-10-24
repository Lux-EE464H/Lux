from prediction_api import predict as p_api
from lifx_api import lifx_api_lib as lifx
from forecast_api import hourly_forecast as w_api
import datetime
import math
import sys
import os
import json
import time
import logging
import colorsys
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_conversions import convert_color
from colormath.color_diff import delta_e_cie2000

FORMAT = "%(asctime)-15s - %(levelname)s - %(module)20s:%(lineno)-5d - %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FORMAT)
LOG = logging.getLogger(__name__)

resources_dir_path = os.path.join(os.getcwd(), "resources")
config_path = os.path.join(resources_dir_path, "config.json")
user_input_path = os.path.join(resources_dir_path, "user_input.json")
last_input_path = os.path.join(resources_dir_path, "last_input.json")


def init_resources():
    LOG.info("Initializing resource directory and files")
    if not os.path.isdir(resources_dir_path):
        os.makedirs(resources_dir_path)

    if not os.path.exists(config_path):
        with open(config_path, "w") as f:
            data = {
                "lifx_token": "",
                "min_in_day": 1440,
                "de_threshold": 20.0,
                "decay": 0.1
            }
            json.dump(data, f)
        raise FileNotFoundError("Must have config file. Creating it now.")

    if not os.path.exists(user_input_path):
        LOG.info("Creating user_input.json")
        with open(user_input_path, 'w') as f:
            data = {
                "r": 0.0,
                "g": 0.0,
                "b": 0.0,
                "weight": 0.0
            }
            json.dump(data, f)

    if not os.path.exists(last_input_path):
        LOG.info("Creating last_input.json")
        with open(last_input_path, 'w') as f:
            data = {
                "r": 0.0,
                "g": 0.0,
                "b": 0.0
            }
            json.dump(data, f)

    with open(config_path, "r") as f:
        data = json.load(f)
        if "lifx_token" not in data or not data["lifx_token"]:
            raise ValueError("Must have LIFX token in config")
        return data


def parse_time(config):
    LOG.info("Parsing time for cos, sin and meridiem")
    t = datetime.datetime.now()
    hours = int(t.strftime('%H'))
    minutes = int(t.strftime('%M'))

    minutes_after_midnight = hours * 60 + minutes
    minutes_past_noon = (minutes_after_midnight + (60 * 12)) % config['min_in_day']

    t_cos = math.cos(minutes_past_noon * (2 * math.pi / config['min_in_day']))
    t_sin = math.sin(minutes_past_noon * (2 * math.pi / config['min_in_day']))
    if abs(t_cos) < 0.0000000001:
        t_cos = 0.0
    if abs(t_sin) < 0.0000000001:
        t_sin = 0.0

    if minutes_past_noon > 720:
        meridiem = "AM"
    else:
        meridiem = "PM"

    return [t_cos, t_sin, meridiem]


def get_prediction(config):
    LOG.info("Getting MLS prediction")
    t = parse_time(config)
    return p_api.predict([0] + t)


def update_mls(rgb, config):
    LOG.info("Updating MLS models with {}".format(rgb))
    t = parse_time(config)
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


def validate_lighting(predicted, current, config):
    LOG.info("Validating current: {} with predicted: {}".format(current, predicted))
    p_rgb = predicted.split(',')
    p_rgb = [float(p) / 255 for p in p_rgb]

    c1 = sRGBColor(p_rgb[0], p_rgb[1], p_rgb[2])
    c2 = sRGBColor(current[0] / 255, current[1] / 255, current[2] / 255)

    de = delta_e_cie2000(convert_color(c1, LabColor), convert_color(c2, LabColor))
    LOG.info("delta_e: {}".format(de))
    return de < config['de_threshold']


def check_last(rgb):
    LOG.info("Comparing previous CCH input with current")
    with open(last_input_path, 'r') as f:
        data = json.loads(f.read())
        r = rgb[0] == data['r']
        g = rgb[1] == data['g']
        b = rgb[2] == data['b']
    return r and g and b


def get_user_input():
    with open(user_input_path, 'r') as f:
        return json.loads(f.read())


def incorporate(mls, clouds, user):
    mls_rgb = mls.split(',')
    mls_rgb = [float(p) / 255 for p in mls_rgb]

    return {
        "r": (mls_rgb[0] * (1 - user['weight'])) + (user['r'] * user['weight']),
        "g": (mls_rgb[1] * (1 - user['weight'])) + (user['g'] * user['weight']),
        "b": (mls_rgb[2] * (1 - user['weight'])) + (user['b'] * user['weight']),
        "brightness": clouds / 2 + 0.5
    }


def update_last_input(rgb):
    with open(last_input_path, 'w') as f:
        data = {
            "r": rgb['r'],
            "g": rgb['g'],
            "b": rgb['b']
        }
        json.dump(data, f)


def update_user_input(rgb, config):
    with open(user_input_path, 'w') as f:
        data = {
            "r": rgb['r'],
            "g": rgb['g'],
            "b": rgb['b'],
            "weight": rgb['weight'] - config['decay']
        }
        json.dump(data, f)


def init_user_input(rgb):
    with open(user_input_path, 'w') as f:
        data = {
            "r": rgb[0],
            "g": rgb[1],
            "b": rgb[2],
            "weight": 0.9
        }
        json.dump(data, f)


def post_to_bulbs(token, rgb, retries, t=1, current=1):
    rgb_s = "rgb:{},{},{}".format(int(rgb['r']), int(rgb['g']), int(rgb['b']))
    res = lifx.set_color(token, rgb_s, rgb['brightness'])

    if res['status'] < 200 or res['status'] >= 300:
        if current > retries:
            LOG.error("Error posting to bulbs. Status={}".format(res['status']))
            return res

        LOG.info("Error posting to bulbs, retrying in {} seconds".format(t))
        time.sleep(t)
        return post_to_bulbs(token, rgb, retries, t=math.pow(2, current) - 1, current=current + 1)

    return res


def main():
    config = init_resources()
    current = get_lighting(config['lifx_token'])
    predicted = get_prediction(config)
    clouds = w_api.current_cloud_coverage()
    user_input = get_user_input()
    incorporated = incorporate(predicted.split(':')[1], clouds, user_input)

    # update MLS if within threshold
    if validate_lighting(predicted.split(':')[1], current, config):
        update_mls(current, config)

    # user changed lighting last cycle
    if not check_last(current):
        init_user_input(current)

    update_last_input(incorporated)
    update_user_input(user_input, config)
    post_to_bulbs(config['lifx_token'], incorporated, 3)


if __name__ == '__main__':
    main()
