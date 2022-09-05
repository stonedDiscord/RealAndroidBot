import asyncio
import logging
import os
import re
import subprocess
from csv import reader
from io import BytesIO

from PIL import Image
from colorlog import ColoredFormatter

logger = logging.getLogger('PokemonGo')
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)
formatter = ColoredFormatter('%(log_color)s[%(asctime)s] %(log_color)s%(levelname)-7s%(reset)s '
                             '| %(log_color)s%(message)s%(reset)s', datefmt='%I:%M:%S %p')
ch.setFormatter(formatter)
logger.addHandler(ch)

RE_CLIPBOARD_TEXT = re.compile(r"^./ClipboardReceiver\(\s*\d+\): Clipboard text: (.+)$")

trackCB_Changes = ''


class CalcyIVError(Exception):
    # logger.error('CalcyIV did not find any combinations.')
    pass


class RedBarError(Exception):
    # logger.error('The red bar is covering the pokémon CP.')
    pass


class PhoneNotConnectedError(Exception):
    # logger.error('Your phone does not appear to be connected. Try \'adb devices\' and see if it is listed there :)')
    pass

class LogcatNotRunningError(Exception):
    # logger.error('For some reason, I can\'t run the logcat on your phone! :(
    # Try to run \'adb logcat\' and see if something happens. Message the developers as well!')
    pass


class PokemonGo(object):
    def __init__(self, wifi_ip = None):
        self.device_id = None
        self.wifi_ip = wifi_ip
        self.calcy_pid = None
        self.use_fallback_screenshots = False
        self.android_version = None


    async def connect_wifi(self, wifi_ip = None, port = '5555'):
        self.wifi_ip = wifi_ip
        args = [
            "adb",
            "-d",
            "tcpip",
            port
        ]
        await self.run(args)
        
        args = [
            "adb",
            "connect",
            self.wifi_ip + ':' + port
        ]
        await self.run(args)
    
    async def disconnect_wifi(self):    
        args = [
            "adb",
            "disconnect",
            self.wifi_ip + ':' + str(port)
        ]
        await self.run(args)
    
    async def get_location(self, save_file=False):
        lat = 0
        lng = 0
        sys_lists = None
        deviceid = await self.get_device()
        logger.info("Getting last known location from {}".format(deviceid))

        args = [
            "adb",
            "-s",
            deviceid,
            "shell",
            "dumpsys",
            "location"
        ]
        returncode, stdout, stderr = await self.run(args)
        
        if stdout:
            str_stdout = str(stdout, encoding='utf-8').strip()
            sys_lists = str_stdout.splitlines()

        if sys_lists:
            #with open("Output.txt", "w") as text_file:
            #    print(f"{sys_lists}", file=text_file)
            if save_file:
                f= open(deviceid + "_debug.txt","w+")
                for line in sys_lists:
                    if 'location' in line.lower():
                        f.write(line+'\r\n')
                f.close
            
            for line in sys_lists:
                if 'fused: location' in line.lower() or 'passive: location' in line.lower() or 'last location=location[fused' in line.lower() or 'last mock location=location[gps' in line.lower():
                    m = re.search(r'[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?),\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)', line)
                    if m and '.' not in m.group():
                        m = re.search(r'[-+]?(\d+),(\d+),\s*[-+]?(\d+),(\d+)', line)
                        temp = m.group().strip()
                        temp_list = temp.split(',')
                        if len(temp_list) == 4:
                            lat = float(temp_list[0] + '.' + temp_list[1])
                            lng = float(temp_list[2] + '.' + temp_list[3])
                        break
                    elif m:
                        coord = m.group().strip()
                        coord_list = coord.split(',')
                        lat = float(coord_list[0])
                        lng = float(coord_list[1])
                        break

        return (lat,lng)

    async def screencap(self):
        if not self.use_fallback_screenshots:
            return_code, stdout, stderr = await self.run(
                ["adb", "-s", await self.get_device(), "exec-out", "screencap", "-p"])
            try:
                return Image.open(BytesIO(stdout))
            except (OSError, IOError):
                logger.debug("Screenshot failed, using fallback method")
                self.use_fallback_screenshots = True
        return_code, stdout, stderr = await self.run(
            ["adb", "-s", await self.get_device(), "shell", "screencap", "-p", "/sdcard/screen.png"])
        return_code, stdout, stderr = await self.run(
            ["adb", "-s", await self.get_device(), "pull", "/sdcard/screen.png", "."])
        image = Image.open("screen.png")
        return image

    async def set_device(self, device_id=None):
        self.device_id = device_id

    async def get_device(self):
        if self.device_id:
            return self.device_id
        devices = await self.get_devices()
        if devices == []:
            raise PhoneNotConnectedError
        if len(devices) > 1:
            logger.info("Multiple devices detected, select your choice:")
            i = 0
            for each_device in devices:
                logger.info("{}.\t{}".format(i, each_device))
                i += 1
            choice = input('Enter Your Choice: ')
            try:
                self.device_id = devices[int(choice)]
            except:
                raise PhoneNotConnectedError
        else:
            self.device_id = devices[0]
        return self.device_id

    async def run(self, args):
        logger.debug("Running %s", args)
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        logger.debug("Return code %d", p.returncode)
        return (p.returncode, stdout, stderr)

    async def get_devices(self):
        code, stdout, stderr = await self.run(["adb", "devices"])
        devices = []

        for line in stdout.decode('utf-8').splitlines()[1:-1]:
            device_id, name = line.split('\t')
            devices.append(device_id)
        return devices

    async def start_logcat(self):
        cmd = ["adb", "-s", await self.get_device(), "logcat", "-T", "1", "-v", "brief",
               "MainService:D j:D ClipboardReceiver:D *:S"]
        logger.info("Starting logcat %s", cmd)
        self.logcat_task = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await self.logcat_task.stdout.readline()  # Read and discard the one line as -T 0 doesn't work

    async def seek_to_end(self):
        # Seek to the end of the file
        while True:
            try:
                task = await asyncio.wait_for(self.logcat_task.stdout.readline(), 0.2)
            except asyncio.TimeoutError:
                break

    async def read_logcat(self):
        if self.logcat_task.returncode != None:
            logger.error("Logcat process is not running")
            logger.error("stdout %s", await self.logcat_task.stdout.read())
            logger.error("stderr %s", await self.logcat_task.stderr.read())
            raise LogcatNotRunningError()

        line = await self.logcat_task.stdout.readline()
        line = line.decode('utf-8', errors='ignore').rstrip()

        return line

    async def get_clipboard(self):
        global trackCB_Changes
        i = 0
        # await self.start_logcat()
        await self.send_intent("clipper.get")
        while i <= 100:
            i += 1
            line = await self.read_logcat()
            match = RE_CLIPBOARD_TEXT.match(line)
            if match:
                if trackCB_Changes != match.group(1):
                    logger.info("RE_CLIPBOARD_TEXT matched.")
                    trackCB_Changes = match.group(1)
                    return match.group(1)
                else:
                    return False
        logger.info("RE_CLIPBOARD_TEXT not found.")
        return False

    async def send_intent(self, intent, package=None, extra_values=[]):
        cmd = "am broadcast -a {}".format(intent)
        if package:
            cmd = cmd + " -n {}".format(package)
        for key, value in extra_values:
            if isinstance(value, bool):
                cmd = cmd + " --ez {} {}".format(key, "true" if value else "false")
            elif '--user' in key:
                cmd = cmd + " --user {}".format(value)
            else:
                cmd = cmd + " -e {} '{}'".format(key, value)
        logger.info("Sending intent: " + cmd)
        await self.run(["adb", "-s", await self.get_device(), "shell", cmd])

    async def tap(self, x, y):
        logger.debug("Tapping at [{}, {}]".format(x, y))
        await self.run(["adb", "-s", await self.get_device(), "shell", "input", "tap", x, y])

    async def key(self, key):
        logger.info("Pressing key {}".format(key))
        await self.run(["adb", "-s", await self.get_device(), "shell", "input", "keyevent", key])

    async def text(self, text):
        logger.info("Typing {}".format(text))
        await self.run(["adb", "-s", await self.get_device(), "shell", "input", "text", text])

    async def swipe(self, x1, y1, x2, y2, duration=None):
        logger.debug("Swiping from [{}, {}] to [{}, {}] in {} milliseconds.".format(x1, y1, x2, y2, duration))
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "input",
            "swipe",
            x1,
            y1,
            x2,
            y2
        ]
        if duration:
            args.append(duration)
        await self.run(args)

    async def check_if_app_running(self, app_process):
        logger.info("Checking if '{}' is running".format(app_process))
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "pidof",
            app_process
        ]
        returncode, stdout, stderr = await self.run(args)

        logger.debug('Check App Return Code: {} | stdout: {} | stderr: {}'.format(returncode,
                                                                                  str(stdout, encoding='utf-8').strip(),
                                                                                  stderr))
        if str(stdout, encoding='utf-8').strip():
            return True
        else:
            return False
    
    async def goto_location(self, x, y, delay=0):
        # logger.info("Going to {}, {} in {} secs".format(x, y, delay))
        await asyncio.sleep(delay)
        if self.android_version >= 8:
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "am",
                "start-foreground-service",
                "-a",
                "theappninjas.gpsjoystick.TELEPORT",
                "--ef",
                "lat",
                x,
                "--ef",
                "lng",
                y
            ]
        else:
            # adb shell am startservice -a theappninjas.gpsjoystick.TELEPORT --ef lat {your-latitude-value} --ef lng {your-longitude-value} --ef alt {your-altitude-value}
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "am",
                "startservice",
                "-a",
                "theappninjas.gpsjoystick.TELEPORT",
                "--ef",
                "lat",
                x,
                "--ef",
                "lng",
                y
            ]
            
        returncode, stdout, stderr = await self.run(args)
        cmdstr = str(stdout, encoding='utf-8').strip().lower()
        if 'no service started' in cmdstr:
            logger.info('Your GPS Joystick is not supported. Please download and use the version from http://gpsjoystick.theappninjas.com/faq/ instead of the playstore version.')
            return False
        return True
            

    async def start_route(self, route_name, delay=0):
        logger.info("Starting {} Route in {} secs".format(route_name, delay))
        await asyncio.sleep(delay)
        if self.android_version >= 8:
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "am",
                "start-foreground-service",
                "-a",
                "theappninjas.gpsjoystick.ROUTE",
                "--es",
                "name",
                '\"' + route_name + '\"'
            ]
        else:
            # adb shell am startservice -a theappninjas.gpsjoystick.ROUTE --es name \"{your-route-name}\"
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "am",
                "startservice",
                "-a",
                "theappninjas.gpsjoystick.ROUTE",
                "--es",
                "name",
                '\"' + route_name + '\"'
            ]
        returncode, stdout, stderr = await self.run(args)
        cmdstr = str(stdout, encoding='utf-8').strip().lower()
        if 'no service started' in cmdstr:
            logger.info('Your GPS Joystick is not supported. Please download and use the version from http://gpsjoystick.theappninjas.com/faq/ instead of the playstore version.')
            return False
        return True

    async def navigation_offset(self, y=0, top=0):
        if y > 0 and top <= 0:
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "wm",
                "overscan",
                "0,"+str(top)+",0,-"+str(y)
            ]
        elif y > 0 and top > 0:
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "wm",
                "overscan",
                "0,-"+str(top)+",0,-"+str(y)
            ]
        elif y <= 0 and top > 0:
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "wm",
                "overscan",
                "0,-"+str(top)+",0,"+str(y)
            ]
        else:
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "wm",
                "overscan",
                "0,"+str(top)+",0,"+str(y)
            ]
        
        
        await self.run(args)
    
    async def set_android_version(self):
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "getprop",
            "ro.build.version.release"
        ]
        returncode, stdout, stderr = await self.run(args)
        output = str(stdout, encoding='utf-8')
        if '.' in output:
            spilt_out = output.split('.')
            output = spilt_out[0]
        self.android_version = int(output)
        return self.android_version
        
    
    async def get_screen_resolution(self):
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "wm",
            "size"
        ]
        returncode, stdout, stderr = await self.run(args)
        output = str(stdout, encoding='utf-8')
        if '\n' in output:
            spilt_out = output.split('\n')
            output = spilt_out[0]
        num_list = [int(s) for s in re.findall(r"[-+]?[.]?[\d]+(?:,\d\d\d)*[\.]?\d*(?:[eE][-+]?\d+)?", output)]
        if len(num_list) == 2:
            return num_list
        return [0,0]
    
    async def get_screen_dpi(self):
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "wm",
            "density"
        ]
        returncode, stdout, stderr = await self.run(args)
        output = str(stdout, encoding='utf-8')
        if '\n' in output:
            spilt_out = output.split('\n')
            output = spilt_out[0]
        num_list = [int(s) for s in re.findall(r"(\d+)", output)]
        if len(num_list) == 1:
            return num_list[0]
        return False
    
    async def change_screen_resolution(self, x=1080,y=1920, dpi=None):
        if dpi:
            args = [
                "adb",
                "-s",
                await self.get_device(),
                "shell",
                "wm",
                "density",
                str(dpi)
            ]
            await self.run(args)
        await asyncio.sleep(1)
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "wm",
            "size",
            str(x)+"x"+str(y)
        ]
        await self.run(args)

    async def reset_screen_resolution(self):
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "wm",
            "overscan",
            "0,0,0,0"
        ]
        await self.run(args)
        await asyncio.sleep(1)
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "wm",
            "size",
            "reset"
        ]
        await self.run(args)
        await asyncio.sleep(1)
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "wm",
            "density",
            "reset"
        ]
        await self.run(args)

    async def set_screen_brightness(self, brightness):
        args = [
            "adb",
            "-s",
            await self.get_device(),
            "shell",
            "settings",
            "put",
            "system screen_brightness",
            brightness
        ]
        await self.run(args)