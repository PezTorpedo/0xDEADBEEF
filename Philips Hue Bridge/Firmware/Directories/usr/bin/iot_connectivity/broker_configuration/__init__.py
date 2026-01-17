import asyncio
import os

import settings
import shared
from utils import mosquitto, schema_validator

from .config_builder import generate_config


class NotProvisioned(Exception):
    pass


class InvalidCertificateFormat(Exception):
    pass


async def _print_error_and_wait():
    print(f"issue while trying to generate the mosquitto bridge configuration: {shared.last_config_error}")
    await asyncio.sleep(settings.broker_reconfigure_period)


async def handle_broker_config():
    while True:
        try:
            try:
                # generate a new config file
                generate_config(True)

                # reload the newly generated config file
                mosquitto.reload_mosquitto()

            except schema_validator.SchemaValidationError as exc:
                shared.last_config_error = f"config error {type(exc).__name__}: {exc}"
                # If schema mismatch happens then it requires force reprovision.
                os.system(f"force_reprovision {settings.provisioning_directory} {settings.mismatched_schema}")  # nosec
                await _print_error_and_wait()
                continue

            except KeyError as exc:
                shared.last_config_error = f"config error {type(exc).__name__}: Key '{exc}' was not found"

                await _print_error_and_wait()
                continue

            except Exception as exc:
                shared.last_config_error = f"config error {type(exc).__name__}: {exc}"
                await _print_error_and_wait()
                continue

            shared.last_config_error = "the mosquitto bridge configuration was successfully written"
            print(shared.last_config_error)
            await asyncio.sleep(settings.jwt_refresh_period)

        except asyncio.CancelledError:
            break
