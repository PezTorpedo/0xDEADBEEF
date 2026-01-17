# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import ffi
from uctypes import bytes_at

from hueutils.c_functions import strlen
from hueutils.ctypes_adapter import ByReference

from .constants import SW_ERROR_EXCEPTION, SW_OK

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

if TYPE_CHECKING:
    from typing import Callable, Optional, Tuple
else:
    Callable = Optional = Tuple = object

_libflasher = ffi.open("libflasher.so")


class LibflasherAssertion(Exception):
    """Raised when libflasher encounters a terminal internal
    error. No further API calls should be made.
    """

    def terminal(self) -> bool:
        return True


def __must_not_return(val, func: Callable):
    def wrapper(*args):
        result = func(*args)
        if result == val:
            raise LibflasherAssertion(pipeline_get_error())
        return result

    return wrapper


# const char *Error_decode_error(Sw_error error)
error_decode_error = _libflasher.func("s", "Error_decode_error", "i")

# const char *Pipeline_get_error()
pipeline_get_error = _libflasher.func("s", "Pipeline_get_error", "")

# Pipeline *Pipeline_create(char *public_key, bool use_syslog)
pipeline_create = __must_not_return(0, _libflasher.func("p", "Pipeline_create", "ssi"))

# Sw_error Pipeline_register_section(Pipeline *pipeline, unsigned int type, bool required,
# const char *reference_version, const char *encryption_key, const char *spec)
pipeline_register_section = __must_not_return(
    SW_ERROR_EXCEPTION,
    _libflasher.func("i", "Pipeline_register_section", "pIispIs"),
)

# Sw_error Pipeline_ingest(Pipeline *pipeline, const uint8_t *data, unsigned int size)
pipeline_ingest = __must_not_return(
    SW_ERROR_EXCEPTION,
    _libflasher.func("i", "Pipeline_ingest", "pPI"),
)

# Sw_error Pipeline_finalise(Pipeline *pipeline, bool override)
pipeline_finalise = __must_not_return(
    SW_ERROR_EXCEPTION,
    _libflasher.func("i", "Pipeline_finalise", "pi"),
)

# int Pipeline_get_special_flags(Pipeline *pipeline)
pipeline_get_special_flags = _libflasher.func("i", "Pipeline_get_special_flags", "p")

# int Pipeline_get_soft_ecc_errors(Pipeline *pipeline)
pipeline_get_soft_ecc_errors = _libflasher.func("i", "Pipeline_get_soft_ecc_errors", "p")

# int Pipeline_get_hard_ecc_errors(Pipeline *pipeline)
pipeline_get_hard_ecc_errors = _libflasher.func("i", "Pipeline_get_hard_ecc_errors", "p")

# int Pipeline_get_bad_blocks(Pipeline *pipeline)
pipeline_get_bad_blocks = _libflasher.func("i", "Pipeline_get_bad_blocks", "p")

# void Pipeline_reset_section_iterator(Pipeline *pipeline)
pipeline_reset_section_iterator = _libflasher.func("v", "Pipeline_reset_section_iterator", "p")

# Sw_error Pipeline_query_section(Pipeline *pipeline, int *type, const char **version)
_pipeline_query_section = _libflasher.func("i", "Pipeline_query_section", "ppP")


def pipeline_query_section(pipeline) -> Optional[Tuple[int, str]]:
    type_ = ByReference()
    version = ByReference()
    if _pipeline_query_section(pipeline, type_, version) == SW_OK:
        return int(type_), bytes_at(int(version), strlen(int(version))).decode()
    return None


# void Pipeline_destroy(Pipeline *pipeline)
pipeline_destroy = _libflasher.func("v", "Pipeline_destroy", "p")
