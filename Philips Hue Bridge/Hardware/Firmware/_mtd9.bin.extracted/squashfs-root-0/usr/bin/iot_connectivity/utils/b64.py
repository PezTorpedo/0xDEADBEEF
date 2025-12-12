import base64

# needed as micropython does not provide it


def urlsafe_b64encode(b: bytes) -> bytes:
    return base64.b64encode(b).replace(b"+", b"-").replace(b"/", b"_")
