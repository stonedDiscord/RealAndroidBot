from pathlib import Path
import logging
import os
import re
import sys

from ImageUtils import match_template, save_screenshot, crop_bottom_half, crop_top_half, crop_middle, \
    extract_text_from_image, crop_horizontal_piece
from utils import get_average_color, Unknown
from names import POKEMON

logger = logging.getLogger('rab')

# have to add 2 functions from PokemonUtils because cannot import


def get_pokemon_name_from_text(s):
    s = s.lower()
    m = re.search(r'\bparas\b', s)
    if m:
        return 'Paras'

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
        if 'male' or '♂' in s:
            return 'Nidoran♂'
        if 'female' or '♀' in s:
            return 'Nidoran♀'
        logger.error("Gender for Nidoran is not specified.")
        return ''

    pkmn_name_list = [x for x in POKEMON.values() if x != '--']
    for pkmn_name in pkmn_name_list:
        if pkmn_name.lower() in s:
            return pkmn_name

    return Unknown.SMALL


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

    m = re.search(r'\batk\s*(\d+)\s+def\s*(\d+)\s+hp\s*(\d+)\b', s.lower())
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


def match_template_wrapper(template_path, im, threshold, resize_template=False):
    found, has_template = match_template(template_path, im, threshold=threshold, resize_template=resize_template)
    if has_template:
        logger.debug('YES: {} ({:.0f} >= {})'.format(os.path.basename(template_path), found[0], threshold))
        return True
    logger.debug('NO: {} ({:.0f} < {})'.format(os.path.basename(template_path), found[0], threshold))
    return False


def match_key_word_wrapper(im, key_word_list, binary=True, threshold=200):
    text = extract_text_from_image(im, binary=binary, threshold=threshold)
    logger.debug('Found text: {}'.format(text))

    out = []
    for x in key_word_list:
        if x in text:
            out.append(x)
    return out


def is_home_page(im):
    logger.debug("Checking: home page?")
    im_bottom = crop_bottom_half(im)

    th_quest_symbol = 5500000  # orginal is 6300000
    template_path = 'assets/QuestSymbol.png'
    has_quest_symbol = match_template_wrapper(template_path, im_bottom, threshold=th_quest_symbol, resize_template=True)
    # if has_quest_symbol:
    #    logger.debug('YES: found {}'.format(os.path.basename(template_path)))
    #    return True

    th_action_menu = 23500000  # orginal is 25500000, 1.1.0 is 23500000
    template_path = 'assets/btn_action_menu.png'
    has_action_menu_btn = match_template_wrapper(template_path, im_bottom, threshold=th_action_menu)
    if has_action_menu_btn and has_quest_symbol:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return True

    # last restort
    r, g, b = im.getpixel((540, 1730))
    #logger.info("Check location color: R:{} G: {} B: {}".format(r,g,b))
    if ((253 <= r <= 255) and (50 <= g <= 65) and (60 <= b <= 70)):
        logger.debug("Main Menu Pokeball (Red) suspected, closing...")
        return True

    # last restort
    r, g, b = im.getpixel((540, 1710))
    #logger.info("Check location color: R:{} G: {} B: {}".format(r,g,b))
    if ((253 <= r <= 255) and (50 <= g <= 65) and (60 <= b <= 70)):
        logger.debug("Main Menu Pokeball (Red) suspected, closing...")
        return True

    # last restort
    r, g, b = im.getpixel((540, 1775))
    #logger.info("Check location color: R:{} G: {} B: {}".format(r,g,b))
    if ((180 <= r <= 190) and (180 <= g <= 190) and (180 <= b <= 190)):
        logger.debug("GMain Menu Pokeball (Grey) suspected, closing...")
        return True

    # last restort
    r, g, b = im.getpixel((540, 1755))
    #logger.info("Check location color: R:{} G: {} B: {}".format(r,g,b))
    if ((180 <= r <= 190) and (180 <= g <= 190) and (180 <= b <= 190)):
        logger.debug("GMain Menu Pokeball (Grey) suspected, closing...")
        return True

    return False


def is_pokemon_inventory_page(im):
    logger.debug("Checking: pokemon inventory?")
    im_cropped = crop_top_half(im)
    matched = match_key_word_wrapper(im_cropped, ['tag', 'pokémon', 'eggs', 'search'], binary=False)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    else:
        return False


def is_transfer_menu(im):
    logger.debug("Checking: transfer menu?")
    im_cropped = crop_bottom_half(im)
    matched = match_key_word_wrapper(im_cropped, ['appraise', 'transfer', 'favorite'], binary=True)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    else:
        return False


def has_completed_quest_on_map(im):
    logger.debug("Checking: has completed quest?")
    r, g, b = im.getpixel((1000, 1675))
    logger.debug("Check quest icon color: R:{} G: {} B: {}".format(r, g, b))
    if (254 <= r <= 255) and (155 <= g <= 160) and (0 <= b <= 5):
        logger.debug('YES: Has Quest not cleared')
        return True


def is_quest_color(r, g, b):
    if ((233 <= r <= 236) and (139 <= g <= 178) and ( 49 <= b <=  92)):
        return 'orange'
    if ((148 <= r <= 151) and (210 <= g <= 218) and (140 <= b <= 150)):
        return 'bonus'
    if ((253 <= r <= 255) and (170 <= g <= 176) and ( 75 <= b <=  81)):
        return 'light orange'
    if (( 83 <= r <=  89) and (170 <= g <= 176) and (253 <= b <= 255)):
        return 'ar mapping'
    if (( 52 <= r <=  54) and ( 52 <= g <=  54) and ( 52 <= b <=  54)):
        return 'ar mapping'
    if ((180 <= r <= 185) and (120 <= g <= 126) and (200 <= b <= 210)):
        return 'sponsored'
    if ((205 <= r <= 215) and (165 <= g <= 170) and ( 26 <= b <=  33)):
        return 'event'

    return False


def completed_quest_position(im):
    # Find position of quest completed color, add 25 and return y value of of it
    x = 400

    for i in range(600, 1900, 10):
        #r, g, b = im.getpixel((x, 1675))
        r, g, b = get_average_color(x, i, 10, im)
        if (is_quest_color(r, g, b)):
            # return (i + 25)
            #r2, g2, b2 = im.getpixel((x, i + 25))
            r2, g2, b2 = get_average_color(x, i + 25, 10, im)
            if (is_quest_color(r2, g2, b2)):
                return (i + 25)
    return False


def is_catch_pokemon_page(im, is_shadow=False, map_check=False):
    logger.debug("Checking: Pokemon catch page?")
    im_cropped = crop_bottom_half(im)
    # Cannot detech shadow poke, have to think of something here

    # ball_list = ['pokeball', 'greatball', 'ultraball', 'premierball']
    # ball_threshold_list = [10000000]
    th_enc_camera = 10000000  # 17000000
    template_path = 'assets/ui_enc_camera.png'
    has_enc_camera = match_template_wrapper(template_path, crop_horizontal_piece(im, 4, 1), threshold=th_enc_camera)
    if has_enc_camera:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return True

    th_enc_runaway = 10000000  # 14000000
    template_path = 'assets/ui_enc_runaway.png'
    has_enc_runaway = match_template_wrapper(template_path, crop_horizontal_piece(im, 4, 1), threshold=th_enc_runaway)
    if has_enc_runaway:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return True

    # if map_check:
    #    th_berry_button = 15000000
    #    template_path = 'assets/ui_berry_button.png'
    #    has_razzberry_btn = match_template_wrapper(template_path, im_cropped, threshold=th_berry_button)
    #    if has_razzberry_btn:
    #        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
    #        return True

    #    th_pokeball_button = 15000000
    #    template_path = 'assets/ui_pokeball_button.png'
    #    has_pokeball_btn = match_template_wrapper(template_path, im_cropped, threshold=th_pokeball_button)
    #    if has_pokeball_btn:
    #        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
    #        return True
    # if is_shadow:
        # This is last resort for pokemon has no pokeball (shadow/raid/etc)
    im_cropped = crop_horizontal_piece(im, 2, 1)
    s1 = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=False)
    s2 = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)
    text = re.sub(r'\s+', ' ', ' '.join([s1, s2])).strip()
    # text = extract_text_from_image(im_cropped)
    logger.debug("Found text: {}".format(text))
    #name = get_pokemon_name_from_text(text)
    atk_iv, def_iv, sta_iv = check_pm_iv_comb(text)
    if Unknown.is_not(atk_iv) or Unknown.is_not(def_iv) or Unknown.is_not(sta_iv):
        logger.debug('YES: found ({} | {} | {} | {} )'.format(text, atk_iv, def_iv, sta_iv))
        return True

    if '???' in text:
        logger.debug('YES: found unkown cp')
        return True

    #tmp_cp = check_pm_cp(text)
    # if Unknown.is_not(tmp_cp):
    #    logger.debug('YES: found by cp')
    #    return True

    if is_shadow:
        im_cropped = crop_horizontal_piece(im, 2, 1)
        text = extract_text_from_image(im_cropped)
        logger.debug("Found text: {}".format(text))
        name = get_pokemon_name_from_text(text)
        # atk_iv, def_iv, sta_iv = check_pm_iv_comb(text)
        if Unknown.is_not(name):
            logger.debug('Found base on name')
            return True

    logger.debug('NO: Pokemon Catch Page')
    return False


def is_trainer_battle(im):
    logger.debug("Checking: trainer battle?")
    im_cropped = crop_top_half(im)

    th_btn_exit = 40000000
    template_path = 'assets/btn_exit.png'
    has_exit_btn = match_template_wrapper(template_path, im_cropped, threshold=th_btn_exit)
    if has_exit_btn:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return True


def is_gym_badge(im):
    logger.debug("Checking: gym badge earned")
    im_cropped = crop_top_half(im)
    matched = match_key_word_wrapper(im_cropped, ['gym', 'badge', 'earned'], binary=False)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    else:
        return False


def is_gym_page(im):
    logger.debug("Checking: gym page?")
    im_cropped = crop_bottom_half(im)

    th_btn_challenge = 40000000
    template_path = 'assets/btn_challenge.png'
    has_challenge_btn = match_template_wrapper(template_path, im_cropped, threshold=th_btn_challenge)
    if has_challenge_btn:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return 'gym_enemy'

    th_btn_deploy_pokemon = 40000000
    template_path = 'assets/btn_deploy_pokemon.png'
    has_deploy_pokemon_btn = match_template_wrapper(template_path, im_cropped, threshold=th_btn_deploy_pokemon)
    if has_deploy_pokemon_btn:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return 'gym_deployable'

    th_btn_pokestop = 40000000
    template_path = 'assets/btn_pokestop.png'
    has_pokestop_btn = match_template_wrapper(template_path, im_cropped, threshold=th_btn_pokestop)
    if has_pokestop_btn:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return 'gym_spinnable'

    matched = match_key_word_wrapper(im_cropped, ['battle', 'private group', 'remote', 'raid pass'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return 'gym_raid'

    th_question_button = 15000000
    template_path = 'assets/btn_question_03_normal_white.png'
    has_gym_question_btn = match_template_wrapper(template_path, im_cropped, threshold=th_question_button)
    if has_gym_question_btn:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return True

    th_raid_question_button = 13000000
    template_path = 'assets/btn_question_normal_white.png'
    has_raid_question_btn = match_template_wrapper(template_path, im_cropped, threshold=th_raid_question_button)
    if has_raid_question_btn:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return True

    matched = match_key_word_wrapper(im_cropped, ['walk closer', 'interact', 'with this', 'gym'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched

    # last restort 1
    r, g, b = im.getpixel((540, 1730))
    logger.debug("Check location color: R:{} G: {} B: {}".format(r, g, b))
    if not ((253 <= r <= 255) and (56 <= g <= 58) and (68 <= b <= 70)):
        r, g, b = im.getpixel((60, 1780))
        #logger.info("Check location color: R:{} G: {} B: {}".format(r,g,b))
        if ((253 <= r <= 255) and (253 <= g <= 255) and (253 <= b <= 255)):
            logger.info("Gym suspected, closing...")
            return True

    # last restort 2
    r, g, b = im.getpixel((980, 220))
    logger.debug("Check location color: R:{} G: {} B: {}".format(r, g, b))
    if (230 <= r <= 240) and (240 <= g <= 255) and (230 <= b <= 240):
        r, g, b = im.getpixel((540, 1730))
        #logger.info("Check location color: R:{} G: {} B: {}".format(r,g,b))
        if not ((253 <= r <= 255) and (56 <= g <= 58) and (68 <= b <= 70)):
            logger.info("Gym suspected, closing...")
            return True

    logger.debug('NO: Gym Page')
    return False


def is_pokestop_page(im):
    # return 1 if pokestop is spinnable
    # return 0 if pokestop is spinned
    # return 2 if pokestop is Grunt
    # return -1 if it's not pokestop
    logger.debug("Checking: pokestop page?")
    im_cropped = crop_top_half(im)
    template_path = 'assets/TroyKeyVector.png'
    found, has_troy_key_vector = match_template(template_path, im_cropped, threshold=7500000, resize_template=True)
    logger.debug('TroyKeyVector Value: {}'.format(found))
    if has_troy_key_vector:
        logger.debug('YES: Pokestop Page: found TroyKeyVector')

    if not has_troy_key_vector:
        r, g, b = im.getpixel((540, 455))
        if (233 <= r <= 253) and (108 <= g <= 118) and (167 <= b <= 187):
            has_troy_key_vector = True
            logger.debug('YES: Pokestop Page: lured')

    #logger.info('DEBUG: {} ({:.0f} >= {})'.format(os.path.basename(template_path), found[0], 7500000))
    if has_troy_key_vector:

        r, g, b = im.getpixel((60, 1800))
        if (130 <= r <= 220) and (90 <= g <= 140) and (210 <= b <= 255):
            # pink
            logger.warning('Pokestop has been spinned.')
            return 'pokestop_spinned'

        if ((49 <= r <= 80) and (50 <= g <= 80) and (51 <= b <= 80)) or ((5 <= r <= 20) and (8 <= g <= 20) and (8 <= b <= 25)):
            # team rocket
            logger.warning('Pokestop has been invaded.')
            return 'pokestop_invaded'
        logger.debug('Pokestop is spinnable.')
        return 'pokestop_spinnable'

    # some detection here to check for lured pokestop
    # else:

    logger.debug('NO: Pokestop Page: TroyKeyVector not found')
    return False


def is_zero_ball(im):
    r, g, b = im.getpixel((405, 1840))
    logger.debug("Check location color: R:{} G: {} B: {}".format(r, g, b))
    if (250 <= r <= 255) and (50 <= g <= 60) and (75 <= b <= 90):
        logger.debug("No Ball Left...")
        return True
    return False


def is_caught_flee(im):
    logger.debug("Checking: pokemon caught?")
    im_cropped = crop_horizontal_piece(im, 2, 1)
    im_cropped2 = crop_horizontal_piece(im, 3, 2)
    s1 = extract_text_from_image(im_cropped, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im_cropped, binary=True, threshold=50, reverse=True)
    s3 = extract_text_from_image(im_cropped2, binary=True, threshold=220, reverse=False)
    s4 = extract_text_from_image(im_cropped2, binary=True, threshold=50, reverse=True)
    text = s1 + ' ' + s2 + ' ' + s3 + ' ' + s4
    text = text.replace('cauaht', 'caught').replace('caraht', 'caught').replace('carnht', 'caught')
    logger.debug('Words: {}'.format(text))

    key_word_list = ['transferred', 'transfered', 'capture', 'caught', 'flee', 'fled', 'successful', 'escaped', 'missed']
    matched = []
    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched

    #matched = match_key_word_wrapper(im_cropped, ['transferred', 'transfered', 'capture', 'caught', 'flee', 'fled'], threshold=220)
    # if len(matched) > 0:
    #    logger.debug('YES: found key word: {}'.format(matched))
    #    return matched
    logger.debug('NO: key word not found')
    return False

# def is_bag_full(im):
#    logger.debug("Checking: bag full?")
#    im_cropped = crop_horizontal_piece(im, 5, 3)
#    matched = match_key_word_wrapper(im_cropped, ['item bag', 'bag is full'], threshold=220)
#    if len(matched) > 0:
#        logger.debug('YES: found key word: {}'.format(matched))
#        return matched
#    logger.debug('NO: key word not found')
#    return False


def is_bag_full(im):
    logger.debug("Checking: bag full?")
    im_cropped = crop_horizontal_piece(im, 3, 2)
    text = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)

    key_word_list = ['item bag', 'bag is full']
    matched = []
    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        logger.warn('Bag Full')
        return matched
    logger.debug('NO: key word not found')
    return False


def is_pokemon_full(im):
    logger.debug("Checking: pokemon inventory full?")
    im_cropped = crop_horizontal_piece(im, 2, 1)
    matched = match_key_word_wrapper(im_cropped, ['storage', 'storage is full',
                                     'transfer pokémon', 'transfer pokemon'], threshold=220)  # 'is full removed
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        logger.warn('Pokemon inventory full')
        return matched
    logger.debug('NO: key word not found')
    return False


def encounter_position(im, pokemon):
    logger.debug("Checking: encounter position")
    im_cropped = im.crop([170, 425, 905, 960])  # middle
    s = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)
    if Unknown.is_(pokemon.name):
        return 540
    #    if pokemon.name.lower() not in s:
    #        logger.info('Pokemon has flew off screen/attacking...')
    #        return -1
    result_s = re.sub('[^0-9a-zA-Z/]+', '', s)
    len_count = len(result_s.replace(' ', ''))
    # print(result_s)
    len_count = len_count - 15  # assume len

    im_cropped = im.crop([170, 290, 540, 960])  # Left
    s = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)
    if ' cp' in s.lower():
        logger.info('Encounter moved left')
        return 270

    im_cropped = im.crop([540, 290, 905, 960])  # right
    s = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)
    if ' cp' not in s.lower() and len_count >= 5:
        logger.info('Encounter moved right')
        return 810

    if ' cp' not in s.lower() and len_count < 5:
        logger.info('Pokemon has flew off screen/attacking...')
        return -1

    return 540


def selection_contains(im):
    logger.debug("Checking: additonal pokemons?")
    im_cropped = crop_horizontal_piece(im, 2, 1)
    matched = match_key_word_wrapper(
        im_cropped, ['selection contains', 'contains these pokémon', 'your selection'], threshold=220)
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_team_rocket_page(im):
    logger.debug("Checking: Grunt page?")
    im_cropped = crop_horizontal_piece(im, 2, 2)
    s1 = extract_text_from_image(im_cropped, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)
    text = s1 + ' ' + s2

    key_word_list = ['grunt', 'runt' 'rocket', 'leader', 'cliff', 'sierra', 'arlo',
                     'collect', 'assembled', 'equip', 'jessie', 'james', 'giovanni', 'battle']
    matched = []
    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        if 'grunt' in matched or 'runt' in matched:
            return 'rocket_grunt'
        if any(x in matched for x in ['leader', 'cliff', 'sierra', 'arlo']):
            return 'rocket_leader'
        if 'giovanni' in matched:
            return 'rocket_giovanni'
        if 'collect' in matched:
            return 'rocket_collect'
        if any(x in matched for x in ['assembled', 'equip']):
            return 'rocket_equip'
        if 'battle' in matched:
            if not is_gym_page(im):
                return 'rocket_???'
            else:
                return False
        return 'rocket_???'

    logger.debug('NO: Rocket Page')
    return False


def is_team_selection(im):
    logger.debug("Checking: Grunt defeated page?")
    key_word_list = ['tap to swap', 'use this party', 'swap', 'battle party']
    im_cropped = crop_bottom_half(im)
    matched = match_key_word_wrapper(im_cropped, key_word_list)
    key_word_list = ['grunt', 'rocket', 'leader', 'collect', 'assembled', 'equip']
    im_cropped = crop_top_half(im)
    matched2 = match_key_word_wrapper(im_cropped, key_word_list)
    matched = matched + matched2
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        if any(x in matched for x in ['grunt', 'tap to swap', 'use this party', 'swap', 'battle party']):
            return 'rocket_grunt'
        if 'rocket' in matched:
            return 'rocket_leader'
        if 'collect' in matched:
            return 'rocket_collect'
        if any(x in matched for x in ['assembled', 'equip']):
            return 'rocket_equip'
        return 'rocket_???'

    logger.debug('NO: key word not found')
    return False


def is_grunt_defeated_page(im):
    logger.debug("Checking: Grunt defeated page?")
    grunt_defeated_word_list = ['hero', 'purifier', 'rescue']
    matched = match_key_word_wrapper(im, grunt_defeated_word_list)
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_shiny_pokemon(im):
    logger.debug("Checking: shiny Pokemon?")
    im_cropped = crop_top_half(im)
    template_path = 'assets/ic_shiny.png'
    found, has_shiny_icon = match_template(template_path, im_cropped, threshold=4000000, resize_template=True)
    if has_shiny_icon:
        logger.debug('Shiny Pokemon: found shiny icon')
        return True
    logger.debug('NOT Shiny Pokemon: shiny icon not found')
    return False


def is_incense(im):
    logger.debug('Checking: adventure incense')
    matched = match_key_word_wrapper(im, ['incense', 'adevnture', 'share'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_egg_hatched_oh(im):
    logger.debug('Checking: oh?')
    im_cropped = crop_top_half(im)
    matched = match_key_word_wrapper(im_cropped, ['oh?'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_egg_hatched_page(im):
    logger.debug("Checking: egg hatched?")
    for template_path in ['assets/Egg_A.png', 'assets/Egg_B.png', 'assets/Egg_C.png', 'assets/Egg_D.png', 'assets/Egg_TR.png']:
        found, has_egg_icon = match_template(template_path, im, threshold=9000000)
        if has_egg_icon:
            logger.debug('YES: found {}'.format(os.path.basename(template_path)))
            return True
    logger.debug('NO: Egg Hatched Page')
    return False


def is_razz_berry_page(im):
    threshold = 30000000
    logger.debug("Checking: razz berry?")
    template_path = 'assets/Item_0701.png'
    im_cropped = crop_horizontal_piece(im, 3, 3)
    found, has_razz_berry = match_template(template_path, im_cropped, threshold=threshold)
    if has_razz_berry:
        logger.debug('YES: {} ({:.0f} >= {})'.format('Razz Berry', found[0], threshold))
        return True
    logger.debug('NO: {} ({:.0f} < {})'.format('Razz Berry', found[0], threshold))
    return False


def is_nanab_berry_page(im):
    threshold = 40000000
    logger.debug("Checking: nanab berry?")
    template_path = 'assets/Item_0703.png'
    im_cropped = crop_horizontal_piece(im, 3, 3)
    found, has_nanab_berry = match_template(template_path, im_cropped, threshold=threshold)
    if has_nanab_berry:
        logger.debug('YES: {} ({:.0f} >= {})'.format('Nanab Berry', found[0], threshold))
        return True
    logger.debug('NO: {} ({:.0f} < {})'.format('Nanab Berry', found[0], threshold))
    return False


def is_pinap_berry_page(im):
    threshold = 50000000
    logger.debug("Checking: pinap berry?")
    template_path = 'assets/Item_0705.png'
    im_cropped = crop_horizontal_piece(im, 3, 3)
    found, has_pinap_berry = match_template(template_path, im_cropped, threshold=threshold)
    if has_pinap_berry:
        logger.debug('YES: {} ({:.0f} >= {})'.format('Pinap Berry', found[0], threshold))
        return True
    logger.debug('NO: {} ({:.0f} < {})'.format('Pinap Berry', found[0], threshold))
    return False


def is_golden_berry_page(im):
    threshold = 35000000
    logger.debug("Checking: golden berry?")
    template_path = 'assets/Item_0706.png'
    im_cropped = crop_horizontal_piece(im, 3, 3)
    # save_screenshot(im_cropped, sub_dir='berry', save=True)
    found, has_golden_berry = match_template(template_path, im_cropped, threshold=threshold)
    if has_golden_berry:
        logger.debug('YES: {} ({:.0f} >= {})'.format('golden Berry', found[0], threshold))
        return True
    logger.debug('NO: {} ({:.0f} < {})'.format('golden Berry', found[0], threshold))
    return False


def is_silver_berry_page(im):
    threshold = 35000000
    logger.debug("Checking: sliver berry?")
    template_path = 'assets/Item_0707.png'
    im_cropped = crop_horizontal_piece(im, 3, 3)
    # save_screenshot(im_cropped, sub_dir='berry', save=True)
    found, has_silver_berry = match_template(template_path, im_cropped, threshold=threshold)
    if has_silver_berry:
        logger.debug('YES: {} ({:.0f} >= {})'.format('Sliver Berry', found[0], threshold))
        return True
    logger.debug('NO: {} ({:.0f} < {})'.format('Sliver Berry', found[0], threshold))
    return False


def is_incubate_page(im):
    logger.debug("Checking: incubate page?")
    matched = match_key_word_wrapper(im, ['incubate', 'use an incubator'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_incubate_page2(im):
    logger.debug("Checking: incubate page?")
    matched = match_key_word_wrapper(im, ['walk to hatch this egg'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_mon_caught_page(im):
    logger.debug("Checking: pokemon caught page?")
    matched = match_key_word_wrapper(crop_middle(im), ['caught', 'gotcha', 'new'], binary=True, threshold=180)
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_mon_details_page(im):
    logger.debug("Checking: pokemon details?")
    s1 = extract_text_from_image(im, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im, binary=True, threshold=200, reverse=True)
    text = s1 + ' ' + s2

    key_word_list = ['weight', 'height', 'stardust', 'candy', 'raids', 'trainer']
    matched = []

    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        if 'atk' in text or 'def' in text:
            logger.debug('This is encounter page')
            return False
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')

    #im_cropped = crop_bottom_half(im)
    # matched = match_key_word_wrapper(im, ['weight', 'height', 'stardust', 'candy', 'raids', 'trainer'], binary=True, threshold=150) # 'battles' remove to prevent raid identify as mon details
    # if len(matched) > 0:
    #    logger.debug('YES: found key word: {}'.format(matched))
    #    return matched
    #logger.debug('NO: key word not found')
    # return False


def is_join_raid_battle(im):
    logger.debug("Checking: join raid battle")
    im_cropped = crop_bottom_half(im)
    matched = match_key_word_wrapper(im_cropped,
                                     ['raid battle', 'pass will', 'be used', 'battle starts'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_power_up_page(im):
    logger.debug("Checking: power up?")
    im_cropped = crop_bottom_half(im)
    matched = match_key_word_wrapper(im_cropped, ['power up'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_shop_page(im):
    logger.debug("Checking: shop page?")
    im_cropped = crop_bottom_half(im)
    matched = match_key_word_wrapper(im_cropped, ['special', 'limited', 'ultra box', 'adventure'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_main_menu_page(im):
    logger.debug("Checking: main menu page?")
    im_cropped = im.crop([70, 790, 965, 1515])
    matched = match_key_word_wrapper(im_cropped, ['shop', 'items', 'pokémon', 'pokemon', 'exit'])
    if len(matched) > 0 and 'exit' not in matched:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_team_selection_vaild(im):
    slot1_vaild = False
    slot2_vaild = False
    slot3_vaild = False

    logger.debug("Checking: pvp team select vaild?")
    im_poke1 = im.crop([75, 1525, 385, 1640])
    im_poke2 = im.crop([385, 1525, 695, 1640])
    im_poke3 = im.crop([695, 1525, 1005, 1640])

    poke1_text = extract_text_from_image(im_poke1, binary=True, threshold=220, reverse=False)
    poke2_text = extract_text_from_image(im_poke2, binary=True, threshold=220, reverse=False)
    poke3_text = extract_text_from_image(im_poke3, binary=True, threshold=220, reverse=False)

    slot1_vaild = True if len(poke1_text) > 3 else False
    slot2_vaild = True if len(poke2_text) > 3 else False
    slot3_vaild = True if len(poke3_text) > 3 else False

    return slot1_vaild, slot2_vaild, slot3_vaild


def is_nearby_page(im):
    logger.debug("Checking: nearby page?")
    im_cropped = crop_top_half(im)
    matched = match_key_word_wrapper(im_cropped, ['nearby', 'radar'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_pokestop_scan_page(im):
    logger.debug("Checking: pokestop scan page?")

    im_cropped = crop_top_half(im)
    im_cropped_bottom = crop_bottom_half(im)
    s1 = extract_text_from_image(im_cropped, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im_cropped_bottom, binary=True, threshold=220, reverse=False)

    text = s1 + ' ' + s2

    key_word_list = ['scanning', 'scan pokéstop', 'scan pokestop']
    matched = []
    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_exit_trainer_dialog(im):
    logger.debug("Checking: exit trainer battle?")

    logger.debug("Checking: pokemon caught page?")
    matched = match_key_word_wrapper(crop_middle(im), ['exit the', 'exit the trainer'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_profile_page(im):
    logger.debug("Checking: profile page?")

    im_cropped = crop_top_half(im)
    im_cropped_bottom = crop_bottom_half(im)
    s1 = extract_text_from_image(im_cropped, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im_cropped_bottom, binary=True, threshold=220, reverse=False)

    text = s1 + ' ' + s2

    key_word_list = ['friend', 'play', 'online', 'gift', 'send', 'trade', 'bubby', 'together']
    matched = []
    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_quest_page(im):
    logger.debug("Checking: quest page?")

    im_cropped = crop_top_half(im)
    th_quest_symbol = 5400000
    template_path = 'assets/QuestSymbol.png'
    has_quest_symbol = match_template_wrapper(template_path, im_cropped, threshold=th_quest_symbol, resize_template=True)
    if has_quest_symbol:
        logger.debug('YES: found {}'.format(os.path.basename(template_path)))
        return True

    s1 = extract_text_from_image(im, binary=True, threshold=220, reverse=False)
    s2 = extract_text_from_image(im, binary=True, threshold=200, reverse=True)
    text = s1 + ' ' + s2

    key_word_list = ['today', 'field', 'special', 'research', 'progress', 'celebration']
    matched = []
    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_mysterious_pokemon(im):
    logger.debug('Checking: mysterious pokemon?')
    im_cropped = crop_top_half(im)
    matched = match_key_word_wrapper(im_cropped, ['mysterious pokémon', 'mysterious', 'field research completed'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_warning_page(im):
    logger.debug('Checking: warning page?')
    im_cropped = crop_bottom_half(im)
    matched = match_key_word_wrapper(im_cropped, ['do not', 'while', 'dangerous', 'surroundings', 'communities',
                                     'areas', 'real-world', 'driving', 'pokémon go', 'pokemon go'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_weather_warning_page(im):
    logger.debug('Checking: weather warning page?')
    im_cropped = crop_middle(im)

    s1 = extract_text_from_image(im_cropped, binary=True, threshold=200, reverse=True)

    text = s1

    key_word_list = ['weather warning', 'weather conditions']
    matched = []
    for x in key_word_list:
        if x in text:
            matched.append(x)

    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_plus_disconnected(im, offset=0):
    for i in range(400, 460+offset):
        r, g, b = im.getpixel((990, i))
        #logger.info("Check location color: R:{} G: {} B: {}".format(r,g,b))
        if (145 <= r <= 155) and (90 <= g <= 100) and (110 <= b <= 150):
            logger.debug("Pokemon Go Plus disconnected...")
            return True
    return False


def is_error_page(im):
    logger.debug('Checking: error page?')
    matched = match_key_word_wrapper(im, ['unknown', 'error'])
    if len(matched) > 0:
        logger.debug('YES: found key word: {}'.format(matched))
        return matched
    logger.debug('NO: key word not found')
    return False


def is_not_pokestop_gym_on_map(im, x, y):
    object_not_found = True
    x = x - 3
    y = y - 3
    r, g, b = get_average_color(x, y, 6, im)
    if (30 <= r <= 90) and (200 <= g <= 255) and (250 <= b <= 255):
        object_not_found = False
    elif (0 <= r <= 50) and (100 <= g <= 120) and (220 <= b <= 255):
        object_not_found = False
    elif (160 <= r <= 200) and (100 <= g <= 120) and (220 <= b <= 255):
        object_not_found = False
    elif (120 <= r <= 140) and (220 <= g <= 255) and (220 <= b <= 255):
        object_not_found = False
    elif (190 <= r <= 210) and (190 <= g <= 210) and (200 <= b <= 220):  # grey
        object_not_found = False
    elif (240 <= r <= 255) and (240 <= g <= 255) and (240 <= b <= 255):  # almost white
        object_not_found = False
    elif (240 <= r <= 255) and (0 <= g <= 60) and (0 <= b <= 60):
        object_not_found = False
    elif (0 <= r <= 60) and (0 <= g <= 50) and (245 <= b <= 255):
        object_not_found = False
    elif (240 <= r <= 255) and (100 <= g <= 115) and (0 <= b <= 50):
        object_not_found = False
    elif (240 <= r <= 255) and (220 <= g <= 255) and (0 <= b <= 5):
        object_not_found = False
    return object_not_found
