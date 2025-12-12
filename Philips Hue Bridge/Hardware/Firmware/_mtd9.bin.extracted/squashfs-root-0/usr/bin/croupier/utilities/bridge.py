# pylint: disable=unspecified-encoding
import os

from config import base_dir

bridge_sw_version = None
bridge_device_type = None
bridge_factory_reset_cnt = None


def init_config():
    global bridge_sw_version, bridge_device_type, bridge_factory_reset_cnt
    with open(base_dir + "/etc/swversion") as fd:
        bridge_sw_version = fd.read().strip()

    with os.popen("fw_printenv -n board", "r") as fd:
        bridge_device_type = fd.read().lower().rstrip("\n")

    with os.popen("fw_printenv -n frcnt", "r") as fd:
        bridge_factory_reset_cnt = fd.read().lower().rstrip("\n")


def device_type():
    global bridge_device_type  # pylint: disable=global-variable-not-assigned
    assert bridge_device_type is not None, "Bridge config not initialized"
    return bridge_device_type


def sw_version():
    global bridge_sw_version  # pylint: disable=global-variable-not-assigned
    assert bridge_sw_version is not None, "Bridge config not initialized"
    return bridge_sw_version


def factory_reset_count():
    global bridge_factory_reset_cnt  # pylint: disable=global-variable-not-assigned
    assert bridge_factory_reset_cnt is not None, "Bridge config not initialized"
    return bridge_factory_reset_cnt
