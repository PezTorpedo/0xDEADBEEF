# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

daemon_name = "updated"
gc_threshold = 20 * 1024
socket_read_timeout = 60
libflasher_chunk_size = 16384
sideload_endpoint = r"^\/updater(?:\/([a-fA-F0-9]{16}))?$"
sideload_auth_endpoint = r"^\/auth$"
nanoconfig_endpoint = r"^/nanoconfig$"
sideload_bind_address = "127.0.0.1"
sideload_port = 9999
whitelist_auth_endpoint = "http://localhost:9001/auth"
fw_install_marker = "/home/updated/last_downloaded_fw.json"
fw_repository_path = "/home/updated/cache"
swupdate_key = "/home/swupdate/certs/enc.k"
swupdate_cert_path = "/home/swupdate/certs"
bridge_component = "bsb002"
bridge_component_override = "updated_bridge_devicetype"
zigbee_component_prefix = "zgb_"
zigbee_transfer_retries = 3
ssl_ca_bundle_path = "/etc/ssl/certs/data.meethue.com/ca.crt"
ssl_verify_peer = True
ssl_verify_host = True
libcurl_debug = False
eui64 = "eui64"
delta_report_delay = 90
report_period = 60 * 60 * 24
swversion_file = "/etc/swversion"
oom_adj_path = "/proc/self/oom_score_adj"
oom_adj_value = -1000

# Parameters determined once at program startup.
fixed = {
    "kernel_cmdline": "/proc/cmdline",
    "mqtt_host": "localhost",
    "mqtt_port": "1883",
    "platform": "PlatformBsb002",
}

# Parameters that can be overridden via the test interface.
dynamic = {
    "iot_transfer_attempts": 10,
    "zigbee_block_request_delay": 400,
    "fw_repository_budget": 5 * 1024 * 1024,
}
