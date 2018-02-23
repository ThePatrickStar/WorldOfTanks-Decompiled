# Embedded file name: scripts/client/VehicleAppearance.py
import BigWorld
import ResMgr
import Math
import Pixie
import weakref
import VehicleEffects
from VehicleEffects import VehicleTrailEffects, VehicleExhaustEffects
from constants import IS_DEVELOPMENT, ARENA_GUI_TYPE
import constants
from debug_utils import *
import helpers
from helpers.EffectMaterialCalculation import calcEffectMaterialIndex
import vehicle_extras
from helpers import bound_effects, DecalMap, isPlayerAvatar
from helpers.EffectsList import EffectsListPlayer, SpecialKeyPointNames
import items.vehicles
import random
import math
import time
from Event import Event
from functools import partial
import material_kinds
from VehicleStickers import VehicleStickers
import AuxiliaryFx
import TriggersManager
from TriggersManager import TRIGGER_TYPE
from Vibroeffects.ControllersManager import ControllersManager as VibrationControllersManager
from LightFx.LightControllersManager import LightControllersManager as LightFxControllersManager
import LightFx.LightManager
import SoundGroups
_ENABLE_VEHICLE_VALIDATION = False
_VEHICLE_DISAPPEAR_TIME = 0.2
_VEHICLE_APPEAR_TIME = 0.2
_ROOT_NODE_NAME = 'V'
_GUN_RECOIL_NODE_NAME = 'G'
_PERIODIC_TIME = 0.25
_PERIODIC_TIME_ENGINE = 0.1
_LOD_DISTANCE_SOUNDS = 150
_LOD_DISTANCE_EXHAUST = 200
_LOD_DISTANCE_TRAIL_PARTICLES = 100
_MOVE_THROUGH_WATER_SOUND = '/vehicles/tanks/water'
_CAMOUFLAGE_MIN_INTENSITY = 1.0
_PITCH_SWINGING_MODIFIERS = (0.9,
 1.88,
 0.3,
 4.0,
 1.0,
 1.0)
_ROUGHNESS_DECREASE_SPEEDS = (5.0, 6.0)
_ROUGHNESS_DECREASE_FACTOR = 0.5
_ROUGHNESS_DECREASE_FACTOR2 = 0.1
_FRICTION_ANG_FACTOR = 0.8
_FRICTION_ANG_BOUND = 0.5
_FRICTION_STRAFE_FACTOR = 0.4
_FRICTION_STRAFE_BOUND = 1.0
_MIN_DEPTH_FOR_HEAVY_SPLASH = 0.5
_EFFECT_MATERIALS_HARDNESS = {'ground': 0.1,
 'stone': 1,
 'wood': 0.5,
 'snow': 0.3,
 'sand': 0,
 'water': 0.2}
_ALLOW_LAMP_LIGHTS = False
frameTimeStamp = 0

class SoundMaxPlaybacksChecker():

    def __init__(self, maxPaybacks, period = 0.25):
        self.__maxPlaybacks = maxPaybacks
        self.__period = period
        self.__queue = []
        self.__distRecalcId = None
        return

    @staticmethod
    def __isSoundPlaying(sound):
        return sound.isPlaying

    def __distRecalc(self):
        if not isPlayerAvatar():
            self.__distRecalcId = None
            self.cleanup()
            return
        else:
            self.__distRecalcId = BigWorld.callback(self.__period, self.__distRecalc)
            cameraPos = BigWorld.camera().position
            for soundDistSq in self.__queue:
                if not self.__isSoundPlaying(soundDistSq[0]):
                    soundDistSq[0] = None
                    soundDistSq[1] = 0
                else:
                    soundDistSq[1] = (cameraPos - soundDistSq[0].position).lengthSquared

            self.__queue = filter(lambda x: x[0] is not None, self.__queue)
            self.__queue.sort(key=lambda soundDistSq: soundDistSq[1])
            return

    def cleanup(self):
        self.__queue = []
        if self.__distRecalcId is not None:
            BigWorld.cancelCallback(self.__distRecalcId)
            self.__distRecalcId = None
        return

    def checkAndPlay(self, newSound):
        if self.__distRecalcId is None:
            self.__distRecalc()
        cameraPos = BigWorld.camera().position
        newSoundDistSq = (cameraPos - newSound.position).lengthSquared
        for sound, distSq in self.__queue:
            if sound is newSound:
                return

        fullQueue = len(self.__queue) == self.__maxPlaybacks
        insertBeforeIdx = len(self.__queue)
        while insertBeforeIdx >= 1:
            sound, distSq = self.__queue[insertBeforeIdx - 1]
            if distSq < newSoundDistSq:
                break
            insertBeforeIdx -= 1

        if insertBeforeIdx < len(self.__queue) or not fullQueue:
            toInsert = [newSound, newSoundDistSq]
            self.__queue.insert(insertBeforeIdx, toInsert)
            if fullQueue:
                excessSound = self.__queue.pop()[0]
                if excessSound is not None:
                    excessSound.stop(True)
            if not self.__isSoundPlaying(newSound):
                newSound.play()
        return

    def removeSound(self, sound):
        if sound is None:
            return
        else:
            for idx, (snd, _) in enumerate(self.__queue):
                if snd == sound:
                    del self.__queue[idx]
                    return

            return


class VehicleAppearance(object):
    VehicleSoundsChecker = SoundMaxPlaybacksChecker(6)
    gunRecoil = property(lambda self: self.__gunRecoil)
    fashion = property(lambda self: self.__fashion)
    terrainMatKind = property(lambda self: self.__currTerrainMatKind)
    isInWater = property(lambda self: self.__isInWater)
    isUnderwater = property(lambda self: self.__isUnderWater)
    waterHeight = property(lambda self: self.__waterHeight)
    detailedEngineState = property(lambda self: self.__detailedEngineState)

    def __init__(self):
        self.__vt = None
        self.modelsDesc = {'chassis': {'model': None,
                     'boundEffects': None,
                     '_visibility': (True, True),
                     '_fetchedModel': None,
                     '_stateFunc': lambda vehicle, state: vehicle.typeDescriptor.chassis['models'][state],
                     '_callbackFunc': '_VehicleAppearance__onChassisModelLoaded'},
         'hull': {'model': None,
                  'boundEffects': None,
                  '_visibility': (True, True),
                  '_node': None,
                  '_fetchedModel': None,
                  '_stateFunc': lambda vehicle, state: vehicle.typeDescriptor.hull['models'][state],
                  '_callbackFunc': '_VehicleAppearance__onHullModelLoaded'},
         'turret': {'model': None,
                    'boundEffects': None,
                    '_visibility': (True, True),
                    '_node': None,
                    '_fetchedModel': None,
                    '_stateFunc': lambda vehicle, state: vehicle.typeDescriptor.turret['models'][state],
                    '_callbackFunc': '_VehicleAppearance__onTurretModelLoaded'},
         'gun': {'model': None,
                 'boundEffects': None,
                 '_visibility': (True, True),
                 '_fetchedModel': None,
                 '_node': None,
                 '_stateFunc': lambda vehicle, state: vehicle.typeDescriptor.gun['models'][state],
                 '_callbackFunc': '_VehicleAppearance__onGunModelLoaded'}}
        self.turretMatrix = Math.WGAdaptiveMatrixProvider()
        self.gunMatrix = Math.WGAdaptiveMatrixProvider()
        self.__vehicle = None
        self.__filter = None
        self.__engineSound = None
        self.__movementSound = None
        self.__waterHeight = -1.0
        self.__isInWater = False
        self.__isUnderWater = False
        self.__splashedWater = False
        self.__vibrationsCtrl = None
        self.__lightFxCtrl = None
        self.__auxiliaryFxCtrl = None
        self.__fashion = None
        self.__crashedTracksCtrl = None
        self.__gunRecoil = None
        self.__firstInit = True
        self.__curDamageState = None
        self.__loadingProgress = len(self.modelsDesc)
        self.__actualDamageState = None
        self.__invalidateLoading = False
        self.__effectsPlayer = None
        self.__engineMode = (0, 0)
        self.__detailedEngineState = VehicleEffects.DetailedEngineState()
        self.__swingMoveFlags = 0
        self.__trackSounds = [None, None]
        self.__currTerrainMatKind = [-1, -1, -1]
        self.__periodicTimerID = None
        self.__periodicTimerIDEngine = None
        self.__trailEffects = None
        self.__exhaustEffects = None
        self.__leftLightRotMat = None
        self.__rightLightRotMat = None
        self.__leftFrontLight = None
        self.__rightFrontLight = None
        self.__prevVelocity = None
        self.__prevTime = None
        self.__useOcclusionDecal = True
        self.__occlusionDecal = None
        self.__vehicleStickers = None
        self.onModelChanged = Event()
        return

    def prerequisites(self, vehicle):
        self.__curDamageState = self.__getDamageModelsState(vehicle.health)
        isPlayerVehicle = vehicle.id == BigWorld.player().playerVehicleID
        out = []
        for desc in self.modelsDesc.itervalues():
            part = desc['_stateFunc'](vehicle, self.__curDamageState)
            out.append(part)
            if isPlayerVehicle:
                BigWorld.wg_setModelQuality(part, 1)

        vDesc = vehicle.typeDescriptor
        out.append(vDesc.type.camouflageExclusionMask)
        splineDesc = vDesc.chassis['splineDesc']
        if splineDesc is not None:
            out.append(splineDesc['segmentModelLeft'])
            out.append(splineDesc['segmentModelRight'])
            if splineDesc['segment2ModelLeft'] is not None:
                out.append(splineDesc['segment2ModelLeft'])
            if splineDesc['segment2ModelRight'] is not None:
                out.append(splineDesc['segment2ModelRight'])
        customization = items.vehicles.g_cache.customization(vDesc.type.customizationNationID)
        camouflageParams = self.__getCamouflageParams(vehicle)
        if camouflageParams is not None and customization is not None:
            camouflageId = camouflageParams[0]
            camouflageDesc = customization['camouflages'].get(camouflageId)
            if camouflageDesc is not None and camouflageDesc['texture'] != '':
                out.append(camouflageDesc['texture'])
                for tgDesc in (vDesc.turret, vDesc.gun):
                    exclMask = tgDesc.get('camouflageExclusionMask')
                    if exclMask is not None and exclMask != '':
                        out.append(exclMask)

        return out

    def destroy(self):
        vehicle = self.__vehicle
        self.__vehicle = None
        self.__filter = None
        if IS_DEVELOPMENT and _ENABLE_VEHICLE_VALIDATION and self.__validateCallbackId is not None:
            BigWorld.cancelCallback(self.__validateCallbackId)
            self.__validateCallbackId = None
        if self.__engineSound is not None:
            VehicleAppearance.VehicleSoundsChecker.removeSound(self.__engineSound)
            self.__engineSound.stop()
            self.__engineSound = None
        if self.__movementSound is not None:
            VehicleAppearance.VehicleSoundsChecker.removeSound(self.__movementSound)
            self.__movementSound.stop()
            self.__movementSound = None
        if self.__vibrationsCtrl is not None:
            self.__vibrationsCtrl.destroy()
            self.__vibrationsCtrl = None
        if self.__lightFxCtrl is not None:
            self.__lightFxCtrl.destroy()
            self.__lightFxCtrl = None
        if self.__auxiliaryFxCtrl is not None:
            self.__auxiliaryFxCtrl.destroy()
            self.__auxiliaryFxCtrl = None
        self.__stopEffects()
        self.__destroyTrackDamageSounds()
        if self.__trailEffects is not None:
            self.__trailEffects.destroy()
            self.__trailEffects = None
        if self.__exhaustEffects is not None:
            self.__exhaustEffects.destroy()
            self.__exhaustEffects = None
        vehicle.stopHornSound(True)
        for desc in self.modelsDesc.iteritems():
            boundEffects = desc[1].get('boundEffects', None)
            if boundEffects is not None:
                boundEffects.destroy()

        if vehicle.isPlayer:
            player = BigWorld.player()
            if player.inputHandler is not None:
                arcadeCamera = player.inputHandler.ctrls['arcade'].camera
                if arcadeCamera is not None:
                    arcadeCamera.removeVehicleToCollideWith(self)
            for desc in self.modelsDesc.itervalues():
                part = desc['_stateFunc'](vehicle, 'undamaged')
                BigWorld.wg_setModelQuality(part, 0)

        vehicle.model.delMotor(vehicle.model.motors[0])
        vehicle.filter.vehicleCollisionCallback = None
        self.__vehicleStickers = None
        self.__removeHavok()
        self.modelsDesc = None
        self.onModelChanged = None
        self.__occlusionDecal = None
        id = getattr(self, '_VehicleAppearance__stippleCallbackID', None)
        if id is not None:
            BigWorld.cancelCallback(id)
            self.__stippleCallbackID = None
        if self.__periodicTimerID is not None:
            BigWorld.cancelCallback(self.__periodicTimerID)
            self.__periodicTimerID = None
        if self.__periodicTimerIDEngine is not None:
            BigWorld.cancelCallback(self.__periodicTimerIDEngine)
            self.__periodicTimerIDEngine = None
        self.__crashedTracksCtrl.destroy()
        self.__crashedTracksCtrl = None
        return

    def start(self, vehicle, prereqs = None):
        self.__vehicle = vehicle
        descr = vehicle.typeDescriptor
        player = BigWorld.player()
        if prereqs is None:
            descr.chassis['hitTester'].loadBspModel()
            descr.hull['hitTester'].loadBspModel()
            descr.turret['hitTester'].loadBspModel()
        filter = BigWorld.WGVehicleFilter()
        vehicle.filter = filter
        filter.vehicleWidth = descr.chassis['topRightCarryingPoint'][0] * 2
        filter.vehicleCollisionCallback = player.handleVehicleCollidedVehicle
        filter.maxMove = descr.physics['speedLimits'][0] * 2.0
        filter.vehicleMinNormalY = descr.physics['minPlaneNormalY']
        filter.isStrafing = vehicle.isStrafing
        for p1, p2, p3 in descr.physics['carryingTriangles']:
            filter.addTriangle((p1[0], 0, p1[1]), (p2[0], 0, p2[1]), (p3[0], 0, p3[1]))

        self.setupGunMatrixTargets(filter)
        self.__createGunRecoil()
        self.__createStickers(prereqs)
        self.__createExhaust()
        self.__crashedTracksCtrl = _CrashedTrackController(vehicle, self)
        self.__createOcclusionDecal()
        self.__fashion = BigWorld.WGVehicleFashion()
        _setupVehicleFashion(self, self.__fashion, self.__vehicle)
        for desc in self.modelsDesc.itervalues():
            modelName = desc['_stateFunc'](vehicle, self.__curDamageState)
            if prereqs is not None:
                try:
                    desc['model'] = prereqs[modelName]
                except Exception:
                    LOG_ERROR("can't load model <%s> from prerequisites." % modelName)

                if desc['model'] is None:
                    modelName = desc['_stateFunc'](vehicle, 'undamaged')
                    try:
                        desc['model'] = BigWorld.Model(modelName)
                    except:
                        LOG_ERROR("can't load model <%s> for tank state %s - no model was loaded from prerequisites, direct load of the model has been failed" % (modelName, self.__curDamageState))

            else:
                try:
                    desc['model'] = BigWorld.Model(modelName)
                except:
                    LOG_ERROR("can't load model <%s> - prerequisites were empty, direct load of the model has been failed" % modelName)

            desc['model'].outsideOnly = 1
            if desc.has_key('boundEffects'):
                desc['boundEffects'] = bound_effects.ModelBoundEffects(desc['model'])

        self.__setupModels()
        if self.__curDamageState == 'undamaged':
            setupSplineTracks(self.__fashion, self.__vehicle.typeDescriptor, self.modelsDesc['chassis']['model'], prereqs)
        state = self.__curDamageState
        if state == 'destroyed':
            self.__playEffect('destruction', SpecialKeyPointNames.STATIC)
        elif state == 'exploded':
            self.__playEffect('explosion', SpecialKeyPointNames.STATIC)
        self.__firstInit = False
        if self.__invalidateLoading:
            self.__invalidateLoading = True
            self.__fetchModels(self.__actualDamageState)
        if vehicle.isAlive():
            fakeModel = BigWorld.player().newFakeModel()
            self.modelsDesc['hull']['model'].node('HP_Fire_1').attach(fakeModel)
            if self.__vehicle.isPlayer:
                if descr.engine['soundPC'] != '':
                    event = descr.engine['soundPC']
                else:
                    event = descr.engine['sound']
                if descr.chassis['soundPC'] != '':
                    eventC = descr.chassis['soundPC']
                else:
                    eventC = descr.chassis['sound']
            else:
                if descr.engine['soundNPC'] != '':
                    event = descr.engine['soundNPC']
                else:
                    event = descr.engine['sound']
                if descr.chassis['soundNPC'] != '':
                    eventC = descr.chassis['soundNPC']
                else:
                    eventC = descr.chassis['sound']
            self.__engineSound = SoundGroups.g_instance.getSound(fakeModel, event)
            if self.__engineSound is None:
                self.__engineSound = SoundGroups.g_instance.getSound(self.modelsDesc['hull']['model'], event)
            self.__movementSound = SoundGroups.g_instance.getSound(self.modelsDesc['turret']['model'], eventC)
            self.__isEngineSoundMutedByLOD = False
        if vehicle.isAlive() and self.__vehicle.isPlayer:
            self.__vibrationsCtrl = VibrationControllersManager()
            if LightFx.LightManager.g_instance is not None and LightFx.LightManager.g_instance.isEnabled():
                self.__lightFxCtrl = LightFxControllersManager(self.__vehicle)
            if AuxiliaryFx.g_instance is not None:
                self.__auxiliaryFxCtrl = AuxiliaryFx.g_instance.createFxController(self.__vehicle)
        vehicle.model.stipple = True
        self.__stippleCallbackID = BigWorld.callback(_VEHICLE_APPEAR_TIME, self.__disableStipple)
        self.__setupTrailParticles()
        self.__setupTrackDamageSounds()
        self.__periodicTimerID = BigWorld.callback(_PERIODIC_TIME, self.__onPeriodicTimer)
        self.__periodicTimerIDEngine = BigWorld.callback(_PERIODIC_TIME_ENGINE, self.__onPeriodicTimerEngine)
        return

    def showStickers(self, show):
        self.__vehicleStickers.show = show

    def updateTurretVisibility(self):
        if self.__vehicle is not None:
            isTurretOK = not self.__vehicle.isTurretDetached
            self.changeVisibility('turret', isTurretOK, isTurretOK)
            self.changeVisibility('gun', isTurretOK, isTurretOK)
        return

    def changeVisibility(self, modelName, modelVisible, attachmentsVisible):
        desc = self.modelsDesc.get(modelName, None)
        if desc is None:
            LOG_ERROR("invalid model's description name <%s>." % modelName)
        desc['model'].visible = modelVisible
        desc['model'].visibleAttachments = attachmentsVisible
        desc['_visibility'] = (modelVisible, attachmentsVisible)
        if modelName == 'chassis':
            self.__crashedTracksCtrl.setVisible(modelVisible)
        return

    def onVehicleHealthChanged(self):
        vehicle = self.__vehicle
        if not vehicle.isAlive():
            BigWorld.wgDelEdgeDetectEntity(vehicle)
            if vehicle.health > 0:
                self.changeEngineMode((0, 0))
            elif self.__engineSound is not None:
                VehicleAppearance.VehicleSoundsChecker.removeSound(self.__engineSound)
                self.__engineSound.stop()
                self.__engineSound = None
            if self.__movementSound is not None:
                VehicleAppearance.VehicleSoundsChecker.removeSound(self.__movementSound)
                self.__movementSound.stop()
                self.__movementSound = None
        state = self.__getDamageModelsState(vehicle.health)
        if state != self.__curDamageState:
            if self.__loadingProgress == len(self.modelsDesc) and not self.__firstInit:
                if state == 'undamaged':
                    self.__stopEffects()
                elif state == 'destroyed':
                    self.__playEffect('destruction')
                if state == 'exploded':
                    self.__havokExplosion()
                if vehicle.health <= 0:
                    BigWorld.player().inputHandler.onVehicleDeath(vehicle, state == 'exploded')
                self.__fetchModels(state)
            else:
                self.__actualDamageState = state
                self.__invalidateLoading = True
        return

    def showAmmoBayEffect(self, mode, fireballVolume):
        if mode == constants.AMMOBAY_DESTRUCTION_MODE.POWDER_BURN_OFF:
            self.__playEffect('ammoBayBurnOff')
            return
        volumes = items.vehicles.g_cache.commonConfig['miscParams']['explosionCandleVolumes']
        candleIdx = 0
        for idx, volume in enumerate(volumes):
            if volume >= fireballVolume:
                break
            candleIdx = idx + 1

        if candleIdx > 0:
            self.__playEffect('explosionCandle%d' % candleIdx)
        else:
            self.__playEffect('explosion')

    def changeEngineMode(self, mode, forceSwinging = False):
        self.__engineMode = mode
        powerMode = mode[0]
        dirFlags = mode[1]
        self.__updateExhaust()
        self.__updateBlockedMovement()
        if forceSwinging:
            flags = mode[1]
            prevFlags = self.__swingMoveFlags
            fashion = self.fashion
            moveMask = 3
            rotMask = 12
            if flags & moveMask ^ prevFlags & moveMask:
                swingPeriod = 2.0
                if flags & 1:
                    fashion.accelSwingingDirection = -1
                elif flags & 2:
                    fashion.accelSwingingDirection = 1
                else:
                    fashion.accelSwingingDirection = 0
            elif not flags & moveMask and flags & rotMask ^ prevFlags & rotMask:
                swingPeriod = 1.0
                fashion.accelSwingingDirection = 0
            else:
                swingPeriod = 0.0
            if swingPeriod > fashion.accelSwingingPeriod:
                fashion.accelSwingingPeriod = swingPeriod
            self.__swingMoveFlags = flags

    def stopSwinging(self):
        self.fashion.accelSwingingPeriod = 0.0

    def removeDamageSticker(self, code):
        self.__vehicleStickers.delDamageSticker(code)

    def addDamageSticker(self, code, componentName, stickerID, segStart, segEnd):
        self.__vehicleStickers.addDamageSticker(code, componentName, stickerID, segStart, segEnd)

    def receiveShotImpulse(self, dir, impulse):
        if self.__curDamageState == 'undamaged':
            self.__fashion.receiveShotImpulse(dir, impulse)
            self.__crashedTracksCtrl.receiveShotImpulse(dir, impulse)

    def addCrashedTrack(self, isLeft):
        self.__crashedTracksCtrl.addTrack(isLeft)
        if not self.__vehicle.isEnteringWorld:
            sound = self.__trackSounds[0 if isLeft else 1]
            if sound is not None and sound[1] is not None:
                sound[1].play()
        return

    def delCrashedTrack(self, isLeft):
        self.__crashedTracksCtrl.delTrack(isLeft)

    def __fetchModels(self, modelState):
        self.__curDamageState = modelState
        self.__loadingProgress = 0
        for desc in self.modelsDesc.itervalues():
            BigWorld.fetchModel(desc['_stateFunc'](self.__vehicle, modelState), getattr(self, desc['_callbackFunc']))

    def __attemptToSetupModels(self):
        self.__loadingProgress += 1
        if self.__loadingProgress == len(self.modelsDesc):
            if self.__invalidateLoading:
                self.__invalidateLoading = False
                self.__fetchModels(self.__actualDamageState)
            else:
                self.__setupModels()

    def __setupModels(self):
        vehicle = self.__vehicle
        chassis = self.modelsDesc['chassis']
        hull = self.modelsDesc['hull']
        turret = self.modelsDesc['turret']
        gun = self.modelsDesc['gun']
        if not self.__firstInit:
            self.__detachStickers()
            self.__removeHavok()
            self.__destroyOcclusionDecal()
            self.__destroyLampLights()
            delattr(gun['model'], 'wg_gunRecoil')
            self.__gunFireNode = None
            self.__attachExhaust(False)
            self.__trailEffects.stopEffects()
            self.__destroyTrackDamageSounds()
            self.__crashedTracksCtrl.reset()
            chassis['model'].stopSoundsOnDestroy = False
            hull['model'].stopSoundsOnDestroy = False
            turret['model'].stopSoundsOnDestroy = False
            hull['_node'].detach(hull['model'])
            turret['_node'].detach(turret['model'])
            gun['_node'].detach(gun['model'])
            chassis['model'] = chassis['_fetchedModel']
            hull['model'] = hull['_fetchedModel']
            turret['model'] = turret['_fetchedModel']
            gun['model'] = gun['_fetchedModel']
            delattr(vehicle.model, 'wg_fashion')
        vehicle.model = None
        vehicle.model = chassis['model']
        vehicle.model.delMotor(vehicle.model.motors[0])
        matrix = vehicle.matrix
        matrix.notModel = True
        vehicle.model.addMotor(BigWorld.Servo(matrix))
        self.__assembleModels()
        if not self.__firstInit:
            chassis['boundEffects'].reattachTo(chassis['model'])
            hull['boundEffects'].reattachTo(hull['model'])
            turret['boundEffects'].reattachTo(turret['model'])
            gun['boundEffects'].reattachTo(gun['model'])
            self.__reattachEffects()
        modelsState = self.__curDamageState
        if modelsState == 'undamaged':
            self.__attachStickers()
            try:
                vehicle.model.wg_fashion = self.__fashion
            except:
                LOG_CURRENT_EXCEPTION()

            self.__attachExhaust(True)
            gun['model'].wg_gunRecoil = self.__gunRecoil
            self.__createLampLights()
            self.__gunFireNode = gun['model'].node('HP_gunFire')
        elif modelsState == 'destroyed' or modelsState == 'exploded':
            self.__destroyExhaust()
            self.__attachStickers(items.vehicles.g_cache.commonConfig['miscParams']['damageStickerAlpha'], True)
        else:
            raise False or AssertionError
        self.__updateCamouflage()
        self.__attachOcclusionDecal()
        self.__applyVisibility()
        self.__vehicle.model.height = self.__computeVehicleHeight()
        self.onModelChanged()
        if 'observer' in vehicle.typeDescriptor.type.tags:
            vehicle.model.visible = False
            vehicle.model.visibleAttachments = False
        if modelsState == 'undamaged':
            self.__setupHavok()
        return

    def __reattachEffects(self):
        if self.__effectsPlayer is not None:
            self.__effectsPlayer.reattachTo(self.modelsDesc['hull']['model'])
        return

    def __playEffect(self, kind, *modifs):
        if self.__effectsPlayer is not None:
            self.__effectsPlayer.stop()
        enableDecal = True
        if kind in ('explosion', 'destruction'):
            if self.isUnderwater:
                return
            filter = self.__vehicle.filter
            isFlying = filter.numLeftTrackContacts < 2 and filter.numRightTrackContacts < 2
            if isFlying:
                enableDecal = False
        vehicle = self.__vehicle
        effects = vehicle.typeDescriptor.type.effects[kind]
        if not effects:
            return
        else:
            effects = random.choice(effects)
            modelMap = {}
            for i, j in vehicle.appearance.modelsDesc.iteritems():
                modelMap[i] = vehicle.appearance.modelsDesc[i]['model']

            self.__effectsPlayer = EffectsListPlayer(effects[1], effects[0], showShockWave=vehicle.isPlayer, showFlashBang=vehicle.isPlayer, isPlayer=vehicle.isPlayer, showDecal=enableDecal, start=vehicle.position + Math.Vector3(0.0, -1.0, 0.0), end=vehicle.position + Math.Vector3(0.0, 1.0, 0.0), modelMap=modelMap)
            self.__effectsPlayer.play(self.modelsDesc['hull']['model'], *modifs)
            return

    def __updateCamouflage(self):
        texture = ''
        colors = [0,
         0,
         0,
         0]
        gloss = 0
        weights = Math.Vector4(1, 0, 0, 0)
        camouflagePresent = False
        vDesc = self.__vehicle.typeDescriptor
        camouflageParams = self.__getCamouflageParams(self.__vehicle)
        customization = items.vehicles.g_cache.customization(vDesc.type.customizationNationID)
        defaultTiling = None
        if camouflageParams is not None and customization is not None:
            camouflage = customization['camouflages'].get(camouflageParams[0])
            if camouflage is not None:
                camouflagePresent = True
                texture = camouflage['texture']
                colors = camouflage['colors']
                gloss = camouflage['gloss'].get(vDesc.type.compactDescr)
                if gloss is None:
                    gloss = 0
                metallic = camouflage['metallic'].get(vDesc.type.compactDescr)
                if metallic is None:
                    metallic = 0
                weights = Math.Vector4(*[ (c >> 24) / 255.0 for c in colors ])
                colors = [ colors[i] & 16777215 | metallic << (3 - i) * 8 & 4278190080L for i in range(0, 4) ]
                defaultTiling = camouflage['tiling'].get(vDesc.type.compactDescr)
        if self.__curDamageState != 'undamaged':
            weights *= 0.1
        if camouflageParams is not None:
            _, camStartTime, camNumDays = camouflageParams
            if camNumDays > 0:
                timeAmount = (time.time() - camStartTime) / (camNumDays * 86400)
                if timeAmount > 1.0:
                    weights *= _CAMOUFLAGE_MIN_INTENSITY
                elif timeAmount > 0:
                    weights *= (1.0 - timeAmount) * (1.0 - _CAMOUFLAGE_MIN_INTENSITY) + _CAMOUFLAGE_MIN_INTENSITY
        for descId in ('chassis', 'hull', 'turret', 'gun'):
            exclusionMap = vDesc.type.camouflageExclusionMask
            tiling = defaultTiling
            if tiling is None:
                tiling = vDesc.type.camouflageTiling
            model = self.modelsDesc[descId]['model']
            if descId == 'chassis':
                compDesc = vDesc.chassis
            elif descId == 'hull':
                compDesc = vDesc.hull
            elif descId == 'turret':
                compDesc = vDesc.turret
            elif descId == 'gun':
                compDesc = vDesc.gun
            else:
                compDesc = None
            if compDesc is not None:
                coeff = compDesc.get('camouflageTiling')
                if coeff is not None:
                    if tiling is not None:
                        tiling = (tiling[0] * coeff[0],
                         tiling[1] * coeff[1],
                         tiling[2] * coeff[2],
                         tiling[3] * coeff[3])
                    else:
                        tiling = coeff
                if compDesc.get('camouflageExclusionMask'):
                    exclusionMap = compDesc['camouflageExclusionMask']
            useCamouflage = camouflagePresent and exclusionMap and texture
            fashion = None
            if hasattr(model, 'wg_fashion'):
                fashion = model.wg_fashion
            elif hasattr(model, 'wg_gunRecoil'):
                fashion = model.wg_gunRecoil
            elif useCamouflage:
                fashion = model.wg_baseFashion = BigWorld.WGBaseFashion()
            elif hasattr(model, 'wg_baseFashion'):
                delattr(model, 'wg_baseFashion')
            if fashion is not None:
                if useCamouflage:
                    fashion.setCamouflage(texture, exclusionMap, tiling, colors[0], colors[1], colors[2], colors[3], gloss, weights)
                else:
                    fashion.removeCamouflage()

        return

    def __getCamouflageParams(self, vehicle):
        vDesc = vehicle.typeDescriptor
        vehicleInfo = BigWorld.player().arena.vehicles.get(vehicle.id)
        if vehicleInfo is not None:
            if vDesc.name == 'ussr:T62A_sport':
                camouflageId = 95 if vehicleInfo['team'] == 1 else 94
                return (camouflageId, time.time(), 100.0)
            camouflagePseudoname = vehicleInfo['events'].get('hunting', None)
            if camouflagePseudoname is not None:
                camouflIdsByNation = {0: {'black': 29,
                     'gold': 30,
                     'red': 31,
                     'silver': 32},
                 1: {'black': 25,
                     'gold': 26,
                     'red': 27,
                     'silver': 28},
                 2: {'black': 52,
                     'gold': 50,
                     'red': 51,
                     'silver': 53},
                 3: {'black': 48,
                     'gold': 46,
                     'red': 47,
                     'silver': 49},
                 4: {'black': 60,
                     'gold': 58,
                     'red': 59,
                     'silver': 61},
                 5: {'black': 56,
                     'gold': 54,
                     'red': 55,
                     'silver': 57}}
                camouflIds = camouflIdsByNation.get(vDesc.type.customizationNationID)
                if camouflIds is not None:
                    ret = camouflIds.get(camouflagePseudoname)
                    if ret is not None:
                        return (ret, time.time(), 100.0)
        arenaType = BigWorld.player().arena.arenaType
        camouflageKind = arenaType.vehicleCamouflageKind
        return vDesc.camouflages[camouflageKind]

    def __stopEffects(self):
        if self.__effectsPlayer is not None:
            self.__effectsPlayer.stop()
        self.__effectsPlayer = None
        return

    def __calcIsUnderwater(self):
        if not self.__isInWater:
            return False
        chassisModel = self.modelsDesc['chassis']['model']
        turretOffs = self.__vehicle.typeDescriptor.chassis['hullPosition'] + self.__vehicle.typeDescriptor.hull['turretPositions'][0]
        turretOffsetMat = Math.Matrix()
        turretOffsetMat.setTranslate(turretOffs)
        turretJointMat = Math.Matrix(chassisModel.matrix)
        turretJointMat.preMultiply(turretOffsetMat)
        turretHeight = turretJointMat.translation.y - self.__vehicle.position.y
        return turretHeight < self.__waterHeight

    def __updateWaterStatus(self):
        self.__waterHeight = BigWorld.wg_collideWater(self.__vehicle.position, self.__vehicle.position + Math.Vector3(0, 1, 0))
        self.__isInWater = self.__waterHeight != -1
        self.__isUnderWater = self.__calcIsUnderwater()
        wasSplashed = self.__splashedWater
        self.__splashedWater = False
        waterHitPoint = None
        if self.__isInWater:
            self.__splashedWater = True
            waterHitPoint = self.__vehicle.position + Math.Vector3(0, self.__waterHeight, 0)
        else:
            trPoint = self.__vehicle.typeDescriptor.chassis['topRightCarryingPoint']
            cornerPoints = [Math.Vector3(trPoint.x, 0, trPoint.y),
             Math.Vector3(trPoint.x, 0, -trPoint.y),
             Math.Vector3(-trPoint.x, 0, -trPoint.y),
             Math.Vector3(-trPoint.x, 0, trPoint.y)]
            vehMat = Math.Matrix(self.__vehicle.model.matrix)
            for cornerPoint in cornerPoints:
                pointToTest = vehMat.applyPoint(cornerPoint)
                dist = BigWorld.wg_collideWater(pointToTest, pointToTest + Math.Vector3(0, 1, 0))
                if dist != -1:
                    self.__splashedWater = True
                    waterHitPoint = pointToTest + Math.Vector3(0, dist, 0)
                    break

        if self.__splashedWater and not wasSplashed:
            lightVelocityThreshold = self.__vehicle.typeDescriptor.type.collisionEffectVelocities['waterContact']
            heavyVelocityThreshold = self.__vehicle.typeDescriptor.type.heavyCollisionEffectVelocities['waterContact']
            vehicleVelocity = abs(self.__vehicle.filter.speedInfo.value[0])
            if vehicleVelocity >= lightVelocityThreshold:
                collRes = BigWorld.wg_collideSegment(self.__vehicle.spaceID, waterHitPoint, waterHitPoint + (0, -_MIN_DEPTH_FOR_HEAVY_SPLASH, 0), 18, lambda matKind, collFlags, itemId, chunkId: collFlags & 8)
                deepEnough = collRes is None
                effectName = 'waterCollisionLight' if vehicleVelocity < heavyVelocityThreshold or not deepEnough else 'waterCollisionHeavy'
                self.__vehicle.showCollisionEffect(waterHitPoint, effectName, Math.Vector3(0, 1, 0))
        if self.isUnderwater and self.__effectsPlayer is not None:
            self.__stopEffects()
        return

    def __onPeriodicTimerEngine(self):
        try:
            self.__newEngine()
        except:
            LOG_CURRENT_EXCEPTION()

        self.__periodicTimerIDEngine = BigWorld.callback(_PERIODIC_TIME_ENGINE, self.__onPeriodicTimerEngine)

    def __onPeriodicTimer(self):
        global frameTimeStamp
        if frameTimeStamp >= BigWorld.wg_getFrameTimestamp():
            self.__periodicTimerID = BigWorld.callback(0.0, self.__onPeriodicTimer)
            return
        else:
            frameTimeStamp = BigWorld.wg_getFrameTimestamp()
            self.__periodicTimerID = BigWorld.callback(_PERIODIC_TIME, self.__onPeriodicTimer)
            self.detailedEngineState.refresh(self.__vehicle.getSpeed(), self.__vehicle.typeDescriptor)
            try:
                self.__updateVibrations()
            except Exception:
                LOG_CURRENT_EXCEPTION()

            try:
                if self.__lightFxCtrl is not None:
                    self.__lightFxCtrl.update(self.__vehicle)
                if self.__auxiliaryFxCtrl is not None:
                    self.__auxiliaryFxCtrl.update(self.__vehicle)
                self.__updateWaterStatus()
            except:
                LOG_CURRENT_EXCEPTION()

            if not self.__vehicle.isAlive():
                return
            try:
                self.__distanceFromPlayer = (BigWorld.camera().position - self.__vehicle.position).length
                for extraData in self.__vehicle.extras.values():
                    extra = extraData.get('extra', None)
                    if isinstance(extra, vehicle_extras.Fire):
                        extra.checkUnderwater(extraData, self.__vehicle, self.isUnderwater)
                        break

                self.__updateCurrTerrainMatKinds()
                self.__updateMovementSounds()
                self.__updateBlockedMovement()
                self.__updateEffectsLOD()
                self.__trailEffects.update()
                self.__updateExhaust()
                self.__vehicle.filter.placingOnGround = not self.__fashion.suspensionWorking
            except:
                LOG_CURRENT_EXCEPTION()

            return

    def __newEngine(self):
        sound = self.__engineSound
        if sound is None:
            return
        else:
            s = self.__vehicle.filter.speedInfo.value[0]
            m = self.__vehicle.typeDescriptor.physics['weight']
            if self.__vt is not None:
                self.__vt.addValue2('mass', m)
            p = self.__vehicle.typeDescriptor.physics['enginePower']
            if self.__vt is not None:
                self.__vt.addValue2('power', p)
            if s > 0:
                v = s / self.__vehicle.typeDescriptor.physics['speedLimits'][0]
            else:
                v = s / self.__vehicle.typeDescriptor.physics['speedLimits'][1]
            if self.__vt is not None:
                self.__vt.addValue2('speed_rel', v)
            if sound.hasParam('speed_rel'):
                param = sound.param('speed_rel')
                param.value = v
            rots = self.__vehicle.filter.speedInfo.value[1]
            if self.__vt is not None:
                self.__vt.addValue2('rot_speed_abs', rots)
            if sound.hasParam('rot_speed_abs'):
                param = sound.param('rot_speed_abs')
                param.value = rots
            rotrel = rots / self.__vehicle.typeDescriptor.physics['rotationSpeedLimit']
            if self.__vt is not None:
                self.__vt.addValue2('rot_speed_rel', rotrel)
            if sound.hasParam('rot_speed_rel'):
                param = sound.param('rot_speed_rel')
                param.value = rotrel
            if self.__vt is not None:
                self.__vt.addValue2('speed_abs', s)
            if sound.hasParam('speed_abs'):
                param = sound.param('speed_abs')
                param.value = s
            sr = self.__vehicle.typeDescriptor.physics['speedLimits'][0] + self.__vehicle.typeDescriptor.physics['speedLimits'][1]
            if self.__vt is not None:
                self.__vt.addValue2('speed range', sr)
            srg = sr / 3
            if self.__vt is not None:
                self.__vt.addValue2('speed range for one gear', srg)
            gear_num = math.ceil(math.floor(math.fabs(s) * 50) / 50 / srg)
            if self.__vt is not None:
                self.__vt.addValue2('gear', gear_num)
            if sound.hasParam('gear_num'):
                param = sound.param('gear_num')
                param.value = gear_num
            rpm = math.fabs(1 + (s - gear_num * srg) / srg)
            if gear_num == 0:
                rpm = 0
            if sound.hasParam('RPM'):
                param = sound.param('RPM')
                param.value = rpm
            if self.__vt is not None:
                self.__vt.addValue2('RPM', rpm)
            a = 0
            if self.__prevVelocity is not None and self.__prevTime is not None and BigWorld.time() != self.__prevTime:
                a = (s - self.__prevVelocity) / (BigWorld.time() - self.__prevTime)
                if a > 1.5:
                    a = 1.5
                if a < -1.5:
                    a = -1.5
                if self.__vt is not None:
                    self.__vt.addValue2('acc_abs', a)
            self.__prevVelocity = s
            self.__prevTime = BigWorld.time()
            if sound.hasParam('acc_abs'):
                param = sound.param('acc_abs')
                param.value = a
            if self.__engineMode[0] == 3:
                l = 2
            elif self.__engineMode[0] == 2:
                l = 3
            else:
                l = self.__engineMode[0]
            if self.__vt is not None:
                self.__vt.addValue2('engine_load', l)
            if sound.hasParam('engine_load'):
                param = sound.param('engine_load')
                param.value = l
            return

    def __updateMovementSounds(self):
        vehicle = self.__vehicle
        isTooFar = self.__distanceFromPlayer > _LOD_DISTANCE_SOUNDS
        if isTooFar != self.__isEngineSoundMutedByLOD:
            self.__isEngineSoundMutedByLOD = isTooFar
            if isTooFar:
                if self.__engineSound is not None:
                    self.__engineSound.stop()
                if self.__movementSound is not None:
                    self.__movementSound.stop()
            else:
                self.changeEngineMode(self.__engineMode)
        if not isTooFar:
            if self.__engineSound is not None:
                VehicleAppearance.VehicleSoundsChecker.checkAndPlay(self.__engineSound)
            if self.__movementSound is not None:
                VehicleAppearance.VehicleSoundsChecker.checkAndPlay(self.__movementSound)
        time = BigWorld.time()
        self.__updateTrackSounds()
        self.__newEngine()
        return

    def __newTrackSounds(self):
        sound = self.__movementSound
        if sound is None:
            return
        else:
            s = self.__vehicle.filter.speedInfo.value[0]
            if sound.hasParam('speed_abs'):
                param = sound.param('speed_abs')
                param.value = s
            rots = self.__vehicle.filter.speedInfo.value[1]
            rotrel = rots / self.__vehicle.typeDescriptor.physics['rotationSpeedLimit']
            if self.__vt is not None:
                self.__vt.addValue2('rot_speed_rel', rotrel)
            if sound.hasParam('rot_speed_rel'):
                param = sound.param('rot_speed_rel')
                param.value = rotrel
            return

    def __updateTrackSounds(self):
        sound = self.__movementSound
        if sound is None:
            return
        else:
            filter = self.__vehicle.filter
            fashion = self.__fashion
            isFlyingParam = sound.param('flying')
            if isFlyingParam is not None:
                if filter.placingOnGround:
                    contactsWithGround = filter.numLeftTrackContacts + filter.numRightTrackContacts
                    isFlyingParam.value = 0.0 if contactsWithGround > 0 else 1.0
                else:
                    isFlyingParam.value = 1.0 if fashion.isFlying else 0.0
            speedFraction = filter.speedInfo.value[0]
            speedFraction = abs(speedFraction / self.__vehicle.typeDescriptor.physics['speedLimits'][0])
            param = sound.param('speed')
            if param is not None:
                param.value = min(1.0, speedFraction)
            if not self.__vehicle.isPlayer:
                toZeroParams = _EFFECT_MATERIALS_HARDNESS.keys()
                toZeroParams += ['hardness', 'friction', 'roughness']
                for paramName in toZeroParams:
                    param = sound.param(paramName)
                    if param is not None:
                        param.value = 0.0

                return
            matEffectsUnderTracks = dict(((effectMaterial, 0.0) for effectMaterial in _EFFECT_MATERIALS_HARDNESS))
            powerMode = self.__engineMode[0]
            if self.__isInWater and powerMode > 1.0 and speedFraction > 0.01:
                matEffectsUnderTracks['water'] = len(self.__currTerrainMatKind)
            else:
                for matKind in self.__currTerrainMatKind:
                    effectIndex = calcEffectMaterialIndex(matKind)
                    if effectIndex is not None:
                        effectMaterial = material_kinds.EFFECT_MATERIALS[effectIndex]
                        if effectMaterial in matEffectsUnderTracks:
                            matEffectsUnderTracks[effectMaterial] = matEffectsUnderTracks.get(effectMaterial, 0) + 1.0

            hardness = 0.0
            for effectMaterial, amount in matEffectsUnderTracks.iteritems():
                param = sound.param(effectMaterial)
                if param is not None:
                    param.value = amount / len(self.__currTerrainMatKind)
                hardness += _EFFECT_MATERIALS_HARDNESS.get(effectMaterial, 0) * amount

            hardnessParam = sound.param('hardness')
            if hardnessParam is not None:
                hardnessParam.value = hardness / len(self.__currTerrainMatKind)
            strafeParam = sound.param('friction')
            if strafeParam is not None:
                angPart = min(abs(filter.angularSpeed) * _FRICTION_ANG_FACTOR, _FRICTION_ANG_BOUND)
                strafePart = min(abs(filter.strafeSpeed) * _FRICTION_STRAFE_FACTOR, _FRICTION_STRAFE_BOUND)
                frictionValue = max(angPart, strafePart)
                strafeParam.value = frictionValue
            roughnessParam = sound.param('roughness')
            if roughnessParam is not None:
                speed = filter.speedInfo.value[2]
                rds = _ROUGHNESS_DECREASE_SPEEDS
                decFactor = (speed - rds[0]) / (rds[1] - rds[0])
                decFactor = 0.0 if decFactor <= 0.0 else (decFactor if decFactor <= 1.0 else 1.0)
                subs = _ROUGHNESS_DECREASE_FACTOR2 * decFactor
                decFactor = 1.0 - (1.0 - _ROUGHNESS_DECREASE_FACTOR) * decFactor
                surfaceCurvature = None
                if filter.placingOnGround:
                    surfaceCurvature = filter.suspCompressionRate
                else:
                    surfaceCurvature = fashion.suspCompressionRate
                roughness = (surfaceCurvature * 2 * speedFraction - subs) * decFactor
                roughnessParam.value = 0 if roughness <= 0.0 else (roughness if roughness <= 1.0 else 1.0)
            return

    def __updateBlockedMovement(self):
        blockingForce = 0.0
        powerMode, dirFlags = self.__engineMode
        vehSpeed = self.__vehicle.filter.speedInfo.value[0]
        if abs(vehSpeed) < 0.25 and powerMode > 1:
            if dirFlags & 1:
                blockingForce = -0.5
            elif dirFlags & 2:
                blockingForce = 0.5

    def __updateEffectsLOD(self):
        enableExhaust = self.__distanceFromPlayer <= _LOD_DISTANCE_EXHAUST
        if enableExhaust != self.__exhaustEffects.enabled:
            self.__exhaustEffects.enable(enableExhaust and not self.__isUnderWater)
        enableTrails = self.__distanceFromPlayer <= _LOD_DISTANCE_TRAIL_PARTICLES and BigWorld.wg_isVehicleDustEnabled()
        self.__trailEffects.enable(enableTrails)

    def __setupTrailParticles(self):
        self.__trailEffects = VehicleTrailEffects(self.__vehicle)

    def __setupTrackDamageSounds(self):
        for i in xrange(2):
            try:
                fakeModel = BigWorld.player().newFakeModel()
                self.__trailEffects.getTrackCenterNode(i).attach(fakeModel)
                self.__trackSounds[i] = (fakeModel, SoundGroups.g_instance.getSound(fakeModel, '/tanks/tank_breakdown/hit_treads'))
            except:
                self.__trackSounds[i] = None
                LOG_CURRENT_EXCEPTION()

        return

    def __destroyTrackDamageSounds(self):
        for i in xrange(2):
            if self.__trackSounds[i] is not None:
                self.__trailEffects.getTrackCenterNode(i).detach(self.__trackSounds[i][0])

        self.__trackSounds = [None, None]
        return

    def __updateCurrTerrainMatKinds(self):
        wasOnSoftTerrain = self.__isOnSoftTerrain()
        testPoints = []
        for iTrack in xrange(2):
            centerNode = self.__trailEffects.getTrackCenterNode(iTrack)
            mMidNode = Math.Matrix(centerNode)
            testPoints.append(mMidNode.translation)

        testPoints.append(self.__vehicle.position)
        for idx, testPoint in enumerate(testPoints):
            res = BigWorld.wg_collideSegment(self.__vehicle.spaceID, testPoint + (0, 2, 0), testPoint + (0, -2, 0), 18)
            self.__currTerrainMatKind[idx] = res[2] if res is not None else 0

        isOnSoftTerrain = self.__isOnSoftTerrain()
        if self.__vehicle.isPlayer and wasOnSoftTerrain != isOnSoftTerrain:
            if isOnSoftTerrain:
                TriggersManager.g_manager.activateTrigger(TRIGGER_TYPE.PLAYER_VEHICLE_ON_SOFT_TERRAIN)
            else:
                TriggersManager.g_manager.deactivateTrigger(TRIGGER_TYPE.PLAYER_VEHICLE_ON_SOFT_TERRAIN)
        self.__fashion.setCurrTerrainMatKinds(self.__currTerrainMatKind[0], self.__currTerrainMatKind[1])
        return

    def __isOnSoftTerrain(self):
        for matKind in self.__currTerrainMatKind:
            groundStr = material_kinds.GROUND_STRENGTHS_BY_IDS.get(matKind)
            if groundStr == 'soft':
                return True

        return False

    def switchFireVibrations(self, bStart):
        if self.__vibrationsCtrl is not None:
            self.__vibrationsCtrl.switchFireVibrations(bStart)
        return

    def executeHitVibrations(self, hitEffectCode):
        if self.__vibrationsCtrl is not None:
            self.__vibrationsCtrl.executeHitVibrations(hitEffectCode)
        return

    def executeRammingVibrations(self, matKind = None):
        if self.__vibrationsCtrl is not None:
            self.__vibrationsCtrl.executeRammingVibrations(self.__vehicle.getSpeed(), matKind)
        return

    def executeShootingVibrations(self, caliber):
        if self.__vibrationsCtrl is not None:
            self.__vibrationsCtrl.executeShootingVibrations(caliber)
        return

    def executeCriticalHitVibrations(self, vehicle, extrasName):
        if self.__vibrationsCtrl is not None:
            self.__vibrationsCtrl.executeCriticalHitVibrations(vehicle, extrasName)
        return

    def __updateVibrations(self):
        if self.__vibrationsCtrl is None:
            return
        else:
            vehicle = self.__vehicle
            crashedTrackCtrl = self.__crashedTracksCtrl
            self.__vibrationsCtrl.update(vehicle, crashedTrackCtrl.isLeftTrackBroken(), crashedTrackCtrl.isRightTrackBroken())
            return

    def __getDamageModelsState(self, vehicleHealth):
        if vehicleHealth > 0:
            return 'undamaged'
        elif vehicleHealth == 0:
            return 'destroyed'
        else:
            return 'exploded'

    def __onChassisModelLoaded(self, model):
        self.__onModelLoaded('chassis', model)

    def __onHullModelLoaded(self, model):
        self.__onModelLoaded('hull', model)

    def __onTurretModelLoaded(self, model):
        self.__onModelLoaded('turret', model)

    def __onGunModelLoaded(self, model):
        self.__onModelLoaded('gun', model)

    def __onModelLoaded(self, name, model):
        if self.modelsDesc is None:
            return
        else:
            desc = self.modelsDesc[name]
            if model is not None:
                desc['_fetchedModel'] = model
            else:
                desc['_fetchedModel'] = desc['model']
                modelState = desc['_stateFunc'](self.__vehicle, self.__curDamageState)
                LOG_ERROR('Model %s not loaded.' % modelState)
            self.__attemptToSetupModels()
            return

    def __assembleModels(self):
        vehicle = self.__vehicle
        hull = self.modelsDesc['hull']
        turret = self.modelsDesc['turret']
        gun = self.modelsDesc['gun']
        try:
            hull['_node'] = vehicle.model.node(_ROOT_NODE_NAME)
            hull['_node'].attach(hull['model'])
            turret['_node'] = hull['model'].node('HP_turretJoint', self.turretMatrix)
            turret['_node'].attach(turret['model'])
            gun['_node'] = turret['model'].node('HP_gunJoint', self.gunMatrix)
            gun['_node'].attach(gun['model'])
            self.updateTurretVisibility()
            if vehicle.isPlayer:
                player = BigWorld.player()
                if player.inputHandler is not None:
                    arcadeCamera = player.inputHandler.ctrls['arcade'].camera
                    if arcadeCamera is not None:
                        arcadeCamera.addVehicleToCollideWith(self)
        except Exception:
            LOG_ERROR('Can not assemble models for %s.' % vehicle.typeDescriptor.name)
            raise

        if IS_DEVELOPMENT and _ENABLE_VEHICLE_VALIDATION:
            self.__validateCallbackId = BigWorld.callback(0.01, self.__validateAssembledModel)
        return

    def __applyVisibility(self):
        vehicle = self.__vehicle
        chassis = self.modelsDesc['chassis']
        hull = self.modelsDesc['hull']
        turret = self.modelsDesc['turret']
        gun = self.modelsDesc['gun']
        chassis['model'].visible = chassis['_visibility'][0]
        chassis['model'].visibleAttachments = chassis['_visibility'][1]
        hull['model'].visible = hull['_visibility'][0]
        hull['model'].visibleAttachments = hull['_visibility'][1]
        turret['model'].visible = turret['_visibility'][0]
        turret['model'].visibleAttachments = turret['_visibility'][1]
        gun['model'].visible = gun['_visibility'][0]
        gun['model'].visibleAttachments = gun['_visibility'][1]

    def __validateAssembledModel(self):
        self.__validateCallbackId = None
        vehicle = self.__vehicle
        vDesc = vehicle.typeDescriptor
        state = self.__curDamageState
        chassis = self.modelsDesc['chassis']
        hull = self.modelsDesc['hull']
        turret = self.modelsDesc['turret']
        gun = self.modelsDesc['gun']
        _validateCfgPos(chassis, hull, vDesc.chassis['hullPosition'], 'hullPosition', vehicle, state)
        _validateCfgPos(hull, turret, vDesc.hull['turretPositions'][0], 'turretPosition', vehicle, state)
        _validateCfgPos(turret, gun, vDesc.turret['gunPosition'], 'gunPosition', vehicle, state)
        return

    def __createExhaust(self):
        self.__exhaustEffects = VehicleExhaustEffects(self.__vehicle.typeDescriptor)

    def __attachExhaust(self, attach):
        if attach:
            hullModel = self.modelsDesc['hull']['model']
            self.__exhaustEffects.attach(hullModel, self.__vehicle.typeDescriptor.hull['exhaust'])
        else:
            self.__exhaustEffects.detach()

    def __destroyExhaust(self):
        self.__exhaustEffects.destroy()

    def __updateExhaust(self):
        if self.__exhaustEffects.enabled == self.__isUnderWater:
            self.__exhaustEffects.enable(not self.__isUnderWater)
        self.__exhaustEffects.changeExhaust(self.__engineMode[0], self.detailedEngineState.rpm)

    def __createGunRecoil(self):
        recoilDescr = self.__vehicle.typeDescriptor.gun['recoil']
        recoil = BigWorld.WGGunRecoil(_GUN_RECOIL_NODE_NAME)
        recoil.setLod(recoilDescr['lodDist'])
        recoil.setDuration(recoilDescr['backoffTime'], recoilDescr['returnTime'])
        recoil.setDepth(recoilDescr['amplitude'])
        self.__gunRecoil = recoil

    def __createStickers(self, prereqs):
        vDesc = self.__vehicle.typeDescriptor
        insigniaRank = self.__vehicle.publicInfo['marksOnGun']
        if BigWorld.player().arenaGuiType == ARENA_GUI_TYPE.HISTORICAL:
            insigniaRank = 0
        self.__vehicleStickers = VehicleStickers(vDesc, insigniaRank)
        clanID = BigWorld.player().arena.vehicles[self.__vehicle.id]['clanDBID']
        self.__vehicleStickers.setClanID(clanID)

    def __attachStickers(self, alpha = 1.0, emblemsOnly = False):
        self.__vehicleStickers.alpha = alpha
        isDamaged = self.__curDamageState != 'undamaged'
        ignoredComponents = set(('turret', 'gun')) if self.__vehicle.isTurretMarkedForDetachment else set()
        modelsAndParents = []
        for componentName in VehicleStickers.COMPONENT_NAMES:
            if componentName in ignoredComponents:
                continue
            modelDesc = self.modelsDesc[componentName]
            modelsAndParents.append((modelDesc['model'], modelDesc['_node']))

        self.__vehicleStickers.attach(modelsAndParents, isDamaged, not emblemsOnly)

    def __detachStickers(self):
        self.__vehicleStickers.detach()

    def __createLampLights(self):
        if not _ALLOW_LAMP_LIGHTS:
            return
        try:
            rotate = Math.Matrix()
            rotate.setRotateX(-0.7)
            self.__leftLightRotMat = Math.Matrix()
            self.__leftLightRotMat.setTranslate(Math.Vector3(0.25, 1.2, 0.25))
            self.__leftLightRotMat.preMultiply(rotate)
            self.__rightLightRotMat = Math.Matrix()
            self.__rightLightRotMat.setTranslate(Math.Vector3(-0.25, 1.2, 0.25))
            self.__rightLightRotMat.preMultiply(rotate)
            hull = self.modelsDesc['hull']
            node1 = hull['model'].node('HP_TrackUp_LFront', self.__leftLightRotMat)
            node2 = hull['model'].node('HP_TrackUp_RFront', self.__rightLightRotMat)
            self.__leftFrontLight = BigWorld.PyChunkSpotLight()
            self.__leftFrontLight.innerRadius = 5
            self.__leftFrontLight.outerRadius = 20
            self.__leftFrontLight.coneAngle = 0.43
            self.__leftFrontLight.castShadows = True
            self.__leftFrontLight.multiplier = 5
            self.__leftFrontLight.source = node1
            self.__leftFrontLight.colour = (255, 255, 255, 0)
            self.__leftFrontLight.specular = 1
            self.__leftFrontLight.diffuse = 1
            self.__leftFrontLight.visible = True
            self.__rightFrontLight = BigWorld.PyChunkSpotLight()
            self.__rightFrontLight.innerRadius = 5
            self.__rightFrontLight.outerRadius = 20
            self.__rightFrontLight.coneAngle = 0.43
            self.__rightFrontLight.castShadows = True
            self.__rightFrontLight.multiplier = 5
            self.__rightFrontLight.source = node2
            self.__rightFrontLight.colour = (255, 255, 255, 0)
            self.__rightFrontLight.specular = 1
            self.__rightFrontLight.diffuse = 1
            self.__rightFrontLight.visible = True
        except Exception:
            LOG_ERROR('Can not attach lamp lights to tank model for %s.' % self.__vehicle.typeDescriptor.name)

    def __destroyLampLights(self):
        if self.__leftFrontLight is not None:
            self.__leftFrontLight.visible = False
            self.__leftFrontLight.source = None
            self.__leftFrontLight = None
            self.__leftLightRotMat = None
        if self.__rightFrontLight is not None:
            self.__rightFrontLight.visible = False
            self.__rightFrontLight.source = None
            self.__rightFrontLight = None
            self.__rightLightRotMat = None
        return

    def __disableStipple(self):
        self.__vehicle.model.stipple = False
        self.__stippleCallbackID = None
        return

    def __computeVehicleHeight(self):
        desc = self.__vehicle.typeDescriptor
        turretBBox = desc.turret['hitTester'].bbox
        gunBBox = desc.gun['hitTester'].bbox
        hullBBox = desc.hull['hitTester'].bbox
        hullTopY = desc.chassis['hullPosition'][1] + hullBBox[1][1]
        turretTopY = desc.chassis['hullPosition'][1] + desc.hull['turretPositions'][0][1] + turretBBox[1][1]
        gunTopY = desc.chassis['hullPosition'][1] + desc.hull['turretPositions'][0][1] + desc.turret['gunPosition'][1] + gunBBox[1][1]
        return max(hullTopY, max(turretTopY, gunTopY))

    def __createOcclusionDecal(self):
        if not self.__useOcclusionDecal:
            return
        self.__destroyOcclusionDecal()
        diffTex = 'maps/spots/TankOcclusion/TankOcclusionMap.dds'
        bumpTex = ''
        hmTex = ''
        priority = 0
        mtype = 4
        influence = 30
        visibilityMask = 4294967295L
        height = 0.0
        stretchX = 1.5
        stretchZ = 1.3
        self.__occlusionDecal = BigWorld.WGOcclusionDecal()
        self.__occlusionDecal.create(diffTex, bumpTex, hmTex, priority, mtype, influence, visibilityMask, height)
        self.__occlusionDecal.setStretch(stretchX, stretchZ)

    def __destroyOcclusionDecal(self):
        if not self.__useOcclusionDecal:
            return
        else:
            if self.__occlusionDecal is not None:
                parent = self.modelsDesc['chassis']['model']
                parent.root.detach(self.__occlusionDecal)
                self.__occlusionDecal = None
            return

    def __attachOcclusionDecal(self):
        if not self.__useOcclusionDecal:
            return
        else:
            if self.__occlusionDecal is not None:
                parent = self.modelsDesc['chassis']['model']
                self.__occlusionDecal.setParent(parent)
                parent.root.attach(self.__occlusionDecal)
            return

    def __setupHavok(self):
        vehicle = self.__vehicle
        vDesc = vehicle.typeDescriptor
        hull = self.modelsDesc['hull']
        hullModel = self.modelsDesc['hull']['model']
        turret = self.modelsDesc['turret']
        turretModel = self.modelsDesc['turret']['model']
        chassis = self.modelsDesc['chassis']
        chassisModel = self.modelsDesc['chassis']['model']
        gun = self.modelsDesc['gun']
        gunModel = self.modelsDesc['gun']['model']
        rootModel = chassisModel
        hkm = BigWorld.wg_createHKAttachment(hullModel, rootModel, vDesc.hull['hitTester'].getBspModel())
        if hkm is not None:
            hull['_node'].attach(hkm)
            hkm.maxAcceleration = vDesc.physics['speedLimits'][0] * 40
            hkm.maxAngularAcceleration = 50
        hull['havok'] = hkm
        hkm = BigWorld.wg_createHKAttachment(turretModel, hullModel, vDesc.turret['hitTester'].getBspModel())
        if hkm is not None:
            turret['_node'].attach(hkm)
            hkm.maxAcceleration = vDesc.physics['speedLimits'][0] * 40
            hkm.maxAngularAcceleration = 150
        turret['havok'] = hkm
        hkm = BigWorld.wg_createHKAttachment(chassisModel, rootModel, vDesc.chassis['hitTester'].getBspModel())
        if hkm is not None:
            chassisModel.root.attach(hkm)
            hkm.addUpdateAttachment(chassisModel)
            hkm.addUpdateAttachment(hullModel)
            hkm.addUpdateAttachment(turretModel)
        chassis['havok'] = hkm
        hkm = BigWorld.wg_createHKAttachment(gunModel, rootModel, vDesc.gun['hitTester'].getBspModel())
        if hkm is not None:
            gun['_node'].attach(hkm)
        gun['havok'] = hkm
        return

    def __removeHavok(self):
        LOG_DEBUG('__removeHavok')
        hull = self.modelsDesc['hull']
        turret = self.modelsDesc['turret']
        chassis = self.modelsDesc['chassis']
        gun = self.modelsDesc['gun']
        if hull.get('havok', None) is not None:
            hull['_node'].detach(hull['havok'])
            hull['havok'] = None
        if turret.get('havok', None) is not None:
            turret['_node'].detach(turret['havok'])
            turret['havok'] = None
        if chassis.get('havok', None) is not None:
            chassis['model'].root.detach(chassis['havok'])
            chassis['havok'] = None
        if gun.get('havok', None) is not None:
            gun['_node'].detach(gun['havok'])
            gun['havok'] = None
        return

    def __havokExplosion(self):
        hull = self.modelsDesc['hull']
        turret = self.modelsDesc['turret']
        chassis = self.modelsDesc['chassis']
        gun = self.modelsDesc['gun']
        if hull['havok'] is not None:
            hull['havok'].releaseBreakables()
        if turret['havok'] is not None:
            turret['havok'].releaseBreakables()
        if chassis['havok'] is not None:
            chassis['havok'].releaseBreakables()
        BigWorld.wg_havokExplosion(hull['model'].position, 300, 5)
        return

    def setupGunMatrixTargets(self, target = None):
        if target is None:
            target = self.__filter
        self.turretMatrix.target = target.turretMatrix
        self.gunMatrix.target = target.gunMatrix
        return


class StippleManager():

    def __init__(self):
        self.__stippleDescs = {}
        self.__stippleToAddDescs = {}

    def showFor(self, vehicle, model):
        if not model.stipple:
            model.stipple = True
            callbackID = BigWorld.callback(0.0, partial(self.__addStippleModel, vehicle.id))
            self.__stippleToAddDescs[vehicle.id] = (model, callbackID)

    def hideIfExistFor(self, vehicle):
        desc = self.__stippleDescs.get(vehicle.id)
        if desc is not None:
            BigWorld.cancelCallback(desc[1])
            BigWorld.player().delModel(desc[0])
            del self.__stippleDescs[vehicle.id]
        desc = self.__stippleToAddDescs.get(vehicle.id)
        if desc is not None:
            BigWorld.cancelCallback(desc[1])
            del self.__stippleToAddDescs[vehicle.id]
        return

    def destroy(self):
        for model, callbackID in self.__stippleDescs.itervalues():
            BigWorld.cancelCallback(callbackID)
            BigWorld.player().delModel(model)

        for model, callbackID in self.__stippleToAddDescs.itervalues():
            BigWorld.cancelCallback(callbackID)

        self.__stippleDescs = None
        self.__stippleToAddDescs = None
        return

    def __addStippleModel(self, vehID):
        model = self.__stippleToAddDescs[vehID][0]
        if model.attached:
            callbackID = BigWorld.callback(0.0, partial(self.__addStippleModel, vehID))
            self.__stippleToAddDescs[vehID] = (model, callbackID)
            return
        del self.__stippleToAddDescs[vehID]
        BigWorld.player().addModel(model)
        callbackID = BigWorld.callback(_VEHICLE_DISAPPEAR_TIME, partial(self.__removeStippleModel, vehID))
        self.__stippleDescs[vehID] = (model, callbackID)

    def __removeStippleModel(self, vehID):
        BigWorld.player().delModel(self.__stippleDescs[vehID][0])
        del self.__stippleDescs[vehID]


class _CrashedTrackController():

    def __init__(self, vehicle, va):
        self.__vehicle = vehicle.proxy
        self.__va = weakref.ref(va)
        self.__flags = 0
        self.__model = None
        self.__fashion = None
        self.__inited = True
        self.__forceHide = False
        self.__loadInfo = [False, False]
        return

    def isLeftTrackBroken(self):
        return self.__flags & 1

    def isRightTrackBroken(self):
        return self.__flags & 2

    def destroy(self):
        self.__vehicle = None
        return

    def setVisible(self, bool):
        self.__forceHide = not bool
        self.__setupTracksHiding(not bool)

    def addTrack(self, isLeft):
        if not self.__inited:
            return
        else:
            if self.__flags == 0 and self.__vehicle is not None and self.__vehicle.isPlayer:
                TriggersManager.g_manager.activateTrigger(TRIGGER_TYPE.PLAYER_VEHICLE_TRACKS_DAMAGED)
            if isLeft:
                self.__flags |= 1
            else:
                self.__flags |= 2
            if self.__model is None:
                self.__loadInfo = [True, isLeft]
                BigWorld.fetchModel(self.__va().modelsDesc['chassis']['_stateFunc'](self.__vehicle, 'destroyed'), self.__onModelLoaded)
            if self.__fashion is None:
                self.__fashion = BigWorld.WGVehicleFashion(True)
                _setupVehicleFashion(self, self.__fashion, self.__vehicle, True)
            self.__fashion.setCrashEffectCoeff(0.0)
            self.__setupTracksHiding()
            return

    def delTrack(self, isLeft):
        if not self.__inited or self.__fashion is None:
            return
        else:
            if self.__loadInfo[0] and self.__loadInfo[1] == isLeft:
                self.__loadInfo = [False, False]
            if isLeft:
                self.__flags &= -2
            else:
                self.__flags &= -3
            self.__setupTracksHiding()
            if self.__flags == 0 and self.__model is not None:
                self.__va().modelsDesc['chassis']['model'].root.detach(self.__model)
                self.__model = None
                self.__fashion = None
            if self.__flags != 0 and self.__vehicle is not None and self.__vehicle.isPlayer:
                TriggersManager.g_manager.deactivateTrigger(TRIGGER_TYPE.PLAYER_VEHICLE_TRACKS_DAMAGED)
            return

    def receiveShotImpulse(self, dir, impulse):
        if not self.__inited or self.__fashion is None:
            return
        else:
            self.__fashion.receiveShotImpulse(dir, impulse)
            return

    def reset(self):
        if not self.__inited:
            return
        else:
            if self.__fashion is not None:
                self.__fashion.setCrashEffectCoeff(-1.0)
            self.__flags = 0
            if self.__model is not None:
                self.__va().modelsDesc['chassis']['model'].root.detach(self.__model)
                self.__model = None
                self.__fashion = None
            return

    def __setupTracksHiding(self, force = False):
        if force or self.__forceHide:
            tracks = (True, True)
            invTracks = (True, True)
        else:
            tracks = (self.__flags & 1, self.__flags & 2)
            invTracks = (not tracks[0], not tracks[1])
        self.__va().fashion.hideTracks(*tracks)
        if self.__fashion is not None:
            self.__fashion.hideTracks(*invTracks)
        return

    def __onModelLoaded(self, model):
        if self.__va() is None or not self.__loadInfo[0] or not self.__inited:
            return
        else:
            va = self.__va()
            self.__loadInfo = [False, False]
            if model:
                self.__model = model
            else:
                self.__inited = False
                modelState = va.modelsDesc['chassis']['_stateFunc'](self.__vehicle, 'destroyed')
                LOG_ERROR('Model %s not loaded.' % modelState)
                return
            try:
                self.__model.wg_fashion = self.__fashion
                va.modelsDesc['chassis']['model'].root.attach(self.__model)
            except:
                va.fashion.hideTracks(False, False)
                self.__inited = False
                LOG_CURRENT_EXCEPTION()

            return


class _SkeletonCollider():

    def __init__(self, vehicle, vehicleAppearance):
        self.__vehicle = vehicle.proxy
        self.__vAppearance = weakref.proxy(vehicleAppearance)
        self.__boxAttachments = list()
        descr = vehicle.typeDescriptor
        descList = [('Scene Root', descr.chassis['hitTester'].bbox),
         ('Scene Root', descr.hull['hitTester'].bbox),
         ('Scene Root', descr.turret['hitTester'].bbox),
         ('Scene Root', descr.gun['hitTester'].bbox)]
        self.__createBoxAttachments(descList)
        vehicle.skeletonCollider = BigWorld.SkeletonCollider()
        for boxAttach in self.__boxAttachments:
            vehicle.skeletonCollider.addCollider(boxAttach)

        self.__vehicleHeight = self.__computeVehicleHeight()

    def destroy(self):
        delattr(self.__vehicle, 'skeletonCollider')
        self.__vehicle = None
        self.__vAppearance = None
        self.__boxAttachments = None
        return

    def attach(self):
        va = self.__vAppearance.modelsDesc
        collider = self.__vehicle.skeletonCollider.getCollider(0)
        va['chassis']['model'].node(collider.name).attach(collider)
        collider = self.__vehicle.skeletonCollider.getCollider(1)
        va['hull']['model'].node(collider.name).attach(collider)
        collider = self.__vehicle.skeletonCollider.getCollider(2)
        va['turret']['model'].node(collider.name).attach(collider)
        collider = self.__vehicle.skeletonCollider.getCollider(3)
        va['gun']['model'].node(collider.name).attach(collider)
        self.__vehicle.model.height = self.__vehicleHeight

    def detach(self):
        va = self.__vAppearance.modelsDesc
        collider = self.__vehicle.skeletonCollider.getCollider(0)
        va['chassis']['model'].node(collider.name).detach(collider)
        collider = self.__vehicle.skeletonCollider.getCollider(1)
        va['hull']['model'].node(collider.name).detach(collider)
        collider = self.__vehicle.skeletonCollider.getCollider(2)
        va['turret']['model'].node(collider.name).detach(collider)
        collider = self.__vehicle.skeletonCollider.getCollider(3)
        va['gun']['model'].node(collider.name).detach(collider)

    def __createBoxAttachments(self, descList):
        for desc in descList:
            boxAttach = BigWorld.BoxAttachment()
            boxAttach.name = desc[0]
            boxAttach.minBounds = desc[1][0]
            boxAttach.maxBounds = desc[1][1]
            self.__boxAttachments.append(boxAttach)


def _almostZero(val, epsilon = 0.0004):
    return -epsilon < val < epsilon


def _createWheelsListByTemplate(startIndex, template, count):
    return [ '%s%d' % (template, i) for i in range(startIndex, startIndex + count) ]


def _setupVehicleFashion(self, fashion, vehicle, isCrashedTrack = False):
    vDesc = vehicle.typeDescriptor
    tracesCfg = vDesc.chassis['traces']
    if isinstance(vehicle.filter, BigWorld.WGVehicleFilter):
        fashion.placingCompensationMatrix = vehicle.filter.placingCompensationMatrix
        fashion.physicsInfo = vehicle.filter.physicsInfo
    fashion.movementInfo = vehicle.filter.movementInfo
    fashion.maxMovement = vDesc.physics['speedLimits'][0]
    try:
        vehicle.filter.placingOnGround = vehicle.filter.placingOnGround if setupTracksFashion(fashion, vehicle.typeDescriptor, isCrashedTrack) else False
        textures = {}
        bumpTexId = -1
        for matKindName, texId in DecalMap.g_instance.getTextureSet(tracesCfg['textureSet']).iteritems():
            if matKindName == 'bump':
                bumpTexId = texId
            else:
                for matKind in material_kinds.EFFECT_MATERIAL_IDS_BY_NAMES[matKindName]:
                    textures[matKind] = texId

        fashion.setTrackTraces(tracesCfg['bufferPrefs'], textures, tracesCfg['centerOffset'], tracesCfg['size'], bumpTexId)
    except:
        LOG_CURRENT_EXCEPTION()


def setupTracksFashion(fashion, vDesc, isCrashedTrack = False):
    retValue = True
    tracesCfg = vDesc.chassis['traces']
    tracksCfg = vDesc.chassis['tracks']
    wheelsCfg = vDesc.chassis['wheels']
    groundNodesCfg = vDesc.chassis['groundNodes']
    suspensionArmsCfg = vDesc.chassis['suspensionArms']
    trackNodesCfg = vDesc.chassis['trackNodes']
    trackParams = vDesc.chassis['trackParams']
    swingingCfg = vDesc.hull['swinging']
    splineDesc = vDesc.chassis['splineDesc']
    pp = tuple((p * m for p, m in zip(swingingCfg['pitchParams'], _PITCH_SWINGING_MODIFIERS)))
    fashion.setPitchSwinging(_ROOT_NODE_NAME, *pp)
    fashion.setRollSwinging(_ROOT_NODE_NAME, *swingingCfg['rollParams'])
    fashion.setShotSwinging(_ROOT_NODE_NAME, swingingCfg['sensitivityToImpulse'])
    splineLod = 9999
    if splineDesc is not None:
        splineLod = splineDesc['lodDist']
    fashion.setLods(tracesCfg['lodDist'], wheelsCfg['lodDist'], tracksCfg['lodDist'], swingingCfg['lodDist'], splineLod)
    fashion.setTracks(tracksCfg['leftMaterial'], tracksCfg['rightMaterial'], tracksCfg['textureScale'])
    if isCrashedTrack:
        return retValue
    else:
        for group in wheelsCfg['groups']:
            nodes = _createWheelsListByTemplate(group[3], group[1], group[2])
            fashion.addWheelGroup(group[0], group[4], nodes)

        for wheel in wheelsCfg['wheels']:
            fashion.addWheel(wheel[0], wheel[2], wheel[1], wheel[3])

        fashion.setLeadingWheelSyncAngle(wheelsCfg['leadingWheelSyncAngle'])
        for groundGroup in groundNodesCfg['groups']:
            nodes = _createWheelsListByTemplate(groundGroup[3], groundGroup[1], groundGroup[2])
            retValue = not fashion.addGroundNodesGroup(nodes, groundGroup[0], groundGroup[4], groundGroup[5])

        for groundNode in groundNodesCfg['nodes']:
            retValue = not fashion.addGroundNode(groundNode[0], groundNode[1], groundNode[2], groundNode[3])

        for suspensionArm in suspensionArmsCfg:
            if suspensionArm[3] is not None and suspensionArm[4] is not None:
                retValue = not fashion.addSuspensionArm(suspensionArm[0], suspensionArm[1], suspensionArm[2], suspensionArm[3], suspensionArm[4])
            elif suspensionArm[5] is not None and suspensionArm[6] is not None:
                retValue = not fashion.addSuspensionArmWheels(suspensionArm[0], suspensionArm[1], suspensionArm[2], suspensionArm[5], suspensionArm[6])

        if trackParams is not None:
            fashion.setTrackParams(trackParams['thickness'], trackParams['elasticity'], trackParams['damping'], trackParams['gravity'], trackParams['maxAmplitude'], trackParams['maxOffset'])
        for trackGroup in trackNodesCfg['groups']:
            nodes = _createWheelsListByTemplate(trackGroup[2], trackGroup[0], trackGroup[1])
            fashion.addTrackNodeGroup(nodes, trackGroup[3])

        for trackNode in trackNodesCfg['nodes']:
            leftSibling = trackNode[3]
            if leftSibling is None:
                leftSibling = ''
            rightSibling = trackNode[4]
            if rightSibling is None:
                rightSibling = ''
            fashion.addTrackNode(trackNode[0], trackNode[1], trackNode[2], leftSibling, rightSibling, trackNode[5], trackNode[6])

        fashion.initialUpdateTracks(1.0)
        return retValue


def setupSplineTracks(fashion, vDesc, chassisModel, prereqs):
    splineDesc = vDesc.chassis['splineDesc']
    if splineDesc is not None:
        leftSpline = None
        rightSpline = None
        segmentModelLeft = segmentModelRight = segment2ModelLeft = segment2ModelRight = None
        modelName = splineDesc['segmentModelLeft']
        try:
            segmentModelLeft = prereqs[modelName]
        except Exception:
            LOG_ERROR("can't load track segment model <%s>" % modelName)

        modelName = splineDesc['segmentModelRight']
        try:
            segmentModelRight = prereqs[modelName]
        except Exception:
            LOG_ERROR("can't load track segment model <%s>" % modelName)

        modelName = splineDesc['segment2ModelLeft']
        if modelName is not None:
            try:
                segment2ModelLeft = prereqs[modelName]
            except Exception:
                LOG_ERROR("can't load track segment 2 model <%s>" % modelName)

        modelName = splineDesc['segment2ModelRight']
        if modelName is not None:
            try:
                segment2ModelRight = prereqs[modelName]
            except Exception:
                LOG_ERROR("can't load track segment 2 model <%s>" % modelName)

        if segmentModelLeft is not None and segmentModelRight is not None:
            if splineDesc['leftDesc'] is not None:
                leftSpline = BigWorld.wg_createSplineTrack(chassisModel, splineDesc['leftDesc'], splineDesc['segmentLength'], segmentModelLeft, splineDesc['segmentOffset'], segment2ModelLeft, splineDesc['segment2Offset'], _ROOT_NODE_NAME, splineDesc['atlasUTiles'], splineDesc['atlasVTiles'])
                if leftSpline is not None:
                    chassisModel.root.attach(leftSpline)
            if splineDesc['rightDesc'] is not None:
                rightSpline = BigWorld.wg_createSplineTrack(chassisModel, splineDesc['rightDesc'], splineDesc['segmentLength'], segmentModelRight, splineDesc['segmentOffset'], segment2ModelRight, splineDesc['segment2Offset'], _ROOT_NODE_NAME, splineDesc['atlasUTiles'], splineDesc['atlasVTiles'])
                if rightSpline is not None:
                    chassisModel.root.attach(rightSpline)
            fashion.setSplineTrack(leftSpline, rightSpline)
    return


def _restoreSoundParam(sound, paramName, paramValue):
    param = sound.param(paramName)
    if param is not None and param.value == 0.0 and param.value != paramValue:
        seekSpeed = param.seekSpeed
        param.seekSpeed = 0
        param.value = paramValue
        param.seekSpeed = seekSpeed
    return


def _seekSoundParam(sound, paramName, paramValue):
    param = sound.param(paramName)
    if param is not None and param.value != paramValue:
        seekSpeed = param.seekSpeed
        param.seekSpeed = 0
        param.value = paramValue
        param.seekSpeed = seekSpeed
    return


def _validateCfgPos(srcModelDesc, dstModelDesc, cfgPos, paramName, vehicle, state):
    invMat = Math.Matrix(srcModelDesc['model'].root)
    invMat.invert()
    invMat.preMultiply(Math.Matrix(dstModelDesc['_node']))
    realOffset = invMat.applyToOrigin()
    length = (realOffset - cfgPos).length
    if length > 0.01 and not _almostZero(realOffset.length):
        modelState = srcModelDesc['_stateFunc'](self.__vehicle, state)
        LOG_WARNING('%s parameter is incorrect. \n Note: it must be <%s>.\nPlayer: %s; Model: %s' % (paramName,
         realOffset,
         vehicle.publicInfo['name'],
         modelState))
        dstModelDesc['model'].visibleAttachments = True
        dstModelDesc['model'].visible = False
