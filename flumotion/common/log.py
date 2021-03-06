# -*- Mode: Python; test-case-name: flumotion.test.test_log -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007 Fluendo, S.L. (www.fluendo.com).
# All rights reserved.

# This file may be distributed and/or modified under the terms of
# the GNU General Public License version 2 as published by
# the Free Software Foundation.
# This file is distributed without any warranty; without even the implied
# warranty of merchantability or fitness for a particular purpose.
# See "LICENSE.GPL" in the source distribution for more information.

# Licensees having purchased or holding a valid Flumotion Advanced
# Streaming Server license may use this file in accordance with the
# Flumotion Advanced Streaming Server Commercial License Agreement.
# See "LICENSE.Flumotion" in the source distribution for more information.

# Headers in this file shall remain intact.

"""logging used by Flumotion, inspired by GStreamer

Just like in GStreamer, five levels of log information are defined.
These are, in order of decreasing verbosity: log, debug, info, warning, error.

API Stability: stabilizing

Maintainer: U{Thomas Vander Stichele <thomas at apestaart dot org>}
"""

from flumotion.extern.log import log as externlog
from flumotion.extern.log.log import *

__version__ = "$Rev: 6964 $"


def init():
    externlog.init('FLU_DEBUG')
    externlog.setPackageScrubList('flumotion', 'twisted')

# backwards-compatible functions
setFluDebug = externlog.setDebug
# for pb unit tests
_getTheFluLogObserver = externlog._getTheTwistedLogObserver
