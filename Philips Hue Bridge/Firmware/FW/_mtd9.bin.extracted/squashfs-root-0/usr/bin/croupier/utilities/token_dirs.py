import errno
import os

import config
from app_config import application_config


def prepare_token_dirs():
    for app in application_config.all_apps():
        token_dir = config.token_dir.format(app)
        try:
            os.mkdir(token_dir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
