# Embedded file name: scripts/client/gui/Scaleform/daapi/view/BattleResultsWindow.py
import re
import math
import operator
import BigWorld
import ArenaType
from account_helpers.AccountSettings import AccountSettings
from debug_utils import LOG_ERROR, LOG_CURRENT_EXCEPTION, LOG_DEBUG
from gui.Scaleform.framework.entities.abstract.AbstractWindowView import AbstractWindowView
from gui.Scaleform.locale.BATTLE_RESULTS import BATTLE_RESULTS
from gui.shared.ClanCache import g_clanCache
from gui.shared.gui_items.dossier.achievements import MarkOnGunAchievement
from helpers import i18n
from adisp import async, process
from CurrentVehicle import g_currentVehicle
from constants import ARENA_BONUS_TYPE, IS_DEVELOPMENT, ARENA_GUI_TYPE, IGR_TYPE
from dossiers2.custom.records import RECORD_DB_IDS, DB_ID_TO_RECORD
from dossiers2.ui import achievements
from dossiers2.ui.achievements import ACHIEVEMENT_TYPE, MARK_ON_GUN_RECORD
from helpers import time_utils
from gui import makeHtmlString
from gui.LobbyContext import g_lobbyContext
from gui.shared import g_eventsCache, events
from gui.shared.utils.requesters import Requester, StatsRequesterr
from items import vehicles as vehicles_core, vehicles
from gui.shared.utils.requesters import StatsRequester
from gui.Scaleform.framework.entities.View import View
from gui.Scaleform.daapi.view.meta.BattleResultsMeta import BattleResultsMeta
from messenger.storage import storage_getter
from gui.shared.gui_items.dossier import getAchievementFactory
from gui.shared.gui_items.Vehicle import VEHICLE_BATTLE_TYPES_ORDER_INDICES
from items.vehicles import VEHICLE_CLASS_TAGS
RESULT_ = '#menu:finalStatistic/commonStats/resultlabel/{0}'
BATTLE_RESULTS_STR = '#battle_results:{0}'
FINISH_REASON = BATTLE_RESULTS_STR.format('finish/reason/{0}')
RESULT_LINE_STR = BATTLE_RESULTS_STR.format('details/calculations/{0}')
STATS_KEY_BASE = BATTLE_RESULTS_STR.format('team/stats/labels_{0}')
TIME_STATS_KEY_BASE = BATTLE_RESULTS_STR.format('details/time/lbl_{0}')
XP_TITLE = BATTLE_RESULTS_STR.format('common/details/xpTitle')
XP_TITLE_DAILY = BATTLE_RESULTS_STR.format('common/details/xpTitleFirstVictory')
MILEAGE_STR_KEY = BATTLE_RESULTS_STR.format('team/stats/mileage')
TIME_DURATION_STR = BATTLE_RESULTS_STR.format('details/time/value')
XP_MULTIPLIER_SIGN_KEY = BATTLE_RESULTS_STR.format('common/xpMultiplierSign')
EFFICIENCY_ALLIES_STR = BATTLE_RESULTS_STR.format('common/battleEfficiency/allies')
UNKNOWN_PLAYER_NAME_VALUE = '#ingame_gui:players_panel/unknown_name'
UNKNOWN_VEHICLE_NAME_VALUE = '#ingame_gui:players_panel/unknown_vehicle'
ARENA_TYPE = '#arenas:type/{0}/name'
ARENA_SPECIAL_TYPE = '#menu:loading/battleTypes/{0}'
VEHICLE_ICON_FILE = '../maps/icons/vehicle/{0}.png'
VEHICLE_ICON_SMALL_FILE = '../maps/icons/vehicle/small/{0}.png'
VEHICLE_NO_IMAGE_FILE_NAME = 'noImage'
ARENA_SCREEN_FILE = '../maps/icons/map/stats/{0}.png'
ARENA_NAME_PATTERN = '{0} - {1}'
LINE_BRAKE_STR = '<br/>'
STATS_KEYS = [('shots', True, None),
 ('hits', False, None),
 ('explosionHits', True, None),
 ('damageDealt', True, None),
 ('sniperDamageDealt', True, None),
 ('directHitsReceived', True, None),
 ('piercingsReceived', True, None),
 ('noDamageDirectHitsReceived', True, None),
 ('explosionHitsReceived', True, None),
 ('damageBlockedByArmor', True, None),
 ('teamHitsDamage', False, None),
 ('spotted', True, None),
 ('damagedKilled', False, None),
 ('damageAssisted', True, 'damageAssistedSelf'),
 ('capturePointsVal', False, None),
 ('mileage', False, None)]
TIME_STATS_KEYS = ['arenaCreateTimeOnlyStr', 'duration', 'playerKilled']

class BattleResultsWindow(View, AbstractWindowView, BattleResultsMeta):
    __playersNameCache = dict()

    def __init__(self, ctx):
        super(BattleResultsWindow, self).__init__()
        self.arenaUniqueID = ctx.get('arenaUniqueID')
        self.stats = None
        if IS_DEVELOPMENT:
            self.testData = ctx.get('testData')
        return

    @storage_getter('users')
    def usersStorage(self):
        return None

    @process
    def _populate(self):
        super(BattleResultsWindow, self)._populate()
        self.stats = yield StatsRequesterr().request()
        commonData = yield self.__getCommonData()
        self.as_setDataS(commonData)

    def _dispose(self):
        super(BattleResultsWindow, self)._dispose()

    def onWindowClose(self):
        import MusicController
        from gui.shared import g_itemsCache
        MusicController.g_musicController.setAccountAttrs(g_itemsCache.items.stats.attributes, True)
        MusicController.g_musicController.play(MusicController.MUSIC_EVENT_LOBBY)
        MusicController.g_musicController.play(MusicController.MUSIC_EVENT_LOBBY)
        self.destroy()

    def getDenunciations(self):
        if self.stats is not None:
            return self.stats.denunciationsLeft
        else:
            return 0

    def showEventsWindow(self, eID):
        self.fireEvent(events.ShowWindowEvent(events.ShowWindowEvent.SHOW_EVENTS_WINDOW, {'eventID': eID}))

    def saveSorting(self, iconType, sortDirection, bonusType):
        AccountSettings.setSettings('statsSorting' if bonusType != ARENA_BONUS_TYPE.SORTIE else 'statsSortingSortie', {'iconType': iconType,
         'sortDirection': sortDirection})

    def __getPlayerName(self, playerDBID, playersData):
        playerNameRes = self.__playersNameCache.get(playerDBID)
        if playerNameRes is None:
            playerInfo = playersData.get(playerDBID, dict())
            playerName = playerInfo.get('name', i18n.makeString(UNKNOWN_PLAYER_NAME_VALUE))
            clanName = playerInfo.get('clanAbbrev', '')
            igrType = playerInfo.get('igrType', '')
            playerNameRes = self.__playersNameCache[playerDBID] = (g_lobbyContext.getPlayerFullName(playerName, clanAbbrev=clanName, pDBID=playerDBID), (playerName,
              clanName,
              g_lobbyContext.getRegionCode(playerDBID),
              igrType))
        return playerNameRes

    def __getPlayerClan(self, playerDBID, playersData):
        playerInfo = playersData.get(playerDBID, dict())
        clanName = playerInfo.get('clanAbbrev', '')
        return clanName

    def __getVehicleData(self, vehicleCompDesc):
        vehicleName = i18n.makeString(UNKNOWN_VEHICLE_NAME_VALUE)
        vehicleShortName = i18n.makeString(UNKNOWN_VEHICLE_NAME_VALUE)
        vehicleIcon = VEHICLE_ICON_FILE.format(VEHICLE_NO_IMAGE_FILE_NAME)
        vehicleIconSmall = VEHICLE_ICON_SMALL_FILE.format(VEHICLE_NO_IMAGE_FILE_NAME)
        vehicleBalanceWeight = 0
        if vehicleCompDesc:
            vt = vehicles_core.getVehicleType(vehicleCompDesc)
            vehicleName = vt.userString
            vehicleShortName = vt.shortUserString
            nameReplaced = vt.name.replace(':', '-')
            vehicleIcon = VEHICLE_ICON_FILE.format(nameReplaced)
            vehicleIconSmall = VEHICLE_ICON_SMALL_FILE.format(nameReplaced)
            _, nation, nId = vehicles_core.parseIntCompactDescr(vehicleCompDesc)
            vDescr = vehicles_core.VehicleDescr(typeID=(nation, nId))
            vehicleBalanceWeight = vDescr.balanceWeight
        return (vehicleName,
         vehicleShortName,
         vehicleIcon,
         vehicleIconSmall,
         vehicleBalanceWeight)

    def __vehiclesComparator(self, item, other):
        res = 0
        iKiller = item.get('killerID', 0)
        cd = item.get('typeCompDescr')
        if cd is not None:
            iType = vehicles_core.getVehicleType(cd)
            iLevel = iType.level if iType else -1
            iWeight = VEHICLE_BATTLE_TYPES_ORDER_INDICES.get(set(VEHICLE_CLASS_TAGS.intersection(iType.tags)).pop(), 10) if iType else 10
        else:
            iLevel = -1
            iWeight = 10
        oKiller = other.get('killerID', 0)
        cd = other.get('typeCompDescr')
        if cd is not None:
            oType = vehicles_core.getVehicleType(other.get('typeCompDescr', None))
            oLevel = oType.level if oType else -1
            oWeight = VEHICLE_BATTLE_TYPES_ORDER_INDICES.get(set(VEHICLE_CLASS_TAGS.intersection(oType.tags)).pop(), 10) if oType else 10
        else:
            oLevel = -1
            oWeight = 10
        if iKiller == 0 and oKiller == 0 or iKiller != 0 and oKiller != 0:
            res = cmp(oLevel, iLevel) or cmp(iWeight, oWeight) or cmp(item.get('vehicleName', ''), other.get('vehicleName', ''))
        elif not iKiller:
            res = -1
        else:
            res = 1
        return res

    def __getStatsLine(self, label = None, col1 = None, col2 = None, col3 = None, col4 = None):
        if col2 is not None:
            lineType = 'wideLine'
        else:
            lineType = 'normalLine'
        lbl = label + '\n' if label is not None else '\n'
        lblStripped = re.sub('<[^<]+?>', '', lbl)
        return {'label': lbl,
         'labelStripped': lblStripped,
         'col1': col1 if col1 is not None else '\n',
         'col2': col2 if col2 is not None else '\n',
         'col3': col3 if col3 is not None else '\n',
         'col4': col4 if col4 is not None else '\n',
         'lineType': None if label is None else lineType}

    def __resultLabel(self, label):
        return i18n.makeString(RESULT_LINE_STR.format(label))

    def __makeCreditsLabel(self, value, canBeFaded = False):
        valStr = BigWorld.wg_getGoldFormat(int(value))
        if value < 0:
            valStr = self.__makeRedLabel(valStr)
        templateName = 'credits_small_inactive_label' if canBeFaded and value == 0 else 'credits_small_label'
        return makeHtmlString('html_templates:lobby/battle_results', templateName, {'value': valStr})

    def __makeXpLabel(self, value, canBeFaded = False):
        valStr = BigWorld.wg_getIntegralFormat(int(value))
        if value < 0:
            valStr = self.__makeRedLabel(valStr)
        templateName = 'xp_small_inactive_label' if canBeFaded and value == 0 else 'xp_small_label'
        return makeHtmlString('html_templates:lobby/battle_results', templateName, {'value': valStr})

    def __makeResourceLabel(self, value, canBeFaded = False):
        valStr = BigWorld.wg_getIntegralFormat(int(value))
        if value < 0:
            valStr = self.__makeRedLabel(valStr)
        templateName = 'resource_small_inactive_label' if canBeFaded and value == 0 else 'resource_small_label'
        return makeHtmlString('html_templates:lobby/battle_results', templateName, {'value': valStr})

    def __makeFreeXpLabel(self, value, canBeFaded = False):
        valStr = BigWorld.wg_getIntegralFormat(int(value))
        templateName = 'free_xp_small_inactive_label' if canBeFaded and value == 0 else 'free_xp_small_label'
        return makeHtmlString('html_templates:lobby/battle_results', templateName, {'value': valStr})

    def __makeGoldLabel(self, value, canBeFaded = False):
        valStr = BigWorld.wg_getGoldFormat(value)
        templateName = 'gold_small_inactive_label' if canBeFaded and value == 0 else 'gold_small_label'
        return makeHtmlString('html_templates:lobby/battle_results', templateName, {'value': valStr})

    def __makeRedLabel(self, value):
        return makeHtmlString('html_templates:lobby/battle_results', 'negative_value', {'value': value})

    def __populateStatValues(self, node, isSelf = False):
        node['teamHitsDamage'] = self.__makeTeamDamageStr(node)
        node['hits'] = self.__makeSlashedValuesStr(node, 'directHits', 'piercings')
        node['damagedKilled'] = self.__makeSlashedValuesStr(node, 'damaged', 'kills')
        node['capturePointsVal'] = self.__makeSlashedValuesStr(node, 'capturePoints', 'droppedCapturePoints')
        node['mileage'] = self.__makeMileageStr(node.get('mileage', 0))
        result = []
        for key, isInt, selfKey in STATS_KEYS:
            if isInt:
                value = node.get(key, 0)
                valueFormatted = BigWorld.wg_getIntegralFormat(value)
                if not value:
                    valueFormatted = makeHtmlString('html_templates:lobby/battle_results', 'empty_stat_value', {'value': valueFormatted})
            else:
                valueFormatted = node.get(key, '')
            if isSelf and selfKey is not None:
                key = selfKey
            result.append({'label': i18n.makeString(STATS_KEY_BASE.format(key)),
             'value': valueFormatted})

        return result

    def __populateAccounting(self, commonData, pData, playersData):
        isPremium = pData.get('isPremium', False)
        premCreditsFactor = pData.get('premiumCreditsFactor10', 10) / 10.0
        creditsToDraw = self.__calculateBaseParam('creditsToDraw', pData, premCreditsFactor)
        pData['xpTitleStr'] = i18n.makeString(XP_TITLE)
        dailyXpFactor = pData.get('dailyXPFactor10', 10) / 10.0
        igrXpFactor = pData.get('igrXPFactor10', 10) / 10.0
        premXpFactor = pData.get('premiumXPFactor10', 10) / 10.0
        aogasFactor = pData.get('aogasFactor10', 10) / 10.0
        aogasValStr = ''
        if dailyXpFactor > 1:
            pData['xpTitleStr'] += i18n.makeString(XP_TITLE_DAILY, dailyXpFactor)
        showIntermediateTotal = False
        creditsData = []
        achievementCredits = pData.get('achievementCredits', 0)
        creditsPenalty = self.__calculateBaseCreditsPenalty(pData)
        creditsCompensation = self.__calculateBaseParam('creditsContributionIn', pData, premCreditsFactor)
        isNoPenalty = achievementCredits > 0
        creditsBase = pData.get('originalCredits', 0)
        creditsCell = creditsBase - achievementCredits + creditsPenalty - creditsCompensation - creditsToDraw
        creditsCellPrem = int(creditsBase * premCreditsFactor) - int(achievementCredits * premCreditsFactor) + int(creditsPenalty * premCreditsFactor) - int(creditsToDraw * premCreditsFactor) - int(creditsCompensation * premCreditsFactor)
        creditsCellStr = self.__makeCreditsLabel(creditsCell, not isPremium)
        creditsCellPremStr = self.__makeCreditsLabel(creditsCellPrem, isPremium)
        pData['creditsStr'] = BigWorld.wg_getGoldFormat(creditsCellPrem if isPremium else creditsCell)
        creditsData.append(self.__getStatsLine(self.__resultLabel('base'), creditsCellStr, None, creditsCellPremStr, None))
        achievementCreditsPrem = 0
        if isNoPenalty:
            showIntermediateTotal = True
            achievementCreditsPrem = int(achievementCredits * premCreditsFactor)
            creditsData.append(self.__getStatsLine(self.__resultLabel('noPenalty'), self.__makeCreditsLabel(achievementCredits, not isPremium), None, self.__makeCreditsLabel(achievementCreditsPrem, isPremium), None))
        orderCredits = self.__calculateBaseParam('orderCredits', pData, premCreditsFactor)
        orderCreditsPrem = int(orderCredits * premCreditsFactor)
        if orderCredits > 0 or orderCreditsPrem > 0:
            showIntermediateTotal = True
            orderCreditsStr = self.__makeCreditsLabel(orderCredits, not isPremium) if orderCredits else None
            orderCreditsPremStr = self.__makeCreditsLabel(orderCreditsPrem, isPremium) if orderCreditsPrem else None
            creditsData.append(self.__getStatsLine(self.__resultLabel('battlePayments'), orderCreditsStr, None, orderCreditsPremStr, None))
        eventCredits = pData.get('eventCredits', 0)
        eventGold = pData.get('eventGold', 0)
        creditsEventStr = self.__makeCreditsLabel(eventCredits, not isPremium) if eventCredits else None
        creditsEventPremStr = self.__makeCreditsLabel(eventCredits, isPremium) if eventCredits else None
        goldEventStr = self.__makeGoldLabel(eventGold, not isPremium) if eventGold else None
        goldEventPremStr = self.__makeGoldLabel(eventGold, isPremium) if eventGold else None
        if eventCredits > 0 or eventGold > 0:
            showIntermediateTotal = True
            creditsData.append(self.__getStatsLine(self.__resultLabel('event'), creditsEventStr, goldEventStr, creditsEventPremStr, goldEventPremStr))
        creditsData.append(self.__getStatsLine())
        creditsPenaltyStr = self.__makeCreditsLabel(int(-creditsPenalty), not isPremium)
        creditsPenaltyPremStr = self.__makeCreditsLabel(int(-creditsPenalty * premCreditsFactor), isPremium)
        creditsData.append(self.__getStatsLine(self.__resultLabel('friendlyFirePenalty'), creditsPenaltyStr, None, creditsPenaltyPremStr, None))
        creditsCompensationStr = self.__makeCreditsLabel(int(creditsCompensation), not isPremium)
        creditsCompensationPremStr = self.__makeCreditsLabel(int(creditsCompensation * premCreditsFactor), isPremium)
        creditsData.append(self.__getStatsLine(self.__resultLabel('friendlyFireCompensation'), creditsCompensationStr, None, creditsCompensationPremStr, None))
        creditsData.append(self.__getStatsLine())
        if creditsPenalty or creditsCompensation:
            showIntermediateTotal = True
        if aogasFactor < 1:
            showIntermediateTotal = True
            aogasValStr = ''.join([i18n.makeString(XP_MULTIPLIER_SIGN_KEY), BigWorld.wg_getFractionalFormat(aogasFactor)])
            aogasValStr = self.__makeRedLabel(aogasValStr)
            creditsData.append(self.__getStatsLine(self.__resultLabel('aogasFactor'), aogasValStr, None, aogasValStr, None))
            creditsData.append(self.__getStatsLine())
        if showIntermediateTotal:
            c = int((creditsCell + achievementCredits + orderCredits + eventCredits - creditsPenalty + creditsCompensation) * aogasFactor)
            cPrem = int((creditsCellPrem + achievementCreditsPrem + orderCreditsPrem + eventCredits - int(creditsPenalty * premCreditsFactor) + int(creditsCompensation * premCreditsFactor)) * aogasFactor)
            creditsData.append(self.__getStatsLine(self.__resultLabel('intermediateTotal'), self.__makeCreditsLabel(c), goldEventStr, self.__makeCreditsLabel(cPrem), goldEventPremStr))
            creditsData.append(self.__getStatsLine())
        creditsAutoRepair = pData.get('autoRepairCost', 0)
        if creditsAutoRepair is None:
            creditsAutoRepair = 0
        creditsAutoRepairStr = self.__makeCreditsLabel(-creditsAutoRepair, not isPremium)
        creditsAutoRepairPremStr = self.__makeCreditsLabel(-creditsAutoRepair, isPremium)
        creditsData.append(self.__getStatsLine(self.__resultLabel('autoRepair'), creditsAutoRepairStr, None, creditsAutoRepairPremStr, None))
        autoLoadCost = pData.get('autoLoadCost', (0, 0))
        if autoLoadCost is None:
            autoLoadCost = (0, 0)
        creditsAutoLoad, goldAutoLoad = autoLoadCost
        creditsAutoLoadStr = self.__makeCreditsLabel(-creditsAutoLoad, not isPremium)
        creditsAutoLoadPremStr = self.__makeCreditsLabel(-creditsAutoLoad, isPremium)
        goldAutoLoadStr = self.__makeGoldLabel(-goldAutoLoad, not isPremium) if goldAutoLoad else None
        goldAutoLoadPremStr = self.__makeGoldLabel(-goldAutoLoad, isPremium) if goldAutoLoad else None
        creditsData.append(self.__getStatsLine(self.__resultLabel('autoLoad'), creditsAutoLoadStr, goldAutoLoadStr, creditsAutoLoadPremStr, goldAutoLoadPremStr))
        autoEquipCost = pData.get('autoEquipCost', (0, 0))
        if autoEquipCost is None:
            autoEquipCost = (0, 0)
        creditsAutoEquip, goldAutoEquip = autoEquipCost
        creditsAutoEquipStr = self.__makeCreditsLabel(-creditsAutoEquip, not isPremium)
        creditsAutoEquipPremStr = self.__makeCreditsLabel(-creditsAutoEquip, isPremium)
        goldAutoEquipStr = self.__makeGoldLabel(-goldAutoEquip, not isPremium)
        goldAutoEquipPremStr = self.__makeGoldLabel(-goldAutoEquip, isPremium)
        creditsData.append(self.__getStatsLine(self.__resultLabel('autoEquip'), creditsAutoEquipStr, goldAutoEquipStr, creditsAutoEquipPremStr, goldAutoEquipPremStr))
        creditsData.append(self.__getStatsLine())
        histAmmoCost = pData.get('histAmmoCost', (0, 0))
        creditsWithoutPremTotal = self.__calculateTotalCredits(pData, creditsBase, orderCredits, creditsToDraw, False)
        pData['creditsNoPremStr'] = self.__makeCreditsLabel(creditsCell, not isPremium)
        creditsWithoutPremTotalStr = self.__makeCreditsLabel(creditsWithoutPremTotal - creditsAutoRepair - creditsAutoEquip - creditsAutoLoad, not isPremium)
        pData['creditsNoPremTotalStr'] = creditsWithoutPremTotalStr
        creditsWithPremTotal = self.__calculateTotalCredits(pData, creditsBase, orderCredits, creditsToDraw, True)
        pData['creditsPremStr'] = self.__makeCreditsLabel(creditsCellPrem, isPremium)
        creditsWithPremTotalStr = self.__makeCreditsLabel(creditsWithPremTotal - creditsAutoRepair - creditsAutoEquip - creditsAutoLoad, isPremium)
        pData['creditsPremTotalStr'] = creditsWithPremTotalStr
        goldTotalStr = self.__makeGoldLabel(eventGold - goldAutoEquip - goldAutoLoad, not isPremium)
        goldTotalPremStr = self.__makeGoldLabel(eventGold - goldAutoEquip - goldAutoLoad, isPremium)
        totalLbl = makeHtmlString('html_templates:lobby/battle_results', 'lightText', {'value': self.__resultLabel('total')})
        creditsData.append(self.__getStatsLine(totalLbl, creditsWithoutPremTotalStr, goldTotalStr, creditsWithPremTotalStr, goldTotalPremStr))
        pData['creditsData'] = creditsData
        xpData = []
        achievementXP = int(pData.get('achievementXP', 0))
        achievementFreeXP = pData.get('achievementFreeXP', 0)
        xpPenalty = int(self.__calculateBaseXpPenalty(pData))
        xpBase = int(pData.get('originalXP', 0))
        xpCell = xpBase - achievementXP + xpPenalty
        xpCellPrem = int((xpBase - achievementXP + xpPenalty) * premXpFactor)
        xpCellStr = self.__makeXpLabel(xpCell, not isPremium)
        xpCellPremStr = self.__makeXpLabel(xpCellPrem, isPremium)
        freeXpBase = pData.get('originalFreeXP', 0)
        freeXpBaseStr = self.__makeFreeXpLabel(freeXpBase - achievementFreeXP, not isPremium)
        freeXpBasePremStr = self.__makeFreeXpLabel(int((freeXpBase - achievementFreeXP) * premXpFactor), isPremium)
        medals = pData.get('dossierPopUps', [])
        if RECORD_DB_IDS[('max15x15', 'maxXP')] in map(lambda (id, value): id, medals):
            label = makeHtmlString('html_templates:lobby/battle_results', 'xpRecord', {})
        else:
            label = self.__resultLabel('base')
        xpData.append(self.__getStatsLine(label, xpCellStr, freeXpBaseStr, xpCellPremStr, freeXpBasePremStr))
        pData['xpStr'] = BigWorld.wg_getIntegralFormat((xpCellPrem if isPremium else xpCell) * igrXpFactor * dailyXpFactor)
        if isNoPenalty:
            xpData.append(self.__getStatsLine(self.__resultLabel('noPenalty'), self.__makeXpLabel(achievementXP, not isPremium), self.__makeFreeXpLabel(achievementFreeXP, not isPremium), self.__makeXpLabel(int(achievementXP * premXpFactor), isPremium), self.__makeFreeXpLabel(int(achievementFreeXP * premXpFactor), isPremium)))
        xpPenaltyStr = self.__makeXpLabel(-xpPenalty, not isPremium)
        xpPenaltyPremStr = self.__makeXpLabel(int(-xpPenalty * premXpFactor), isPremium)
        xpData.append(self.__getStatsLine(self.__resultLabel('friendlyFirePenalty'), xpPenaltyStr, None, xpPenaltyPremStr, None))
        if igrXpFactor > 1:
            igrType = 0
            accountDBID = pData.get('accountDBID', 0)
            igrType = playersData.get(accountDBID, {'igrType': 0}).get('igrType')
            icon = makeHtmlString('html_templates:igr/iconSmall', 'premium' if igrType == IGR_TYPE.PREMIUM else 'basic')
            igrBonusLabelStr = i18n.makeString(BATTLE_RESULTS.DETAILS_CALCULATIONS_IGRBONUS, igrIcon=icon)
            igrBonusStr = makeHtmlString('html_templates:lobby/battle_results', 'igr_bonus', {'value': BigWorld.wg_getNiceNumberFormat(igrXpFactor)})
            xpData.append(self.__getStatsLine(igrBonusLabelStr, igrBonusStr, igrBonusStr, igrBonusStr, igrBonusStr))
        if dailyXpFactor > 1:
            dailyXpStr = makeHtmlString('html_templates:lobby/battle_results', 'multy_xp_small_label', {'value': int(dailyXpFactor)})
            xpData.append(self.__getStatsLine(self.__resultLabel('firstWin'), dailyXpStr, dailyXpStr, dailyXpStr, dailyXpStr))
        orderXP = self.__calculateBaseParam('orderXP', pData, premXpFactor)
        orderXPPrem = int(orderXP * premXpFactor)
        if orderXP > 0:
            orderXPStr = self.__makeXpLabel(orderXP, not isPremium) if orderXP else None
            orderXPPremStr = self.__makeXpLabel(orderXPPrem, isPremium) if orderXPPrem else None
            xpData.append(self.__getStatsLine(self.__resultLabel('tacticalTraining'), orderXPStr, None, orderXPPremStr, None))
        orderFreeXP = self.__calculateBaseParam('orderFreeXP', pData, premXpFactor)
        orderFreeXPPrem = int(orderFreeXP * premCreditsFactor)
        if orderFreeXP > 0:
            orderFreeXPStr = self.__makeFreeXpLabel(orderFreeXP, not isPremium) if orderFreeXP else None
            orderFreeXPPremStr = self.__makeFreeXpLabel(orderFreeXPPrem, isPremium) if orderFreeXPPrem else None
            xpData.append(self.__getStatsLine(self.__resultLabel('militaryManeuvers'), None, orderFreeXPStr, None, orderFreeXPPremStr))
        eventXP = pData.get('eventXP', 0)
        eventFreeXP = pData.get('eventFreeXP', 0)
        if eventXP > 0 or eventFreeXP > 0:
            eventXPStr = self.__makeXpLabel(eventXP, not isPremium)
            eventXPPremStr = self.__makeXpLabel(eventXP, isPremium)
            eventFreeXPStr = self.__makeFreeXpLabel(eventFreeXP, not isPremium)
            eventFreeXPPremStr = self.__makeFreeXpLabel(eventFreeXP, isPremium)
            xpData.append(self.__getStatsLine(self.__resultLabel('event'), eventXPStr, eventFreeXPStr, eventXPPremStr, eventFreeXPPremStr))
        if aogasFactor < 1:
            xpData.append(self.__getStatsLine(self.__resultLabel('aogasFactor'), aogasValStr, aogasValStr, aogasValStr, aogasValStr))
        if len(xpData) < 3:
            xpData.append(self.__getStatsLine())
        if len(xpData) < 7:
            xpData.append(self.__getStatsLine())
        pData['xpNoPremStr'] = self.__makeXpLabel(xpCell * igrXpFactor * dailyXpFactor, not isPremium)
        pData['xpPremStr'] = self.__makeXpLabel(xpCellPrem * igrXpFactor * dailyXpFactor, isPremium)
        freeXpTotal = self.__makeFreeXpLabel(self.__calculateTotalFreeXp(pData, freeXpBase, orderFreeXP), not isPremium)
        freeXpPremTotal = self.__makeFreeXpLabel(self.__calculateTotalFreeXp(pData, freeXpBase, orderFreeXP, True), isPremium)
        xpData.append(self.__getStatsLine(totalLbl, self.__makeXpLabel(self.__calculateTotalXp(pData, xpBase, orderXP), not isPremium), freeXpTotal, self.__makeXpLabel(self.__calculateTotalXp(pData, xpBase, orderXP, True), isPremium), freeXpPremTotal))
        pData['xpData'] = xpData
        if commonData.get('bonusType', 0) == ARENA_BONUS_TYPE.SORTIE:
            resValue = pData.get('fortResource', 0)
            resValue = 0 if resValue is None else resValue
            orderFortResource = pData.get('orderFortResource', 0)
            baseResValue = resValue - orderFortResource
            pData['fortResourceTotal'] = baseResValue
            pData['resStr'] = self.__makeResourceLabel(baseResValue, not isPremium)
            pData['resPremStr'] = self.__makeResourceLabel(baseResValue, isPremium)
            resData = []
            resData.append(self.__getStatsLine(self.__resultLabel('base'), None, self.__makeResourceLabel(baseResValue, not isPremium), None, self.__makeResourceLabel(baseResValue, isPremium)))
            if orderFortResource:
                resData.append(self.__getStatsLine(self.__resultLabel('heavyTrucks'), None, self.__makeResourceLabel(orderFortResource, not isPremium), None, self.__makeResourceLabel(orderFortResource, isPremium)))
            if len(resData) > 1:
                resData.append(self.__getStatsLine())
            resData.append(self.__getStatsLine(self.__resultLabel('total'), None, self.__makeResourceLabel(resValue, not isPremium), None, self.__makeResourceLabel(resValue, isPremium)))
            pData['resourceData'] = resData
        return

    @classmethod
    def _packAchievement(cls, achieve, isUnique = False):
        rank, i18nValue = (None, None)
        if achieve.getType() != ACHIEVEMENT_TYPE.SERIES:
            rank, i18nValue = achieve.getValue(), achieve.getI18nValue()
        icons = achieve.getIcons()
        specialIcon = icons.get(MarkOnGunAchievement.IT_95X85, None)
        customData = []
        aType = achieve.getName()
        if aType == 'marksOnGun':
            customData.extend([achieve.getDamageRating(), achieve.getVehicleNationID()])
        return {'type': aType,
         'block': achieve.getBlock(),
         'inactive': False,
         'icon': achieve.getSmallIcon() if specialIcon is None else '',
         'rank': rank,
         'localizedValue': i18nValue,
         'unic': isUnique,
         'rare': False,
         'title': achieve.getUserName(),
         'description': achieve.getUserDescription(),
         'rareIconId': None,
         'isEpic': achieve._getIconName() in achievements.BATTLE_ACHIEVES_WITH_RIBBON,
         'specialIcon': specialIcon,
         'customData': customData}

    def __populatePersonalMedals(self, pData):
        pData['dossierType'] = None
        pData['dossierCompDescr'] = None
        achievementsData = pData.get('dossierPopUps', [])
        pData['achievementsLeft'] = []
        pData['achievementsRight'] = []
        for achievementId, achieveValue in achievementsData:
            record = DB_ID_TO_RECORD[achievementId]
            if record[1] in ('maxXP', 'maxFrags', 'maxDamage', 'markOfMastery'):
                continue
            factory = getAchievementFactory(record)
            if factory is not None:
                achieve = factory.create(value=achieveValue)
                isMarkOnGun = record == MARK_ON_GUN_RECORD
                if isMarkOnGun:
                    if 'typeCompDescr' in pData:
                        achieve.setVehicleNationID(vehicles_core.parseIntCompactDescr(pData['typeCompDescr'])[1])
                    if 'damageRating' in pData:
                        achieve.setDamageRating(pData['damageRating'])
                achieveData = self._packAchievement(achieve, isUnique=True)
                if achieve.getName() in achievements.BATTLE_ACHIEVES_RIGHT:
                    pData['achievementsRight'].append(achieveData)
                else:
                    pData['achievementsLeft'].append(achieveData)

        markOfMastery = pData.get('markOfMastery', 0)
        factory = getAchievementFactory(('achievements', 'markOfMastery'))
        if markOfMastery > 0 and factory is not None:
            achieve = factory.create(value=markOfMastery)
            pData['achievementsLeft'].append(self._packAchievement(achieve))
        pData['achievementsRight'].sort(key=lambda k: k['isEpic'], reverse=True)
        return

    def __getVehicleIdByAccountID(self, accountDBID, vehiclesData):
        vehicleId = None
        for vId, vInfo in vehiclesData.iteritems():
            if vInfo.get('accountDBID', None) == accountDBID:
                vehicleId = vId
                break

        return vehicleId

    def __populateEfficiency(self, pData, vehiclesData, playersData):
        playerTeam = pData.get('team')
        playerDBID = pData.get('accountDBID')
        playerVehicleId = self.__getVehicleIdByAccountID(playerDBID, vehiclesData)
        efficiency = {1: [],
         2: []}
        details = pData.get('details', dict())
        for vId, iInfo in details.iteritems():
            vInfo = vehiclesData.get(vId, dict())
            pInfo = playersData.get(vInfo.get('accountDBID', -1), dict())
            vehiclePlayerDBID = vInfo.get('accountDBID', None)
            if vehiclePlayerDBID == playerDBID:
                continue
            _, iInfo['vehicleName'], _, iInfo['tankIcon'], iInfo['balanceWeight'] = self.__getVehicleData(vInfo.get('typeCompDescr', None))
            playerNameData = self.__getPlayerName(vehiclePlayerDBID, playersData)
            iInfo['playerFullName'] = playerNameData[0]
            iInfo['playerName'], iInfo['playerClan'], iInfo['playerRegion'], _ = playerNameData[1]
            iInfo['vehicleId'] = vId
            iInfo['typeCompDescr'] = vInfo.get('typeCompDescr')
            iInfo['killed'] = bool(vInfo.get('deathReason', -1) != -1)
            team = pInfo.get('team', pData.get('team') % 2 + 1)
            iInfo['isAlly'] = team == playerTeam
            iInfo['isFake'] = False
            iInfo['damageDealtVals'] = makeHtmlString('html_templates:lobby/battle_results', 'tooltip_two_liner', {'line1': BigWorld.wg_getIntegralFormat(iInfo['damageDealt']),
             'line2': BigWorld.wg_getIntegralFormat(iInfo['piercings'])})
            iInfo['damageDealtNames'] = makeHtmlString('html_templates:lobby/battle_results', 'tooltip_two_liner', {'line1': i18n.makeString(BATTLE_RESULTS_STR.format('common/tooltip/damage/part1')),
             'line2': i18n.makeString(BATTLE_RESULTS_STR.format('common/tooltip/damage/part2'))})
            iInfo['damageAssisted'] = iInfo.get('damageAssistedTrack', 0) + iInfo.get('damageAssistedRadio', 0)
            iInfo['damageAssistedVals'] = makeHtmlString('html_templates:lobby/battle_results', 'tooltip_two_liner', {'line1': BigWorld.wg_getIntegralFormat(iInfo['damageAssistedRadio']),
             'line2': BigWorld.wg_getIntegralFormat(iInfo['damageAssistedTrack'])})
            iInfo['damageAssistedNames'] = makeHtmlString('html_templates:lobby/battle_results', 'tooltip_two_liner', {'line1': i18n.makeString(BATTLE_RESULTS_STR.format('common/tooltip/assist/part1')),
             'line2': i18n.makeString(BATTLE_RESULTS_STR.format('common/tooltip/assist/part2'))})
            destroyedTankmen = iInfo['crits'] >> 24 & 255
            destroyedDevices = iInfo['crits'] >> 12 & 4095
            criticalDevices = iInfo['crits'] & 4095
            critsCount = 0
            criticalDevicesList = []
            destroyedDevicesList = []
            destroyedTankmenList = []
            for shift in range(len(vehicles.VEHICLE_DEVICE_TYPE_NAMES)):
                if 1 << shift & criticalDevices:
                    critsCount += 1
                    criticalDevicesList.append(self.__makeTooltipModuleLabel(vehicles.VEHICLE_DEVICE_TYPE_NAMES[shift], 'Critical'))
                if 1 << shift & destroyedDevices:
                    critsCount += 1
                    destroyedDevicesList.append(self.__makeTooltipModuleLabel(vehicles.VEHICLE_DEVICE_TYPE_NAMES[shift], 'Destroyed'))

            for shift in range(len(vehicles.VEHICLE_TANKMAN_TYPE_NAMES)):
                if 1 << shift & destroyedTankmen:
                    critsCount += 1
                    destroyedTankmenList.append(self.__makeTooltipTankmenLabel(vehicles.VEHICLE_TANKMAN_TYPE_NAMES[shift]))

            iInfo['critsCount'] = BigWorld.wg_getIntegralFormat(critsCount)
            iInfo['criticalDevices'] = LINE_BRAKE_STR.join(criticalDevicesList)
            iInfo['destroyedDevices'] = LINE_BRAKE_STR.join(destroyedDevicesList)
            iInfo['destroyedTankmen'] = LINE_BRAKE_STR.join(destroyedTankmenList)
            if not iInfo['isAlly'] or iInfo['isAlly'] and vInfo.get('killerID', 0) == playerVehicleId:
                efficiency[team].append(iInfo)

        enemies = sorted(efficiency[playerTeam % 2 + 1], cmp=self.__vehiclesComparator)
        allies = sorted(efficiency[playerTeam], cmp=self.__vehiclesComparator)
        if len(allies) > 0:
            enemies.append({'playerName': EFFICIENCY_ALLIES_STR,
             'isFake': True})
        pData['details'] = enemies + allies
        return

    def __makeTooltipModuleLabel(self, key, suffix):
        return makeHtmlString('html_templates:lobby/battle_results', 'tooltip_crit_label', {'image': '{0}{1}'.format(key, suffix),
         'value': i18n.makeString('#item_types:{0}/name'.format(key))})

    def __makeTooltipTankmenLabel(self, key):
        return makeHtmlString('html_templates:lobby/battle_results', 'tooltip_crit_label', {'image': '{0}Destroyed'.format(key),
         'value': i18n.makeString('#item_types:tankman/roles/{0}'.format(key))})

    def __populateResultStrings(self, commonData, pData):
        winnerTeam = commonData.get('winnerTeam', 0)
        if not winnerTeam:
            status = 'tie'
        elif winnerTeam == pData.get('team'):
            status = 'win'
        else:
            status = 'lose'
        commonData['resultShortStr'] = status
        commonData['resultStr'] = RESULT_.format(status)
        if commonData.get('guiType', 0) != ARENA_GUI_TYPE.EVENT_BATTLES:
            reason = commonData.get('finishReason', 0)
            if reason == 1:
                commonData['finishReasonStr'] = FINISH_REASON.format(''.join([str(reason), str(status)]))
            else:
                commonData['finishReasonStr'] = FINISH_REASON.format(reason)
        else:
            commonData['finishReasonStr'] = ''

    def __populateTankSlot(self, commonData, pData, vehiclesData, playersData):
        playerNameData = self.__getPlayerName(pData.get('accountDBID', None), playersData)
        commonData['playerNameStr'], commonData['clanNameStr'], commonData['regionNameStr'], _ = playerNameData[1]
        commonData['playerFullNameStr'] = playerNameData[0]
        commonData['vehicleName'], _, commonData['tankIcon'], _, _ = self.__getVehicleData(pData.get('typeCompDescr', None))
        killerID = pData.get('killerID', 0)
        deathReason = pData.get('deathReason', -1)
        commonData['deathReason'] = deathReason
        isPrematureLeave = pData.get('isPrematureLeave', False)
        if isPrematureLeave:
            commonData['vehicleStateStr'] = i18n.makeString(BATTLE_RESULTS.COMMON_VEHICLESTATE_PREMATURELEAVE)
        elif deathReason > -1:
            commonData['vehicleStateStr'] = i18n.makeString('#battle_results:common/vehicleState/dead{0}'.format(deathReason))
            if killerID:
                killerVehicle = vehiclesData.get(killerID, dict())
                killerPlayerId = killerVehicle.get('accountDBID', None)
                commonData['vehicleStatePrefixStr'] = '{0} ('.format(commonData['vehicleStateStr'])
                commonData['vehicleStateSuffixStr'] = ')'
                playerNameData = self.__getPlayerName(killerPlayerId, playersData)
                commonData['killerFullNameStr'] = playerNameData[0]
                commonData['killerNameStr'], commonData['killerClanNameStr'], commonData['killerRegionNameStr'], _ = playerNameData[1]
        else:
            commonData['vehicleStateStr'] = BATTLE_RESULTS.COMMON_VEHICLESTATE_ALIVE
        return

    def __populateArenaData(self, commonData, pData):
        arenaTypeID = commonData.get('arenaTypeID', 0)
        guiType = commonData.get('guiType', 0)
        arenaType = ArenaType.g_cache[arenaTypeID] if arenaTypeID > 0 else None
        if guiType == ARENA_GUI_TYPE.SORTIE:
            arenaGuiName = i18n.makeString(BATTLE_RESULTS.COMMON_BATTLETYPE_SORTIE)
        elif guiType == ARENA_GUI_TYPE.RANDOM:
            arenaGuiName = ARENA_TYPE.format(arenaType.gameplayName)
        else:
            arenaGuiName = ARENA_SPECIAL_TYPE.format(guiType)
        commonData['arenaStr'] = ARENA_NAME_PATTERN.format(i18n.makeString(arenaType.name), i18n.makeString(arenaGuiName))
        createTime = commonData.get('arenaCreateTime')
        createTime = time_utils.makeLocalServerTime(createTime)
        commonData['arenaCreateTimeStr'] = BigWorld.wg_getShortDateFormat(createTime) + ' ' + BigWorld.wg_getShortTimeFormat(createTime)
        commonData['arenaCreateTimeOnlyStr'] = BigWorld.wg_getShortTimeFormat(createTime)
        commonData['arenaIcon'] = ARENA_SCREEN_FILE.format(arenaType.geometryName)
        duration = commonData.get('duration', 0)
        minutes = int(duration / 60)
        seconds = int(duration % 60)
        commonData['duration'] = i18n.makeString(TIME_DURATION_STR, minutes, seconds)
        commonData['playerKilled'] = '-'
        if pData.get('killerID', 0):
            lifeTime = pData.get('lifeTime', 0)
            minutes = int(lifeTime / 60)
            seconds = int(lifeTime % 60)
            commonData['playerKilled'] = i18n.makeString(TIME_DURATION_STR, minutes, seconds)
        commonData['timeStats'] = []
        for key in TIME_STATS_KEYS:
            commonData['timeStats'].append({'label': i18n.makeString(TIME_STATS_KEY_BASE.format(key)),
             'value': commonData[key]})

        return

    def __makeTeamDamageStr(self, data):
        tkills = data.get('tkills', 0)
        tdamageDealt = data.get('tdamageDealt', 0)
        tDamageStr = '/'.join([str(tkills), str(tdamageDealt)])
        if tkills > 0 or tdamageDealt > 0:
            tDamageStr = self.__makeRedLabel(tDamageStr)
        else:
            tDamageStr = makeHtmlString('html_templates:lobby/battle_results', 'empty_stat_value', {'value': tDamageStr})
        return tDamageStr

    def __makeSlashedValuesStr(self, data, firstKey, secondKey):
        val1 = data.get(firstKey, 0)
        val1Str = str(val1) if val1 else makeHtmlString('html_templates:lobby/battle_results', 'empty_stat_value', {'value': val1})
        val2 = data.get(secondKey, 0)
        val2Str = str(val2) if val2 else makeHtmlString('html_templates:lobby/battle_results', 'empty_stat_value', {'value': val2})
        if not val1 and not val2:
            slash = makeHtmlString('html_templates:lobby/battle_results', 'empty_stat_value', {'value': '/'})
        else:
            slash = '/'
        return slash.join([val1Str, val2Str])

    def __makeMileageStr(self, mileage):
        km = float(mileage) / 1000
        val = BigWorld.wg_getFractionalFormat(km) + i18n.makeString(MILEAGE_STR_KEY)
        if not mileage:
            val = makeHtmlString('html_templates:lobby/battle_results', 'empty_stat_value', {'value': val})
        return val

    def __populateTeamsData(self, pData, playersData, vehiclesData, commonData):
        bonusType = commonData.get('bonusType', 0)
        squads = {1: {},
         2: {}}
        stat = {1: [],
         2: []}
        lastSquadId = 0
        squadManCount = 0
        playerSquadId = 0
        playerDBID = pData.get('accountDBID')
        playerTeam = pData.get('team')
        for pId, pInfo in playersData.iteritems():
            row = None
            for vId, vInfo in vehiclesData.iteritems():
                if pId == vInfo.get('accountDBID'):
                    row = pInfo.copy()
                    row.update(vInfo)
                    row['vehicleId'] = vId
                    row['damageAssisted'] = row.get('damageAssistedTrack', 0) + row.get('damageAssistedRadio', 0)
                    row['statValues'] = self.__populateStatValues(row)
                    health = vInfo.get('health', 0)
                    percents = 0
                    if health > 0:
                        percents = math.ceil(health * 100 / float(health + vInfo.get('damageReceived', 0)))
                    row['healthPercents'] = percents
                    row['vehicleFullName'], row['vehicleName'], row['bigTankIcon'], row['tankIcon'], row['balanceWeight'] = self.__getVehicleData(vInfo.get('typeCompDescr', None))
                    row['realKills'] = vInfo.get('kills', 0) - vInfo.get('tkills', 0)
                    achievementsData = tuple(row.get('achievements', []))
                    row['showResources'] = bonusType == ARENA_BONUS_TYPE.SORTIE
                    if bonusType == ARENA_BONUS_TYPE.SORTIE:
                        row['resourceCount'] = vInfo.get('fortResource', 0)
                    row['medalsCount'] = len(achievementsData)
                    achievementsList = []
                    for achievementId in achievementsData:
                        factory = getAchievementFactory(DB_ID_TO_RECORD[achievementId])
                        if factory is not None:
                            achive = factory.create(value=0)
                            achievementsList.append(self._packAchievement(achive, isUnique=True))

                    achievementsList.sort(key=lambda k: k['isEpic'], reverse=True)
                    row['achievements'] = achievementsList
                    killerID = row.get('killerID', 0)
                    deathReason = row.get('deathReason', -1)
                    isPrematureLeave = vInfo.get('isPrematureLeave', False)
                    if isPrematureLeave:
                        row['vehicleStateStr'] = i18n.makeString(BATTLE_RESULTS.COMMON_VEHICLESTATE_PREMATURELEAVE)
                    elif deathReason > -1:
                        row['vehicleStateStr'] = i18n.makeString('#battle_results:common/vehicleState/dead{0}'.format(deathReason))
                        if killerID:
                            killerVehicle = vehiclesData.get(killerID, dict())
                            killerPlayerId = killerVehicle.get('accountDBID', None)
                            row['vehicleStatePrefixStr'] = '{0} ('.format(row['vehicleStateStr'])
                            row['vehicleStateSuffixStr'] = ')'
                            playerNameData = self.__getPlayerName(killerPlayerId, playersData)
                            row['killerFullNameStr'] = playerNameData[0]
                            row['killerNameStr'], row['killerClanNameStr'], row['killerRegionNameStr'], _ = playerNameData[1]
                    else:
                        row['vehicleStateStr'] = BATTLE_RESULTS.COMMON_VEHICLESTATE_ALIVE
                    break

            if row is None:
                row = pInfo.copy()
            row['playerId'] = pId
            row['userName'] = pInfo.get('name')
            playerNameData = self.__getPlayerName(pId, playersData)
            row['playerFullName'] = playerNameData[0]
            row['playerName'], row['playerClan'], row['playerRegion'], row['playerIgrType'] = playerNameData[1]
            row['playerInfo'] = {}
            row['isSelf'] = playerDBID == pId
            if playerDBID == pId:
                playerSquadId = row.get('prebattleID', 0)
            team = row['team']
            prebattleID = row.get('prebattleID', 0)
            if bonusType == ARENA_BONUS_TYPE.REGULAR and prebattleID:
                if not lastSquadId or lastSquadId != prebattleID:
                    squadManCount = 1
                    lastSquadId = prebattleID
                else:
                    squadManCount += 1
                if prebattleID not in squads[team].keys():
                    squads[team][prebattleID] = 1
                else:
                    squads[team][prebattleID] += 1
            stat[team].append(row)

        if bonusType == ARENA_BONUS_TYPE.REGULAR and not (IS_DEVELOPMENT and squadManCount == len(playersData)):
            squadsSorted = dict()
            squadsSorted[1] = sorted(squads[1].iteritems(), cmp=lambda x, y: cmp(x[0], y[0]))
            squadsSorted[2] = sorted(squads[2].iteritems(), cmp=lambda x, y: cmp(x[0], y[0]))
            squads[1] = [ id for id, num in squadsSorted[1] if 1 < num < 4 ]
            squads[2] = [ id for id, num in squadsSorted[2] if 1 < num < 4 ]
        for team in (1, 2):
            data = sorted(stat[team], cmp=self.__vehiclesComparator)
            sortIdx = len(data)
            teamResourceTotal = 0
            for item in data:
                item['vehicleSort'] = sortIdx
                item['xpSort'] = item.get('xp', 0) - item.get('achievementXP', 0)
                sortIdx -= 1
                if bonusType == ARENA_BONUS_TYPE.REGULAR and not (IS_DEVELOPMENT and squadManCount == len(playersData)):
                    item['isOwnSquad'] = playerSquadId == item.get('prebattleID') if playerSquadId != 0 else False
                    item['squadID'] = squads[team].index(item.get('prebattleID')) + 1 if item.get('prebattleID') in squads[team] else 0
                else:
                    item['squadID'] = 0
                    item['isOwnSquad'] = False
                if bonusType == ARENA_BONUS_TYPE.SORTIE:
                    teamResourceTotal += item.get('resourceCount', 0)

            if team == playerTeam:
                commonData['totalFortResourceStr'] = makeHtmlString('html_templates:lobby/battle_results', 'teamResourceTotal', {'resourceValue': teamResourceTotal})

        return (stat[pData.get('team')], stat[pData.get('team') % 2 + 1])

    def __calculateBaseXpPenalty(self, pData):
        aogasFactor = pData.get('aogasFactor10', 10) / 10.0
        if not aogasFactor:
            return 0
        dailyFactor = pData.get('dailyXPFactor10', 10) / 10.0
        premFactor = pData.get('premiumXPFactor10', 10) / 10.0
        igrFactor = pData.get('igrXPFactor10', 10) / 10.0
        isPrem = pData.get('isPremium', False)
        xpPenalty = pData.get('xpPenalty', 0)
        xpPenalty = math.ceil(int(xpPenalty / aogasFactor) / dailyFactor)
        if isPrem:
            xpPenalty = math.ceil(xpPenalty / premFactor)
        if igrFactor:
            xpPenalty = math.ceil(xpPenalty / igrFactor)
        return xpPenalty

    def __calculateTotalCredits(self, pData, baseCredits, baseOrderCredits, creditsToDraw, usePremFactor = False):
        premFactor = pData.get('premiumCreditsFactor10', 10) / 10.0 if usePremFactor else 1.0
        isPrem = pData.get('isPremium', False)
        credits = pData.get('credits', 0) - creditsToDraw * premFactor
        if isPrem != usePremFactor:
            aogasFactor = pData.get('aogasFactor10', 10) / 10.0
            eventCredits = pData.get('eventCredits', 0)
            orderCredits = pData.get('orderCredits', 0)
            credits = int((int(int(baseCredits * premFactor) - creditsToDraw * premFactor) + baseOrderCredits * premFactor + eventCredits) * aogasFactor)
        return credits

    def __calculateTotalFreeXp(self, pData, baseFreeXp, baseOrderFreeXp, usePremFactor = False):
        if not baseFreeXp:
            return 0
        isPrem = pData.get('isPremium', False)
        freeXP = float(pData.get('freeXP', 0))
        if isPrem != usePremFactor:
            aogasFactor = pData.get('aogasFactor10', 10) / 10.0
            dailyFactor = pData.get('dailyXPFactor10', 10) / 10.0
            igrFactor = pData.get('igrXPFactor10', 10) / 10.0
            premFactor = pData.get('premiumXPFactor10', 10) / 10.0 if usePremFactor else 1.0
            eventFreeXP = pData.get('eventFreeXP', 0)
            freeXP = int((int(int(int(baseFreeXp * igrFactor) * premFactor) * dailyFactor) + int(baseOrderFreeXp * premFactor) + eventFreeXP) * aogasFactor)
        return freeXP

    def __calculateTotalXp(self, pData, baseXp, baseOrderXp, usePremFactor = False):
        isPrem = pData.get('isPremium', False)
        xp = pData.get('xp', 0)
        if isPrem != usePremFactor:
            aogasFactor = pData.get('aogasFactor10', 10) / 10.0
            dailyFactor = pData.get('dailyXPFactor10', 10) / 10.0
            igrFactor = pData.get('igrXPFactor10', 10) / 10.0
            premFactor = pData.get('premiumXPFactor10', 10) / 10.0 if usePremFactor else 1.0
            eventXP = pData.get('eventXP', 0)
            xp = int((int(int(int(baseXp * igrFactor) * premFactor) * dailyFactor) + int(baseOrderXp * premFactor) + eventXP) * aogasFactor)
        return xp

    def __calculateBaseCreditsPenalty(self, pData):
        isPrem = pData.get('isPremium', False)
        creditsPenalty = pData.get('creditsPenalty', 0) + pData.get('creditsContributionOut', 0)
        if isPrem:
            premFactor = pData.get('premiumCreditsFactor10', 10) / 10.0
            creditsPenalty = math.ceil(creditsPenalty / premFactor)
        return creditsPenalty

    def __calculateBaseParam(self, paramKey, pData, premFactor):
        isPremium = pData.get('isPremium', False)
        paramValue = pData.get(paramKey, 0)
        if isPremium:
            paramValue = math.ceil(paramValue / premFactor)
        return paramValue

    def selectVehicle(self, inventoryId):
        g_currentVehicle.selectVehicle(inventoryId)
        return g_currentVehicle.invID == inventoryId

    def __parseQuestsProgress(self, battleResults):
        questsProgress = battleResults.get('personal', {}).get('questsProgress', {})

        def _sortFunc(aData, bData):
            aQuest, aCurProg, aPrevProg, _, _ = aData
            bQuest, bCurProg, bPrevProg, _, _ = bData
            res = cmp(aQuest.isCompleted(aCurProg), bQuest.isCompleted(bCurProg))
            if res:
                return -res
            if aQuest.isCompleted() and bQuest.isCompleted(bCurProg):
                res = aQuest.getBonusCount(aCurProg) - aPrevProg.get('bonusCount', 0) - (bQuest.getBonusCount(bCurProg) - bPrevProg.get('bonusCount', 0))
                if not res:
                    return res
            return cmp(aQuest.getID(), bQuest.getID())

        from gui.Scaleform.daapi.view.lobby.server_events import events_helpers
        quests = g_eventsCache.getQuests()
        result = []
        for qID, qProgress in questsProgress.iteritems():
            if qID in quests:
                quest = quests[qID]
                pGroupBy, pPrev, pCur = qProgress
                isCompleted = pCur.get('bonusCount', 0) - pPrev.get('bonusCount', 0) > 0
                isProgressReset = not isCompleted and quest.bonusCond.isInRow() and pCur.get('battlesCount', 0) == 0
                if pPrev or max(pCur.itervalues()) != 0:
                    result.append((quest,
                     {pGroupBy: pCur},
                     {pGroupBy: pPrev},
                     isProgressReset,
                     isCompleted))

        formatted = []
        for e, pCur, pPrev, reset, complete in sorted(result, cmp=_sortFunc):
            info = events_helpers.getEventPostBattleInfo(e, quests, pCur, pPrev, reset, complete)
            if info is not None:
                formatted.append(info)

        return formatted

    @async
    @process
    def __getCommonData(self, callback):
        results = None
        if self.arenaUniqueID:
            results = yield StatsRequester().getBattleResults(int(self.arenaUniqueID))
        elif IS_DEVELOPMENT:
            results = self.testData
            yield lambda callback: callback(None)
        LOG_DEBUG('Player got battle results: ', self.arenaUniqueID, results)
        if results:
            personalData = results.get('personal', dict()).copy()
            playersData = results.get('players', dict()).copy()
            vehiclesData = results.get('vehicles', dict()).copy()
            commonData = results.get('common', dict()).copy()
            bonusType = commonData.get('bonusType', 0)
            if bonusType == ARENA_BONUS_TYPE.SORTIE:
                commonData['clans'] = self.__processClanData(personalData, playersData)
            else:
                commonData['clans'] = {'allies': {'clanDBID': -1,
                            'clanAbbrev': ''},
                 'enemies': {'clanDBID': -1,
                             'clanAbbrev': ''}}
            statsSorting = AccountSettings.getSettings('statsSorting' if bonusType != ARENA_BONUS_TYPE.SORTIE else 'statsSortingSortie')
            commonData['iconType'] = statsSorting.get('iconType')
            commonData['sortDirection'] = statsSorting.get('sortDirection')
            self.__populateResultStrings(commonData, personalData)
            self.__populatePersonalMedals(personalData)
            self.__populateArenaData(commonData, personalData)
            personalData['damageAssisted'] = personalData.get('damageAssistedTrack', 0) + personalData.get('damageAssistedRadio', 0)
            personalData['statValues'] = self.__populateStatValues(personalData, True)
            self.__populateAccounting(commonData, personalData, playersData)
            self.__populateTankSlot(commonData, personalData, vehiclesData, playersData)
            self.__populateEfficiency(personalData, vehiclesData, playersData)
            team1, team2 = self.__populateTeamsData(personalData, playersData, vehiclesData, commonData)
            resultingVehicles = []
            dailyXPFactor = 2
            if False:
                try:
                    multipliedXPVehs = yield StatsRequester().getMultipliedXPVehicles()
                    vehicleTypeLocks = yield StatsRequester().getVehicleTypeLocks()
                    globalVehicleLocks = yield StatsRequester().getGlobalVehicleLocks()
                    dailyXPFactor = yield StatsRequester().getDailyXPFactor() or 2
                    vehicles = yield Requester('vehicle').getFromInventory()

                    def sorting(first, second):
                        if first.isFavorite and not second.isFavorite:
                            return -1
                        if not first.isFavorite and second.isFavorite:
                            return 1
                        return first.__cmp__(second)

                    vehicles.sort(sorting)
                    vehiclesFiltered = [ vehicle for vehicle in vehicles if vehicle.descriptor.type.compactDescr not in multipliedXPVehs and vehicle.repairCost == 0 and vehicle.lock == 0 and None not in vehicle.crew and vehicle.crew != [] and not vehicleTypeLocks.get(vehicle.descriptor.type.compactDescr, {}).get(1, False) and not globalVehicleLocks.get(1, False) ]
                    for vehicle in vehiclesFiltered:
                        try:
                            vehicleInfo = dict()
                            vehicleInfo['inventoryId'] = vehicle.inventoryId
                            vehicleInfo['label'] = vehicle.name
                            vehicleInfo['selected'] = g_currentVehicle.invID == vehicle.inventoryId
                        except Exception:
                            LOG_ERROR("Exception while '%s' vehicle processing" % vehicle.descriptor.type.name)
                            LOG_CURRENT_EXCEPTION()
                            continue

                        resultingVehicles.append(vehicleInfo)

                except Exception:
                    LOG_CURRENT_EXCEPTION()

            callback({'personal': personalData,
             'common': commonData,
             'team1': team1,
             'team2': team2,
             'vehicles': resultingVehicles,
             'dailyXPFactor': dailyXPFactor,
             'quests': self.__parseQuestsProgress(results)})
        else:
            callback(None)
        return

    @process
    def getClanEmblem(self, uid, clanDBID):
        clanEmblem = yield g_clanCache.getClanEmblemTextureID(clanDBID, False, uid)
        if not self.isDisposed():
            self.as_setClanEmblemS(uid, ' <IMG SRC="img://{0}" width="24" height="24" vspace="-10"/>'.format(clanEmblem))

    def __processClanData(self, personalData, playersData):
        clans = []
        resClans = {'allies': {'clanDBID': -1,
                    'clanAbbrev': ''},
         'enemies': {'clanDBID': -1,
                     'clanAbbrev': ''}}
        for pId, pInfo in playersData.iteritems():
            clanDBID = pInfo.get('clanDBID')
            if clanDBID and clanDBID not in clans:
                clans.append(clanDBID)
                resClans['allies' if pInfo.get('team') == personalData.get('team') else 'enemies'] = {'clanDBID': clanDBID,
                 'clanAbbrev': i18n.makeString(BATTLE_RESULTS.COMMON_CLANABBREV, clanAbbrev=pInfo.get('clanAbbrev'))}

        return resClans
