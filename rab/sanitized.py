import sys

from numbers import Number
from pathlib import Path
from datetime import datetime
from logging import getLogger

try:
    import config
except ImportError as e:
    raise ImportError('Main Config Error') from e

sequence = (tuple, list)
path = (str, Path)
set_sequence = (tuple, list, set, frozenset)
set_sequence_range = (tuple, list, range, set, frozenset)

#worker_count = config.GRID[0] * config.GRID[1]
monocle_dir = Path(__file__).resolve().parents[1]

_valid_types = {
    'BETA_CLIENT': bool,
    'DB_ENGINE': str,
    'DB_ENGINE2': str,
    'DB_POOL_RECYCLE': Number,
    'DB_POOL_SIZE': Number,
    'DB_MAX_OVERFLOW': Number,
    'ENABLE_ITEM_MANAGEMENT': bool,
    'ENABLE_KEEP_MON': bool,
    'ENABLE_KEEP_PVP': bool,
    'ENABLE_KEEP_SHINY': bool,
    'GL_CP': int,
    'GL_RATING': Number,
    'GL_TO_KEEP': sequence,
    'ITEM_CONFIG': dict,
    'ITEM_MANAGEMENT_INTERVAL': Number,
    'MIN_ATK': int,
    'MIN_DEF': int,
    'MIN_LVL': Number,
    'MIN_STA': int,
    'SCREENSHOT_POSITIONS': dict,
    'UL_CP': int,
    'UL_RATING': Number,
    'UL_TO_KEEP': sequence
}

_defaults = {
    'BETA_CLIENT': False,
    'DB_POOL_RECYCLE': 299,
    'DB_POOL_SIZE': 5,
    'DB_MAX_OVERFLOW': 10,
    'ENABLE_ITEM_MANAGEMENT': False,
    'ENABLE_KEEP_MON': True,
    'ENABLE_KEEP_PVP': False,
    'ENABLE_KEEP_SHINY': True,
    'GL_CP': 1450,
    'GL_RATING': 100.0,
    'GL_TO_KEEP': [],
    'ITEM_CONFIG': {},
    'ITEM_MANAGEMENT_INTERVAL': 30,
    'MIN_ATK': 15,
    'MIN_DEF': 15,
    'MIN_LVL': 1,
    'MIN_STA': 15,
    'SCREENSHOT_POSITIONS': {
        "rename": [539, 936],
        "next": [980, 280],
        "keyboard_ok": [933,1085],
        "rename_ok": [540, 1050],
        "close_calcy_dialog": [966, 1092],
        "edit_box": [90, 1090],
        "paste": [483, 1092],
        "favorite_button": [980, 156],
        "favorite_button_box": [960, 142, 1001, 180],
        "pokemon_menu_button": [933, 1777],
        "appraise_button": [934, 1377],
        "continue_appraisal": [590, 1770],
        "dismiss_calcy": [555, 1296],
        "appraisal_box": [45, 1664, 1032, 1872],
        "pokestop": [540, 1250],
        "spin_swipe": [150, 1040, 540, 1040],
        "x_button": [540, 1750],
        "quest_button": [1000, 1870],
        "claim_reward_box": [320, 1230, 750, 1310],
        "exit_encounter": [90, 150],
        "im_a_passenger_button_box": [320, 1425, 760, 1490],
        "exit_other": [550,830],
        "oh_hatching_box": [430, 430, 700, 640],
        "shop_button_text_box": [470,1130,615,1200],
        "bottom_pokestop_bar": [240, 1958, 300, 1985],
        "char_box": [500,1160,590,1260],
        "char": [550,1220]
    },
    'UL_CP': 2350,
    'UL_RATING': 100.0,
    'UL_TO_KEEP': []
}


class Config:
    __spec__ = __spec__
    __slots__ = tuple(_valid_types.keys()) + ('log',)

    def __init__(self):
        self.log = getLogger('sanitizer')
        for key, value in (x for x in vars(config).items() if x[0].isupper()):
            try:
                if isinstance(value, _valid_types[key]):
                    setattr(self, key, value)
                    if key in _defaults:
                        del _defaults[key]
                elif key in _defaults and value is _defaults[key]:
                    setattr(self, key, _defaults.pop(key))
                else:
                    valid = _valid_types[key]
                    actual = type(value).__name__
                    if isinstance(valid, type):
                        err = '{} must be {}. Yours is: {}.'.format(
                            key, valid.__name__, actual)
                    else:
                        types = ', '.join((x.__name__ for x in valid))
                        err = '{} must be one of {}. Yours is: {}'.format(
                            key, types, actual)
                    raise TypeError(err)
            except KeyError:
                self.log.warning('{} is not a valid config option'.format(key))

    def __getattr__(self, name):
        try:
            default = _defaults.pop(name)
            setattr(self, name, default)
            return default
        except KeyError:
            if name == '__path__':
                return
            if name == '__file__':
                return
            err = '{} not in config, and no default has been set.'.format(name)
            self.log.error(err)
            raise AttributeError(err)

sys.modules[__name__] = Config()

del _valid_types, config
