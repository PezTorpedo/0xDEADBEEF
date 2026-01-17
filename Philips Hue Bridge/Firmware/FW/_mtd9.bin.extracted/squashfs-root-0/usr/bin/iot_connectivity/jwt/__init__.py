import json

from utils import b64

from .sign import sign_ec


def _trim_padding(b: bytes) -> bytes:
    return b.rstrip(b"=")


def _serialize_element(o: dict) -> bytes:
    return _trim_padding(b64.urlsafe_b64encode(json.dumps(o).encode()))


def jwt_ec(payload: dict, key_file: str, key_passphrase: str = "", bits: int = 256) -> bytes:
    header = {"alg": f"ES{bits}", "typ": "JWT"}

    with open(key_file) as f:  # pylint: disable=unspecified-encoding
        key_file_content = f.read().encode()

    unsigned = _serialize_element(header) + b"." + _serialize_element(payload)

    signature = _trim_padding(b64.urlsafe_b64encode(sign_ec(unsigned, key_file_content, key_passphrase, bits)))

    return unsigned.decode() + "." + signature.decode()
