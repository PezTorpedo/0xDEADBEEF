# Signify Company Confidential.
# Copyright (C) 2023 Signify Holding.
# All rights reserved.

import config
from bridge.platform import Platform, Spec  # NOQA
from bridge.platform_bsb002 import PlatformBsb002  # NOQA
from bridge.platform_hse import PlatformHse  # NOQA
from util.misc import memoize


@memoize
def hal() -> Platform:
    return globals()[config.fixed["platform"]]()
