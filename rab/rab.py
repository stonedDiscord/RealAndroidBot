import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
import random
#import threading

import subprocess
import signal
from datetime import datetime

# import beepy
import uiautomator2 as u2
import yaml

from ImageUtils import save_screenshot, extract_text_from_image
from Pokemon import Pokemon
from PokemonUtils import get_pokemon_name_from_text
from action import manage_gifts, select_vaild_pokemon, tap_screen, resize_coords, screen_cap, spin_pokestop, \
    tap_close_btn, catch_pokemon, tap_exit_trainer, close_team_rocket, fight_team_rocket, \
    after_pokemon_caught, tap_incubate, tap_caught_ok_btn, select_egg, \
    tap_exit_btn, tap_remove_quest_ok_btn, clear_quest, set_config, check_quest, \
    clear_pokemon_inventory, tap_pokeball_btn, tap_open_pokemon_btn, tap_collect_component, \
    tap_equip_radar, tap_gym_btn, fav_last_caught, check_player_level, poke_location, report_encounter
from check_shiny import load_tap_pokemon, load_spawns
from find_object import find_object_to_tap, walk_towards_pokestops, find_pokestop
from item import check_items
from page_detection import is_home_page, is_gym_page, is_pokestop_page, is_catch_pokemon_page, is_team_rocket_page, \
    is_egg_hatched_page, is_egg_hatched_oh, is_incubate_page, is_bag_full, is_mon_details_page, is_shop_page, is_nearby_page, \
    is_mon_caught_page, is_incubate_page2, is_warning_page, is_error_page, is_power_up_page, is_grunt_defeated_page, \
    has_completed_quest_on_map, completed_quest_position, is_team_selection, is_join_raid_battle, is_main_menu_page, \
    is_profile_page, is_pokemon_full, is_pokestop_scan_page, is_gym_badge, is_exit_trainer_dialog, \
    is_plus_disconnected, is_weather_warning_page, is_not_pokestop_gym_on_map, is_incense
from PvpUtils import get_pvp_info
from utils import Loader, Unknown, get_id_from_names, calculate_cooldown, get_average_color, timer, POKEMON

from IncomingData import LocalNetworkHandler
from pokemonlib import PokemonGo, PhoneNotConnectedError
from Webhook import send_to_discord, send_to_telegram
from pgsharp import PGSharp
from mad import MADClass

# database
from db import session_scope, session2_scope, device_checkin, donation_status, get_empty_forts, update_forts, get_empty_pokestops, update_pokestops

localnetwork = None

Loader.add_constructor('!include', Loader.include)

spawns_reported = []  # store past 100 spawns for reference
spawns_to_check = []
spawns_to_snipe = []
device_id = None
wifi_ip = None
wifi_port = None
last_active_location = {}
last_caught_location = {}
telegram_id = None
telegram_src = None
feed_dict = None
feed_src = []
snipe_src = []
snipe_count = {}
donor_until = None

config = None  # Set global config

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)-7s | %(message)s', level='INFO', datefmt='%H:%M:%S')
logger = logging.getLogger('rab')

client = None
pgsharp_client = None
mad_client = None
# Features
PGSHARPV2 = 0


def is_json(s):
    try:
        json_object = json.loads(s)
    except ValueError as e:
        return False
    return True


def check_pm_iv(s):
    m = re.search(r'\b(?P<atk>\d+)/(?P<def>\d+)/(?P<sta>\d+)\b', s)
    if not m:
        if '💯' in s:
            return 100

    try:
        m = re.search(r'\bIV ?(\d*\.?\d*)\b', s.upper())
        if m:
            if m.group(1):
                return int(float(m.group(1)))

        if '#GL' in s.upper() or '#UL' in s.upper():
            m = re.search(r'(\d*\.?\d*) ?%', s.upper())
            if m:
                if m.group(1):
                    return int(float(m.group(1)))
    except:
        logger.critical('Unable to extract IV \n{}\nGroup {}'.format(s, m.group(1)))

    return Unknown.TINY


def check_pm_stats(s):
    m = re.search(r'\b(?P<atk>\d+)/(?P<def>\d+)/(?P<sta>\d+)\b', s)
    if m:
        iv_atk = int(m.group('atk'))
        iv_def = int(m.group('def'))
        iv_sta = int(m.group('sta'))

        return iv_atk, iv_def, iv_sta

    m = re.search(r'\bAtk\*\*\s+(?P<atk>\d+)\s+\*\*Def\*\*\s+(?P<def>\d+)\s+\*\*Sta\*\*\s+(?P<sta>\d+)\b', s)
    if m:
        iv_atk = int(m.group('atk'))
        iv_def = int(m.group('def'))
        iv_sta = int(m.group('sta'))

        return iv_atk, iv_def, iv_sta

    return Unknown.TINY, Unknown.TINY, Unknown.TINY


def check_pm_cp(s):
    m = re.search(r"\bCP\*\*(\d+)\b", s.upper())
    if m:
        return int(m.group(1)) if m and int(m.group(1)) < 5000 else Unknown.TINY
    m = re.search(r"\bCP\s*(\d+)\b", s.upper())
    if m:
        return int(m.group(1)) if m and int(m.group(1)) < 5000 else Unknown.TINY


def check_pm_level(s):
    m = re.search(r"\b(?:LEVEL|LVL|LV|L)\*\*(\d+)\b", s.upper())
    if m:
        return int(m.group(1)) if m and int(m.group(1)) <= 50 else Unknown.TINY
    m = re.search(r"\b(?:LEVEL|LVL|LV|L)\s*(\d+)\b", s.upper())
    return int(m.group(1)) if m and int(m.group(1)) <= 50 else Unknown.TINY


def check_pm_gender(s):
    if 'female' in s.lower() or '♀' in s:
        return 'Female'

    if 'male' in s.lower() or '♂' in s:
        return 'Male'

    if 'genderless' in s.lower() or 'neutral' in s.lower() or u'\u26b2' in s.lower():
        return 'Genderless'

    return Unknown.TINY


def extract_spawn_from_dict(s):
    spawn = json.loads(s)
    logger.debug(spawn)
    if 'dex' in spawn:
        spawn['pokedex'] = int(spawn['dex'])
        spawn['name'] = POKEMON[spawn['pokedex']]

    if 'name' not in spawn:
        spawn['name'] = get_pokemon_name_from_text(s)

    spawn['cp'] = spawn['cp']

    if 'iv' in spawn and spawn['iv'] == 100:
        spawn['atk'], spawn['def'], spawn['sta'] = 15, 15, 15

    if 'atk' in spawn and 'def' in spawn and 'sta' in spawn and \
            isinstance(spawn['atk'], int) and isinstance(spawn['def'], int) and isinstance(spawn['sta'], int):
        spawn['iv'] = round((spawn['atk'] + spawn['def'] + spawn['sta']) * 100 / 45)
        spawn['iv'] = Unknown.TINY if spawn['iv'] < 0 else spawn['iv']
    else:
        spawn['atk'], spawn['def'], spawn['sta'] = Unknown.TINY, Unknown.TINY, Unknown.TINY
    spawn['iv'] = spawn.get('iv', Unknown.TINY)

    if 'lvl' in spawn:
        spawn['level'] = spawn['lvl']

    spawn['level'] = spawn['level']

    if 'latitude' in spawn:
        spawn['latitude'] = spawn['latitude']

    if 'lng' in spawn:
        spawn['longitude'] = spawn['lng']
        spawn['latitude'] = spawn['lat']

    if 'is_lured' not in spawn:
        spawn['is_lured'] = False

    if 'is_boosted' not in spawn:
        spawn['is_boosted'] = False

    if 'is_ditto' not in spawn:
        spawn['is_ditto'] = False

    key_to_pop = ['lvl']
    for key in key_to_pop:
        if key in spawn:
            spawn.pop(key)

    return spawn


def check_coords_from_text(s):
    # word_list = re.split(r"[^a-zA-Z0-9.-]", msg)
    # remove empty output string
    if not s:
        logger.warning('Message contains no text.')
        return None

    word_list = re.findall(r"[a-zA-Z0-9.-]+", s)
    if len(word_list) < 2:
        return None

    for i in range(0, len(word_list) - 1):
        float_ptn = r"[+-]?\d+?\.\d+?$"
        if re.match(float_ptn, word_list[i]) and re.match(float_ptn, word_list[i + 1]):
            # print(float(word_list[i]), float(word_list[i+1]), '\n')
            coordinates = [float(word_list[i]), float(word_list[i + 1])]
            return coordinates

    return None

# For keeping track of what RAB is doing


class RAB_Status(object):
    def __init__(self):
        self.pokemon_encountered = 0  # Everything, including quest and shadow
        self.pokemon_caught = 0  # Everything, including quest and shadow
        self.pokemon_fled = 0
        self.pokemon_unknown_status = 0
        self.pokemon_gave_up = 0
        self.pokemon_no_ball_encounter = 0
        self.pokemon_shiny_encountered = 0
        self.pokemon_shiny_caught = 0
        self.pokemon_shadow_caught = 0
        self.pokemon_quest_caught = 0
        #self.pokestop_spinned = 0
        self.time_started = 0
        self.time_end = 0

    def __dict__(self):
        return dict({
            'pokemon_encountered': self.pokemon_encountered,
            'pokemon_caught': self.pokemon_caught,
            'pokemon_fled': self.pokemon_fled,
            'pokemon_unknown_status': self.pokemon_unknown_status,
            'pokemon_gave_up': self.pokemon_gave_up,
            'pokemon_no_ball_encounter': self.pokemon_no_ball_encounter,
            'pokemon_shiny_encountered': self.pokemon_shiny_encountered,
            'pokemon_shiny_caught': self.pokemon_shiny_caught,
            'pokemon_shadow_caught': self.pokemon_shadow_caught,
            # 'pokemon_quest_caught': self.pokemon_quest_caught,
            'time_started': datetime.fromtimestamp(self.time_started).strftime("%m/%d/%Y, %H:%M:%S") if self.time_started > 0 else '',
            'time_end': datetime.fromtimestamp(self.time_end).strftime("%m/%d/%Y, %H:%M:%S") if self.time_end > 0 else '',
            'time_elapsed': time.strftime('%H:%M:%S', time.gmtime(int(time.time() - self.time_started)))
        })


rab_runtime_status = RAB_Status()


class Main:
    def __init__(self, args):
        self.args = args
        self.device_id = None
        self.wifi_ip = None
        self.wifi_port = None
        self.develop_mode = None
        self.map_mode = None  # developer's personal mode
        self.iteration_num = 0
        self.last_iteration = time.time()
        self.trivial_page_count = 0
        self.trivial_page_threshold = 3
        self.track_bag_time = 0
        self.track_time = int(time.time())
        self.track_pogo_time = int(time.time())
        self.track_quest_time = int(time.time())
        self.bag_full = False
        self.flip_switch = 0
        self.manual_direction = 0  # 0 - up, 1 - down
        self.manual_steps = 0  # reset to 0 when 100 and flip the switch
        self.pokemon = Pokemon()
        self.rabwindow = None
        #self.p = PokemonGo()
        # self.d = u2.connect()
        self.missedcolors = []  # list of [r,g,b] that doesn't yeild results.
        self.repeated_coords = []  # list of coordiates that get repeated.
        self.count_gym_count = 0
        self.max_color_list = 30  # Orginally 20
        self.max_coord_list = 20
        self.poke_in_gym = 0
        self.config = {}
        self.no_spawn_count = 0
        self.zoomout = True
        self.no_action_count = 0
        self.no_action_max = 10
        self.no_ball = False
        self.turn_pokestop = 0

        self.player_level = 0

        # Limited Features
        self.subscriber = False
        self.limited_time_feature = 1622505599  # Monday, 31 May 2021 23:59:59 GMT
        self.pgsharpv2 = False

    async def setup(self):
        global rab_runtime_status
        global device_id
        global wifi_ip
        global wifi_port
        global client
        global telegram_id
        global telegram_src
        global feed_dict
        global feed_src
        global snipe_src
        global donor_until

        if donor_until:
            self.subscriber = True

        self.p = PokemonGo()

        if self.args.develop_mode is not None:
            self.develop_mode = True

        if self.args.map_mode is not None:
            self.map_mode = True

        await self.p.set_adb_path(get_adb(config['client'].get('type', 'Real')))

        if self.args.wifi_ip is not None:
            if self.args.wifi_port is not None:
                self.wifi_port = self.args.wifi_port
                wifi_port = self.wifi_port
            else:
                self.wifi_port = '5555'
                wifi_port = '5555'

            self.wifi_ip = self.args.wifi_ip
            wifi_ip = self.wifi_ip
            await self.p.connect_wifi(self.args.wifi_ip, self.wifi_port)
            self.device_id = self.args.wifi_ip + ':' + self.wifi_port
            await self.p.set_device(self.device_id)

        try:
            if self.args.device_id is None:
                self.device_id = await self.p.get_device()
            else:
                if self.args.wifi_ip is None:
                    await self.p.set_device(self.args.device_id)
                    self.device_id = self.args.device_id
                else:
                    self.device_id = await self.p.get_device()
        except PhoneNotConnectedError:
            logger.exception("RAB is unable to detect any phone attached to your system.")
            input("Press <ENTER> key to continue...")
            sys.exit(1)
        except Exception as e:
            # Change exception to error for deployment (so client wont see chunks of errors during exit)
            logger.error("An error occured while trying to get your device(s)")
            logger.error("Please check device type and connection")
            input("Press <ENTER> key to continue...")
            sys.exit(1)

        if not self.device_id:
            logger.warning("Cannot get devices, please ensure you have connected your device.")
            input("Press <ENTER> key to continue...")
            sys.exit(1)
        device_id = self.device_id

        # load config
        default_config_path = "config.yaml"
        device_config_path = self.device_id + ".yaml"
        if self.args.config_filename:
            config_path = self.args.config_filename
        else:
            config_path = default_config_path
            if os.path.exists(device_config_path):
                config_path = device_config_path

        if not os.path.exists(config_path):
            raise ValueError("Config file {} doesn't exist.".format(self.args.config_filename))

        with open(config_path, "r", encoding='utf8') as f:
            self.config = yaml.load(f, Loader)

        await self.p.set_android_version()
        if self.p.android_version:
            logger.info("Detected Android Version: {}".format(self.p.android_version))

        dpi = None
        if not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:

            orginal_size = await self.p.get_screen_resolution()
            orginal_x = orginal_size[0]
            orginal_y = orginal_size[1]
            logger.info("Detected screen resolution is {},{}".format(orginal_x, orginal_y))
            overwrite_x = 1080
            overwrite_y = 1920
            resize = False
            if self.config['client'].get('lower_resolution', False):
                overwrite_x = 720
                overwrite_y = 1280
                resize = True

            # simulate less than 1080
            # orginal_x = 720
            if orginal_x > orginal_y:
                logger.info("RAB does not officially support emulator or tablet. RAB might not work as intented if you continue.")
                logger.info("If you are using emulator, try set your emulator to phone mode instead of tablet and try again...")

            elif (orginal_x < 1080 and orginal_y < 1920) or overwrite_y < 1920:
                if orginal_x < 720 and orginal_y < 1280:
                    logger.info("We do not support phones with orginal resolution of less than 720x1280")
                    answer = input('Do you want to go ahead and try? (y/n)')
                    if answer.lower() != 'y':
                        return False
                if orginal_x >= 720 and orginal_y >= 1280:
                    overwrite_x = 720
                    overwrite_y = 1280
                resize = True

            orginal_dpi = int(await self.p.get_screen_dpi())
            dpi = orginal_dpi
            if self.config['client'].get('lower_resolution', False):
                logger.info(f"Your orginal screen dpi is {orginal_dpi}")
                if self.config['client'].get('dpi', 0) > 0:
                    dpi = int(self.config['client'].get('dpi', 0))
                else:
                    dpi = int(2/3 * orginal_dpi)
                logger.info(f"RAB will adjust your dpi to {dpi}")
            else:
                if self.config['client'].get('dpi', 0) > 0:
                    dpi = int(self.config['client'].get('dpi', 0))
                    logger.info(f"RAB will adjust your dpi to {dpi}")

            # Change resolution for all
            # orginal_dpi = int(await self.p.get_screen_dpi())
            #logger.info(f"Your orginal screen dpi is {orginal_dpi}")
            #orginal_pixel = orginal_x * orginal_y
            #target_pixel = overwrite_x * overwrite_y
            #dpi = int((target_pixel/orginal_pixel) * orginal_dpi)
            #logger.info(f"RAB will adjust your dpi to {dpi}")

            # Resize screen resolution
            if not self.config['client'].get('manual_set_resolution', False):
                if resize and dpi == orginal_dpi:
                    await self.p.change_screen_resolution(overwrite_x, overwrite_y)
                if resize and dpi != orginal_dpi:
                    await self.p.change_screen_resolution(overwrite_x, overwrite_y, dpi)
                else:
                    await self.p.change_screen_resolution()

                self.config['resize'] = resize
                if self.config['client'].get('dim_phone', True):
                    await self.p.set_screen_brightness(0)

            if self.config['client'].get('navigation_offset', 0) > 0:
                await asyncio.sleep(1.0)  # Let's wait for a while
                await self.p.navigation_offset(self.config['client'].get('navigation_offset', 0))

            # let's do some verification before calling ui
            oversize_top = 0
            im_rgb = await self.p.screencap()
            if resize:
                new_size = (1080, 1920)
                im_rgb = im_rgb.resize(new_size)

            for y in range(1, 250, 1):
                r, g, b, a = im_rgb.getpixel((540, y))
                if r > 0 and g > 0 and b > 0:
                    oversize_top = y
                    if resize:
                        oversize_top = int((oversize_top)*1280/1920)
                    break
            if oversize_top == 1:
                oversize_top = 0

            oversize_bottom = 0
            if self.config['client'].get('navigation_offset', 0) == 0 and self.config['client'].get('auto_offset', True):
                im_rgb = await self.p.screencap()
                if resize:
                    new_size = (1080, 1920)
                    im_rgb = im_rgb.resize(new_size)
                for y in range(1919, 1670, -1):
                    r, g, b, a = im_rgb.getpixel((10, y))
                    if r > 1 and g > 1 and b > 1:
                        oversize_bottom = 1920-y
                        break

                if oversize_bottom == 1:
                    oversize_bottom = 0
                if oversize_bottom > 0:
                    if resize:
                        oversize_bottom = int((oversize_bottom)*1280/1920)
                    self.config['client']['navigation_offset'] = oversize_bottom - 1

            if self.config['client'].get('navigation_offset', 0) == 0 and self.config['client'].get('auto_offset', True) and oversize_bottom == 0:
                # For Samsung and other phones with grey bottom
                oversize_bottom = 0
                for y in range(1919, 1670, -1):
                    r, g, b, a = im_rgb.getpixel((10, y))
                    if ((240 <= r <= 245) and (240 <= g <= 245) and (240 <= b <= 245)):
                        continue
                    else:
                        oversize_bottom = 1920-y
                        break

                if oversize_bottom == 1:
                    oversize_bottom = 0
                if oversize_bottom > 0:
                    if resize:
                        oversize_bottom = int((oversize_bottom)*1280/1920)
                    self.config['client']['navigation_offset'] = oversize_bottom - 1

            if oversize_bottom > 5 and config['client'].get('screenshot_shift', 0) == 0:
                logger.info('Navigation buttons Found, please set your navigation_offset value to {} in config'.format(self.config['client'].get('navigation_offset', 0)))
                await asyncio.sleep(1.0)  # Let's wait for a while
                await self.p.navigation_offset(self.config['client'].get('navigation_offset', 0), oversize_top)
                await asyncio.sleep(2.0)

            await asyncio.sleep(3.0)  # Let's wait for a while

            self.d = u2.connect(self.device_id)
            logger.info('Device Info: {}'.format(self.d.info))
            x, y = self.d.window_size()
            await set_config(self.config)

            if not self.p.android_version:
                device_info = self.d.device_info
                tmp_ver = device_info.get('version')
                if '.' in tmp_ver:
                    spilt_out = tmp_ver.strip().split('.')
                    tmp_ver = spilt_out[0]
                self.p.android_version = int(tmp_ver)
            if self.p.android_version:
                logger.info("Detected Android Version: {}".format(self.p.android_version))
            else:
                logger.info('RAB is unable to get your devices Android version')
                while True:
                    try:
                        userInput = int(input('Please enter your devices Android version to continue: '))
                    except ValueError:
                        logger.info("Entry is not a number! Try again.")
                        continue
                    else:
                        self.p.android_version = userInput
                        break

            im_rgb = await screen_cap(self.d)
            if not is_home_page(im_rgb):
                if is_warning_page(im_rgb):
                    await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                    await asyncio.sleep(3)
                im_rgb = await screen_cap(self.d)
                if not is_home_page(im_rgb):
                    self.d.press("back")
                    await asyncio.sleep(2)

            if client:
                try:
                    with session_scope() as session:
                        is_valid = donation_status(session, telegram_id, self.d.serial)
                    if not is_valid:
                        if is_valid > 0:
                            logger.info(
                                f'You have {is_valid}/3 devices in use. Device list will reset when donation status is renewed.')
                        else:
                            logger.info('Your device is not in our system')
                        feed_dict.clear()
                        feed_dict = {'Free Feed': -1001204900874}
                        feed_src[:] = []
                        snipe_src[:] = []

                        if self.config['shiny_check'].get('enabled', False):
                            #feed_src[:] = default_shiny_feed + config['shiny_check'].get('src_telegram',[])
                            for each_feed in self.config['shiny_check'].get('src_telegram', []):
                                if feed_dict.get(each_feed):
                                    feed_src.append(feed_dict.get(each_feed))

                        if self.config['snipe'].get('enabled', False) and not self.config['shiny_check'].get('enabled', False):
                            #snipe_src[:] = default_snipe_feed + config['snipe'].get('src_telegram',[])
                            for each_feed in self.config['snipe'].get('src_telegram', []):
                                if feed_dict.get(each_feed):
                                    snipe_src.append(feed_dict.get(each_feed))

                        tmp_dic = dict.fromkeys(feed_src + snipe_src)
                        telegram_src[:] = list(tmp_dic)
                except:
                    logger.error('Error connecting to server... continue without server features...')

            logger.info(self.d.app_current())
            appInfor = self.d.app_current()
            if appInfor['package'] != 'com.nianticlabs.pokemongo':
                logger.error('Pokemon Go not found! Resetting...')
                await self.reset_app()

            if self.config['client'].get('auto_offset', True):
                logger.info('Please wait... checking offset...')
                #info = self.d(resourceId='android:id/content', packageName='com.nianticlabs.pokemongo').info
                #y = info['bounds'].get('top')

                # if y > 0:
                #    self.config['client']['screen_offset'] = y
                #    logger.info('Offset Value Found, please set your screen_offset value to {} and disable auto_offset in your config'.format(self.config['client'].get('screen_offset',0)))

                # Assume we are at map
                if resize:
                    x1 = int(540*720/1080)
                    y1 = int(1780*1280/1920)
                    x2 = int(840*720/1080)
                    y2 = int(1600*1280/1920)
                else:
                    x1 = 540
                    y1 = 1780
                    x2 = 840
                    y2 = 1600
                await self.p.tap(x1, y1)
                await asyncio.sleep(2)
                await self.p.tap(x2, y2)
                await asyncio.sleep(3)

                offset_found = False
                im_rgb = await screen_cap(self.d)
                for y in range(0, 200, 10):
                    # Section 1
                    text_ITEM1 = im_rgb.crop([340, 300 + y, 925, 410 + y])
                    text = extract_text_from_image(text_ITEM1)

                    ##print('y: {} text: {}'.format(y,text))
                    if text in ['potion', 'super potion', 'hyper potion', 'max potion', 'revive', 'max revive', 'incense', 'poké ball', 'great ball', 'ultra ball']:
                        offset_found = True
                        self.config['client']['screen_offset'] = y
                        break
                if offset_found:
                    logger.info('Offset Value Found, it is ' + format(self.config['client'].get('screen_offset', 0)))
                    await self.p.tap(x1, y1)
                    await asyncio.sleep(2)
                else:
                    await self.p.tap(x1, y1)
                    await asyncio.sleep(2)
                    logger.warning('Offset Value NOT Found. Your phone might be incompatible with RAB!')

        else:
            self.d = u2.connect(self.device_id)
            logger.info('Device Info: {}'.format(self.d.info))

        await set_config(self.config)

        if self.config['client'].get('lower_resolution', False):
            logger.error('Pokemon Go will now restart for the changes to take place')
            await self.reset_app()
            webhook_url = self.config['discord'].get('webhook_url', '')
            self.d.app_wait("com.nianticlabs.pokemongo", front=True)
            sleep_time = 60 if self.config['client'].get('client', '').lower() != 'mad' else 90
            logger.info(f'Pokemon Go App started, waiting for {sleep_time} secs to login...')
            await asyncio.sleep(sleep_time)
            im_rgb = await screen_cap(self.d)
            if not is_home_page(im_rgb):
                if is_warning_page(im_rgb):
                    await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                    await asyncio.sleep(3)
                im_rgb = await screen_cap(self.d)
                if not is_home_page(im_rgb):
                    self.d.press("back")
                    await asyncio.sleep(2)

            im_rgb = await screen_cap(self.d)
            i = 0
            if not is_home_page(im_rgb):
                while True:
                    im_rgb = await screen_cap(self.d)
                    if is_home_page(im_rgb) or i == 8:
                        break
                    elif i % 2 == 0:
                        await tap_close_btn(self.p)
                        i += 1
                        await asyncio.sleep(0.5)
                    else:
                        # send the magic button
                        self.d.press("back")
                        # await tap_close_btn(self.p)
                        i += 1
                        await asyncio.sleep(0.5)

            # im_rgb = await screen_cap(self.d)
            if is_home_page(im_rgb):
                if webhook_url and self.config['discord'].get('enabled', False):
                    logger.info('Pokemon Go restarted. Resume scanning...')

        # Save sample screenshot
        im_rgb = await screen_cap(self.d)
        filename = self.device_id.replace('.', '').replace(':', '.').replace('-', '.') + '.png'
        logger.info('Saving {} to screenshots folder. You can send this screenshot to RAB Team if you need help'.format(filename))
        save_screenshot(im_rgb, save=True, filename=filename)

        logger.warning('RAB will now attempt to zoom out your Map!')
        logger.warning('If your Map zoomed in instead, quit RAB and restart and change your zoom Out Method under Configuration Tab!')
        if config['client'].get('zoom_option', 'Pinch In'):
            self.d(packageName='com.nianticlabs.pokemongo').pinch_in(percent=60, steps=40)
        else:
            self.d(packageName='com.nianticlabs.pokemongo').pinch_out(percent=70, steps=40)


    async def check_map(self):
        global rab_runtime_status
        global pgsharp_client
        global mad_client
        global last_active_location

        pokemon_caught = None

        if self.iteration_num != 0:
            current_time = int(time.time())
            logger.info('Iteration #{} took {:.3f} sec.'.format(self.iteration_num, current_time - self.last_iteration))
            self.last_iteration = current_time

        logger.info('=' * 50)
        self.iteration_num += 1
        logger.info('>>> Start iteration #{}'.format(self.iteration_num))

        find_team_rocket = False
        if self.config['client'].get('team_rocket_blastoff', False):
            find_team_rocket = True

        self.pokemon = Pokemon()
        offset = self.config['client'].get('screen_offset', 0)

        if self.flip_switch == 0:
            min_x = 370
            max_x = 710
            min_y = 1000
            max_y = 1440
            x_steps = 14
            y_steps = 14
            self.flip_switch = 1
        elif self.flip_switch == 1:
            min_x = 710
            max_x = 370
            min_y = 1440
            max_y = 1000
            x_steps = -14
            y_steps = -14
            self.flip_switch = 2
        elif self.flip_switch == 2:
            min_x = 370
            max_x = 710
            min_y = 1440
            max_y = 1000
            x_steps = 14
            y_steps = -14
            self.flip_switch = 3
        elif self.flip_switch == 3:
            min_x = 710
            max_x = 370
            min_y = 1000
            max_y = 1440
            x_steps = -14
            y_steps = 14
            self.flip_switch = 0

        r, g, b = 0, 0, 0  # to prevent errors
        # no ball, turn pokestop 50x
        logger.info(f'Ball and pgsharp status: {self.no_ball}, {self.pgsharpv2}')
        if self.no_ball and not self.pgsharpv2:

            while True:
                if self.turn_pokestop >= 50:
                    logger.info('Turned 50 pokestops, resuming normal operation...')
                    self.no_ball = False
                    self.turn_pokestop = 0
                    return 'no_pokemon'
                logger.info(f"Searching for pokestop to spin...{self.turn_pokestop}/50")
                im_rgb = await screen_cap(self.d)
                pokestop_found, x, y, r, g, b = find_pokestop(im_rgb, min_x, max_x, x_steps, min_y, max_y, y_steps,
                                                              self.bag_full, find_team_rocket=find_team_rocket)
                if pokestop_found:
                    delay_time = self.config['client'].get('delay', 1.5)
                    await tap_screen(self.p, x, y, delay_time)
                    im_rgb = await screen_cap(self.d)
                    pokestop_status = is_pokestop_page(im_rgb)
                    if pokestop_status:
                        self.turn_pokestop += 1
                        self.trivial_page_count = 0
                        logger.info('Pokestop found: {}'.format(pokestop_status))
                        if pokestop_status in ['pokestop_spinnable', 'pokestop_invaded']:
                            self.trivial_page_count = 0
                            if self.track_bag_time == 0:
                                if self.config['spin_pokestop']:
                                    self.bag_full = await spin_pokestop(self.p, self.d)

                                team_go_rocket = is_team_selection(im_rgb)
                                if not team_go_rocket:
                                    # tap more buttons after spinning
                                    if pokestop_status == 'pokestop_invaded':
                                        while True:
                                            im_rgb = await screen_cap(self.d)
                                            result = await self.teamrocket(im_rgb)
                                            if result:
                                                return result
                                            if is_home_page(im_rgb):
                                                self.trivial_page_count = 0
                                                break
                                            else:
                                                # press until it's home page
                                                # await close_team_rocket(self.p)
                                                await tap_close_btn(self.p)
                                                # self.d.press("back")
                                                await asyncio.sleep(0.2)
                                        self.no_action_count = 0
                                        # if self.pgsharpv2:
                                        self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                                        await asyncio.sleep(0.5)  # wait a while after spin
                                continue
                                # return 'on_pokestop'

                        im_rgb = await screen_cap(self.d)
                        team_go_rocket = is_team_selection(im_rgb)
                        if not team_go_rocket:
                            logger.warning('Still on pokestop cooldown.')
                            if self.pgsharpv2:
                                self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                            self.d.press("back")
                            while True:
                                im_rgb = await screen_cap(self.d)
                                if is_home_page(im_rgb):
                                    self.trivial_page_count = 0
                                    break
                                else:
                                    await tap_close_btn(self.p)
                                    await asyncio.sleep(0.5)
                            self.no_action_count = 0
                            return 'on_pokestop'
                        else:
                            break
                    elif self.config['client'].get('instant_spin'):
                        self.turn_pokestop += 1
                        self.trivial_page_count = 0
                        logger.info('Instant Spin enabled, assuming Pokestop spinned...')
                        return 'on_pokestop'
                    else:
                        break

                else:
                    return 'no_pokestop'
            return 'no_pokestop'
        elif not self.pgsharpv2:
            # This makes the program flip direction of search so that it won't always search in one direction
            # This is to try to avoid keep tapping the same thing over and over again (Example pokestop/gyms)

            im_rgb = await screen_cap(self.d)
            if not self.config['spin_pokestop']:
                self.bag_full = True  # If user choose not to spin pokestop (Maybe he wants to clear egg bag)
            pokefound, x, y, r, g, b = find_object_to_tap(im_rgb, min_x, max_x, x_steps, min_y, max_y, y_steps,
                                                          self.bag_full, self.missedcolors, skip_pokestop=self.config['client'].get('auto_goplus', False))
            if pokefound:
                logger.debug("Tap location ({}, {}) | RGB ({}, {}, {}), ".format(x, y, r, g, b))
                logger.info("Tapping...")

                # Let's double confirm no egg before tapping
                if is_egg_hatched_oh(im_rgb):
                    self.trivial_page_count = 0
                    await asyncio.sleep(2.0)
                    logger.info('Egg Hatched!')
                    await tap_screen(self.p, 540, 1190, 0.5)
                    if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                        await asyncio.sleep(5.0)
                    im_rgb = await screen_cap(self.d)
                    if is_mon_details_page(im_rgb):
                        await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    # put on a new egg
                    im_rgb = await screen_cap(self.d)
                    if is_egg_hatched_page(im_rgb):
                        await select_egg(self.p)
                        await tap_incubate(self.p)
                    self.no_action_count = 0
                    return 'on_egg'
            else:
                self.no_action_count += 1
                return 'not found'  # return if nothing is found

            delay_time = self.config['client'].get('delay', 1.5)

            await tap_screen(self.p, x, y, delay_time)
        else:
            # PGSharp v2
            current_count = await pgsharp_client.get_nearby_count(self.p, self.d)
            if current_count != pgsharp_client.nearby_count:
                pgsharp_client.nearby_count = current_count
                #pgsharp_client.current_index = 0
            if pgsharp_client.current_index >= pgsharp_client.nearby_count:
                pgsharp_client.current_index = 0
            if pgsharp_client.nearby_count == 0:
                if not await pgsharp_client.wait_for_spawn(self.p, self.d):
                    logger.info('No nearby Pokemon found...')
                    self.no_action_count += 1
                    return 'not found'  # return if nothing is found
            # all okay, let's move
            try:
                x, y = await pgsharp_client.get_item_position(self.d(resourceId='me.underw.hp:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo')[pgsharp_client.current_index].info, self.config.get('resize', False))
            except:
                return 'on_error'
            logger.info("Moving to next Pokemon...")
            await tap_screen(self.p, x, y, 4)
            # await asyncio.sleep(3.5)
            # test new method
            logger.info("Tapping...")
            for y in range(1260, 1180, -10):
                await tap_screen(self.p, 540, y, 0.25)

                im_rgb = await screen_cap(self.d)
                if not is_home_page(im_rgb):
                    try:
                        if await pgsharp_client.pokemon_encountered(self.p, self.d, self.pokemon):
                            pgsharp_client.current_index += 1
                            # if not self.config['client'].get('transfer_on_catch',False):
                            counter = 0
                            while Unknown.is_(self.pokemon.name):
                                if counter >= 3:
                                    break
                                im_rgb = await screen_cap(self.d)
                                self.pokemon.update_stats_from_catch_screen(im_rgb)
                                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                                    await asyncio.sleep(1)
                                    self.d.press("back")  # Flee
                                    self.no_action_count = 0
                                    return 'on_pokemon'
                                counter += 1
                                await asyncio.sleep(0.5)

                            pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                            if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                                if pokemon_caught != 'No Ball':
                                    self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)

                            if pokemon_caught == 'No Ball':
                                self.no_ball = True
                                if pgsharp_client.start_location:
                                    logger.info("Attempt to teleport to starting location...")
                                    await self.pgsharp_teleport_home()
                            elif self.player_level >= 30 and pgsharp_client:
                                await self.check_and_send(self.pokemon, pgsharp_client)
                            self.no_action_count = 0
                            # return 'on_pokemon'
                            await asyncio.sleep(1)
                            if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                                if pokemon_caught != 'No Ball':
                                    await fav_last_caught(self.p, self.d, self.pokemon)
                                    await asyncio.sleep(1)
                            # whatever the results, after caught search for pokestop, click and break

                            counter = 0
                            if self.config['spin_pokestop'] and not self.config['client'].get('auto_goplus', False):
                                while True:

                                    if counter >= 4:
                                        break
                                    counter += 1
                                    logger.info("Searching for pokestop to spin...")
                                    im_rgb = await screen_cap(self.d)
                                    pokestop_found, x, y, r, g, b = find_pokestop(im_rgb, min_x, max_x, x_steps, min_y, max_y, y_steps,
                                                                                  self.bag_full, find_team_rocket=find_team_rocket)
                                    if pokestop_found:
                                        delay_time = self.config['client'].get('delay', 1.5)

                                        await tap_screen(self.p, x, y, delay_time)
                                        im_rgb = await screen_cap(self.d)
                                        pokestop_status = is_pokestop_page(im_rgb)
                                        if pokestop_status:
                                            self.trivial_page_count = 0
                                            logger.info('Pokestop found: {}'.format(pokestop_status))
                                            if pokestop_status in ['pokestop_spinnable', 'pokestop_invaded']:
                                                self.trivial_page_count = 0
                                                if self.track_bag_time == 0:
                                                    self.bag_full = await spin_pokestop(self.p, self.d)

                                                    team_go_rocket = is_team_selection(im_rgb)
                                                    if not team_go_rocket:
                                                        # tap more buttons after spinning
                                                        if pokestop_status == 'pokestop_invaded':
                                                            while True:
                                                                im_rgb = await screen_cap(self.d)
                                                                result = await self.teamrocket(im_rgb)
                                                                if result:
                                                                    return result
                                                                if is_home_page(im_rgb):
                                                                    self.trivial_page_count = 0
                                                                    break
                                                                else:
                                                                    # press until it's home page
                                                                    # await close_team_rocket(self.p)
                                                                    await tap_close_btn(self.p)
                                                                    # self.d.press("back")
                                                                    await asyncio.sleep(0.2)
                                                            self.no_action_count = 0
                                                            # if self.pgsharpv2:
                                                            self.d(packageName='com.nianticlabs.pokemongo').swipe(
                                                                "left", steps=50)
                                                            await asyncio.sleep(0.5)  # wait a while after spin
                                                continue
                                                # return 'on_pokestop'

                                            im_rgb = await screen_cap(self.d)
                                            team_go_rocket = is_team_selection(im_rgb)
                                            if not team_go_rocket:
                                                logger.warning('Still on pokestop cooldown.')
                                                if self.pgsharpv2:
                                                    self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                                                self.d.press("back")
                                                while True:
                                                    im_rgb = await screen_cap(self.d)
                                                    if is_home_page(im_rgb):
                                                        self.trivial_page_count = 0
                                                        break
                                                    else:
                                                        await tap_close_btn(self.p)
                                                        await asyncio.sleep(0.5)
                                                self.no_action_count = 0
                                                break
                                                # return 'on_pokestop'
                                            else:
                                                break
                                        gym_status = is_gym_page(im_rgb)
                                        if gym_status:
                                            logger.info('Gym found: {}'.format(gym_status))
                                            await tap_screen(self.p, 920, 1790)
                                            self.bag_full = await spin_pokestop(self.p, self.d)
                                            im_rgb = await screen_cap(self.d)
                                            if is_gym_badge(im_rgb):
                                                await tap_close_btn(self.p)
                                                await asyncio.sleep(0.5)
                                            await tap_close_btn(self.p)
                                            return 'on_gym'
                                        else:
                                            break
                                    else:
                                        return 'no_pokestop'
                                return 'pokemon_caught'
                            else:
                                return 'pokemon_caught'
                    except Exception as e:
                        # Change exception to error for depolyment (so client wont see chuck of erros during exit)
                        logger.exception("Encounter unexpected error: {}".format(e))
                        cleanup()
                    break
            pgsharp_client.current_index += 1

        self.pokemon.screen_x, self.pokemon.screen_y = x, y
        if mad_client:
            await mad_client.pokemon_encountered(self.p, self.d, self.pokemon)

        if self.config['client'].get('client', '').lower() in ['hal', 'pokemod']:
            #logger.info('Getting information...')
            self.pokemon.update_stats_from_pokemod_toast(self.p, self.d)
            # start to catch immediately if found IV (Don't use name)
            if Unknown.is_not(self.pokemon.atk_iv) or \
                    Unknown.is_not(self.pokemon.def_iv) or \
                    Unknown.is_not(self.pokemon.sta_iv):
                if Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                    im_rgb = await screen_cap(self.d)
                    save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                    self.pokemon.update_stats_from_catch_screen(im_rgb)

                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                    await asyncio.sleep(1)
                    self.d.press("back")  # Flee
                    self.no_action_count = 0
                    return 'on_pokemon'

                if self.pokemon.shiny:
                    save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))

                if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                    report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)

                if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid'] and not self.pgsharpv2:
                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, track_r=r, track_g=g, track_b=b, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                else:
                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                    if pokemon_caught != 'No Ball':
                        self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    if pokemon_caught == 'No Ball':
                        self.no_ball = True
                    elif self.player_level >= 30 and pgsharp_client:
                        await self.check_and_send(self.pokemon, pgsharp_client)

                if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                    if pokemon_caught != 'No Ball':
                        await asyncio.sleep(1)
                        await fav_last_caught(self.p, self.d, self.pokemon)
                        await asyncio.sleep(1)
                    if pokemon_caught == 'No Ball':
                        self.no_ball = True
                    elif self.player_level >= 30 and pgsharp_client:
                        await self.check_and_send(self.pokemon, pgsharp_client)
                self.no_action_count = 0
                return 'on_pokemon'

        im_rgb = await screen_cap(self.d)
        save_screenshot(im_rgb, sub_dir='start', save=self.config['screenshot'].get('start'))

        # For those that manually spin pokestop, let's check for them and spin first to end their poor waiting time
        if not self.config['client'].get('instant_spin', False) or self.config['client'].get('client', '').lower() in ['polygon', 'polygon paid']:
            pokestop_status = is_pokestop_page(im_rgb)
            if pokestop_status:
                self.trivial_page_count = 0
                logger.info('Pokestop found: {}'.format(pokestop_status))
                if pokestop_status in ['pokestop_spinnable', 'pokestop_invaded']:
                    self.trivial_page_count = 0
                    if self.track_bag_time == 0:
                        if self.config['spin_pokestop']:
                            self.bag_full = await spin_pokestop(self.p, self.d)

                        team_go_rocket = is_team_selection(im_rgb)
                        if not team_go_rocket:
                            # tap more buttons after spinning
                            if pokestop_status == 'pokestop_invaded':
                                while True:
                                    im_rgb = await screen_cap(self.d)
                                    result = await self.teamrocket(im_rgb)
                                    if result:
                                        return result
                                    if is_home_page(im_rgb):
                                        self.trivial_page_count = 0
                                        break
                                    else:
                                        # press until it's home page
                                        # await close_team_rocket(self.p)
                                        await tap_close_btn(self.p)
                                        # self.d.press("back")
                                        await asyncio.sleep(0.2)
                                self.no_action_count = 0
                    if self.pgsharpv2:
                        self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                    return 'on_pokestop'

                im_rgb = await screen_cap(self.d)
                team_go_rocket = is_team_selection(im_rgb)
                if not team_go_rocket:
                    logger.warning('Still on pokestop cooldown.')
                    if self.pgsharpv2:
                        self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                    self.d.press("back")
                    # while True:
                    #    im_rgb = await screen_cap(self.d)
                    #    if is_home_page(im_rgb):
                    #        self.trivial_page_count = 0
                    #        break
                    #    else:
                    #        await tap_close_btn(self.p)
                    #        await asyncio.sleep(0.5)
                    self.no_action_count = 0
                    return 'on_pokestop'

        if not self.config['client'].get('skip_encounter_intro'):
            await asyncio.sleep(1)
            im_rgb = await screen_cap(self.d)

        if 'none' in self.config['client'].get('client', '').lower():
            # Handle None so that it will be faster for GPS Joystick Only users
            if not is_catch_pokemon_page(im_rgb, is_shadow=True, map_check=True):
                # if is_home_page(im_rgb):
                #    pokestopfound = False

                #    if (28 <= r <= 32) and (187 <= g <= 191) and (254 <= b <= 255):
                #        pokestopfound = True
                #    if (28 <= r <= 32) and (145 <= g <= 191) and (254 <= b <= 255):
                #        pokestopfound = True
                #    if (80 <= r <= 100) and (254 <= g <= 255) and (254 <= b <= 255):
                #        pokestopfound = True
                #    if (30 <= r <= 50) and (100 <= g <= 120) and (254 <= b <= 255):
                #        pokestopfound = True

                # add missed colors, cap at 20, pokestop let it pass
                #    if not pokestopfound:
                #        if len(self.missedcolors) > self.max_color_list:
                #            self.missedcolors.pop(0)
                #        missed_colors = [r,g,b]
                #        self.missedcolors.append(missed_colors)
                #    return 'on_home_page'

                if is_join_raid_battle(im_rgb):
                    self.trivial_page_count = 0
                    if len(self.missedcolors) > self.max_color_list:
                        self.missedcolors.pop(0)
                    missed_colors = [r, g, b]
                    self.missedcolors.append(missed_colors)
                    await tap_close_btn(self.p)
                    await tap_close_btn(self.p)
                    if self.pgsharpv2:
                        self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                    return 'on_gym'

                if is_gym_page(im_rgb):
                    self.trivial_page_count = 0
                    self.count_gym_count += 1
                    if self.count_gym_count >= 10:
                        # reset to zero
                        self.count_gym_count = 0
                    if is_gym_page(im_rgb) == 'gym_deployable':
                        logger.info("Deploying to gym")
                        await tap_gym_btn(self.p)
                        await tap_screen(self.p, 190, 1040)
                        await tap_remove_quest_ok_btn(self.p)
                    self.d.press("back")
                    # while True:
                    #    im_rgb = await screen_cap(self.d)
                    #    if is_home_page(im_rgb) or i == 4:
                    #        self.trivial_page_count = 0
                    #        break
                    #    else:
                    # send the magic button
                    #        self.d.press("back") # Back button more effective, let's deal with unable to detect home page later
                    # await tap_close_btn(self.p)
                    #        i += 1
                    #        await asyncio.sleep(1)
                    # return 'on_gym'

        # bring this infront to try prevent bot hang at mon details page
        if is_mon_details_page(im_rgb):
            self.trivial_page_count = 0
            await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
            # put on a new egg
            im_rgb = await screen_cap(self.d)
            if is_egg_hatched_page(im_rgb):
                await select_egg(self.p)
                await tap_incubate(self.p)
            self.no_action_count = 0
            return 'on_pokemon'

        if not config['client'].get('client', '').lower() in ['none'] or not self.config['client'].get('client', '').lower() in ['hal', 'pokemod'] or not self.pgsharpv2:
            self.pokemon.update_stats_from_pokemod(im_rgb)

            # start to catch immediately if found IV (Don't use name)
            if Unknown.is_not(self.pokemon.atk_iv) or \
                    Unknown.is_not(self.pokemon.def_iv) or \
                    Unknown.is_not(self.pokemon.sta_iv):
                if Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                    im_rgb = await screen_cap(self.d)
                    save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                    self.pokemon.update_stats_from_catch_screen(im_rgb)

                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                    await asyncio.sleep(1)
                    self.d.press("back")  # Flee
                    self.no_action_count = 0
                    return 'on_pokemon'

                if self.pokemon.shiny:
                    save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))

                if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                    report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)

                if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid'] and not self.pgsharpv2:
                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, track_r=r, track_g=g, track_b=b, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                else:
                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                    if pokemon_caught != 'No Ball':
                        self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    if pokemon_caught == 'No Ball':
                        self.no_ball = True
                    elif self.player_level >= 30 and pgsharp_client:
                        await self.check_and_send(self.pokemon, pgsharp_client)
                if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                    if pokemon_caught != 'No Ball':
                        await asyncio.sleep(1)
                        await fav_last_caught(self.p, self.d, self.pokemon)
                        await asyncio.sleep(1)
                    if pokemon_caught == 'No Ball':
                        self.no_ball = True
                    elif self.player_level >= 30 and pgsharp_client:
                        await self.check_and_send(self.pokemon, pgsharp_client)
                self.no_action_count = 0
                return 'on_pokemon'

        if is_catch_pokemon_page(im_rgb, is_shadow=False, map_check=True):
            # transfer_on_catch is set to true, use the faster is_catch_pokemon_page instead
            # skip shiny too since transfer_on_catch will handle it
            self.pokemon.update_stats_from_catch_screen(im_rgb)
            if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                await asyncio.sleep(1)
                self.d.press("back")  # Flee
                self.no_action_count = 0
                return 'on_pokemon'

            if (Unknown.is_not(self.pokemon.atk_iv) or
                    Unknown.is_not(self.pokemon.def_iv) or
                    Unknown.is_not(self.pokemon.sta_iv)) or \
                    (Unknown.is_not(self.pokemon.name) and
                     self.config['client'].get('client', '').lower() == 'none'):
                if self.pokemon.shiny:
                    save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))

                if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                    report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)

                if config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid'] and not self.pgsharpv2:
                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, track_r=r, track_g=g, track_b=b, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                else:
                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                    if pokemon_caught != 'No Ball':
                        await asyncio.sleep(1)
                        self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    if pokemon_caught == 'No Ball':
                        self.no_ball = True
                    elif self.player_level >= 30 and pgsharp_client:
                        await self.check_and_send(self.pokemon, pgsharp_client)
                if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                    if pokemon_caught != 'No Ball':
                        await asyncio.sleep(1)
                        await fav_last_caught(self.p, self.d, self.pokemon)
                        await asyncio.sleep(1)
                    if pokemon_caught == 'No Ball':
                        self.no_ball = True
                    elif self.player_level >= 30 and pgsharp_client:
                        await self.check_and_send(self.pokemon, pgsharp_client)
                self.no_action_count = 0
                return 'on_pokemon'

        if is_pokemon_full(im_rgb) and self.config.get('poke_management'):
            if self.config['poke_management'].get('enable_poke_management', False):
                self.trivial_page_count = 0
                await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                await clear_pokemon_inventory(self.p, self.d, pgsharp_client=pgsharp_client, mad_client=mad_client)
                self.no_action_count = 0
                return 'on_poke_management'

        if self.config['client'].get('instant_spin') and not self.bag_full:
            self.bag_full = is_bag_full(im_rgb)

        im_rgb = await screen_cap(self.d)
        if self.config['quest'].get('enable_check_quest', False):  # This has to be before checking home
            if has_completed_quest_on_map(im_rgb):
                logger.info("Checking and clearing quest....")
                await check_quest(self.d, self.p, self.pokemon, rab_runtime_status=rab_runtime_status)
                self.track_quest_time = int(time.time())

        if is_gym_page(im_rgb):
            self.trivial_page_count = 0
            self.count_gym_count += 1
            if self.count_gym_count >= 10:
                # reset to zero
                self.count_gym_count = 0
            if is_gym_page(im_rgb) == 'gym_deployable':
                logger.info("Deploying to gym")
                await tap_gym_btn(self.p)
                await tap_screen(self.p, 190, 1040)
                await tap_remove_quest_ok_btn(self.p)
            self.d.press("back")
            self.no_action_count = 0
            if self.pgsharpv2:
                self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
            return 'on_gym'

        if is_join_raid_battle(im_rgb):
            self.trivial_page_count = 0
            if len(self.missedcolors) > self.max_color_list:
                self.missedcolors.pop(0)
            #missed_colors = [r,g,b]
            # self.missedcolors.append(missed_colors)
            await tap_close_btn(self.p)
            await tap_close_btn(self.p)
            self.no_action_count = 0
            if self.pgsharpv2:
                self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
            return 'on_gym'

        # im_rgb = await screen_cap(self.d)
        if is_egg_hatched_oh(im_rgb):
            self.trivial_page_count = 0
            await asyncio.sleep(2.0)
            logger.info('Egg Hatched!')
            await tap_screen(self.p, 540, 1190, 0.5)
            if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                await asyncio.sleep(5.0)
            im_rgb = await screen_cap(self.d)
            if is_mon_details_page(im_rgb):
                await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
            # put on a new egg
            im_rgb = await screen_cap(self.d)
            if is_egg_hatched_page(im_rgb):
                await select_egg(self.p)
                await tap_incubate(self.p)
            return 'on_egg'

        # bring this infront to try prevent bot hang at mon details page
        if is_mon_details_page(im_rgb):
            self.trivial_page_count = 0
            await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
            # put on a new egg
            im_rgb = await screen_cap(self.d)
            if is_egg_hatched_page(im_rgb):
                await select_egg(self.p)
                await tap_incubate(self.p)
            self.no_action_count = 0
            return 'on_pokemon'

        if is_home_page(im_rgb):
            pokestopfound = False

            if not self.pgsharpv2:
                if (28 <= r <= 32) and (187 <= g <= 191) and (254 <= b <= 255):
                    pokestopfound = True
                if (28 <= r <= 32) and (145 <= g <= 191) and (254 <= b <= 255):
                    pokestopfound = True
                if (80 <= r <= 100) and (254 <= g <= 255) and (254 <= b <= 255):
                    pokestopfound = True
                if (30 <= r <= 50) and (100 <= g <= 120) and (254 <= b <= 255):
                    pokestopfound = True

                # add missed colors, cap at 20, pokestop let it pass
                if not pokestopfound:
                    if len(self.missedcolors) > self.max_color_list:
                        self.missedcolors.pop(0)
                    missed_colors = [r, g, b]
                    self.missedcolors.append(missed_colors)
                    self.no_action_count += 1
            else:
                self.no_action_count += 1
            if self.pgsharpv2:
                self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
            return 'on_home_page'

        pokestop_status = is_pokestop_page(im_rgb)
        if pokestop_status:
            self.trivial_page_count = 0
            if not self.config['client'].get('instant_spin'):
                if not self.config['spin_pokestop']:
                    await tap_close_btn(self.p)

                if pokestop_status in ['pokestop_spinned', 'pokestop_spinnable', 'pokestop_invaded']:
                    self.trivial_page_count = 0
                    if self.track_bag_time == 0:
                        if pokestop_status != 'pokestop_spinned':
                            await spin_pokestop(self.p, self.d)
                        im_rgb = await screen_cap(self.d)
                        self.bag_full = is_bag_full(im_rgb)
                        # tap more buttons after spinning
                        if pokestop_status == 'pokestop_invaded':
                            while True:
                                im_rgb = await screen_cap(self.d)
                                result = await self.teamrocket(im_rgb)
                                if result:
                                    return result
                                if is_home_page(im_rgb):
                                    self.trivial_page_count = 0
                                    break
                                else:
                                    # press until it's home page
                                    # await close_team_rocket(self.p)
                                    await tap_close_btn(self.p)
                                    await asyncio.sleep(0.5)
                        if self.pgsharpv2:
                            self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                        return 'on_pokestop'
                    if pokestop_status == 'pokestop_invaded':
                        # Close Pokestop
                        while True:
                            im_rgb = await screen_cap(self.d)
                            result = await self.teamrocket(im_rgb)
                            if result:
                                return result
                            if is_home_page(im_rgb):
                                self.trivial_page_count = 0
                                break
                            else:
                                # press until it's home page
                                # await close_team_rocket(self.p)
                                await tap_close_btn(self.p)
                                await asyncio.sleep(0.5)
                    # while True:
                    #    im_rgb = await screen_cap(self.d)
                    #    if is_home_page(im_rgb):
                    #        self.trivial_page_count = 0
                    #        break
                    #    else:
                            # press until it's home page
                            # await close_team_rocket(self.p)
                    #        await tap_close_btn(self.p)
                    #        await asyncio.sleep(0.5)
                    logger.warning('Still on pokestop cooldown.')
                    self.d.press("back")
                    if self.pgsharpv2:
                        self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                    return 'on_pokestop'

        result = await self.teamrocket(im_rgb)
        if result:
            return result

        # team go rocket blastoff v2, only check if this is enabled in option
        if self.config['client'].get('team_rocket_blastoff'):
            team_go_rocket = is_team_selection(im_rgb)
            if team_go_rocket:
                result = await fight_team_rocket(self.p, self.d, team_go_rocket)
                if result:
                    # catch shadow pokemon
                    self.pokemon.type = 'shadow'
                    im_rgb = await screen_cap(self.d)
                    self.pokemon.update_stats_from_pokemod(im_rgb)
                    if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                        await asyncio.sleep(1)
                        self.d.press("back")  # Flee
                        return 'on_pokemon'
                    if not self.pokemon.shiny or Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                        im_rgb = await screen_cap(self.d)
                        save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                        self.pokemon.update_stats_from_catch_screen(im_rgb)
                        if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                            await asyncio.sleep(1)
                            self.d.press("back")  # Flee
                            return 'on_pokemon'

                    if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                        report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)

                    if self.pokemon.shiny:
                        save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
                    if is_catch_pokemon_page(im_rgb, is_shadow=True):
                        pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, is_shadow=True, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                        if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)) and pokemon_caught != 'No Ball':
                            self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                        if pokemon_caught != 'No Ball':
                            await asyncio.sleep(1)
                            await fav_last_caught(self.p, self.d, self.pokemon)
                            await asyncio.sleep(1)

                if self.pgsharpv2:
                    self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)

                self.no_action_count = 0
                return 'on_team_rocket'

        if is_grunt_defeated_page(im_rgb):
            await tap_screen(self.p, 540, 1700, 1.0)
            self.pokemon.type = 'shadow'
            im_rgb = await screen_cap(self.d)
            self.pokemon.update_stats_from_pokemod(im_rgb)
            if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                await asyncio.sleep(1)
                self.d.press("back")  # Flee
                return 'on_pokemon'
            if not self.pokemon.shiny or Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                im_rgb = await screen_cap(self.d)
                save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                self.pokemon.update_stats_from_catch_screen(im_rgb)
                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                    await asyncio.sleep(1)
                    self.d.press("back")  # Flee
                    return 'on_pokemon'

            if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
            if self.pokemon.shiny:
                save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
            pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, is_shadow=True, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
            if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)) and pokemon_caught != 'No Ball':
                self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
            if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                if pokemon_caught != 'No Ball':
                    await asyncio.sleep(1)
                    await fav_last_caught(self.p, self.d, self.pokemon)
                    await asyncio.sleep(1)

            self.no_action_count = 0
            return 'on_shadow_pokemon'

        # Take another picture here because some page here might be triggered by the previous tappping and not correctly screen captured previously
        im_rgb = await screen_cap(self.d)

        if is_join_raid_battle(im_rgb):
            self.trivial_page_count = 0
            if len(self.missedcolors) > self.max_color_list:
                self.missedcolors.pop(0)
            missed_colors = [r, g, b]
            self.missedcolors.append(missed_colors)
            await tap_close_btn(self.p)
            await tap_close_btn(self.p)
            if self.pgsharpv2:
                self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
            return 'on_gym'

        if is_gym_page(im_rgb):
            self.trivial_page_count = 0
            self.count_gym_count += 1
            if self.count_gym_count >= 10:
                # reset to zero
                self.count_gym_count = 0
            if is_gym_page(im_rgb) == 'gym_deployable':
                logger.info("Deploying to gym")
                await tap_gym_btn(self.p)
                await tap_screen(self.p, 190, 1040)
                await tap_remove_quest_ok_btn(self.p)
            self.d.press("back")
            if self.pgsharpv2:
                self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
            return 'on_gym'

        # if self.config['client'].get('transfer_on_catch', False): # Some pokemon cannot be detected by is_catch_pokemon_page, this is here to catch all missied
        #    self.pokemon.update_stats_from_pokemod(im_rgb)
        #    if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
        #        await asyncio.sleep(1)
        #        await tap_exit_btn(self.p) # Flee
        #        return 'on_pokemon'
        #    save_screenshot(im_rgb, sub_dir='start', save=self.config['screenshot'].get('start'))
            # start to catch immediately if found IV (Don't use name)
        #    if Unknown.is_not(self.pokemon.atk_iv) or \
        #            Unknown.is_not(self.pokemon.def_iv) or \
        #            Unknown.is_not(self.pokemon.sta_iv):
        #        if not self.pokemon.shiny or Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
        #            im_rgb = await screen_cap(self.d)
        #            save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
        #            self.pokemon.update_stats_from_catch_screen(im_rgb)
        #            if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
        #                await asyncio.sleep(1)
        #                await tap_exit_btn(self.p) # Flee
        #                return 'on_pokemon'

        #        if self.pokemon.shiny:
        #            save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))

        #        pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon)
        #        if (pokemon_caught and not self.config['client'].get('transfer_on_catch',False)):
        #            self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
        #        return 'on_pokemon'

        # prevent bot from hang at this page
        text = extract_text_from_image(im_rgb)
        if any(x in text for x in ['component', 'collect', 'radar', 'assemble', 'equip']):
            save_screenshot(im_rgb, sub_dir='rocket', save=False)
            # collect i/6 component
            await tap_collect_component(self.p)
            logger.info('Collect component after catching shadow pokemon.')

        # collect 6/6 components, and combine components
        if any(x in text for x in ['enough', 'combine', 'assembled', 'team go rocket hideouts']):
            await asyncio.sleep(1.5)
            await tap_equip_radar(self.p)
            logger.info('Combine radar.')

        if is_incubate_page(im_rgb):
            self.trivial_page_count = 0
            await tap_incubate(self.p)
            return 'incubate_new_egg'

        if is_incubate_page2(im_rgb):
            self.trivial_page_count = 0
            await tap_close_btn(self.p)
            await tap_close_btn(self.p)
            return 'on_pokemon'

        if is_warning_page(im_rgb):
            self.trivial_page_count = 0
            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
            return 'on_warning'

        if is_main_menu_page(im_rgb) or is_shop_page(im_rgb) or is_nearby_page(im_rgb) or is_incense(im_rgb):
            self.trivial_page_count = 0
            await tap_close_btn(self.p)
            self.no_action_count += 1
            return 'on_pokemon'

        if is_mon_details_page(im_rgb):
            self.trivial_page_count = 0
            await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
            # put on a new egg
            im_rgb = await screen_cap(self.d)
            if is_egg_hatched_page(im_rgb):
                await select_egg(self.p)
                await tap_incubate(self.p)
            return 'on_pokemon'

        if is_mon_caught_page(im_rgb):
            self.trivial_page_count = 0
            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
            await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
            return 'on_pokemon'

        if is_power_up_page(im_rgb):
            self.trivial_page_count = 0
            self.d.press("back")
            self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
            return 'on_pokemon'

        if is_error_page(im_rgb):
            self.trivial_page_count = 0
            self.d.press("back")
            return 'on_error'

        # Catch Pokemon <- why this is here? when appeared?
        # im_rgb = await screen_cap(self.d)
        # if is_catch_pokemon_page(im_rgb):
        #    self.trivial_page_count = 0
        #    if self.config['client'].get('encounter_iv', False):
        #        self.pokemon.update_stats_from_pokemod(im_rgb)
        #        im_rgb = await screen_cap(self.d)
        #        save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
        #    self.pokemon.update_stats_from_catch_screen(im_rgb)

        #    if self.pokemon.shiny:
        #        save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))

        #    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon)
        #    if pokemon_caught and not self.config['client'].get('transfer_on_catch',False):
        #        self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
        #    return 'on_pokemon'

        # unknown error handling
        # for any new pages that are not handled, take a screenshot
        self.trivial_page_count += 1
        self.no_action_count += 1

        return 'on_world'

    async def check_and_send(self, pokemon, pgsharp_client=None):
        if pokemon.iv == 100:
            try:
                if pgsharp_client:
                    pokemon.latitude, pokemon.longitude = await pgsharp_client.get_location(self.p, self.d)
                text = "{} {} CP{} {}/{}/{} level{} {},{}".format(pokemon.name, pokemon.gender, pokemon.cp,
                                                                  pokemon.atk_iv, pokemon.def_iv, pokemon.sta_iv, pokemon.level, pokemon.latitude, pokemon.longitude)
                send_to_telegram(text, cid_pool='-1001469656053')
                return True
            except:
                return
        elif pokemon.pvp_info:
            if (pokemon.pvp_info['GL'].get('rating', 0 > 99.6) and pokemon.pvp_info['GL'].get('cp', 0 > 1400)) or (pokemon.pvp_info['UL'].get('rating', 0 > 99.6) and pokemon.pvp_info['UL'].get('cp', 0 > 2400)):
                pass
        return False

    async def pgsharp_teleport_home(self):
        global pgsharp_client
        offset = self.config['client'].get('screen_offset', 0)

        if self.config['client'].get('auto_goplus', False):

            logger.info("Checking Go Plus status...")
            counter = 0
            while True:
                im_rgb = await screen_cap(self.d)
                if counter >= 3:
                    logger.info("Unable to disconnect, will continue to teleport...")
                    break
                if not is_plus_disconnected(im_rgb, offset):
                    logger.info("Go Plus is connected, attempt to disconnect now....")
                    await tap_screen(self.p, 990, 450, 1.0)
                    logger.info("Please wait... Go Plus disconnecting...")
                    await asyncio.sleep(7.0)
                    counter += 1
                else:
                    logger.info("Go Plus disconnectd!")
                    break

        cur_lat, cur_lon = await pgsharp_client.get_location(self.p, self.d)

        cd_total_sec = calculate_cooldown(cur_lat,
                                          cur_lon,
                                          pgsharp_client.start_location[0], pgsharp_client.start_location[1])
        await pgsharp_client.teleport(self.p, self.d, pgsharp_client.start_location[0], pgsharp_client.start_location[1])
        logger.info('Pausing for {:.2f} mins before resuming from starting location...'.format(cd_total_sec / 60))
        await asyncio.sleep(cd_total_sec)
        logger.info('Resuming...')

        if self.config['client'].get('auto_goplus', False):
            logger.info("Checking Go Plus status...")
            counter = 0
            while True:
                im_rgb = await screen_cap(self.d)
                if counter >= 3:
                    logger.info("Unable to connect...")
                    break
                if is_plus_disconnected(im_rgb, offset):
                    logger.info("Go Plus is disconnected, attempt to connect now....")
                    await tap_screen(self.p, 990, 450, 1.0)
                    logger.info("Please wait... Go Plus connecting...")
                    await asyncio.sleep(7.0)
                    counter += 1
                else:
                    logger.info("Go Plus connected!")
                    break

    async def teamrocket(self, im_rgb):
        # team go rocket, keep this, non team rocket blastoff will still see this
        team_go_rocket = is_team_rocket_page(im_rgb)
        if team_go_rocket:
            self.trivial_page_count = 0
            if team_go_rocket == 'rocket_collect':
                await tap_screen(self.p, 540, 1715, 1.0)
                return 'on_team_rocket'
            if team_go_rocket == 'rocket_equip':
                await tap_screen(self.p, 540, 1540, 3.0)
                return 'on_team_rocket'
            if team_go_rocket == 'rocket_???':
                # tap a few more time to ensure it's at the real battle page
                await tap_screen(self.p, 540, 1000, 0.5)
                await tap_screen(self.p, 540, 1000, 0.5)
                await tap_screen(self.p, 540, 1000, 0.5)
                await tap_screen(self.p, 540, 1000, 0.5)

            if not self.config['client'].get('team_rocket_blastoff'):
                while True:
                    im_rgb = await screen_cap(self.d)
                    if is_home_page(im_rgb):
                        self.trivial_page_count = 0
                        break
                    else:
                        # press until it's home page
                        # await close_team_rocket(self.p)
                        await tap_close_btn(self.p)
                        await asyncio.sleep(0.5)
            else:
                result = await fight_team_rocket(self.p, self.d, team_go_rocket)
                if result:
                    # catch shadow pokemon
                    self.pokemon.type = 'shadow'

                    if self.config['client'].get('client').lower() == 'pgsharp paid':
                        await pgsharp_client.pokemon_encountered(self.p, self.d, self.pokemon)
                        # await asyncio.sleep(2.5)
                        im_rgb = await screen_cap(self.d)
                        self.pokemon.update_stats_from_catch_screen(im_rgb)

                    else:
                        im_rgb = await screen_cap(self.d)
                        self.pokemon.update_stats_from_pokemod(im_rgb)
                    if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                        await asyncio.sleep(1)
                        self.d.press("back")  # Flee
                        return 'on_pokemon'
                    if not self.pokemon.shiny or Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                        im_rgb = await screen_cap(self.d)
                        save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                        self.pokemon.update_stats_from_catch_screen(im_rgb)
                        if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                            await asyncio.sleep(1)
                            self.d.press("back")  # Flee
                            return 'on_pokemon'

                    if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                        report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)

                    if self.pokemon.shiny:
                        save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
                    if is_catch_pokemon_page(im_rgb, is_shadow=True):
                        pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, is_shadow=True, rab_runtime_status=rab_runtime_status, pgsharp_client=pgsharp_client, mad_client=mad_client, device_id=self.device_id)
                        if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)) and pokemon_caught != 'No Ball':
                            self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                        if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                            if pokemon_caught != 'No Ball':
                                await asyncio.sleep(1)
                                await fav_last_caught(self.p, self.d, self.pokemon)
                                await asyncio.sleep(1)
                    if self.config['client'].get('client').lower() == 'pgsharp paid':
                        await asyncio.sleep(4)
                        # prevent bot from hang at this page
                        im_rgb = await screen_cap(self.d)
                        text = extract_text_from_image(im_rgb)
                        if any(x in text for x in ['component', 'collect', 'radar', 'assemble', 'equip']):
                            save_screenshot(im_rgb, sub_dir='rocket', save=False)
                            # collect i/6 component
                            await tap_collect_component(self.p)
                            logger.info('Collect component after catching shadow pokemon.')

                        # collect 6/6 components, and combine components
                        if any(x in text for x in ['enough', 'combine', 'assembled', 'team go rocket hideouts']):
                            await asyncio.sleep(1.5)
                            await tap_equip_radar(self.p)
                            logger.info('Combine radar.')

            if self.pgsharpv2:
                self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
            return 'on_team_rocket'
        return False

    async def check_pokemon_in_view(self):
        pass

    async def check_pokestop_in_view(self):
        pass

    async def snipe(self):
        global last_active_location
        global spawns_to_snipe
        global localnetwork
        global rab_runtime_status
        global pgsharp_client
        global mad_client
        global snipe_count

        offset = self.config['client'].get('screen_offset', 0)

        if len(spawns_to_snipe) > 0:
            current_check = spawns_to_snipe.pop()
            # discharge anything that has past 2 mins
            if time.time() - current_check['reported_time'] > 120:
                return False
            if self.config['client'].get('auto_goplus', False):

                logger.info("Checking Go Plus status...")
                counter = 0
                while True:
                    im_rgb = await screen_cap(self.d)
                    if counter >= 3:
                        logger.info("Unable to disconnect, cancelling snipping...")
                        return False
                    if not is_plus_disconnected(im_rgb, offset):
                        logger.info("Go Plus is connected, attempt to disconnect now....")
                        await tap_screen(self.p, 990, 450, 1.0)
                        logger.info("Please wait... Go Plus disconnecting...")
                        await asyncio.sleep(7.0)
                        counter += 1
                    else:
                        logger.info("Go Plus disconnectd!")
                        break

            logger.info('Teleporting to Snipe...')
            await self.p.goto_location(current_check['latitude'], current_check['longitude'], 1)

            # adjust based on the spawns left
            timeout = 60
            # if len(spawns_to_snipe) <= 8:
            #    timeout = 60
            # elif len(spawns_to_snipe) <= 20:
            #    timeout = 45
            # else:
            #    timeout = 30
            pokemon_tapped = await load_tap_pokemon(self.p, self.d, self.pokemon, current_check, timeout=timeout, config=self.config, pgsharp_client=pgsharp_client, mad_client=mad_client)

            if pokemon_tapped:
                self.pokemon = pokemon_tapped
            else:
                await asyncio.sleep(1.0)
                await tap_screen(self.p, 540, 1230, 1.0)
                await asyncio.sleep(1.0)
                await tap_screen(self.p, 540, 1240, 1.0)
                im_rgb = await screen_cap(self.d)
                self.pokemon.update_stats_from_pokemod(im_rgb)

            if (self.pokemon.name == current_check['name']) or \
                    (self.pokemon.iv == current_check['iv']) or \
                    (self.pokemon.cp == current_check['cp']):
                logger.info('Tapped {} (IV{} | CP{} | LVL{}).'
                            .format(self.pokemon.name, self.pokemon.iv, self.pokemon.cp, self.pokemon.level))

            if not self.config['client'].get('skip_encounter_intro'):
                await asyncio.sleep(3.0)
            im_rgb = await screen_cap(self.d)

            if is_catch_pokemon_page(im_rgb):
                self.trivial_page_count = 0
                if self.config['client'].get('encounter_iv', False):
                    self.pokemon.update_stats_from_pokemod(im_rgb)
                if Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                    im_rgb = await screen_cap(self.d)
                    save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                    self.pokemon.update_stats_from_catch_screen(im_rgb)

                if current_check.get('shiny_check', False):
                    if not self.pokemon.shiny:
                        # Not correct poke, for now just teleport back
                        logger.info('Incorrect Pokemon, restarting route...')
                        await asyncio.sleep(1)
                        self.d.press("back")  # Flee
                        cd_total_sec = 1
                        # cd_total_sec = calculate_cooldown(last_active_location.get('latitude', 0),
                        #                                  last_active_location.get('longitude', 0),
                        #                                  self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1])
                        await self.p.goto_location(self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1], 1)
                        logger.info('Pausing for {:.2f} mins before restarting route...'.format(cd_total_sec / 60))
                        await asyncio.sleep(cd_total_sec)
                        logger.info('Resuming route...')
                        await self.p.start_route(self.config['snipe']['default_route_name'])
                        if self.config['client'].get('auto_goplus', False):
                            logger.info("Checking Go Plus status...")
                            counter = 0
                            while True:
                                im_rgb = await screen_cap(self.d)
                                if counter >= 3:
                                    logger.info("Unable to connect...")
                                    break
                                if is_plus_disconnected(im_rgb, offset):
                                    logger.info("Go Plus is disconnected, attempt to connect now....")
                                    await tap_screen(self.p, 990, 450, 1.0)
                                    logger.info("Please wait... Go Plus connecting...")
                                    await asyncio.sleep(7.0)
                                    counter += 1
                                else:
                                    logger.info("Go Plus connectd!")
                                    break
                        return False

                elif self.pokemon.cp != current_check['cp']:
                    # Not correct poke, for now just teleport back
                    logger.info('Incorrect Pokemon, restarting route...')
                    await asyncio.sleep(1)
                    self.d.press("back")  # Flee
                    cd_total_sec = 1
                    # cd_total_sec = calculate_cooldown(last_active_location.get('latitude', 0),
                    #                                  last_active_location.get('longitude', 0),
                    #                                  self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1])
                    await self.p.goto_location(self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1], 1)
                    logger.info('Pausing for {:.2f} mins before restarting route...'.format(cd_total_sec / 60))
                    await asyncio.sleep(cd_total_sec)
                    logger.info('Resuming route...')
                    await self.p.start_route(self.config['snipe']['default_route_name'])
                    if self.config['client'].get('auto_goplus', False):
                        logger.info("Checking Go Plus status...")
                        counter = 0
                        while True:
                            im_rgb = await screen_cap(self.d)
                            if counter >= 3:
                                logger.info("Unable to connect...")
                                break
                            if is_plus_disconnected(im_rgb, offset):
                                logger.info("Go Plus is disconnected, attempt to connect now....")
                                await tap_screen(self.p, 990, 450, 1.0)
                                logger.info("Please wait... Go Plus connecting...")
                                await asyncio.sleep(7.0)
                                counter += 1
                            else:
                                logger.info("Go Plus connectd!")
                                break
                    return False

                pokemon_caught = False
                if self.player_level >= 30 and pgsharp_client:
                    await self.check_and_send(self.pokemon, pgsharp_client)
                cd_total_sec = calculate_cooldown(last_active_location.get('latitude', 0),
                                                  last_active_location.get('longitude', 0),
                                                  current_check['latitude'], current_check['longitude'])
                if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                    report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)

                if self.config['snipe'].get('auto_catch', False):
                    if cd_total_sec >= 0:
                        logger.info('Pausing for {:.2f} mins before catching...'.format(cd_total_sec / 60))
                        await asyncio.sleep(cd_total_sec)

                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                    self.no_action_count = 0

                else:
                    logger.critical('Pokemon for Snipe Found! CD TIME: {:.2f} min.'.format(cd_total_sec / 60))
                    await asyncio.sleep(cd_total_sec)
                    logger.critical('Pokemon for Snipe Found! YOU CAN CATCH NOW')
                    # beepy.beep(sound=1)
                    print('\a')  # This is suppose to play a beep sound....
                    input("Enter sure it's at main map before press Enter to continue...")
                    pokemon_caught = True

                if pokemon_caught and not self.config['client'].get('transfer_on_catch', False):
                    self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    last_active_location['latitude'] = current_check['latitude']
                    last_active_location['longitude'] = current_check['longitude']
                    last_active_location['time'] = int(time.time())
                    snipe_count[current_check['name'].lower()] = snipe_count.get(current_check['name'].lower(), 0) + 1
                elif pokemon_caught and self.config['client'].get('transfer_on_catch', False):
                    # even if fled with still need countdown
                    if pokemon_caught != 'No Ball':
                        await asyncio.sleep(1)
                        await fav_last_caught(self.p, self.d, self.pokemon)
                        await asyncio.sleep(1)
                    last_active_location['latitude'] = current_check['latitude']
                    last_active_location['longitude'] = current_check['longitude']
                    last_active_location['time'] = int(time.time())
                    snipe_count[current_check['name'].lower()] = snipe_count.get(current_check['name'].lower(), 0) + 1

                await asyncio.sleep(1)
                if not pokemon_caught:
                    self.d.press("back")  # Flee
                    cd_total_sec = 1
                else:
                    cd_total_sec = calculate_cooldown(current_check['latitude'],
                                                      current_check['longitude'],
                                                      self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1])
                if len(spawns_to_snipe) == 0:
                    await self.p.goto_location(self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1], 1)
                    logger.info('Pausing for {:.2f} mins before restarting route...'.format(cd_total_sec / 60))
                    await asyncio.sleep(cd_total_sec)
                    logger.info('Resuming route...')
                    await self.p.start_route(self.config['snipe']['default_route_name'])
                if self.config['client'].get('auto_goplus', False):
                    logger.info("Checking Go Plus status...")
                    counter = 0
                    while True:
                        im_rgb = await screen_cap(self.d)
                        if counter >= 3:
                            logger.info("Unable to connect...")
                            break
                        if is_plus_disconnected(im_rgb, offset):
                            logger.info("Go Plus is disconnected, attempt to connect now....")
                            await tap_screen(self.p, 990, 450, 1.0)
                            logger.info("Please wait... Go Plus connecting...")
                            await asyncio.sleep(7.0)
                            counter += 1
                        else:
                            logger.info("Go Plus connectd!")
                            break
                return 'on_pokemon'
            else:
                if len(spawns_to_snipe) > 0:
                    # no need resume or wait if not found
                    logger.info('Snipe Pokemon not found. Going for next...')
                    return False

                # cd_total_sec = calculate_cooldown(last_active_location.get('latitude', 0),
                #                                  last_active_location.get('longitude', 0),
                #                                  self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1])

                cd_total_sec = 1
                await self.p.goto_location(self.config['snipe']['default_location'][0], self.config['snipe']['default_location'][1], 1)

                logger.info('Snipe Pokemon not found. Pausing for {:.2f} mins before restarting route...'.format(
                    cd_total_sec / 60))
                await asyncio.sleep(cd_total_sec)
                logger.info('Resuming route...')
                await self.p.start_route(self.config['snipe']['default_route_name'])
                if self.config['client'].get('auto_goplus', False):
                    logger.info("Checking Go Plus status...")
                    counter = 0
                    while True:
                        im_rgb = await screen_cap(self.d)
                        if counter >= 3:
                            logger.info("Unable to connect...")
                            break
                        if is_plus_disconnected(im_rgb, offset):
                            logger.info("Go Plus is disconnected, attempt to connect now....")
                            await tap_screen(self.p, 990, 450, 1.0)
                            logger.info("Please wait... Go Plus connecting...")
                            await asyncio.sleep(7.0)
                            counter += 1
                        else:
                            logger.info("Go Plus connectd!")
                            break
                return False

        return False

    async def shiny_check(self):
        global spawns_to_check
        global last_active_location
        global last_caught_location
        global rab_runtime_status
        global pgsharp_client
        global mad_client

        im_rgb = await screen_cap(self.d)
        if is_pokemon_full(im_rgb) and self.config.get('poke_management'):
            if self.config['poke_management'].get('enable_poke_management', False):
                self.trivial_page_count = 0
                await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                await clear_pokemon_inventory(self.p, self.d, pgsharp_client=pgsharp_client, mad_client=mad_client)
                return 'on_poke_management'

        if self.pgsharpv2:
            # PGSHarp v2
            current_count = await pgsharp_client.get_nearby_count(self.p, self.d)
            if current_count != pgsharp_client.nearby_count:
                pgsharp_client.nearby_count = current_count
                #pgsharp_client.current_index = 0
            if pgsharp_client.current_index >= pgsharp_client.nearby_count:
                pgsharp_client.current_index = 0
            if pgsharp_client.nearby_count == 0:
                if not await pgsharp_client.wait_for_spawn(self.p, self.d):
                    logger.info('No Pokemon found in snipe feed...')
                    return 'not found'  # return if nothing is found
            # all okay, let's move
            try:
                # Let's try always tap first one
                x, y = await pgsharp_client.get_item_position(self.d(resourceId='me.underw.hp:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo')[0].info, self.config.get('resize', False))
            except:
                return 'on_error'

            tempDict = {}
            tempDict['screen_x'] = x
            tempDict['screen_y'] = y
            tempDict['latitude'] = 0.0
            tempDict['longitude'] = 0.0
            tempDict['name'] = 'Unkown'
            tempDict['iv'] = 0
            tempDict['cp'] = 0
            tempDict['level'] = 0
            tempDict['reported_time'] = int(time.time())
            spawns_to_check.append(tempDict)

        if len(spawns_to_check) > 0:
            if self.iteration_num != 0:
                current_time = int(time.time())
                logger.info('{} Iteration #{} took {:.3f} sec {}'
                            .format('=' * 20, self.iteration_num, current_time - self.last_iteration, '=' * 20))
                self.last_iteration = current_time
            self.iteration_num += 1
            self.pokemon = Pokemon()

            while True:
                mon_to_check = spawns_to_check.pop(0)
                sec_reported = time.time() - mon_to_check.get('reported_time', 0)
                if sec_reported >= 25 * 60:
                    logger.warning("Ignored {},{}: {} (IV{} | CP{} | LVL{}), reported {:.0f} sec ago."
                                   .format(mon_to_check['latitude'], mon_to_check['longitude'], mon_to_check['name'],
                                           mon_to_check['iv'], mon_to_check['cp'], mon_to_check['level'], sec_reported))
                    return
                else:
                    break

            if not self.pgsharpv2:
                logger.info('Checking {},{}: {} (IV{} | CP{} | LVL{}) (reported {:.0f} min ago, {} {} left).'
                            .format(mon_to_check['latitude'], mon_to_check['longitude'], mon_to_check['name'],
                                    mon_to_check['iv'], mon_to_check['cp'], mon_to_check['level'], sec_reported / 60,
                                    len(spawns_to_check), 'spawn' if len(spawns_to_check) <= 1 else 'spawns'))
            else:
                logger.info('Checking pokemon...')
            # adjust based on the spawns left
            timeout = 90
            # if len(spawns_to_check) <= 8:
            #    timeout = 60
            # elif len(spawns_to_check) <= 20:
            #    timeout = 45
            # else:
            #    timeout = 30
            pokemon_tapped = await load_tap_pokemon(self.p, self.d, self.pokemon, mon_to_check, timeout=timeout, config=self.config, zoomout=self.zoomout, pgsharp_client=pgsharp_client, mad_client=mad_client)
            if pokemon_tapped:
                self.pokemon = pokemon_tapped
                self.pokemon.latitude, self.pokemon.longitude = mon_to_check['latitude'], mon_to_check['longitude']
            else:
                self.no_spawn_count += 1
                return 'not_shiny'
                # await asyncio.sleep(1.0)
                # await tap_screen(self.p, 540, 1230, 1.0)
                # await asyncio.sleep(1.0)
                # await tap_screen(self.p, 540, 1240, 1.0)
                # im_rgb = await screen_cap(self.d)
                # self.pokemon.update_stats_from_pokemod(im_rgb)

            if (self.pokemon.name == mon_to_check['name']) or \
                    (self.pokemon.iv == mon_to_check['iv']) or \
                    (self.pokemon.cp == mon_to_check['cp']) or \
                    self.pgsharpv2:
                logger.info('Tapped {} (IV{} | CP{} | LVL{}).'
                            .format(self.pokemon.name, self.pokemon.iv, self.pokemon.cp, self.pokemon.level))

                if not self.config['client'].get('skip_encounter_intro'):
                    await asyncio.sleep(3.0)
                im_rgb = await screen_cap(self.d)
                if is_catch_pokemon_page(im_rgb):
                    self.pokemon.update_stats_from_catch_screen(im_rgb)
                    self.no_spawn_count = 0

                if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                    report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)

                if self.player_level >= 30 and pgsharp_client:
                    await self.check_and_send(self.pokemon, pgsharp_client)
                if self.pokemon.shiny:
                    save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
                    cd_total_sec = calculate_cooldown(last_caught_location.get('latitude', 0),
                                                      last_caught_location.get('longitude', 0),
                                                      mon_to_check['latitude'], mon_to_check['longitude'])
                    sec_elapsed = int(time.time()) - last_caught_location.get('time', 0)
                    cd_sec_left = cd_total_sec - sec_elapsed
                    if cd_sec_left < 0:
                        cd_sec_left = 0
                    # beepy.beep(sound=1)

                    if self.config['shiny_check'].get('auto_catch'):
                        if cd_sec_left > 0:
                            logger.info('Pausing for {:.2f} min before catching...'.format(cd_sec_left / 60))
                            await asyncio.sleep(cd_sec_left)

                        pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                        if pokemon_caught and not self.config['client'].get('transfer_on_catch', False):
                            self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            last_caught_location['latitude'] = mon_to_check['latitude']
                            last_caught_location['longitude'] = mon_to_check['longitude']
                            last_caught_location['time'] = int(time.time())
                            return 'on_pokemon'
                        elif pokemon_caught and self.config['client'].get('transfer_on_catch', False):
                            if pokemon_caught != 'No Ball':
                                await asyncio.sleep(1)
                                await fav_last_caught(self.p, self.d, self.pokemon)
                                await asyncio.sleep(1)
                            last_caught_location['latitude'] = mon_to_check['latitude']
                            last_caught_location['longitude'] = mon_to_check['longitude']
                            last_caught_location['time'] = int(time.time())
                            return 'on_pokemon'
                        self.no_action_count = 0
                        return 'on_pokemon'

                    # for now do nothing...
                    logger.critical('Alert: Shiny Found! CD TIME: {:.2f} min.'.format(cd_sec_left / 60))
                    await asyncio.sleep(cd_sec_left)
                    logger.critical('Alert: Shiny Found! YOU CAN CATCH NOW')
                    # beepy.beep(sound=1)
                    print('\a')  # This is suppose to play a beep sound....
                    input("Press Enter to continue...")
                    last_caught_location['latitude'] = mon_to_check['latitude']
                    last_caught_location['longitude'] = mon_to_check['longitude']
                    last_caught_location['time'] = int(time.time())
                    return 'on_catch_screen'

                #logger.info("{},{} is not shiny".format(mon_to_check['latitude'],mon_to_check['longitude']))
                logger.info('Not Shiny, moving to next Pokemon...')
                return 'not_shiny'
            else:
                logger.info('Incorrect Pokemon, moving to next Pokemon...')
                return 'not_shiny'
        else:
            logger.warning("Waiting for new spawns.")

    async def update_location(self, save_file=False):
        global last_active_location
        global last_caught_location
        global pgsharp_client

        if self.config['client'].get('pgsharp_shuno_hunt', 0) and self.pgsharpv2 and pgsharp_client:
            if save_file:
                lat, lon = await self.p.get_location(save_file)
            try:
                lat, lon = await pgsharp_client.get_location(self.p, self.d)
            except:
                # use orginal method
                lat, lon = await pgsharp_client.get_location(self.p, self.d, method2=True)
        else:
            lat, lon = await self.p.get_location(save_file)

        config_location = self.config['telegram'].get('default_location', [0, 0])

        if lat and lon:
            last_active_location['latitude'] = lat
            last_active_location['longitude'] = lon
            if not last_caught_location:  # set last caught to be the first position got in game
                last_caught_location['latitude'] = lat
                last_caught_location['longitude'] = lon
        else:
            last_active_location['latitude'] = config_location[0]
            last_active_location['longitude'] = config_location[1]
            if not last_caught_location:  # set last caught to be the first position got in game
                last_caught_location['latitude'] = config_location[0]
                last_caught_location['longitude'] = config_location[1]
        last_active_location['time'] = int(time.time())
        logger.info('Last active location: {}, {}'.format(last_active_location['latitude'],
                                                          last_active_location['longitude']))

    async def farmer(self):
        global localnetwork
        global rab_runtime_status
        global last_active_location
        global last_caught_location
        self.pokemon = Pokemon()

        # Clear data that we don't need
        #localnetwork.fort[:] = []
        #localnetwork.pokestop[:] = []
        localnetwork.slotable_gym[:] = []
        localnetwork.gym_sloted[:] = []
        #localnetwork.wild[:] = []
        localnetwork.gym[:] = []
        #localnetwork.encounter[:] = []
        localnetwork.incident[:] = []

        message = ''
        now = datetime.now()
        str_now = now.strftime("%Y-%m-%d %H:%M:%S")

        if len(localnetwork.catch) > 0 and len(localnetwork.encounter) > 0:
            encounterPokeData = localnetwork.encounter.pop()
            self.pokemon.update_stats_from_polygon(encounterPokeData)

            caught_status = localnetwork.catch.pop()  # remove it
            logger.debug('Status: {}'.format(caught_status.get('status')))
            if caught_status.get('status') == 'CATCH_SUCCESS':
                # {'status': 'CATCH_SUCCESS', 'capturedPokemonId': '13903424631688390465', 'scores': {'activityType': ['ACTIVITY_CATCH_POKEMON', 'ACTIVITY_CATCH_EXCELLENT_THROW', 'ACTIVITY_CATCH_CURVEBALL', 'ACTIVITY_CATCH_FIRST_THROW'], 'exp': [100, 1000, 20, 50], 'candy': [3, 0, 0, 0], 'stardust': [100, 0, 0, 0], 'xlCandy': [0, 0, 0, 0]}, 'captureReason': 'DEFAULT', 'pokemonDisplay': {'gender': 'FEMALE', 'form': 'POLIWAG_NORMAL', 'displayId': '1914603624632000740'}}
                if 'displayPokedexId' in caught_status:
                    logger.info('Ditto is caught')
                    self.pokemon.name = 'Ditto'
                logger.info('{}: {} Caught CP: {} ({}/{}/{}) Shiny: {}'.format(str_now, self.pokemon.name,
                            self.pokemon.cp, self.pokemon.atk_iv, self.pokemon.def_iv, self.pokemon.sta_iv, self.pokemon.shiny))
                message = '{}: {} Caught CP: {} ({}/{}/{}) Shiny: {}'.format(str_now, self.pokemon.name, self.pokemon.cp,
                                                                             self.pokemon.atk_iv, self.pokemon.def_iv, self.pokemon.sta_iv, self.pokemon.shiny)
                ttl_exp = sum(caught_status['scores'].get('exp', []))
                ttl_candies = sum(caught_status['scores'].get('candy', []))
                ttl_stardust = sum(caught_status['scores'].get('stardust', []))
                ttl_XL = sum(caught_status['scores'].get('xlCandy', []))
                logger.info('Total Experience: {} | Candies: {} | XL: {} | Stardust: {}'.format(
                    ttl_exp, ttl_candies, ttl_XL, ttl_stardust))
                message += '\nTotal Experience: {} | Candies: {} | XL: {} | Stardust: {}'.format(
                    ttl_exp, ttl_candies, ttl_XL, ttl_stardust)

            elif caught_status.get('status') == 'CATCH_ESCAPE':
                logger.info('Pokemon escaped...')
            elif caught_status.get('status') == 'CATCH_MISSED':
                logger.info('Miss Target...')
            elif caught_status.get('status') == 'CATCH_FLEE':
                logger.info("Pokemon fled...")
                message = '{}: {} CP: {} ({}/{}/{}) Shiny: {} FLED'.format(str_now, self.pokemon.name, self.pokemon.cp,
                                                                           self.pokemon.atk_iv, self.pokemon.def_iv, self.pokemon.sta_iv, self.pokemon.shiny)
            else:
                logger.error("Error...")
            localnetwork.encounter[:] = []
            localnetwork.wild[:] = []

        if len(localnetwork.hatched) > 0:
            hatched_status = localnetwork.hatched.pop()  # remove it

        if len(localnetwork.fort) > 0:
            pokestop_status = localnetwork.fort.pop()

        if len(localnetwork.pokestop_spin_result) > 0:
            spin_result_status = localnetwork.pokestop_spin_result.pop()
            logger.info("Pokestop spinned")

        webhook_url = config['discord'].get('webhook_url', '')
        if webhook_url and message and config.get('discord', False):
            send_to_discord(webhook_url, 'RAB Farmer Reporter ({})'.format(self.device_id), message)

    async def polygon(self):
        # Things to do
        # 0. walk a bit if no pokemon found to see if it will appear <-- Done
        # 1. Check egg hatch <-- Done
        # 2. Sort wild list to the distance of player (check to ensure if there's shiny, it's still first in list) <-- Done
        # 3. Check why sometimes stuck at catching (action)
        # 4. Inventory Managememt <-- Done
        # 5. Quest <-- Done
        # 6. Set min and max item. min to stop catching max to stop spinning <-- Done
        # 7. When in instant catch/transfer mode, remove all level up quest <-- Done
        # Known bug: bot hang after catching shiny... i dont know why....

        global localnetwork
        global rab_runtime_status
        global last_active_location
        global last_caught_location

        # let's check
        timeout = 60
        t0 = time.time()
        t1 = t0 + timeout  # 5 sec timeout
        amplitude = 0.00015
        pokemon_caught = False
        incensePoke = None

        if self.iteration_num != 0:
            current_time = int(time.time())
            logger.info('Iteration #{} took {:.3f} sec.'.format(self.iteration_num, current_time - self.last_iteration))
            self.last_iteration = current_time

        logger.info('=' * 50)
        self.iteration_num += 1
        logger.info('>>> Start iteration #{}'.format(self.iteration_num))
        self.pokemon = Pokemon()

        # bring this infront to try prevent bot hang at mon details page
        # if len(localnetwork.hatched)>0: # this is not working
        im_rgb = await screen_cap(self.d)
        if not is_home_page(im_rgb):

            if is_exit_trainer_dialog(im_rgb):
                await tap_exit_trainer(self.p)

            # im_rgb = await screen_cap(self.d)
            if is_egg_hatched_oh(im_rgb):
                self.trivial_page_count = 0
                await asyncio.sleep(2.0)
                logger.info('Egg Hatched!')
                await tap_screen(self.p, 540, 1190, 0.5)
                if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                    await asyncio.sleep(5.0)
                im_rgb = await screen_cap(self.d)
                if is_mon_details_page(im_rgb):
                    await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                # put on a new egg
                im_rgb = await screen_cap(self.d)
                if is_egg_hatched_page(im_rgb):
                    await select_egg(self.p)
                    await tap_incubate(self.p)
                return 'on_egg'

            # bring this infront to try prevent bot hang at mon details page
            if is_mon_details_page(im_rgb):
                self.trivial_page_count = 0
                await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                # put on a new egg
                im_rgb = await screen_cap(self.d)
                if is_egg_hatched_page(im_rgb):
                    await select_egg(self.p)
                    await tap_incubate(self.p)
                self.no_action_count = 0
                return 'on_pokemon'

            i = 0
            while True:
                im_rgb = await screen_cap(self.d)
                if is_home_page(im_rgb) or i == 4:
                    self.trivial_page_count = 0
                    break
                else:
                    # send the magic button
                    # self.d.press("back")
                    await tap_close_btn(self.p)
                    i += 1
                    await asyncio.sleep(0.5)

            if is_profile_page(im_rgb) or is_pokestop_scan_page(im_rgb):  # fix the problem of keep getting stuck here
                #logger.info('Stuck at profile page?')
                i = 0
                while True:
                    im_rgb = await screen_cap(self.d)
                    if is_home_page(im_rgb) or i == 4:
                        self.trivial_page_count = 0
                        break
                    else:
                        # send the magic button
                        self.d.press("back")  # Back button more effective, let's deal with unable to detect home page later
                        # await tap_close_btn(self.p)
                        i += 1
                        await asyncio.sleep(1)

            if is_catch_pokemon_page(im_rgb):
                # No idea why here.... just use back button to quit
                self.d.press("back")

            if is_main_menu_page(im_rgb) or is_shop_page(im_rgb) or is_nearby_page(im_rgb) or is_incense(im_rgb):
                self.trivial_page_count = 0
                await tap_close_btn(self.p)
                # return 'on_error'

        if self.config['quest'].get('enable_check_quest', False):
            if has_completed_quest_on_map(im_rgb):
                logger.info("Checking and clearing quest....")
                await check_quest(self.d, self.p, self.pokemon, rab_runtime_status=rab_runtime_status)
                self.track_quest_time = int(time.time())
                return 'on_quest'

            # localnetwork.hatched.pop(0)
            # return 'on_pokemon' # No need return, continue from here

        if self.config['catch'].get('shiny_mode', False) and not localnetwork.priorityList:
            default_CD = 4.0
            pokestop = localnetwork.pokestop.pop(0)
            logger.info('Moving to new pokestop')
            #  'latitude': 1.300738, 'longitude': 103.855647,
            await self.p.goto_location(pokestop.get('latitude'), pokestop.get('longitude'), 0.5)
            if localnetwork.last_lat != 0:
                default_CD = calculate_cooldown(localnetwork.last_lat,
                                                localnetwork.last_lng,
                                                pokestop.get('latitude'),
                                                pokestop.get('longitude'))
                if default_CD < 4.0:
                    default_CD = 4.0  # need min 4 secs to hit pokestops
            logger.info('Cooldown timing: {}'.format(default_CD))
            await asyncio.sleep(default_CD)
            # Some how day and night affect how the game detect it's points.....
            # await tap_screen(self.p, 546, 1173, 0.5)
            # im_rgb = await screen_cap(self.d)
            # if is_home_page(im_rgb):
            #    await tap_screen(self.p, 546, 1243, 0.5)

            # await tap_screen(self.p, 546, 1173, 0.1) # old value 1243
            # await tap_screen(self.p, 546, 1243, 0.1) # old value 1243
            localnetwork.last_lat = last_active_location['latitude']
            localnetwork.last_lng = last_active_location['longitude']
            localnetwork.wild[:] = []
            localnetwork.encounter[:] = []

            return 'shiny check'

        if self.config['catch'].get('shiny_mode', False) and localnetwork.priorityList:
            if not ('shiny' in localnetwork.priorityList[0]['pokemon'].get('pokemonDisplay')):
                priorityPoke = localnetwork.priorityList.pop(0)
                return 'shiny check'

        # Gym Detaisl: {'fortId': 'cb6496916fbe46cf9acc2affd9337872.16', 'lastModifiedMs': '1614308171030', 'latitude': 1.285035, 'longitude': 103.844354, 'team': 'TEAM_YELLOW', 'guardPokemonId': 'EXEGGUTOR', 'enabled': True, 'guardPokemonDisplay': {'gender': 'FEMALE', 'form': 'EXEGGUTOR_NORMAL'}, 'closed': True, 'gymDisplay': {'totalGymCp': 12988, 'lowestPokemonMotivation': 0.9982962012290955, 'slotsAvailable': 1, 'occupiedMillis': '88633'}, 'sameTeamDeployLockoutEndMs': '1614308538505'}
        # we only slot if RAB is not chasing pokemon
        if localnetwork.slotable_gym and self.poke_in_gym < 9 and self.config['client'].get('auto_slot', False) and not self.config['catch'].get('mon_to_chase', False):
            slotableGym = localnetwork.slotable_gym.pop()
            default_CD = calculate_cooldown(localnetwork.last_lat,
                                            localnetwork.last_lng,
                                            slotableGym.get('latitude'),
                                            slotableGym.get('longitude'))

            logger.info('Moving to Gym for sloting (Availible Slots: {}) Cooldown: {}'.format(
                slotableGym['gymDisplay'].get('slotsAvailable'), default_CD))
            await self.p.goto_location(slotableGym.get('latitude'), slotableGym.get('longitude'), 0.5)
            await asyncio.sleep(default_CD)  # wait for network
            #txt = input("Pause to take manual screenshots")
            # egg might pop here, let's check before tapping
            im_rgb = await screen_cap(self.d)
            if is_egg_hatched_oh(im_rgb):
                self.trivial_page_count = 0
                await asyncio.sleep(2.0)
                logger.info('Egg Hatched!')
                await tap_screen(self.p, 540, 1190, 0.5)
                if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                    await asyncio.sleep(5.0)
                im_rgb = await screen_cap(self.d)
                if is_mon_details_page(im_rgb):
                    await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                # put on a new egg
                im_rgb = await screen_cap(self.d)
                if is_egg_hatched_page(im_rgb):
                    await select_egg(self.p)
                    await tap_incubate(self.p)
                return 'on_egg'

            if is_mon_details_page(im_rgb):
                self.trivial_page_count = 0
                await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                # put on a new egg
                im_rgb = await screen_cap(self.d)
                if is_egg_hatched_page(im_rgb):
                    await select_egg(self.p)
                    await tap_incubate(self.p)
                return 'on_egg'

            await tap_screen(self.p, 545, 1140, 5)
            await tap_screen(self.p, 955, 1570, 1)

            # First Pokemon in list position
            await tap_screen(self.p, poke_location[self.poke_in_gym].get('x'), poke_location[self.poke_in_gym].get('y'), 2)
            # await tap_screen(self.p, 540, 980, 1.5) #okay
            im_rgb = await screen_cap(self.d)
            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
            # await tap_screen(self.p, 940, 600, 1) # Sort by recent
            # await tap_close_btn(self.p)
            await tap_close_btn(self.p)
            if len(localnetwork.gym) > 0:
                localnetwork.gym[:] = []  # Clear this to tell RAB next pokestop / pokemon is okay to catch

            self.poke_in_gym += 1
            localnetwork.last_lat = last_active_location['latitude']
            localnetwork.last_lng = last_active_location['longitude']

        if self.poke_in_gym >= 9:
            localnetwork.slotable_gym[:] = []  # clear this list to prevent memory issue
            # things to do -> check if any poke is dead

        if localnetwork.inventory_full:
            if localnetwork.mode == 0:
                # Let's assume inventory is full and there's ball
                localnetwork.mode = 1
            if localnetwork.total_ball_count == 0:
                logger.warning('Inventory is full and there might be not enoughball....')

        if ((len(localnetwork.wild) > 0 or len(localnetwork.encounter) > 0) and localnetwork.mode == 1) or localnetwork.priorityList or localnetwork.incense_pokemon or localnetwork.chase_after_poke:
            logger.debug('wild: {} | encounter: {} | incense: {} | mode: {}'.format(len(localnetwork.wild),
                         len(localnetwork.encounter), len(localnetwork.incense_pokemon), localnetwork.mode))
            if not localnetwork.priorityList and not localnetwork.incense_pokemon and not localnetwork.chase_after_poke:
                if not localnetwork.inventory_full:
                    if ((localnetwork.items and localnetwork.total_ball_count <= self.config['catch'].get('stop_at_ball', 10) and not localnetwork.priorityList)) or localnetwork.total_ball_count == 0:
                        logger.info('Starting Spin Spokestop Mode...')
                        localnetwork.rejected[:] = []  # reset this to ensure mem is freed
                        localnetwork.rejected_chase[:] = []
                        # got stuck after catching pokemon. added this to see if this the problem
                        localnetwork.priorityList[:] = []
                        # sort pokestop here everytime mode change. this will make RAB go after the nearest pokestops instead of jumping large distance
                        localnetwork.sort_pokestops()
                        localnetwork.mode = 0
                        return

            # Get current location, sort list by distance then pop
            x = last_active_location['latitude']
            y = last_active_location['longitude']

            poke_to_chase = {}

            # Teleport to chase after pokemon and wait till it appear
            if localnetwork.chase_after_poke:
                poke_to_chase = localnetwork.chase_after_poke.pop(0)

                if poke_to_chase.get('latitude', 0) != 0:
                    lat, lng = poke_to_chase.get('latitude'), poke_to_chase.get('longitude')
                    default_CD = calculate_cooldown(last_active_location['latitude'],
                                                    last_active_location['longitude'],
                                                    lat,
                                                    lng)
                    logger.info('Chasing after {} at {},{} CD: {}'.format(
                        POKEMON[poke_to_chase.get('pokedexNumber', 0)], lat, lng, default_CD))
                    localnetwork.wild[:] = []  # delete to let it repopulate
                    await self.p.goto_location(lat, lng, 0.5)

                    await asyncio.sleep(default_CD)
                    # move around until wild is populated
                    num_round = 0
                    while not localnetwork.wild:
                        if localnetwork.pokemon_inventory_full:
                            if self.config['poke_management'].get('enable_poke_management', False):
                                self.trivial_page_count = 0
                                im_rgb = await screen_cap(self.d)
                                if is_pokemon_full(im_rgb):
                                    await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                                    await clear_pokemon_inventory(self.p, self.d)
                                    if not self.config['poke_management'].get('mass_transfer', False):
                                        # Take a long time to clear. Delete all wild and let new ones come in
                                        localnetwork.wild[:] = []
                                elif is_home_page(im_rgb):
                                    await tap_pokeball_btn(self.p)
                                    await tap_open_pokemon_btn(self.p, 2)
                                    await clear_pokemon_inventory(self.p, self.d)
                                    if not self.config['poke_management'].get('mass_transfer', False):
                                        # Take a long time to clear. Delete all wild and let new ones come in
                                        localnetwork.wild[:] = []
                                localnetwork.pokemon_inventory_full = False

                        if num_round > 10:
                            break
                        await self.p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(lat, lng, 0.5)
                        await self.p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(lat, lng, 0.5)
                        await self.p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(lat, lng, 0.5)
                        await self.p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(lat, lng, 0.5)
                        num_round += 1
                else:
                    localnetwork.rejected_chase.append(poke_to_chase)
                    poke_to_chase.clear()

            for_sort = localnetwork.wild.copy()
            localnetwork.wild[:] = []
            encounterId = ''
            priorityPoke = None
            poke_found = False

            if not localnetwork.priorityList and not localnetwork.incense_pokemon:
                if poke_to_chase:
                    i = 0
                    tmp_poke = None
                    logger.debug('All wild pokemon found: {}'.format(for_sort))
                    for each_wild in for_sort:
                        logger.debug('WILD: {} CHASE: {}'.format(each_wild['pokemon'].get(
                            'pokemonId'), POKEMON[poke_to_chase.get('pokedexNumber')].replace(' ', '_').upper()))
                        if each_wild['pokemon'].get('pokemonId') == POKEMON[poke_to_chase.get('pokedexNumber')].replace(' ', '_').upper():
                            await self.p.goto_location(each_wild.get('latitude'), each_wild.get('longitude'), 0.5)
                            last_active_location['latitude'] = each_wild.get('latitude')
                            last_active_location['longitude'] = each_wild.get('longitude')
                            tmp_poke = for_sort.pop(i)
                            poke_found = True
                            break
                        i += 1
                    if poke_found:
                        localnetwork.wild[:] = for_sort.copy()
                        localnetwork.wild.insert(0, tmp_poke)

                    if not poke_found:
                        localnetwork.rejected_chase.append(poke_to_chase)
                        localnetwork.wild[:] = for_sort.copy()
                        logger.warning('Pokemon to chase not found!')
                        localnetwork.chase_after_poke[:] = []
                        return
                if not poke_to_chase or not poke_found:
                    while True:
                        if len(for_sort) <= 0:
                            break

                        for_sort[:] = localnetwork.get_ordered_list(for_sort, x, y)
                        x = for_sort[0].get('latitude')
                        y = for_sort[0].get('longitude')

                        # if for_sort[0].get('timeTillHiddenMs',100000) <= 36000:
                        #    for_sort.pop(0) # And never add back
                        # else:
                        localnetwork.wild.append(for_sort.pop(0))

                    if localnetwork.wild:
                        encounterId = localnetwork.wild[0].get('encounterId')
                        logger.info('Moving to location of {}'.format(localnetwork.wild[0]['pokemon'].get('pokemonId')))
                        await self.p.goto_location(localnetwork.wild[0].get('latitude'), localnetwork.wild[0].get('longitude'), 0.5)
                        last_active_location['latitude'] = localnetwork.wild[0].get('latitude')
                        last_active_location['longitude'] = localnetwork.wild[0].get('longitude')
                    else:
                        logger.warning('Wild Pokemon not found!')
                        # move 0.0001 from current location to try load some wild pokemon
                        # await self.p.goto_location(localnetwork.wild[0].get('latitude') + 0.00005, localnetwork.wild[0].get('longitude') + 0.00005, 0.5)
                        return
            elif localnetwork.priorityList:
                # Polygon# indicate there's Shiny (we do 100IV later)
                # get wild index
                await asyncio.sleep(2.0)  # wait for network
                priorityPoke = localnetwork.priorityList.pop()
                encounterId = priorityPoke.get('encounterId')
                logger.info('Moving to location of {} (Priority Catch)'.format(priorityPoke['pokemon'].get('pokemonId')))
                await self.p.goto_location(priorityPoke.get('latitude'), priorityPoke.get('longitude'), 0.5)
                last_active_location['latitude'] = priorityPoke.get('latitude')
                last_active_location['longitude'] = priorityPoke.get('longitude')
            elif localnetwork.incense_pokemon:
                # Polygon# indicate there's Shiny (we do 100IV later)
                # get wild index
                await asyncio.sleep(2.0)  # wait for network
                incensePoke = localnetwork.incense_pokemon.pop()
                localnetwork.incense_pokemon[:] = []
                encounterId = incensePoke.get('encounterId')
                logger.info('Moving to location of {} (Incense Pokeomon)'.format(incensePoke.get('pokemonTypeId')))
                #logger.info('Full Results: {}'.format(incensePoke))
                # {'result': 'INCENSE_ENCOUNTER_AVAILABLE', 'pokemonTypeId': 'MILTANK', 'lat': 1.3038122631878932, 'lng': 103.83317396792022, 'encounterLocation': '31da198df7f', 'encounterId': '8342348775075069043', 'disappearTimeMs': '1615715649852', 'pokemonDisplay': {'gender': 'FEMALE', 'weatherBoostedCondition': 'PARTLY_CLOUDY', 'displayId': '8342348775075069043'}}
                await self.p.goto_location(incensePoke.get('latitude'), incensePoke.get('longitude'), 0.5)
                last_active_location['latitude'] = incensePoke.get('latitude')
                last_active_location['longitude'] = incensePoke.get('longitude')

            # move command issued, let's wait x secs before tapping
            default_CD = 4.0
            if localnetwork.last_lat != 0 and not poke_to_chase:
                default_CD = calculate_cooldown(localnetwork.last_lat,
                                                localnetwork.last_lng,
                                                last_active_location['latitude'],
                                                last_active_location['longitude'])
                if default_CD < 4.0:
                    default_CD = 4.0  # need min 4 secs to hit pokestops

            logger.info('Cooldown timing: {}'.format(default_CD))
            await asyncio.sleep(default_CD)
            currentCount = len(localnetwork.wild)
            localnetwork.last_lat = last_active_location['latitude']
            localnetwork.last_lng = last_active_location['longitude']

            while True:
                pokemon_caught = False
                localnetwork.encounter[:] = []  # Let's clear encounter right before tapping
                logger.info('>>>>> Start tapping spawns >>>>>')
                if time.time() > t1:
                    logger.warning('No spawn after {} sec.'.format(timeout))
                    encounterIndex = localnetwork.check_duplicate(localnetwork.wild, 'encounterId', encounterId)
                    if encounterIndex >= 0:
                        rejected = localnetwork.wild.pop(encounterIndex)  # remove it
                        localnetwork.rejected.append(rejected)  # Too many pokemon ~ miss a few wont die
                    self.trivial_page_count += 1
                    return

                # await tap_screen(self.p, 540, 1240, 0.25)
                # im_rgb = await screen_cap(self.d)
                # if is_home_page(im_rgb):
                #    await tap_screen(self.p, 540, 1240, 0.25)
                #    im_rgb = await screen_cap(self.d)
                #    if is_home_page(im_rgb):
                #        await tap_screen(self.p, 540, 1210, 0.25)
                #        im_rgb = await screen_cap(self.d)
                #        if is_home_page(im_rgb):
                #            await tap_screen(self.p, 540, 1210, 0.25)
                #            im_rgb = await screen_cap(self.d)
                #            if is_home_page(im_rgb):
                #                await tap_screen(self.p, 540, 1170, 0.25)
                #                im_rgb = await screen_cap(self.d)
                #                if is_home_page(im_rgb):
                #                    await tap_screen(self.p, 540, 1170, 0.25)

                point_count = 0
                # test new method
                if not incensePoke:
                    for y in range(1260, 1150, -5):
                        await tap_screen(self.p, random.randint(535, 545), y, 0.25)
                        if len(localnetwork.encounter) > 0 and poke_found:
                            break
                        if len(localnetwork.repeat_encounter) > 0:
                            break
                        if len(localnetwork.incident) > 0:
                            break
                        if len(localnetwork.gym) > 0:
                            break
                        if len(localnetwork.incense_pokemon_encounter) > 0:
                            break
                        if localnetwork.pokemon_inventory_full:
                            break
                        if len(localnetwork.pokestop_spin_result) > 0:
                            self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                            await asyncio.sleep(1)  # To prevent zoomin
                            localnetwork.pokestop_spin_result[:] = []
                else:
                    # incense searching
                    while True:
                        if point_count == 0:
                            x = 540
                            y = 1240
                        elif point_count == 1:
                            x = 560
                            y = 1240
                        elif point_count == 2:
                            x = 560
                            y = 1220
                        elif point_count == 3:
                            x = 540
                            y = 1220
                        elif point_count == 4:
                            x = 520
                            y = 1220
                        elif point_count == 5:
                            x = 520
                            y = 1240
                        elif point_count == 6:
                            x = 520
                            y = 1260
                        elif point_count == 7:
                            x = 540
                            y = 1260
                        elif point_count == 8:
                            x = 560
                            y = 1260
                        else:
                            break

                        await tap_screen(self.p, x, y, 0.2)
                        if len(localnetwork.repeat_encounter) > 0:
                            break
                        if len(localnetwork.incense_pokemon_encounter) > 0:
                            break
                        if len(localnetwork.incident) > 0:
                            break
                        if len(localnetwork.gym) > 0:
                            break
                        if localnetwork.pokemon_inventory_full:
                            break
                        if len(localnetwork.pokestop_spin_result) > 0:
                            self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                            await asyncio.sleep(1)  # To prevent zoomin
                            localnetwork.pokestop_spin_result[:] = []
                        point_count += 1

                # await tap_screen(self.p, 540, 1240, 0.25)
                    # await tap_screen(self.p, 540, 1225, 0.2)
                # await tap_screen(self.p, 540, 1210, 0.25)
                # await tap_screen(self.p, 540, 1190, 0.25)
                # await tap_screen(self.p, 540, 1170, 0.25) # super high poke
                    #failed = False

                if len(localnetwork.incense_pokemon_encounter) > 0:
                    incensePokeData = localnetwork.incense_pokemon_encounter.pop()
                    self.pokemon.update_stats_from_polygon(incensePokeData)
                    if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                        report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
                    if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                        await asyncio.sleep(1)
                        self.d.press("back")  # Flee
                        localnetwork.incense_pokemon_encounter[:] = []
                        return 'on_pokemon'

                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, localnetwork, incensePokeData['pokemon']['pokemonDisplay'].get('displayId'), rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                    if pokemon_caught == 'No Ball':
                        localnetwork.total_ball_count = 0
                        localnetwork.mode = 0
                    localnetwork.incense_pokemon_encounter[:] = []
                    if priorityPoke:
                        # Make sure shiny list is empty to prevent it from checking it again
                        localnetwork.priorityList[:] = []
                    return 'on_pokemon'

                wildPokeData = None
                if len(localnetwork.encounter) > 0:
                    encounterIndex = localnetwork.check_duplicate(localnetwork.encounter, 'encounterId', encounterId)
                    if encounterIndex >= 0 or poke_found:
                        localnetwork.repeat_encounter[:] = []
                        self.trivial_page_count = 0
                        # remove from list before catching
                        encounterPokeData = localnetwork.encounter.pop(encounterIndex)
                        wildEncounterIndex = localnetwork.check_duplicate(localnetwork.wild, 'encounterId', encounterId)
                        wildPokeData = localnetwork.wild.pop(wildEncounterIndex)
                        self.pokemon.update_stats_from_polygon(encounterPokeData)
                        if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                            report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
                        if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                            await asyncio.sleep(1)
                            self.d.press("back")  # Flee
                            localnetwork.encounter[:] = []
                            return 'on_pokemon'
                        pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, localnetwork, wildPokeData['pokemon']['pokemonDisplay'].get('displayId'), rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                        if pokemon_caught == 'No Ball':
                            localnetwork.total_ball_count = 0
                            localnetwork.mode = 0
                        localnetwork.encounter[:] = []
                        if priorityPoke:
                            # Make sure shiny list is empty to prevent it from checking it again
                            localnetwork.priorityList[:] = []
                    else:
                        # wrong poke, here need refinement
                        newEncounterID = None
                        im_rgb = await screen_cap(self.d)  # In case didn't get from network intime
                        if is_catch_pokemon_page(im_rgb):
                            self.trivial_page_count = 0
                            if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                                report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
                            if not priorityPoke:
                                logger.info('Wrong Pokemon')
                                wildPokeData = localnetwork.encounter.pop()

                                self.pokemon.update_stats_from_polygon(wildPokeData)
                                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                                    await asyncio.sleep(1)
                                    self.d.press("back")  # Flee
                                    localnetwork.encounter[:] = []
                                    return 'on_pokemon'
                                pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, localnetwork, wildPokeData['pokemon']['pokemonDisplay'].get('displayId'), rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                                if pokemon_caught == 'No Ball':
                                    localnetwork.total_ball_count = 0
                                    localnetwork.mode = 0
                            else:
                                logger.info('Shiny Pokemon')
                                wildPokeData = priorityPoke
                                pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, localnetwork, priorityPoke['pokemon']['pokemonDisplay'].get('displayId'), rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                                if pokemon_caught == 'No Ball':
                                    localnetwork.total_ball_count = 0
                                    localnetwork.mode = 0
                                localnetwork.priorityList[:] = []
                            localnetwork.encounter[:] = []
                            newEncounterID = wildPokeData.get('encounterId')
                            newEncounterIndex = localnetwork.check_duplicate(localnetwork.wild, 'encounterId', newEncounterID)
                            if newEncounterIndex >= 0:
                                # remove from wild poke so that bot will not go after it anymore
                                localnetwork.wild.pop(newEncounterIndex)
                            localnetwork.repeat_encounter[:] = []

                    if pokemon_caught and not self.config['client'].get('transfer_on_catch', False):
                        self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                        if pokemon_caught != 'No Ball':
                            await asyncio.sleep(1)
                            await fav_last_caught(self.p, self.d, self.pokemon)
                            await asyncio.sleep(1)

                    return 'on_pokemon'

                if len(localnetwork.fort) > 0:
                    if len(localnetwork.incident) > 0:
                        self.trivial_page_count = 0
                        await asyncio.sleep(2.0)  # Wait for correct screenshot
                        # Screenshot is called to see which page of team rocket we are at now
                        im_rgb = await screen_cap(self.d)
                        team_go_rocket = is_team_rocket_page(im_rgb)
                        logger.debug(localnetwork.incident)
                        localnetwork.incident[:] = []
                        await asyncio.sleep(4.0)
                        self.trivial_page_count = 0
                        if team_go_rocket == 'rocket_collect':
                            await tap_screen(self.p, 540, 1715, 1.0)
                            return 'on_team_rocket'
                        if team_go_rocket == 'rocket_equip':
                            await tap_screen(self.p, 540, 1540, 3.0)
                            return 'on_team_rocket'

                        result = await fight_team_rocket(self.p, self.d, team_go_rocket)
                        if result:
                            # catch shadow pokemon
                            self.pokemon.type = 'shadow'
                            im_rgb = await screen_cap(self.d)
                            try:
                                self.pokemon.update_stats_from_catch_screen(im_rgb)
                                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                                    await asyncio.sleep(1)
                                    self.d.press("back")  # Flee
                                    localnetwork.encounter[:] = []
                                    return 'on_pokemon'
                            except:
                                pass
                            if not self.pokemon.shiny or Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                                im_rgb = await screen_cap(self.d)
                                save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                                self.pokemon.update_stats_from_catch_screen(im_rgb)
                                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                                    await asyncio.sleep(1)
                                    self.d.press("back")  # Flee
                                    localnetwork.encounter[:] = []
                                    return 'on_pokemon'

                            if self.pokemon.shiny:
                                save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
                            if is_catch_pokemon_page(im_rgb, is_shadow=True):
                                if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                                    report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
                                pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                                if pokemon_caught == 'No Ball':
                                    localnetwork.total_ball_count = 0
                                    localnetwork.mode = 0
                                if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                                    self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                                if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                                    if pokemon_caught != 'No Ball':
                                        await asyncio.sleep(1)
                                        await fav_last_caught(self.p, self.d, self.pokemon)
                                        await asyncio.sleep(1)
                                return 'on_pokemon'

                    logger.info('Pokemon too near pokestop... go for next pokemon')
                    localnetwork.fort.pop(0)
                    if len(localnetwork.pokestop_spin_result) > 0:
                        spin_result_status = localnetwork.pokestop_spin_result.pop()
                        logger.info("Pokestop spinned")
                        if spin_result_status.get('result') == 'INVENTORY_FULL':
                            localnetwork.mode = 1
                        localnetwork.pokestop_spin_result[:] = []
                    encounterIndex = localnetwork.check_duplicate(localnetwork.wild, 'encounterId', encounterId)
                    if len(localnetwork.wild) > 0:
                        rejected = localnetwork.wild.pop(encounterIndex)  # remove it
                        localnetwork.rejected.append(rejected)  # Too many pokemon ~ miss a few wont die
                    if not self.config['client'].get('instant_spin'):
                        if not self.config['spin_pokestop']:
                            await tap_close_btn(self.p)
                            return
                        await spin_pokestop(self.p, self.d)
                    return 'on_pokestop'
                    # await tap_close_btn(self.p)
                    #self.d.swipe(1040, 960 - 100, 1040, 960 + 100, 0.5)

                if len(localnetwork.gym) > 0:
                    self.trivial_page_count = 0
                    logger.info('Pokemon too near gym... go for next pokemon')
                    localnetwork.gym.pop(0)
                    await asyncio.sleep(4)
                    # await tap_close_btn(self.p)
                    self.d.press("back")
                    i = 0
                    while True:
                        im_rgb = await screen_cap(self.d)
                        if is_home_page(im_rgb) or i == 8:
                            self.trivial_page_count = 0
                            break
                        else:
                            # send the magic button
                            self.d.press("back")  # Back button more effective, let's deal with unable to detect home page later
                            # await tap_close_btn(self.p)
                            i += 1
                            await asyncio.sleep(1)
                    encounterIndex = localnetwork.check_duplicate(localnetwork.wild, 'encounterId', encounterId)
                    if len(localnetwork.wild) > 0:
                        rejected = localnetwork.wild.pop(encounterIndex)  # remove it
                        localnetwork.rejected.append(rejected)  # Too many pokemon ~ miss a few wont die
                    return 'on_gym'
                    #self.d.swipe(1040, 960 - 100, 1040, 960 + 100, 0.5)

                if localnetwork.pokemon_inventory_full:
                    if self.config['poke_management'].get('enable_poke_management', False):
                        self.trivial_page_count = 0
                        im_rgb = await screen_cap(self.d)
                        if is_pokemon_full(im_rgb):
                            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                            await clear_pokemon_inventory(self.p, self.d)
                            if not self.config['poke_management'].get('mass_transfer', False):
                                # Take a long time to clear. Delete all wild and let new ones come in
                                localnetwork.wild[:] = []
                        elif is_home_page(im_rgb):
                            await tap_pokeball_btn(self.p)
                            await tap_open_pokemon_btn(self.p, 2)
                            await clear_pokemon_inventory(self.p, self.d)
                            if not self.config['poke_management'].get('mass_transfer', False):
                                # Take a long time to clear. Delete all wild and let new ones come in
                                localnetwork.wild[:] = []
                        localnetwork.pokemon_inventory_full = False
                        return 'on_poke_management'

                # await asyncio.sleep(1.0) # wait for data
                im_rgb = await screen_cap(self.d)
                if is_egg_hatched_oh(im_rgb):
                    self.trivial_page_count = 0
                    await asyncio.sleep(2.0)
                    logger.info('Egg Hatched!')
                    await tap_screen(self.p, 540, 1190, 0.5)
                    if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                        await asyncio.sleep(5.0)
                    im_rgb = await screen_cap(self.d)
                    if is_mon_details_page(im_rgb):
                        await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    # put on a new egg
                    im_rgb = await screen_cap(self.d)
                    if is_egg_hatched_page(im_rgb):
                        await select_egg(self.p)
                        await tap_incubate(self.p)
                    return 'on_egg'

                if is_mon_details_page(im_rgb):
                    self.trivial_page_count = 0
                    await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    # put on a new egg
                    im_rgb = await screen_cap(self.d)
                    if is_egg_hatched_page(im_rgb):
                        await select_egg(self.p)
                        await tap_incubate(self.p)
                    return 'on_egg'

                # In case of corrupted data, scrrenshot use as backup
                # im_rgb = await screen_cap(self.d) # In case didn't get from network intime
                if is_catch_pokemon_page(im_rgb):
                    self.trivial_page_count = 0
                    self.pokemon.update_stats_from_catch_screen(im_rgb)
                    if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                        report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
                    if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                        await asyncio.sleep(1)
                        self.d.press("back")  # Flee
                        localnetwork.encounter[:] = []
                        return 'on_pokemon'
                    # Catch it the normal way
                    pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                    if pokemon_caught == 'No Ball':
                        localnetwork.total_ball_count = 0
                        localnetwork.mode = 0
                    if pokemon_caught and not self.config['client'].get('transfer_on_catch', False):
                        self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                    if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                        if pokemon_caught != 'No Ball':
                            await asyncio.sleep(1)
                            await fav_last_caught(self.p, self.d, self.pokemon)
                            await asyncio.sleep(1)
                    if pokemon_caught:
                        wildEncounterIndex = localnetwork.check_duplicate(localnetwork.wild, 'encounterId', encounterId)
                        if len(localnetwork.wild) > 0:
                            wildPokeData = localnetwork.wild.pop(wildEncounterIndex)
                        # self.pokemon.update_stats_from_polygon(encounterPokeData)
                    return 'on_pokemon'

                if is_pokemon_full(im_rgb) and self.config.get('poke_management'):
                    if self.config['poke_management'].get('enable_poke_management', False):
                        self.trivial_page_count = 0
                        await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                        await clear_pokemon_inventory(self.p, self.d)
                        if not self.config['poke_management'].get('mass_transfer', False):
                            localnetwork.wild[:] = []  # Take a long time to clear. Delete all wild and let new ones come in
                        return 'on_poke_management'

                await asyncio.sleep(1.0)

                # Some manual detection until figure out which protos are called
                # team go rocket, keep this, non team rocket blastoff will still see this
                team_go_rocket = is_team_rocket_page(im_rgb)
                if team_go_rocket:
                    self.trivial_page_count = 0
                    if team_go_rocket == 'rocket_collect':
                        await tap_screen(self.p, 540, 1715, 1.0)
                        return 'on_team_rocket'
                    if team_go_rocket == 'rocket_equip':
                        await tap_screen(self.p, 540, 1540, 3.0)
                        return 'on_team_rocket'

                    result = await fight_team_rocket(self.p, self.d, team_go_rocket)
                    if result:
                        # catch shadow pokemon
                        self.pokemon.type = 'shadow'
                        im_rgb = await screen_cap(self.d)
                        self.pokemon.update_stats_from_catch_screen(im_rgb)
                        if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                            report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
                        if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                            await asyncio.sleep(1)
                            self.d.press("back")  # Flee
                            localnetwork.encounter[:] = []
                            return 'on_pokemon'

                        if self.pokemon.shiny:
                            save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
                        if is_catch_pokemon_page(im_rgb, is_shadow=True):
                            pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                            if pokemon_caught == 'No Ball':
                                localnetwork.total_ball_count = 0
                                localnetwork.mode = 0
                            if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                                self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                                if pokemon_caught != 'No Ball':
                                    await asyncio.sleep(1)
                                    await fav_last_caught(self.p, self.d, self.pokemon)
                                    await asyncio.sleep(1)
                            return 'on_pokemon'

                await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)
                await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)
                await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)
                await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)

        if len(localnetwork.pokestop) > 0 and (len(localnetwork.wild) == 0 or localnetwork.mode == 0):  # spin mode
            if localnetwork.items and localnetwork.mode == 0 and localnetwork.total_ball_count >= self.config['catch'].get('resume_at_ball', 100):
                logger.info('Resuming Catching Mode...')
                localnetwork.mode = 1
                return

            # spin 10x and add numbers to .total_ball_count
            if (localnetwork.hitPokestopCount % 10 == 0) and localnetwork.total_ball_count == 0:
                localnetwork.total_ball_count = 1

            # need to hit a poke to check item count
            if ((localnetwork.hitPokestopCount % self.config['catch'].get('catchpoke_every_x_spin', 10) == 0) and len(localnetwork.wild) > 0) and localnetwork.total_ball_count != 0:
                # Get current location, sort list by distance then pop
                x = last_active_location['latitude']
                y = last_active_location['longitude']
                for_sort = localnetwork.wild.copy()
                localnetwork.wild[:] = []
                encounterId = ''

                while True:
                    if len(for_sort) <= 0:
                        break

                    for_sort[:] = localnetwork.get_ordered_list(for_sort, x, y)
                    x = for_sort[0].get('latitude')
                    y = for_sort[0].get('longitude')

                    localnetwork.wild.append(for_sort.pop(0))

                if len(localnetwork.wild) > 0:
                    wildPoke = localnetwork.wild.pop(0)
                    encounterId = wildPoke.get('encounterId')
                    logger.info('Moving to location of {}'.format(wildPoke['pokemon'].get('pokemonId')))
                    await self.p.goto_location(wildPoke.get('latitude'), wildPoke.get('longitude'), 0.5)

                    # move command issued, let's wait x secs before tapping
                    default_CD = 3.0
                    if localnetwork.last_lat != 0:
                        default_CD = calculate_cooldown(localnetwork.last_lat,
                                                        localnetwork.last_lng,
                                                        wildPoke.get('latitude'),
                                                        wildPoke.get('longitude'))
                        if default_CD < 4.0:
                            default_CD = 4.0  # need min 4 secs to hit pokestops

                    logger.info('Cooldown timing: {}'.format(default_CD))
                    await asyncio.sleep(default_CD)
                    localnetwork.last_lat = last_active_location['latitude']
                    localnetwork.last_lng = last_active_location['longitude']

                    pokemon_caught = False
                    localnetwork.encounter[:] = []  # Let's clear encounter right before tapping
                    logger.info('>>>>> Start tapping spawns >>>>>')

                    # await tap_screen(self.p, 540, 1240, 0.25)
                    # im_rgb = await screen_cap(self.d)
                    # if is_home_page(im_rgb):
                    #    await tap_screen(self.p, 540, 1240, 0.25)
                    #    im_rgb = await screen_cap(self.d)
                    #    if is_home_page(im_rgb):
                    #        await tap_screen(self.p, 540, 1210, 0.25)
                    #        im_rgb = await screen_cap(self.d)
                    #        if is_home_page(im_rgb):
                    #            await tap_screen(self.p, 540, 1210, 0.25)
                    #            im_rgb = await screen_cap(self.d)
                    #            if is_home_page(im_rgb):
                    #                await tap_screen(self.p, 540, 1170, 0.25)
                    #                im_rgb = await screen_cap(self.d)
                    #                if is_home_page(im_rgb):
                    #                    await tap_screen(self.p, 540, 1170, 0.25)
                    # test new method
                    for y in range(1260, 1170, -10):
                        await tap_screen(self.p, 540, y, 0.2)
                        if len(localnetwork.encounter) > 0:
                            break
                        if len(localnetwork.incident) > 0:
                            break
                        if len(localnetwork.gym) > 0:
                            break
                        if localnetwork.pokemon_inventory_full:
                            break
                        if len(localnetwork.pokestop_spin_result) > 0:
                            self.d(packageName='com.nianticlabs.pokemongo').swipe("left", steps=50)
                            await asyncio.sleep(1)  # To prevent zoomin

                    # await tap_screen(self.p, 540, 1240, 0.25)
                    # await tap_screen(self.p, 540, 1225, 0.25) # try tap once only
                    # await tap_screen(self.p, 540, 1210, 0.25)
                    # await tap_screen(self.p, 540, 1190, 0.25)
                    # await tap_screen(self.p, 540, 1170, 0.25) # super high poke
                    last_active_location['latitude'] = wildPoke.get('latitude')
                    last_active_location['longitude'] = wildPoke.get('longitude')
                else:
                    logger.info('No wild pokemon in sight...')
                    return
                    #failed = False

                # await asyncio.sleep(1.5) # wait for data
            else:
                default_CD = 4.0
                pokestop = localnetwork.pokestop.pop(0)
                logger.info('Moving to new pokestop')
                #  'latitude': 1.300738, 'longitude': 103.855647,
                await self.p.goto_location(pokestop.get('latitude'), pokestop.get('longitude'), 0.5)
                if localnetwork.last_lat != 0:
                    default_CD = calculate_cooldown(localnetwork.last_lat,
                                                    localnetwork.last_lng,
                                                    pokestop.get('latitude'),
                                                    pokestop.get('longitude'))
                    if default_CD < 4.0:
                        default_CD = 4.0  # need min 4 secs to hit pokestops
                logger.info('Cooldown timing: {}'.format(default_CD))
                await asyncio.sleep(default_CD)
                # Some how day and night affect how the game detect it's points.....
                await tap_screen(self.p, 546, 1173, 0.5)
                im_rgb = await screen_cap(self.d)
                if is_home_page(im_rgb):
                    await tap_screen(self.p, 546, 1243, 0.5)

                # await tap_screen(self.p, 546, 1173, 0.1) # old value 1243
                # await tap_screen(self.p, 546, 1243, 0.1) # old value 1243
                localnetwork.last_lat = last_active_location['latitude']
                localnetwork.last_lng = last_active_location['longitude']

            await asyncio.sleep(1.5)  # wait for networkdata
            if len(localnetwork.fort) > 0:
                self.trivial_page_count = 0
                logger.info('Hit a pokestop')
                localnetwork.fort.pop(0)
                if len(localnetwork.pokestop_spin_result) > 0:
                    spin_result_status = localnetwork.pokestop_spin_result.pop()
                    logger.info("Pokestop spinned")
                    if spin_result_status.get('result') == 'INVENTORY_FULL':
                        localnetwork.mode = 1
                    localnetwork.pokestop_spin_result[:] = []
                localnetwork.hitPokestopCount += 1
                if len(localnetwork.wild) > 0:
                    localnetwork.wild.pop(0)

                if len(localnetwork.incident) > 0:
                    await asyncio.sleep(2.0)  # Wait for correct screenshot
                    im_rgb = await screen_cap(self.d)  # Screenshot is called to see which page of team rocket we are at now
                    team_go_rocket = is_team_rocket_page(im_rgb)
                    logger.debug(localnetwork.incident)
                    localnetwork.incident[:] = []
                    await asyncio.sleep(4.0)
                    self.trivial_page_count = 0
                    if team_go_rocket == 'rocket_collect':
                        await tap_screen(self.p, 540, 1715, 1.0)
                        return 'on_team_rocket'
                    if team_go_rocket == 'rocket_equip':
                        await tap_screen(self.p, 540, 1540, 3.0)
                        return 'on_team_rocket'

                    result = await fight_team_rocket(self.p, self.d, team_go_rocket)
                    if result:
                        # catch shadow pokemon
                        self.pokemon.type = 'shadow'
                        im_rgb = await screen_cap(self.d)
                        try:
                            self.pokemon.update_stats_from_catch_screen(im_rgb)
                            if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                                await asyncio.sleep(1)
                                # await tap_exit_btn(self.p) # Flee
                                self.d.press("back")
                                localnetwork.encounter[:] = []
                                return 'on_pokemon'
                        except:
                            pass

                        if not self.pokemon.shiny or Unknown.is_(self.pokemon.name) or Unknown.is_(self.pokemon.cp):
                            im_rgb = await screen_cap(self.d)
                            save_screenshot(im_rgb, sub_dir='encounter', save=self.config['screenshot'].get('encounter'))
                            self.pokemon.update_stats_from_catch_screen(im_rgb)

                            if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                                await asyncio.sleep(1)
                                # await tap_exit_btn(self.p) # Flee
                                self.d.press("back")
                                localnetwork.encounter[:] = []

                                return 'on_pokemon'

                        if self.pokemon.shiny:
                            save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
                        if is_catch_pokemon_page(im_rgb, is_shadow=True):
                            pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                            if pokemon_caught == 'No Ball':
                                localnetwork.total_ball_count = 0
                                localnetwork.mode = 0
                            if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                                self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                                if pokemon_caught != 'No Ball':
                                    await asyncio.sleep(1)
                                    await fav_last_caught(self.p, self.d, self.pokemon)
                                    await asyncio.sleep(1)

                if localnetwork.pokemon_inventory_full:
                    if self.config['poke_management'].get('enable_poke_management', False):
                        self.trivial_page_count = 0
                        im_rgb = await screen_cap(self.d)
                        if is_pokemon_full(im_rgb):
                            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                            await clear_pokemon_inventory(self.p, self.d)
                            if not self.config['poke_management'].get('mass_transfer', False):
                                # Take a long time to clear. Delete all wild and let new ones come in
                                localnetwork.wild[:] = []
                        elif is_home_page(im_rgb):
                            await tap_pokeball_btn(self.p)
                            await tap_open_pokemon_btn(self.p, 2)
                            await clear_pokemon_inventory(self.p, self.d)
                            if not self.config['poke_management'].get('mass_transfer', False):
                                # Take a long time to clear. Delete all wild and let new ones come in
                                localnetwork.wild[:] = []
                        localnetwork.pokemon_inventory_full = False
                        return 'on_poke_management'

                if not self.config['client'].get('instant_spin'):
                    if not self.config['spin_pokestop']:
                        await tap_close_btn(self.p)
                    await spin_pokestop(self.p, self.d)

                return 'on_pokestop'

            im_rgb = await screen_cap(self.d)  # Manual in case didn't get data from network
            if is_catch_pokemon_page(im_rgb):
                if self.config['discord'].get('notify_all_encountered', False) and self.config['discord'].get('enabled', False):
                    report_encounter(self.p, self.d, self.pokemon, self.device_id, pgsharp_client)
                self.trivial_page_count = 0
                self.pokemon.update_stats_from_catch_screen(im_rgb)
                if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                    await asyncio.sleep(1)
                    # await tap_exit_btn(self.p) # Flee
                    self.d.press("back")
                    localnetwork.encounter[:] = []
                    return 'on_pokemon'
                # Catch it the normal way
                pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, localnetwork, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                if pokemon_caught == 'No Ball':
                    localnetwork.total_ball_count = 0
                    localnetwork.mode = 0
                if pokemon_caught and not self.config['client'].get('transfer_on_catch', False):
                    self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                    if pokemon_caught != 'No Ball':
                        await asyncio.sleep(1)
                        await fav_last_caught(self.p, self.d, self.pokemon)
                        await asyncio.sleep(1)
                # if pokemon_caught:
                #    wildEncounterIndex = localnetwork.check_duplicate(localnetwork.wild,'encounterId',encounterId)
                #    wildPokeData = localnetwork.wild.pop(0)
                    # self.pokemon.update_stats_from_polygon(encounterPokeData)
                localnetwork.hitPokestopCount = 0

                if localnetwork.items and localnetwork.mode == 0 and localnetwork.total_ball_count >= self.config['catch'].get('resume_at_ball', 100):
                    localnetwork.mode = 1

                # reset both wild and encounter because a lot of old data when going from pokestops to pokestops
                localnetwork.wild[:] = []
                localnetwork.encounter[:] = []

                if localnetwork.items and localnetwork.mode == 0 and localnetwork.total_ball_count >= self.config['catch'].get('resume_at_ball', 100):
                    logger.info('Resuming Catching Mode...')
                    localnetwork.mode = 1
                return 'on_pokemon'

            if is_pokemon_full(im_rgb) and self.config.get('poke_management'):
                if self.config['poke_management'].get('enable_poke_management', False):
                    self.trivial_page_count = 0
                    await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                    await clear_pokemon_inventory(self.p, self.d)
                    if not self.config['poke_management'].get('mass_transfer', False):
                        localnetwork.wild[:] = []  # Take a long time to clear. Delete all wild and let new ones come in
                    return 'on_poke_management'

            if len(localnetwork.gym) > 0:
                self.trivial_page_count = 0
                logger.info('Hit a Gym')
                im_rgb = await screen_cap(self.d)  # Double check as we are tapping multiple times
                if is_gym_page(im_rgb):
                    localnetwork.gym.pop(0)
                    self.trivial_page_count = 0
                    await asyncio.sleep(4)
                    self.d.press("back")

                if len(localnetwork.gym) > 0:
                    localnetwork.gym.pop(0)
                localnetwork.hitPokestopCount += 1  # consider it as hitting pokestop, so that bot can move on
                if len(localnetwork.wild) > 0:
                    localnetwork.wild.pop(0)
                await asyncio.sleep(4)
                await tap_close_btn(self.p)
                return 'on_gym'

            if is_egg_hatched_oh(im_rgb):
                self.trivial_page_count = 0
                await asyncio.sleep(2.0)
                logger.info('Egg Hatched!')
                await tap_screen(self.p, 540, 1190, 0.5)
                if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                    await asyncio.sleep(5.0)
                im_rgb = await screen_cap(self.d)
                if is_mon_details_page(im_rgb):
                    await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                # put on a new egg
                im_rgb = await screen_cap(self.d)
                if is_egg_hatched_page(im_rgb):
                    await select_egg(self.p)
                    await tap_incubate(self.p)
                return 'on_egg'

            if is_mon_details_page(im_rgb):
                self.trivial_page_count = 0
                await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                # put on a new egg
                im_rgb = await screen_cap(self.d)
                if is_egg_hatched_page(im_rgb):
                    await select_egg(self.p)
                    await tap_incubate(self.p)
                return 'on_egg'

            team_go_rocket = is_team_rocket_page(im_rgb)
            if team_go_rocket:
                self.trivial_page_count = 0
                if team_go_rocket == 'rocket_collect':
                    await tap_screen(self.p, 540, 1715, 1.0)
                    return 'on_team_rocket'
                if team_go_rocket == 'rocket_equip':
                    await tap_screen(self.p, 540, 1540, 3.0)
                    return 'on_team_rocket'

                result = await fight_team_rocket(self.p, self.d, team_go_rocket)
                if result:
                    # catch shadow pokemon
                    self.pokemon.type = 'shadow'
                    im_rgb = await screen_cap(self.d)
                    self.pokemon.update_stats_from_catch_screen(im_rgb)
                    if self.config['catch'].get('only_shiny', False) and not self.pokemon.shiny:
                        await asyncio.sleep(1)
                        # await tap_exit_btn(self.p) # Flee
                        self.d.press("back")
                        localnetwork.encounter[:] = []
                        return 'on_pokemon'

                    if self.pokemon.shiny:
                        save_screenshot(im_rgb, sub_dir='shiny', save=self.config['screenshot'].get('shiny'))
                    if is_catch_pokemon_page(im_rgb, is_shadow=True):
                        pokemon_caught = await catch_pokemon(self.p, self.d, self.pokemon, rab_runtime_status=rab_runtime_status, device_id=self.device_id)
                        if pokemon_caught == 'No Ball':
                            localnetwork.total_ball_count = 0
                            localnetwork.mode = 0
                        if (pokemon_caught and not self.config['client'].get('transfer_on_catch', False)):
                            self.pokemon = await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                        if (pokemon_caught and self.config['client'].get('transfer_on_catch', False)):
                            if pokemon_caught != 'No Ball':
                                await asyncio.sleep(1)
                                await fav_last_caught(self.p, self.d, self.pokemon)
                                await asyncio.sleep(1)
                        # clear this list as this is likely triggered due to data curruption/slow network reply
                        localnetwork.incident[:] = []
                return 'on_teamrocket'

            if localnetwork.mode == 1:  # only move around if doing catching
                timeout = 20
                while True:
                    if last_active_location['latitude'] != 0 and last_active_location['longitude'] != 0:
                        logger.info('>>>>> Start moving around to load spawns >>>>>')
                        if time.time() > t0 + timeout:
                            logger.warning('Walked for {} sec.'.format(timeout))
                            break

                        await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)
                        await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)
                        await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)
                        await self.p.goto_location(last_active_location['latitude'] + random.randint(-1, 1) * amplitude, last_active_location['longitude'] + random.randint(-1, 1) * amplitude, 0.5)
                        await self.p.goto_location(last_active_location['latitude'], last_active_location['longitude'], 0.5)

                        if len(localnetwork.wild) > 0:
                            return

            # await close_team_rocket(self.p)
        # unknown error handling
        # for any new pages that are not handled, take a screenshot
        self.trivial_page_count += 1

        return

    async def develop(self):
        pass

    async def run_map_check(self):
        global localnetwork
        target = {}
        #failed_fort = {}
        failed_forts_list = []
        failed_pokestops_list = []
        summary_gym = []
        summary_pokestop = []

        # connect and get all gyms with no name
        try:
            with session2_scope() as session:
                fort_details = get_empty_forts(session)

                total_forts = len(fort_details)
                logger.info(f'Total forts retrieved: {total_forts}')

                if total_forts > 0:
                    for each_fort in fort_details:
                        logger.info(
                            f"Going to ID: {each_fort.id} Name: {each_fort.name} coord: {each_fort.lat},{each_fort.lon}")
                        target['latitude'], target['longitude'] = each_fort.lat, each_fort.lon
                        await self.p.goto_location(each_fort.lat, each_fort.lon, 1)

                        if await load_spawns(self.p, self.d, target):
                            await asyncio.sleep(3)  # wait for it to go back before tapping
                            # success, let's tap
                            await tap_screen(self.p, 540, 1160, 5)
                            if len(localnetwork.gym) > 0:
                                gym_details = localnetwork.gym.pop()
                                network_lat = gym_details['gymStatusAndDefenders']['pokemonFortProto'].get('latitude', 0)
                                network_lon = gym_details['gymStatusAndDefenders']['pokemonFortProto'].get('longitude', 0)
                                if round(each_fort.lat, 5) == round(network_lat, 5) and round(each_fort.lon, 5) == round(network_lon, 5):
                                    each_fort_id = each_fort.id
                                    # logger.info(f"{gym_details}")
                                    with session2_scope() as session2:
                                        update_forts(session2, each_fort_id, gym_details.get('name', 'UNKOWN'),
                                                     gym_details.get('url', '').replace('http', 'https'))
                                        logger.info("Updated: {}".format(gym_details.get('name', 'UNKOWN')))
                                        summary_gym.append(gym_details.get('name', 'UNKOWN'))
                                else:
                                    logger.info("Incorrect gym: {} should be: {}".format(
                                        gym_details.get('name', 'UNKOWN'), each_fort.name))
                                    failed_forts_list.append(each_fort)
                                await tap_close_btn(self.p)
                            else:
                                logger.info("Failed: {}".format(each_fort))
                                failed_forts_list.append(each_fort)
                                # update information
                                # update_forts(session, fort_id, fort_name, fort_url)

                            localnetwork.gym[:] = []
                            localnetwork.wild[:] = []
                            localnetwork.encounter[:] = []
                            if len(localnetwork.fort) > 0:
                                localnetwork.fort[:] = []
                                await tap_close_btn(self.p)
                        else:
                            logger.info("Failed to load map: {}".format(each_fort.name))
                            failed_forts_list.append(each_fort)

                        # ensure it's main map before continue
                        im_rgb = await screen_cap(self.d)
                        if not is_home_page(im_rgb):
                            i = 0
                            while True:
                                im_rgb = await screen_cap(self.d)
                                if is_home_page(im_rgb) or i == 8:
                                    break
                                elif i % 2 == 0:
                                    await tap_close_btn(self.p)
                                    i += 1
                                    await asyncio.sleep(0.5)
                                else:
                                    # send the magic button
                                    self.d.press("back")
                                    # await tap_close_btn(self.p)
                                    i += 1
                                    await asyncio.sleep(0.5)
                else:
                    logger.info("All gyms have full details")
        except Exception as e:
            logger.info("Error getting gyms without name: {}".format(e))
            return False

        # connect and get all pokestops with no name
        try:
            with session2_scope() as session:
                pokestop_details = get_empty_pokestops(session)

                total_pokestops = len(pokestop_details)
                logger.info(f'Total pokestops retrieved: {total_pokestops}')

                if total_pokestops > 0:
                    for each_pokestop in pokestop_details:
                        logger.info(
                            f"Going to ID: {each_pokestop.id} Name: {each_pokestop.name} coord: {each_pokestop.lat},{each_pokestop.lon}")
                        target['latitude'], target['longitude'] = each_pokestop.lat, each_pokestop.lon
                        await self.p.goto_location(each_pokestop.lat, each_pokestop.lon, 1)

                        if await load_spawns(self.p, self.d, target):
                            # success, let's tap
                            await asyncio.sleep(3)  # wait for it to go back before tapping
                            await tap_screen(self.p, 540, 1160, 5)
                            if len(localnetwork.fort) > 0:
                                pokestop_details = localnetwork.fort.pop()
                                # logger.info(f"{pokestop_details}")
                                network_lat = pokestop_details.get('latitude', 0)
                                network_lon = pokestop_details.get('longitude', 0)
                                if round(each_pokestop.lat, 5) == round(network_lat, 5) and round(each_pokestop.lon, 5) == round(network_lon, 5):
                                    each_pokestop_id = each_pokestop.id
                                    with session2_scope() as session2:
                                        update_pokestops(session2, each_pokestop_id, pokestop_details.get(
                                            'name', 'UNKOWN'), pokestop_details['imageUrl'][0].replace('http', 'https'))
                                        logger.info("Updated: {}".format(pokestop_details.get('name', 'UNKOWN')))
                                        summary_pokestop.append(pokestop_details.get('name', 'UNKOWN'))
                                else:
                                    logger.info("Incorrect Pokestop: {}".format(pokestop_details.get('name', 'UNKOWN')))
                                    failed_pokestops_list.append(each_pokestop)
                                await tap_close_btn(self.p)
                            else:
                                logger.info("Failed: {}".format(each_pokestop))
                                failed_pokestops_list.append(each_pokestop)
                                # update information
                                # update_forts(session, fort_id, fort_name, fort_url)

                            localnetwork.fort[:] = []
                            localnetwork.wild[:] = []
                            localnetwork.encounter[:] = []
                            if len(localnetwork.gym) > 0:
                                localnetwork.gym[:] = []
                                await tap_close_btn(self.p)
                        else:
                            logger.info("Failed to load map: {}".format(each_pokestop.name))
                            failed_pokestops_list.append(each_pokestop)

                        # ensure it's main map before continue
                        im_rgb = await screen_cap(self.d)
                        if not is_home_page(im_rgb):
                            i = 0
                            while True:
                                im_rgb = await screen_cap(self.d)
                                if is_home_page(im_rgb) or i == 8:
                                    break
                                elif i % 2 == 0:
                                    await tap_close_btn(self.p)
                                    i += 1
                                    await asyncio.sleep(0.5)
                                else:
                                    # send the magic button
                                    self.d.press("back")
                                    # await tap_close_btn(self.p)
                                    i += 1
                                    await asyncio.sleep(0.5)
                else:
                    logger.info("All pokestops have full details")
        except Exception as e:
            logger.info("Error getting pokestops without name: {}".format(e))
            return False

        logger.info("---Data Collection Summary---")
        logger.info("Total Gyms failed: {}".format(len(failed_forts_list)))
        logger.info("{}\n\n".format(failed_forts_list))
        logger.info("Total Pokestops failed: {}".format(len(failed_pokestops_list)))
        logger.info("{}\n\n".format(failed_pokestops_list))

        logger.info("Total Gyms added: {}".format(len(summary_gym)))
        logger.info("{}\n\n".format(summary_gym))

        logger.info("Total Pokestops added: {}".format(len(summary_pokestop)))
        logger.info("{}\n\n".format(summary_pokestop))
        return True

    async def reset_app(self):
        global rab_runtime_status
        global spawns_to_check

        webhook_url = self.config['discord'].get('webhook_url', '')

        logger.info('Attempt to restart Pokemon Go')
        if webhook_url and self.config['discord'].get('enabled', False) and self.config['discord'].get('restart', True):
            send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id), 'Attempt to restart Pokemon Go...')
        self.d.app_stop("com.nianticlabs.pokemongo")
        await asyncio.sleep(10)
        spawns_to_check[:] = []  # Clear list

        # This is for polygon
        if 'polygon' in self.config['client'].get('client', '').lower():
            self.d.app_start("com.evermorelabs.polygonsharp", use_monkey=True)
            pid = self.d.app_wait("com.evermorelabs.polygonsharp")
            logger.info("Starting Polygon#...")
            if not pid:
                logger.error("Polygon Sharp is not running. Exiting...")
                if webhook_url and self.config['discord'].get('enabled', False):
                    send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id),
                                    'An Error has occoured while trying to start Polygon Sharp')
                cleanup()
            else:
                self.d.app_wait("com.evermorelabs.polygonsharp", front=True)
                await asyncio.sleep(2)
                logger.info("Polygon Sharp is running...")
                if self.d(text="STOP").exists:
                    self.d(text="STOP").click()
                    await asyncio.sleep(1.5)
                if self.d(text="START").exists:
                    self.d(text="START").click()
                    await asyncio.sleep(6)
                # self.d.press("enter")
                # await asyncio.sleep(1.5)
                # self.d.press("down")
                # await asyncio.sleep(1.5)
                # self.d.press("enter")
                # await asyncio.sleep(1.5)
                # self.d.press("up")
                # await asyncio.sleep(1.5)
                # self.d.press("enter")

        # This is for HAL
        if 'hal' in self.config['client'].get('client', '').lower():
            self.d.app_start("com.pokemod.hal.public", use_monkey=True)
            pid = self.d.app_wait("com.pokemod.hal.public")
            logger.info("Starting HAL...")
            if not pid:
                logger.error("Pokemod HAL is not running. Exiting...")
                if webhook_url and self.config['discord'].get('enabled', False):
                    send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id),
                                    'An Error has occoured while trying to start Pokemod HAL')
                cleanup()
            else:
                self.d.app_wait("com.pokemod.hal.public", front=True)
                await asyncio.sleep(2)
                logger.info("Pokemod HAL is running...")
                if self.d(text="STOP SERVICE").exists:
                    self.d(text="STOP SERVICE").click()
                    await asyncio.sleep(1.5)
                if self.d(text="START SERVICE").exists:
                    self.d(text="START SERVICE").click()
                    await asyncio.sleep(6)
                #'START SERVICE'
                #'STOP SERVICE'
                # self.d.press("enter") # focus
                # await asyncio.sleep(1.5)
                # self.d.press("enter") # Stop service
                # await asyncio.sleep(1.5)
                # self.d.press("enter") # Start service

        # This is for Espresso
        if 'pokemod' in self.config['client'].get('client', '').lower():
            self.d.app_start("com.pokemod.espresso", use_monkey=True)
            pid = self.d.app_wait("com.pokemod.espresso")
            logger.info("Starting Pokemod Espresso...")
            if not pid:
                logger.error("Pokemod Espresso is not running. Exiting...")
                if webhook_url and self.config['discord'].get('enabled', False):
                    send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id),
                                    'An Error has occoured while trying to start Pokemod Espresso')
                cleanup()
            else:
                self.d.app_wait("com.pokemod.espresso", front=True)
                await asyncio.sleep(2)
                logger.info("Pokemod Espresso is running...")
                if self.d(text="Start Service ON").exists:
                    self.d(text="Start Service ON").click()
                    await asyncio.sleep(1.5)
                i = 0
                while True:
                    await asyncio.sleep(1)
                    if self.d(text="Start Service OFF").exists:
                        self.d(text="Start Service OFF").click()
                        await asyncio.sleep(1.5)
                        break
                    if i >= 10:
                        break
                    i += 1

                if self.d(text="LAUNCH POKÉMON GO").exists:
                    self.d(text="LAUNCH POKÉMON GO").click()
                    await asyncio.sleep(6)

        if 'mad' in self.config['client'].get('client', '').lower():
            self.d.app_start("com.mad.pogoenhancer", use_monkey=True)
            pid = self.d.app_wait("com.mad.pogoenhancer")
            logger.info("Starting MAD Enhancer...")
            if not pid:
                logger.error("MAD Enhancer is not running. Exiting...")
                if webhook_url and self.config['discord'].get('enabled', False):
                    send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id),
                                    'An Error has occoured while trying to start MAD Enhancer')
                cleanup()
            else:
                self.d.app_wait("com.mad.pogoenhancer", front=True)
                await asyncio.sleep(2)
                logger.info("MAD Enhancer is running...")
                if self.d(text="STOP").exists:
                    self.d(text="STOP").click()
                    await asyncio.sleep(1.5)
                if self.d(text="START").exists:
                    self.d(text="START").click()
                    await asyncio.sleep(6)

        if self.config['client'].get('client', '').lower() in ['pgsharp', 'pgsharp paid', 'none']:
            self.d.app_start("com.nianticlabs.pokemongo", use_monkey=True)
            pid = self.d.app_wait("com.nianticlabs.pokemongo")
            logger.info("Starting Pokemon Go...")
            await asyncio.sleep(6)

        # Extra Tap, for those users that uses dual app feature of xiaomi
        await tap_screen(self.p, 300, 1540, 1)

    async def start(self):
        global last_active_location
        global last_caught_location
        global localnetwork
        global rab_runtime_status
        global pgsharp_client
        global mad_client

        pokemon = Pokemon()
        rab_runtime_status.time_started = int(time.time())
        if await self.setup() is False:
            cleanup()
        offset = self.config['client'].get('screen_offset', 0)
        await asyncio.sleep(2.0)  # wait a while for resizing if any
        if self.develop_mode:
            # run devleop function, to easily access availible library without to test outside the project
            await self.develop()
            cleanup()

        if self.map_mode:
            # run map mode function
            localnetwork = LocalNetworkHandler(self.config['network'].get(
                'host', '0.0.0.0'), self.config['network'].get('port', 5120))
            localnetwork.config = self.config
            await self.run_map_check()
            cleanup()

        if self.config['client'].get('client', '').lower() in ['polygon paid', 'polygonpaid', 'polygon farmer', 'polygonfarmer']:
            # logger.info("Preparing Polygon# Paid Mode")
            #logger.info("Please ensure your map in ZOOM IN to the max (not zoomed out)")
            localnetwork = LocalNetworkHandler(self.config['network'].get(
                'host', '0.0.0.0'), self.config['network'].get('port', 5120))
            localnetwork.config = self.config

        if self.config['item_management'].get('clear_item_on_start', False) and self.config['item_management'].get('enable_item_management', False) and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
            await check_items(self.p, self.d, self.config)

        if self.config['item_management'].get('manage_gifts_on_start', False):
            await manage_gifts(self.p, self.d)

        if self.config['telegram'].get('enabled') and self.config['shiny_check'].get('enabled') and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
            logger.warning('SHINY CHECK IN PROGRESS, MAKE SURE INSTANT SPIN IS DISABLED (RAB & 3RD PARTY)')
            logger.warning('SHINY CHECK IN PROGRESS, MAKE SURE POKESTOP PRIORITY IS DISABLED (RAB)')
            logger.info("Start shiny checking ...")

        if self.config['client'].get('auto_goplus', False) and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
            im_rgb = await screen_cap(self.d)
            logger.info("Checking Go Plus status...")
            if is_plus_disconnected(im_rgb, offset):
                logger.info("Go Plus Disconnected, attempt to connect now....")
                await tap_screen(self.p, 990, 450, 1.0)
                logger.info("Go Plus Reconnecting...")

        # limited time features
        # Add in settings for pgsharpv2 options and add in here in future
        if self.config['client'].get('client', '').lower() in ['pgsharp', 'pgsharp paid', 'pgsharppaid']:
            #xml = self.d.dump_hierarchy()
            # with open('xml.txt', 'w') as f:
            #    f.write(xml)
            if (int(time.time()) <= self.limited_time_feature) or self.subscriber:
                pgsharp_client = PGSharp()
                logger.info("Please wait.... Checking and readjusting icons...")
                self.d.press("back")
                self.d.press("back")
                try:
                    if self.config['client'].get('pgsharp_reposition', True):
                        await pgsharp_client.reposition(self.p, self.d)
                    else:
                        pgsharp_client.feed_index = 1
                        pgsharp_client.icon_index = 0
                        pgsharp_client.joystick_index = 2
                    x, y = await pgsharp_client.get_location(self.p, self.d)
                    pgsharp_client.start_location = [x, y]
                    if not pgsharp_client.start_location:
                        logger.info("RAB is unable to get starting location, certain features might not work...")
                except:
                    pgsharp_client.feed_index = 1
                    pgsharp_client.icon_index = 0
                    pgsharp_client.joystick_index = 2

                frame_count = await pgsharp_client.get_overlay_frame_count(self.p, self.d)
                if frame_count >= 2:
                    self.pgsharpv2 = False
                    logger.info(
                        "2 or more overlay frame detected. Use Nearby Radar for Enchanced PGSharp feature of RAB. Use Quick Sniper for Shuno hunting.")
                elif frame_count == 1:
                    if self.config['client'].get('pgsharp_shuno_hunt', 0):
                        logger.info("Overlay frame detected. Please ensure it is Quick sniper and not Nearby Radar!")
                        logger.info("RAB will now run in PGSharp 100IV Hunting Mode")
                        if not self.subscriber:
                            logger.info("PGSharp 100IV Hunting Mode is a limited time trial feature and will expire on: {}".format(
                                datetime.fromtimestamp(self.limited_time_feature).strftime("%d %b %Y, %H:%M:%S")))
                            logger.info("If you like this feature, do consider donating.")
                    else:
                        logger.info("Overlay frame detected. Please ensure it is Nearby Radar and not Quick sniper!")
                        logger.info("RAB will now run in Enchanced PGSharp Mode")
                        logger.info(
                            "Note: Enchanced PGSharp feature of RAB might not work for all phones, if it doesn't work for you, disable Nearby Radar and fall back to normal mode.")
                        # if not self.subscriber:
                        #    logger.info("Enchanced PGSharp Mode is a limited time trial feature and will expire on: {}".format(datetime.fromtimestamp(self.limited_time_feature).strftime("%d %b %Y, %H:%M:%S")))
                        #    logger.info("If you like this feature, do consider donating.")
                    self.pgsharpv2 = True
                    pgsharp_client.nearby_count = await pgsharp_client.get_nearby_count(self.p, self.d)
                else:
                    if self.config['client'].get('pgsharp_shuno_hunt', 0):
                        logger.info(
                            "No overlay frame detected for PGSharp. Please enable Quick sniper to enable PGSharp 100IV Hunting feature of RAB.")
                    else:
                        logger.info(
                            "No overlay frame detected for PGSharp. Please enable Nearby Radar to enable Enchanced PGSharp feature of RAB.")
                    self.pgsharpv2 = False
            else:
                pgsharp_client = PGSharp()
                logger.info("Please wait.... Checking and readjusting icons...")
                try:
                    if self.config['client'].get('pgsharp_reposition', True):
                        await pgsharp_client.reposition(self.p, self.d)
                    else:
                        pgsharp_client.feed_index = 1
                        pgsharp_client.icon_index = 0
                        pgsharp_client.joystick_index = 2
                    x, y = await pgsharp_client.get_location(self.p, self.d)
                    pgsharp_client.start_location = [x, y]
                    if not pgsharp_client.start_location:
                        logger.info("RAB is unable to get starting location, certain features might not work...")
                except:
                    pgsharp_client.feed_index = 1
                    pgsharp_client.icon_index = 0
                    pgsharp_client.joystick_index = 2

                frame_count = await pgsharp_client.get_overlay_frame_count(self.p, self.d)
                if frame_count >= 2:
                    self.pgsharpv2 = False
                    logger.info("2 or more overlay frame detected. Use Nearby Radar for Enchanced PGSharp feature of RAB.")
                elif frame_count == 1:
                    if self.config['client'].get('pgsharp_shuno_hunt', 0):
                        logger.info("100IV PGSharp hunting is only availible for donors")
                    else:
                        logger.info("Overlay frame detected. Please ensure it is Nearby Radar and not Quick sniper!")
                        logger.info("RAB will now run in Enchanced PGSharp Mode")
                        logger.info(
                            "Note: Enchanced PGSharp feature of RAB might not work for all phones, if it doesn't work for you, disable Nearby Radar and fall back to normal mode.")
                        # if not self.subscriber:
                        #    logger.info("Enchanced PGSharp Mode is now free for all users.")
                        self.pgsharpv2 = True
                        pgsharp_client.nearby_count = await pgsharp_client.get_nearby_count(self.p, self.d)
                else:
                    if self.config['client'].get('pgsharp_shuno_hunt', 0):
                        logger.info("100IV PGSharp hunting is only availible for donors")
                    else:
                        logger.info(
                            "No overlay frame detected for PGSharp. Enable Nearby Radar to enable Enchanced PGSharp feature of RAB.")
                    self.pgsharpv2 = False

        await self.update_location(save_file=True)

        if self.config['client'].get('client', '').lower() in ['mad']:
            mad_client = MADClass()

        if self.config['quest'].get('enable_check_quest', False) and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
            im_rgb = await screen_cap(self.d)
            if not is_home_page(im_rgb):
                i = 0
                while True:
                    im_rgb = await screen_cap(self.d)
                    if is_home_page(im_rgb) or i == 8:
                        self.trivial_page_count = 0
                        break
                    elif i % 2 == 0:
                        await tap_close_btn(self.p)
                        i += 1
                        await asyncio.sleep(0.5)
                    else:
                        # send the magic button
                        self.d.press("back")
                        # await tap_close_btn(self.p)
                        i += 1
                        await asyncio.sleep(0.5)
            logger.info("Checking and clearing quest....")
            await tap_screen(self.p, 986, 1592, 3.0)
            await tap_screen(self.p, 540, 390, 3.0)
            await clear_quest(self.d, self.p, pokemon)
            await tap_close_btn(self.p)
            await asyncio.sleep(1)

        if self.config['poke_management'].get('enable_poke_management', False) and self.config['poke_management'].get('manage_poke_on_start', False) and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
            await asyncio.sleep(1)
            im_rgb = await screen_cap(self.d)
            if is_home_page(im_rgb):
                await tap_pokeball_btn(self.p)
            await tap_open_pokemon_btn(self.p, 2)
            await clear_pokemon_inventory(self.p, self.d, pgsharp_client=pgsharp_client, mad_client=mad_client)

        while True:
            appInfor = self.d.app_current()  # Quit RAB if Pokemon Go is not found
            if not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
                if appInfor['package'] != 'com.nianticlabs.pokemongo':
                    await self.reset_app()
                    logger.info("Restarting App because pokemon go is not found: {}".format(appInfor['package']))
                    webhook_url = self.config['discord'].get('webhook_url', '')
                    self.d.app_wait("com.nianticlabs.pokemongo", front=True)
                    sleep_time = 60 if self.config['client'].get('client', '').lower() != 'mad' else 90
                    logger.info(f'Pokemon Go App started, waiting for {sleep_time} secs to login...')
                    await asyncio.sleep(sleep_time)
                    im_rgb = await screen_cap(self.d)
                    if not is_home_page(im_rgb):
                        if is_warning_page(im_rgb):
                            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                            await asyncio.sleep(3)
                        im_rgb = await screen_cap(self.d)
                        if not is_home_page(im_rgb):
                            self.d.press("back")
                            await asyncio.sleep(2)

                    im_rgb = await screen_cap(self.d)
                    i = 0
                    if not is_home_page(im_rgb):
                        while True:
                            im_rgb = await screen_cap(self.d)
                            if is_home_page(im_rgb) or i == 8:
                                break
                            elif i % 2 == 0:
                                await tap_close_btn(self.p)
                                i += 1
                                await asyncio.sleep(0.5)
                            else:
                                # send the magic button
                                self.d.press("back")
                                # await tap_close_btn(self.p)
                                i += 1
                                await asyncio.sleep(0.5)

                    if is_home_page(im_rgb):
                        if webhook_url and self.config['discord'].get('enabled', False) and self.config['discord'].get('restart', True):
                            send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id),
                                            'Pokemon Go restarted. Resume scanning...')
                        im_rgb = await screen_cap(self.d)
                        if config['client'].get('zoom_option', 'Pinch In'):
                            self.d(packageName='com.nianticlabs.pokemongo').pinch_in(percent=60, steps=40)
                        else:
                            self.d(packageName='com.nianticlabs.pokemongo').pinch_out(percent=70, steps=40)
                        if pgsharp_client:
                            try:
                                if self.config['client'].get('pgsharp_reposition', True):
                                    await pgsharp_client.reposition(self.p, self.d)
                                else:
                                    pgsharp_client.feed_index = 1
                                    pgsharp_client.icon_index = 0
                                    pgsharp_client.joystick_index = 2
                                x, y = await pgsharp_client.get_location(self.p, self.d)
                                pgsharp_client.start_location = [x, y]
                                if not pgsharp_client.start_location:
                                    logger.info("RAB is unable to get starting location, certain features might not work...")
                            except:
                                pgsharp_client.feed_index = 1
                                pgsharp_client.icon_index = 0
                                pgsharp_client.joystick_index = 2

            last_status = 'Something Else'  # Use this to skip take screenshot for polygon to speed it up going from location to location
            # Assuming screen starts at main map, check for pokemon
            pokemon = Pokemon()

            try:
                # if localnetwork:
                #    # save it as last location before moving to new loaction
                #    await self.update_location()
                #    if self.config['client'].get('client','').lower() in ['polygon paid', 'polygonpaid', 'polygon farmer', 'polygonfarmer'] and last_active_location['latitude'] == 0:
                #        if last_active_location['latitude'] == 0:
                #            last_active_location['latitude'] = last_active_location['latitude']
                #            last_active_location['longitude'] = last_active_location['longitude']
                #    logger.info('Network Location: ({},{})'.format(last_active_location['latitude'],last_active_location['longitude']))
                #    logger.info('GPX Location: ({},{})'.format(last_active_location['latitude'],last_active_location['longitude']))
                # if not self.config['client'].get('client','').lower() in ['polygon paid', 'polygonpaid', 'polygon farmer', 'polygonfarmer', 'pgsharp', 'pgsharp paid', 'pgsharppaid']:
                if pgsharp_client:
                    await pgsharp_client.close_pgsharp_menu(self.p, self.d)

                if self.config['client'].get('client', '').lower() in ['pgsharp', 'pgsharp paid'] and last_active_location.get('latitude', 0) == 0 and self.config['client'].get('pgsharp_shuno_hunt', 0):
                    await self.update_location()
                if not (self.config['client'].get('client', '').lower() in ['pgsharp', 'pgsharp paid']):
                    await self.update_location()

                if self.config['telegram'].get('enabled', False) and self.config['snipe'].get('enabled', False):
                    await self.snipe()

                # Check if it's time to clear quest
                time_diff = int(time.time()) - self.track_quest_time
                if time_diff >= self.config['quest'].get('clear_quest_interval', 10) * 60 and self.config['quest'].get('enable_check_quest', False) and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
                    # check it's home page before clearing...
                    im_rgb = await screen_cap(self.d)
                    if not is_home_page(im_rgb):
                        if is_egg_hatched_oh(im_rgb):
                            self.trivial_page_count = 0
                            await asyncio.sleep(2.0)
                            logger.info('Egg Hatched!')
                            await tap_screen(self.p, 540, 1190, 0.5)
                            if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                                await asyncio.sleep(5.0)
                            im_rgb = await screen_cap(self.d)
                            if is_mon_details_page(im_rgb):
                                await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            # put on a new egg
                            im_rgb = await screen_cap(self.d)
                            if is_egg_hatched_page(im_rgb):
                                await select_egg(self.p)
                                await tap_incubate(self.p)

                        if is_mon_details_page(im_rgb):
                            self.trivial_page_count = 0
                            await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            # put on a new egg
                            im_rgb = await screen_cap(self.d)
                            if is_egg_hatched_page(im_rgb):
                                await select_egg(self.p)
                                await tap_incubate(self.p)
                            self.no_action_count = 0

                        if is_egg_hatched_page(im_rgb):
                            await select_egg(self.p)
                            await tap_incubate(self.p)

                        # prevent bot from hang at this page
                        text = extract_text_from_image(im_rgb)
                        if any(x in text for x in ['component', 'collect', 'radar', 'assemble', 'equip']):
                            save_screenshot(im_rgb, sub_dir='rocket', save=False)
                            # collect i/6 component
                            await tap_collect_component(self.p)
                            logger.info('Collect component after catching shadow pokemon.')

                        # collect 6/6 components, and combine components
                        if any(x in text for x in ['enough', 'combine', 'assembled', 'team go rocket hideouts']):
                            await asyncio.sleep(1.5)
                            await tap_equip_radar(self.p)
                            logger.info('Combine radar.')

                        i = 0
                        while True:
                            im_rgb = await screen_cap(self.d)
                            if is_home_page(im_rgb) or i == 8:
                                self.trivial_page_count = 0
                                break
                            elif i % 2 == 0:
                                await tap_close_btn(self.p)
                                i += 1
                                await asyncio.sleep(0.5)
                            else:
                                # send the magic button
                                self.d.press("back")
                                # await tap_close_btn(self.p)
                                i += 1
                                await asyncio.sleep(0.5)
                    logger.info("Checking and clearing quest....")
                    await tap_screen(self.p, 986, 1592, 3.0)
                    await tap_screen(self.p, 540, 390, 3.0)
                    await clear_quest(self.d, self.p, pokemon)
                    await tap_close_btn(self.p)
                    self.track_quest_time = int(time.time())

                if self.config['item_management'].get('enable_item_management', False) and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
                    time_diff = int(time.time()) - self.track_time
                    # logger.info("Time different: {}".format(time_diff))
                    if time_diff >= self.config['item_management'].get('item_management_interval', 60) * 60:
                        self.track_time = int(time.time())
                        try:
                            await check_items(self.p, self.d, self.config)
                            self.bag_full = False
                        except Exception as e:
                            # Error occurs, tap x and exit
                            await tap_screen(self.p, 540, 1780, 2)  # Close Item Page

                if self.config['item_management'].get('manage_gifts_on_start', False) and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
                    time_diff = int(time.time()) - self.track_time
                    # logger.info("Time different: {}".format(time_diff))
                    if time_diff >= self.config['item_management'].get('gift_interval', 60) * 60:
                        self.track_time = int(time.time())
                        logger.info("Managing gifts....")
                        try:
                            await manage_gifts(self.p, self.d)
                        except Exception as e:
                            # Error occurs, tap x and exit
                            await tap_screen(self.p, 540, 1780, 2)  # Close Page

                if not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
                    logger.info('')
                    logger.info('Trivial page #{}'.format(self.trivial_page_count))
                if localnetwork and not self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
                    if self.config['client'].get('auto_goplus', False):
                        time_diff = int(time.time()) - self.track_pogo_time
                        if time_diff >= (30 * 60):
                            im_rgb = await screen_cap(self.d)  # Manual in case didn't get data from network
                            self.track_pogo_time = int(time.time())
                            # Check every 30mins
                            logger.info("Checking Go Plus status...")
                            if self.config['client'].get('client', '').lower() == 'hal':
                                if is_plus_disconnected(im_rgb, offset):
                                    logger.info("Go Plus Disconnected...")
                                    await tap_screen(self.p, 990, 450, 1.0)
                                    logger.info("Go Plus Reconnecting...")
                            else:
                                if is_plus_disconnected(im_rgb, offset):
                                    logger.info("Go Plus Disconnected...")
                                    await tap_screen(self.p, 990, 450, 1.0)
                                    logger.info("Attempting to reconnect...")
                                else:
                                    logger.info(
                                        "Go Plus is still connecting. Attempt to disconnect and reconnect to prolong Go Plus connection...")
                                    await tap_screen(self.p, 990, 450, 1.0)
                                    i = 0
                                    while True:
                                        if i == 7:
                                            break
                                        await asyncio.sleep(1)
                                        im_rgb = await screen_cap(self.d)
                                        if is_plus_disconnected(im_rgb, offset):
                                            await tap_screen(self.p, 990, 450, 1.0)
                                            logger.info("Attempting to reconnect...")
                                            break
                                        i += 1

                # if last_status != 'on_egg' or last_status != 'on_pokestop' or last_status != 'on_gym' or last_status != 'on_pokemon': # Let's appy to Polygon# first
                # Check how many times it is not map page
                if not localnetwork:
                    im_rgb = await screen_cap(self.d)  # Manual in case didn't get data from network
                    if self.config['client'].get('auto_goplus', False):
                        time_diff = int(time.time()) - self.track_pogo_time
                        if time_diff >= (30 * 60):
                            self.track_pogo_time = int(time.time())
                            # Check every 30mins
                            logger.info("Checking Go Plus status...")
                            if self.config['client'].get('client', '').lower() in ['pgsharppaid', 'pgsharp paid', 'hal']:
                                if is_plus_disconnected(im_rgb, offset):
                                    logger.info("Go Plus Disconnected...")
                                    await tap_screen(self.p, 990, 450, 1.0)
                                    logger.info("Go Plus Reconnecting...")
                            else:
                                if is_plus_disconnected(im_rgb, offset):
                                    logger.info("Go Plus Disconnected...")
                                    await tap_screen(self.p, 990, 450, 1.0)
                                    logger.info("Attempting to reconnect...")
                                else:
                                    logger.info(
                                        "Go Plus is still connecting. Attempt to disconnect and reconnect to prolong Go Plus connection...")
                                    await tap_screen(self.p, 990, 450, 1.0)
                                    i = 0
                                    while True:
                                        if i == 7:
                                            break
                                        await asyncio.sleep(1)
                                        im_rgb = await screen_cap(self.d)
                                        if is_plus_disconnected(im_rgb, offset):
                                            await tap_screen(self.p, 990, 450, 1.0)
                                            logger.info("Attempting to reconnect...")
                                            break
                                        i += 1

                    if is_weather_warning_page(im_rgb):
                        self.trivial_page_count = 0
                        await tap_caught_ok_btn(self.p, im_rgb=im_rgb)

                    if not is_home_page(im_rgb):
                        if is_warning_page(im_rgb):
                            self.trivial_page_count = 0
                            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)

                        if is_exit_trainer_dialog(im_rgb):
                            await tap_exit_trainer(self.p)

                        if is_egg_hatched_oh(im_rgb):
                            self.trivial_page_count = 0
                            await asyncio.sleep(2.0)
                            logger.info('Egg Hatched!')
                            await tap_screen(self.p, 540, 1190, 0.5)
                            if self.config['client'].get('client', '').lower() in ['none', 'pgsharp', 'pgsharp paid', 'mad']:
                                await asyncio.sleep(5.0)
                            im_rgb = await screen_cap(self.d)
                            if is_mon_details_page(im_rgb):
                                await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            # put on a new egg
                            im_rgb = await screen_cap(self.d)
                            if is_egg_hatched_page(im_rgb):
                                await select_egg(self.p)
                                await tap_incubate(self.p)

                        if is_egg_hatched_page(im_rgb):
                            await select_egg(self.p)
                            await tap_incubate(self.p)

                        if is_mon_details_page(im_rgb):
                            self.trivial_page_count = 0
                            await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            # put on a new egg
                            im_rgb = await screen_cap(self.d)
                            if is_egg_hatched_page(im_rgb):
                                await select_egg(self.p)
                                await tap_incubate(self.p)
                            self.no_action_count = 0

                        text = extract_text_from_image(im_rgb)
                        if any(x in text for x in ['component', 'collect', 'radar', 'assemble', 'equip']):
                            save_screenshot(im_rgb, sub_dir='rocket', save=False)
                            # collect i/6 component
                            await tap_collect_component(self.p)
                            logger.info('Collect component after catching shadow pokemon.')

                        # collect 6/6 components, and combine components
                        if any(x in text for x in ['enough', 'combine', 'assembled', 'team go rocket hideouts']):
                            await asyncio.sleep(1.5)
                            await tap_equip_radar(self.p)
                            logger.info('Combine radar.')

                        i = 1
                        while True:
                            im_rgb = await screen_cap(self.d)
                            result = await self.teamrocket(im_rgb)
                            if result:
                                break
                            if is_home_page(im_rgb) or i == 8:
                                self.trivial_page_count = 0
                                break
                            elif i % 2 == 0:
                                await tap_close_btn(self.p)
                                i += 1
                                await asyncio.sleep(0.5)
                            else:
                                # send the magic button
                                self.d.press("back")
                                # await tap_close_btn(self.p)
                                i += 1
                                await asyncio.sleep(0.5)

                        if is_profile_page(im_rgb) or is_pokestop_scan_page(im_rgb):  # fix the problem of keep getting stuck here
                            #logger.info('Stuck at profile page?')
                            i = 0
                            while True:
                                im_rgb = await screen_cap(self.d)
                                if is_home_page(im_rgb) or i == 4:
                                    self.trivial_page_count = 0
                                    break
                                else:
                                    # send the magic button
                                    # Back button more effective, let's deal with unable to detect home page later
                                    self.d.press("back")
                                    # await tap_close_btn(self.p)
                                    i += 1
                                    await asyncio.sleep(1)

                        if is_catch_pokemon_page(im_rgb):
                            # No idea why here.... just use back button to quit
                            self.d.press("back")

                        if is_egg_hatched_page(im_rgb):
                            self.trivial_page_count = 0
                            await asyncio.sleep(2.0)
                            logger.info('Egg Hatched!')
                            await tap_screen(self.p, 540, 1190, 0.5)
                            await after_pokemon_caught(self.p, self.d, self.pokemon, self.config)
                            # put on a new egg
                            im_rgb = await screen_cap(self.d)
                            if is_egg_hatched_page(im_rgb):
                                await select_egg(self.p)
                                await tap_incubate(self.p)

                        if is_warning_page(im_rgb):
                            self.trivial_page_count = 0
                            await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                            await asyncio.sleep(0.75)
                            im_rgb = await screen_cap(self.d)
                            if not is_home_page(im_rgb):
                                self.d.press("back")

                if (self.config['telegram'].get('enabled') and self.config['shiny_check'].get('enabled')) or (self.config['client'].get('pgsharp_shuno_hunt', 0) and self.pgsharpv2):
                    result = await self.shiny_check()
                    if result == 'not_shiny':
                        # await tap_exit_btn(self.p) # Flee
                        self.d.press("back")
                        if (self.no_spawn_count >= 3) or (self.no_spawn_count >= 2 and self.pgsharpv2):
                            await self.reset_app()
                            logger.info("Restarting App because there are no spawn for detected for {} times".format(
                                self.no_spawn_count))
                            webhook_url = self.config['discord'].get('webhook_url', '')
                            self.d.app_wait("com.nianticlabs.pokemongo", front=True)
                            sleep_time = 60 if self.config['client'].get('client', '').lower() != 'mad' else 90
                            logger.info(f'Pokemon Go App started, waiting for {sleep_time} secs to login...')
                            await asyncio.sleep(sleep_time)
                            im_rgb = await screen_cap(self.d)
                            if not is_home_page(im_rgb):
                                if is_warning_page(im_rgb):
                                    await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                                    await asyncio.sleep(3)
                                im_rgb = await screen_cap(self.d)
                                if not is_home_page(im_rgb):
                                    self.d.press("back")
                                    await asyncio.sleep(2)
                            im_rgb = await screen_cap(self.d)
                            i = 0
                            if not is_home_page(im_rgb):
                                while True:
                                    im_rgb = await screen_cap(self.d)
                                    if is_home_page(im_rgb) or i == 8:
                                        break
                                    elif i % 2 == 0:
                                        await tap_close_btn(self.p)
                                        i += 1
                                        await asyncio.sleep(0.5)
                                    else:
                                        # send the magic button
                                        self.d.press("back")
                                        # await tap_close_btn(self.p)
                                        i += 1
                                        await asyncio.sleep(0.5)
                            if is_home_page(im_rgb):
                                if webhook_url and self.config['discord'].get('enabled', False) and self.config['discord'].get('restart', True):
                                    send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id),
                                                    'Pokemon Go restarted. Resume scanning...')
                                im_rgb = await screen_cap(self.d)
                                if config['client'].get('zoom_option', 'Pinch In'):
                                    self.d(packageName='com.nianticlabs.pokemongo').pinch_in(percent=60, steps=40)
                                else:
                                    self.d(packageName='com.nianticlabs.pokemongo').pinch_out(percent=70, steps=40)
                                if pgsharp_client:
                                    try:
                                        if self.config['client'].get('pgsharp_reposition', True):
                                            await pgsharp_client.reposition(self.p, self.d)
                                        else:
                                            pgsharp_client.feed_index = 1
                                            pgsharp_client.icon_index = 0
                                            pgsharp_client.joystick_index = 2
                                        x, y = await pgsharp_client.get_location(self.p, self.d)
                                        pgsharp_client.start_location = [x, y]
                                        if not pgsharp_client.start_location:
                                            logger.info(
                                                "RAB is unable to get starting location, certain features might not work...")
                                    except:
                                        pgsharp_client.feed_index = 1
                                        pgsharp_client.icon_index = 0
                                        pgsharp_client.joystick_index = 2

                            self.no_spawn_count = 0

                    if len(spawns_to_check) == 0:
                        await asyncio.sleep(1.0)
                elif self.config['client'].get('client', '').lower() in ['polygon paid', 'polygonpaid']:
                    if localnetwork.pokemon_inventory_full:
                        if self.config['poke_management'].get('enable_poke_management', False):
                            im_rgb = await screen_cap(self.d)
                            if is_pokemon_full(im_rgb):
                                await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                                await clear_pokemon_inventory(self.p, self.d)
                                if not self.config['poke_management'].get('mass_transfer', False):
                                    # Take a long time to clear. Delete all wild and let new ones come in
                                    localnetwork.wild[:] = []
                            elif is_home_page(im_rgb):
                                await tap_pokeball_btn(self.p)
                                await tap_open_pokemon_btn(self.p, 2)
                                await clear_pokemon_inventory(self.p, self.d)
                                if not self.config['poke_management'].get('mass_transfer', False):
                                    # Take a long time to clear. Delete all wild and let new ones come in
                                    localnetwork.wild[:] = []
                            localnetwork.pokemon_inventory_full = False
                            # return 'on_poke_management'
                    last_status = await self.polygon()
                    # if last_status != 'on_egg' or last_status != 'on_pokestop' or last_status != 'on_gym' or last_status != 'on_pokemon':
                    #    await asyncio.sleep(1)
                elif self.config['client'].get('client', '').lower() in ['polygon farmer', 'polygonfarmer']:
                    last_status = await self.farmer()
                    await asyncio.sleep(1.0)
                else:
                    no_spawn = False
                    if pgsharp_client:
                        if pgsharp_client.nearby_count == 0 and not self.config['client'].get('auto_route', True):
                            no_spawn = True
                            logger.info(f'RAB will attempt to walk...')
                        if self.config['client'].get('auto_route', True):
                            no_spawn = False

                    if (self.config['client'].get('client', '').lower() == 'pgsharp' and not self.config['client'].get('auto_route', True)) or no_spawn:
                        if (not self.pgsharpv2) or no_spawn:
                            while True:
                                if self.flip_switch == 0:
                                    min_x = 90
                                    max_x = 980
                                    min_y = 200
                                    max_y = 815
                                    x_steps = 8
                                    y_steps = 8
                                    self.flip_switch = 1
                                elif self.flip_switch == 1:
                                    min_x = 980
                                    max_x = 90
                                    min_y = 815
                                    max_y = 200
                                    x_steps = -8
                                    y_steps = -8
                                    self.flip_switch = 2
                                elif self.flip_switch == 2:
                                    min_x = 90
                                    max_x = 980
                                    min_y = 815
                                    max_y = 200
                                    x_steps = 8
                                    y_steps = -8
                                    self.flip_switch = 3
                                elif self.flip_switch == 3:
                                    min_x = 980
                                    max_x = 90
                                    min_y = 200
                                    max_y = 815
                                    x_steps = -8
                                    y_steps = 8
                                    self.flip_switch = 0

                                im_rgb = await screen_cap(self.d)
                                pokefound, x, y = walk_towards_pokestops(im_rgb)

                                if pokefound:
                                    if not is_not_pokestop_gym_on_map(im_rgb, x, y):
                                        # double check again
                                        pokefound = False

                                    for each_location in self.repeated_coords:
                                        if ((x - 25) <= each_location[0] <= (x + 25)) and ((y - 25) <= each_location[1] <= (y - 25)):
                                            pokefound = False

                                    if pokefound and self.count_gym_count >= 2:
                                        tmp_coord = [x, y]
                                        if len(self.repeated_coords) > 10:
                                            self.repeated_coords.pop(0)
                                        self.repeated_coords.append(tmp_coord)
                                        self.count_gym_count = 0

                                if not pokefound:
                                    x1, y1 = resize_coords(1040, 860)
                                    x2, y2 = resize_coords(1040, 1060)
                                    self.d.swipe(x1, y1, x2, y2, 0.5)
                                    while True:
                                        x = random.randrange(415, 680)
                                        if self.manual_direction == 0:
                                            y = random.randrange(1040, 1150)
                                        else:
                                            y = random.randrange(1310, 1535)
                                        if is_not_pokestop_gym_on_map(im_rgb, x, y):
                                            break

                                    self.manual_steps += 1
                                    if self.manual_steps >= 50:
                                        if self.manual_direction == 0:
                                            self.manual_direction = 1
                                        else:
                                            self.manual_direction == 0
                                        self.manual_steps = 0

                                await tap_screen(self.p, x, y, 0.5)
                                await asyncio.sleep(1.5)
                                im_rgb = await screen_cap(self.d)
                                if is_home_page(im_rgb):
                                    break
                                # if not home, get out to prevent double click
                                i = 0
                                while True:
                                    im_rgb = await screen_cap(self.d)
                                    if is_home_page(im_rgb) or i == 5:
                                        self.trivial_page_count = 0
                                        break
                                    else:
                                        # send the magic button
                                        self.d.press("back")
                                        # await tap_close_btn(self.p)
                                        i += 1
                                        await asyncio.sleep(0.5)
                                    # elif i % 2 == 0:
                                    #    await tap_close_btn(self.p)
                                    #    i += 1
                                    #    await asyncio.sleep(0.5)

                    await self.check_map()

                    # Check if it's time reset bag status
                    time_diff = int(time.time()) - self.track_bag_time
                    if self.bag_full and self.track_bag_time == 0:
                        # start Tracking
                        self.track_bag_time = int(time.time())
                    if self.bag_full and \
                            time_diff >= self.config['item_management'].get('reset_bagfull_interval', 10) * 60:
                        self.track_bag_time = 0
                        self.bag_full = False
                    if self.no_action_count >= self.no_action_max:
                        await self.reset_app()
                        logger.info("Restarting App because no actions detected for {} times".format(self.no_action_count))
                        webhook_url = self.config['discord'].get('webhook_url', '')
                        self.d.app_wait("com.nianticlabs.pokemongo", front=True)
                        sleep_time = 60 if self.config['client'].get('client', '').lower() != 'mad' else 90
                        logger.info(f'Pokemon Go App started, waiting for {sleep_time} secs to login...')
                        await asyncio.sleep(sleep_time)
                        im_rgb = await screen_cap(self.d)
                        if not is_home_page(im_rgb):
                            if is_warning_page(im_rgb):
                                await tap_caught_ok_btn(self.p, im_rgb=im_rgb)
                                await asyncio.sleep(3)
                            im_rgb = await screen_cap(self.d)
                            if not is_home_page(im_rgb):
                                self.d.press("back")
                                await asyncio.sleep(2)
                        im_rgb = await screen_cap(self.d)
                        i = 0
                        if not is_home_page(im_rgb):
                            while True:
                                im_rgb = await screen_cap(self.d)
                                if is_home_page(im_rgb) or i == 8:
                                    break
                                elif i % 2 == 0:
                                    await tap_close_btn(self.p)
                                    i += 1
                                    await asyncio.sleep(0.5)
                                else:
                                    # send the magic button
                                    self.d.press("back")
                                    # await tap_close_btn(self.p)
                                    i += 1
                                    await asyncio.sleep(0.5)
                        if is_home_page(im_rgb):
                            if webhook_url and self.config['discord'].get('enabled', False) and self.config['discord'].get('restart', True):
                                send_to_discord(webhook_url, 'RAB Bot ({})'.format(self.device_id),
                                                'Pokemon Go restarted. Resume scanning...')
                            im_rgb = await screen_cap(self.d)
                            if config['client'].get('zoom_option', 'Pinch In'):
                                self.d(packageName='com.nianticlabs.pokemongo').pinch_in(percent=60, steps=40)
                            else:
                                self.d(packageName='com.nianticlabs.pokemongo').pinch_out(percent=70, steps=40)
                            if pgsharp_client:
                                try:
                                    if self.config['client'].get('pgsharp_reposition', True):
                                        await pgsharp_client.reposition(self.p, self.d)
                                    else:
                                        pgsharp_client.feed_index = 1
                                        pgsharp_client.icon_index = 0
                                        pgsharp_client.joystick_index = 2
                                    x, y = await pgsharp_client.get_location(self.p, self.d)
                                    pgsharp_client.start_location = [x, y]
                                    if not pgsharp_client.start_location:
                                        logger.info("RAB is unable to get starting location, certain features might not work...")
                                except:
                                    pgsharp_client.feed_index = 1
                                    pgsharp_client.icon_index = 0
                                    pgsharp_client.joystick_index = 2
                        self.no_action_count = 0
                    if self.config['client'].get('disable_auto_restart', 0):
                        self.no_action_count = 0

            except KeyboardInterrupt:
                try:
                    response = input("Press <ENTER> to continue...")
                    if response == 'quit':
                        print('Exiting....')
                        break
                except KeyboardInterrupt:
                    continue
            except SystemExit:
                raise
            except Exception as e:
                # Change exception to error for depolyment (so client wont see chuck of erros during exit)
                logger.exception("Encounter unexpected error: {}".format(e))
                cleanup()


def get_adb(devicetype):
    if(devicetype.lower() == "nox"):
        return "C:\\Program Files (x86)\\Nox\\bin\\nox_adb.exe"
    elif(devicetype.lower() == "mumu"):
        return "C:\\Program Files\\MuMu\\emulator\\nemu\\vmonitor\\bin\\adb_server.exe"
    else:
        return "adb"


def get_env(name, message, cast=str):
    if name in os.environ:
        return os.environ[name]
    while True:
        value = input(message)
        try:
            return cast(value)
        except ValueError as e:
            print(e, file=sys.stderr)
            time.sleep(1)


def readconfig(configfile=None):
    if configfile is None:
        path = 'config.yaml'
    else:
        path = configfile

    with open(path, "r", encoding='utf8') as f:
        config = yaml.load(f, Loader)

    if config:
        return config


def cleanup():
    global device_id
    global wifi_ip
    global config
    global client
    global localnetwork
    global rab_runtime_status

    adb_path = get_adb(config['client'].get('type', 'Real'))

    if not config['client'].get('manual_set_resolution', False):
        args = [
            adb_path,
            "-s",
            device_id,
            "shell",
            "wm",
            "density",
            "reset"
        ]
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        args = [
            adb_path,
            "-s",
            device_id,
            "shell",
            "wm",
            "size",
            "reset"
        ]
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        args = [
            adb_path,
            "-s",
            device_id,
            "shell",
            "settings",
            "put",
            "system screen_brightness",
            100
        ]
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()

    time.sleep(1.0)  # Let's wait for a while
    args = [
        adb_path,
        "-s",
        device_id,
        "shell",
        "wm",
        "overscan",
        "0,0,0,0"
    ]
    p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
    stdout, stderr = p.communicate()

    if wifi_ip:
        args = [
            adb_path,
            "disconnect",
            device_id
        ]
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()

    if config['client'].get('client', '').lower() in ['polygon paid', 'polygonpaid']:
        if localnetwork:
            localnetwork.close_connection()

    # client.loop.stop()
    # client.disconnect()
    print('------Summary------')
    rab_runtime_status.time_end = int(time.time())
    print('{}'.format(rab_runtime_status.__dict__()))
    print('-------------------')
    input("Press any key to continue to exit...")
    sys.exit(1)


def signal_handler(sig, frame):
    cleanup()


async def telegram_feed(event):
    try:
        global config
        global client
        global telegram_id
        global donor_until
        global telegram_src
        global feed_dict
        global feed_src
        global snipe_src
        global spawns_to_snipe
        global spawns_to_check
        global snipe_count

        #logger.debug('FEED POOL: {} SHINY POOL: {} SNIPE POOL: {}'.format(telegram_src, feed_src, snipe_src))

        current_time = int(time.time())
        if donor_until:
            if current_time > donor_until:
                logger.info('Your Donor Status has expired. You will be no longer be able to recieve feed from donor channels.')
                feed_dict.clear()
                feed_dict = {'Free Feed': -1001204900874}
                feed_src[:] = []
                snipe_src[:] = []

                if config['shiny_check'].get('enabled', False):
                    #feed_src[:] = default_shiny_feed + config['shiny_check'].get('src_telegram',[])
                    for each_feed in config['shiny_check'].get('src_telegram', []):
                        if feed_dict.get(each_feed):
                            feed_src.append(feed_dict.get(each_feed))

                if config['snipe'].get('enabled', False) and not config['shiny_check'].get('enabled', False):
                    #snipe_src[:] = default_snipe_feed + config['snipe'].get('src_telegram',[])
                    for each_feed in config['snipe'].get('src_telegram', []):
                        if feed_dict.get(each_feed):
                            snipe_src.append(feed_dict.get(each_feed))

                tmp_dic = dict.fromkeys(feed_src + snipe_src)
                telegram_src[:] = list(tmp_dic)
                donor_until = 0

        text = event.text
        logger.debug('Received raw data from telegram: {}'.format(text))
        raw_to_id = event.to_id
        logger.debug('Received raw data from telegram ({}): {}'.format(raw_to_id.channel_id, text))
        # Need to find out how to get the correct id for public channel, this only works for private
        to_id = int('-100' + str(raw_to_id.channel_id))

        if to_id in feed_src and not config['shiny_check'].get('enabled', False):
            return False
        if to_id in snipe_src and not config['snipe'].get('enabled', False):
            return False
        logger.debug('Received data from telegram ({}): {}'.format(to_id, text))

        spawn = dict()
        if is_json(text):
            spawn = extract_spawn_from_dict(text)
        else:
            coordinates = check_coords_from_text(text)
            if coordinates:
                spawn['latitude'] = round(float(coordinates[0]), 5) if coordinates else 0.0
                spawn['longitude'] = round(float(coordinates[1]), 5) if coordinates else 0.0
                spawn['name'] = get_pokemon_name_from_text(text)
                spawn['dex'] = get_id_from_names(spawn['name'])
                spawn['iv'] = check_pm_iv(text)
                spawn['atk'], spawn['def'], spawn['sta'] = check_pm_stats(text)

                if isinstance(spawn['atk'], int) and Unknown.is_(spawn['iv']):
                    spawn['iv'] = int((spawn['atk'] + spawn['def'] + spawn['sta'])/45*100)

                if spawn['iv'] == 100:
                    spawn['atk'], spawn['def'], spawn['sta'] = 15, 15, 15

                if to_id in snipe_src:
                    spawn['cp'] = check_pm_cp(text)
                else:
                    spawn['cp'] = check_pm_cp(text)
                spawn['level'] = check_pm_level(text)
                spawn['gender'] = check_pm_gender(text)

        if spawn.get('latitude') and spawn.get('longitude') and to_id in feed_src:
            if not (config['shiny_check'].get('mon_to_check') and
                    spawn['name'] not in config['shiny_check'].get('mon_to_check')):
                logger.debug('{} (IV{} | CP{} | LVL{}) is in mon_to_check.'
                             .format(spawn['name'], spawn['iv'], spawn['cp'], spawn['level']))
                if spawn['name'] not in config['shiny_check'].get('mon_to_ignore', []):
                    logger.debug('{} (IV{} | CP{} | LVL{}) is not in mon_to_ignore.'
                                 .format(spawn['name'], spawn['iv'], spawn['cp'], spawn['level']))
                    if (spawn['latitude'], spawn['longitude']) not in \
                            [(x['latitude'], x['longitude']) for x in spawns_reported]:
                        if not (spawn['name'] == 'Kricketot' and spawn['iv'] != 100):
                            spawns_reported.append(spawn)
                            # keep 100 spawns in memory only
                            if len(spawns_reported) >= 100:
                                spawns_reported.pop(0)
                            spawn['reported_time'] = time.time()
                            spawns_to_check.append(spawn)
                            spawns_to_check.sort(key=lambda i: (i['latitude'], i['longitude'], i['reported_time']))
                            logger.info('Added {} (IV{} | CP{} | LVL{}) ({} spawns to be checked.)'
                                        .format(spawn['name'], spawn['iv'], spawn['cp'], spawn['level'],
                                                len(spawns_to_check)))
            else:
                logger.info('Ignored {} (IV{} | CP{} | LVL{}).'
                            .format(spawn['name'], spawn['iv'], spawn['cp'], spawn['level']))
        elif spawn.get('latitude') and spawn.get('longitude') and to_id in snipe_src:
            cd_total_sec = calculate_cooldown(last_active_location.get('latitude', 0),
                                              last_active_location.get('longitude', 0),
                                              spawn.get('latitude', 0), spawn.get('longitude', 0))

            config_max_cd = config['snipe'].get('snipe_max_cd', 0) * 60
            if cd_total_sec <= config_max_cd and config_max_cd != 0 and isinstance(spawn['atk'], int) and isinstance(spawn['def'], int) and isinstance(spawn['sta'], int) and isinstance(spawn['level'], int):
                logger.debug(
                    "--- This Poke can be snipe within {} min: {}---\nRaw Data: {}".format(round(cd_total_sec/60, 2), spawn, text))
                # let see if this is the pokemon that we really
                great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = get_pvp_info(
                    spawn.get('dex', 1), spawn.get('atk', 0), spawn.get('def', 0), spawn.get('sta', 0), spawn.get('level', 1))
                for pokename, each_poke in config['snipe'].get('snipe_list', {}).items():
                    poke_found = False

                    # Add more options
                    if (pokename.lower() == spawn['name'].lower() and each_poke.get('type', '') == 'by_cp_less' and spawn['cp'] <= each_poke.get('cp', 0)):
                        poke_found = True
                    elif (pokename.lower() == spawn['name'].lower() and each_poke.get('type', '') == 'by_cp_more' and spawn['cp'] >= each_poke.get('cp', 0)):
                        poke_found = True
                    elif (pokename.lower() == spawn['name'].lower() and each_poke.get('type', '') == 'by_ivs' and (spawn['atk'] == each_poke.get('atk', 0) and spawn['def'] == each_poke.get('def', 0) and spawn['sta'] == each_poke.get('sta', 0)) or (spawn['atk'] == each_poke.get('atk', 0) and spawn['def'] == each_poke.get('def', 0) and spawn['sta'] == each_poke.get('sta', 0) and spawn['cp'] <= each_poke.get('cp', 0))):
                        poke_found = True
                    elif (pokename.lower() == POKEMON[great_id].lower() and ((each_poke.get('type', '') == 'gl') or (each_poke.get('type', '') == 'pvp'))) and great_rating >= each_poke.get('rating', 101):
                        poke_found = True
                    elif (pokename.lower() == POKEMON[ultra_id].lower() and ((each_poke.get('type', '') == 'ul') or (each_poke.get('type', '') == 'pvp'))) and ultra_rating >= each_poke.get('rating', 101):
                        poke_found = True
                    elif pokename.lower() == spawn['name'].lower() and (each_poke.get('type', '') == 'iv100' and spawn['iv'] == 100):
                        poke_found = True
                    elif config['snipe'].get('snipe_any_100iv', False) and spawn['iv'] == 100:
                        poke_found = True

                    if poke_found:
                        if snipe_count.get(pokename.lower(), 0) >= (each_poke.get('snipe_limit', 0) - 1) and each_poke.get('snipe_limit', 0) != 0:
                            logger.info('Ignored {}, snipe limit {} reached'.format(
                                spawn['name'], each_poke.get('snipe_limit', 0)))
                            continue
                        if (spawn['latitude'], spawn['longitude']) not in [(x['latitude'], x['longitude']) for x in spawns_reported]:
                            spawns_reported.append(spawn)
                            # keep 100 spawns in memory only
                            if len(spawns_reported) >= 100:
                                spawns_reported.pop(0)
                            spawn['cooldown_time'] = cd_total_sec
                            spawn['snipe_type'] = each_poke.get('type')
                            spawn['reported_time'] = time.time()
                            if each_poke.get('shiny_check', False):
                                spawn['shiny_check'] = True
                            spawns_to_snipe.append(spawn)
                            spawns_to_snipe.sort(key=lambda i: (i['latitude'], i['longitude'], i['reported_time']))
                            logger.info('Added {} (IV{} | CP{} | LVL{} | GL:{} | UL:{} | Shiny Check: {}) ({} for snipping...)'
                                        .format(spawn['name'], spawn['iv'], spawn['cp'], spawn['level'], great_rating, ultra_rating, spawn.get('shiny_check', False),
                                                len(spawns_to_snipe)))
                            if config['snipe'].get('snipe_any_100iv', False):
                                break  # no need check other conidition if it's just checking 100IV
    except Exception as e:
        # Change exception to error for depolyment (so client wont see chuck of erros during exit)
        logger.exception("Encounter Telegram Error: {}".format(e))
        pass


def call_main(event=None, telegram_client=None, frm_telegram_id=None, frm_donor_until=None):
    global config
    global client
    global telegram_id
    global donor_until
    global telegram_src
    global feed_dict
    global feed_src
    global snipe_src

    client = telegram_client
    telegram_id = frm_telegram_id
    donor_until = frm_donor_until

    # if sys.platform == 'win32':
    #    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    parser = argparse.ArgumentParser(description='Real Android Bot')
    parser.add_argument('--device-id', type=str, default=None,
                        help="Optional, if not specified the phone is automatically detected. "
                             "Useful only if you have multiple phones connected. Use adb devices to get a list of ids.")
    parser.add_argument('--wifi-ip', type=str, default=None,
                        help='If you want to connect your device through Wi-Fi, then set this value.')
    parser.add_argument('--wifi-port', type=str, default='5555',
                        help='For over wifi. Default port is 5555.')
    parser.add_argument('--config-filename', type=str, default=None,
                        help='Config file location.')
    parser.add_argument('--log-level', default='INFO',
                        help='Log level')
    parser.add_argument('--develop-mode', type=str, default=None,
                        help='Developer Mode')
    parser.add_argument('--map-mode', type=str, default=None,
                        help='Map Mode')
    parser.add_argument('--headless', type=str, default=None,
                        help='Headless Mode')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, signal_handler)

    logger.setLevel(args.log_level)

    try:
        if args.config_filename:
            config = readconfig(args.config_filename)
        else:
            config = readconfig('config.yaml')
    except:
        logger.info('Please ensure that you have copied config.example.yaml to rab folder and renamed it to config.yaml')
        logger.info('Also ensure that you have edited the file according to what 3rd party app that you are using.')
        logger.info('Check through the options of the config file and ensure it works for your 3rd party app.')
        sys.exit(1)

    if client:
        logger.info('TELEGRAM CLIENT IS ACTIVE')
        default_shiny_feed = [-1001204900874]
        default_snipe_feed = [-1001204900874]
        # Free Feed -1001204900874, 100IV Shiny -1001263837537, 82IV Shiny -1001342429024, Rare 100IV -1001474496106
        if frm_donor_until:
            feed_dict = {'Free Feed': -1001204900874, '100IV Shiny': -1001263837537, '82IV Shiny': -1001342429024,
                         'Rare 100IV': -1001474496106, 'PVP': -1001519876298, 'Hidden 1': -1001329595625, 'Hidden 2': -1001469656053}
        else:
            feed_dict = {'Free Feed': -1001204900874}

        if config['shiny_check'].get('enabled', False):
            #feed_src[:] = default_shiny_feed + config['shiny_check'].get('src_telegram',[])
            for each_feed in config['shiny_check'].get('src_telegram', []):
                if feed_dict.get(each_feed):
                    feed_src.append(feed_dict.get(each_feed))
        else:
            feed_src[:] = []

        if config['snipe'].get('enabled', False) and not config['shiny_check'].get('enabled', False):
            #snipe_src[:] = default_snipe_feed + config['snipe'].get('src_telegram',[])
            for each_feed in config['snipe'].get('src_telegram', []):
                if feed_dict.get(each_feed):
                    snipe_src.append(feed_dict.get(each_feed))
        else:
            snipe_src[:] = []
        # Convert to dict to remove duplictaes and then convert back to list
        tmp_dic = dict.fromkeys(feed_src + snipe_src)
        telegram_src = list(tmp_dic)
        logger.debug('CHANNELS AVAILIBLE: {}'.format(telegram_src))
        client.add_event_handler(telegram_feed, event.NewMessage(chats=telegram_src))

        # Feed Check
        # @client.on(events.NewMessage(chats=telegram_src))  # Default Shiny Channel until finialized

        client.loop.run_until_complete(Main(args).start())
    else:
        asyncio.run(Main(args).start())

# call_main()
#logger.info('Unexpected exit')
# cleanup() # Do clean up for everything that exits unexcpectly
