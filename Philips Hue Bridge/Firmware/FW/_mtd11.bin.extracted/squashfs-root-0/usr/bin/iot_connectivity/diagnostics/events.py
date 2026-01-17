_total_messages = 0


def send_event(diagnostics, name, description=""):
    global _total_messages
    _total_messages += 1

    body = {"report_counter": _total_messages, "version": 1, "name": name, "description": description}

    diagnostics.send(body, "iot_connectivity_event")
