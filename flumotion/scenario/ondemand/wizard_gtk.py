# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2008 Fluendo, S.L. (www.fluendo.com).
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

import gettext

from zope.interface import implements

from flumotion.admin.assistant.interfaces import IScenarioAssistantPlugin
from flumotion.scenario.steps.ondemandstep import OnDemandStep
from flumotion.scenario.steps.summarysteps import OndemandSummaryStep

_ = gettext.gettext


class OndemandAssistantPlugin(object):
    implements(IScenarioAssistantPlugin)
    short = _("Stream files on demand")
    description = _("""Allows you to serve a collection of files from disk.""")

    def __init__(self):
        self._consumer = None

    # IScenarioAssistantPlugin

    def addSteps(self, wizard):
        wizard.addStepSection(OnDemandStep)
        wizard.addStepSection(OndemandSummaryStep)

    def save(self, wizard, saver):
        ondemandStep = wizard.getStep('Demand')
        consumer = ondemandStep.getServerConsumer()
        saver.addServerConsumer(consumer, 'ondemand')
        self._consumer = consumer

    def getSelectComponentName(self):
        return self._consumer.name
