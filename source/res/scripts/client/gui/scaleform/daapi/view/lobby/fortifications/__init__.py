# Embedded file name: scripts/client/gui/Scaleform/daapi/view/lobby/fortifications/__init__.py
from gui.Scaleform.framework.ScopeTemplates import SimpleScope, VIEW_SCOPE, LOBBY_SUB_SCOPE, MultipleScope, SCOPE_TYPE, WINDOW_SCOPE
from gui.Scaleform.genConsts.FORTIFICATION_ALIASES import FORTIFICATION_ALIASES
from gui.Scaleform.locale.FORTIFICATIONS import FORTIFICATIONS
from gui.shared.utils import CONST_CONTAINER

class FORT_SCOPE_TYPE(CONST_CONTAINER):
    FORT_WINDOWED_MULTISCOPE = 'FortWindowed'


TRANSPORTING_DISABLED = 'transportingDisabled'
TRANSPORTING_CONFIRMED_EVENT = 'onTransportingConfirmed'

class FortifiedWindowScopes(object):
    ASSIGN_BUILD_DLG_SCOPE = SimpleScope(FORTIFICATION_ALIASES.FORT_FIXED_PLAYERS_WINDOW_ALIAS, VIEW_SCOPE)
    FORT_MAIN_SCOPE = SimpleScope(FORTIFICATION_ALIASES.MAIN_VIEW_ALIAS, LOBBY_SUB_SCOPE)
    FORT_WINDOWED_MULTISCOPE = MultipleScope(FORT_SCOPE_TYPE.FORT_WINDOWED_MULTISCOPE, (WINDOW_SCOPE, FORT_MAIN_SCOPE))


class FortificationEffects(object):
    NONE_STATE = 'none'
    FADE_IN = 0
    VISIBLE = 2
    FADE_OUT = 1
    INVISIBLE = 3
    DONT_MOVE = 0
    MOVE_UP = 1
    MOVE_DOWN = 2
    TEXTS = {FORTIFICATION_ALIASES.MODE_COMMON: {'descrText': ''},
     FORTIFICATION_ALIASES.MODE_COMMON_TUTORIAL: {'descrText': ''},
     FORTIFICATION_ALIASES.MODE_DIRECTIONS: {'descrText': FORTIFICATIONS.FORTMAINVIEW_DIRECTIONS_SELECTINGSTATUS},
     FORTIFICATION_ALIASES.MODE_DIRECTIONS_TUTORIAL: {'descrText': ''},
     FORTIFICATION_ALIASES.MODE_TRANSPORTING: {'descrText': FORTIFICATIONS.FORTMAINVIEW_TRANSPORTING_EXPORTINGSTATUS},
     FORTIFICATION_ALIASES.MODE_TRANSPORTING_TUTORIAL: {'descrText': FORTIFICATIONS.FORTMAINVIEW_TRANSPORTING_TUTORIALDESCR},
     TRANSPORTING_DISABLED: {'descrText': FORTIFICATIONS.FORTMAINVIEW_TRANSPORTING_TUTORIALDESCRDISABLED}}
    STATES = {NONE_STATE: {FORTIFICATION_ALIASES.MODE_COMMON: {'yellowVignette': INVISIBLE,
                                                      'descrTextMove': DONT_MOVE,
                                                      'statsBtn': VISIBLE,
                                                      'clanListBtn': VISIBLE,
                                                      'transportToggle': VISIBLE,
                                                      'clanInfo': VISIBLE,
                                                      'totalDepotQuantity': VISIBLE,
                                                      'footerBitmapFill': VISIBLE,
                                                      'ordersPanel': VISIBLE,
                                                      'sortieBtn': VISIBLE,
                                                      'intelligenceButton': VISIBLE,
                                                      'leaveModeBtn': INVISIBLE,
                                                      'tutorialArrow': INVISIBLE},
                  FORTIFICATION_ALIASES.MODE_COMMON_TUTORIAL: {'yellowVignette': VISIBLE,
                                                               'descrTextMove': DONT_MOVE,
                                                               'statsBtn': INVISIBLE,
                                                               'clanListBtn': INVISIBLE,
                                                               'transportToggle': VISIBLE,
                                                               'clanInfo': INVISIBLE,
                                                               'totalDepotQuantity': INVISIBLE,
                                                               'footerBitmapFill': INVISIBLE,
                                                               'ordersPanel': INVISIBLE,
                                                               'sortieBtn': INVISIBLE,
                                                               'intelligenceButton': INVISIBLE,
                                                               'leaveModeBtn': INVISIBLE,
                                                               'tutorialArrow': INVISIBLE},
                  FORTIFICATION_ALIASES.MODE_DIRECTIONS_TUTORIAL: {'yellowVignette': VISIBLE,
                                                                   'descrTextMove': DONT_MOVE,
                                                                   'statsBtn': INVISIBLE,
                                                                   'clanListBtn': INVISIBLE,
                                                                   'transportToggle': INVISIBLE,
                                                                   'clanInfo': INVISIBLE,
                                                                   'totalDepotQuantity': INVISIBLE,
                                                                   'footerBitmapFill': INVISIBLE,
                                                                   'ordersPanel': INVISIBLE,
                                                                   'sortieBtn': INVISIBLE,
                                                                   'intelligenceButton': INVISIBLE,
                                                                   'leaveModeBtn': INVISIBLE,
                                                                   'tutorialArrow': INVISIBLE},
                  FORTIFICATION_ALIASES.MODE_TRANSPORTING_TUTORIAL: {'yellowVignette': VISIBLE,
                                                                     'descrTextMove': MOVE_DOWN,
                                                                     'statsBtn': INVISIBLE,
                                                                     'clanListBtn': INVISIBLE,
                                                                     'transportToggle': VISIBLE,
                                                                     'clanInfo': INVISIBLE,
                                                                     'totalDepotQuantity': VISIBLE,
                                                                     'footerBitmapFill': INVISIBLE,
                                                                     'ordersPanel': INVISIBLE,
                                                                     'sortieBtn': INVISIBLE,
                                                                     'intelligenceButton': INVISIBLE,
                                                                     'leaveModeBtn': INVISIBLE,
                                                                     'tutorialArrow': FADE_IN}},
     FORTIFICATION_ALIASES.MODE_COMMON: {FORTIFICATION_ALIASES.MODE_DIRECTIONS: {'yellowVignette': FADE_IN,
                                                                                 'descrTextMove': MOVE_DOWN,
                                                                                 'statsBtn': VISIBLE,
                                                                                 'clanListBtn': VISIBLE,
                                                                                 'transportToggle': INVISIBLE,
                                                                                 'clanInfo': FADE_OUT,
                                                                                 'totalDepotQuantity': INVISIBLE,
                                                                                 'footerBitmapFill': FADE_OUT,
                                                                                 'ordersPanel': FADE_OUT,
                                                                                 'sortieBtn': FADE_OUT,
                                                                                 'intelligenceButton': FADE_OUT,
                                                                                 'leaveModeBtn': FADE_IN,
                                                                                 'tutorialArrow': INVISIBLE},
                                         FORTIFICATION_ALIASES.MODE_TRANSPORTING: {'yellowVignette': FADE_IN,
                                                                                   'descrTextMove': MOVE_DOWN,
                                                                                   'statsBtn': FADE_OUT,
                                                                                   'clanListBtn': FADE_OUT,
                                                                                   'transportToggle': VISIBLE,
                                                                                   'clanInfo': FADE_OUT,
                                                                                   'totalDepotQuantity': VISIBLE,
                                                                                   'footerBitmapFill': FADE_OUT,
                                                                                   'ordersPanel': FADE_OUT,
                                                                                   'sortieBtn': FADE_OUT,
                                                                                   'intelligenceButton': FADE_OUT,
                                                                                   'leaveModeBtn': FADE_IN,
                                                                                   'tutorialArrow': INVISIBLE}},
     FORTIFICATION_ALIASES.MODE_TRANSPORTING: {FORTIFICATION_ALIASES.MODE_COMMON: {'yellowVignette': FADE_OUT,
                                                                                   'descrTextMove': MOVE_UP,
                                                                                   'statsBtn': FADE_IN,
                                                                                   'clanListBtn': FADE_IN,
                                                                                   'transportToggle': VISIBLE,
                                                                                   'clanInfo': FADE_IN,
                                                                                   'totalDepotQuantity': VISIBLE,
                                                                                   'footerBitmapFill': FADE_IN,
                                                                                   'ordersPanel': FADE_IN,
                                                                                   'sortieBtn': FADE_IN,
                                                                                   'intelligenceButton': FADE_IN,
                                                                                   'leaveModeBtn': FADE_OUT,
                                                                                   'tutorialArrow': INVISIBLE}},
     FORTIFICATION_ALIASES.MODE_DIRECTIONS: {FORTIFICATION_ALIASES.MODE_COMMON: {'yellowVignette': FADE_OUT,
                                                                                 'descrTextMove': MOVE_UP,
                                                                                 'statsBtn': VISIBLE,
                                                                                 'clanListBtn': VISIBLE,
                                                                                 'transportToggle': VISIBLE,
                                                                                 'clanInfo': FADE_IN,
                                                                                 'totalDepotQuantity': VISIBLE,
                                                                                 'footerBitmapFill': FADE_IN,
                                                                                 'ordersPanel': FADE_IN,
                                                                                 'sortieBtn': FADE_IN,
                                                                                 'intelligenceButton': FADE_IN,
                                                                                 'leaveModeBtn': FADE_OUT,
                                                                                 'tutorialArrow': INVISIBLE}},
     FORTIFICATION_ALIASES.MODE_DIRECTIONS_TUTORIAL: {FORTIFICATION_ALIASES.MODE_COMMON_TUTORIAL: {'yellowVignette': VISIBLE,
                                                                                                   'descrTextMove': DONT_MOVE,
                                                                                                   'statsBtn': INVISIBLE,
                                                                                                   'clanListBtn': INVISIBLE,
                                                                                                   'transportToggle': INVISIBLE,
                                                                                                   'clanInfo': INVISIBLE,
                                                                                                   'totalDepotQuantity': INVISIBLE,
                                                                                                   'footerBitmapFill': INVISIBLE,
                                                                                                   'ordersPanel': INVISIBLE,
                                                                                                   'sortieBtn': INVISIBLE,
                                                                                                   'intelligenceButton': INVISIBLE,
                                                                                                   'leaveModeBtn': INVISIBLE,
                                                                                                   'tutorialArrow': INVISIBLE}},
     FORTIFICATION_ALIASES.MODE_COMMON_TUTORIAL: {FORTIFICATION_ALIASES.MODE_TRANSPORTING_TUTORIAL: {'yellowVignette': VISIBLE,
                                                                                                     'descrTextMove': MOVE_DOWN,
                                                                                                     'statsBtn': INVISIBLE,
                                                                                                     'clanListBtn': INVISIBLE,
                                                                                                     'transportToggle': VISIBLE,
                                                                                                     'clanInfo': INVISIBLE,
                                                                                                     'totalDepotQuantity': FADE_IN,
                                                                                                     'footerBitmapFill': INVISIBLE,
                                                                                                     'ordersPanel': INVISIBLE,
                                                                                                     'sortieBtn': INVISIBLE,
                                                                                                     'intelligenceButton': INVISIBLE,
                                                                                                     'leaveModeBtn': INVISIBLE,
                                                                                                     'tutorialArrow': FADE_IN}},
     FORTIFICATION_ALIASES.MODE_TRANSPORTING_TUTORIAL: {FORTIFICATION_ALIASES.MODE_TRANSPORTING: {'yellowVignette': VISIBLE,
                                                                                                  'descrTextMove': DONT_MOVE,
                                                                                                  'statsBtn': INVISIBLE,
                                                                                                  'clanListBtn': INVISIBLE,
                                                                                                  'transportToggle': INVISIBLE,
                                                                                                  'clanInfo': INVISIBLE,
                                                                                                  'totalDepotQuantity': VISIBLE,
                                                                                                  'footerBitmapFill': INVISIBLE,
                                                                                                  'ordersPanel': INVISIBLE,
                                                                                                  'sortieBtn': INVISIBLE,
                                                                                                  'intelligenceButton': INVISIBLE,
                                                                                                  'leaveModeBtn': INVISIBLE,
                                                                                                  'tutorialArrow': FADE_OUT}}}