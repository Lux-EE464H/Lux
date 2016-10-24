import requests
import logging
import sys
import pprint

FORMAT = "%(asctime)-15s - %(levelname)s - %(module)20s:%(lineno)-5d - %(message)s"
logging.basicConfig(stream=sys.stdout, level=logging.INFO, format=FORMAT)
LOG = logging.getLogger(__name__)


# Verifies whether a color string is valid for Lifx bulbs
def __validate_color(token, color):

    header = {
        "Authorization": "Bearer %s" % token,
    }

    request = {
        "string": color
    }

    LOG.info("Validating color --- {}".format(request))
    response = requests.get('https://api.lifx.com/v1/color', data=request, headers=header)
    LOG.debug("Validate color response: {}".format(response.status_code))

    if response.status_code == 200:
        return True
    return False


# Sets color for all lights associated with access token
# Optionally, specify a group to set color for only those lights
def set_color(token, color, brightness=1.0, select="all"):

    if not __validate_color(token, color):
        raise ValueError("Invalid color value. Refer to Lifx API documentation for valid colors.")

    header = {
        "Authorization": "Bearer %s" % token,
    }

    request = {
        "color": color,
        "brightness": brightness
    }

    LOG.info("Setting colors for selector [{}] to color [{}]".format(select, request))
    r = requests.put('https://api.lifx.com/v1/lights/{}/state'.format(select), data=request, headers=header)
    response = {"status": r.status_code,
                "data": r.json()}
    LOG.debug("Set color response:\n{}".format(pprint.pformat(response)))
    return response


# Gets state for lights
# Can optionally select a group of lights
def get_lights(token, select="all"):

    headers = {
        "Authorization": "Bearer %s" % token,
    }

    LOG.info("Getting lights for selector [{}]".format(select))
    r = requests.get('https://api.lifx.com/v1/lights/{}'.format(select), headers=headers)
    response = {"status": r.status_code,
                "data": r.json()}
    LOG.debug("List lights response:\n{}".format(pprint.pformat(response)))
    return response


