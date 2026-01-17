from hueutils.c_functions import getenv

report_period_8hr = 8 * 3600
report_period_24hr = 24 * 3600
# This period will be used if the provisioning service does not return a 'retry-timeout'
# or returns an invalid value.
default_force_reprovisioning_after = 6 * 3600
jwt_refresh_period = int(getenv("JWT_PERIOD") or 3600)
broker_reconfigure_period = 60

# make jwt a bit older than expected to guarantee is valid even with clock drift
jwt_iat_correction = 60

daemon_name = "iot_connectivity"

# The base_dir path is not useful for the bridge but
# is useful for testing. The test can override the base_dir
# by redefining settings to make it run in in the test environment

base_dir = getenv("BASE_DIR") or ""

provisioning_directory = base_dir + "/etc/iot-credentials"
mqtt_bridge_conf_file = base_dir + "/etc/mosquitto/inc/iot_bridge.conf"
mqtt_log_subscription = "$SYS/broker/log/#"
topic_daily_conn_data = "report/connectivity"
provisioning_status_subscription = "status/provisioning/provisioning_state"
# These tags have been defined in mosquitto and used to filter errors of interest
tag_disconnect_err = "[TAG_DISCONN_ERR]"
tag_bridge_fail_err = "[TAG_BRIDGE_ERR]"
tag_connect_ack_err = "[TAG_CONACK_ERR]"
reprovision_cmd = "iot/in/provision"
no_iot_connection = "no_iot_connection"
reprovisioning_cmd = "reprovision_command"
mismatched_schema = "mismatched_schema"
mqtt_host = "localhost"
mqtt_port = 1883
