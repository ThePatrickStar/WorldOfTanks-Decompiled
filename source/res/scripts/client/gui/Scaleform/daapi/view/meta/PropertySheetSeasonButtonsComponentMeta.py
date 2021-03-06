# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/meta/PropertySheetSeasonButtonsComponentMeta.py
from gui.Scaleform.framework.entities.BaseDAAPIComponent import BaseDAAPIComponent

class PropertySheetSeasonButtonsComponentMeta(BaseDAAPIComponent):

    def refreshSeasonButtons(self):
        self._printOverrideError('refreshSeasonButtons')

    def show(self):
        self._printOverrideError('show')

    def refresh(self):
        self._printOverrideError('refresh')

    def hide(self):
        self._printOverrideError('hide')

    def as_setRendererDataS(self, data):
        return self.flashObject.as_setRendererData(data) if self._isDAAPIInited() else None
