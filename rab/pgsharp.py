import asyncio
import logging
from action import tap_screen

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d %(levelname)-7s | %(message)s',
    level='INFO', datefmt='%H:%M:%S')
logger = logging.getLogger('rab')

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
        if d(resourceId='me.underw.hp:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo').exists:
            return d(resourceId='me.underw.hp:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo').count
        else:
            return 0

    async def reposition(self, p, d):
        # 0 = menu
        # 1 = joystick
        # 2 = feed
        # 3 = timer
        info0 = None
        info1 = None
        info2 = None
        info3 = None

        pokemon_info = d(resourceId='com.nianticlabs.pokemongo:id/unitySurfaceView',
                         packageName='com.nianticlabs.pokemongo').info
        cd_timer = False

        height = 1920
        if pokemon_info['bounds'].get('bottom') > 1280:
            height = 1920
            width = 1080
        else:
            height = 1280
            width = 720

        # total handle count
        floating_icon_count = d(className='android.widget.FrameLayout',
                                packageName='com.nianticlabs.pokemongo', clickable=True).count
        if floating_icon_count == 2:
            # Assuming it's just feed and main
            if d(resourceId='me.underw.hp:id/hl_cd_text', packageName='com.nianticlabs.pokemongo').exists:
                cd_timer = True
            info0 = d(className='android.widget.FrameLayout',
                      packageName='com.nianticlabs.pokemongo', clickable=True)[1].info  # menu
            info2 = d(className='android.widget.FrameLayout',
                      packageName='com.nianticlabs.pokemongo', clickable=True)[0].info  # feed

        elif floating_icon_count == 3:
            if d(resourceId='me.underw.hp:id/hl_cd_text', packageName='com.nianticlabs.pokemongo').exists:
                cd_timer = True

            if not cd_timer:
                info0 = d(className='android.widget.FrameLayout',
                          packageName='com.nianticlabs.pokemongo', clickable=True)[0].info  # menu
                info1 = d(className='android.widget.FrameLayout',
                          packageName='com.nianticlabs.pokemongo', clickable=True)[1].info  # joystick
                info2 = d(className='android.widget.FrameLayout',
                          packageName='com.nianticlabs.pokemongo', clickable=True)[2].info  # Feed
            else:
                info0 = d(className='android.widget.FrameLayout',
                          packageName='com.nianticlabs.pokemongo', clickable=True)[0].info  # menu
                info2 = d(className='android.widget.FrameLayout',
                          packageName='com.nianticlabs.pokemongo', clickable=True)[1].info  # Feed
                info3 = d(className='android.widget.FrameLayout',
                          packageName='com.nianticlabs.pokemongo', clickable=True)[2].info  # Timer
        else:
            return False

        # Move menu
        menu_sx, menu_sy = await self.get_item_position(info0)
        menu_ex, menu_ey = 0.05, 0.1 * height
        d.drag(menu_sx, menu_sy, menu_ex, menu_ey, 1)

        # Move joystick
        if info1 and floating_icon_count == 3:
            info1 = d(className='android.widget.FrameLayout',
                      packageName='com.nianticlabs.pokemongo', clickable=True)[1].info  # joystick
            joy_sx, joy_sy = await self.get_item_position(info1)
            joy_ex, joy_ey = 0, 0.98 * height
            d.drag(joy_sx, joy_sy, joy_ex, joy_ey, 1)
            await tap_screen(p, joy_ex+25, joy_ey)  # This will prevent icons from moving

        # Move timer
        if info1 and floating_icon_count == 3:
            info3 = d(className='android.widget.FrameLayout',
                      packageName='com.nianticlabs.pokemongo', clickable=True)[2].info  # Timer
            time_sx, time_sy = await self.get_item_position(info3)
            time_ex, time_ey = 0.5 * width, 0
            d.drag(time_sx, time_sy, time_ex, time_ey, 1)

        # Move feed
        feed_sx, feed_sy = await self.get_item_position(info2)
        feed_ex, feed_ey = 0.98 * width, 0.45 * height
        d.drag(feed_sx, feed_sy, feed_ex, feed_ey, 1)


    async def get_item_position(self, info, resized=False):
        ya = info['bounds'].get('top')
        xs = info['bounds'].get('left')
        ya1 = info['bounds'].get('bottom')
        xs1 = info['bounds'].get('right')

        x = xs + int(((xs1 - xs)/2))
        y = ya + int(((ya1 - ya)/2))

        # uiautomator2 gives real screen positions
        # so we have to calculate against tap_screen
        if resized:
            x = x * 1080 / 720
            y = y * 1920 / 1280

        return (x, y)

    async def wait_for_spawn(self, p, d):
        counter = 0
        while True:
            await asyncio.sleep(1.0)
            if counter >= 60:
                return False
            if d(resourceId='me.underw.hp:id/hl_sri_icon', packageName='com.nianticlabs.pokemongo').exists:
                return True
            counter += 1

    async def teleport(self, p, d, x, y, resized=False):

        if not d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Teleport").exists:
            d.xpath('//*[@resource-id="android:id/content"]/android.widget.FrameLayout[3]').click()

        # Open Teleport
        if d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Teleport").exists:
            d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Teleport").click()
            await asyncio.sleep(0.5)

        text = str(x) + ', ' + str(y)
        try:
            d.set_fastinput_ime(True)
            d.clear_text()
            d.send_keys(text)            
            d.set_fastinput_ime(False)
        except:
            d(focused=True).set_text(text)

        await asyncio.sleep(1)
        if d(text='OK', resourceId='android:id/button1', packageName='com.nianticlabs.pokemongo').exists:
            d(text='OK', resourceId='android:id/button1', packageName='com.nianticlabs.pokemongo').click()

        await asyncio.sleep(0.5)

        if d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Teleport").exists:
            d.xpath('//*[@resource-id="android:id/content"]/android.widget.FrameLayout[3]').click()

    async def get_location(self, p, d, method2=False):
        x_location, y_location = 0.0, 0.0

        if not d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Map").exists:
            d.xpath('//*[@resource-id="android:id/content"]/android.widget.FrameLayout[3]').click()

        # Open map
        if d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Map").exists:
            d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Map").click()
            await asyncio.sleep(0.5)

        # Click Home 1x
        if d(resourceId="me.underw.hp:id/hl_mbmap_home").exists:
            d(resourceId="me.underw.hp:id/hl_mbmap_home").click()
            await asyncio.sleep(0.5)

        # Get map view
        if d(resourceId='me.underw.hp:id/hl_mbmap_mapview', packageName='com.nianticlabs.pokemongo', clickable=True).exists:
            await tap_screen(p, 540, 920)
            await asyncio.sleep(0.5)

        if d(resourceId='me.underw.hp:id/hl_mapbox_popup_latlng', packageName='com.nianticlabs.pokemongo').exists:
            info = d(resourceId='me.underw.hp:id/hl_mapbox_popup_latlng',
                     packageName='com.nianticlabs.pokemongo').info
            coords = info.get('text').split(',')
            x_location = float(coords[0])
            y_location = float(coords[1])

        if d(resourceId='me.underw.hp:id/hl_mbmap_close', packageName='com.nianticlabs.pokemongo').exists:
            d(resourceId='me.underw.hp:id/hl_mbmap_close', packageName='com.nianticlabs.pokemongo').click()
            await asyncio.sleep(0.5)

        if d(resourceId="me.underw.hp:id/hl_shortcut_menu_item_txt", text="Map").exists:
            d.xpath('//*[@resource-id="android:id/content"]/android.widget.FrameLayout[3]').click()

        return x_location, y_location

    async def find_menu(self, p, d):
        x, y = 0, 0
        count = d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo', clickable=True).count
        for i in range(0, count):
            self.menu_index = i
            x, y = await self.get_location(p, d)
            if x != 0:
                return True

        return False

    async def close_pgsharp_menu(self, p, d):
        try:
            if d(resourceId='me.underw.hp:id/hl_floatmenu_map', packageName='com.nianticlabs.pokemongo').exists:
                d(className='android.widget.FrameLayout', packageName='com.nianticlabs.pokemongo',
                  clickable=True)[self.menu_index].click()
        except:
            pass

    async def pokemon_encountered(self, p, d, pokemon):
        if d(resourceId='me.underw.hp:id/hl_ec_sum_lvv', packageName='com.nianticlabs.pokemongo').exists:
            pokemon.get_stats_from_pgsharp(p, d, detail=True)
            return True
        else:
            return False

    async def get_overlay_frame_count(self, p, d):
        return d(className='android.widget.ImageView', packageName='com.nianticlabs.pokemongo', clickable=True).count
