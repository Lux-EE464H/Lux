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
import pprint
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

min_in_day = 24 * 60


def init_resources():
    if not os.path.isdir(resources_dir_path):
        os.makedirs(resources_dir_path)

    if not os.path.exists(config_path):
        raise FileNotFoundError("Config file missing in resources directory")

    if not os.path.exists(user_input_path):
        open(user_input_path, "x")

    if not os.path.exists(last_input_path):
        open(last_input_path, "x")

    with open(config_path, "r") as f:
        data = json.load(f)

        if "lifx_token" not in data or not data["lifx_token"]:
            raise ValueError("Missing LIFX token in config")

        if "delta_e" not in data or not data["delta_e"]:
            raise ValueError("Missing deltaE in config")

        if "decay_rate" not in data or not data["decay_rate"]:
            raise ValueError("Missing decay rate in config")

        return data


def parse_time():
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

    LOG.info("Parsed time for t_cos: {}, t_sin: {}, and meridiem: {}".format(t_cos, t_sin, meridiem))
    return [t_cos, t_sin, meridiem]


def get_prediction():
    t = parse_time()
    p = p_api.predict([0] + t)
    LOG.info("Predicted lighting: {}".format(pprint.pformat(p)))
    return p


def update_mls(hsbk):
    rgb = colorsys.hsv_to_rgb(hsbk['h'] / 360, hsbk['s'], hsbk['b'])
    LOG.info("Updating MLS model with {}".format(pprint.pformat(rgb)))
    t = parse_time()
    p_api.update([[rgb[0]*255, rgb[1]*255, rgb[2]*255]] + t)


def is_same_hsbk(c1, c2):
    if abs(c1['h'] - c2['h']) <= 1 \
            and abs(c1['s'] - c2['s']) <= 1 \
            and abs(c1['b'] - c2['b']) <= 1 \
            and abs(c1['k'] - c2['k']) <= 1:
        return True
    return False

def get_lighting(token):
    res = lifx.get_lights(token)
    lights = {}

    for l in res['data']:
        lights[l['id']] = {"h": l['color']['hue'],
                           "s": l['color']['saturation'],
                           "k": l['color']['kelvin'],
                           "b": l['brightness'],
                           "connected": l['connected']}
    majority = {}
    maximum = ({},0)
    for l_id, light in lights.items():
        if light['connected'] == True:
            if l_id in majority and is_same_hsbk(light, majority[l_id]):
                majority[l_id] += 1
            elif l_id not in majority:
                majority[l_id] = 1

            if majority[l_id] > maximum[1]:
                maximum = (light, majority[l_id])
            #LOG.info("from API: {}".format(pprint.pformat(res['data'][0])))
    LOG.info("Selected lighting configuration: {}".format(pprint.pformat(maximum[0])))
    return maximum[0]


def validate_lighting(predicted, current, threshold):
    c1_rgb = colorsys.hsv_to_rgb(current['h'] / 360, current['s'], current['b'])

    c1 = sRGBColor(c1_rgb[0], c1_rgb[1], c1_rgb[2])
    c2 = sRGBColor(predicted['r'] / 255.0, predicted['g'] / 255.0, predicted['b'] / 255.0)

    print("c1 is " + str(c1) + " and c2 is " + str(c2))

    de = delta_e_cie2000(convert_color(c1, LabColor), convert_color(c2, LabColor))
    LOG.info("delta_e: {} is within valid range: {}".format(de, de < threshold))
    return de < threshold


def check_last(hsbk):
    with open(last_input_path, 'r') as f:
        data = json.loads(f.read())
        print("HSBK currently is: " + str(hsbk) + " and Last Time's input is: " + str(data))
        return is_same_hsbk(hsbk, data)


def get_user_input():
    with open(user_input_path, 'r') as f:
        if os.path.getsize(user_input_path) == 0:
            return None
        return json.loads(f.read())


def blend_color_component(c_mls, c_user, t):
    # Algorithm: http://stackoverflow.com/questions/726549/algorithm-for-additive-color-mixing-for-rgb-values
    return math.sqrt(((1 - t) * (c_mls ** 2)) + (t * (c_user ** 2)))

def blend_with_white(white_component, target_component, t):
    return ((t * white_component) + ((1-t) * target_component))

def incorporate(mls, clouds, user):
    if user is not None:
        c_user = colorsys.hsv_to_rgb(user['h'] / 360, user['s'], user['b'])
        #if user['weight'] >= 0.5:
        #    white_prop = 2*(1-user['weight'])
        #    mls['r'] = blend_with_white(230.0, c_user[0] / 255, white_prop)
        #    mls['g'] = blend_with_white(255.0, c_user[1] / 255, white_prop)
        #    mls['b'] = blend_with_white(255.0, c_user[2] / 255, white_prop)
       # else:
        white_prop = user['weight']
        #print("\nCHECK C_USER: " + str(c_user[0]) + "," + str(c_user[1]) + "," + str(c_user[2]))
        mls['r'] = blend_with_white(c_user[0] * 255.0, mls['r'], white_prop)
        mls['g'] = blend_with_white(c_user[1] * 255.0, mls['g'], white_prop)
        mls['b'] = blend_with_white(c_user[2] * 255.0, mls['b'], white_prop)
        #print("\nCHECK Blended: " + str(mls['r']) + "," + str(mls['g']) + "," + str(mls['b']))    
    mls['brightness'] = round(clouds / 2 + 0.5, 1)
    return mls


def update_last_input(hsbk):
    with open(last_input_path, 'w') as f:
        json.dump(hsbk, f)


def update_user_input():
    if os.path.getsize(user_input_path) == 0:
        return
    with open(user_input_path, 'r+') as f:
        data = json.loads(f.read())
        f.seek(0, 0)
        f.truncate()
        decay = data['decay']
        #data['decay'] = (decay * 10)
        data["weight"] = 0 if data['weight'] - decay <= 0 else data['weight'] - decay
        json.dump(data, f)


def init_user_input(hsbk, decay):
    with open(user_input_path, 'w') as f:
        hsbk['weight'] = 1.0
        hsbk['decay'] = decay
        json.dump(hsbk, f)


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


def is_initial_cycle():
    return os.path.getsize(last_input_path) == 0

def main():
    config = init_resources()

    current = get_lighting(config['lifx_token'])
    predicted = get_prediction()
    clouds = w_api.current_cloud_coverage()

    if not is_initial_cycle():
        # user changed lighting last cycle
        if not check_last(current):
            print("Initializing user input")
            init_user_input(current, config['decay_rate'])

        # update MLS if within threshold
        if validate_lighting(predicted, current, config['delta_e']):
            update_mls(current)

        update_user_input()

    user_input = get_user_input()
    incorporated = incorporate(predicted, clouds, user_input)

    post_to_bulbs(config['lifx_token'], incorporated, 3)
    time.sleep(1)
    update_last_input(get_lighting(config['lifx_token']))


if __name__ == '__main__':
    main()
