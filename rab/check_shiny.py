import asyncio
import logging
import random
import time

import numpy as np
from PIL import Image

from ImageUtils import save_screenshot
from action import tap_screen, screen_cap, tap_close_btn, tap_exit_btn, tap_caught_ok_btn, tap_warning_ok_btn
from page_detection import is_catch_pokemon_page, is_pokestop_page, is_gym_page, is_home_page, is_team_rocket_page, is_team_selection, \
                            is_join_raid_battle, is_weather_warning_page, is_warning_page
from utils import Unknown

logger = logging.getLogger(__name__)


async def start_apps(d):
    d.app_stop("com.nianticlabs.pokemongo")
    d.app_stop("com.theappninjas.fakegpsjoystick")
    d.app_start("com.pokemod.espresso", stop=True)
    d.app_wait("com.pokemod.espresso")
    await asyncio.sleep(2.0)
    d.click(770, 635)
    await asyncio.sleep(1.0)
    d.click(540, 835)
    await asyncio.sleep(30.0)
    d.click(540, 1400)

    # tap go plus
    d.long_click(988, 445, 2.0)

async def load_spawns(p, d, target_pokemon, timeout=90, config = None, zoomout=True, pgsharp_client = None, mad_client = None, lat=0, lng=0):
    if not lat:
        if pgsharp_client:
            try:
                await tap_screen(p, target_pokemon['screen_x'], target_pokemon['screen_y'], 1)
                lat, lng = await pgsharp_client.get_location(p,d)
                target_pokemon['latitude'], target_pokemon['longitude'] = lat, lng
            except:
                logger.error('Unable to get location, skipping...')
                return False
        else:
            lat, lng = target_pokemon['latitude'], target_pokemon['longitude']
    
    amplitude = 0.00015
    t0 = time.time()
    t1 = t0 + timeout
    if not pgsharp_client:
        await p.goto_location(lat, lng, 0.5)
        await asyncio.sleep(1.0)

    success_load = True
    while True:
        logger.info('>>>>> Start moving around to load spawns >>>>>')
        
        if time.time() > t0 + 60:
            logger.warning('Walked for {} sec.'.format(60))
            success_load = False
            break

        if not pgsharp_client:
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)

        # check if the sightings appear
        im_rgb = await screen_cap(d)
        im_cropped = im_rgb.crop((800, 1750, 1060, 1800))
        im_cropped = im_cropped.convert('L')
        im_array = np.array(im_cropped)
        width, height = im_array.shape
        im_array_new = np.zeros((width, height))
        for i in range(width):
            for j in range(height):
                im_array_new[i, j] = 0 if 210 <= im_array[i, j] <= 255 else 1
        if im_array_new.sum() >= 1000:
            logger.info('Nearby sightings are loaded (sum: {}).'.format(im_array_new.sum()))
            save_screenshot(Image.fromarray(im_array), sub_dir='sighting', save=False)
            break
        
        if is_weather_warning_page(im_rgb):
            logger.info('Weather warning detected')
            await tap_warning_ok_btn(p)
    return success_load

async def load_tap_pokemon(p, d, pokemon, target_pokemon, timeout=90, config = None, zoomout=True, pgsharp_client = None, mad_client = None):
    logger.info('Start moving around and tapping.')
    amplitude = 0.00015
    t0 = time.time()
    t1 = t0 + timeout
    if pgsharp_client:
        try:
            await tap_screen(p, target_pokemon['screen_x'], target_pokemon['screen_y'], 1)
            lat, lng = await pgsharp_client.get_location(p,d)
            target_pokemon['latitude'], target_pokemon['longitude'] = lat, lng
        except:
            logger.error('Unable to get location, skipping...')
            return False
    else:
        lat, lng = target_pokemon['latitude'], target_pokemon['longitude']
        
    await load_spawns(p, d, target_pokemon, timeout, config, zoomout, pgsharp_client, mad_client, lat, lng)
    
    i = 0 # to prevent clicking into places that cannot be recongized
    while True:
        logger.info('>>>>> Start tapping spawns >>>>>')

        if time.time() > t1:
            logger.warning('No spawn after {} sec.'.format(timeout))
            break

        if pgsharp_client:
            for y in range(1260, 1180, -10):
                await tap_screen(p, 540, y, 0.2)
                if await pgsharp_client.pokemon_encountered(p, d, pokemon):
                    break
        elif mad_client:
            for y in range(1260, 1180, -10):
                await tap_screen(p, 540, y, 0.2)
                if pokemon.update_stats_from_mad(p,d):
                    break   
        elif zoomout and not pgsharp_client:
            if pokemon.name in config['snipe'].get('mon_at_high_location', ['Burmy', 'Zubat']):
                await tap_screen(p, 540, 1190, 0.25)
            else:
                await tap_screen(p, 540, 1260, 0.25)
                im_rgb = await screen_cap(d)
                if is_home_page(im_rgb):
                    await tap_screen(p, 540, 1260, 0.25)
                    im_rgb = await screen_cap(d)
                    if is_home_page(im_rgb):
                        await tap_screen(p, 540, 1240, 0.25)
                        im_rgb = await screen_cap(d)
                        if is_home_page(im_rgb):
                            await tap_screen(p, 540, 1240, 0.25)
                            im_rgb = await screen_cap(d)
                            if is_home_page(im_rgb):
                                await tap_screen(p, 540, 1210, 0.25)
                                im_rgb = await screen_cap(d)
                                if is_home_page(im_rgb):
                                    await tap_screen(p, 540, 1210, 0.25)
                                    im_rgb = await screen_cap(d)
                                    if is_home_page(im_rgb):
                                        await tap_screen(p, 540, 1170, 0.25)
                                        im_rgb = await screen_cap(d)
                                        if is_home_page(im_rgb):
                                            await tap_screen(p, 540, 1170, 0.25)
        elif not pgsharp_client:
            if pokemon.name in config['snipe'].get('mon_at_high_location', ['Burmy', 'Zubat']):
                await tap_screen(p, 540, 1200, 0.25)
            else:
                await tap_screen(p, 540, 1320, 0.25)
                im_rgb = await screen_cap(d)
                if is_home_page(im_rgb):
                    await tap_screen(p, 540, 1280, 0.25)
                    im_rgb = await screen_cap(d)
                    if is_home_page(im_rgb):
                        await tap_screen(p, 540, 1200, 0.25)
                        im_rgb = await screen_cap(d)
                        if is_home_page(im_rgb):
                            await tap_screen(p, 540, 1320, 0.25)
                            im_rgb = await screen_cap(d)
                            if is_home_page(im_rgb):
                                await tap_screen(p, 540, 1280, 0.25)
                                im_rgb = await screen_cap(d)
                                if is_home_page(im_rgb):
                                    await tap_screen(p, 540, 1200, 0.25)
            #if i in [1, 5, 9]:
            #    await tap_screen(p, 540, 1240, 1)
            #elif i in [2, 6, 10]:
            #    await tap_screen(p, 540, 1210, 1)
            #elif i in [3, 7, 11]:
            #    await tap_screen(p, 540, 1190, 1)
            #elif i in [4, 8, 12]:
            #    await tap_screen(p, 540, 1170, 1) # super high poke
            #else:
            #    await tap_screen(p, 540, 1210, 1)
            #await tap_screen(p, 540, 1240, 0.25)
            #await tap_screen(p, 540, 1210, 0.25)
            #await tap_screen(p, 540, 1190, 0.25)
            #await tap_screen(p, 540, 1170, 0.25)
        #if target_pokemon['name'] in ['Burmy']:
        #    await tap_screen(p, 540, 1210, 1.5)
        #else:
        #    im_rgb = await screen_cap(d)
        #    save_screenshot(im_rgb, sub_dir='encounter', save=False)
        #    if pokemon.name in ['Yamask']:
        #        for y in range(1228, 1199, -1):
        #            await tap_screen(p, 540, y, 0.1)
        #    else:
        #        for y in range(1228, 1199, -3):
        #            await tap_screen(p, 540, y, 0.1)
            # await tap_screen(p, 540, 1228, 0.25)
            # await tap_screen(p, 540, 1219, 0.25)
            # await tap_screen(p, 540, 1210, 0.25)
            # await tap_screen(p, 540, 1201, 0.25)
            # await tap_screen(p, 540, random.randint(1205, 1220), 1.5)
        # await tap_screen(p, 540, 1220, 1.5)
        im_rgb = await screen_cap(d)
        save_screenshot(im_rgb, sub_dir='encounter', save=False)
        #if pgsharp_client:
        #    await pgsharp_client.pokemon_encountered(p, d, pokemon)
        if config['client'].get('client', '').lower() in ['hal', 'pokemod']:
            pokemon.update_stats_from_pokemod_toast(p, d)
        else:
            pokemon.update_stats_from_pokemod(im_rgb)
        if Unknown.is_(pokemon.iv) or Unknown.is_(pokemon.cp) or Unknown.is_(pokemon.level) or Unknown.is_(pokemon.name):
            im_rgb = await screen_cap(d)
            pokemon.update_stats_from_catch_screen(im_rgb)

        if Unknown.is_not(pokemon.iv) and pokemon.iv == target_pokemon['iv']:
            logger.info('IV matched: {}'.format(pokemon.iv))
            if pokemon.iv != 100:
                # No need to do further check if it's not hundo
                return pokemon

            if Unknown.is_not(pokemon.cp) and pokemon.cp == target_pokemon['cp']:
                logger.info('CP matched: {}'.format(pokemon.cp))
                return pokemon

            if Unknown.is_not(pokemon.level) and pokemon.level == target_pokemon['level']:
                logger.info('LVL matched: {}'.format(pokemon.level))
                return pokemon

        if is_catch_pokemon_page(im_rgb):
            pokemon.update_stats_from_catch_screen(im_rgb)
            if Unknown.is_not(pokemon.cp) and pokemon.cp == target_pokemon['cp']:
                logger.info('CP matched: {} (IV{} | CP{} | LVL{})'
                            .format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                return pokemon
            if Unknown.is_not(pokemon.name) and pokemon.name == target_pokemon['name']:
                logger.info('Name matched: {} (IV{} | CP{} | LVL{})'
                            .format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                return pokemon
            if pokemon.shiny:
                logger.info('Encountered shiny: {} (IV{} | CP{} | LVL{})'
                            .format(pokemon.name, pokemon.iv, pokemon.cp, pokemon.level))
                return pokemon

            #await tap_exit_btn(p)  # exit
            #d.swipe(1040, 960 - 100, 1040, 960 + 100, 0.5)
            return pokemon # dont waste time, let's go next one
            if time.time() > t1:
                logger.warning('No spawn after {} sec.'.format(timeout))
                break
            else:
                continue

        if is_home_page(im_rgb) and not pgsharp_client:
            #d.swipe(1040, 960 - 200, 1040, 960 + 200, 0.5)
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)
            await p.goto_location(lat + random.randint(-1, 1) * amplitude, lng + random.randint(-1, 1) * amplitude, 0.5)
            await p.goto_location(lat, lng, 0.5)
            if time.time() > t1:
                logger.warning('No spawn after {} sec.'.format(timeout))
                break
            else:
                continue
        
        if is_weather_warning_page(im_rgb):
            logger.info('Weather warning detected')
            await tap_warning_ok_btn(p)
            continue
        if is_warning_page(im_rgb):
            logger.info('Travel too fast warning detected')
            await tap_warning_ok_btn(p)
            continue    

        pokestop_status = is_pokestop_page(im_rgb)
        if pokestop_status:
            while True:
                im_rgb = await screen_cap(d)
                if is_team_selection(im_rgb):
                    await tap_exit_btn(p)
                    await asyncio.sleep(1)
                    await tap_screen(p, 540, 960, 1)
                    return False
                
                if is_home_page(im_rgb):
                    return False # Don't waste time, go next one
                else:
                    # press until it's home page
                    # await close_team_rocket(self.p)
                    await tap_close_btn(p) 
                    await asyncio.sleep(0.5)
            await asyncio.sleep(1.0)
            if config.get('resize',False):
                x1 = int(1040/1080*720)
                y1 = int(860/1920*1280)
                x2 = int(1040/1080*720)
                y2 = int(1060/1920*1280)
            else:
                x1 = 1040
                y1 = 860
                x2 = 1040
                y2 = 1060
            d.swipe(x1, y1, x2, y2, 0.5)
            
            if time.time() > t1:
                logger.warning('No spawn after {} sec.'.format(timeout))
                break
            continue

        if is_join_raid_battle(im_rgb): # Due to multiple tap, might land in this page
            await tap_close_btn(p)
            await tap_close_btn(p)
            return False
        
        if is_gym_page(im_rgb):
            await tap_close_btn(p)
            await asyncio.sleep(1.0)
            if config.get('resize',False):
                x1 = int(1040/1080*720)
                y1 = int(860/1920*1280)
                x2 = int(1040/1080*720)
                y2 = int(1060/1920*1280)
            else:
                x1 = 1040
                y1 = 860
                x2 = 1040
                y2 = 1060
            d.swipe(x1, y1, x2, y2, 0.5)
            if time.time() > t1:
                logger.warning('No spawn after {} sec.'.format(timeout))
                break
            else:
                continue

        if is_team_rocket_page(im_rgb):
            await tap_close_btn(p)
            await asyncio.sleep(1.0)
            if config.get('resize',False):
                x1 = int(1040/1080*720)
                y1 = int(860/1920*1280)
                x2 = int(1040/1080*720)
                y2 = int(1060/1920*1280)
            else:
                x1 = 1040
                y1 = 860
                x2 = 1040
                y2 = 1060
            d.swipe(x1, y1, x2, y2, 0.5)
            if time.time() > t1:
                logger.warning('No spawn after {} sec.'.format(timeout))
                break
            else:
                continue
        
        if not is_home_page(im_rgb):
            d.press("back") 
            continue
        
        if time.time() > t1:
            logger.warning('No spawn after {} sec.'.format(timeout))
            break

    
    
    return False