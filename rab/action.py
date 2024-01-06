import asyncio
import logging
import random
import time
import sys
import re
import requests
import numpy as np

from pathlib import Path
from PIL import Image

from ImageUtils import extract_text_from_image, crop_horizontal_piece, crop_top_half, crop_bottom_half
from page_detection import is_catch_pokemon_page, is_mon_caught_page, save_screenshot, \
    is_grunt_defeated_page, is_home_page, completed_quest_position, match_key_word_wrapper, \
    is_quest_page, is_caught_flee, is_zero_ball, is_mon_details_page, is_mysterious_pokemon, \
    is_razz_berry_page, is_nanab_berry_page, is_pinap_berry_page, is_golden_berry_page, \
    is_silver_berry_page, is_team_selection_vaild, is_pokemon_full, is_pokemon_inventory_page, \
    is_transfer_menu, is_power_up_page, selection_contains, encounter_position, is_bag_full
from utils import Loader, Unknown, timer, get_average_color
from Pokemon import Pokemon
from PokemonUtils import get_pokemon_name_from_text
from Webhook import send_to_discord

logger = logging.getLogger('rab')

#path = "config.yaml"
# with open(path, "r") as f:
#    config = yaml.load(f, Loader)
config = None

# defining the 9 locations
poke_location = [{'x': 190, 'y':  650}, {'x': 540, 'y':  650}, {'x': 880, 'y':  650},
                { 'x': 190, 'y': 1040}, {'x': 540, 'y': 1040}, {'x': 880, 'y': 1040},
                { 'x': 190, 'y': 1460}, {'x': 540, 'y': 1460}, {'x': 880, 'y': 1460}]


async def set_config(main_config):
    global config
    config = main_config


async def screen_cap(p, border_width=80):
    global config
    screenshot_shift = config['client'].get('screenshot_shift', 0)
    t0 = time.time()
    image = p.screenshot()
    if config.get('resize', False):
        image = image.crop((0, 0 + screenshot_shift, 720, 1280 + screenshot_shift))
    else:
        image = image.crop((0, 0 + screenshot_shift, 1080, 1920 + screenshot_shift))
    # cover top border to black
    data = np.array(image)
    h, w, c = data.shape
    if config.get('resize', False):
        border_width = 40
    for i in range(border_width):
        for j in range(w):
            data[i, j, :] = [0, 0, 0]
    image_new = Image.fromarray(data, mode='RGB')
    if config.get('resize', False):
        new_size = (1080, 1920)
        image_new = image_new.resize(new_size)

    logger.debug('Finished taking screenshot in {:0.1f} sec.'.format(time.time() - t0))
    return image_new


async def screen_cap_native(p, border_width=100):
    global config
    screenshot_shift = config['client'].get('screenshot_shift', 0)
    t0 = time.time()

    image = await p.screencap()
    image = image.convert('RGB')
    image = image.crop((0, 0 + screenshot_shift, 1080, 1920 + screenshot_shift))
    # cover top border to black
    data = np.array(image)
    h, w, c = data.shape
    for i in range(border_width):
        for j in range(w):
            data[i, j, :] = [0, 0, 0]
    image_new = Image.fromarray(data, mode='RGB')
    if config.get('resize', False):
        new_size = (1080, 1920)
        image_new = image_new.resize(new_size)

    logger.info('Finished taking screenshot in {:0.1f} sec.'.format(time.time() - t0))
    return image_new


def resize_coords(x, y):
    if config.get('resize', False):
        x = int((x* 720)/1080)  # Yes, this would make more sense as x / 1080 and then * 720
        y = int((y*1280)/1920)  # But this way it is more accurate because bigger numbers are easier for computers
    offset = config['client'].get('screen_offset', 0)
    return x, y+offset


async def swipe_screen(p, x1, y1, x2, y2, duration=0.5):
    logger.debug('Swipe requested from '+str(x1)+','+str(y1)+' to '+str(x2)+','+str(y2))
    x1, y1 = resize_coords(x1, y1)
    x2, y2 = resize_coords(x2, y2)
    await p.swipe(x1, y1, x2, y2, duration)


def drag_screen(p, x1, y1, x2, y2, duration=0.5):
    logger.debug('Drag requested from '+str(x1)+','+str(y1)+' to '+str(x2)+','+str(y2))
    x1, y1 = resize_coords(x1, y1)
    x2, y2 = resize_coords(x2, y2)
    p.drag(x1, y1, x2, y2, duration)


async def tap_screen(p, x, y, duration=0.5):
    logger.debug('Tap requested at '+str(x)+','+str(y))
    x, y = resize_coords(x, y)
    await p.tap(x, y)
    logger.debug('Tapped '+str(x)+','+str(y))
    # p.click(x, y)
    await asyncio.sleep(duration)


async def tap_pokeball_btn(p, duration=1.0):
    await tap_screen(p, 540, 1790, duration)


async def tap_open_pokemon_btn(p, duration=1.0):
    await tap_screen(p, 240, 1600, duration)


async def tap_close_btn(p, duration=1.0):
    await tap_screen(p, 540, 1790, duration)


async def tap_exit_btn(p, duration=1.0):
    await tap_screen(p, 100, 150, duration=duration)


async def tap_select_berry_btn(p, duration=0.5):
    await tap_screen(p, 130, 1700, duration=duration)


async def tap_select_ball_btn(p, duration=0.5):
    await tap_screen(p, 950, 1700, duration=duration)


def is_ok_btn_color(r, g, b):
    if (30 <= r <= 170) and (200 <= g <= 220) and (145 <= b <= 170):
        return True
    else:
        return False


async def tap_caught_ok_btn(p, duration=1.0, im_rgb=None):
    x, y = 540, 1350

    if im_rgb:
        # search ok button
        for i in range(860, 1690):
            r, g, b = im_rgb.getpixel((x, i))
            if is_ok_btn_color(r, g, b):
                y = i + 20
                r, g, b = im_rgb.getpixel((x, y))
                if is_ok_btn_color(r, g, b):
                    break
    logger.debug('Tap Ok button: {},{}'.format(x, i+10))
    if y < 1690:
        await tap_screen(p, x, y, duration=duration)
        return True
    else:
        return False


async def tap_poke_management(p, duration=1.0, im_rgb=None):
    await tap_screen(p, 540, 1080, duration=duration)


async def tap_mon_ok_btn(p, duration=1.0):
    await tap_screen(p, 540, 1780, duration=duration)


async def tap_mon_menu_btn(p, duration=0.75):
    await tap_screen(p, 940, 1780, duration=duration)


async def tap_mon_transfer_btn(p, duration=0.5):
    await tap_screen(p, 940, 1560, duration=duration)


async def tap_mon_appraise_btn(p, duration=0.5):
    await tap_screen(p, 940, 1410, duration=duration)  # Value for 0.195.0


async def tap_transfer_yes_btn(p, duration=1.0):
    await tap_screen(p, 540, 1130, duration=duration)


async def tap_transfer_shiny_no_btn(p, duration=0.75):
    await tap_screen(p, 540, 1155, duration=duration)


async def tap_transfer_shiny_yes_btn(p, duration=0.75):
    await tap_screen(p, 540, 1000, duration=duration)


async def tap_remove_quest_ok_btn(p, duration=1.0):
    await tap_screen(p, 540, 1045, duration=duration)


async def tap_rescue_button(p, duration=1.5):
    # Rescue Pokemon
    await tap_screen(p, 540, 1700, duration)


async def tap_collect_component(p, duration=1.5):
    await tap_screen(p, 540, 1715, duration)


async def tap_exit_trainer(p, duration=3.0):
    await tap_screen(p, 540, 960, duration)


async def tap_equip_radar(p, duration=3.0):
    await tap_screen(p, 540, 1620, duration)


async def tap_first_egg(p, duration=0.75):
    await tap_screen(p, 200, 550, duration=duration)


async def tap_incubate_btn(p, duration=1.0):
    await tap_screen(p, 540, 1400, duration=duration)


async def tap_free_incubator(p, duration=1.0):
    await tap_screen(p, 165, 1400, duration=duration)


async def tap_power_up(p, duration=1.0):
    await tap_screen(p, 300, 1565, duration=duration)


async def tap_power_up_btn(p, duration=1.0):
    await tap_screen(p, 450, 1625, duration=duration)


async def tap_power_up_confirm(p, duration=0.75):
    await tap_screen(p, 540, 1000, duration=duration)


async def tap_power_up_plus(p, duration=0.5):
    await tap_screen(p, 830, 1370, duration=duration)


async def tap_fav_icon(p, duration=1):
    await tap_screen(p, 974, 188, duration=duration)


async def tap_gym_btn(p, duration=1):
    await tap_screen(p, 945, 1560, duration=duration)


def check_if_requires_highthrow(pokemon):
    if pokemon.name in config['catch'].get('high_far_pokemon', []):
        return True
    return False


@timer
def get_berries_by_matching(im):
    berry_list = []

    im_cropped = crop_horizontal_piece(im, 5, 5)
    text = extract_text_from_image(im_cropped, binary=False, threshold=150)
    # text = text.replace('berry', '')
    text = ' '.join(text.split())
    types_of_berries = text.count('berry')
    if types_of_berries == 0:
        return berry_list

    if is_razz_berry_page(im):
        berry_list.append('razz berry')

    if is_nanab_berry_page(im):
        berry_list.append('nanab berry')

    if is_pinap_berry_page(im):
        berry_list.append('pinap berry')
    if len(berry_list) == 3:
        return berry_list

    if is_golden_berry_page(im):
        berry_list.append('golden razz berry')
    if len(berry_list) == 3:
        return berry_list

    if is_silver_berry_page(im):
        berry_list.append('silver pinap berry')

    logger.debug('Found berries: {}'.format(berry_list))
    return berry_list


@timer
def get_berries(im):
    im_cropped = crop_horizontal_piece(im, 5, 5)
    text = extract_text_from_image(im_cropped, binary=False, threshold=150)
    # text = text.replace('berry', '')
    text = ' '.join(text.split())
    types_of_berries = text.count('berry')
    logger.debug("{}: {} berries".format(text, types_of_berries))
    # save_screenshot(im_cropped, sub_dir='berry', save=True)
    berry_list = []
    if 'pinap golden razz' in text:
        berry_list += ['silver pinap berry', 'golden razz berry']
        text = text.replace('pinap golden razz', '')
    if 'pinap pinap' in text:
        berry_list += ['silver pinap berry', 'pinap berry']
        text = text.replace('pinap pinap', '')
    if 'silver pinap' in text:
        berry_list += ['silver pinap berry']
        text = text.replace('silver pinap', '')
    if 'golden razz' in text:
        berry_list += ['golden razz berry']
        text = text.replace('golden razz', '')
    if 'pinap' in text:
        berry_list += ['pinap berry']
        text = text.replace('pinap', '')
    if 'nanab' in text:
        berry_list += ['nanab berry']
        text = text.replace('nanab', '')
    if 'razz' in text:
        berry_list += ['razz berry']
        text = text.replace('razz', '')
    if len(berry_list) < types_of_berries:
        if 'silver pinap berry' not in berry_list:
            if is_silver_berry_page(im):
                berry_list.insert(0, 'silver pinap berry')
        if 'golden razz berry' not in berry_list and len(berry_list) < types_of_berries:
            if is_golden_berry_page(im):
                berry_list.insert(0, 'golden razz berry')
        if 'pinap berry' not in berry_list and len(berry_list) < types_of_berries:
            if is_pinap_berry_page(im):
                berry_list.insert(0, 'pinap berry')
        if 'nanab berry' not in berry_list and len(berry_list) < types_of_berries:
            if is_nanab_berry_page(im):
                berry_list.insert(0, 'nanab berry')
        if 'razz berry' not in berry_list and len(berry_list) < types_of_berries:
            if is_razz_berry_page(im):
                berry_list.insert(0, 'razz berry')

        # berry_list.insert(0, 'unknown berry')
    logger.debug('Found berries: {}'.format(berry_list))
    return berry_list


def get_berry_location(berry_name, berry_list):
    if berry_name not in berry_list:
        return None
    y = 1700
    if len(berry_list) >= 3:
        berry_loc_list = [(180, y), (540, y), (900, y)]
    elif len(berry_list) == 2:
        berry_loc_list = [(360, y), (720, y)]
    elif len(berry_list) == 1:
        berry_loc_list = [(540, y)]
    else:
        berry_loc_list = []
    return berry_loc_list[berry_list.index(berry_name)]


def get_ball_location(ball_name, ball_list):
    if ball_name not in ball_list:
        return None
    y = 1700
    if len(ball_list) == 3:
        ball_loc_list = [(180, y), (540, y), (900, y)]
    elif len(ball_list) == 2:
        ball_loc_list = [(360, y), (720, y)]
    elif len(ball_list) == 1:
        ball_loc_list = [(540, y)]
    else:
        ball_loc_list = []
    return ball_loc_list[ball_list.index(ball_name)]


async def power_up(d, p, by_level=5):
    await tap_power_up(p)
    # Temporary up by 5 levels (to clear quest)
    # Let's build a quest class later to remember the quest
    for i in range(by_level - 1):
        await tap_power_up_plus(p)
    await tap_power_up_btn(p)
    await tap_power_up_confirm(p)


async def catch_quest_pokemon(d, p, pokemon):
    if not config['client'].get('skip_encounter_intro'):
        await asyncio.sleep(3)
    else:
        await asyncio.sleep(1.5)
    im_rgb = await screen_cap(d)
    if is_catch_pokemon_page(im_rgb):
        if config['client'].get('encounter_iv', False):
            pokemon.update_stats_from_pokemod(im_rgb)
        if not pokemon.shiny or Unknown.is_(pokemon.name) or Unknown.is_(pokemon.cp):
            im_rgb = await screen_cap(d)
            save_screenshot(im_rgb, sub_dir='encounter', save=config['screenshot'].get('encounter'))
            pokemon.update_stats_from_catch_screen(im_rgb)

        if pokemon.shiny:
            save_screenshot(im_rgb, sub_dir='shiny', save=config['screenshot'].get('shiny'))

        pokemon_caught = await catch_pokemon(p, d, pokemon)
        if (pokemon_caught and not config['client'].get('transfer_on_catch', False)):
            if pokemon_caught != 'No Ball':
                pokemon = await after_pokemon_caught(p, d, pokemon, config)
        return True
    return False


async def clear_quest(d, p, pokemon):
    im_rgb = await screen_cap(d)
    if not is_quest_page(im_rgb):
        logger.warning("RAB didn't manage to tap into quest page....")
        save_screenshot(im_rgb, sub_dir='exception', save=config['screenshot'].get('exception'))
        i = 0
        while True:
            im_rgb = await screen_cap(d)
            if is_home_page(im_rgb):
                break
            elif i == 4:
                # Back button not working
                await tap_caught_ok_btn(p, im_rgb=im_rgb)
                await asyncio.sleep(0.5)
                im_rgb = await screen_cap(d)
                if is_home_page(im_rgb):
                    break
                else:
                    await tap_close_btn(p)
                    break

            else:
                # press until it's home page
                # await close_team_rocket(self.p)
                # await tap_close_btn(p)
                d.press("back")
                await asyncio.sleep(0.2)
            i += 1
        return 'home'

    offset = config['client'].get('screen_offset', 0)

    item_removed = False

    for i in range(4):
        item_removed = False
        # Box 1
        im_rgb = await screen_cap(d)
        im_cropped = im_rgb.crop((80, 935 + offset, 795, 1170 + offset))
        text = extract_text_from_image(im_cropped)
        if not quest_can_be_completed(text):
            await tap_screen(p, 995, 990, 1.0)
            logger.debug('tapped box 1')
            await tap_remove_quest_ok_btn(p)
            item_removed = True

            if await catch_quest_pokemon(d, p, pokemon):
                return 'on_pokemon'

            continue

        # Box 2
        im_cropped = im_rgb.crop((80, 1225 + offset, 795, 1450 + offset))
        text = extract_text_from_image(im_cropped)
        if not quest_can_be_completed(text):
            await tap_screen(p, 995, 1260, 1.0)
            logger.debug('tapped box 2')
            await tap_remove_quest_ok_btn(p)
            item_removed = True

            if await catch_quest_pokemon(d, p, pokemon):
                return 'on_pokemon'

            continue

        # Box 3
        im_cropped = im_rgb.crop((80, 1510 + offset, 795, 1740 + offset))
        text = extract_text_from_image(im_cropped)
        if not quest_can_be_completed(text):
            await tap_screen(p, 995, 1550, 1.0)
            logger.debug('tapped box 3')
            await tap_remove_quest_ok_btn(p)
            item_removed = True

            if await catch_quest_pokemon(d, p, pokemon):
                return 'on_pokemon'

            continue
        if not item_removed:
            break
    return False


async def check_quest(d, p, pokemon, rab_runtime_status=None):
    # Tap quest icon
    await tap_screen(p, 986, 1595, 2.0)
    await asyncio.sleep(0.5)
    im_rgb = await screen_cap(d)
    if not is_quest_page(im_rgb):
        logger.warning("RAB didn't manage to tap into quest page....")
        save_screenshot(im_rgb, sub_dir='exception', save=config['screenshot'].get('exception'))
        i = 0
        while True:
            im_rgb = await screen_cap(d)
            if is_home_page(im_rgb):
                break
            elif i == 4:
                # Back button not working
                await tap_caught_ok_btn(p, im_rgb=im_rgb)
                await asyncio.sleep(0.5)
                im_rgb = await screen_cap(d)
                if is_home_page(im_rgb):
                    break
                else:
                    await tap_close_btn(p)
                    break

            else:
                # press until it's home page
                # await close_team_rocket(self.p)
                # await tap_close_btn(p)
                d.press("back")
                await asyncio.sleep(0.2)
            i += 1
        return False

    await tap_screen(p, 200, 325, 1.5)
    logger.info("Checking and clearing TODAY Quest....")
    i = 0
    while True:
        im_rgb = await screen_cap(d)
        y = completed_quest_position(im_rgb)
        if y:
            await tap_screen(p, 400, y, 0.25)
            # tap multiple times to clear rewards
            await tap_screen(p, 400, y, 0.25)
            await tap_screen(p, 400, y, 0.25)
            await tap_screen(p, 400, y, 0.25)
            if not config['client'].get('skip_encounter_intro'):
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(1)
            im_rgb = await screen_cap(d)
            if is_mysterious_pokemon(im_rgb):
                await tap_screen(p, 540, 1215, 0.5)  # Start Encounter
                if not config['client'].get('skip_encounter_intro'):
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(1)
                im_rgb = await screen_cap(d)

            if is_pokemon_full(im_rgb) and config.get('poke_management'):
                if config['poke_management'].get('enable_poke_management', False):
                    await tap_caught_ok_btn(p, im_rgb=im_rgb)
                    await clear_pokemon_inventory(p, d)
                    return False

            if is_catch_pokemon_page(im_rgb, is_shadow=False, map_check=True):
                pokemon.update_stats_from_catch_screen(im_rgb)

                if (Unknown.is_not(pokemon.atk_iv) or
                        Unknown.is_not(pokemon.def_iv) or
                        Unknown.is_not(pokemon.sta_iv)) or \
                        (Unknown.is_not(pokemon.name) and
                         config['client'].get('client', '').lower() == 'none'):

                    if pokemon.shiny:
                        save_screenshot(im_rgb, sub_dir='shiny', save=config['screenshot'].get('shiny'))

                    pokemon_caught = await catch_pokemon(p, d, pokemon, rab_runtime_status=rab_runtime_status)
                    if (pokemon_caught and not config['client'].get('transfer_on_catch', False)):
                        if pokemon_caught != 'No Ball':
                            await asyncio.sleep(1)
                            pokemon = await after_pokemon_caught(p, d, pokemon, config)
                    return 'on_pokemon'

        matched = match_key_word_wrapper(im_rgb, ['pokémon in gyms', 'pokemon in gym', config['quest'].get(
            'last_quest_quit_today', 'something that will not match').lower()])
        if len(matched) > 0:
            logger.debug('YES: found key word: {}'.format(matched))
            break
        if i == 5:
            break
        matched = match_key_word_wrapper(
            im_rgb, ['pokemon has appeared', 'pokémon has appeared', 'mysterious pokémon',  'mysterious pokemon'])
        if len(matched) > 0:
            logger.debug('YES: found key word: {}'.format(matched))
            await tap_screen(p, 540, 1185, 4)
        drag_screen(d, 800, 1825, 800, 300, 4)
        i += 1

    # Check Field Page
    logger.info("Checking and clearing FIELD Quest....")
    await tap_screen(p, 540, 285, 1.5)

    await asyncio.sleep(1)

    # Clear quest
    # Check first 3 box, delete quest if the quest can't be complete by bot
    if await clear_quest(d, p, pokemon):
        return 'on_pokemon'

    while True:
        im_rgb = await screen_cap(d)
        matched = match_key_word_wrapper(
            im_rgb, ['pokemon has appeared', 'pokémon has appeared', 'mysterious pokémon',  'mysterious pokemon'])

        y = completed_quest_position(im_rgb)
        if len(matched) > 0:
            logger.debug('YES: found key word: {}'.format(matched))
            await tap_screen(p, 540, 1185, 0.5)
            y = 1185
        if y:
            await tap_screen(p, 400, y, 0.5)

            if not config['client'].get('skip_encounter_intro'):
                await asyncio.sleep(3)
            else:
                await asyncio.sleep(1)

            im_rgb = await screen_cap(d)
            if is_mysterious_pokemon(im_rgb):
                await tap_screen(p, 540, 1215, 0.5)  # Start Encounter
                if not config['client'].get('skip_encounter_intro'):
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(1)
                im_rgb = await screen_cap(d)

            if is_catch_pokemon_page(im_rgb, is_shadow=False, map_check=True):
                pokemon.update_stats_from_catch_screen(im_rgb)

                if (Unknown.is_not(pokemon.atk_iv) or
                        Unknown.is_not(pokemon.def_iv) or
                        Unknown.is_not(pokemon.sta_iv)) or \
                        (Unknown.is_not(pokemon.name) and
                         config['client'].get('client', '').lower() == 'none'):

                    if pokemon.shiny:
                        save_screenshot(im_rgb, sub_dir='shiny', save=config['screenshot'].get('shiny'))

                    pokemon_caught = await catch_pokemon(p, d, pokemon, rab_runtime_status=rab_runtime_status)
                    if (pokemon_caught and not config['client'].get('transfer_on_catch', False)):
                        if pokemon_caught != 'No Ball':
                            await asyncio.sleep(1)
                            pokemon = await after_pokemon_caught(p, d, pokemon, config)
                    return 'on_pokemon'
        else:
            break

    # Check Special Page
    logger.info("Checking and clearing SPECIAL Quest....")
    await tap_screen(p, 880, 325, 2.0)
    # Page Shift
    last_iteration = int(time.time())
    while True:
        im_rgb = await screen_cap(d)
        matched = match_key_word_wrapper(im_rgb, ['mythical discovery', 'more research', 'coming soon', 'research requests', config['quest'].get(
            'last_quest_quit', 'something that will not match').lower()])
        current_time = int(time.time())
        if (current_time - last_iteration) >= 180:
            logger.debug('Stuck for 3 mins, Quitting....')
            break
        if len(matched) > 0:
            logger.debug('YES: found key word: {}'.format(matched))
            break
        while True:
            im_rgb = await screen_cap(d)
            y = completed_quest_position(im_rgb)
            if y:
                await tap_screen(p, 400, y, 0.5)
                await tap_screen(p, 400, y, 0.5)
                # tap multiple times to clear rewards
                await tap_screen(p, 400, y, 0.5)
                await tap_screen(p, 400, y, 0.5)
                await tap_screen(p, 400, y, 0.5)
                if not config['client'].get('skip_encounter_intro'):
                    await asyncio.sleep(3)
                else:
                    await asyncio.sleep(1)

                im_rgb = await screen_cap(d)
                if is_mysterious_pokemon(im_rgb):
                    await tap_screen(p, 540, 1215, 0.5)  # Start Encounter
                    if not config['client'].get('skip_encounter_intro'):
                        await asyncio.sleep(3)
                    else:
                        await asyncio.sleep(1)
                    im_rgb = await screen_cap(d)

                if is_catch_pokemon_page(im_rgb, is_shadow=False, map_check=True):
                    pokemon.update_stats_from_catch_screen(im_rgb)

                    if (Unknown.is_not(pokemon.atk_iv) or
                            Unknown.is_not(pokemon.def_iv) or
                            Unknown.is_not(pokemon.sta_iv)) or \
                            (Unknown.is_not(pokemon.name) and
                             config['client'].get('client', '').lower() == 'none'):

                        if pokemon.shiny:
                            save_screenshot(im_rgb, sub_dir='shiny', save=config['screenshot'].get('shiny'))

                        pokemon_caught = await catch_pokemon(p, d, pokemon, rab_runtime_status=rab_runtime_status)
                        if (pokemon_caught and not config['client'].get('transfer_on_catch', False)):
                            if pokemon_caught != 'No Ball':
                                await asyncio.sleep(1)
                                pokemon = await after_pokemon_caught(p, d, pokemon, config)
                        return 'on_pokemon'
            else:
                drag_screen(d, 800, 1825, 800, 300, 4)
                break
            drag_screen(d, 800, 1825, 800, 300, 4)

    await tap_close_btn(p, 1)
    return

    # return 'on_quest'


def quest_can_be_completed(text):
    can_complete_list = ['spin', 'hatch', 'catch', 'throw', 'transfer', 'visit', 'field research']
    non_complete_list = ['scan', 'raid', 'evolve', 'trade']

    if config['client'].get('team_rocket_blastoff', False):
        if 'grunt' not in can_complete_list:
            can_complete_list.append('grunt')
        if 'grunt' in non_complete_list:
            non_complete_list.remove('grunt')
    else:
        if 'grunt' in can_complete_list:
            can_complete_list.remove('grunt')
        if 'grunt' not in non_complete_list:
            non_complete_list.append('grunt')

    if config['client'].get('client', 'none').lower() == 'hal':
        if 'buddy' not in can_complete_list:
            can_complete_list.append('buddy')
        if 'buddy' in non_complete_list:
            non_complete_list.remove('buddy')
    else:
        if 'buddy' in can_complete_list:
            can_complete_list.remove('buddy')
        if 'buddy' not in non_complete_list:
            non_complete_list.append('buddy')

    if config['ball_selection'].get('take_snapshot', False):
        if 'snapshots' not in can_complete_list:
            can_complete_list.append('snapshots')
        if 'snapshots' in non_complete_list:
            non_complete_list.remove('snapshots')
    else:
        if 'snapshots' in can_complete_list:
            can_complete_list.remove('snapshots')
        if 'snapshots' not in non_complete_list:
            non_complete_list.append('snapshots')

    if config['item_management'].get('gift_interval', False):
        if 'gift' not in can_complete_list:
            can_complete_list.append('gift')
        if 'gift' in non_complete_list:
            non_complete_list.remove('gift')
    else:
        if 'gift' in can_complete_list:
            can_complete_list.remove('gift')
        if 'gift' not in non_complete_list:
            non_complete_list.append('gift')

    # this one has the logic reversed
    if config['client'].get('transfer_on_catch', False) or config['quest'].get('power_up_lvl', 5) == 0:
        if 'power up' in can_complete_list:
            can_complete_list.remove('power up')
        if 'power up' not in non_complete_list:
            non_complete_list.append('power up')
    else:
        if 'power up' not in can_complete_list:
            can_complete_list.append('power up')
        if 'power up' in non_complete_list:
            can_complete_list.remove('power up')

    for each_task in non_complete_list:
        if each_task in text:
            return False
    for each_task in can_complete_list:
        if each_task in text:
            return True

    return False


async def check_pokemon_exisits(p, d, x, y):
    im_rgb = await screen_cap(d)
    r, g, b = get_average_color(x-15, y-15, 30, im_rgb)
    if (240 <= r <= 255) and (253 <= g <= 255) and (236 <= b <= 250):
        return False
    else:
        return True


async def clear_pokemon_inventory(p, d, pgsharp_client=None, mad_client=None):
    if not config.get('poke_management'):
        return False

    if not config['poke_management'].get('enable_poke_management', False):
        return False

    no_of_pokemons = config['poke_management'].get('stop_check_at', 50)  # No of times to loop
    text_entry = True
    # await tap_pokeball_btn(p)
    # await tap_open_pokemon_btn(p,2)
    # Prevent transferring of strong pokemon, clear using search
    await tap_screen(p, 540, 350, 1)
    text = config['poke_management'].get('poke_search_string', "age0-1")  # Most recent 2 day, we will make this configurable
    # await asyncio.sleep(30)
    # xml = d.dump_hierarchy()
    # with open('xml.txt', 'w') as f:
    #    f.write(xml)
    try:
        d.implicitly_wait(10.0)
        d(className='android.widget.EditText', packageName='com.nianticlabs.pokemongo', clickable=True).click()
        d.implicitly_wait(10.0)
        d(className='android.widget.EditText', packageName='com.nianticlabs.pokemongo', clickable=True).set_text(text)
        # d(focused=True).set_text(text)
        await asyncio.sleep(1)
        d(text='OK', className='android.widget.Button', packageName='com.nianticlabs.pokemongo', clickable=True).click()
    except:
        try:
            d.set_fastinput_ime(True)
            d.send_keys(text)
            # d.clear_text()
            d.set_fastinput_ime(False)
            await asyncio.sleep(1)
            d(text='OK', className='android.widget.Button', packageName='com.nianticlabs.pokemongo', clickable=True).click()
        except:
            logger.info('Unable to set search text with your Phone. RAB will continue Mass Transfer in groups of 9 instead...')
            d.press("back")
            await asyncio.sleep(0.5)
            d.press("back")
            await asyncio.sleep(0.5)
            text_entry = False

    poke_transfered = False

    # to avoid scrolling in pokemon inventory, once reach max 9 poke that cannot be transfered, exit/return
    current_kept = 0
    chosen = 0

    logger.info('Action: Clearing Pokemon Inventory')
    await asyncio.sleep(1.5)
    no_pokemon_inventory_found = False

    # Open sort
    await tap_screen(p, 930, 1770, 1)
    # Tap combat power
    await tap_screen(p, 930, 1575, 1)
    # Open sort
    await tap_screen(p, 930, 1770, 1)
    # Tap recent
    await tap_screen(p, 930, 607, 1)

    offset = config['client'].get('screen_offset', 0)
    
    # Ensure search text has been entered before using mass transfer
    if config['poke_management'].get('mass_transfer', False) and text_entry:
        logger.info("Mass transfer all pokemon caught using rule: {}".format(
            config['poke_management'].get('poke_search_string', "age0-1")))
        # long tap
        x = poke_location[0].get('x')
        y = poke_location[0].get('y')

        x, y = resize_coords(x, y)

        d.long_click(x, y)
        await asyncio.sleep(1)
        await tap_screen(p, 880, 215, 1)

        im_rgb = await screen_cap(d)
        r, g, b = im_rgb.getpixel((900, 1800 + offset))
        if not ((253 <= r <= 255) and (253 <= g <= 255) and (253 <= b <= 255)):
            logger.info("There's nothing more to transfer...")
            d.press("back")
        else:
            await tap_screen(p, 540, 1815, 1)
            im_rgb = await screen_cap(d)
            if selection_contains(im_rgb):
                await tap_caught_ok_btn(p, im_rgb=im_rgb)
                im_rgb = await screen_cap(d)
            await tap_caught_ok_btn(p, im_rgb=im_rgb)  # apply to transfer

    elif config['poke_management'].get('mass_transfer', False) and not text_entry:
        for i in range(no_of_pokemons):
            if chosen == 0:
                # long tap
                x = poke_location[chosen].get('x')
                y = poke_location[chosen].get('y')

                x, y = resize_coords(x, y)

                d.long_click(x, y)
            else:
                await tap_screen(p, poke_location[chosen].get('x'), poke_location[chosen].get('y'), 0.5)
            chosen += 1
            if chosen == 9 or i == (no_of_pokemons - 1):
                im_rgb = await screen_cap(d)
                r, g, b = im_rgb.getpixel((900, 1800 + offset))
                if not ((253 <= r <= 255) and (253 <= g <= 255) and (253 <= b <= 255)):
                    logger.info("There's nothing more to transfer...")
                    d.press("back")
                    break

                await tap_screen(p, 540, 1815, 1)
                im_rgb = await screen_cap(d)
                if selection_contains(im_rgb):
                    await tap_caught_ok_btn(p, im_rgb=im_rgb)
                    im_rgb = await screen_cap(d)
                await tap_caught_ok_btn(p, im_rgb=im_rgb)  # apply to transfer
                await asyncio.sleep(1)
                logger.info('{}/{} Pokemon processed...'.format(i+1, no_of_pokemons))
                chosen = 0
    else:
        for i in range(no_of_pokemons):
            pokemon = Pokemon()  # Create and overwrite everything to get correct new pokemon info
            await asyncio.sleep(1)

            im_rgb = await screen_cap(d)
            if is_pokemon_inventory_page(im_rgb):
                pass
            elif is_mon_details_page(im_rgb):
                d.press("back")
                await asyncio.sleep(2)
            elif is_transfer_menu(im_rgb):
                d.press("back")
                await asyncio.sleep(1)
                d.press("back")
                await asyncio.sleep(2)
            elif is_power_up_page(im_rgb):
                d.press("back")
                await asyncio.sleep(1)
                d.press("back")
                await asyncio.sleep(2)
            elif is_home_page(im_rgb):
                no_pokemon_inventory_found = True
                break

            logger.info('Checking Pokemon {}/{}...'.format(i+1, no_of_pokemons))
            if not await check_pokemon_exisits(p, d, poke_location[current_kept].get('x'), poke_location[current_kept].get('y') + offset):
                logger.info("There's nothing more to transfer...")
                break
            # First Pokemon in list position
            await tap_screen(p, poke_location[current_kept].get('x'), poke_location[current_kept].get('y'), 1.5)
            if mad_client:
                try:
                    pokemon.update_stats_from_mad(p, d)
                except:
                    pass
                # pokemon.update_stats_from_catch_screen(im_rgb)
            im_rgb = await screen_cap(d)
            if not is_mon_details_page(im_rgb):
                continue
            r, g, b = im_rgb.getpixel((430, 1590 + offset))
            if ((230 <= r <= 235) and (125 <= g <= 130) and (180 <= b <= 185)) or ((253 <= r <= 255) and (200 <= g <= 205) and (230 <= b <= 235)):
                logger.info('This is (most likely) a Shadow Pokemon.')
                pokemon.type = 'shadow'

            if config['poke_management'].get('inventory_iv') or mad_client:
                im_cropped = im_rgb.crop([270, 870, 800, 1085])
                text = extract_text_from_image(im_cropped).replace("\n", " ")
                pokemon.name = get_pokemon_name_from_text(text)
                if pgsharp_client:
                    pokemon.get_stats_from_pgsharp(p, d, detail=False)
                else:
                    pokemon.update_stats_from_mon_page(im_rgb)
            else:
                pokemon.update_stats_from_mon_page(im_rgb)

            r, g, b = im_rgb.getpixel((974, 188 + offset))
            if (240 <= r <= 250) and (180 <= g <= 200) and (8 <= b <= 15):
                await tap_mon_ok_btn(p)
                logger.info('Kept Favorite Pokemon.')
                pokemon.status = True

            if not pokemon.status:
                pokemon = await after_pokemon_caught(p, d, pokemon, config, from_appraisal=True)

            y1 = 1430
            y2 = 650

            if pokemon.status:
                current_kept += 1
                if current_kept == 9:
                    drag_screen(d, 190, y1, 190, y2, 2)
                    current_kept = 0
                    await asyncio.sleep(2)
                    # First Pokemon in list position
                    await tap_screen(p, poke_location[current_kept].get('x'), poke_location[current_kept].get('y'), 1)
                    y1 = 1040
                    y2 = 650

                    drag_screen(d, 190, y1, 190, y2, 1)
                    await asyncio.sleep(2)
                    # First Pokemon in list position
                    await tap_screen(p, poke_location[current_kept].get('x'), poke_location[current_kept].get('y'), 1)
                # break

    if not no_pokemon_inventory_found:
        await tap_pokeball_btn(p)
    return 'clear_pokemon_inventory'


@timer
def get_poke_balls(im):
    im_cropped = crop_horizontal_piece(im, 5, 5)
    text = extract_text_from_image(im_cropped, binary=False)
    # save_screenshot(im_cropped, sub_dir='ball', save=True)
    ball_list = []
    if 'poke' in text:
        ball_list.append('poke ball')
    if 'great' in text:
        ball_list.append('great ball')
    if 'ultra' in text:
        ball_list.append('ultra ball')
    logger.debug('Found poke balls: {}'.format(ball_list))
    return ball_list


@timer
async def feed_berry(p, d, pokemon):
    logger.info('Action: feed berry')
    await tap_select_berry_btn(p)
    im_rgb = await screen_cap(d)
    #
    if config['client'].get('advance_berry_check', False):
        berries = get_berries_by_matching(im_rgb)
    else:
        berries = get_berries(im_rgb)
    save_screenshot(im_rgb, sub_dir='berry', save=False)

    if len(berries) == 0:
        x1, y1 = resize_coords(300, 1880)
        x2, y2 = resize_coords( 50, 1880)
        await p.swipe(x1, y1, x2, y2, 250)
        logger.warning('No berry or already used a berry.')
        return False

    berry_selectable = False
    if Unknown.is_not(pokemon.name) and pokemon.name in config['berry_selection'].get('pinap_exclusive', []):
        berry_location = get_berry_location('pinap berry', berries)
        if berry_location is not None:
            await tap_screen(p, berry_location[0], berry_location[1], 0.75)
            logger.info('Used [{}] to {} (IV{} | CP{} | LVL{}).'
                        .format('pinap berry', pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
            berry_selectable = True
    elif pokemon.shiny or \
            (Unknown.is_not(pokemon.iv) and pokemon.iv == 100) or \
            (Unknown.is_not(pokemon.cp) and pokemon.cp >= 2000) or \
            (Unknown.is_not(pokemon.level) and pokemon.level >= 30):
        # feed golden razz berry or razz berry
        for berry_name in config['berry_selection'].get('shiny_or_high_lvl', ['golden razz berry', 'razz berry']):
            berry_location = get_berry_location(berry_name, berries)
            if berry_location is not None:
                await tap_screen(p, berry_location[0], berry_location[1], 0.75)
                logger.info('Used [{}] to {} (IV{} | CP{} | LVL{}).'
                            .format(berry_name, pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                berry_selectable = True
                break
    elif (Unknown.is_not(pokemon.cp) and pokemon.cp < 1000) and \
            (Unknown.is_not(pokemon.level) and pokemon.level < 15):
        for berry_name in config['berry_selection'].get('low_lvl_or_unknown', ['razz berry', 'nanab berry']):
            berry_location = get_berry_location(berry_name, berries)
            if berry_location is not None:
                await tap_screen(p, berry_location[0], berry_location[1], 0.75)
                logger.info('Used [{}] to {} (IV{} | CP{} | LVL{}).'
                            .format(berry_name, pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                berry_selectable = True
                break
    else:
        for berry_name in config['berry_selection'].get('mid_lvl', ['nanab berry', 'razz berry']):
            berry_location = get_berry_location(berry_name, berries)
            if berry_location is not None:
                await tap_screen(p, berry_location[0], berry_location[1], 0.75)
                logger.info('Used [{}] to {} (IV{} | CP{} | LVL{}).'
                            .format(berry_name, pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                berry_selectable = True
                break
    sx, sy = resize_coords(350, 1880)
    ex, ey = resize_coords( 50, 1880)
    if berry_selectable:
        d.swipe(sx, sy, ex, ey, 0.5)
        await tap_screen(p, 540, 1660, 0.75)

        await asyncio.sleep(1.5)
    else:
        d.swipe(sx, sy, ex, ey, 0.5)
        logger.warning('No selectable berry.')

    return berry_selectable


@timer
async def select_ball(p, d, pokemon):
    logger.info('Action: select poke ball')
    if not pokemon.shiny and \
            ((Unknown.is_not(pokemon.cp) and pokemon.cp <= 100) or
             (Unknown.is_not(pokemon.level) and pokemon.level <= 5)):
        logger.info('Skipped selecting ball for {} (IV{} | CP{} | LVL{}).'
                    .format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
        return

    await tap_select_ball_btn(p)
    im_rgb = await screen_cap(d)
    poke_balls = get_poke_balls(im_rgb)
    save_screenshot(im_rgb, sub_dir='ball', save=False)

    if len(poke_balls) == 0:
        x1, y1 = resize_coords( 780, 1880)
        x2, y2 = resize_coords(1030, 1880)
        await p.swipe(x1, y1, x2, y2, 250)
        logger.warning('No poke balls.')
        return 'No Ball'

    if pokemon.shiny or \
            (Unknown.is_not(pokemon.iv) and pokemon.iv == 100) or \
            (Unknown.is_not(pokemon.cp) and pokemon.cp >= 2000) or \
            (Unknown.is_not(pokemon.level) and pokemon.level >= 30):
        # use ultra ball first
        for ball_name in config['ball_selection'].get('shiny_or_high_lvl', ['ultra ball', 'great ball', 'poke ball']):
            ball_location = get_ball_location(ball_name, poke_balls)
            if ball_location is not None:
                await tap_screen(p, ball_location[0], ball_location[1], 0.75)
                logger.info('Selected [{}] to {} (IV{} | CP{} | LVL{}).'
                            .format(ball_name, pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                break
    elif (Unknown.is_not(pokemon.cp) and pokemon.cp < 1000) and \
            (Unknown.is_not(pokemon.level) and pokemon.level < 15):
        for ball_name in config['ball_selection'].get('low_lvl_or_unknown', ['great ball', 'poke ball', 'ultra ball']):
            ball_location = get_ball_location(ball_name, poke_balls)
            if ball_location is not None:
                await tap_screen(p, ball_location[0], ball_location[1], 0.75)
                logger.info('Selected [{}] to {} (IV{} | CP{} | LVL{}).'
                            .format(ball_name, pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                break
    else:
        for ball_name in config['ball_selection'].get('mid_lvl', ['great ball', 'ultra ball', 'poke ball']):
            ball_location = get_ball_location(ball_name, poke_balls)
            if ball_location is not None:
                await tap_screen(p, ball_location[0], ball_location[1], 0.75)
                logger.info('Selected [{}] to {} (IV{} | CP{} | LVL{}).'
                            .format(ball_name, pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                break


@timer
async def throw_ball(p, pokemon, trial=1, track_x=None, track_y=None):
    logger.info('Action: throw pokeball')
    maintain_height = ['Swirlix', 'Spritzee', 'Wurmple', 'Lillipup', 'Tympole', 'Chimchar', 'Goldeen', 'Duskull', 'Charmander',
                       'Rattata', 'Dwebble', 'Roselia', 'Torchic', 'Oshawott', 'Binacle', 'Tepig', 'Caterpie', 'Tynamo', 'Weedle', 'Turtwig', 'Pidgey']

    increase_height = 3 if check_if_requires_highthrow(pokemon) else 0
    if trial >= 4:
        increase_height = 1

    if not pokemon.name in maintain_height and not track_y:
        y_end = 830 - (80 * (increase_height + trial))  # 590 - (80 * (increase_height + trial))
    else:
        if not track_y:
            y_end = 830  # 510
        else:
            y_end = track_y

    swipe_speed = 250
    if y_end <= 350:
        y_end = random.randrange(100, 290)
        swipe_speed = 150

    if track_x:
        x1, y1 = resize_coords(540, 1650)
        x2, y2 = resize_coords(track_x, y_end)
        await p.swipe(x1, y1, x2, y2, 150)
    else:
        x1, y1 = resize_coords(540, 1780)
        x2, y2 = resize_coords(540, y_end)
        await p.swipe(x1, y1, x2, y2, swipe_speed)


def format_iv(pokemon):
    return '({}/{}/{})'.format(pokemon.atk_iv, pokemon.def_iv, pokemon.sta_iv)


async def report_encounter(p, d, pokemon, device_id, pgsharp_client=None):
    #if pgsharp_client:
    #    pokemon.latitude, pokemon.longitude = await pgsharp_client.get_location(p, d)
    #send to map
    #mapresp = requests.post("url", data={pokemon}, auth=('username', 'password'))
    if config.get('discord', False):
        message = ''
        if config['discord'].get('notify_encountered', False) and config['discord'].get('enabled', False):
            keep_poke = await check_keep(p, d, pokemon, keep_shiny=True, show_log=False)
            iv_str = pokemon.name + ' Found ' + format_iv(pokemon)
            if keep_poke or pokemon.shiny:
                if pokemon.shiny and config['discord'].get('notify_shiny', False):
                    message = '**Shiny** ' + iv_str
                elif pokemon.iv == 100 and config['discord'].get('notify_max_iv', False):
                    message = '**100IV** ' + iv_str
                elif pokemon.pvp_info and config['discord'].get('notify_pvp_iv', False):
                    if pokemon.pvp_info['GL'].get('rating', 0) >= config['pvp'].get('gl_rating', 100) or pokemon.pvp_info['UL'].get('rating', 0) >= config['pvp'].get('ul_rating', 100):
                        message = '**PVP** ' + iv_str + ' PVP Information: {}'.format(pokemon.pvp_info)
            if message == '' and config['discord'].get('notify_all_encountered', False):
                message = 'IVs: ' + iv_str + ' Pokemon Data: {}'.format(pokemon)
            webhook_url = config['discord'].get('webhook_url', '')
            if webhook_url:
                shiny_folder = ''
                if pokemon.shiny:
                    shiny_folder = 'shiny/'
                send_to_discord(webhook_url, 'RAB Encounter {}'.format(device_id), message, "https://github.com/PokeAPI/sprites/raw/master/sprites/pokemon/" + shiny_folder + str(pokemon.dex) + ".png")


@timer
async def catch_pokemon(p, d, pokemon, localnetwork=None, displayID=None, is_shadow=False, track_r=0, track_g=0, track_b=0, rab_runtime_status=None, pgsharp_client=None, mad_client=None, device_id=''):
    # {'type': None, 'status': None, 'dex': 241, 'name': 'Miltank', 'form': '???', 'shiny': False, 'iv': 84, 'atk_iv': 10, 'def_iv': 14, 'sta_iv': 14, 'cp': 975, 'level': 15, 'gender': 'Female', 'pvp_info': {'GL': {'dex': 241, 'name': 'Miltank', 'rating': 96.57, 'cp': 1495, 'level': '23'}, 'UL': {'dex': 241, 'name': 'Miltank', 'rating': 98.12, 'cp': 2497, 'level': '47.5'}}, 'screen_x': 0, 'screen_y': 0, 'latitude': 0, 'longitude': 0}

    if rab_runtime_status:
        rab_runtime_status.pokemon_encountered += 1
        if pokemon.shiny:
            rab_runtime_status.pokemon_shiny_encountered += 1

    # if client s HAL and keep mon = true and transfer_on_catch = true, send vol down key to disable transfer
    keep_mon = await check_keep(p, d, pokemon)
    if config['client'].get('client', '').lower() in ['hal'] and config['client'].get('transfer_on_catch', False) and config['catch'].get('enable_keep_mon', True) and keep_mon:
        logger.info('Pokemon to be kept. Disable auto transfer...')
        d.press("volume_down")

    tracking = False
    no_ball = False
    confirm_caught = False  # This is for discord
    if track_r > 0:
        tracking = True
        logger.debug('Tracking R: {} G: {} B: {}'.format(track_r, track_g, track_b))

    await report_encounter(p, d, pokemon, device_id, pgsharp_client)

    if config['ball_selection'].get('take_snapshot', False):
        offset = config['client'].get('screen_offset', 0)
        logger.info('Taking snapshot...')
        await tap_screen(p, 540,  160, 1.0)
        await tap_screen(p, 540, 1700, 1.0)
        await tap_screen(p, 940, 1700, 1.0)
        await tap_screen(p, 140, 1700, 1.0)

    logger.info('Action: catch pokemon')
    is_caught = False
    need_wait = False
    catching = True
    trial = 0
    berry_selectable = True

    if localnetwork:
        # First run, this list will be empty, need to go through the berry and balls at least once
        logger.info('ITEMS: {}'.format(localnetwork.items))
        localnetwork.total_berries_count = localnetwork.items.get('ITEM_RAZZ_BERRY', 0) + localnetwork.items.get(
            'ITEM_NANAB_BERRY', 0) + localnetwork.items.get('ITEM_GOLDEN_RAZZ_BERRY', 0) + localnetwork.items.get('ITEM_GOLDEN_PINAP_BERRY', 0)

    while catching:
        is_caught = False
        trial += 1
        logger.info('Current trial #{}'.format(trial))
        im_rgb = await screen_cap(d)
        if is_zero_ball(im_rgb):
            logger.warning('No More Balls')
            await tap_exit_btn(p)  # Flee, dont waste time
            is_caught = False
            no_ball = True
            if rab_runtime_status:
                rab_runtime_status.pokemon_no_ball_encounter += 1
            return 'No Ball'

        if trial > 1:
            # Make sure it's not home page to prevent catch_pokemon from tapping into other pages that cannot self heal
            if is_home_page(im_rgb):
                return False
        if trial >= 9:
            logger.warning('Gave up.')
            await tap_exit_btn(p)  # Flee, dont waste time
            is_caught = False
            if rab_runtime_status:
                rab_runtime_status.pokemon_gave_up += 1
            break

        if localnetwork and localnetwork.items:
            # Checkball....see if throw until no more or not....
            localnetwork.total_ball_count = localnetwork.items.get(
                'ITEM_POKE_BALL', 0) + localnetwork.items.get('ITEM_GREAT_BALL', 0) + localnetwork.items.get('ITEM_ULTRA_BALL', 0)
            if localnetwork.total_ball_count == 0 and 'ITEM_ULTRA_BALL' in localnetwork.items:
                logger.warning('No more balls')
                await tap_exit_btn(p)  # Flee, dont waste time
                is_caught = False
                no_ball = True
                if rab_runtime_status:
                    rab_runtime_status.pokemon_no_ball_encounter += 1
                break

        if berry_selectable and config['berry_selection'].get('use_berry', True):
            if not localnetwork:
                berry_selectable = await feed_berry(p, d, pokemon)
            else:
                if localnetwork.total_berries_count > 0 or (not localnetwork.items):
                    berry_selectable = await feed_berry(p, d, pokemon)

        # select ball at the first time
        if trial == 1 and pokemon.type not in ['shadow', 'boss'] and config['ball_selection'].get('select_ball', True):
            await select_ball(p, d, pokemon)

        tracking = False

        # Do not track for these value
        if track_r > 0 and track_g > 0 and track_b > 0:
            if (80 <= track_r <= 100) and (80 <= track_g <= 105) and (85 <= track_b <= 115):
                tracking = False
            if (100 <= track_r <= 125) and (125 <= track_g <= 140) and (120 <= track_b <= 135):
                tracking = False
            if (120 <= track_r <= 130) and (90 <= track_g <= 100) and (146 <= track_b <= 156):
                tracking = False
            if (153 <= track_r <= 163) and (200 <= track_g <= 210) and (77 <= track_b <= 87):
                tracking = False
            if (92 <= track_r <= 102) and (142 <= track_g <= 152) and (199 <= track_b <= 209):
                tracking = False
            if (249 <= track_r <= 255) and (163 <= track_g <= 173) and (172 <= track_b <= 182):
                tracking = False
            if (212 <= track_r <= 222) and (74 <= track_g <= 84) and (99 <= track_b <= 109):
                tracking = False
            if (245 <= track_r <= 255) and (215 <= track_g <= 255) and (220 <= track_b <= 255):
                tracking = False
            if (245 <= track_r <= 255) and (215 <= track_g <= 255) and (90 <= track_b <= 150):
                tracking = False

        error_allowed = 5

        pokemon_position = 540

        if config['client'].get('client', '').lower() in ['pgsharp']:
            im_rgb = await screen_cap(d)
            pokemon_position = encounter_position(im_rgb, pokemon)

        if tracking:
            track_x = 0
            track_y = 0
            color_found = False
            for s in range(50, 1000, 20):
                if color_found:
                    break
                for t in range(530, 1080, 20):
                    r, g, b = get_average_color(s, t, 20, im_rgb)

                    min_r = track_r - error_allowed
                    if min_r < 0:
                        min_r = 0
                    max_r = track_r + error_allowed
                    if max_r > 255:
                        max_r = 255

                    min_g = track_g - error_allowed
                    if min_g < 0:
                        min_g = 0
                    max_g = track_g + error_allowed
                    if max_g > 255:
                        max_g = 255

                    min_b = track_b - error_allowed
                    if min_b < 0:
                        min_b = 0
                    max_b = track_b + error_allowed
                    if max_b > 255:
                        max_b = 255

                    if (min_r <= r <= max_r) and (min_g <= g <= max_g) and (min_b <= b <= max_b):
                        color_found = True
                        track_x = s + 40
                        track_y = t
                        if s < 120:
                            logger.info('Not tracking...')
                            track_x = 0
                            track_y = 0
                        break

            if track_x > 0:
                logger.info('Pokemon Tracked...')
                await throw_ball(p, pokemon, trial, track_x, track_y)
            else:
                await throw_ball(p, pokemon, trial)
        else:
            if pokemon_position > 0:
                await throw_ball(p, pokemon, trial, pokemon_position)
            elif Unknown.is_(pokemon.name):
                await throw_ball(p, pokemon, trial)
            else:
                await throw_ball(p, pokemon, trial, 540, 300)
        # debug
        tmpTime = time.time()

        # Let's keep the old codes
        # This section attempt to use toast to check the status of last action
        if (config['client'].get('transfer_on_catch', False) and config['client'].get('client', '').lower() in ['hal', 'pokemod', 'espresso']) or config['client'].get('client', '').lower() in ['mad', 'pgsharp', 'pgsharp paid', 'pgsharppaid']:
            await asyncio.sleep(2)
            message = d.toast.get_message(2.0, 4.0, "").lower()
            if 'caught' in message or 'capture' in message:
                logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                is_caught = True
                confirm_caught = True
                if rab_runtime_status:
                    rab_runtime_status.pokemon_caught += 1
                    if pokemon.shiny:
                        rab_runtime_status.pokemon_shiny_caught += 1
                    if is_shadow:
                        rab_runtime_status.pokemon_shadow_caught += 1
                if not config['client'].get('transfer_on_catch', False):
                    if config['client'].get('client', '').lower() == 'mad':
                        await asyncio.sleep(6)
                    else:
                        await asyncio.sleep(12)

                break
            elif 'escaped' in message:
                logger.info('Pokemon escaped')
                if config['client'].get('client', '').lower() == 'mad':
                    await asyncio.sleep(5)
                else:
                    await asyncio.sleep(7)
                continue
            elif 'missed' in message:
                logger.info('Missed hitting...')
                continue
            elif 'fled' in message or 'flee' in message:
                logger.info('{} (IV{} | CP{} | LVL{}) has fled.'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                is_caught = False
                if rab_runtime_status:
                    rab_runtime_status.pokemon_fled += 1
                break
            else:
                logger.debug('Missed hitting...')
                continue

        # if config['client'].get('client','').lower() in ['pgsharp', 'pgsharp paid']:

        # Wait if not transfer_on_catch
        if (not config['client'].get('transfer_on_catch', False)) or config['client'].get('client', '').lower() in ['pgsharp', 'pgsharp paid']:
            if config['client'].get('transfer_on_catch', False):
                await asyncio.sleep(1.2)
                tmpTime2 = time.time()
                im_rgb = await screen_cap(d)
                # im_rgb = await screen_cap_native(p)
                # This is only for PGSharp Paid
                runTime = round((time.time() - tmpTime), 3)
                ssTime = round((time.time() - tmpTime2), 3)
                logger.debug('Run Time: {} | SS Time: {}'.format(runTime, ssTime))
                caught_flee_list = is_caught_flee(im_rgb)

                if caught_flee_list:
                    logger.debug('{}'.format(caught_flee_list))
                    if 'caught' in caught_flee_list or 'capture' in caught_flee_list or 'transfered' in caught_flee_list or 'transferred' in caught_flee_list:
                        logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(
                            pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                        is_caught = True
                        confirm_caught = True
                        if rab_runtime_status:
                            rab_runtime_status.pokemon_caught += 1
                            if pokemon.shiny:
                                rab_runtime_status.pokemon_shiny_caught += 1
                            if is_shadow:
                                rab_runtime_status.pokemon_shadow_caught += 1

                        break
                    elif 'escaped' in caught_flee_list:
                        logger.info('Pokemon escaped')
                        await asyncio.sleep(2)
                        continue
                    elif 'missed' in caught_flee_list:
                        logger.info('Missed hitting.')
                        continue
                    elif is_home_page(im_rgb):
                        logger.info('{} (IV{} | CP{} | LVL{}) was caught (Might have fled).'.format(
                            pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                        is_caught = True
                        if rab_runtime_status:
                            rab_runtime_status.pokemon_unknown_status += 1
                        break
                    else:
                        logger.debug('Still on catch screen...')
                        continue
                if is_home_page(im_rgb):
                    logger.info('{} (IV{} | CP{} | LVL{}) was caught (Might have fled).'.format(
                        pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                    is_caught = True
                    if rab_runtime_status:
                        rab_runtime_status.pokemon_unknown_status += 1
                    break
                else:
                    logger.debug('Still on catch screen...')
            else:
                await asyncio.sleep(1.5)
                logger.info('Check if the pokemon escaped instantly.')
                im_rgb = await screen_cap(d)
                if is_catch_pokemon_page(im_rgb, map_check=True):
                    logger.info('Pokemon escaped instantly.')
                    continue

            await asyncio.sleep(4.0)
            logger.info('Check if the pokemon broke free.')

            im_rgb = await screen_cap(d)
            if is_catch_pokemon_page(im_rgb, map_check=True):
                logger.info('Pokemon escaped.')
                continue

        # await asyncio.sleep(1) # a small wait for network update
        if localnetwork:
            # wait asyncio.sleep(1.5) # additonally wait or network
            running_loop = True
            loop_count = 0
            while running_loop:
                await asyncio.sleep(0.2)
                if loop_count >= 15:
                    logger.warning('Catch data not found')
                    break
                if len(localnetwork.catch) > 0:
                    break
                loop_count += 1
            if len(localnetwork.catch) > 0:
                caught_status = localnetwork.catch.pop()  # remove it
                localnetwork.catch[:] = []
                logger.debug('Status: {}'.format(caught_status.get('status')))
                if caught_status.get('status') == 'CATCH_SUCCESS':
                    # {'status': 'CATCH_SUCCESS', 'capturedPokemonId': '13903424631688390465', 'scores': {'activityType': ['ACTIVITY_CATCH_POKEMON', 'ACTIVITY_CATCH_EXCELLENT_THROW', 'ACTIVITY_CATCH_CURVEBALL', 'ACTIVITY_CATCH_FIRST_THROW'], 'exp': [100, 1000, 20, 50], 'candy': [3, 0, 0, 0], 'stardust': [100, 0, 0, 0], 'xlCandy': [0, 0, 0, 0]}, 'captureReason': 'DEFAULT', 'pokemonDisplay': {'gender': 'FEMALE', 'form': 'POLIWAG_NORMAL', 'displayId': '1914603624632000740'}}
                    logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(pokemon.name, pokemon.iv, pokemon.cp,
                                                                              pokemon.level))
                    ttl_exp = sum(caught_status['scores'].get('exp', []))
                    ttl_candies = sum(caught_status['scores'].get('candy', []))
                    ttl_stardust = sum(caught_status['scores'].get('stardust', []))
                    ttl_XL = sum(caught_status['scores'].get('xlCandy', []))
                    logger.info('Total Experience: {} | Candies: {} | XL: {} | Stardust: {}'.format(
                        ttl_exp, ttl_candies, ttl_XL, ttl_stardust))
                    is_caught = True
                    confirm_caught = True
                    if 'displayPokedexId' in caught_status:
                        logger.info('Ditto is caught')
                    if rab_runtime_status:
                        rab_runtime_status.pokemon_caught += 1
                        if pokemon.shiny:
                            rab_runtime_status.pokemon_shiny_caught += 1
                        if is_shadow:
                            rab_runtime_status.pokemon_shadow_caught += 1
                    break
                elif caught_status.get('status') == 'CATCH_ESCAPE':
                    logger.info('Pokemon escaped...')
                    continue
                elif caught_status.get('status') == 'CATCH_MISSED':
                    logger.info('Miss Target...')
                    continue
                elif caught_status.get('status') == 'CATCH_FLEE':
                    logger.info("Pokemon fled...")
                    is_caught = False
                    if rab_runtime_status:
                        rab_runtime_status.pokemon_fled += 1
                    break
                else:
                    logger.error("Error...")
                    is_caught = False
                    if rab_runtime_status:
                        rab_runtime_status.pokemon_unknown_status += 1
                    break

            else:
                # say no catchIndex, we do manual and see where is the poke
                im_rgb = await screen_cap(d)
                caught_list = is_mon_caught_page(im_rgb)
                if caught_list:
                    logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(pokemon.name, pokemon.iv, pokemon.cp,
                                                                              pokemon.level))
                    is_caught = True
                    confirm_caught = True
                    # need to wait for 6 secs if Pokemon is new
                    if 'new' in caught_list:
                        need_wait = True
                    break
                    if rab_runtime_status:
                        rab_runtime_status.pokemon_caught += 1
                        if pokemon.shiny:
                            rab_runtime_status.pokemon_shiny_caught += 1
                        if is_shadow:
                            rab_runtime_status.pokemon_shadow_caught += 1
                elif is_catch_pokemon_page(im_rgb, is_shadow):
                    logger.debug('Still on catch screen.')
                    continue
                else:
                    if config['client'].get('transfer_on_catch', False):
                        # im_rgb = await screen_cap(d)
                        caught_flee_list = is_caught_flee(im_rgb)
                        if caught_flee_list:
                            if 'fled' in caught_flee_list or 'flee' in caught_flee_list:
                                logger.info('{} (IV{} | CP{} | LVL{}) fled.'.format(
                                    pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                                is_caught = False
                                if rab_runtime_status:
                                    rab_runtime_status.pokemon_fled += 1
                                break
                            else:
                                logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(
                                    pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                                is_caught = True
                                confirm_caught = True
                                if rab_runtime_status:
                                    rab_runtime_status.pokemon_unknown_status += 1
                                break

                        logger.info('{} (IV{} | CP{} | LVL{}) was caught (Might have fled).'.format(
                            pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                        is_caught = True
                        if rab_runtime_status:
                            rab_runtime_status.pokemon_caught += 1
                            if pokemon.shiny:
                                rab_runtime_status.pokemon_shiny_caught += 1
                            if is_shadow:
                                rab_runtime_status.pokemon_shadow_caught += 1
                        break
                    else:
                        logger.info("Pokemon fled.")
                        is_caught = False
                        if rab_runtime_status:
                            rab_runtime_status.pokemon_fled += 1
                    break
        elif not is_caught:
            if not mad_client:
                await asyncio.sleep(1)
            if config['client'].get('transfer_on_catch', False):
                await asyncio.sleep(2.5)
                im_rgb = await screen_cap(d)
                caught_flee_list = is_caught_flee(im_rgb)
                if caught_flee_list:
                    if 'caught' in caught_flee_list or 'capture' in caught_flee_list or 'transfered' in caught_flee_list or 'transferred' in caught_flee_list:
                        logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(
                            pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                        is_caught = True
                        confirm_caught = True
                        if rab_runtime_status:
                            rab_runtime_status.pokemon_caught += 1
                            if pokemon.shiny:
                                rab_runtime_status.pokemon_shiny_caught += 1
                            if is_shadow:
                                rab_runtime_status.pokemon_shadow_caught += 1
                        break
                    elif 'escaped' in caught_flee_list:
                        logger.info("Still on catch screen...")
                        continue
                    else:
                        logger.info('{} (IV{} | CP{} | LVL{}) fled.'.format(
                            pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                        is_caught = False
                        if rab_runtime_status:
                            rab_runtime_status.pokemon_fled += 1
                        break
                elif is_home_page(im_rgb):
                    logger.info('{} (IV{} | CP{} | LVL{}) was caught (Might have fled).'.format(
                        pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                    is_caught = True
                    if rab_runtime_status:
                        rab_runtime_status.pokemon_unknown_status += 1
                    break
                elif is_catch_pokemon_page(im_rgb, is_shadow):
                    logger.debug('Still on catch screen...')
                    continue

            if mad_client:
                pass
            elif config['client'].get('hyper_mode', False):
                await asyncio.sleep(2.5)
            else:
                await asyncio.sleep(6)
            im_rgb = await screen_cap(d)
            caught_list = is_mon_caught_page(im_rgb)

            if caught_list:
                logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(pokemon.name, pokemon.iv, pokemon.cp,
                                                                          pokemon.level))
                is_caught = True
                confirm_caught = True
                if rab_runtime_status:
                    rab_runtime_status.pokemon_caught += 1
                    if pokemon.shiny:
                        rab_runtime_status.pokemon_shiny_caught += 1
                    if is_shadow:
                        rab_runtime_status.pokemon_shadow_caught += 1
                # need to wait for 6 secs if Pokemon is new
                if 'new' in caught_list:
                    need_wait = True
                break
            elif is_catch_pokemon_page(im_rgb, is_shadow=is_shadow, map_check=True):
                logger.debug('Still on catch screen...')
                continue
            else:
                if config['client'].get('transfer_on_catch', False):
                    caught_flee_list = is_caught_flee(im_rgb)
                    if caught_flee_list:
                        if 'caught' in caught_flee_list or 'capture' in caught_flee_list or 'transfered' in caught_flee_list or 'transferred' in caught_flee_list:
                            logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(
                                pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                            is_caught = True
                            confirm_caught = True
                            if rab_runtime_status:
                                rab_runtime_status.pokemon_caught += 1
                                if pokemon.shiny:
                                    rab_runtime_status.pokemon_shiny_caught += 1
                                if is_shadow:
                                    rab_runtime_status.pokemon_shadow_caught += 1
                            break
                        elif 'escaped' in caught_flee_list:
                            logger.info("Still on catch screen...")
                            continue
                        else:
                            logger.info('{} (IV{} | CP{} | LVL{}) fled.'.format(
                                pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                            is_caught = False
                            if rab_runtime_status:
                                rab_runtime_status.pokemon_fled += 1
                            break
                    else:
                        await asyncio.sleep(4)
                        im_rgb = await screen_cap(d)
                        if is_catch_pokemon_page(im_rgb, is_shadow):
                            logger.debug('Still on catch screen...')
                            continue
                        else:
                            logger.info('{} (IV{} | CP{} | LVL{}) was caught (Might have fled).'.format(
                                pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                            is_caught = True
                            if rab_runtime_status:
                                rab_runtime_status.pokemon_unknown_status += 1
                else:
                    await asyncio.sleep(2.5)
                    if is_home_page(im_rgb):
                        logger.info("Pokemon fled.")
                        is_caught = False
                        if rab_runtime_status:
                            rab_runtime_status.pokemon_fled += 1
                        break
                    else:
                        caught_list = is_mon_caught_page(im_rgb)
                        if caught_list:
                            logger.info('{} (IV{} | CP{} | LVL{}) was caught.'.format(pokemon.name, pokemon.iv, pokemon.cp,
                                                                                      pokemon.level))
                            is_caught = True
                            confirm_caught = True
                            # need to wait for 6 secs if Pokemon is new
                            if 'new' in caught_list:
                                need_wait = True
                            if rab_runtime_status:
                                rab_runtime_status.pokemon_caught += 1
                                if pokemon.shiny:
                                    rab_runtime_status.pokemon_shiny_caught += 1
                                if is_shadow:
                                    rab_runtime_status.pokemon_shadow_caught += 1
                            break
                break

    if is_caught:
        if config.get('discord', False):
            if config['discord'].get('notify_caught_fled', False) and config['discord'].get('enabled', False):

                if keep_mon or pokemon.shiny:
                    message = ''
                    if confirm_caught:
                        if pokemon.shiny and config['discord'].get('notify_shiny', False):
                            message = '**Shiny** {} Caught '.format(pokemon.name) + format_iv(pokemon)
                        elif pokemon.iv == 100 and config['discord'].get('notify_max_iv', False):
                            message = '**100IV** {} Caught'.format(pokemon.name)
                        elif pokemon.pvp_info and config['discord'].get('notify_pvp_iv', False):
                            if pokemon.pvp_info['GL'].get('rating', 0) >= config['pvp'].get('gl_rating', 100) or pokemon.pvp_info['UL'].get('rating', 0) >= config['pvp'].get('ul_rating', 100):
                                message = '**PVP** {} Caught {} PVP Information: {}'.format(
                                    pokemon.name, format_iv(pokemon), pokemon.pvp_info)
                    else:
                        if pokemon.shiny and config['discord'].get('notify_shiny', False):
                            message = '**Shiny** {} Caught (or fled){}'.format(pokemon.name, format_iv(pokemon))
                        elif pokemon.iv == 100 and config['discord'].get('notify_max_iv', False):
                            message = '**100IV** {} Caught (or fled)'.format(pokemon.name)
                        elif pokemon.pvp_info and config['discord'].get('notify_pvp_iv', False):
                            if pokemon.pvp_info['GL'].get('rating', 0) >= config['pvp'].get('gl_rating', 100) or pokemon.pvp_info['UL'].get('rating', 0) >= config['pvp'].get('ul_rating', 100):
                                message = '**PVP** {} Caught (or fled) {} PVP Information: {}'.format(
                                    pokemon.name, format_iv(pokemon), pokemon.pvp_info)

                    webhook_url = config['discord'].get('webhook_url', '')
                    if webhook_url and message:
                        shiny_folder = ''
                        if pokemon.shiny:
                            shiny_folder = 'shiny/'
                        send_to_discord(webhook_url, 'RAB Caught {}'.format(device_id), message, "https://github.com/PokeAPI/sprites/raw/master/sprites/pokemon/" + shiny_folder + str(pokemon.dex) + ".png")

            if config['discord'].get('notify_all_caught', False) and config['discord'].get('enabled', False):
                if confirm_caught:
                    message = '{} Caught CP: {} {} Shiny: {}'.format(pokemon.name, pokemon.cp, format_iv(pokemon), pokemon.shiny)
                else:
                    message = '{} Caught (or fled) CP: {} {} Shiny: {}'.format(pokemon.name, pokemon.cp, format_iv(pokemon), pokemon.shiny)

                webhook_url = config['discord'].get('webhook_url', '')
                if webhook_url and message:
                    shiny_folder = ''
                    if pokemon.shiny:
                        shiny_folder = 'shiny/'
                    send_to_discord(webhook_url, 'RAB Caught {}'.format(device_id), message, "https://github.com/PokeAPI/sprites/raw/master/sprites/pokemon/" + shiny_folder + str(pokemon.dex) + ".png")

        if localnetwork:
            localnetwork.catch[:] = []  # Let's clear it totally
        if not config['client'].get('transfer_on_catch', False):
            await tap_caught_ok_btn(p, im_rgb=im_rgb)
        if need_wait:
            await asyncio.sleep(6.0)
        return True  # return displayPokedexId if have

    if no_ball:
        return 'No Ball'

    return False


@timer
async def appraisal(p, d, pokemon):
    logger.info('Action: appraisal')
    await tap_mon_menu_btn(p, duration=1)  # menu button
    i = 0
    while True:
        im_rgb = await screen_cap(d)
        if is_transfer_menu(im_rgb):
            break
        if i >= 5:
            break
        await asyncio.sleep(1.0)
        i += 1
    await tap_mon_appraise_btn(p)  # appraise
    await tap_mon_appraise_btn(p, duration=1.5)  # appraise

    if Unknown.is_(pokemon.cp):
        get_result = await find_cp(p, d)
        if get_result:
            pokemon.cp = get_result

    im_rgb = await screen_cap(d)
    pokemon.update_stats_from_mon_details(im_rgb, config['client'].get('screen_offset', 0))

    # if pokemon.atk_iv == Unknown.TINY or pokemon.def_iv == Unknown.TINY or pokemon.sta_iv == Unknown.TINY or pokemon.cp == Unknown.TINY:
    #    draw = ImageDraw.Draw(im_rgb)
    #    font = ImageFont.load_default()
    #    draw.text((25, 25),"ATK:{} | DEF:{} | STA:{} | CP:{}".format(pokemon.atk_iv,pokemon.def_iv,pokemon.sta_iv,pokemon.cp),(255,255,255),font=font)
    #    save_screenshot(im_rgb, sub_dir='appraisal', save=config['screenshot'].get('appraisal'))

    await tap_mon_ok_btn(p, duration=0.75)  # close the appraisal page

    return pokemon


@timer
async def transfer_pokemon(p, d, pokemon, keep_shiny=True):
    logger.info('Action: transfer pokemon')

    await tap_mon_menu_btn(p, duration=1.5)  # menu button
    i = 0
    while True:
        im_rgb = await screen_cap(d)
        if is_transfer_menu(im_rgb):
            break
        else:
            await tap_mon_menu_btn(p, duration=1.5)
        if i >= 5:
            break
        await asyncio.sleep(1.0)
        i += 1

    await tap_mon_transfer_btn(p)  # transfer
    await tap_transfer_yes_btn(p)  # yes

    im_rgb = await screen_cap(d)
    text = extract_text_from_image(im_rgb)
    if 'shiny' in text:
        pokemon.shiny = True
        logger.info('Found shiny Pokemon while transferring.')
        if keep_shiny:
            await tap_transfer_shiny_no_btn(p)
            await tap_mon_menu_btn(p)
            await tap_mon_ok_btn(p)
            logger.info('Kept shiny Pokemon.')
            pokemon.shiny = True
            pokemon.status = True
        else:
            await tap_transfer_shiny_yes_btn(p)
            logger.warning('Transferred shiny Pokemon.')
            pokemon.status = False
    elif 'event' in text:
        logger.info('Found event Pokemon while transferring.')
        if config['catch'].get('keep_event', True):
            await tap_transfer_shiny_no_btn(p)
            await tap_mon_menu_btn(p)
            await tap_mon_ok_btn(p)
            logger.info('Kept Event Pokemon.')
            pokemon.status = True
        else:
            await tap_transfer_shiny_yes_btn(p)
            logger.info('Transferred event Pokemon.')
            pokemon.status = False
    elif 'legendary' in text or 'mythical' in text:
        logger.info('Found Legendary/Mythical Pokemon while transferring.')
        if config['catch'].get('keep_legendary', True):
            await tap_transfer_shiny_no_btn(p)
            await tap_mon_menu_btn(p)
            await tap_mon_ok_btn(p)
            logger.info('Kept Legendary/Mythical Pokemon.')
            pokemon.status = True
        else:
            await tap_transfer_shiny_yes_btn(p)
            logger.warning('Transferred Legendary/Mythical Pokemon.')
            pokemon.status = False
    elif 'lucky' in text:
        logger.info('Found Lucky Pokemon while transferring.')
        if config['catch'].get('keep_lucky', True):
            await tap_transfer_shiny_no_btn(p)
            await tap_mon_menu_btn(p)
            await tap_mon_ok_btn(p)
            logger.info('Kept Lucky Pokemon.')
            pokemon.status = True
        else:
            await tap_transfer_shiny_yes_btn(p)
            logger.warning('Transferred Lucky Pokemon.')
            pokemon.status = False

    return pokemon


async def check_keep(p, d, pokemon, keep_shiny=True, show_log=True, from_appraisal=False):
    global config
    keep_mon = False
    poke_level = 60
    # filters to keep or transfer
    if (Unknown.is_not(pokemon.atk_iv) and Unknown.is_not(pokemon.def_iv) and Unknown.is_not(pokemon.sta_iv)):
        if Unknown.is_not(pokemon.level):  # if level is unkown. we just keep it
            poke_level = pokemon.level
        else:
            poke_level = 60  # if it is known, we use this to compare to config

        if from_appraisal and Unknown.is_(pokemon.level):
            poke_level = 0

        if config['client'].get('client', '').lower() == 'none':
            poke_level = 0

        if config['catch'].get('or_condition', False):
            if (pokemon.atk_iv >= config['catch'].get('min_atk', 15) and pokemon.def_iv >= config['catch'].get('min_def', 15) and
                    pokemon.sta_iv >= config['catch'].get('min_sta', 15)) or poke_level >= config['catch'].get('min_lvl', 35):
                keep_mon = True
                if show_log:
                    logger.info('Keep {} (IV{} | CP{} | LVL{}).'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
        else:
            if (pokemon.atk_iv >= config['catch'].get('min_atk', 15) and pokemon.def_iv >= config['catch'].get('min_def', 15) and
                    pokemon.sta_iv >= config['catch'].get('min_sta', 15)) and poke_level >= config['catch'].get('min_lvl', 1):
                keep_mon = True
                if show_log:
                    logger.info('Keep {} (IV{} | CP{} | LVL{}).'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))

    if (Unknown.is_(pokemon.atk_iv) or Unknown.is_(pokemon.def_iv) or Unknown.is_(pokemon.sta_iv)):
        # There will be a chance of unkown, so let's keep it
        keep_mon = True
    if pokemon.shiny and keep_shiny:
        keep_mon = True
        if show_log:
            logger.info('Keep shiny {} (IV{} | CP{} | LVL{}).'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
    if pokemon.type == 'shadow':
        if ((Unknown.is_not(pokemon.iv) and pokemon.iv >= 86) or pokemon.atk_iv == 0) and config['catch'].get('keep_strong_shadow', False):
            keep_mon = True
            if show_log:
                logger.info('Keep strong shadow {} (IV{} | CP{} | LVL{}).'
                            .format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
        elif pokemon.name in config['catch'].get('shadow_mon_to_keep', []):
            keep_mon = True
            if show_log:
                logger.info('Keep shadow {} (IV{} | CP{} | LVL{}).'
                            .format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
        else:
            keep_mon = False
    if pokemon.name in config['catch'].get('mon_to_keep', []):
        keep_mon = True
        if show_log:
            logger.info('Keep {} (IV{} | CP{} | LVL{}).'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
    if config['pvp'].get('enable_keep_pvp') and \
            (pokemon.pvp_info.get('GL', {}).get('name') in config['pvp'].get('gl_to_keep', []) or
             (pokemon.pvp_info.get('GL', {}).get('rating', 0) >= config['pvp'].get('gl_rating', 100) and
              pokemon.pvp_info.get('GL', {}).get('cp', 0) >= config['pvp'].get('gl_cp', 1450))):
        keep_mon = True
        if show_log:
            logger.info(
                'Keep GL {} (IV{} | CP{} | LVL{} | PVP{}).'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level,
                                                                   pokemon.pvp_info.get('GL', {}).get('rating')))
    if config['pvp'].get('enable_keep_pvp') and \
            (pokemon.pvp_info.get('UL', {}).get('name') in config['pvp'].get('ul_to_keep', []) or
             (pokemon.pvp_info.get('UL', {}).get('rating', 0) >= config['pvp'].get('ul_rating', 100) and
              pokemon.pvp_info.get('UL', {}).get('cp', 0) >= config['pvp'].get('ul_cp', 2400))):
        keep_mon = True
        if show_log:
            logger.info(
                'Keep UL {} (IV{} | CP{} | LVL{} | PVP{}).'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level,
                                                                   pokemon.pvp_info.get('UL', {}).get('rating')))
    if not keep_mon and not config['client'].get('transfer_on_catch'):
        if show_log:
            logger.info('Transfer {} (IV{} | CP{} | LVL{}).'.format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))

    return keep_mon


@timer
async def after_pokemon_caught(p, d, pokemon, config, keep_shiny=True, from_appraisal=False):
    logger.info('Action: transfer or keep pokemon')
    await asyncio.sleep(config['catch'].get('delay_before_appraisal', 1.0))
    # Conditions to do the appraisal:
    # (1) Pokemod method fails (IV unknown)
    # (2) Pokemon not in 'mon_to_keep' list (despite of IV)
    if (Unknown.is_(pokemon.atk_iv) or Unknown.is_(pokemon.def_iv) or Unknown.is_(pokemon.sta_iv)) and \
            pokemon.name not in config['catch'].get('mon_to_keep', []):
        pokemon = await appraisal(p, d, pokemon)

    # Let clear powerup quest
    if (not Unknown.is_(pokemon.level)) and (config['quest'].get('power_up_lvl', 5) > 0) and pokemon.level == 1 and config['quest'].get('enable_check_quest', False):
        await power_up(d, p, config['quest'].get('power_up_lvl', 5))
        await asyncio.sleep(3.0)  # Wait for powerup animation to finish

    keep_mon = await check_keep(p, d, pokemon, from_appraisal=from_appraisal)

    # do the transferring
    pokemon.status = keep_mon
    if keep_mon:
        # fav it to prevent pokemon being transfer during mass transfer
        if config['poke_management'].get('mass_transfer', False):
            await tap_fav_icon(p)
        await tap_mon_ok_btn(p)
    else:
        pokemon = await transfer_pokemon(p, d, pokemon, config['catch'].get('enable_keep_shiny', True))

    # extra steps for shadow pokemon
    if pokemon.type == 'shadow':
        await asyncio.sleep(3.0)
    im_rgb = await screen_cap(d)
    text = extract_text_from_image(im_rgb)
    if any(x in text for x in ['component', 'collect', 'radar', 'assemble', 'equip']):
        save_screenshot(im_rgb, sub_dir='rocket', save=False)
        # collect i/6 component
        await tap_collect_component(p)
        logger.info('Collect component after catching shadow pokemon.')
        # collect 6/6 components, and combine components
        if any(x in text for x in ['enough', 'combine', 'assembled', 'team go rocket hideouts']):
            await asyncio.sleep(1.5)
            await tap_equip_radar(p)
            logger.info('Combine radar.')

    return pokemon


@timer
async def find_cp(p, d):
    cp_to_keep = 0
    i = 0
    while True:
        if i >= 2:
            break
        im_rgb = await screen_cap(d)
        im_cropped = crop_horizontal_piece(im_rgb, 4, 1)
        s2 = extract_text_from_image(im_cropped, binary=True, threshold=240, reverse=True)

        text = re.sub('[^0-9]+', ' ', s2)

        logger.debug('Orginal Text: {} Reduced Text: {}'.format(s2, text))
        num_list = [int(s) for s in re.findall(r"(\d+)", text)]

        if len(num_list) >= 1:
            if int(num_list[0]) > 99:
                cp_to_keep = int(num_list[0])
                break
            if int(num_list[0]) > cp_to_keep:
                cp_to_keep = int(num_list[0])
        i += 1
        await asyncio.sleep(0.5)
    if cp_to_keep < 10:
        return False
    else:
        return cp_to_keep


@timer
async def spin_pokestop(p, d):
    logger.info('Action: spin pokestop')
    x1, y1 = resize_coords(240, 1020)
    x2, y2 = resize_coords(930, 1020)
    await p.swipe(x1, y1, x2, y2, 200)   # swipe left to right
    im_rgb = await screen_cap(d)
    bag = is_bag_full(im_rgb)
    await asyncio.sleep(1)
    await tap_close_btn(p)  # Close Pokestop
    return bag


@timer
async def close_team_rocket(p):
    logger.info('Action: close team go rocket')
    await tap_close_btn(p)  # Close Pokestop and tap 4x
    await tap_close_btn(p, duration=1.5)
    await tap_close_btn(p)
    # await tap_close_btn(p)


@timer
async def fight_trainer(p, d, trainer_type='rocket_grunt'):
    if not trainer_type:
        return
    logger.info('Action: fight {}'.format(trainer_type))

    t0 = time.time()
    while True:
        im_rgb = await screen_cap(d)
        im_rgb = await screen_cap(d)
        text = extract_text_from_image(im_rgb) 
        # Get Ready! Swipe! 
        if any(x in text for x in ['get', 'ready', 'swipe']):
            for _ in range(50):
                # 200-400,1200
                swipe_screen(p, 200, 1000, 400, 1200, 0.1)
                swipe_screen(p, 400, 1000, 200, 1200, 0.1)
        # YOU WIN! GOOD EFFORT! NEXT BATTLE
        elif any(x in text for x in ['you', 'win', 'good', 'effort', 'next', 'battle', 'hero', 'purifier', 'rescue']):
            break

        await tap_screen(p, 540, 1675, 0.1)  # Attack!

    return True


@timer
async def fight_team_rocket(p, d, rocket_type='rocket_grunt'):
    if not rocket_type:
        return
    logger.info('Action: fight team go {}'.format(rocket_type))
    # Polygon need to press fight rocket button
    if config['client'].get('client', '').lower() in ['pgsharp paid', 'polygon', 'polygonpaid', 'polygon paid']:
        await tap_screen(p, 540, 1500, 3.0)  # Rocket Button Yes

    im_rgb = await screen_cap(d)
    if is_pokemon_full(im_rgb) and config.get('poke_management'):
        if config['poke_management'].get('enable_poke_management', False):
            await tap_caught_ok_btn(p, im_rgb=im_rgb)
            await clear_pokemon_inventory(p, d)
            return False

    if rocket_type == 'rocket_leader':
        # use rocket radar
        await asyncio.sleep(2)
        await tap_screen(p, 540, 1080, 1.0)
        # await tap_caught_ok_btn(p)

    await asyncio.sleep(1)

    # let's check we have all pokemon
    im_rgb = await screen_cap(d)
    slot1, slot2, slot3 = is_team_selection_vaild(im_rgb)
    if not slot1:
        await tap_screen(p, 245, 1500, 1.5)
        await select_vaild_pokemon(p, d)

    if not slot2:
        await tap_screen(p, 540, 1500, 1.5)
        await select_vaild_pokemon(p, d)

    if not slot3:
        await tap_screen(p, 825, 1500, 1.5)
        await select_vaild_pokemon(p, d)

    await asyncio.sleep(2)
    logger.debug('Tap use this party button')
    await tap_screen(p, 540, 1720, 3.0)  # Use This Party Button
    await asyncio.sleep(3)  # New blast off go straight to catch
    i = 0
    t0 = time.time()
    while True:
        im_rgb = await screen_cap(d)
        if config['client'].get('client').lower() == 'pgsharp paid':
            if is_catch_pokemon_page(im_rgb, is_shadow=True) or i >= 10:
                break
        else:
            await tap_screen(p, 540, 1500, 1.0)  # Extra Tap and wait
            if is_grunt_defeated_page(im_rgb):
                t1 = time.time()
                logger.info('Time cost to defeat team go rocket: {:.1f} sec ({} taps).'.format(t1 - t0, i))
                logger.info('Tap Rescue Pokemon button')
                await tap_rescue_button(p)
                await asyncio.sleep(1)
                break
            elif i >= 30:
                # 30 secs past
                return False
        await asyncio.sleep(1)
        i += 1
    return True


@timer
async def check_player_level(p, d):
    offset = config['client'].get('screen_offset', 0)
    player_level = []
    await tap_screen(p, 135, 1755, 3.0)  # Profile
    await tap_screen(p, 350, 250, 1.0)  # Me tab
    im_rgb = await screen_cap(d)
    im_cropped = im_rgb.crop([20, 1240, 200, 1325 + offset])
    text = extract_text_from_image(im_cropped, binary=False, threshold=150).replace("\n", " ")
    logger.debug(f'Level text: {text}')
    player_level[:] = [int(s) for s in text.split() if s.isdigit()]
    d.press("back")
    return player_level


async def check_gift(p, d):
    im_rgb = await screen_cap(d)
    bag_full = False
    r, g, b = get_average_color(485, 1588, 3, im_rgb)
    if (200 <= r <= 230) and (15 <= g <= 20) and (200 <= b <= 220):
        logger.info("Opening gift")
        # Tap gift
        await tap_screen(p, 540, 1440, 2)
        # Tap open
        await tap_screen(p, 540, 1485, 2)
        await asyncio.sleep(1)
        im_rgb = await screen_cap(d)
        bag_full = is_bag_full(im_rgb)
        if bag_full:
            logger.info("Bag is full...")
            d.press("back")
            await asyncio.sleep(1)
            d.press("back")
            await asyncio.sleep(1)
        else:
            await asyncio.sleep(15)  # showing rewards
    # should be friends profile now
    await tap_screen(p, 210, 1630, 2)
    im_rgb = await screen_cap(d)
    text = extract_text_from_image(im_rgb)
    # Your friend still has an unopened Gift from you.    
    if any(x in text for x in ['which gift', 'gift do you', 'want to send']):
        logger.info("Sending gift")
        await tap_screen(p, 540, 600, 2)
        # Tap send
        await tap_screen(p, 540, 1515, 2)
        await asyncio.sleep(3)
    d.press("back")


async def manage_gifts(p, d):
    await tap_screen(p, 135, 1755, 3.0)  # Profile
    await tap_screen(p, 500, 250, 1.0)  # Friends tab

    # Open sort
    await tap_screen(p, 930, 1770, 1)
    # Tap gift
    await tap_screen(p, 930, 1380, 1)
    # Open sort
    await tap_screen(p, 930, 1770, 1)
    # Tap receive gift
    await tap_screen(p, 930, 1575, 1)

    for entry in range(3):
        await tap_screen(p, 300, 810 + 345*entry, 2)
        await check_gift(p, d)
    d.press("back")


@timer
async def fav_last_caught(p, d, pokemon):
    if not config.get('poke_management'):
        return False

    if not config['poke_management'].get('enable_poke_management', False):
        return False

    if not config['poke_management'].get('mass_transfer', False):
        return False

    keep_mon = await check_keep(p, d, pokemon)

    if keep_mon:
        await asyncio.sleep(1)
        await tap_pokeball_btn(p)
        await tap_open_pokemon_btn(p, 2)

        await tap_screen(p, poke_location[0].get('x'), poke_location[0].get('y'), 1.5)
        await tap_fav_icon(p)
        d.press("back")
        await asyncio.sleep(1)
        d.press("back")
        await asyncio.sleep(1)


@timer
async def select_vaild_pokemon(p, d):
    chosen = False
    im_rgb = await screen_cap(d)

    if not chosen:
        r, g, b = im_rgb.getpixel((330, 945))
        if not ((250 <= r <= 255) and (225 <= g <= 235) and (225 <= b <= 235)) and not ((220 <= r <= 240) and (240 <= g <= 255) and (210 <= b <= 230)):
            await tap_screen(p, 200, 965, 1)
            chosen = True

    if not chosen:
        r, g, b = im_rgb.getpixel((395, 945))
        if not ((250 <= r <= 255) and (225 <= g <= 235) and (225 <= b <= 235)) and not ((220 <= r <= 240) and (240 <= g <= 255) and (210 <= b <= 230)):
            await tap_screen(p, 540, 965, 1)
            chosen = True

    if not chosen:
        r, g, b = im_rgb.getpixel((735, 945))
        if not ((250 <= r <= 255) and (225 <= g <= 235) and (225 <= b <= 235)) and not ((220 <= r <= 240) and (240 <= g <= 255) and (210 <= b <= 230)):
            await tap_screen(p, 875, 965, 1)
            chosen = True

    await tap_screen(p, 540, 1650, 1)  # Done Button


@timer
async def tap_incubate(p):
    logger.info('Action: incubate')
    await tap_incubate_btn(p)
    await tap_free_incubator(p)
    await tap_close_btn(p)


@timer
async def select_egg(p):
    logger.info('Action: select egg')
    await tap_first_egg(p)
