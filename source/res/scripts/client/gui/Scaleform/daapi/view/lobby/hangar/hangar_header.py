# Python bytecode 2.7 (decompiled from Python 2.7)
# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/hangar/hangar_header.py
import constants
from CurrentVehicle import g_currentVehicle
from gui.ClientUpdateManager import g_clientUpdateManager
from gui.Scaleform.daapi.view.lobby.missions.regular import missions_page
from gui.Scaleform.daapi.view.meta.HangarHeaderMeta import HangarHeaderMeta
from gui.Scaleform.genConsts.TOOLTIPS_CONSTANTS import TOOLTIPS_CONSTANTS
from gui.Scaleform.locale.MENU import MENU
from gui.Scaleform.locale.RES_ICONS import RES_ICONS
from gui.Scaleform.locale.TOOLTIPS import TOOLTIPS
from gui.server_events.events_dispatcher import showMissionsForCurrentVehicle, showPersonalMission, showMissionsElen
from gui.shared.formatters import text_styles, icons
from gui.shared.utils.functions import makeTooltip
from gui.shared import events
from gui.shared.event_bus import EVENT_BUS_SCOPE
from helpers import dependency
from helpers.i18n import makeString as _ms
from gui.shared.personality import ServicesLocator
from skeletons.gui.shared import IItemsCache
from skeletons.gui.server_events import IEventsCache
from skeletons.gui.game_control import IQuestsController
from skeletons.gui.event_boards_controllers import IEventBoardController
from skeletons.connection_mgr import IConnectionManager
from gui.prb_control import prb_getters
from skeletons.gui.lobby_context import ILobbyContext
from gui.prb_control.entities.listener import IGlobalListener
from gui.event_boards.listener import IEventBoardsListener

class WIDGET_PQ_STATE(object):
    DISABLED = 0
    UNAVAILABLE = 1
    COMPLETED = 2
    DONE = 4
    AVAILABLE = 8
    IN_PROGRESS = 16
    AWARD = 32


class LABEL_STATE(object):
    ACTIVE = 'active'
    EMPTY = 'empty'
    INACTIVE = 'inactive'
    ALL_DONE = 'all_done'


def _findPersonalQuestsState(eventsCache, vehicle):
    state = WIDGET_PQ_STATE.DISABLED
    vehicleLvl = vehicle.level
    vehicleType = vehicle.type
    for tile in eventsCache.personalMissions.getOperations().itervalues():
        for chainID, chain in tile.getQuests().iteritems():
            if tile.getChainVehicleClass(chainID) != vehicleType:
                continue
            for quest in chain.itervalues():
                if vehicleLvl < quest.getVehMinLevel():
                    continue
                if quest.isFullCompleted():
                    state |= WIDGET_PQ_STATE.DONE
                    continue
                if quest.isMainCompleted():
                    state |= WIDGET_PQ_STATE.COMPLETED
                    if not quest.isInProgress():
                        continue
                state |= WIDGET_PQ_STATE.UNAVAILABLE
                if quest.canBeSelected():
                    state |= WIDGET_PQ_STATE.AVAILABLE
                if quest.isInProgress():
                    return (state | WIDGET_PQ_STATE.IN_PROGRESS,
                     quest,
                     chain,
                     tile)

    return (state,
     None,
     None,
     None)


class HangarHeader(HangarHeaderMeta, IGlobalListener, IEventBoardsListener):
    _itemsCache = dependency.descriptor(IItemsCache)
    _eventsCache = dependency.descriptor(IEventsCache)
    _questController = dependency.descriptor(IQuestsController)
    _eventsController = dependency.descriptor(IEventBoardController)
    _connectionMgr = dependency.descriptor(IConnectionManager)
    _lobbyContext = dependency.descriptor(ILobbyContext)

    def __init__(self):
        super(HangarHeader, self).__init__()
        self._currentVehicle = None
        self._personalQuestID = None
        return

    def showPersonalQuests(self):
        showPersonalMission(missionID=self._personalQuestID)

    def showCommonQuests(self):
        missions_page.setHideDoneFilter()
        showMissionsForCurrentVehicle()

    def showEventQuests(self, eventQuestsID):
        showMissionsElen(eventQuestsID)

    def onUpdateHangarFlag(self):
        self.update()

    def update(self, *args):
        self._personalQuestID = None
        headerVO = self._makeHeaderVO()
        self.as_setDataS(headerVO)
        return

    def _populate(self):
        super(HangarHeader, self)._populate()
        self._currentVehicle = g_currentVehicle
        self._eventsCache.onSyncCompleted += self.update
        self._eventsCache.onProgressUpdated += self.update
        g_clientUpdateManager.addCallbacks({'inventory.1': self.update,
         'stats.tutorialsCompleted': self.update})
        if self._eventsController:
            self._eventsController.addListener(self)
        self.addListener(events.TutorialEvent.SET_HANGAR_HEADER_ENABLED, self.__onSetHangarHeaderEnabled, scope=EVENT_BUS_SCOPE.LOBBY)
        self._lobbyContext.getServerSettings().onServerSettingsChange += self.__onServerSettingChanged

    def _dispose(self):
        g_clientUpdateManager.removeObjectCallbacks(self)
        self._eventsCache.onSyncCompleted -= self.update
        self._eventsCache.onProgressUpdated -= self.update
        self._currentVehicle = None
        self._personalQuestID = None
        if self._eventsController:
            self._eventsController.removeListener(self)
        self.removeListener(events.TutorialEvent.SET_HANGAR_HEADER_ENABLED, self.__onSetHangarHeaderEnabled, scope=EVENT_BUS_SCOPE.LOBBY)
        self._lobbyContext.getServerSettings().onServerSettingsChange -= self.__onServerSettingChanged
        super(HangarHeader, self)._dispose()
        return

    def _makeHeaderVO(self):
        if self.app.tutorialManager.hangarHeaderEnabled and self._currentVehicle.isPresent():
            vehicle = self._currentVehicle.item
            headerVO = {'tankType': '{}_elite'.format(vehicle.type) if vehicle.isElite else vehicle.type,
             'tankInfo': text_styles.concatStylesToMultiLine(text_styles.promoSubTitle(vehicle.shortUserName), text_styles.stats(MENU.levels_roman(vehicle.level))),
             'isPremIGR': vehicle.isPremiumIGR,
             'isVisible': True,
             'isBeginner': False}
            self._addQuestsToHeaderVO(headerVO, vehicle)
        else:
            headerVO = {'isVisible': False}
        return headerVO

    def _addQuestsToHeaderVO(self, headerVO, vehicle):
        headerVO.update(self.__getBattleQuestsVO(vehicle))
        headerVO.update(self.__getPersonalQuestsVO(vehicle))
        headerVO.update(self.__getElenQuestsVO(vehicle))

    def __onServerSettingChanged(self, diff):
        if 'elenSettings' in diff:
            self.update()

    def __getBattleQuestsVO(self, vehicle):
        quests = self._questController.getQuestForVehicle(vehicle)
        totalCount = len(quests)
        completedQuests = len([ q for q in quests if q.isCompleted() ])
        if totalCount > 0:
            if completedQuests != totalCount:
                label = _ms(MENU.hangarHeaderBattleQuestsLabel(LABEL_STATE.ACTIVE), total=totalCount - completedQuests)
            else:
                label = icons.makeImageTag(RES_ICONS.MAPS_ICONS_LIBRARY_OUTLINE_QUESTS_ALL_DONE)
            commonQuestsIcon = RES_ICONS.MAPS_ICONS_LIBRARY_OUTLINE_QUESTS_AVAILABLE
        else:
            commonQuestsIcon = RES_ICONS.MAPS_ICONS_LIBRARY_OUTLINE_QUESTS_DISABLED
            label = ''
        return {'commonQuestsLabel': label,
         'commonQuestsIcon': commonQuestsIcon,
         'commonQuestsTooltip': TOOLTIPS_CONSTANTS.QUESTS_PREVIEW,
         'commonQuestsEnable': totalCount > 0,
         'commonQuestsVisible': True}

    def __getPersonalQuestsVO(self, vehicle):
        if not self._lobbyContext.getServerSettings().isPersonalMissionsEnabled():
            return {'personalQuestsLabel': _ms(MENU.hangarHeaderPersonalQuestsLabel(LABEL_STATE.INACTIVE)),
             'personalQuestsIcon': RES_ICONS.vehicleTypeInactiveOutline(vehicle.type),
             'personalQuestsEnable': False,
             'personalQuestsVisible': True,
             'isPersonalReward': False,
             'personalQuestsTooltip': None,
             'personalQuestsTooltipIsSpecial': False}
        else:
            pqState, quest, chain, tile = _findPersonalQuestsState(self._eventsCache, vehicle)
            enable = True
            if pqState & WIDGET_PQ_STATE.AWARD:
                icon = RES_ICONS.MAPS_ICONS_LIBRARY_OUTLINE_REWARD
                labelState = LABEL_STATE.ACTIVE
                tooltip = makeTooltip(_ms(TOOLTIPS.HANGAR_HEADER_PERSONALQUESTS_AWARD_HEADER, tileName=tile.getUserName()), _ms(TOOLTIPS.HANGAR_HEADER_PERSONALQUESTS_AWARD_BODY, chainName=_ms(MENU.classesShort(tile.getChainMajorTag(quest.getChainID())))))
            elif pqState & WIDGET_PQ_STATE.IN_PROGRESS:
                icon = RES_ICONS.vehicleTypeOutline(vehicle.type)
                labelState = LABEL_STATE.ACTIVE
                tooltip = TOOLTIPS_CONSTANTS.PERSONAL_QUESTS_PREVIEW
            elif pqState & WIDGET_PQ_STATE.AVAILABLE:
                icon = RES_ICONS.MAPS_ICONS_LIBRARY_OUTLINE_PLUS
                labelState = LABEL_STATE.EMPTY
                tooltip = TOOLTIPS.HANGAR_HEADER_PERSONALQUESTS_AVAILABLE
            elif pqState & WIDGET_PQ_STATE.COMPLETED:
                icon = RES_ICONS.vehicleTypeOutline(vehicle.type)
                labelState = LABEL_STATE.ALL_DONE
                if pqState & WIDGET_PQ_STATE.UNAVAILABLE:
                    tooltip = TOOLTIPS.HANGAR_HEADER_PERSONALQUESTS_UNAVAILABLE
                else:
                    tooltip = TOOLTIPS.HANGAR_HEADER_PERSONALQUESTS_COMPLETED
            elif pqState & WIDGET_PQ_STATE.DONE:
                icon = RES_ICONS.vehicleTypeInactiveOutline(vehicle.type)
                labelState = LABEL_STATE.INACTIVE
                tooltip = TOOLTIPS.HANGAR_HEADER_PERSONALQUESTS_DONE
                enable = False
            else:
                icon = RES_ICONS.vehicleTypeInactiveOutline(vehicle.type)
                labelState = LABEL_STATE.INACTIVE
                tooltip = TOOLTIPS.HANGAR_HEADER_PERSONALQUESTS_DISABLED
                enable = False
            if all((quest, chain, tile)):
                self._personalQuestID = quest.getID()
                ctx = {'current': quest.getInternalID()}
            else:
                self._personalQuestID = None
                ctx = {'icon': icons.makeImageTag(RES_ICONS.MAPS_ICONS_LIBRARY_OUTLINE_QUESTS_ALL_DONE)}
            return {'personalQuestsLabel': _ms(MENU.hangarHeaderPersonalQuestsLabel(labelState), **ctx),
             'personalQuestsIcon': icon,
             'personalQuestsEnable': enable,
             'personalQuestsVisible': True,
             'isPersonalReward': bool(pqState & WIDGET_PQ_STATE.AWARD),
             'personalQuestsTooltip': tooltip,
             'personalQuestsTooltipIsSpecial': bool(pqState & WIDGET_PQ_STATE.IN_PROGRESS)}

    def __getElenQuestsVO(self, vehicle):
        eventsData = self._eventsController.getEventsSettingsData()
        hangarFlagData = self._eventsController.getHangarFlagData()
        isElenEnabled = ServicesLocator.lobbyContext.getServerSettings().isElenEnabled()
        dataError = eventsData is None or hangarFlagData is None
        if dataError or not isElenEnabled or not eventsData.hasActiveEvents() or hangarFlagData.isSpecialAccount():
            return {'isEvent': False}
        else:
            currentEvent = eventsData.getEventForVehicle(vehicle.intCD)
            if currentEvent is not None and currentEvent.isStarted() and not currentEvent.isFinished():
                eventId = currentEvent.getEventID()
                isRegistered = hangarFlagData.isRegistered(eventId)
                hasAnotherActiveEvents = eventsData.hasAnotherActiveEvents(eventId)
                regIsFinished = currentEvent.isRegistrationFinished()
                notValidEvent = regIsFinished and not isRegistered or hangarFlagData.wasCanceled(eventId)
                if notValidEvent and not hasAnotherActiveEvents:
                    return {'isEvent': False}
                if notValidEvent and hasAnotherActiveEvents:
                    enable = False
                else:
                    enable = True
            else:
                if not eventsData.hasActiveEventsByState(hangarFlagData.getHangarFlags()):
                    return {'isEvent': False}
                eventId = None
                enable = False
            if enable:
                eventQuestsTooltip = TOOLTIPS_CONSTANTS.EVENT_QUESTS_PREVIEW
                eventQuestsTooltipIsSpecial = True
                battleType = currentEvent.getBattleType()
                wrongBattleType = self.prbEntity.getEntityType() != battleType
                inSquadState = self.prbDispatcher.getFunctionalState().isInUnit(constants.PREBATTLE_TYPE.SQUAD)
                if inSquadState:
                    unit = prb_getters.getUnit(safe=True)
                    if len(unit.getMembers()) == 1:
                        inSquadState = False
                wrongSquadState = inSquadState and not currentEvent.getIsSquadAllowed()
                noserver = not currentEvent.isAvailableServer(self._connectionMgr.peripheryID)
                hasWarning = wrongBattleType or noserver or wrongSquadState
                registrationWillExpiredSoon = currentEvent.isRegistrationFinishSoon()
                endSoonWarning = currentEvent.isEndSoon() and not hasWarning and isRegistered
                if registrationWillExpiredSoon and not isRegistered or endSoonWarning:
                    eventQuestsLabel = icons.makeImageTag(RES_ICONS.MAPS_ICONS_EVENTBOARDS_FLAGICONS_TIME_ICON)
                elif hasWarning and isRegistered:
                    eventQuestsLabel = icons.makeImageTag(RES_ICONS.MAPS_ICONS_EVENTBOARDS_FLAGICONS_ALERT_ICON)
                else:
                    eventQuestsLabel = icons.makeImageTag(RES_ICONS.MAPS_ICONS_EVENTBOARDS_FLAGICONS_ICON_FLAG)
                if isRegistered:
                    eventQuestsIcon = RES_ICONS.MAPS_ICONS_EVENTBOARDS_FLAGICONS_CUP_ICON
                else:
                    eventQuestsIcon = RES_ICONS.MAPS_ICONS_EVENTBOARDS_FLAGICONS_CROSS
            else:
                if not eventsData.hasActiveEvents():
                    return {'isEvent': False}
                eventQuestsTooltip = TOOLTIPS.HANGAR_ELEN_BOTTOM_NOEVENTS
                eventQuestsTooltipIsSpecial = False
                eventQuestsLabel = '--'
                eventQuestsIcon = RES_ICONS.MAPS_ICONS_EVENTBOARDS_FLAGICONS_CUP_DISABLE_ICON
            res = {'isEvent': True,
             'eventQuestsEnable': enable,
             'eventQuestsIcon': eventQuestsIcon,
             'eventQuestsLabel': eventQuestsLabel,
             'eventQuestsTooltip': eventQuestsTooltip,
             'eventQuestsTooltipIsSpecial': eventQuestsTooltipIsSpecial,
             'eventQuestsID': eventId}
            return res

    def __onSetHangarHeaderEnabled(self, _=None):
        self.update()
