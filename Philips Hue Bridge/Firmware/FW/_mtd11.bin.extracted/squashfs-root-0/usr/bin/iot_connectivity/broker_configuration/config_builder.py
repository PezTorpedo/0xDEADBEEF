import json
import os
import time

import jwt
import settings
from utils import schema_validator

from hueutils.c_functions import fsync

from .conf_template import template
from .expected_schema import SERVICE_JSON_SCHEMA


class NotProvisioned(Exception):
    pass


class InvalidCertificateFormat(Exception):
    pass


def _read_provisioning_settings():
    with os.popen(f"is_provision_valid {settings.provisioning_directory}") as prov_proc:
        provision_status = prov_proc.read().rstrip("\n")
        if provision_status not in ("healthy_certificate", "close_to_expiration", "forced_reprovisioning"):
            raise NotProvisioned(provision_status)

    try:
        with open(f"{settings.provisioning_directory}/service.json", "r") as f:  # pylint: disable=unspecified-encoding
            service_json = json.loads(f.read())
            schema_validator.validate_schema(service_json, SERVICE_JSON_SCHEMA)
            return service_json

    except schema_validator.SchemaValidationError as exc:
        # reraise the exception to be handled by next level function call
        raise exc

    except Exception as exc:
        raise InvalidCertificateFormat(f"{type(exc).__name__} {str(exc)}") from exc


def _get_device_id():
    with os.popen("fw_printenv -n eui64") as f:
        return f.read().lower().rstrip("\n")


def _write_config(file, **args):
    assert all(args.values()), "one of the configuration arguments is empty"
    file.write(template.format(**args))


def _create_jwt(audience):
    # remove some seconds from iat to guarantee valid JWT even with clock drift
    iat = int(time.time()) - settings.jwt_iat_correction

    # google sets the 24h limit
    exp = iat + 24 * 3600

    return jwt.jwt_ec({"iat": iat, "exp": exp, "aud": audience}, f"{settings.provisioning_directory}/private_key.pem")


def generate_config(lazy_reload):
    conf_values = _read_provisioning_settings()
    # use the client id
    conf_values["device_id"] = _get_device_id()
    conf_values["jwt"] = _create_jwt(conf_values["aud"])
    conf_values["reload_type"] = "lazy" if lazy_reload else "immediate"
    with open(settings.mqtt_bridge_conf_file + ".new", "w") as f:  # pylint: disable=unspecified-encoding
        _write_config(f, **conf_values)
        fsync(f.fileno())
        os.rename(settings.mqtt_bridge_conf_file + ".new", settings.mqtt_bridge_conf_file)
