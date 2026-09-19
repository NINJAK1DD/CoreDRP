# Copyright 2026 Rob Cooke
# SPDX-License-Identifier: Apache-2.0
"""Explicit lab fault injection. Disabled unless a test names a boundary."""
import os,signal

def hit(point):
    if os.environ.get('COREDRP_TEST_CRASH')==point:
        os.kill(os.getpid(),signal.SIGKILL)


def io_fault(point):
    """Inject an OS failure at a named persistence operation in isolated tests."""
    import errno
    if os.environ.get('COREDRP_TEST_IO')==point:
        code=errno.ENOSPC if os.environ.get('COREDRP_TEST_ERRNO')=='ENOSPC' else errno.EIO
        raise OSError(code,'injected storage failure')
