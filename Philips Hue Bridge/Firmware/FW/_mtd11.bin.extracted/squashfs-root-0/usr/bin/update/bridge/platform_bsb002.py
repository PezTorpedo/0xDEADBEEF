# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import asyncio
import re

import config
from bridge import Platform, Spec, subprocess, uboot
from bridge.ubi import UbiError, ubi_assess, ubi_attach, ubi_attached, ubi_detach
from util.diagnostics import loggable
from util.misc import memoize, simple_read

from flasher import SECTION_BSB002

# We extract `ubi.mtd=X` substring from the kernel command line,
# and then use this lookup table to figure out the active bootslot.
__BOOTSLOTS = {
    'ubi.mtd=5': 0,
    'ubi.mtd=7': 1,
}

# Firmware destinations per bootslot. In other words, pointing to
# partitions belonging to a bootslot.
# UBI-enabled flashing scenario.
__FIRMWARE_DESTINATIONS = [
    "/dev/mtd4:mtd=kernel.bin /dev/ubi2_0:ubi=root.bin",
    "/dev/mtd6:mtd=kernel.bin /dev/ubi2_0:ubi=root.bin",
]

# Firmware destinations per bootslot. In other words, pointing to
# partitions belonging to a bootslot.
# Raw MTD flashing scenario.
__FALLBACK_FIRMWARE_DESTINATIONS = [
    "/dev/mtd4:mtd=kernel.bin /dev/mtd5:mtd=root.bin",
    "/dev/mtd6:mtd=kernel.bin /dev/mtd7:mtd=root.bin",
]

# The MTD device for the _other_ bootslot rootfs. So in essence
# a reciprocal of the two definitions above.
# If the active bootslot is 0, the MTD device for rootfs belonging
# to other bootslot (1) would be `7` (and the other way around).
__ROOTFS_DEVICES = [
    "/dev/mtd7",
    "/dev/mtd5",
]

# The expected sysfs hierarchy when the ubi volume is mounted correctly.
__SYSFS_ENTRIES = [
    {
        "/sys/class/ubi/ubi2/mtd_num": "7",
        "/sys/class/ubi/ubi2/volumes_count": "1",
        "/sys/class/ubi/ubi2/ubi2_0/name": "rootfs",
    },
    {
        "/sys/class/ubi/ubi2/mtd_num": "5",
        "/sys/class/ubi/ubi2/volumes_count": "1",
        "/sys/class/ubi/ubi2/ubi2_0/name": "rootfs",
    },
]

# Extracts the active MTD root partition from the kernel cmdline.
__KERNEL_CMDLINE_RE = r'ubi\.mtd=\d'


@loggable
class PlatformBsb002(Platform):
    def __init__(self):
        self.__active_bootslot: int = None
        self.__specs: list = None

    def get_platform_id(self) -> str:
        return "BSB002"

    @memoize
    def get_board_id(self) -> str:
        return uboot.read_variable(config.eui64)

    @memoize
    def get_version(self) -> str:
        return simple_read(config.swversion_file)

    def set_version(self, *_):
        pass

    def get_component_versions(self) -> dict:
        return None

    def get_specs(self) -> list:
        return [
            Spec(
                type=SECTION_BSB002,
                required=True,
                destinations=self.__specs,
            )
        ]

    def get_bundle_version(self, sections: dict) -> str:
        return sections.get(SECTION_BSB002, "unknown")

    def get_bootslot_index(self) -> int:
        assert self.__active_bootslot is not None, "get_bootslot_id() can't be called before startup()"
        return self.__active_bootslot

    def set_bootslot_index(self, bootslot: int):
        uboot.write_variable('bootslot', str(bootslot))

    async def startup(self):
        self.__read_active_bootslot()
        self.__adjust_nor_bootslot_index()
        await self.__attach_ubi_device()

    def pre_update_action(self):
        pass

    def post_update_action(self):
        pass

    def load_firmware_key(self) -> bytes:
        self._logger.info("Loading firmware decryption key from %s", config.swupdate_key)
        with open(config.swupdate_key, "rb") as key_file:
            return key_file.read()

    def store_reset_reason(self, reason):
        self._logger.info("Storing reset reason %s in uboot", reason)
        uboot.write_variable('resetreason', reason)

    async def reboot(self):
        await self.__flush_diagnostics()
        subprocess.run("shuthuedown")

    async def shutdown(self):
        await self.reboot()

    async def factoryreset(self):
        await self.__flush_diagnostics()
        subprocess.run("factoryreset.sh")

    async def __flush_diagnostics(self):
        await asyncio.sleep(1)
        subprocess.run("if [ -x /etc/init.d/messenger ];then /etc/init.d/messenger flush; fi")

    def __read_active_bootslot(self):
        # Read the kernel boot parameters and determine the active
        # bootslot. This much safer than reading the `bootslot` NOR flash
        # variable, because the cmdline is immutable for the entire duration
        # of the bridge uptime. So even if we switch the bootslot, crash,
        # and restart we will still correctly read the active bootslot.
        cmdline = simple_read(config.fixed["kernel_cmdline"])
        match = re.match(__KERNEL_CMDLINE_RE, cmdline)
        if match:
            self.__active_bootslot = __BOOTSLOTS[match.group()]
        else:
            raise ValueError(f"unable to determine the active bootslot from kernel cmdline: {cmdline}")
        if self.__active_bootslot not in (0, 1):
            raise ValueError(f"the active bootslot is {self.__active_bootslot} which is not a valid value")

    def __adjust_nor_bootslot_index(self):
        """
        Reads the value of the `bootslot` NOR variable and makes sure
        it matches the actual active bootslot. Resets it if it doesn't match.
        This prevents booting into a partially flashed bootslot if
        we flash a bootslot, switch the variable, crash, restart,
        start flashing again and for some reason reboot while flashing.
        """
        nor_bootslot_index = int(uboot.read_variable("bootslot"))
        if nor_bootslot_index != self.__active_bootslot:
            self._logger.warning(
                "The value of `bootslot` NOR variable %d does not match the active bootslot %d, resetting",
                nor_bootslot_index,
                self.__active_bootslot,
            )
            uboot.write_variable("bootslot", str(self.__active_bootslot))

    async def __attach_ubi_device(self):
        self.__specs = __FIRMWARE_DESTINATIONS
        other_mtd = __ROOTFS_DEVICES[self.get_bootslot_index()]

        if ubi_attached(2):
            self._logger.warning("Detaching unwanted ubi2")
            try:
                ubi_detach(2)
            except subprocess.SubprocessError:
                # The UBI detach ioctl call is almost infallible. The only possible
                # error from it, assuming being fed a valid device ID, is EBUSY.
                # There's really nothing to be done about it, so let the daemon
                # crash and hopefully the issue will resolve itself either after
                # restarting the daemon, or restarting the bridge.
                self._logger.error("Can't detach ubi2, most likely UBI_IOCDET returned EBUSY")
                # Let's give the diagnostic machinery a chance to send out the error.
                await asyncio.sleep(5)
                raise Exception("Goodbye, cruel world")  # pylint: disable=raise-missing-from

        try:
            self._logger.info("Attaching ubi2 to %s", other_mtd)
            ubi_attach(2, other_mtd)
        except subprocess.SubprocessError as se:
            self._logger.warning("Can't attach ubi2: %s", str(se))
            # Let's attempt raw MTD flashing.
            self.__specs = __FALLBACK_FIRMWARE_DESTINATIONS
            return

        try:
            # It is possible not to have a `rootfs` volume on the UBI device.
            # So assert on that and revert to flashing raw MTD in case
            # of abnormalities.
            ubi_assess(__SYSFS_ENTRIES[self.get_bootslot_index()])
        except UbiError as ue:
            self._logger.warning("ubi2 is attached but appears wrong: %s", str(ue))
            self.__specs = __FALLBACK_FIRMWARE_DESTINATIONS
            try:
                ubi_detach(2)
            except subprocess.SubprocessError:
                # All the same as the previous instance of this error.
                self._logger.error("Can't detach ubi2, most likely UBI_IOCDET returned EBUSY")
                await asyncio.sleep(5)
                raise Exception("Goodbye, cruel world")  # pylint: disable=raise-missing-from
