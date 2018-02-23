# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/header/AccountPopover.py
import BigWorld
from adisp import process
from gui.Scaleform.genConsts.FORTIFICATION_ALIASES import FORTIFICATION_ALIASES
from gui.Scaleform.locale import RES_ICONS
from gui.prb_control.dispatcher import g_prbLoader
from helpers.i18n import makeString
from gui.LobbyContext import g_lobbyContext
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.framework import AppRef
from gui.Scaleform.daapi.view.lobby.popover.SmartPopOverView import SmartPopOverView
from gui.Scaleform.daapi.view.meta.AccountPopoverMeta import AccountPopoverMeta
from gui.Scaleform.locale.MENU import MENU
from gui.shared import g_itemsCache, events
from gui.shared.event_bus import EVENT_BUS_SCOPE
from gui.shared.ClanCache import g_clanCache
from gui.shared.fortifications import isStartingScriptDone
from PlayerEvents import g_playerEvents

class AccountPopover(AccountPopoverMeta, SmartPopOverView, View, AppRef):

    def __init__(self, _):
        super(AccountPopover, self).__init__()

    def openProfile(self):
        self.__showProfileWindow()
        self.destroy()

    def openClanStatistic(self):
        self.fireEvent(events.ShowViewEvent(FORTIFICATION_ALIASES.FORT_CLAN_STATISTICS_WINDOW_EVENT), EVENT_BUS_SCOPE.LOBBY)
        self.destroy()

    def _populate(self):
        g_playerEvents.onCenterIsLongDisconnected += self.__onCenterIsLongDisconnected
        super(AccountPopover, self)._populate()
        self.__populateUserInfo()
        self.__populateClanEmblem()

    def _dispose(self):
        super(AccountPopover, self)._dispose()
        g_playerEvents.onCenterIsLongDisconnected -= self.__onCenterIsLongDisconnected

    def __populateUserInfo(self):
        self.__setUserInfo()
        self.__syncUserInfo()

    @process
    def __populateClanEmblem(self):
        yield lambda callback: callback(True)
        if g_clanCache.isInClan:
            clanEmblemID = yield g_clanCache.getClanEmblemID()
            if clanEmblemID is not None:
                self.as_setClanEmblemS(clanEmblemID)
        return

    def __showProfileWindow(self, ctx = None):
        self.fireEvent(events.LoadEvent(events.LoadEvent.LOAD_PROFILE, ctx or {}), scope=EVENT_BUS_SCOPE.LOBBY)

    def __setUserInfo(self):
        self.__setUserData()
        self.__setAchieves()
        self.__setClanData()
        self.__setCrewData()
        self.__setInfoButtonState()

    def __setUserData(self):
        userName = BigWorld.player().name
        self.__userData = {'fullName': g_lobbyContext.getPlayerFullName(userName, clanInfo=g_clanCache.clanInfo),
         'userName': userName,
         'clanAbbrev': g_clanCache.clanAbbrev}

    def __setAchieves(self):
        items = g_itemsCache.items
        randomStats = items.getAccountDossier().getRandomStats()
        winsEfficiency = randomStats.getWinsEfficiency()
        if winsEfficiency is None:
            winsEffLabel = '--'
        else:
            winsEffLabel = '%s %%' % BigWorld.wg_getNiceNumberFormat(winsEfficiency * 100)

        def _packStats(label, value, iconPath):
            return {'name': makeString('#menu:header/account/popover/achieves/%s' % label),
             'value': value,
             'icon': iconPath}

        self.__achieves = [_packStats('rating', BigWorld.wg_getIntegralFormat(items.stats.getGlobalRating()), RES_ICONS.RES_ICONS.MAPS_ICONS_STATISTIC_RATING), _packStats('battles', BigWorld.wg_getIntegralFormat(randomStats.getBattlesCount()), RES_ICONS.RES_ICONS.MAPS_ICONS_STATISTIC_RATIO), _packStats('wins', winsEffLabel, RES_ICONS.RES_ICONS.MAPS_ICONS_STATISTIC_FIGHTS)]
        return

    def __setClanData(self):
        if g_clanCache.isInClan:
            self.__clanData = {'formation': makeString(MENU.HEADER_ACCOUNT_POPOVER_CLAN_HEADER),
             'formationName': '%s [%s]' % (g_clanCache.clanName, g_clanCache.clanAbbrev),
             'position': g_clanCache.getClanRoleUserString(),
             'btnLabel': makeString(MENU.HEADER_ACCOUNT_POPOVER_CLAN_BTNLABEL) if isStartingScriptDone() else None,
             'btnEnabled': not BigWorld.player().isLongDisconnectedFromCenter}
        else:
            self.__clanData = None
        return

    def __setCrewData(self):
        if False:
            self.__crewData = {'formation': makeString(MENU.HEADER_ACCOUNT_POPOVER_CREW_HEADER),
             'formationName': '',
             'position': makeString(MENU.HEADER_ACCOUNT_POPOVER_CREW_POSITION_RECRUIT),
             'btnLabel': makeString(MENU.HEADER_ACCOUNT_POPOVER_CREW_BTNLABEL),
             'btnEnabled': True}
        else:
            self.__crewData = None
        return

    def __syncUserInfo(self):
        self.as_setDataS(self.__userData, g_itemsCache.items.stats.isTeamKiller, self.__achieves, self.__infoBtnEnabled, self.__clanData, self.__crewData)

    def __setInfoButtonState(self):
        self.__infoBtnEnabled = True
        prbDispatcher = g_prbLoader.getDispatcher()
        if prbDispatcher:
            state = prbDispatcher.getFunctionalState()
            self.__infoBtnEnabled = not state.isNavigationDisabled()

    def __onCenterIsLongDisconnected(self, *args):
        self.__setClanData()
        self.__syncUserInfo()
