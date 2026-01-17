template = """# dynamically generated configuration

connection cloud-iot

bridge_reload_type {reload_type}

address {url}:{port}

bridge_insecure false
bridge_tls_version tlsv1.2
bridge_capath /etc/ssl/certs/google_iot
bridge_cafile /etc/ca-certificates/ca.ecc.cert-and-crls.pem
bridge_certfile /etc/ssl/certs/tunnel_pass/mqtt.hue.signify.com.cn.client.ecc.cert.pem
bridge_keyfile /etc/ssl/certs/tunnel_pass/mqtt.hue.signify.com.cn.client.key
bridge_ciphers ECDHE-ECDSA-AES128-GCM-SHA256
bridge_ciphers_tls1.3 TLS_CHACHA20_POLY1305_SHA256

keepalive_interval {keepalive}
bridge_tcp_keepalive 30 5 5
bridge_tcp_user_timeout 60000
restart_timeout 5 3600

bridge_protocol_version mqttv311
try_private false
bridge_attempt_unsubscribe false
bridge_outgoing_retain false

notifications_local_only true
notification_topic $SYS/broker/connection/cloud/state

local_clientid cloud-iot
remote_username unused
remote_password {jwt}
remote_clientid {client-id-prefix}{device_id}

topic # in 0 iot/in/ {topic-prefix}{device_id}/commands/
topic # out 1 iot/out/ {topic-prefix}{device_id}/events/
topic config in 1 iot/ {topic-prefix}{device_id}/
topic state out 0 iot/ {topic-prefix}{device_id}/
"""
