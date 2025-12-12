from utilities import bridge


def _check_sw_version(version):
    return bridge.sw_version() == version


def is_device_config_valid(config):
    return _check_sw_version(config["sw"])
