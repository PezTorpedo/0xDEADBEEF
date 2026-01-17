# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import asyncio
import re

import config
from bridge import Platform, Spec, subprocess, uboot
from util.diagnostics import loggable
from util.misc import memoize, simple_read

from flasher import SECTION_BSB002

# Maps the `ubi.mtd` kernel boot parameter to active bootslot.
__BOOTSLOTS = {
    'ubi.mtd=5': 0,
    'ubi.mtd=7': 1,
}

# Extracts the active MTD root partition from the kernel cmdline.
__KERNEL_CMDLINE_RE = r'ubi\.mtd=\d'


@loggable
class PlatformHse(Platform):
    def __init__(self):
        self.__active_bootslot: int = None

    def get_platform_id(self) -> str:
        return "HSE"

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
                destinations=[
                    "/dev/mtd4:mtd=kernel.bin /dev/mtd5:mtd=root.bin",
                    "/dev/mtd6:mtd=kernel.bin /dev/mtd7:mtd=root.bin",
                ],
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
