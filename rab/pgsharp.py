import asyncio
import logging
import time
import datetime
import sys

from utils import get_id_from_names, Unknown

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)-7s | %(message)s', level='INFO', datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)
logger.setLevel('INFO')

class MapUIError(Exception):
    pass
    

class PGSharp:
    
    def __init__(self):
        self.nearby_count = 0
        self.current_index = 0
        self.feed_position = []
        self.joystick_position = []
        self.start_location = []
        self.icon_position = []
        self.menu_index = 0
        self.feed_index = None
        self.joystick_index = None
        self.icon_index = None
        self.menu_position = None

    async def get_nearby_count(self, p, d):
        if d(resourceId='me.underworld.helaplugin:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo').exists:
            return d(resourceId='me.underworld.helaplugin:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo').count
        else:
            return 0
    
    async def reposition(self, p, d):
        info0 = None
        info1 = None
        info2 = None
        info3 = None # this is for timer
        pokemon_info = d(resourceId='com.nianticlabs.pokemongo:id/unitySurfaceView', packageName='com.nianticlabs.pokemongo').info
        cd_timer = False
        
        height = 1920
        if pokemon_info['bounds'].get('bottom') > 1280:
            height = 1920
            width = 1080
        else:
            height = 1280
            width = 720
        
        # 0 = menu
        # 1 = joystick
        # 2 = feed 
        # total handle count
        floating_icon_count = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True).count
        if floating_icon_count == 2:
            # Assuming it's just feed and main
            if d(resourceId='me.underworld.helaplugin:id/hl_cd_text', packageName='com.nianticlabs.pokemongo').exists:
                cd_timer = True
            info0 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[0].info #menu
            info2 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[1].info #Feed
             
        elif floating_icon_count == 3:
            if d(resourceId='me.underworld.helaplugin:id/hl_cd_text', packageName='com.nianticlabs.pokemongo').exists:
                cd_timer = True
            
            if not cd_timer:
                info0 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[0].info #menu
                info1 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[1].info #joystick
                info2 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[2].info #Feed
            else:
                info0 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[0].info #menu
                info2 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[1].info #Feed
                info3 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[2].info #Timer
                
            
            
            
            #await asyncio.sleep(4.0)
            #x,y = await self.get_location(p, d)
            #if x>0:
            #    self.start_location = [x,y]
            #    logger.info('RAB is able to retrieve location from PGSharp...')
            #else:
            #    logger.info('RAB is unable to retrieve location from PGSharp...')
            
        else:
            return False
        
        #Move Feed First
        feed_sx, feed_sy = await self.get_item_position(info2)
        feed_ex, feed_ey = 0.94 * width, 0.90 * height
        d.drag(feed_sx, feed_sy, feed_ex, feed_ey, 1)
        await p.tap(feed_ex+25, feed_ey) # This will prevent icons from moving
        #await asyncio.sleep(4.0)

        #Move joystick
        if info1 and floating_icon_count == 3:
            info1 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[1].info #joystick
            feed_sx, feed_sy = await self.get_item_position(info1)
            feed_ex, feed_ey = 0, 0.98 * height
            d.drag(feed_sx, feed_sy, feed_ex, feed_ey, 1)
            await p.tap(feed_ex+25, feed_ey) # This will prevent icons from moving
        
        #Move timer
        if info1 and floating_icon_count == 3:
            info3 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[2].info #Timer
            feed_sx, feed_sy = await self.get_item_position(info3)
            feed_ex, feed_ey = 0.5 * width, 0
            d.drag(feed_sx, feed_sy, feed_ex, feed_ey, 1)
            #await p.tap(feed_ex+25, feed_ey) # This will prevent icons from moving
        
        #await asyncio.sleep(4.0)
        
        #Move menu icon
        info0 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[0].info #menu
        feed_sx, feed_sy = await self.get_item_position(info0)
        feed_ex, feed_ey = 0.92 * width, 0.36 * height
        d.drag(feed_sx, feed_sy, feed_ex, feed_ey,1)
        await p.tap(feed_ex, feed_ey) # This will prevent icons from moving
        if d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
            # tap one more time to close it
            await p.tap(feed_ex, feed_ey)
        #await asyncio.sleep(4.0)
        
        if floating_icon_count == 3 and cd_timer:
            info2 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[1].info #Feed
        elif floating_icon_count == 3 and not cd_timer:
            info2 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[2].info #Feed
        else:
            info2 = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[1].info #Feed
        feed_sx, feed_sy = await self.get_item_position(info2)
        feed_ex, feed_ey = 0, 0.15 * height
        d.drag(feed_sx, feed_sy, feed_ex, feed_ey, 1)
        await p.tap(feed_ex+25, feed_ey) # This will prevent icons from moving

    # old method
    async def reposition2(self, p, d):
        # 0 - icon
        # 1 - joystick
        # 2 - feed
        this_feed_index = None
        this_joystick_index = None
        this_icon_index = None
        
        floating_icon_count = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo').count
        pokemon_info = d(resourceId='com.nianticlabs.pokemongo:id/unitySurfaceView', packageName='com.nianticlabs.pokemongo').info
        
        height = 1920
        if pokemon_info['bounds'].get('bottom') > 1280:
            height = 1920
        else:
            height = 1280
        
        if floating_icon_count == 3:
            # verify who is feed
            for x in range(3):
                try:
                    info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[x].info
                    test1_top = info['bounds'].get('top')
                    test1_left = info['bounds'].get('left')
                    count = d(className='android.widget.LinearLayout', packageName='com.nianticlabs.pokemongo').count
                    for i in range(0, count):
                        info2 = d(className='android.widget.LinearLayout', packageName='com.nianticlabs.pokemongo')[i].info
                        test2_top = info2['bounds'].get('top')
                        test2_left = info2['bounds'].get('left')
                        if test1_top == test2_top and test1_left == test2_left:
                            this_feed_index = x
                            break
                    if this_feed_index:
                        break
                except:
                    pass
            
            # verify who is icon
            rem_diff = 0
            rem_this_icon_index = 0 
            for x in range(3):
                # skip the index that is confirm feed
                try:
                    if this_feed_index == x:
                        continue
                    info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[x].info
                    test_top = info['bounds'].get('top')
                    test_bottom = info['bounds'].get('bottom')
                    test_diff = test_bottom - test_top
                    if test_diff > rem_diff:
                        rem_diff = test_diff
                        rem_this_icon_index = x
                except:
                    pass
            
            this_icon_index = rem_this_icon_index
            
            # verify who is joystick
            for x in range(3):
                if this_feed_index == x:
                    continue
                if this_icon_index == x:
                    continue
                this_joystick_index = x
            
            logger.info(f'Feed Index: {this_feed_index} | Icon Index: {this_icon_index} | Joystick Index: {this_joystick_index}')    
            
            feed_info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[this_feed_index].info
            joystick_info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[this_joystick_index].info
            icon_info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[this_icon_index].info
            
            feed_shifted = False
            
            feed_sx, feed_sy = await self.get_item_position(feed_info)
            if (feed_info['bounds'].get('top') == joystick_info['bounds'].get('top') and feed_info['bounds'].get('left') == joystick_info['bounds'].get('left')) or (feed_info['bounds'].get('top') == icon_info['bounds'].get('top') and feed_info['bounds'].get('left') == icon_info['bounds'].get('left')):
                feed_ex, feed_ey = 0, 0.5 * height
                feed_shifted = True
            else:
                feed_ex, feed_ey = 0, 0.2 * height
            d.drag(feed_sx, feed_sy, feed_ex, feed_ey, 0.5)
        
            # Move joystick
            joystick_sx, joystick_sy = await self.get_item_position(joystick_info)
            joystick_ex, joystick_ey = 0, 0.99 * height
            d.drag(joystick_sx, joystick_sy, joystick_ex, joystick_ey, 0.5)
        
            # Move icon
            icon_sx, icon_sy = await self.get_item_position(icon_info)
            icon_ex, icon_ey = 0.92 * pokemon_info['bounds'].get('right'), 0.35 * height
            d.drag(icon_sx, icon_sy, icon_ex, icon_ey)
            
            this_feed_index = None
            this_joystick_index = None
            this_icon_index = None
            # verify who is feed
            for x in range(3):
                try:
                    info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[x].info
                    test1_top = info['bounds'].get('top')
                    test1_left = info['bounds'].get('left')
                    count = d(className='android.widget.LinearLayout', packageName='com.nianticlabs.pokemongo').count
                    for i in range(0, count):
                        info2 = d(className='android.widget.LinearLayout', packageName='com.nianticlabs.pokemongo')[i].info
                        test2_top = info2['bounds'].get('top')
                        test2_left = info2['bounds'].get('left')
                        if test1_top == test2_top and test1_left == test2_left:
                            this_feed_index = x
                            break
                    if this_feed_index:
                        break
                except:
                    pass
        
            # verify who is icon
            rem_diff = 0
            rem_this_icon_index = 0 
            for x in range(3):
                try:
                    # skip the index that is confirm feed
                    if this_feed_index == x:
                        continue
                    info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[x].info
                    test_top = info['bounds'].get('top')
                    test_bottom = info['bounds'].get('bottom')
                    test_diff = test_bottom - test_top
                    if test_diff > rem_diff:
                        rem_diff = test_diff
                        rem_this_icon_index = x
                except:
                    pass
            
            this_icon_index = rem_this_icon_index
            
            # verify who is joystick
            for x in range(3):
                if this_feed_index == x:
                    continue
                if this_icon_index == x:
                    continue
                this_joystick_index = x
            
            logger.info(f'Feed Index: {this_feed_index} | Icon Index: {this_icon_index} | Joystick Index: {this_joystick_index}')
            
            # Move feed
            if feed_shifted:
                feed_info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[this_feed_index].info
                feed_sx, feed_sy = await self.get_item_position(feed_info)
                feed_ex, feed_ey = 0, 0.2 * height
                d.drag(feed_sx, feed_sy, feed_ex, feed_ey, 0.5)
            
            self.feed_index = this_feed_index
            self.joystick_index = this_joystick_index
            self.icon_index = this_icon_index
            
            await asyncio.sleep(6.0)
            x,y = await self.get_location(p, d)
            if x>0:
                self.start_location = [x,y]
                logger.info('RAB is able to retrieve location from PGSharp...')
            else:
                logger.info('RAB is unable to retrieve location from PGSharp...')
        else:
            return False
        
            
    #async def check_if_joystick(self, info):
    #    ya = info['bounds'].get('top')
    #    xs = info['bounds'].get('left')
    #    ya1 = info['bounds'].get('bottom')
    #    xs1 = info['bounds'].get('right')
        
    #    y_diff = ya1 - ya
    #    x_diff = xs1 - xs
        
    #    logger.info(f'x diff: {x_diff}, y diff: {y_diff}')
    
    async def get_item_position(self, info, resized=False):
        ya = info['bounds'].get('top')
        xs = info['bounds'].get('left')
        ya1 = info['bounds'].get('bottom')
        xs1 = info['bounds'].get('right')
        
        x = xs + int(((xs1 - xs)/2))
        y = ya + int(((ya1 - ya)/2))
        
        if resized:
            x = x * 2
            y = y * 2
        
        return (x, y)
        
    async def wait_for_spawn(self, p, d):
        counter = 0
        while True:
            await asyncio.sleep(1.0)
            if counter >= 60:
                return False
            if d(resourceId='me.underworld.helaplugin:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo').exists:
                return True
            counter += 1
    
    async def teleport(self, p, d, x, y, resized=False):
        iconx = 0
        icony = 0
        
        # class="android.widget.EditText" package="com.nianticlabs.pokemongo"
        # resource-id="me.underworld.helaplugin:id/hl_floatmenu_tp"
        #if d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True).exists:
            #info = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].info
            #iconx, icony = await self.get_item_position(info)
        #    if not d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
        #        d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
                #await p.tap(iconx,icony)
        
        # Open map icon
        #if d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo').exists:
        #    info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[self.icon_index].info
        #    iconx, icony = await self.get_item_position(info)
        #    if not d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
                #d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
        #        await p.tap(iconx,icony)
        
        if not d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
            d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
        
        # Open Teleport
        if d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_tp', packageName='com.nianticlabs.pokemongo').exists:
            d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_tp', packageName='com.nianticlabs.pokemongo').click()
            await asyncio.sleep(0.5)
        
        text = str(x) + ', ' + str(y)
        try:
            d.set_fastinput_ime(True) 
            d.send_keys(text)
            #d.clear_text() 
            d.set_fastinput_ime(False)
        except:
            d(focused=True).set_text(text)
            
        await asyncio.sleep(1)
        d(text='OK', resourceId='android:id/button1', packageName='com.nianticlabs.pokemongo').click()
        
        await asyncio.sleep(0.5)
        
        if iconx > 0 and d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
            d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
            #await p.tap(iconx,icony)
    
    async def get_location(self, p, d, method2=False):
        iconx = 0
        icony = 0
        x_location, y_location = 0.0, 0.0
        
        #if not method2:
        #    feed_info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[self.feed_index].info
        #    joystick_info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[self.joystick_index].info
        #    icon_info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[self.icon_index].info
        
            # Open map icon
        #    if d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo').exists:
                #info = d(resourceId='me.underworld.helaplugin:id/hl_floating_icon', packageName='com.nianticlabs.pokemongo')[self.icon_index].info
                #iconx, icony = await self.get_item_position(info)
        #        if not d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
        #            d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
                    #await p.tap(iconx,icony)
        #else:
            # Open map icon
        #    if d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True).exists:
        #        info = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].info
        #        iconx, icony = await self.get_item_position(info)
        #        if not d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
                    #d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
        #            await p.tap(iconx,icony)
        
        if not d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
            d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
        
        # Open map
        if d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
            d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').click()
            await asyncio.sleep(0.5)
        
        # Click Home 1x
        if d(resourceId='me.underworld.helaplugin:id/hl_mbmap_home', packageName='com.nianticlabs.pokemongo').exists:
            d(resourceId='me.underworld.helaplugin:id/hl_mbmap_home', packageName='com.nianticlabs.pokemongo').click()
            await asyncio.sleep(0.5)
        
        # Get map view
        if d(resourceId='me.underworld.helaplugin:id/hl_mbmap_mapview', packageName='com.nianticlabs.pokemongo',clickable=True).exists:
            info = d(resourceId='me.underworld.helaplugin:id/hl_mbmap_mapview', packageName='com.nianticlabs.pokemongo',clickable=True).info
            #d(resourceId='me.underworld.helaplugin:id/hl_mbmap_mapview', packageName='com.nianticlabs.pokemongo',clickable=True).click()
            #x, y = await self.get_item_position(info)
            await p.tap(540,920)
            await asyncio.sleep(0.5)
        
        if d(resourceId='me.underworld.helaplugin:id/hl_mapbox_popup_latlng', packageName='com.nianticlabs.pokemongo').exists:
            info = d(resourceId='me.underworld.helaplugin:id/hl_mapbox_popup_latlng', packageName='com.nianticlabs.pokemongo').info
            coords = info.get('text').split(',')
            x_location = float(coords[0])
            y_location = float(coords[1])
            
            #print('{},{}'.format(x_location, y_location))
        
        if d(resourceId='me.underworld.helaplugin:id/hl_mbmap_close', packageName='com.nianticlabs.pokemongo').exists:
            d(resourceId='me.underworld.helaplugin:id/hl_mbmap_close', packageName='com.nianticlabs.pokemongo').click()
            await asyncio.sleep(0.5)
        
        if d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
            d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
        
        return x_location, y_location

    async def find_menu(self, p, d):
        x, y = 0, 0
        count = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True).count
        for i in range(0, count):
            self.menu_index = i
            x, y = await self.get_location(p,d)
            if x != 0:
                return True
        
        return False
    
    async def close_pgsharp_menu(self, p, d):
        try:
            if d(resourceId='me.underworld.helaplugin:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
                d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',clickable=True)[self.menu_index].click()
        except:
            pass
    
    async def pokemon_encountered(self, p, d, pokemon):
        if d(resourceId='me.underworld.helaplugin:id/hl_ec_sum_lvv', packageName='com.nianticlabs.pokemongo').exists:
            pokemon.get_stats_from_pgsharp(p,d,detail=True) 
            return True
        else:
            return False
    
    async def get_overlay_frame_count(self, p, d):
        return d(className='android.widget.ImageView', packageName='com.nianticlabs.pokemongo',clickable=True).count