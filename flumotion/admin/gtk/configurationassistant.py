# -*- Mode: Python -*-
# vi:si:et:sw=4:sts=4:ts=4
#
# Flumotion - a streaming media server
# Copyright (C) 2004,2005,2006,2007,2008 Fluendo, S.L. (www.fluendo.com).
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

"""Configuration Assistant - A graphical user interface to create a stream.


This simple drawing explains the basic user interface:

  +----------+---------------------------------+
  |          |             Title               |
  | Sidebar  |---------------------------------+
  |          |                                 |
  |          |                                 |
  |          |                                 |
  |          |         WizardStep              |
  |          |                                 |
  |          |                                 |
  |          |                                 |
  |          |                                 |
  |          |                                 |
  |          +---------------------------------+
  |          |            Buttons              |
  +----------+---------------------------------+

Sidebar shows the available and visited steps, it allows you to quickly
navigate back to a previous step.
Title and the sidebar name contains text / icon the wizard step can set.
Buttons contain navigation and help.

Most WizardSteps are loaded over the network from the manager (to the admin
client where the code runs).
"""
import gettext
import os
import sets
import webbrowser

import gtk
from gtk import gdk
from twisted.internet import defer

from flumotion.admin.assistant.save import AssistantSaver
from flumotion.admin.gtk.workerstep import WorkerWizardStep
from flumotion.admin.gtk.workerlist import WorkerList
from flumotion.common import errors, messages
from flumotion.common.common import pathToModuleName
from flumotion.common.documentation import getWebLink
from flumotion.common.i18n import N_, ngettext, gettexter
from flumotion.common.pygobject import gsignal
from flumotion.configure import configure
from flumotion.ui.wizard import SectionWizard, WizardStep


# pychecker doesn't like the auto-generated widget attrs
# or the extra args we name in callbacks
__pychecker__ = 'no-classattr no-argsused'
__version__ = "$Rev: 7805 $"
T_ = gettexter()
_ = gettext.gettext


# the denominator arg for all calls of this function was sniffed from
# the glade file's spinbutton adjustment


def _fraction_from_float(number, denominator):
    """
    Return a string to be used in serializing to XML.
    """
    return "%d/%d" % (number * denominator, denominator)


class WelcomeStep(WizardStep):
    """
    This step is showing an informative description which introduces
    the user to the configuration assistant.
    """
    name = "Welcome"
    title = _('Welcome')
    section = _('Welcome')
    icon = 'wizard.png'
    gladeFile = 'welcome-wizard.glade'
    docSection = 'help-configuration-assistant-welcome'
    docAnchor = ''
    docVersion = 'local'

    def getNext(self):
        return None


class ScenarioStep(WizardStep):
    """
    This step is showing a list of possible scenarios.
    The user will select the scenario he want to use,
    then the scenario itself will decide the future steps.
    """
    name = "Scenario"
    title = _('Scenario')
    section = _('Scenario')
    icon = 'wizard.png'
    gladeFile = 'scenario-wizard.glade'
    docSection = 'help-configuration-assistant-scenario'
    docAnchor = ''
    docVersion = 'local'

    # WizardStep

    def __init__(self, wizard):
        self._currentScenarioType = None
        self._radioGroup = None
        self._scenarioRadioButtons = []
        super(ScenarioStep, self).__init__(wizard)

    def setup(self):

        def addScenarios(list):
            for scenario in list:
                self.addScenario(_(scenario.getDescription()),
                                 scenario.getType())

            firstButton = self.scenarios_box.get_children()[0]
            firstButton.set_active(True)
            firstButton.toggled()
            firstButton.grab_focus()

        d = self.wizard.getAdminModel().getScenarios()
        d.addCallback(addScenarios)

        return d

    def getNext(self):
        self.wizard.waitForTask('get-next-step')
        self.wizard.cleanFutureSteps()

        def addScenarioSteps(scenarioClass):
            scenario = scenarioClass()
            scenario.addSteps(self.wizard)
            self.wizard.setScenario(scenario)
            self.wizard.taskFinished()

        d = self.wizard.getWizardScenario(self._currentScenarioType)
        d.addCallback(addScenarioSteps)

        return d

    # Public

    def addScenario(self, scenarioDesc, scenarioType):
        """
        Adds a new entry to the scenarios list of the wizard.

        @param scenarioDesc: Description that will be shown on the list.
        @type  scenarioDesc: str
        @param scenarioType: The type of the scenario we are adding.
        @type  scenarioType: str
        """
        button = gtk.RadioButton(self._radioGroup, scenarioDesc)
        button.connect('toggled',
                       self._on_radiobutton__toggled,
                       scenarioType)
        button.connect('activate',
                       self._on_radiobutton__activate)

        self.scenarios_box.pack_start(button, False, False)
        button.show()

        if self._radioGroup is None:
            self._radioGroup = button

    # Private

    # Callbacks

    def _on_radiobutton__activate(self, radio):
        self.wizard.goNext()

    def _on_radiobutton__toggled(self, radio, scenarioType):
        if radio.get_active():
            self._currentScenarioType = scenarioType


class ConfigurationAssistant(SectionWizard):
    """This is the main configuration assistant class,
    it is responsible for::
    - executing tasks which will block the ui
    - showing a worker list in the UI
    - communicating with the manager, fetching bundles
      and registry information
    - running check defined by a step in a worker, for instance
      querying for hardware devices and their capabilities
    It extends SectionWizard which provides the basic user interface, such
    as sidebar, buttons, title bar and basic step navigation.
    """
    gsignal('finished', str)

    def __init__(self, parent=None):
        SectionWizard.__init__(self, parent)
        self.connect('help-clicked', self._on_assistant__help_clicked)
        # Set the name of the toplevel window, this is used by the
        # ui unittest framework
        self.window1.set_name('ConfigurationAssistant')
        self.message_area.disableTimestamps()

        self._cursorWatch = gdk.Cursor(gdk.WATCH)
        self._tasks = []
        self._adminModel = None
        self._workerHeavenState = None
        self._lastWorker = 0 # combo id last worker from step to step
        self._stepWorkers = {}
        self._scenario = None
        self._existingComponentNames = []
        self._porters = []
        self._mountPoints = []
        self._consumers = {}

        self._workerList = WorkerList()
        self.top_vbox.pack_start(self._workerList, False, False)
        self._workerList.connect('worker-selected',
                                  self.on_combobox_worker_changed)

    # SectionWizard

    def completed(self):
        saver = AssistantSaver()
        saver.setFlowName('default')
        saver.setExistingComponentNames(self._existingComponentNames)
        self._scenario.save(self, saver)

        xml = saver.getXML()
        self.emit('finished', xml)

    def destroy(self):
        SectionWizard.destroy(self)
        self._adminModel = None

    def beforeShowStep(self, step):
        if isinstance(step, WorkerWizardStep):
            self._workerList.show()
            self._workerList.notifySelected()
        else:
            self._workerList.hide()

        self._fetchDescription(step)
        self._setupWorker(step, self._workerList.getWorker())

    def prepareNextStep(self, step):
        self._setupWorker(step, self._workerList.getWorker())
        SectionWizard.prepareNextStep(self, step)

    def blockNext(self, block):
        # Do not block/unblock if we have tasks running
        if self._tasks:
            return
        SectionWizard.blockNext(self, block)

    # Public API

    # FIXME: Remove this and make fgc create a new scenario

    def addInitialSteps(self):
        """Add the step sections of the wizard, can be
        overridden in a subclass
        """
        # These two steps are independent of the scenarios, they
        # should always be added.
        self.addStepSection(WelcomeStep)
        self.addStepSection(ScenarioStep)

    def setScenario(self, scenario):
        """Sets the current scenario of the assistant.
        Normally called by ScenarioStep to tell the assistant the
        current scenario just after creating it.
        @param scenario: the scenario of the assistant
        @type scenario: a L{flumotion.admin.assistant.scenarios.Scenario}
          subclass
        """
        self._scenario = scenario

    def getScenario(self):
        """Fetches the currently set scenario of the assistant.
        @returns scenario: the scenario of the assistant
        @rtype: a L{flumotion.admin.assistant.scenarios.Scenario} subclass
        """
        return self._scenario

    def setWorkerHeavenState(self, workerHeavenState):
        """
        Sets the worker heaven state of the assistant
        @param workerHeavenState: the worker heaven state
        @type workerHeavenState: L{WorkerComponentUIState}
        """
        self._workerHeavenState = workerHeavenState
        self._workerList.setWorkerHeavenState(workerHeavenState)

    def setAdminModel(self, adminModel):
        """
        Sets the admin model of the assistant
        @param adminModel: the admin model
        @type adminModel: L{AdminModel}
        """
        self._adminModel = adminModel

    def setHTTPPorters(self, porters):
        """
        Sets the list of currently configured porters so
        we can reuse them for future streamers.

        @param porters: list of porters
        @type porters : list of L{flumotion.admin.assistant.models.Porter}
        """

        self._porters = porters

    def getHTTPPorters(self):
        """
        Obtains the list of the currently configured porters.

        @rtype : list of L{flumotion.admin.assistant.models.Porter}
        """
        return self._porters

    def addMountPoint(self, worker, port, mount_point, consumer=None):
        """
        Marks a mount point as used on the given worker and port.
        If a consumer name is provided it means we are changing the
        mount point for that consumer and that we should keep track of
        it for further modifications.

        @param worker   : The worker where the mount_point is configured.
        @type  worker   : str
        @param port     : The port where the streamer should be listening.
        @type  port     : int
        @param mount_point : The mount point where the data will be served.
        @type  mount_point : str
        @param consumer : The consumer that is changing its mountpoint.
        @type  consumer : str

        @returns : True if the mount point is not used and has been
                   inserted correctly, False otherwise.
        @rtype   : boolean
        """
        if not worker or not port or not mount_point:
            return False

        if consumer in self._consumers:
            oldData = self._consumers[consumer]
            if oldData in self._mountPoints:
                self._mountPoints.remove(oldData)

        data = (worker, port, mount_point)

        if data in self._mountPoints:
            return False

        self._mountPoints.append(data)

        if consumer:
            self._consumers[consumer] = data

        return True

    def getAdminModel(self):
        """Gets the admin model of the assistant
        @returns adminModel: the admin model
        @rtype adminModel: L{AdminModel}
        """
        return self._adminModel

    def waitForTask(self, taskName):
        """Instruct the assistant that we're waiting for a task
        to be finished. This changes the cursor and prevents
        the user from continuing moving forward.
        Each call to this method should have another call
        to taskFinished() when the task is actually done.
        @param taskName: name of the name
        @type taskName: string
        """
        self.info("waiting for task %s" % (taskName, ))
        if not self._tasks:
            if self.window1.window is not None:
                self.window1.window.set_cursor(self._cursorWatch)
            self.blockNext(True)
        self._tasks.append(taskName)

    def taskFinished(self, blockNext=False):
        """Instruct the assistant that a task was finished.
        @param blockNext: if we should still next when done
        @type blockNext: boolean
        """
        if not self._tasks:
            raise AssertionError(
                "Stray call to taskFinished(), forgot to call waitForTask()?")

        taskName = self._tasks.pop()
        self.info("task %s has now finished" % (taskName, ))
        if not self._tasks:
            self.window1.window.set_cursor(None)
            self.blockNext(blockNext)

    def pendingTask(self):
        """Returns true if there are any pending tasks
        @returns: if there are pending tasks
        @rtype: bool
        """
        return bool(self._tasks)

    def checkElements(self, workerName, *elementNames):
        """Check if the given list of GStreamer elements exist on the
        given worker.
        @param workerName: name of the worker to check on
        @type workerName: string
        @param elementNames: names of the elements to check
        @type elementNames: list of strings
        @returns: a deferred returning a tuple of the missing elements
        @rtype: L{twisted.internet.defer.Deferred}
        """
        if not self._adminModel:
            self.debug('No admin connected, not checking presence of elements')
            return

        asked = sets.Set(elementNames)

        def _checkElementsCallback(existing, workerName):
            existing = sets.Set(existing)
            self.taskFinished()
            return tuple(asked.difference(existing))

        self.waitForTask('check elements %r' % (elementNames, ))
        d = self._adminModel.checkElements(workerName, elementNames)
        d.addCallback(_checkElementsCallback, workerName)
        return d

    def requireElements(self, workerName, *elementNames):
        """Require that the given list of GStreamer elements exists on the
        given worker. If the elements do not exist, an error message is
        posted and the next button remains blocked.
        @param workerName: name of the worker to check on
        @type workerName: string
        @param elementNames: names of the elements to check
        @type elementNames: list of strings
        @returns: element name
        @rtype: deferred -> list of strings
        """
        if not self._adminModel:
            self.debug('No admin connected, not checking presence of elements')
            return

        self.debug('requiring elements %r' % (elementNames, ))
        f = ngettext("Checking the existence of GStreamer element '%s' "
                     "on %s worker.",
                     "Checking the existence of GStreamer elements '%s' "
                     "on %s worker.",
                     len(elementNames))
        msg = messages.Info(T_(f, "', '".join(elementNames), workerName),
                            mid='require-elements')

        self.add_msg(msg)

        def gotMissingElements(elements, workerName):
            self.clear_msg('require-elements')

            if elements:
                self.warning('elements %r do not exist' % (elements, ))
                f = ngettext("Worker '%s' is missing GStreamer element '%s'.",
                    "Worker '%s' is missing GStreamer elements '%s'.",
                    len(elements))
                message = messages.Error(T_(f, workerName,
                    "', '".join(elements)))
                message.add(T_(N_("\n"
                    "Please install the necessary GStreamer plug-ins that "
                    "provide these elements and restart the worker.")))
                message.add(T_(N_("\n\n"
                    "You will not be able to go forward using this worker.")))
                message.id = 'element' + '-'.join(elementNames)
                self.add_msg(message)
            self.taskFinished(bool(elements))
            return elements

        self.waitForTask('require elements %r' % (elementNames, ))
        d = self.checkElements(workerName, *elementNames)
        d.addCallback(gotMissingElements, workerName)

        return d

    def checkImport(self, workerName, moduleName):
        """Check if the given module can be imported.
        @param workerName:  name of the worker to check on
        @type workerName: string
        @param moduleName:  name of the module to import
        @type moduleName: string
        @returns: a deferred firing None or Failure.
        @rtype: L{twisted.internet.defer.Deferred}
        """
        if not self._adminModel:
            self.debug('No admin connected, not checking presence of elements')
            return

        d = self._adminModel.checkImport(workerName, moduleName)
        return d

    def requireImport(self, workerName, moduleName, projectName=None,
                       projectURL=None):
        """Require that the given module can be imported on the given worker.
        If the module cannot be imported, an error message is
        posted and the next button remains blocked.
        @param workerName:  name of the worker to check on
        @type workerName: string
        @param moduleName:  name of the module to import
        @type moduleName: string
        @param projectName: name of the module to import
        @type projectName: string
        @param projectURL:  URL of the project
        @type projectURL: string
        @returns: a deferred firing None or Failure
        @rtype: L{twisted.internet.defer.Deferred}
        """
        if not self._adminModel:
            self.debug('No admin connected, not checking presence of elements')
            return

        self.debug('requiring module %s' % moduleName)

        def _checkImportErrback(failure):
            self.warning('could not import %s', moduleName)
            message = messages.Error(T_(N_(
                "Worker '%s' cannot import module '%s'."),
                workerName, moduleName))
            if projectName:
                message.add(T_(N_("\n"
                    "This module is part of '%s'."), projectName))
            if projectURL:
                message.add(T_(N_("\n"
                    "The project's homepage is %s"), projectURL))
            message.add(T_(N_("\n\n"
                "You will not be able to go forward using this worker.")))
            message.id = 'module-%s' % moduleName
            self.add_msg(message)
            self.taskFinished(True)

        d = self.checkImport(workerName, moduleName)
        d.addErrback(_checkImportErrback)
        return d

    # FIXME: maybe add id here for return messages ?

    def runInWorker(self, workerName, moduleName, functionName,
                    *args, **kwargs):
        """
        Run the given function and arguments on the selected worker.
        The given function should return a L{messages.Result}.

        @param workerName:   name of the worker to run the function in
        @type  workerName:   string
        @param moduleName:   name of the module where the function is found
        @type  moduleName:   string
        @param functionName: name of the function to run
        @type  functionName: string

        @returns: a deferred firing the Result's value.
        @rtype: L{twisted.internet.defer.Deferred}
        """
        self.debug('runInWorker(moduleName=%r, functionName=%r)' % (
            moduleName, functionName))
        admin = self._adminModel
        if not admin:
            self.warning('skipping runInWorker, no admin')
            return defer.fail(errors.FlumotionError('no admin'))

        if not workerName:
            self.warning('skipping runInWorker, no worker')
            return defer.fail(errors.FlumotionError('no worker'))

        def callback(result):
            self.debug('runInWorker callbacked a result')
            self.clear_msg(functionName)

            if not isinstance(result, messages.Result):
                msg = messages.Error(T_(
                    N_("Internal error: could not run check code on worker.")),
                    debug=('function %r returned a non-Result %r'
                           % (functionName, result)))
                self.add_msg(msg)
                self.taskFinished(True)
                raise errors.RemoteRunError(functionName, 'Internal error.')

            for m in result.messages:
                self.debug('showing msg %r' % m)
                self.add_msg(m)

            if result.failed:
                self.debug('... that failed')
                self.taskFinished(True)
                raise errors.RemoteRunFailure(functionName, 'Result failed')
            self.debug('... that succeeded')
            self.taskFinished()
            return result.value

        def errback(failure):
            self.debug('runInWorker errbacked, showing error msg')
            if failure.check(errors.RemoteRunError):
                debug = failure.value
            else:
                debug = "Failure while running %s.%s:\n%s" % (
                    moduleName, functionName, failure.getTraceback())

            msg = messages.Error(T_(
                N_("Internal error: could not run check code on worker.")),
                debug=debug)
            self.add_msg(msg)
            self.taskFinished(True)
            raise errors.RemoteRunError(functionName, 'Internal error.')

        self.waitForTask('run in worker: %s.%s(%r, %r)' % (
            moduleName, functionName, args, kwargs))
        d = admin.workerRun(workerName, moduleName,
                            functionName, *args, **kwargs)
        d.addErrback(errback)
        d.addCallback(callback)
        return d

    def getWizardEntry(self, componentType):
        """Fetches a assistant bundle from a specific kind of component
        @param componentType: the component type to get the assistant entry
          bundle from.
        @type componentType: string
        @returns: a deferred returning either::
          - factory of the component
          - noBundle error: if the component lacks a assistant bundle
        @rtype: L{twisted.internet.defer.Deferred}
        """
        self.waitForTask('get assistant entry %s' % (componentType, ))
        self.clear_msg('assistant-bundle')
        d = self._adminModel.callRemote(
            'getEntryByType', componentType, 'wizard')
        d.addCallback(self._gotEntryPoint)
        return d

    def getWizardScenario(self, scenarioType):
        """
        Fetches a scenario bundle from a specific kind of component.

        @param scenarioType: the scenario type to get the assistant entry
          bundle from.
        @type scenarioType: string
        @returns: a deferred returning either::
          - factory of the component
          - noBundle error: if the component lacks a assistant bundle
        @rtype: L{twisted.internet.defer.Deferred}
        """
        self.waitForTask('get assistant entry %s' % (scenarioType, ))
        self.clear_msg('assistant-bundle')
        d = self._adminModel.callRemote(
            'getScenarioByType', scenarioType, 'wizard')
        d.addCallback(self._gotEntryPoint)
        return d

    def getWizardPlugEntry(self, plugType):
        """Fetches a assistant bundle from a specific kind of plug
        @param plugType: the plug type to get the assistant entry
          bundle from.
        @type plugType: string
        @returns: a deferred returning either::
          - factory of the plug
          - noBundle error: if the plug lacks a assistant bundle
        @rtype: L{twisted.internet.defer.Deferred}
        """
        self.waitForTask('get assistant plug %s' % (plugType, ))
        self.clear_msg('assistant-bundle')
        d = self._adminModel.callRemote(
            'getPlugEntry', plugType, 'wizard')
        d.addCallback(self._gotEntryPoint)
        return d

    def getWizardEntries(self, wizardTypes=None, provides=None, accepts=None):
        """Queries the manager for a list of assistant entries matching the
        query.
        @param wizardTypes: list of component types to fetch, is usually
                            something like ['video-producer'] or
                            ['audio-encoder']
        @type  wizardTypes: list of str
        @param provides:    formats provided, eg ['jpeg', 'speex']
        @type  provides:    list of str
        @param accepts:     formats accepted, eg ['theora']
        @type  accepts:     list of str

        @returns: a deferred firing a list
                  of L{flumotion.common.componentui.WizardEntryState}
        @rtype: L{twisted.internet.defer.Deferred}
        """
        self.debug('querying wizard entries (wizardTypes=%r,provides=%r'
                   ',accepts=%r)'% (wizardTypes, provides, accepts))
        return self._adminModel.getWizardEntries(wizardTypes=wizardTypes,
                                                 provides=provides,
                                                 accepts=accepts)

    def setExistingComponentNames(self, componentNames):
        """Tells the assistant about the existing components available, so
        we can resolve naming conflicts when saving the configuration
        @param componentNames: existing component names
        @type componentNames: list of strings
        """
        self._existingComponentNames = componentNames

    def workerChangedForStep(self, step, workerName):
        """Tell a step that its worker changed.
        @param step: step which worker changed for
        @type step: a L{WorkerWizardStep} subclass
        @param workerName: name of the worker
        @type workerName: string
        """
        if self._stepWorkers.get(step) == workerName:
            return

        self.debug('calling %r.workerChanged' % step)
        step.workerChanged(workerName)
        self._stepWorkers[step] = workerName

    # Private

    def _gotEntryPoint(self, (filename, procname)):
        # The manager always returns / as a path separator, replace them with
        # the separator since the rest of our infrastructure depends on that.
        filename = filename.replace('/', os.path.sep)
        modname = pathToModuleName(filename)
        d = self._adminModel.getBundledFunction(modname, procname)
        self.clear_msg('assistant-bundle')
        self.taskFinished()
        return d

    def _setupWorker(self, step, worker):
        # get name of active worker
        self.debug('%r setting worker to %s' % (step, worker))
        step.worker = worker

    def _showHelpLink(self, section, anchor, docVersion):
        if docVersion == 'remote':
            version = self._adminModel.planet.get('version')
        else:
            version = configure.version

        url = getWebLink(section, anchor, version=version)
        webbrowser.open(url)

    def _fetchDescription(self, step):
        if not hasattr(step, 'model'):
            self.setStepDescription('')
            return

        def gotComponentEntry(entry):
            self.setStepDescription(entry.description)

        d = self._adminModel.callRemote(
            'getComponentEntry', step.model.componentType)
        d.addCallback(gotComponentEntry)

    # Callbacks

    def on_combobox_worker_changed(self, combobox, worker):
        self.debug('combobox_workerChanged, worker %r' % worker)
        if worker:
            self.clear_msg('worker-error')
            self._lastWorker = worker
            step = self.getCurrentStep()
            if step and isinstance(step, WorkerWizardStep):
                self._setupWorker(step, worker)
                self.workerChangedForStep(step, worker)
        else:
            msg = messages.Error(T_(
                    N_('All workers have logged out.\n'
                    'Make sure your Flumotion network is running '
                    'properly and try again.')),
                mid='worker-error')
            self.add_msg(msg)

    def _on_assistant__help_clicked(self, assistant, section, anchor, version):
        self._showHelpLink(section, anchor, version)
