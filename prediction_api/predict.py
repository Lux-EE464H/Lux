#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2014 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Interface for Lux predictions to Google Prediction API
"""
from __future__ import print_function

import argparse
import os
import pprint
import sys
import time

from apiclient import discovery
from apiclient import sample_tools
from oauth2client import client

# Global instance of the Prediction API
pAPI = None

# Declare command-line flags.
# argparser = argparse.ArgumentParser(add_help=False)
# argparser.add_argument('object_name',
#     help='Full Google Storage path of csv data (ex bucket/object)')
# argparser.add_argument('model_id',
#     help='Model Id of your choosing to name trained model')
# argparser.add_argument('project_id',
#     help='Model Id of your choosing to name trained model')


def print_header(line):
  '''Format and print header block sized to length of line'''
  header_str = '='
  header_line = header_str * len(line)
  print('\n' + header_line)
  print(line)
  print(header_line)

def predictRed(tcos, tsin, meridiem):
    body = {'input': {'csvInstance': [tcos,tsin,meridiem]}}
    result = pAPI.predict(
      body=body, id="lux-r", project="lux-simulation-gb").execute()
    return float((result['outputValue']).replace("'",""))

def predictGreen(tcos, tsin, meridiem):
    body = {'input': {'csvInstance': [tcos,tsin,meridiem]}}
    result = pAPI.predict(
      body=body, id="lux-g", project="lux-simulation-gb").execute()
    return float((result['outputValue']).replace("'",""))

def predictBlue(tcos, tsin, meridiem):
    body = {'input': {'csvInstance': [tcos,tsin,meridiem]}}
    result = pAPI.predict(
      body=body, id="lux-b", project="lux-simulation-gb").execute()
    return float((result['outputValue']).replace("'",""))

def updateRed(outputVal, tcos, tsin, meridiem):
    body = {'output': outputVal, 'csvInstance':[tcos,tsin,meridiem]}
    result = pAPI.update(
      body=body, id="lux-r", project="lux-simulation-gb").execute()
    return result

def updateGreen(outputVal, tcos, tsin, meridiem):
    body = {'output': outputVal, 'csvInstance':[tcos,tsin,meridiem]}
    result = pAPI.update(
      body=body, id="lux-g", project="lux-simulation-gb").execute()
    return result

def updateBlue(outputVal, tcos, tsin, meridiem):
    body = {'output': outputVal, 'csvInstance':[tcos,tsin,meridiem]}
    result = pAPI.update(
      body=body, id="lux-b", project="lux-simulation-gb").execute()
    return result

def predict(argv):

  if len(argv) != 4:
    print("Error -- invalid number of arguments.\n Usage:\n >> python predict.py <time cosine value> <time sine value> <meridiem>")
    raise SyntaxError()
    
  # If you previously ran this app with an earlier version of the API
  # or if you change the list of scopes below, revoke your app's permission
  # here: https://accounts.google.com/IssuedAuthSubTokens
  # Then re-run the app to re-authorize it.
  service, flags = sample_tools.init(
      argv[:1], 'prediction', 'v1.6', __doc__, __file__,
      scope=(
          'https://www.googleapis.com/auth/prediction',
          'https://www.googleapis.com/auth/devstorage.read_only'))

  # Allow for offline access, which will let predictions happen without
  # constant authorization  
  flow = client.flow_from_clientsecrets('client_secrets.json', scope=(
          'https://www.googleapis.com/auth/prediction',
          'https://www.googleapis.com/auth/devstorage.read_only'))
  flow.params['access_type'] = 'offline'

  try:
    # Get access to the Prediction API.
    global pAPI 
    pAPI = service.trainedmodels()

    # Describe model.
    # print_header('Fetching model description')
    # result = papi.analyze(id="lux-g", project="lux-simulation-gb").execute()
    # print('Analyze results:')
    # pprint.pprint(result)

    # Make a predictions using the newly trained model.
    #print_header('Making a prediction')
    time_cosine = argv[1] # -0.9396926
    time_sine = argv[2] # 0.3420202
    meridiem = argv[3] # "PM"

    red_prediction = int(round(predictRed(time_cosine, time_sine, meridiem)))
    green_prediction = int(round(predictGreen(time_cosine, time_sine, meridiem)))
    blue_prediction = int(round(predictBlue(time_cosine, time_sine, meridiem)))
    print("rgb:{},{},{}".format(red_prediction,green_prediction, blue_prediction))
    return("rgb:{},{},{}".format(red_prediction,green_prediction, blue_prediction))

  	

  except client.AccessTokenRefreshError:
    print ('The credentials have been revoked or expired, please re-run '
           'the application to re-authorize.')

def update(argv):

  # if an incorrect number of arguments are supplied, throw an exception
  if len(argv) != 4:
    print("Error -- invalid number of arguments.\n format: <outputValue> <time cosine value> <time sine value> <meridiem>")
    raise SyntaxError()

  # If you previously ran this app with an earlier version of the API
  # or if you change the list of scopes below, revoke your app's permission
  # here: https://accounts.google.com/IssuedAuthSubTokens
  # Then re-run the app to re-authorize it.
  service, flags = sample_tools.init(
      argv[:1], 'prediction', 'v1.6', __doc__, __file__,
      scope=(
          'https://www.googleapis.com/auth/prediction',
          'https://www.googleapis.com/auth/devstorage.read_only'))

  # Allow for offline access, which will let predictions happen without
  # constant authorization  
  flow = client.flow_from_clientsecrets('client_secrets.json', scope=(
          'https://www.googleapis.com/auth/prediction',
          'https://www.googleapis.com/auth/devstorage.read_only'))
  flow.params['access_type'] = 'offline'

  try:
    # Get access to the Prediction API.
    global pAPI 
    pAPI = service.trainedmodels()

    # Describe model.
    # print_header('Fetching model description')
    # result = papi.analyze(id="lux-g", project="lux-simulation-gb").execute()
    # print('Analyze results:')
    # pprint.pprint(result)

    #print_header('Making a prediction')
    outputValue = argv[0]
    time_cosine = argv[1] # -0.9396926
    time_sine = argv[2] # 0.3420202
    meridiem = argv[3] # "PM"

    updateRedResult = updateRed(outputValue, time_cosine, time_sine, meridiem)
    updateGreenResult = updateGreen(outputValue, time_cosine, time_sine, meridiem)
    updateBlueResult = updateBlue(outputValue, time_cosine, time_sine, meridiem)

    return("results:{},{},{}".format(updateRedResult,updateGreenResult,updateBlueResult))

  except client.AccessTokenRefreshError:
    print ('The credentials have been revoked or expired, please re-run '
           'the application to re-authorize.')

if __name__ == '__main__':
  main(sys.argv)
