# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/prb_windows/sf_settings.py
from gui.Scaleform.framework.managers.containers import POP_UP_CRITERIA
from gui.Scaleform.framework.managers.loaders import PackageBusinessHandler
from gui.Scaleform.framework import ViewSettings, GroupedViewSettings, ViewTypes, ScopeTemplates
from gui.Scaleform.genConsts.PREBATTLE_ALIASES import PREBATTLE_ALIASES
from gui.shared import EVENT_BUS_SCOPE
from gui.shared.events import ShowWindowEvent

def getViewSettings():
    from gui.Scaleform.daapi.view.lobby.prb_windows.BattleSessionList import BattleSessionList
    from gui.Scaleform.daapi.view.lobby.prb_windows.BattleSessionWindow import BattleSessionWindow
    from gui.Scaleform.daapi.view.lobby.prb_windows.PrbSendInvitesWindow import PrbSendInvitesWindow
    from gui.Scaleform.daapi.view.lobby.prb_windows import invite_windows
    from gui.Scaleform.daapi.view.lobby.prb_windows.SquadWindow import SquadWindow
    from gui.Scaleform.daapi.view.lobby.prb_windows.CompanyListView import CompanyListView
    from gui.Scaleform.daapi.view.lobby.prb_windows.CompanyMainWindow import CompanyMainWindow
    from gui.Scaleform.daapi.view.lobby.prb_windows.CompanyRoomView import CompanyRoomView
    from gui.Scaleform.daapi.view.lobby.prb_windows.SquadView import SquadView
    return [GroupedViewSettings(PREBATTLE_ALIASES.SEND_INVITES_WINDOW_PY, PrbSendInvitesWindow, 'prbSendInvitesWindow.swf', ViewTypes.WINDOW, '', ShowWindowEvent.SHOW_SEND_INVITES_WINDOW, ScopeTemplates.DEFAULT_SCOPE),
     GroupedViewSettings(PREBATTLE_ALIASES.AUTO_INVITE_WINDOW_PY, invite_windows.AutoInviteWindow, 'receivedInviteWindow.swf', ViewTypes.WINDOW, 'receivedInviteWindow', None, ScopeTemplates.DEFAULT_SCOPE),
     GroupedViewSettings(PREBATTLE_ALIASES.SQUAD_WINDOW_PY, SquadWindow, 'squadWindow.swf', ViewTypes.WINDOW, '', ShowWindowEvent.SHOW_SQUAD_WINDOW, ScopeTemplates.DEFAULT_SCOPE),
     GroupedViewSettings(PREBATTLE_ALIASES.COMPANY_WINDOW_PY, CompanyMainWindow, 'companyMainWindow.swf', ViewTypes.WINDOW, '', ShowWindowEvent.SHOW_COMPANY_MAIN_WINDOW, ScopeTemplates.DEFAULT_SCOPE),
     GroupedViewSettings(PREBATTLE_ALIASES.BATTLE_SESSION_ROOM_WINDOW_PY, BattleSessionWindow, 'battleSessionWindow.swf', ViewTypes.WINDOW, '', ShowWindowEvent.SHOW_BATTLE_SESSION_WINDOW, ScopeTemplates.DEFAULT_SCOPE),
     GroupedViewSettings(PREBATTLE_ALIASES.BATTLE_SESSION_LIST_WINDOW_PY, BattleSessionList, 'battleSessionList.swf', ViewTypes.WINDOW, '', ShowWindowEvent.SHOW_BATTLE_SESSION_LIST, ScopeTemplates.DEFAULT_SCOPE),
     ViewSettings(PREBATTLE_ALIASES.SQUAD_VIEW_PY, SquadView, None, ViewTypes.COMPONENT, None, ScopeTemplates.DEFAULT_SCOPE),
     ViewSettings(PREBATTLE_ALIASES.COMPANY_LIST_VIEW_PY, CompanyListView, None, ViewTypes.COMPONENT, None, ScopeTemplates.DEFAULT_SCOPE),
     ViewSettings(PREBATTLE_ALIASES.COMPANY_ROOM_VIEW_PY, CompanyRoomView, None, ViewTypes.COMPONENT, None, ScopeTemplates.DEFAULT_SCOPE)]


def getBusinessHandlers():
    return [PrbPackageBusinessHandler()]


class PrbPackageBusinessHandler(PackageBusinessHandler):

    def __init__(self):
        listeners = [(ShowWindowEvent.SHOW_SQUAD_WINDOW, self.__showSquadWindow),
         (ShowWindowEvent.SHOW_COMPANY_MAIN_WINDOW, self.__showCompanyMainWindow),
         (ShowWindowEvent.SHOW_BATTLE_SESSION_WINDOW, self.__showBattleSessionWindow),
         (ShowWindowEvent.SHOW_BATTLE_SESSION_LIST, self.__showBattleSessionList),
         (ShowWindowEvent.SHOW_SEND_INVITES_WINDOW, self.__showSendInvitesWindow),
         (ShowWindowEvent.SHOW_AUTO_INVITE_WINDOW, self.__showAutoInviteWindow)]
        super(PrbPackageBusinessHandler, self).__init__(listeners, EVENT_BUS_SCOPE.LOBBY)

    def __showBattleSessionWindow(self, _):
        viewAlias = PREBATTLE_ALIASES.BATTLE_SESSION_ROOM_WINDOW_PY
        self.app.loadView(viewAlias, viewAlias)

    def __showBattleSessionList(self, _):
        viewAlias = PREBATTLE_ALIASES.BATTLE_SESSION_LIST_WINDOW_PY
        self.app.loadView(viewAlias, viewAlias)

    def __showSquadWindow(self, event):
        alias = name = PREBATTLE_ALIASES.SQUAD_WINDOW_PY
        self.app.loadView(alias, name, event.ctx)

    def __showSendInvitesWindow(self, event):
        alias = name = PREBATTLE_ALIASES.SEND_INVITES_WINDOW_PY
        self.app.loadView(alias, name, event.ctx)

    def __showAutoInviteWindow(self, event):
        alias = PREBATTLE_ALIASES.AUTO_INVITE_WINDOW_PY
        name = 'autoInviteWindow_{0:n}'.format(event.ctx.get('prbID'))
        self.app.loadView(alias, name, event.ctx)

    def __showCompanyMainWindow(self, event):
        alias = name = PREBATTLE_ALIASES.COMPANY_WINDOW_PY
        windowContainer = self.app.containerManager.getContainer(ViewTypes.WINDOW)
        window = windowContainer.getView(criteria={POP_UP_CRITERIA.VIEW_ALIAS: alias})
        if window is not None:
            window.updateWindowState(event.ctx)
        else:
            self.app.loadView(alias, name, event.ctx if event else None)
        return
