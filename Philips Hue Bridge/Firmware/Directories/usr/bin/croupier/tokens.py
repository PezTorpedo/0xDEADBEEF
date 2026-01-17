import os
import time

import config
from app_config import application_config
from utilities.event_logger import EventLogger

from hueutils.c_functions import fsync

token_validity = {}


def __accept_token(app_name, validity):
    if app_name not in application_config.jwt_enabled_apps():
        return False
    if validity <= 0:
        return False
    return True


def __token_filename(app_name):
    return config.token_dir.format(app_name) + config.token_file


def __validity_filename(app_name):
    return config.token_dir.format(app_name) + config.validity_file


def __write_token(app_name, token):
    temp_auth_token_file = __token_filename(app_name) + ".new"
    with open(temp_auth_token_file, "w", encoding="utf-8") as file:
        file.write(token)
        fsync(file.fileno())


def __write_validity(app_name, validity):
    temp_auth_validity_file = __validity_filename(app_name) + ".new"
    with open(temp_auth_validity_file, "w", encoding="utf-8") as file:
        file.write(str(validity))
        token_validity[app_name] = validity
        fsync(file.fileno())


def __activate(app_name):
    auth_token_file = __token_filename(app_name)
    auth_validity_file = __validity_filename(app_name)
    temp_auth_token_file = auth_token_file + ".new"
    temp_auth_validity_file = auth_validity_file + ".new"
    os.rename(temp_auth_token_file, auth_token_file)
    os.rename(temp_auth_validity_file, auth_validity_file)


def __get_time_elapsed_since_creation(file_path):
    # the position of st_mtime in stat tuple is 8
    return int(time.time() - os.stat(file_path)[8])


def __get_remaining_jwt_validity(app_name):
    token_validity_file = config.token_dir.format(app_name) + config.validity_file
    validity_left = 0
    try:
        with open(token_validity_file, "r", encoding="utf-8") as file:
            token_expiration = int(file.read())
            # this is the time elapsed since jwt was last written to the file.
            # it needs to be taken into account as daemon restart will flush the shared validity_table
            time_elapsed = __get_time_elapsed_since_creation(token_validity_file)
            validity_left = token_expiration - time_elapsed

    except OSError as err:
        # It doesn't matter whether the cloud is connected or not, we log the error

        EventLogger().log_event("oserror", "exception", app_name, True, f"validity read error {err}")
        print(f"Error in reading JWT file {err}")

    except Exception:
        print("Error in reading JWT file, continuing")

    return validity_left


# TODO: Not sure if this belongs here, as it will deduce the check_period from the remaining validity automatically
def get_validity_left(app_name):
    if app_name in token_validity:
        return token_validity[app_name] - config.token_status_check_period
    return __get_remaining_jwt_validity(app_name)


def set_validity(app, validity_left):
    token_validity[app] = validity_left


def store(app_name, token, validity):
    if __accept_token(app_name, validity):
        # Token reception is successful when both files are written successfully
        __write_token(app_name, token)
        __write_validity(app_name, validity)
        __activate(app_name)
