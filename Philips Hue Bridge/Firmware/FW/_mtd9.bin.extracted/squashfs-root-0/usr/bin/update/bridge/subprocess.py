# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import os


class SubprocessError(Exception):
    """Raised when a subprocess execution failed."""


def run(command: str):
    """
    Runs a subprocess, redirecting stdout to `/dev/null`.

    Parameters:
        command: the command to run.

    Raises:
        SubprocessError: when the subprocess exit code was non-zero.
    """
    exit_code = os.system(f"{command} > /dev/null")

    if exit_code != 0:
        raise SubprocessError(f"unexpected exit code {exit_code} when running `{command}`")


def run_with_output(command: str) -> str:
    """
    Runs a subprocess and returns its stdout.

    Due to limitations of µPython the exit code of the subprocess
    is lost. An assumption therefore is made that the subprocess
    must produce some output for the execution result to be considered
    successful.

    Parameters:
        command: the command to run.

    Raises:
        SubprocessError: when the subprocess did not produce any output.
    """
    with os.popen(command) as stdout:
        output = stdout.read()

        if not output:
            raise SubprocessError(f"no output produced when running `{command}`")

        return output
