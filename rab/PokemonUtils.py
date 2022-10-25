from pathlib import Path
import logging
import re
import sys

from ImageUtils import crop_horizontal_piece, extract_text_from_image, save_screenshot, crop_top_half, crop_top_by_percent
from names import POKEMON
from page_detection import is_shiny_pokemon
from utils import Unknown, get_level_to_cpm, get_base_stats

logger = logging.getLogger('rab')

level_to_cpm = get_level_to_cpm()

y_atk = 0
y_def = 0
y_sta = 0
x_start_position = 0
x_step = 0


def cp_from_level(dex, level, poke_atk, poke_def, poke_sta):
    cp_index = ((level * 2) - 2)
    base_stats = get_base_stats(dex)
    cp = int(((base_stats.get('attack') + poke_atk) * (base_stats.get('defense') + poke_def) **
             0.5 * (base_stats.get('stamina') + poke_sta)**0.5 * level_to_cpm[cp_index]**2) / 10)
    return cp


def level_from_cp(dex, cp, poke_atk, poke_def, poke_sta):
    base_stats = get_base_stats(dex)
    level = 1
    level_found = False
    for each_cpm in level_to_cpm:
        if round(((base_stats.get('attack') + poke_atk) * (base_stats.get('defense') + poke_def)**0.5 * (base_stats.get('stamina') + poke_sta)**0.5 * each_cpm**2) / 10) >= cp:
            level_found = True
            break
        level += 1
    if level_found:
        temp = level / 2
        if temp - int(temp) == 0:
            return temp
        else:
            temp = temp + 0.5
            return temp
    else:
        return False
    return False


def level_from_cpm(cp_multiplier):
    return min(range(len(level_to_cpm)), key=lambda i: abs(level_to_cpm[i] - cp_multiplier)) * 0.5 + 1


def get_pokemon_name_from_text(s):
    s = s.lower()
    m = re.search(r'\bparas\b', s)
    if m:
        return 'Paras'

    m = re.search(r'\bexegecute\b', s)
    if m:
        return 'Exeggcute'

    m = re.search(r'\babra\b', s)
    if m:
        return 'Abra'

    m = re.search(r'\bmarill\b', s)
    if m:
        return 'Marill'

    m = re.search(r'\bklink\b', s)
    if m:
        return 'Klink'

    m = re.search(r'\bklang\b', s)
    if m:
        return 'Klang'

    m = re.search(r'\bswoobat\b', s)
    if m:
        return 'Swoobat'

    if 'parasect' in s:
        return 'Parasect'

    if 'kadabra' in s:
        return 'Kadabra'

    if 'azumarill' in s:
        return 'Azumarill'

    if 'klinklang' in s:
        return 'Klinklang'

    if 'mewtwo' in s:
        return 'Mewtwo'

    if 'farfetch' in s:
        return "Farfetch'd"

    if 'mime' in s and 'mr' in s:
        return 'Mr. Mime'

    if 'mime' in s and 'jr' in s:
        return 'Mime Jr.'

    if 'nidoran' in s:
        if 'female' in s or '♀' in s:
            return 'Nidoran♀'
        if 'male' in s or '♂' in s:
            return 'Nidoran♂'
        logger.error("Gender for Nidoran is not specified")
        return ''

    pkmn_name_list = [x for x in POKEMON.values() if x != '--']
    for pkmn_name in pkmn_name_list:
        if pkmn_name.lower() in s:
            return pkmn_name

    return Unknown.SMALL


def check_pm_iv(s):
    if '💯' in s:
        return 100

    m = re.search(r'\biv:?\s*(\d+)\b', s.lower())
    if m:
        return int(m.group(1))

    m = re.search(r'(\d+)%', s.lower())
    if m:
        return int(m.group(1))

    return Unknown.TINY


def check_pm_iv_comb(s):
    # attack / defense / stamina
    m = re.search(r'\b(\d+)/(\d+)/(\d+)\b', s)
    if m:
        atk = int(m.group(1))
        dfs = int(m.group(2))
        sta = int(m.group(3))

        atk_iv = atk if 0 <= atk <= 15 else Unknown.TINY
        def_iv = dfs if 0 <= dfs <= 15 else Unknown.TINY
        sta_iv = sta if 0 <= sta <= 15 else Unknown.TINY
        return atk_iv, def_iv, sta_iv

    m = re.search(r'\batk\s*(\d+)\s+\|\s+def\s*(\d+)\s+\|\s+sta\s*(\d+)\b', s.lower())
    if m:
        atk = int(m.group(1))
        dfs = int(m.group(2))
        sta = int(m.group(3))
        atk_iv = atk if 0 <= atk <= 15 else Unknown.TINY
        def_iv = dfs if 0 <= dfs <= 15 else Unknown.TINY
        sta_iv = sta if 0 <= sta <= 15 else Unknown.TINY
        return atk_iv, def_iv, sta_iv

    m = re.search(r'\batk\s*(\d+)\s+def\s*(\d+)\s+hp\s*(\d+)\b', s.lower())
    if m:
        atk = int(m.group(1))
        dfs = int(m.group(2))
        sta = int(m.group(3))
        atk_iv = atk if 0 <= atk <= 15 else Unknown.TINY
        def_iv = dfs if 0 <= dfs <= 15 else Unknown.TINY
        sta_iv = sta if 0 <= sta <= 15 else Unknown.TINY
        return atk_iv, def_iv, sta_iv

    m = re.search(r'a(\d+) ?/ ?d(\d+) ?/ ?s(\d+)', s.lower())
    if m:
        atk = int(m.group(1))
        dfs = int(m.group(2))
        sta = int(m.group(3))
        atk_iv = atk if 0 <= atk <= 15 else Unknown.TINY
        def_iv = dfs if 0 <= dfs <= 15 else Unknown.TINY
        sta_iv = sta if 0 <= sta <= 15 else Unknown.TINY
        return atk_iv, def_iv, sta_iv

    return Unknown.TINY, Unknown.TINY, Unknown.TINY


def check_pm_cp(s):
    m = re.search(r"\bcp\s*(\d+)\b", s.lower())
    return int(m.group(1)) if m else Unknown.TINY


def check_pm_gender(s):
    if 'female' in s.lower() or '♀' in s:
        return 'Female'

    if 'male' in s.lower() or '♂' in s:
        return 'Male'

    if 'genderless' in s.lower() or 'neutral' in s.lower() or u'\u26b2' or u'\u26A4' or u'\u26A5' in s.lower():
        return 'Genderless'

    return Unknown.TINY


def check_pm_level(s):
    m = re.search(r"\b(?:level|lvl|lv|l|wi|vi|ti|iwi|t.|t):? ?(\d+)\b", s.lower())
    return int(m.group(1)) if m and int(m.group(1)) < 35 else Unknown.TINY


def get_stats_from_polygon(data):
    # {'encounterId': '5426974339150050516', 'lastModifiedMs': '1610155683687', 'latitude': 1.2892464083114312, 'longitude': 103.84848207392109, 'spawnPointId': '31da19a09cd', 'pokemon': {'pokemonId': 'SHELLOS', 'cp': 199, 'stamina': 65, 'maxStamina': 65, 'move1': 'MUD_SLAP_FAST', 'move2': 'MUD_BOMB', 'heightM': 0.29722938, 'weightKg': 7.305354, 'individualAttack': 6, 'individualDefense': 15, 'individualStamina': 4, 'cpMultiplier': 0.34921268, 'pokemonDisplay': {'gender': 'MALE', 'form': 'SHELLOS_EAST_SEA', 'weatherBoostedCondition': 'RAINY', 'displayId': '5426974339150050516'}, 'originDetail': {}}}
    pokemon = dict()

    poke_cp_bm = data['pokemon'].get('cpMultiplier')
    # Changeable part of the CP multiplier, increasing at power up
    poke_cp_am = data['pokemon'].get('additionalCpMultiplier', .0)
    # Resulting CP multiplier
    poke_cp_m = poke_cp_bm + poke_cp_am

    pokemon['name'] = data['pokemon'].get('pokemonId').replace('_', ' ').title()
    if data['pokemon']['pokemonDisplay'].get('form', ''):
        pokemon['form'] = data['pokemon']['pokemonDisplay'].get('form').replace(
            data['pokemon'].get('pokemonId'), '').replace('_', ' ').title().strip()
    pokemon['cp'] = data['pokemon'].get('cp', 0)
    pokemon['level'] = level_from_cpm(poke_cp_m)
    pokemon['atk_iv'] = data['pokemon'].get('individualAttack', 0)
    pokemon['def_iv'] = data['pokemon'].get('individualDefense', 0)
    pokemon['sta_iv'] = data['pokemon'].get('individualStamina', 0)
    pokemon['gender'] = data['pokemon']['pokemonDisplay'].get('gender').title()
    if 'shiny' in data['pokemon']['pokemonDisplay']:
        pokemon['shiny'] = True
        logger.info("Pokemon is shiny.")

    logger.debug(pokemon)
    return pokemon


def get_stats_from_pokemod(im):
    pokemon = dict()
    im_cropped = crop_top_by_percent(im, 70)
    save_screenshot(im_cropped, sub_dir='pokemod', save=False)
    s1 = extract_text_from_image(im_cropped, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)
    text = re.sub(r':', ' ', ' '.join([s1, s2])).strip()
    logger.debug("Check toast: {}".format(text))

    pokemon['name'] = get_pokemon_name_from_text(text)
    pokemon['cp'] = check_pm_cp(text)
    pokemon['level'] = check_pm_level(text)
    pokemon['atk_iv'], pokemon['def_iv'], pokemon['sta_iv'] = check_pm_iv_comb(text)
    pokemon['iv'] = check_pm_iv(text)
    pokemon['gender'] = check_pm_gender(text)

    # if '+f' in text or '+4' in text:
    #    pokemon['shiny'] = True
    #    logger.info("Pokemon is shiny (from toast).")
    if is_shiny_pokemon(im):
        pokemon['shiny'] = True
        logger.info("Pokemon is shiny (from icon).")

    logger.debug(pokemon)
    return pokemon


def get_stats_from_text(text):
    pokemon = dict()

    if '✨' in text:
        pokemon['shiny'] = True

    pokemon['level'] = check_pm_level(text)

    # get iv combination
    pokemon['atk_iv'], pokemon['def_iv'], pokemon['sta_iv'] = check_pm_iv_comb(text)

    pokemon['gender'] = check_pm_gender(text)

    pokemon['iv'] = check_pm_iv(text)

    pokemon['name'] = get_pokemon_name_from_text(text)

    pokemon['cp'] = check_pm_cp(text)

    logger.debug(pokemon)
    return pokemon


def get_stats_from_mon(im):
    logger.debug('Checking pokemon stats from pokemon details.')
    # Search for individual IV
    # defaulted to 1, if not detected will transfer
    pokemon = dict()
    #im_cropped = im.crop([270, 870, 800, 1015])
    im_cropped = crop_horizontal_piece(im, 3, 2)
    text = extract_text_from_image(im_cropped).replace("\n", " ")
    pokemon['name'] = get_pokemon_name_from_text(text)

    pokemon['level'] = check_pm_level(text)
    if not pokemon.get('level', False):
        im_cropped = crop_horizontal_piece(im, 3, 1)

        s2 = extract_text_from_image(im_cropped, binary=True, threshold=250, reverse=True)

        text = re.sub('[^a-zA-Z0-9]+', ' ', s2)
        logger.debug('Debug Text: {}'.format(text))
        num_list = [int(s) for s in re.findall(r"[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", text)]

        if len(num_list) >= 1:
            pokemon['cp'] = int(num_list[0])

    # get iv combination
    pokemon['atk_iv'], pokemon['def_iv'], pokemon['sta_iv'] = check_pm_iv_comb(text)
    return pokemon


def get_stats_from_catch_screen(im):
    # crop the image with Pokemon name, CP and shiny icon
    pokemon = dict()
    im_cropped = crop_top_by_percent(im, 70)
    save_screenshot(im_cropped, sub_dir='encounter', save=False)
    s1 = extract_text_from_image(im_cropped, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)
    text = re.sub(r'\s+', ' ', ' '.join([s1, s2])).strip()
    # text = extract_text_from_image(im_cropped)
    logger.debug("Found text: {}".format(text))

    # get name
    pokemon['name'] = get_pokemon_name_from_text(text)
    if Unknown.is_(pokemon['name']):
        save_screenshot(im_cropped, sub_dir='exception', save=False)

    # get cp value
    pokemon['cp'] = check_pm_cp(text)

    pokemon['level'] = check_pm_level(text)

    # get iv combination
    pokemon['atk_iv'], pokemon['def_iv'], pokemon['sta_iv'] = check_pm_iv_comb(text)

    if Unknown.is_(pokemon['cp']):
        im_cropped = crop_horizontal_piece(im, 3, 1)

        s2 = extract_text_from_image(im_cropped, binary=True, threshold=250, reverse=True)

        text = re.sub('[^a-zA-Z0-9]+', ' ', s2)
        logger.debug('Debug Text: {}'.format(text))
        num_list = [int(s) for s in re.findall(r"[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", text)]

        if len(num_list) >= 1:
            pokemon['cp'] = int(num_list[0])

    if is_shiny_pokemon(im):
        pokemon['shiny'] = True
        logger.info("Pokemon is shiny (from icon).")

    logger.debug(pokemon)
    return pokemon


def get_stats_from_mon_details(im, offset_x=0):
    global y_atk
    global y_def
    global y_sta
    global x_start_position
    global x_step

    logger.debug('Checking pokemon stats from pokemon details.')
    # Search for individual IV
    # defaulted to 1, if not detected will transfer
    pokemon = dict()
    im_cropped = crop_horizontal_piece(im, 3, 2)
    #im_cropped = im.crop([270, 870, 800, 1015])
    text = extract_text_from_image(im_cropped).replace("\n", " ")
    pokemon['name'] = get_pokemon_name_from_text(text)

    tries = 0
    while True:
        tries += 1
        atk_found, def_found, sta_found = False, False, False

        if y_atk == 0:
            # code something here to look for the starting of x and y
            # find y first
            starting_y = 1270
            y_found = 0
            y_atk = 1385
            y_def = 1490
            y_sta = 1590

            x_start_position = 140
            x_end_position = 491

            for i in range(starting_y, 1635):
                r, g, b = im.getpixel((320 + offset_x, i))
                if ((220 <= r <= 230) and (120 <= g <= 130) and (115 <= b <= 125)) or ((220 <= r <= 245) and (140 <= g <= 150) and (15 <= b <= 30)) or ((220 <= r <= 235) and (220 <= g <= 235) and (220 <= b <= 235)):
                    y_atk = i + 8
                    break

            for i in range(y_atk+60, 1635):
                r, g, b = im.getpixel((320 + offset_x, i))
                if ((220 <= r <= 230) and (120 <= g <= 130) and (115 <= b <= 125)) or ((220 <= r <= 245) and (140 <= g <= 150) and (15 <= b <= 30)) or ((220 <= r <= 235) and (220 <= g <= 235) and (220 <= b <= 235)):
                    y_def = i + 8
                    break

            for i in range(y_def+60, 1635):
                r, g, b = im.getpixel((320 + offset_x, i))
                if ((220 <= r <= 230) and (120 <= g <= 130) and (115 <= b <= 125)) or ((220 <= r <= 245) and (140 <= g <= 150) and (15 <= b <= 30)) or ((220 <= r <= 235) and (220 <= g <= 235) and (220 <= b <= 235)):
                    y_sta = i + 8
                    break

            starting_x = 105
            for i in range(starting_x, 180):
                r, g, b = im.getpixel((i, y_atk))
                if ((220 <= r <= 240) and (120 <= g <= 140) and (115 <= b <= 140)) or ((220 <= r <= 245) and (140 <= g <= 160) and (15 <= b <= 50)) or ((220 <= r <= 240) and (220 <= g <= 240) and (220 <= b <= 240)):
                    x_start_position = i
                    break
            ending_x = 441
            for i in range(530, ending_x, -1):
                r, g, b = im.getpixel((i, y_atk))
                if ((220 <= r <= 240) and (120 <= g <= 140) and (115 <= b <= 140)) or ((220 <= r <= 245) and (140 <= g <= 160) and (15 <= b <= 50)) or ((220 <= r <= 240) and (220 <= g <= 240) and (220 <= b <= 240)):
                    x_end_position = i
                    break

            x_step = (x_end_position - x_start_position)/15

        for i in range(1, 16):
            x = int(x_start_position + ((x_step * i) - 11))

            r_atk, g_atk, b_atk = im.getpixel((x, y_atk))
            r_def, g_def, b_def = im.getpixel((x, y_def))
            r_sta, g_sta, b_sta = im.getpixel((x, y_sta))
            if (220 <= r_atk <= 230) and (127 <= g_atk <= 129) and (120 <= b_atk <= 122):
                pokemon['atk_iv'] = 15
                atk_found = True

            if (220 <= r_def <= 230) and (127 <= g_def <= 129) and (120 <= b_def <= 122):
                pokemon['def_iv'] = 15
                def_found = True

            if (220 <= r_sta <= 230) and (127 <= g_sta <= 129) and (120 <= b_sta <= 122):
                pokemon['sta_iv'] = 15
                sta_found = True

            if not atk_found and (220 <= r_atk <= 230) and (220 <= g_atk <= 230) and (225 <= b_atk <= 235):
                pokemon['atk_iv'] = i - 1
                atk_found = True

            if not def_found and (220 <= r_def <= 230) and (220 <= g_def <= 230) and (225 <= b_def <= 235):
                pokemon['def_iv'] = i - 1
                def_found = True

            if not sta_found and (220 <= r_sta <= 230) and (220 <= g_sta <= 230) and (225 <= b_sta <= 235):
                pokemon['sta_iv'] = i - 1
                sta_found = True

        logger.debug(pokemon)
        if not pokemon.get('atk_iv') or not pokemon.get('def_iv') or not pokemon.get('sta_iv'):
            y_atk = 0
        else:
            break

        if tries >= 3:
            break
    return pokemon
