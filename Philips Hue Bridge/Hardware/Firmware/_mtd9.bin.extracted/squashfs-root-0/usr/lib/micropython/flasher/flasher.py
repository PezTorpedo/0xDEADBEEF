# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

"""Python bindings to libflasher.so"""
from .constants import SW_ERROR_SPECIAL_IMAGE, SW_OK
from .libflasher import (
    LibflasherAssertion,
    error_decode_error,
    pipeline_create,
    pipeline_destroy,
    pipeline_finalise,
    pipeline_get_bad_blocks,
    pipeline_get_hard_ecc_errors,
    pipeline_get_soft_ecc_errors,
    pipeline_get_special_flags,
    pipeline_ingest,
    pipeline_query_section,
    pipeline_register_section,
    pipeline_reset_section_iterator,
)


class LibflasherError(Exception):
    """Raised when libflasher call returns an error.

    Attributes:
        code:            the error code as returned by an API call.
        message:         the human-readable error description.
    """

    def __init__(self, code: int):
        self.code = code
        self.message = error_decode_error(code)

    def __str__(self):
        return self.message


class LibflasherSpecialImage(Exception):
    """Raised when a special image was present in the firmware bundle.

    Attributes:
        options: the option bits from the special image
    """

    def __init__(self, options: int):
        self.options = options


class Sink:
    def __init__(self, handle):
        self._handle = handle

    def __enter__(self):
        return self

    def ingest(self, data: bytes):
        """Streams (a chunk of) data into the sink.

        May block for a time required to write an erase block to flash.

        Parameters:
            data (bytes): the raw data chunk.

        Raises:
            LibflasherAssertion: when libflasher.so encounters an unrecoverable internal error.
            LibflasherError:     when an error happens during ingestion.
        """
        ret = pipeline_ingest(self._handle, data, len(data))
        if ret != SW_OK:
            raise LibflasherError(ret)

    def __exit__(self, exc_type, exc_value, _):
        if exc_type is LibflasherAssertion:
            # An unrecoverable error. Return None so LibflasherAssertion
            # will get re-raised.
            return None

        # Otherwise make sure to call finalise, even if an exception
        # was raised in the `with` block.
        # The last argument to `Pipeline_finalise` is `override`, which,
        # if set to True, will make libflahser erase partitions and
        # return SW_ERROR_OVERRIDE even if everything went OK with flashing.
        # This allows the calling code to abort the flashing process
        # even after feeding in the lash chunk of data by raising some
        # exception (which is not LibflasherError).
        finalise_result = pipeline_finalise(self._handle, 1 if exc_type and exc_type is not LibflasherError else 0)

        if not exc_value:
            # All `ingest` calls returned `SW_OK` and no exceptions.

            if finalise_result == SW_ERROR_SPECIAL_IMAGE:
                # Special image with flags.
                raise LibflasherSpecialImage(pipeline_get_special_flags(self._handle))

            if finalise_result != SW_OK:
                # Error code from `Pipeline_finalise`.
                raise LibflasherError(finalise_result)

            # All is good.
            return True
        # An exception within the `with` block, re-raise.
        return None


class Pipeline:
    """Provides pythonic interface to the functionality of `libflasher.so`.

    Allows streaming of certain firmware bundle packages directly to MTD
    partitions, block devices, or to an external program via pipe. Handles
    the bundle unpacking, flashing (or piping), and final verification of
    the firmware. Will also erase target partitions if a flashing error occurs
    (only for MTD devices).

    Implements the context manager interface, the typical usage is as below.

    ```python
    try:
        with Pipeline(...) as pipeline:
            # Registed sections of interest
            pipeline.register_section(...)
            with pipeline.sink() as sink:
                # While there's data.
                sink.ingest(...)
            # Query actual section versions with `pipeline.query_sections()`
            # Query flash errors with `pipeline.query_flash_errors()`
    except LibflasherError as err:
        # Flashing failed, the exact reason is in `err.code` and `err.message`.
    except LibflasherAssertion:
        # Unrecoverable error in `libflasher.so`, see below.
        # Log the error and exit.
    ```

    Errors are reported back wrapped in `LibflasherError` exception.

    If the processed firmware file contained a special image,
    `LibflasherSpecialImage` is raised, encapsulating the special image flags.

    If a reference version is provided for a section, it will be compared
    to the actual version of the section, and `LibflasherError(code=27)`
    will get raised if the section version is less or equal to the reference version.

    A special handling is required if `LibflasherAssertion` is raised. This may
    happen if a critical and unrecoverable error happened in `libflasher.so`,
    the resources may have been left unfreed, file descriptors may have been left
    open, and the API is no longer usable by the calling process. The calling
    process _must_ restart.

    The verbosity level of libflasher can be increased by setting an environment
    variable `LIBFLASHER_VERBOSITY`. Set to 1 for DEBUG, and to 2 for TRACE.
    """

    def __init__(self, magic: str, public_key: str, use_syslog=False):
        self._magic = magic
        self._public_key = public_key
        self._use_syslog = use_syslog

    def __enter__(self):
        self._handle = pipeline_create(self._magic, self._public_key, 1 if self._use_syslog else 0)
        return self

    def __exit__(self, exc_type, exc_value, _):
        if exc_type is LibflasherAssertion:
            # An unrecoverable error. Return None so LibflasherAssertion
            # will get re-raised.
            return
        # Otherwise destroy the pipeline to free up resources.
        pipeline_destroy(self._handle)

    def register_section(self, type_: int, required: bool, version: str, key: bytes, spec: str):
        pipeline_register_section(self._handle, type_, 1 if required else 0, version, key, len(key), spec)

    def query_flash_errors(self) -> tuple:
        return (
            pipeline_get_soft_ecc_errors(self._handle),
            pipeline_get_hard_ecc_errors(self._handle),
            pipeline_get_bad_blocks(self._handle),
        )

    def query_sections(self) -> dict:
        sections = {}
        pipeline_reset_section_iterator(self._handle)
        while section := pipeline_query_section(self._handle):
            sections[section[0]] = section[1]
        return sections

    def sink(self) -> Sink:
        return Sink(self._handle)
