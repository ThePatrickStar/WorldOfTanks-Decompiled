# Embedded file name: scripts/client/gui/shared/tooltips/vehicle.py
import BigWorld
import constants
from debug_utils import LOG_ERROR, LOG_DEBUG
from gui.Scaleform.daapi.view.lobby.techtree import NODE_STATE
from gui.shared import g_itemsCache
from gui.shared.tooltips import ToolTipDataField, ToolTipParameterField, ToolTipAttrField, ToolTipData, getComplexStatus, getUnlockPrice, TOOLTIP_TYPE
from gui.shared.gui_items.Vehicle import Vehicle
from gui.shared.utils import ItemsParameters, ParametersCache
from gui.shared.utils.gui_items import InventoryVehicle
from gui.prb_control.dispatcher import g_prbLoader

class VehicleStatusField(ToolTipDataField):

    def _getValue(self):
        vehicle = self._tooltip.item
        config = self._tooltip.context.getStatusConfiguration(self._tooltip.item)
        if config.node is not None:
            return self.__getTechTreeVehicleStatus(config, vehicle)
        else:
            return self.__getVehicleStatus(config.showCustomStates, vehicle)

    def __getTechTreeVehicleStatus(self, config, vehicle):
        nodeState = int(config.node.state)
        tooltip, level = None, InventoryVehicle.STATE_LEVEL.WARNING
        if not nodeState & NODE_STATE.UNLOCKED:
            if not nodeState & NODE_STATE.NEXT_2_UNLOCK:
                tooltip = '#tooltips:researchPage/vehicle/status/parentModuleIsLocked'
            elif not nodeState & NODE_STATE.ENOUGH_XP:
                tooltip = '#tooltips:researchPage/module/status/notEnoughXP'
                level = InventoryVehicle.STATE_LEVEL.CRITICAL
        else:
            if nodeState & NODE_STATE.IN_INVENTORY:
                return self.__getVehicleStatus(False, vehicle)
            if not nodeState & NODE_STATE.ENOUGH_MONEY:
                level = InventoryVehicle.STATE_LEVEL.CRITICAL
                if nodeState & NODE_STATE.PREMIUM:
                    tooltip = '#tooltips:moduleFits/gold_error'
                else:
                    tooltip = '#tooltips:moduleFits/credit_error'
        header, text = getComplexStatus(tooltip)
        if header is None and text is None:
            return
        else:
            return {'header': header,
             'text': text,
             'level': level}

    def __getVehicleStatus(self, showCustomStates, vehicle):
        if showCustomStates:
            isUnlocked = vehicle.isUnlocked
            isInInventory = vehicle.isInInventory
            credits, gold = g_itemsCache.items.stats.money
            msg = None
            level = InventoryVehicle.STATE_LEVEL.WARNING
            if not isUnlocked:
                msg = 'notUnlocked'
            elif isInInventory:
                msg = 'inHangar'
            elif credits < vehicle.buyPrice[0]:
                msg = 'notEnoughCredits'
                level = InventoryVehicle.STATE_LEVEL.CRITICAL
            elif gold < vehicle.buyPrice[1]:
                msg = 'notEnoughGold'
                level = InventoryVehicle.STATE_LEVEL.CRITICAL
            if msg is not None:
                header, text = getComplexStatus('#tooltips:vehicleStatus/%s' % msg)
                return {'header': header,
                 'text': text,
                 'level': level}
            return
        state, level = vehicle.getState()
        if state == Vehicle.VEHICLE_STATE.SERVER_RESTRICTION:
            return
        state, level = self.__preprocessState(state, level)
        header, text = getComplexStatus('#tooltips:vehicleStatus/%s' % state)
        if header is None and text is None:
            return
        else:
            return {'header': header,
             'text': text,
             'level': level}

    def __preprocessState(self, state, level):
        config = self._tooltip.context.getStatusConfiguration(self._tooltip.item)
        preQueue = g_prbLoader.getDispatcher().getPreQueueFunctional()
        if config.checkNotSuitable and state != Vehicle.VEHICLE_STATE.BATTLE and preQueue.getQueueType() == constants.QUEUE_TYPE.HISTORICAL:
            battle = preQueue.getItemData()
            if battle is not None:
                if not battle.canParticipateWith(self._tooltip.item.intCD):
                    return ('notSuitable', Vehicle.VEHICLE_STATE_LEVEL.WARNING)
        return (state, level)


class VehicleStatsField(ToolTipDataField):

    def _getValue(self):
        result = []
        vehicle = self._tooltip.item
        configuration = self._tooltip.context.getStatsConfiguration(vehicle)
        xp = configuration.xp
        dailyXP = configuration.dailyXP
        unlockPrice = configuration.unlockPrice
        buyPrice = configuration.buyPrice
        sellPrice = configuration.sellPrice
        techTreeNode = configuration.node
        if buyPrice and sellPrice:
            LOG_ERROR('You are not allowed to use buyPrice and sellPrice at the same time')
            return
        else:
            isUnlocked = vehicle.isUnlocked
            isInInventory = vehicle.isInInventory
            isNextToUnlock = False
            parentCD = None
            if techTreeNode is not None:
                isNextToUnlock = bool(int(techTreeNode.state) & NODE_STATE.NEXT_2_UNLOCK)
                parentCD = techTreeNode.unlockProps.parentID
            if xp:
                xpValue = vehicle.xp
                if xpValue:
                    result.append(('xp', xpValue))
            if dailyXP:
                attrs = g_itemsCache.items.stats.attributes
                if attrs & constants.ACCOUNT_ATTR.DAILY_MULTIPLIED_XP and vehicle.dailyXPFactor:
                    result.append(('dailyXPFactor', vehicle.dailyXPFactor))
            if unlockPrice:
                isAvailable, cost, need = getUnlockPrice(vehicle.intCD, parentCD)
                unlockPriceStat = [cost]
                if isAvailable and not isUnlocked and need > 0 and techTreeNode is not None:
                    unlockPriceStat.append(need)
                if cost > 0:
                    result.append(('unlock_price', unlockPriceStat))
            if buyPrice:
                price = vehicle.buyPrice
                needed = (0, 0)
                if not isInInventory and (isNextToUnlock or isUnlocked):
                    credits, gold = g_itemsCache.items.stats.money
                    creditsNeeded = price[0] - credits if price[0] else 0
                    goldNeeded = price[1] - gold if price[1] else 0
                    needed = (max(0, creditsNeeded), max(0, goldNeeded))
                result.append(('buy_price', (price, needed)))
                result.append(('def_buy_price', vehicle.defaultPrice))
                result.append(('action_prc', vehicle.actionPrc))
            if sellPrice:
                result.append(('sell_price', vehicle.sellPrice))
                result.append(('def_sell_price', vehicle.defaultSellPrice))
                result.append(('action_prc', vehicle.sellActionPrc))
            return result


class VehicleParamsField(ToolTipParameterField):
    PARAMS = {'lightTank': ('speedLimits', 'enginePowerPerTon', 'chassisRotationSpeed', 'circularVisionRadius'),
     'mediumTank': ('speedLimits', 'enginePowerPerTon', 'chassisRotationSpeed', 'damageAvgPerMinute'),
     'heavyTank': ('hullArmor', 'turretArmor', 'damageAvg', 'piercingPower'),
     'SPG': ('damageAvg', 'explosionRadius', 'shotDispersionAngle', 'aimingTime', 'reloadTimeSecs'),
     'AT-SPG': ('speedLimits', 'chassisRotationSpeed', 'damageAvgPerMinute', 'shotDispersionAngle', 'piercingPower'),
     'default': ('speedLimits', 'enginePower', 'chassisRotationSpeed')}

    def _getValue(self):
        result = list()
        vehicle = self._tooltip.item
        configuration = self._tooltip.context.getParamsConfiguration(vehicle)
        params = configuration.params
        crew = configuration.crew
        eqs = configuration.eqs
        devices = configuration.devices
        vehicleCommonParams = dict(ItemsParameters.g_instance.getParameters(vehicle.descriptor))
        vehicleRawParams = dict(ParametersCache.g_instance.getParameters(vehicle.descriptor))
        result.append([])
        if params:
            for paramName in self.PARAMS.get(vehicle.type, 'default'):
                if paramName in vehicleCommonParams or paramName in vehicleRawParams:
                    result[-1].append(self._getParameterValue(paramName, vehicleCommonParams, vehicleRawParams))

        result.append([])
        if crew:
            currentCrewSize = 0
            if vehicle.isInInventory:
                currentCrewSize = len([ x for _, x in vehicle.crew if x is not None ])
            result[-1].append({'label': 'crew',
             'current': currentCrewSize,
             'total': len(vehicle.descriptor.type.crewRoles)})
        if eqs:
            result[-1].append({'label': 'equipments',
             'current': len([ x for x in vehicle.eqs if x ]),
             'total': len(vehicle.eqs)})
        if devices:
            result[-1].append({'label': 'devices',
             'current': len([ x for x in vehicle.descriptor.optionalDevices if x ]),
             'total': len(vehicle.descriptor.optionalDevices)})
        return result

    def _getParameterValue(self, paramName, paramsDict, rawParamsDict):
        if paramName == 'enginePowerPerTon':
            return (paramName, BigWorld.wg_getNiceNumberFormat(rawParamsDict[paramName]))
        if paramName == 'damageAvgPerMinute':
            return (paramName, BigWorld.wg_getIntegralFormat(rawParamsDict[paramName]))
        if paramName == 'damageAvg':
            return (paramName, BigWorld.wg_getNiceNumberFormat(rawParamsDict[paramName]))
        if paramName == 'reloadTimeSecs':
            return (paramName, BigWorld.wg_getIntegralFormat(rawParamsDict[paramName]))
        if paramName == 'explosionRadius':
            return (paramName, BigWorld.wg_getNiceNumberFormat(rawParamsDict[paramName]))
        if paramName == 'shotDispersionAngle':
            return (paramName, BigWorld.wg_getNiceNumberFormat(rawParamsDict[paramName]))
        if paramName in paramsDict:
            return (paramName, paramsDict.get(paramName))
        return (paramName, rawParamsDict.get(paramName))


class VehicleLocksField(ToolTipParameterField):

    def _getValue(self):
        vehicle = self._tooltip.item
        return {'CLAN': vehicle.clanLock or None,
         'ROAMING': vehicle.isDisabledInRoaming}


class VehicleTooltipData(ToolTipData):

    def __init__(self, context):
        super(VehicleTooltipData, self).__init__(context, TOOLTIP_TYPE.VEHICLE)
        self.fields = (ToolTipAttrField(self, 'name', 'userName'),
         ToolTipAttrField(self, 'type'),
         ToolTipAttrField(self, 'isElite'),
         ToolTipAttrField(self, 'isPremium'),
         ToolTipAttrField(self, 'level'),
         ToolTipAttrField(self, 'isFavorite'),
         VehicleStatusField(self, 'status'),
         VehicleStatsField(self, 'stats'),
         VehicleParamsField(self, 'params'),
         VehicleLocksField(self, 'locks'))