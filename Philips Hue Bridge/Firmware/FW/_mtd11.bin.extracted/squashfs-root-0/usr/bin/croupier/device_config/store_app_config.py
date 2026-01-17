# pylint: disable=unspecified-encoding.
import json
import os

import config
from app_config import application_config

from hueutils.c_functions import fsync


def _write_app_config(app_name, app_configuration):
    """Writes the app configuration into its urls.json file

    Parameters:
        -app_name: Name of the application
        -app_configuration: App Config Content to be written in JSON
    """
    url_file = config.token_dir.format(app_name) + config.url_file
    temp_url_file = url_file + ".new"
    try:
        with open(temp_url_file, "w") as file:
            file.write(app_configuration)
            fsync(file.fileno())

        os.rename(temp_url_file, url_file)
    except OSError as error:
        print("File error: " + str(error))
    except Exception as error:
        print("General error: " + str(error))


def store_app_config(device_config):
    """Stores the given device config into urls.json files

    Parameters:
        -device_config: Received device configuration in JSON
    """
    for app_name in application_config.urls_enabled_apps():
        app_configuration = json.dumps(device_config[app_name])
        # Write the contents into urls.json directly
        _write_app_config(app_name, app_configuration)
