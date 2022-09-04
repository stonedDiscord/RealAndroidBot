# !/usr/bin/env python3.7
import asyncio
import logging
import sys
import re


from action import tap_screen, screen_cap
from ImageUtils import compare_image, crop_middle, extract_text_from_image

logger = logging.getLogger(__name__)
from pathlib import Path
import pytesseract
if sys.platform == 'win32':
    if Path('Tesseract-OCR/tesseract.exe').is_file():
        pytesseract.pytesseract.tesseract_cmd = r'Tesseract-OCR\tesseract.exe'
        tool = pytesseract
    else:
        tool = pytesseract
else:
    tool = pytesseract
    
async def find_item(im_rgb, item_to_find, config, section):
    # assuming height of text is constant, 70 
    item_y_pos = 0
    for y in range(300, 1620, 5):
        # Section 1
        text_ITEM = im_rgb.crop([340, y, 945, 70 + y])
        text = extract_text_from_image(text_ITEM)
        
        if text:
            text = text.splitlines()[0].replace('|', '').replace('poke','poké').strip()
            if item_to_find.lower() == text:
                logger.info("Item Found: {}".format(text))  
                item_y_pos = y
                break
    return item_y_pos
    

async def delete_item(p, d, section, val, auto_max=False, config=None):
    offset = config['client'].get('screen_offset', 0)
    x, y = 0, 0
    if section == 1:
        x, y = 990, 345 + offset
    elif section == 2:
        x, y = 990, 725 + offset
    elif section == 3:
        x, y = 990, 1115 + offset
        
    success = True
    await tap_screen(p, x, y, 2)
    
    if not auto_max:
        await tap_screen(p, 285, 915, 1.5)

    im_rgb = await screen_cap(d)
    if int(val) > 1:
        # if we want to keep up to certain value
        # get total number
        im_cropped = crop_middle(im_rgb)
        s = extract_text_from_image(im_rgb, binary=True, threshold=220, reverse=False)
        #s1 = extract_text_from_image(im_rgb, binary=False, threshold=180, reverse=False)
        logger.debug(f'RAB Debug 1: {s}')  
        m = re.search(r'(\d+).+cancel', s)
        if m:
            total_item = abs(int(m.group(1)))
            if total_item > int(val):
                item_to_delete = total_item - val
                logger.info(f'Deleting {item_to_delete} items...')   
                #if not auto_max:
                #    item_to_delete = item_to_delete - 1
                for x in range(item_to_delete):
                    await tap_screen(p, 795, 915, 0.25)
            else:
                success = False
        else:
            logger.warning(f'Unable to retrieve values. RAB Debug: {s}...')  
            success = False
    else:
        logger.info('Deleting all...')        
        #if not 
    if success:
        await tap_screen(p, 540, 1220, 1.5)
    else:
        await tap_screen(p, 540, 1350, 1.5)
    
    return success

async def delete_item_backup(p, section, auto_max=False, offset=0, config=None):
    x, y = 0, 0
    if section == 1:
        x, y = 990, 345 + offset
    elif section == 2:
        x, y = 990, 725 + offset
    elif section == 3:
        x, y = 990, 1115 + offset
    await tap_screen(p, x, y, 2)  # delete item base on section passed in
    if not auto_max:
        # 790, 915 = + Sign
        # 285, 915 = - Sign
        await tap_screen(p, 285, 915, 1)
        #if config.get('resize',False):
        #    x1 = int(790/1080*720)
        #    y1 = int(840/1920*1280)
        #    x2 = int(190/1080*720)
        #    y2 = int(840/1920*1280)
        #else:
        #    x1 = 790
        #    y1 = 915
        #    x2 = 790
        #    y2 = 915
        #await p.swipe(x1, y1, x2, y2, 10000)  # hold 10 secs
    #await asyncio.sleep(2)
    await tap_screen(p, 540, 1190, 2)  # yes button

async def check_item_backup(p, d, config):
    offset = config['client'].get('screen_offset', 0)
    auto_max = config['item_management'].get('auto_max', False)
    last_item_quit = config['item_management'].get('last_item_quit','').lower()


    # Assume we are at map
    await tap_screen(p, 540, 1780, 2)  # Pokeball/Menu
    await tap_screen(p, 840, 1600, 3)  # Items
    
    page_count = 0
    item_tracker = 0
    delete_x = 990
    delete_y = 0
    
    last_image = None
    
    all_items = config.get('item_config',{})
    while True:
        page_count += 1
        logger.info(f"Page Count: {page_count}")
        im_rgb = await screen_cap(d)
        
        for key, value in all_items.items():
            logger.info(f"Checking: {key} Value: {value}")
            delete_y = await find_item(im_rgb, key, config)
            if delete_y>0:
                await delete_item(p, delete_y, value, im_rgb, auto_max, config)

        # Quit condition
        if last_item_quit == key.lower():
            delete_y = await find_item(im_rgb, last_item_quit, config)
            if delete_y>0:
                break
        
        # Quit when reach 20 pages
        if page_count >= 20:
            break
        
        if not last_image:
            last_image = im_rgb
        else:
            img_diff_value = compare_image(im_rgb,last_image)
            last_image = im_rgb
            if img_diff_value <= 500000:
                break
            #print(f'Differnce in value: {img_diff_value}')
        
        # Keep track of items, 4 per page
        item_tracker += 1
        if item_tracker >= 4:
            # let's shift the page
            if config.get('resize',False):
                x1 = int(989/1080*720)
                y1 = int(1500/1920*1280)
                x2 = int(989/1080*720)
                y2 = int(347/1920*1280)
            else:
                x1 = 989
                y1 = 1500
                x2 = 989
                y2 = 347
            d.drag(x1, y1, x2, y2, 4)
            await asyncio.sleep(5)
            item_tracker = 0
        
    await asyncio.sleep(1)
    await tap_screen(p, 540, 1780, 2)        

async def check_item(p, d, config):
    offset = config['client'].get('screen_offset', 0)
    #builder = MyBuilder()
    # lets cut up this image and get the text of each segment
    auto_max = config['item_management'].get('auto_max', False)
    last_item_quit = config['item_management'].get('last_item_quit','something that will not match').lower()

    i = 0
    continue_loop = True
    last_image = None

    # Assume we are at map
    await tap_screen(p, 540, 1780, 2)  # Pokeball/Menu
    await tap_screen(p, 840, 1600, 3)  # Items
    # throw text found into another function to match text
    track_item = []
    while continue_loop:
        while True:
            i += 1
            logger.info("ITEM PAGE: {}".format(i))
            im_rgb = await screen_cap(d)
            # Section 1
            text_ITEM1 = im_rgb.crop([340, 300 + offset, 925, 450 + offset])
            text_ITEM1 = tool.image_to_string(text_ITEM1)

            if text_ITEM1:
                text_ITEM1 = text_ITEM1.splitlines()[0].replace('|', '').replace('poke','poké').strip()
                logger.info("Text: {}".format(text_ITEM1))  
                if config['item_config'].get(text_ITEM1, 0) and text_ITEM1 not in track_item:
                    #await delete_item(p, 1, auto_max, offset, config)
                    if await delete_item(p, d, 1, config['item_config'].get(text_ITEM1, 0), auto_max, config):
                        track_item.append(text_ITEM1)
                        break
                if last_item_quit in text_ITEM1.lower() and last_item_quit != '':
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
                if len(text_ITEM1) >= 25 or text_ITEM1 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # Section 2
            text_ITEM2 = im_rgb.crop([340, 680 + offset, 925, 850 + offset])
            text_ITEM2 = tool.image_to_string(text_ITEM2)

            if text_ITEM2:
                text_ITEM2 = text_ITEM2.splitlines()[0].replace('|', '').strip().replace('poke','poké').strip()
                logger.info("Text: {}".format(text_ITEM2))
                if config['item_config'].get(text_ITEM2, 0) and text_ITEM2 not in track_item:
                    #await delete_item(p, 2, auto_max, offset, config)
                    if await delete_item(p, d, 2, config['item_config'].get(text_ITEM2, 0), auto_max, config):
                        track_item.append(text_ITEM2)
                        break
                if last_item_quit in text_ITEM2.lower() and last_item_quit != '':
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
                if len(text_ITEM2) >= 26 or text_ITEM2 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # Section 3
            text_ITEM3 = im_rgb.crop([340, 1070 + offset, 925, 1230 + offset])
            text_ITEM3 = tool.image_to_string(text_ITEM3)

            if text_ITEM3:
                text_ITEM3 = text_ITEM3.splitlines()[0].replace('|', '').strip().replace('poke','poké').strip()
                logger.info("Text: {}".format(text_ITEM3))
                if config['item_config'].get(text_ITEM3, 0) and text_ITEM3 not in track_item:
                    #await delete_item(p, 3, auto_max, offset, config)
                    if await delete_item(p, d, 3, config['item_config'].get(text_ITEM3, 0), auto_max, config):
                        track_item.append(text_ITEM3)
                        break
                if last_item_quit in text_ITEM3.lower() and last_item_quit != '':
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
                if len(text_ITEM3) >= 26 or text_ITEM3 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # Section 4
            text_ITEM4 = im_rgb.crop([340, 1445 + offset, 925, 1610 + offset])
            text_ITEM4 = tool.image_to_string(text_ITEM4)

            if text_ITEM4:
                text_ITEM4 = text_ITEM4.splitlines()[0].replace('|', '').strip().replace('poke','poké').strip()
                logger.info("Text: {}".format(text_ITEM4))
                if last_item_quit in text_ITEM4.lower() and last_item_quit != '':
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
                if len(text_ITEM4) >= 26 or text_ITEM4 == "":
                    await tap_screen(p, 540, 1780, 2)  # Close Item Page
                    continue_loop = False
                    break
            else:
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                continue_loop = False
                break

            # let's shift the page
            if config.get('resize',False):
                x1 = int(989/1080*720)
                y1 = int(1500/1920*1280)
                x2 = int(989/1080*720)
                y2 = int(347/1920*1280)
            else:
                x1 = 989
                y1 = 1500
                x2 = 989
                y2 = 347
            d.drag(x1, y1, x2, y2, 4)  # test y = 383 or y = 384
            await asyncio.sleep(5)
            
            if not last_image:
                last_image = im_rgb
            else:
                img_diff_value = compare_image(im_rgb,last_image)
                last_image = im_rgb
                if img_diff_value <= 500000:
                    break

            if i == 20:
                # too many pages, let's close and get out
                await tap_screen(p, 540, 1780, 2)  # Close Item Page
                break