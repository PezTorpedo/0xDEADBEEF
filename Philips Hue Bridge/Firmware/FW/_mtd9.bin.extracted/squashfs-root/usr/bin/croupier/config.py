# NOTE: Any changes in this should be reflected in test_config.py also in component_tests/
from hueutils.c_functions import getenv

base_dir = getenv("BASE_DIR") or ""
daemon_name = "croupierd"
token_dir = base_dir + "/tmp/{}/"  # nosec  B108 /tmp is being used in production
token_file = "auth_token"
validity_file = "auth_validity"
url_file = "urls.json"
jwt_request_topic = "iot/out/{}/jwt"
jwt_subscription = "iot/in/+/jwt"
# In agreement with cloud 2minutes
token_status_check_period = 120
wait_before_retry = 5
# the topic on which device config will be published for each daemon
google_iot_config = "iot/config"
google_iot_state = "iot/state"
state_fetch_timeout = 120
state_initial_backoff = 120
state_maximum_backoff = 1200
supported_features_file = "/etc/croupierd/supported_features.json"
vault_req_backoff_min = 30
vault_req_backoff_max = 180
cert_request_topic = "iot/out/vault/https_cert"
cert_receive_topic = "iot/in/vault/https_cert"
data_id = "https_cert"
event_log_dir = "/tmp/token_log/"
temp_log_dir = "/tmp/temp_log/"
log_period = 3600
mqtt_host = "localhost"
mqtt_port = 1883
