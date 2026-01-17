# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import os
from asyncio import Lock
from time import time as now

import config
from bridge import hal
from util.diagnostics import loggable, use_syslog
from util.persistence import DataObject
from util.singleton import singleton
from util.stream_wrapper_base import StreamWrapperBase

from flasher import LibflasherAssertion, LibflasherSpecialImage, Pipeline

METADATA_SCHEMA = DataObject(
    install_started=float, target_version=str, source=str, soft_ecc_errors=int, hard_ecc_errors=int, bad_blocks=int
)


class FirmwareCertificateError(Exception):
    pass


@singleton
@loggable
class Bootslot:
    '''Provides APIs to manage bootslots.

    Can be used to query the active bootslot, to flash the inactive
    bootslot, and to activate the firmware in the inactive bootslot.

    Dut to the vast amount of modules that use this class it is implemented
    as a singleton, otherwise passing it around would get out of hand.

    Attributes:
        active_index:    the actual active bootslot index (0 or 1), read from the kernel cmdline.
        active_version:  the actual active bootslot firmware version, read from `/etc/swversion`.
        active_metadata: the metadata persisted for this bootslot after the last FW installation.
        inactive_index:  the inactive bootslot index, always the complement of the `active_index`.
        inactive_metadata: the metadata of the last FW flashed into inactive bootslot.
    '''

    def __init__(self):
        self.__lock = Lock()
        self.active_index = hal().get_bootslot_index()
        self.inactive_index = 1 - self.active_index
        self.active_version = hal().get_version()
        self.active_metadata = self.__load_active_bootslot_metadata()
        self.inactive_metadata: DataObject = None
        self._logger.info('Instantiated, self=%s', self)

    def __str__(self) -> str:
        return '{}(active_index={}, active_version={}, active_metadata={}, inactive_index={}, inactive_metadata={})'.format(
            type(self).__name__,
            self.active_index,
            self.active_version,
            self.active_metadata,
            self.inactive_index,
            self.inactive_metadata,
        )

    def __load_active_bootslot_metadata(self) -> DataObject:
        try:
            return DataObject.load(path=config.fw_install_marker, delete=True, schema=METADATA_SCHEMA)
        except Exception as ex:
            if isinstance(ex, OSError) and ex.errno == 2:
                self._logger.info('No last installation metadata found')
            else:
                self._logger.exception('Unable to load the last installation metadata')
            return None

    def __find_certificate(self) -> str:
        pem_files = [file for file, *_ in os.ilistdir(config.swupdate_cert_path) if file.endswith('.pem')]
        if not pem_files:
            raise FirmwareCertificateError('No certificate file found')
        if len(pem_files) > 1:
            raise FirmwareCertificateError(
                'Expected to find one certificate file, but found multiple: {}'.format(pem_files)
            )
        return '{}/{}'.format(config.swupdate_cert_path, pem_files[0])

    # pylint: disable=too-many-arguments, too-many-locals
    async def fill(
        self,
        from_stream: StreamWrapperBase,
        source: str,
        expected_md5: str = None,
        allow_downgrade: bool = False,
        version_callback=None,
    ):
        '''
        Fills the inactive bootslot from the given stream. Will update the
        inactive botslot metadata if successful.

        This function is a coroutine.

        Parameters:
            from_stream:      the stream to pull the data from.
            source:           the source of the firmware, either 'sideload', 'iot', or 'portal'.
            expected_md5:     the expected checksum of the downloaded image, or None to disable checksum check.
            allow_downgrade:  the flag to indicate that the version check can be skipped.
            version_callback: will get invoked to inform the caller about the encountered FW2 package section versions.

        Raises:
            CanceledError:            when the task is canceled.
            OSError:                  when reading from stream fails.
            TimeoutError:             when a socket operation times out.
            LibflasherSpecialImage:   when a "special" image is encountered and no actual flashing was performed.
            LibflasherError:          when the bootslot flashing fails.
            LibflasherAssertion:      when the flashing library encounters an unrecoverable error.
            FirmwareChecksumError:    when the checksum check of the streamed image fails.
            FirmwareCertificateError: when the right firmware certificate can't be found.
        '''
        async with self.__lock:
            key = hal().load_firmware_key()
            hal().pre_update_action()
            try:
                with Pipeline(hal().get_platform_id(), self.__find_certificate(), use_syslog()) as pipeline:
                    for spec in hal().get_specs():
                        destination = spec.destinations[self.inactive_index % len(spec.destinations)]
                        self._logger.debug("registering section, id=%d, spec=%s", spec.type, destination)
                        pipeline.register_section(
                            spec.type, spec.required, None if allow_downgrade else hal().get_version(), key, destination
                        )
                    try:
                        with pipeline.sink() as sink:
                            await from_stream.stream(sink.ingest, checksum=expected_md5)
                        # Store the system version if the platform requires that.
                        # Should this fail, the entire update will (and must) fail.
                        hal().set_version(hal().get_bundle_version(pipeline.query_sections()), self.inactive_index)
                    except (LibflasherAssertion, LibflasherSpecialImage):
                        version_callback = None
                        raise
                    finally:
                        if version_callback:
                            version_callback(hal().get_bundle_version(pipeline.query_sections()))
                    soft_ecc_errors, hard_ecc_errors, bad_blocks = pipeline.query_flash_errors()
                    self.inactive_metadata = DataObject(
                        target_version=hal().get_bundle_version(pipeline.query_sections()),
                        source=source,
                        soft_ecc_errors=soft_ecc_errors,
                        hard_ecc_errors=hard_ecc_errors,
                        bad_blocks=bad_blocks,
                    )
                    self._logger.info(
                        "Successfully filled bootslot %d %s",
                        self.inactive_index,
                        self.inactive_metadata.remap(
                            ("target_version", "version"),
                            "soft_ecc_errors",
                            "hard_ecc_errors",
                            "bad_blocks",
                        ),
                    )
            except Exception as ex:
                if not isinstance(ex, LibflasherSpecialImage):
                    self.inactive_metadata = None
                raise
            finally:
                hal().post_update_action()

    async def install(self, factory_reset=False):
        '''Reboots the bridge. If the inactive bootslot is known to be filled
        with a valid software, the bootslot is switched as well.
        '''
        if self.inactive_metadata:
            self._logger.info(
                'Switching bootslot from %d (%s) to %d (%s)',
                self.active_index,
                self.active_version,
                self.inactive_index,
                self.inactive_metadata.target_version,
            )
            hal().set_bootslot_index(self.inactive_index)
            try:
                reset_reason = 5 if self.inactive_metadata.source == "iot" else 6
                hal().store_reset_reason(reset_reason)
            except Exception:
                self._logger.exception('Unable to store the reset reason to uboot')

            self.inactive_metadata.update(install_started=now())
            try:
                self.inactive_metadata.store(config.fw_install_marker)
            except Exception:
                self._logger.exception('Unable to store the last installation metadata')
        if factory_reset:
            self._logger.info('Rebooting (with factory reset)')
            await hal().factoryreset()
        else:
            self._logger.info('Rebooting')
            await hal().shutdown()
