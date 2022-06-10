import os
import json
import obd
import logging

SETTINGS_PATH = os.environ.get('SETTINGS_DIR', os.getcwd()) + '/settings.json'

def connection_params():
    """ Configure the OBD connection parameters given in settings.json file and set the logger. """
    log_level = 'INFO'      # default to info
    params = {}
    if os.path.isfile(SETTINGS_PATH):
        file = open(SETTINGS_PATH)
        data = json.load(file)
        log_level = data['connection']['log_level']
        if data['connection']['auto'] == False:
            params = data['connection']['parameters']
    # delay is defined whether manual or auto; convert delay from ms to seconds
    params['delay_cmds'] = data['connection']['parameters']['delay_cmds'] / 1000  

    obd.logger.setLevel(log_level)     
    logging.basicConfig(filename='obd.log', filemode='w', level=log_level)
    return params
