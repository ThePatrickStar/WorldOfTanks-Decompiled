# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/meta/FortificationsViewMeta.py
from gui.Scaleform.framework.entities.View import View

class FortificationsViewMeta(View):
    """
    DO NOT MODIFY!
    Generated with yaml.
    __author__ = 'yaml_processor'
    @extends View
    """

    def onFortCreateClick(self):
        self._printOverrideError('onFortCreateClick')

    def onDirectionCreateClick(self):
        self._printOverrideError('onDirectionCreateClick')

    def onEscapePress(self):
        self._printOverrideError('onEscapePress')

    def as_loadViewS(self, flashAlias, pyAlias):
        return self.flashObject.as_loadView(flashAlias, pyAlias) if self._isDAAPIInited() else None

    def as_setCommonDataS(self, data):
        """
        :param data: Represented by FortificationVO (AS)
        """
        return self.flashObject.as_setCommonData(data) if self._isDAAPIInited() else None

    def as_waitingDataS(self, data):
        """
        :param data: Represented by FortWaitingVO (AS)
        """
        return self.flashObject.as_waitingData(data) if self._isDAAPIInited() else None
