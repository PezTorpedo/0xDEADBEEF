# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

from bridge import subprocess


def read_variable(name: str) -> str:
    """
    Returns the value of the given UBoot variable, or None
    if the variable is not set.
    """
    try:
        return subprocess.run_with_output(f"fw_printenv -n {name} 2>/dev/null").rstrip("\n")
    except subprocess.SubprocessError:
        return None


def write_variable(name: str, value: str):
    """
    Sets the given UBoot variable to the given value.

    Raises:
        SubprocessError: when `fw_setenv` fails.
    """
    subprocess.run(f"fw_setenv {name} {value}")
