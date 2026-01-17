# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from typing import Optional, Tuple

class LibflasherAssertion(Exception): ...

# const char *Error_decode_error(Sw_error error)
def error_decode_error(error: int) -> str: ...

# const char *Pipeline_get_error()
def pipeline_get_error() -> str: ...

# Pipeline *Pipeline_create(char *public_key, bool use_syslog)
def pipeline_create(public_key: str, use_syslog: bool) -> int: ...

# Sw_error Pipeline_register_section(Pipeline *pipeline, unsigned int type, bool required,
# const char *reference_version, const char *encryption_key, const char *spec)
def pipeline_register_section(
    pipeline: int,
    type: int,
    required: bool,
    reference_version: str,
    encryption_key: str,
    spec: str,
) -> int: ...

# Sw_error Pipeline_ingest(Pipeline *pipeline, const uint8_t *data, unsigned int size)
def pipeline_ingest(pipeline: int, data: bytes, size: int) -> int: ...

# Sw_error Pipeline_finalise(Pipeline *pipeline, bool override)
def pipeline_finalise(pipeline: int, override: bool) -> int: ...

# int Pipeline_get_special_flags(Pipeline *pipeline)
def pipeline_get_special_flags(pipeline: int) -> int: ...

# int Pipeline_get_soft_ecc_errors(Pipeline *pipeline)
def pipeline_get_soft_ecc_errors(pipeline: int) -> int: ...

# int Pipeline_get_hard_ecc_errors(Pipeline *pipeline)
def pipeline_get_hard_ecc_errors(pipeline: int) -> int: ...

# int Pipeline_get_bad_blocks(Pipeline *pipeline)
def pipeline_get_bad_blocks(pipeline: int) -> int: ...

# void Pipeline_reset_section_iterator(Pipeline *pipeline)
def pipeline_reset_section_iterator(pipeline: int) -> None: ...

# Sw_error Pipeline_query_section(Pipeline *pipeline, int *type, const char **version)
def pipeline_query_section(pipeline: int) -> Optional[Tuple[int, str]]: ...

# void Pipeline_destroy(Pipeline *pipeline)
def pipeline_destroy(pipeline: int) -> None: ...
