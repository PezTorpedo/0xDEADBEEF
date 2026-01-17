import settings
import shared
from broker_configuration import config_builder
from utils import mosquitto


async def process_provisioning_status(mqtt):
    async for msg in mqtt.subscribe(settings.provisioning_status_subscription):
        provisioned = msg["payload"] == b"1"
        print(f"Provisioning event, provisioned={provisioned}")
        if provisioned:
            try:
                # Generate a new MQTT bridge config file
                config_builder.generate_config(False)

                # Restarting mosquitto so a connection using new credentials
                # can be made
                mosquitto.reload_mosquitto()

                config_builder.generate_config(True)
                mosquitto.reload_mosquitto()
                shared.last_config_error = "the mosquitto bridge configuration was successfully written"
                print("Mosquitto reloaded after a successful reprovisioning.")

            except KeyError as exc:
                shared.last_config_error = f"config error {type(exc).__name__}: Key '{exc}' was not found"

            except Exception as exc:
                shared.last_config_error = f"config error {type(exc).__name__}: {exc}"
