import config


def send_jwt_request(mqtt_conn, app):
    print(f"Requesting {app} token")
    jwt_request_topic = config.jwt_request_topic.format(app)
    # send the request with empty payload exactly once
    mqtt_conn.publish(jwt_request_topic, "", 0)
