# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from collections import namedtuple

Spec = namedtuple("Spec", "type required destinations")


class Platform:
    """Hardware abstraction layer for supported platforms."""

    def get_platform_id(self) -> str:
        """Returns the identifier of the hardware platform, such as "BSB002"."""
        raise NotImplementedError()

    def get_board_id(self) -> str:
        """Returns the bridge ID (Eui64)."""
        raise NotImplementedError()

    def get_version(self) -> str:
        """Returns the platform version."""
        raise NotImplementedError()

    def set_version(self, version: str, bootslot: int):
        """Stores the platform version for platforms that require that."""
        raise NotImplementedError()

    def get_component_versions(self) -> dict:
        """Returns a dictionary of platform-specific component versions."""
        raise NotImplementedError()

    def get_specs(self) -> list:
        """Returns the list of libflasher specs, telling how to interpret various firmware bundle sections."""
        raise NotImplementedError()

    def get_bundle_version(self, sections: dict) -> str:
        """Extracts the platform version from the bundle section vesions dictionary."""
        raise NotImplementedError()

    def get_bootslot_index(self) -> int:
        """Returns the active bootslot number, such as 0 or 1."""
        raise NotImplementedError()

    def set_bootslot_index(self, bootslot: int):
        """Sets the active bootslot index, to be used on the next boot."""
        raise NotImplementedError()

    async def startup(self):
        """Executes platform-specific initialisation actions."""
        raise NotImplementedError()

    def pre_update_action(self):
        """Executes platform-specific pre-update actions."""
        raise NotImplementedError()

    def post_update_action(self):
        """Executes platform-specific post-update actions."""
        raise NotImplementedError()

    def load_firmware_key(self) -> bytes:
        """Retrieves the firmware encryption key."""
        raise NotImplementedError()

    def store_reset_reason(self, reason):
        """Stores reset reason, to be used on the next boot."""
        raise NotImplementedError()

    async def reboot(self):
        """Reboots the platform."""
        raise NotImplementedError()

    async def shutdown(self):
        """Shuts down the platform."""
        raise NotImplementedError()

    async def factoryreset(self):
        """Factory resets the platform."""
        raise NotImplementedError()
