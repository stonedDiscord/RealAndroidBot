from pathlib import Path
import asyncio
import logging
import sys
import re


from action import resize_coords, tap_close_btn, tap_screen, drag_screen, screen_cap, poke_location
from ImageUtils import compare_image, extract_text_from_image, extract_line_from_image

logger = logging.getLogger('rab')

async def find_item(im_rgb, item_to_find, config, section):
    # assuming height of text is constant, 70
    item_y_pos = 0
    for y in range(300, 1620, 5):
        # Section 1
        text_ITEM = im_rgb.crop([340, y, 945, 70 + y])
        text = extract_line_from_image(text_ITEM)

        if text:
            text = text.splitlines()[0].replace('|', '').replace('poke', 'poké').strip()
            if item_to_find.lower() == text:
                logger.info("Item Found: {}".format(text))
                item_y_pos = y
                break
    return item_y_pos


async def delete_item(p, d, section, val, auto_max=False, config=None):
    x, y = 990, 345
    if section == 2:
        y = 725
    elif section == 3:
        y = 1115

    success = True
    await tap_screen(p, x, y, 2)

    if not auto_max:
        await tap_screen(p, 285, 915, 1.5)

    im_rgb = await screen_cap(d)
    if int(val) > 1:
        # if we want to keep up to certain value
        # get total number
        s = extract_text_from_image(im_rgb, binary=True, threshold=220, reverse=False)
        m = re.search(r'(\d+).+cancel', s)
        if m:
            total_items = abs(int(m.group(1)))
            if total_items > int(val):
                items_to_delete = total_items - val
                logger.info(f'Deleting {items_to_delete} items...')
                # if not auto_max:
                #    item_to_delete = item_to_delete - 1
                for x in range(items_to_delete):
                    await tap_screen(p, 795, 915, 0.25)
            else:
                success = False
        else:
            logger.warning(f'Unable to retrieve values. RAB Debug: {s}...')
            success = False
    else:
        logger.info('Deleting all...')
        # if not
    if success:
        await tap_screen(p, 540, 1220, 1.5)
    else:
        await tap_screen(p, 540, 1350, 1.5)

    return success


async def use_item(p, d, section, val, config=None):
    x, y = 150, 345
    if section == 2:
        y = 725
    elif section == 3:
        y = 1115

    success = True
    await tap_screen(p, x, y, 2)

    im_rgb = await screen_cap(d)
    im_rgb = im_rgb.crop([170, 275, 280, 330])
    s = extract_line_from_image(im_rgb)
    logger.debug(f'Have {s}')
    s = ''.join(i for i in s if i.isdigit())
    try:
        s = int(s)
    except ValueError:
        s = 1

    if val > s:
        val = s

    for chosen in range(val):
        await tap_screen(p, poke_location[chosen].get('x'), poke_location[chosen].get('y'), 0.5)

    if val != s:
        await tap_close_btn(p)

    return success


async def check_items(p, d, config):
    offset = config['client'].get('screen_offset', 0)
    #builder = MyBuilder()
    # lets cut up this image and get the text of each segment
    auto_max = config['item_management'].get('auto_max', False)
    last_item_quit = config['item_management'].get('last_item_quit', 'something that will not match').lower()

    i = 0
    continue_loop = True
    last_image = None

    logger.info("Checking items...")

    # Assume we are at map
    await tap_screen(p, 540, 1780, 2)  # Pokeball/Menu
    await tap_screen(p, 840, 1600, 3)  # Items
    # throw text found into another function to match text
    track_item = []
    while continue_loop:
        while True:
            i += 1
            logger.debug("ITEM PAGE: {}".format(i))
            im_rgb = await screen_cap(d)
            # Section 1
            text_ITEM1 = im_rgb.crop([340, 300 + offset, 925, 450 + offset])
            text_ITEM1 = extract_line_from_image(text_ITEM1)

            if text_ITEM1:
                text_ITEM1 = text_ITEM1.splitlines()[0].replace('|', '').replace('poke', 'poké').strip()
                logger.debug("Text: {}".format(text_ITEM1))
                if config['item_config_use'].get(text_ITEM1, 0) and text_ITEM1 not in track_item:
                    logger.info(f'Using {text_ITEM1}')
                    if await use_item(p, d, 1, config['item_config_use'].get(text_ITEM1, 0), config):
                        track_item.append(text_ITEM1)
                        break
                if config['item_config'].get(text_ITEM1, 0) and text_ITEM1 not in track_item:
                    logger.info(f'Deleting {text_ITEM1}')
                    if await delete_item(p, d, 1, config['item_config'].get(text_ITEM1, 0), auto_max, config):
                        track_item.append(text_ITEM1)
                        break
                if (last_item_quit in text_ITEM1.lower() and last_item_quit != '') or len(text_ITEM1) >= 25 or text_ITEM1 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # Section 2
            text_ITEM2 = im_rgb.crop([340, 680 + offset, 925, 850 + offset])
            text_ITEM2 = extract_line_from_image(text_ITEM2)

            if text_ITEM2:
                text_ITEM2 = text_ITEM2.splitlines()[0].replace('|', '').strip().replace('poke', 'poké').strip()
                logger.debug("Text: {}".format(text_ITEM2))
                if config['item_config_use'].get(text_ITEM2, 0) and text_ITEM2 not in track_item:
                    logger.info(f'Using {text_ITEM2}')
                    if await use_item(p, d, 2, config['item_config_use'].get(text_ITEM2, 0), config):
                        track_item.append(text_ITEM2)
                        break
                if config['item_config'].get(text_ITEM2, 0) and text_ITEM2 not in track_item:
                    logger.info(f'Deleting {text_ITEM2}')
                    if await delete_item(p, d, 2, config['item_config'].get(text_ITEM2, 0), auto_max, config):
                        track_item.append(text_ITEM2)
                        break
                if (last_item_quit in text_ITEM2.lower() and last_item_quit != '') or len(text_ITEM2) >= 26 or text_ITEM2 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # Section 3
            text_ITEM3 = im_rgb.crop([340, 1070 + offset, 925, 1230 + offset])
            text_ITEM3 = extract_line_from_image(text_ITEM3)

            if text_ITEM3:
                text_ITEM3 = text_ITEM3.splitlines()[0].replace('|', '').strip().replace('poke', 'poké').strip()
                logger.debug("Text: {}".format(text_ITEM3))
                if config['item_config_use'].get(text_ITEM3, 0) and text_ITEM3 not in track_item:
                    logger.info(f'Using {text_ITEM3}')
                    if await use_item(p, d, 3, config['item_config_use'].get(text_ITEM3, 0), config):
                        track_item.append(text_ITEM3)
                        break
                if config['item_config'].get(text_ITEM3, 0) and text_ITEM3 not in track_item:
                    logger.info(f'Deleting {text_ITEM3}')
                    if await delete_item(p, d, 3, config['item_config'].get(text_ITEM3, 0), auto_max, config):
                        track_item.append(text_ITEM3)
                        break
                if (last_item_quit in text_ITEM3.lower() and last_item_quit != '') or len(text_ITEM3) >= 26 or text_ITEM3 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # Section 4
            text_ITEM4 = im_rgb.crop([340, 1445 + offset, 925, 1610 + offset])
            text_ITEM4 = extract_line_from_image(text_ITEM4)

            if text_ITEM4:
                text_ITEM4 = text_ITEM4.splitlines()[0].replace('|', '').strip().replace('poke', 'poké').strip()
                logger.debug("Text: {}".format(text_ITEM4))
                if (last_item_quit in text_ITEM4.lower() and last_item_quit != '') or len(text_ITEM4) >= 26 or text_ITEM4 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # let's shift the page down
            drag_screen(d, 989, 1500, 989, 347, 4)  # test y = 383 or y = 384
            await asyncio.sleep(5)

            if not last_image:
                last_image = im_rgb
            else:
                img_diff_value = compare_image(im_rgb, last_image)
                last_image = im_rgb
                if img_diff_value <= 500000:
                    break

            if i == 20:
                # too many pages, let's close and get out
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                break
