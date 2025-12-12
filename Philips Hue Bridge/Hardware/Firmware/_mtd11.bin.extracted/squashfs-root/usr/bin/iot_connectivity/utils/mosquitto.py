import os

import settings


def reload_mosquitto():
    os.system(settings.base_dir + "/etc/init.d/mosquitto reload")  # nosec
