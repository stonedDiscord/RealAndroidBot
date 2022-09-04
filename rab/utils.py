import asyncio
import json
import logging
import operator
import os
import random
import re
import time
from asyncio import Semaphore
from enum import Enum
from math import sin, cos, sqrt, atan2, radians
from os.path import join
from pickle import dump as pickle_dump, load as pickle_load, HIGHEST_PROTOCOL

import yaml
from s2sphere import Cell as S2Cell, LatLng, CellId as S2CellId

import sanitized as conf
from names import POKEMON

logger = logging.getLogger(__name__)

# iPhones 5 + 5C (4S is really not playable)
IPHONES = {'iPhone5,1': 'N41AP',
           'iPhone5,2': 'N42AP',
           'iPhone5,3': 'N48AP',
           'iPhone5,4': 'N49AP',
           'iPhone6,1': 'N51AP',
           'iPhone6,2': 'N53AP',
           'iPhone7,1': 'N56AP',
           'iPhone7,2': 'N61AP',
           'iPhone8,1': 'N71AP',
           'iPhone8,2': 'N66AP',
           'iPhone8,4': 'N69AP',
           'iPhone9,1': 'D10AP',
           'iPhone9,2': 'D11AP',
           'iPhone9,3': 'D101AP',
           'iPhone9,4': 'D111AP',
           'iPhone10,1': 'D20AP',
           'iPhone10,2': 'D21AP',
           'iPhone10,3': 'D22AP',
           'iPhone10,4': 'D201AP',
           'iPhone10,5': 'D211AP',
           'iPhone10,6': 'D221AP'}

GENDER = {'m': 'Male', 'f': 'Female', 'n': 'Genderless'}


def timer(func):
    if asyncio.iscoroutinefunction(func):
        async def wrapper(*args, **kwargs):
            start = time.time()
            result = await func(*args, **kwargs)
            logger.debug('>>> function {} took {:.3f} sec.'.format(func.__name__, time.time() - start))
            return result
    else:
        def wrapper(*args, **kwargs):
            start = time.time()
            result = func(*args, **kwargs)
            logger.debug('>>> function {} took {:.3f} sec.'.format(func.__name__, time.time() - start))
            return result
    return wrapper


def in_func(a, b):
    return a in b


def not_in_func(a, b):
    return a not in b


ops = {
    'lt': operator.lt,
    'le': operator.le,
    'eq': operator.eq,
    'ne': operator.ne,
    'ge': operator.ge,
    'gt': operator.gt,
    'in': in_func,
    'not_in': not_in_func,
}


class Units(Enum):
    miles = 1
    kilometers = 2
    meters = 3


class Unknown:
    """ Enum for unknown DTS. """
    TINY = '?'
    SMALL = '???'
    REGULAR = 'unknown'
    EMPTY = ''

    __unknown_set = {TINY, SMALL, REGULAR}

    @classmethod
    def is_(cls, *args):
        """ Returns true if any given arguments are unknown, else false """
        for arg in args:
            if arg in cls.__unknown_set:
                return True
        return False

    @classmethod
    def is_not(cls, *args):
        """ Returns false if any given arguments are unknown, else true """
        for arg in args:
            if arg in cls.__unknown_set:
                return False
        return True

    @classmethod
    def or_empty(cls, val, default=EMPTY):
        """ Returns an default if unknown, else the original value. """
        return val if val not in cls.__unknown_set else default


class Loader(yaml.SafeLoader):
    def __init__(self, stream):
        self._root = os.path.split(stream.name)[0]
        super(Loader, self).__init__(stream)

    def include(self, node):
        filename = os.path.join(self._root, self.construct_scalar(node))
        with open(filename, 'r', encoding='utf8') as f:
            return yaml.load(f, Loader)


# Return CP multipliers
def get_cp_multipliers():
    if not hasattr(get_cp_multipliers, 'info'):
        file_ = 'data/cp_multipliers.json'
        with open(file_, 'r') as f:
            get_cp_multipliers.info = json.load(f)
    return get_cp_multipliers.info

def get_level_to_cpm():
    with open('data/level_to_cpm.json') as json_data:
        level_to_cpm = json.load(json_data)
    json_data.close()
    
    return level_to_cpm

def get_id_from_names(search_name):
    for poke_id, poke_name in POKEMON.items():
        if poke_name == search_name:
            return poke_id
    return '?'


# Returns the base stats for a pokemon
def get_base_stats(pokemon_id):
    if not hasattr(get_base_stats, 'info'):
        get_base_stats.info = {}
        file_ = 'data/base_stats.json'
        with open(file_, 'r') as f:
            j = json.loads(f.read())
        for id_ in j:
            get_base_stats.info[int(id_)] = {
                "attack": float(j[id_].get('attack')),
                "defense": float(j[id_].get('defense')),
                "stamina": float(j[id_].get('stamina'))
            }

    return get_base_stats.info.get(pokemon_id)


# Returns the highest possible stat product for PvP great league for a pkmn
def get_great_product(pokemon_id):
    if not hasattr(get_great_product, 'info'):
        get_great_product.info = {}
        file_ = 'data/base_stats.json'
        with open(file_, 'r') as f:
            j = json.loads(f.read())
        for id_ in j:
            get_great_product.info[int(id_)] = j[id_].get('1500_product')

    return get_great_product.info.get(pokemon_id)


# Returns the highest possible stat product for PvP ultra league for a pkmn
def get_ultra_product(pokemon_id):
    if not hasattr(get_ultra_product, 'info'):
        get_ultra_product.info = {}
        file_ = 'data/base_stats.json'
        with open(file_, 'r') as f:
            j = json.loads(f.read())
        for id_ in j:
            get_ultra_product.info[int(id_)] = j[id_].get('2500_product')

    return get_ultra_product.info.get(pokemon_id)


def get_evolutions(pokemon_id):
    if not hasattr(get_evolutions, 'info'):
        get_evolutions.info = {}
        file_ = 'data/base_stats.json'
        with open(file_, 'r') as f:
            j = json.loads(f.read())
        for id_ in j:
            get_evolutions.info[int(id_)] = j[id_].get('evolutions')
    return get_evolutions.info.get(pokemon_id)


def get_average_color(x, y, n, image):
    """ Returns a 3-tuple containing the RGB value of the average color of the
    given square bounded area of length = n whose origin (top left corner)
    is (x, y) in the given image"""
    # Usage Example: r, g, b = get_average_color((24,290), 50, image)

    r, g, b = 0, 0, 0
    count = 0
    for s in range(x, x + n + 1):
        for t in range(y, y + n + 1):
            pixlr, pixlg, pixlb = image.getpixel((s, t))
            r += pixlr
            g += pixlg
            b += pixlb
            count += 1
    return (int((r / count)), int((g / count)), int((b / count)))


def splitCoords(text):
    '''Splits a string that represents a coordinate into a list of floats
    Arguments:
        text {string} -- The lat/long pair in string format, e.g.: ' 35.281374, 139.663600  '
    Returns:
        list -- A pair of floats, one for latitude and one for longitude.
        boolean -- False, if not a valid coordinate.
    '''
    try:
        match = re.search('^https://maps.google.com/maps\?q=(.+)$', text)
        if match:
            coord = match[1]
            coord = [float(x.strip()) for x in coord.split(',')]
        else:
            coord = [float(x.strip()) for x in text.split(',')]
        if not isinstance(coord[0], float) or not isinstance(coord[1], float):
            raise ValueError('Not a coordinate')
    except:
        return False
    else:
        return coord


def best_factors(n):
    return next(((i, n // i) for i in range(int(n ** 0.5), 0, -1) if n % i == 0))


def percentage_split(seq, percentages):
    percentages[-1] += 1.0 - sum(percentages)
    prv = 0
    size = len(seq)
    cum_percentage = 0
    for p in percentages:
        cum_percentage += p
        nxt = int(cum_percentage * size)
        yield seq[prv:nxt]
        prv = nxt


def calculate_distance(lat1, lng1, lat2, lng2):
    # approximate radius of earth in km
    R = 6371.0088

    lat1_radian, lng1_radian = radians(float(lat1)), radians(float(lng1))
    lat2_radian, lng2_radian = radians(float(lat2)), radians(float(lng2))

    lng_diff = lng2_radian - lng1_radian
    lat_diff = lat2_radian - lat1_radian

    a = sin(lat_diff / 2) ** 2 + cos(lat1_radian) * cos(lat2_radian) * sin(lng_diff / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c
    logger.debug('Distance between ({:.6f}, {:.6f}) and ({:.6f}, {:.6f}) is {:.0f} km'
                 .format(lat1, lng1, lat2, lng2, distance))
    return distance


def calculate_cooldown(lat1, lng1, lat2, lng2):
    '''Calculates the cooldown time needed
    Returns:
        float -- time in seconds
    '''
    distance = calculate_distance(lat1, lng1, lat2, lng2)
    if distance <= 0.1:
        return 3
    if distance <= 1.0:
        return (distance / 1.0) * 60.0
    if distance <= 2.0:
        return (distance / 2.0) * 90.0
    if distance <= 4.0:
        return (distance / 4.0) * 120.0
    if distance <= 5.0:
        return (distance / 5.0) * 150.0
    if distance <= 8.0:
        return (distance / 8.0) * 360.0
    cooldown = distance / 8.0 * 360.0
    return cooldown if cooldown <= 7200 else 7200


def float_range(start, end, step):
    """range for floats, also capable of iterating backwards"""
    if start > end:
        while end <= start:
            yield start
            start += -step
    else:
        while start <= end:
            yield start
            start += step


def round_coords(point, precision, _round=round):
    return _round(point[0], precision), _round(point[1], precision)


def get_current_hour(now=None, _time=time):
    now = now or _time()
    return round(now - (now % 3600))


def time_until_time(seconds, seen=None, _time=time):
    current_seconds = seen or _time() % 3600
    if current_seconds > seconds:
        return seconds + 3600 - current_seconds
    elif current_seconds + 3600 < seconds:
        return seconds - 3600 - current_seconds
    else:
        return seconds - current_seconds


def load_pickle(name, raise_exception=False):
    location = join(conf.DIRECTORY, 'pickles', '{}.pickle'.format(name))
    try:
        with open(location, 'rb') as f:
            return pickle_load(f)
    except (FileNotFoundError, EOFError):
        if raise_exception:
            raise FileNotFoundError
        else:
            return None


def dump_pickle(name, var):
    folder = join(conf.DIRECTORY, 'pickles')
    try:
        os.mkdir(folder)
    except FileExistsError:
        pass
    except Exception as e:
        raise OSError("Failed to create 'pickles' folder, please create it manually") from e

    location = join(folder, '{}.pickle'.format(name))
    with open(location, 'wb') as f:
        pickle_dump(var, f, HIGHEST_PROTOCOL)


def randomize_point(point, amount=0.0003):
    '''Randomize point, by up to ~47 meters by default.'''
    lat, lon = point
    return (
        random.uniform(lat - amount, lat + amount),
        random.uniform(lon - amount, lon + amount)
    )


def calc_pokemon_level(cp_multiplier):
    if cp_multiplier < 0.734:
        pokemon_level = (58.35178527 * cp_multiplier * cp_multiplier - 2.838007664 * cp_multiplier + 0.8539209906)
    else:
        pokemon_level = 171.0112688 * cp_multiplier - 95.20425243
    pokemon_level = int((round(pokemon_level) * 2) / 2)
    return pokemon_level


def get_gmaps_link(lat, lon):
    return "http://maps.google.com/maps?q={},{}".format(lat, lon)


# Returns a String link to Apple Maps Pin at the location
# Code from PokeAlarm
def get_applemaps_link(lat, lon):
    latLon = '{},{}'.format(repr(lat), repr(lon))
    return 'http://maps.apple.com/maps?daddr={}&z=10&t=s&dirflg=w'.format(latLon)


class FlexibleSemaphore(Semaphore):
    def increment(self, by=1):
        self._value += by
        for idx in range(by):
            self._wake_up_next()

    def decrement(self, by=1):
        self._value -= by

    def value(self):
        return self._value


def get_vertex(cell, v):
    vertex = LatLng.from_point(cell.get_vertex(v))
    return vertex.lat().degrees, vertex.lng().degrees


def get_s2_cell_as_polygon(lat, lon, level=12):
    cell = S2Cell(S2CellId.from_lat_lng(LatLng.from_degrees(lat, lon)).parent(level))
    return [(get_vertex(cell, v)) for v in range(0, 4)]