import tkinter as tk
import argparse
import os
import sys
import time
import webbrowser
import yaml
import rab
import logging
import json
#from tkinter.filedialog import askopenfilename
from utils import Loader
from tkinter import ttk, PhotoImage, StringVar, IntVar, DoubleVar, messagebox
from PIL import Image, ImageTk
from telethon import TelegramClient, events, errors
from db import session_scope, vaild_subscription

import subprocess
from functools import partial

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)-7s | %(message)s', level='INFO', datefmt='%H:%M:%S')
logger = logging.getLogger('rab')


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(
                scrollregion=canvas.bbox("all")
            )
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")

        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")


class StdoutRedirector(object):
    def __init__(self, text_widget):
        self.text_space = text_widget

    def write(self, string):
        self.text_space.insert('end', string)
        self.text_space.see('end')


class RABGui(object):
    def __init__(self, config, lang, config_path, device_id=None, gui_lang=None):
        self.version = '1.12.0'
        self.win_main = None
        self.config = config
        self.lang = lang
        self.gui_lang = config['client'].get('gui_language', 'english')
        if config_path == 'config.example.yaml':
            config_path = 'config.yaml'
        self.config_path = config_path
        self.device_id = device_id
        self.tabControl = None
        self.ContainerThree = None
        self.client = None
        self.telegram_id = None
        self.donor_until = None
        self.console_box = None
        self.photo = None

        # build config if not availible
        if not config.get('client'):
            config['client'] = {}
        if not config.get('discord'):
            config['discord'] = {}
        if not config.get('network'):
            config['network'] = {}
        if not config.get('telegram'):
            config['telegram'] = {}
        if not config.get('shiny_check'):
            config['shiny_check'] = {}
        if not config.get('snipe'):
            config['snipe'] = {}
        if not config.get('quest'):
            config['quest'] = {}
        if not config.get('screenshot'):
            config['screenshot'] = {}
        if not config.get('catch'):
            config['catch'] = {}
        if not config.get('berry_selection'):
            config['berry_selection'] = {}
        if not config.get('ball_selection'):
            config['ball_selection'] = {}
        if not config.get('pvp'):
            config['pvp'] = {}
        if not config.get('poke_management'):
            config['poke_management'] = {}
        if not config.get('item_management'):
            config['item_management'] = {}
        if not config.get('item_config'):
            config['item_config'] = {}

        if config['telegram'].get('enabled'):
            self.start_telegram()

        # tabs
        self.tab1 = None
        self.tab2 = None
        self.tab3 = None
        self.tab4 = None
        self.tab5 = None
        self.tab6 = None

        # tab 1
        self.imgInstructions = None

        # Widgets that need to change values
        self.results = None
        self.tab2Frame2Host = None
        self.tab2Frame2Port = None
        self.tab2Frame2PokestopPriority = None
        self.tab3Frame1StopAtBall = None
        self.tab3Frame1ResumeAtBall = None
        self.tab3Frame1CatchEveryXSpin = None
        self.tab3Frame1GoAfterShiny = None
        self.tab3Frame1GoAfterMaxIV = None
        self.tab3Frame1ShinyMode = None
        self.tab4Frame1InventoryIV = None
        self.tab4Frame2AutoMax = None

        # Config var binding
        # Tab 2 Frame 1
        self.clientVar = None  # Type of client
        self.typeVar = None  # Type of device
        self.boolTeamRocket = None  # Team Rocket
        self.boolInstantSpin = None  # Instant Spin
        self.boolSkipIntro = None  # Skip Encounter Intro
        self.boolEncounterIV = None  # Encounter IV
        self.boolQuickCatch = None  # Quick Catch
        self.boolAutoRoute = None  # Auto Route
        self.boolPokestopPriority = None  # Pokestop Priority
        self.boolAutoGoplus = None  # Auto Go Plus
        self.boolAutoSlotGym = None  # Auto Slot Gym
        self.boolAdvanceBerryCheck = None  # Advance Berry Check
        self.tab2Frame1TeamRocket = None
        self.tab2Frame1InstantSpin = None
        self.tab2Frame1SkipIntro = None
        self.tab2Frame1EncounterIV = None
        self.tab2Frame1QuickCatch = None
        self.tab2Frame2AutoRoute = None

        # Tab 2 Frame 2
        self.strHost = None
        self.strPort = None
        self.boolManualResolution = None
        self.boolAutoOffset = None
        self.intScreenOffset = None
        self.intNavigationOffset = None
        self.intScreenshotOffset = None
        self.boolLowerResolution = None
        self.strDelayTime = None
        self.strDensity = None

        self.ZoomOutVar = None
        self.boolPGSharpShuno = None
        self.tab2Frame2PGSharpShunoHunt = None
        self.boolDisableAutoRestart = None
        self.boolShinyHuntAutoCatch = None
        self.tab2Frame2ShinyAutoCatch = None
        self.boolPGSharpReposition = None

        # Tap 2 Frame 3
        self.boolDiscordEnabled = None
        self.strWebhookAddress = None
        self.boolDiscordAll = None
        self.boolDiscordAllEncountered = None
        self.boolDiscordEncountered = None
        self.boolDiscordCaughtOrFled = None
        self.boolDiscord100IV = None
        self.boolDiscordPVP = None
        self.boolDiscordRestart = None

        # Tab 2 Fram 4
        self.boolQuestEnabled = None
        self.intPowerUp = None
        self.intClearQuest = None
        self.strQuestToday = None
        self.strQuestSpecial = None

        # Tab 3 Frame 1
        self.boolKeepMon = None
        self.intMinAtk = None
        self.intMinDef = None
        self.intMinSta = None
        self.boolUseOr = None
        self.intMinLvl = None
        self.boolKeepShiny = None
        self.boolKeepStrongShadow = None
        self.boolKeepLegendary = None
        self.boolKeepLucky = None
        self.boolKeepEvent = None
        self.boolShinyTap = None
        self.dblAppraisalDelay = None
        self.txtHighFarPokemon = None
        self.txtMon2Keep = None
        self.txtShadow2Keep = None
        self.txtPoke2Chase = None
        self.intStopAtBall = None
        self.intResumeAtBall = None
        self.intCatchEveryXSpin = None
        self.boolGoAfterShiny = None
        self.boolGoAfterMaxIV = None
        self.boolShinyMode = None

        # Tab 3 Frame 2
        self.boolUseBerry = None
        self.txtBerryP1 = None
        self.txtBerryP2 = None
        self.txtBerryP3 = None
        self.txtPinapExclusive = None

        # Tab 3 Frame 3
        self.boolSelectBall = None
        self.txtSelectBallP1 = None
        self.txtSelectBallP2 = None
        self.txtSelectBallP3 = None

        # Tab 3 Frame 4
        self.boolEnablePVP = None
        self.txtGL2Keep = None
        self.dblGLRating = None
        self.intGLCP = None

        self.txtUL2Keep = None
        self.dblULRating = None
        self.intULCP = None

        # Tab 4 Frame 1
        self.boolEnablePokeManagement = None
        self.boolManageOnStart = None
        self.tab4Frame1InventoryIV = None
        self.intStopCheck = None
        self.boolMassTransfer = None
        self.strPokeBagSearch = None

        # Tab 4 Frame 2
        self.boolEnableItemManagement = None
        self.boolClearItemOnStart = None
        self.boolManageGiftsOnStart = None
        self.boolAutoMax = None
        self.intItemInterval = None
        self.intBagFullInterval = None
        self.strItem2Quit = None
        self.itemEntries = []

        # Tab 5 Frame 1
        self.boolEnableTelegramFeed = None
        self.strTelegramApiID = None
        self.strTelegramApiHash = None
        self.strTelegramProxy = None

        # Tab 5 Frame 2
        self.tab5Frame2 = None
        self.boolEnableShinyCheck = None
        self.boolFeedFree = None
        self.tab5Frame2Feed100IVShiny = None
        self.tab5Frame2Feed82IVShiny = None
        self.tab5Frame2PVPShiny = None
        self.tab5Frame2FeedRare100IV = None
        self.boolFeed100IVShiny = None
        self.boolFeed82IVShiny = None
        self.boolFeedPVP = None
        self.boolFeedRare100IV = None
        self.boolShinyAutoCatch = None
        self.txtShinyMon2Catch = None
        self.txtShinyMon2Ignore = None

        # Tab 5 Frame 3
        self.tab5Frame3 = None
        self.boolEnableSnipeCheck = None
        self.boolSnipeAutoCatch = None
        self.strSnipeMaxCD = None
        self.tab5Frame3SnipeList = None

        self.boolSnipeFeedFree = None
        self.tab5Frame3Feed100IVShiny = None
        self.tab5Frame3Feed82IVShiny = None
        self.tab5Frame3PVP = None
        self.tab5Frame3FeedRare100IV = None
        self.boolSnipeFeed100IVShiny = None
        self.boolSnipeFeed82IVShiny = None
        self.boolSnipeFeedPVP = None
        self.boolSnipeFeedRare100IV = None
        self.strSnipeRouteName = None
        self.strSnipeCoordinates = None
        self.tab5Frame3SnipeCoordinates = None

        # Items
        self.var1 = None
        self.var2 = None
        self.var3 = None
        self.var4 = None
        self.var5 = None
        self.var6 = None
        self.var7 = None
        self.var8 = None
        self.var9 = None
        self.var10 = None
        self.var11 = None
        self.var12 = None
        self.var13 = None
        self.var14 = None

    async def print_id(self):
        me = await self.client.get_me()
        self.telegram_id = me.id
        logger.info('Your Telegram ID: {}'.format(self.telegram_id))
        with session_scope() as session:
            donor_until = vaild_subscription(session, self.telegram_id)

    def disableChildren(self, parent):
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ('Frame', 'Labelframe'):
                child.configure(state='disable')
            else:
                self.disableChildren(child)

    def enableChildren(self, parent):
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ('Frame', 'Labelframe'):
                child.configure(state='normal')
            else:
                self.enableChildren(child)

    def start_telegram(self):
        logger.info('Starting Telegram...')
        if self.device_id:
            tg_session_name = self.device_id.upper()
            tg_session_file = self.device_id.upper()
        else:
            tg_session_name = 'TG_SESSION'
            tg_session_file = 'CONFIG'

        session = os.environ.get(tg_session_name, tg_session_file)

        if self.config['telegram'].get('telegram_api_id', False):
            api_id = self.config['telegram'].get('telegram_api_id')
        else:
            self.get_env('TG_API_ID', 'Enter your API ID: ', int)

        if self.config['telegram'].get('telegram_api_hash', False):
            api_hash = self.config['telegram'].get('telegram_api_hash')
        else:
            self.get_env('TG_API_HASH', 'Enter your API hash: ')
        proxy = self.config['telegram'].get('proxy', '')
        try:
            self.client = TelegramClient(session, api_id, api_hash, proxy=proxy).start()
        except errors.FloodWaitError as e:
            logger.info('Have to sleep', e.seconds, 'seconds')
            time.sleep(e.seconds + 1)
            self.client = TelegramClient(session, api_id, api_hash, proxy=proxy).start()

        # with self.client:
        self.client.loop.run_until_complete(self.print_id())

    def shutdown_telegram(self):
        logger.info('Shuting down Telegram...')
        self.client.loop.stop()
        self.client.disconnect()

    def get_env(self, name, message, cast=str):
        if name in os.environ:
            return os.environ[name]
        while True:
            value = input(message)
            try:
                return cast(value)
            except ValueError as e:
                logger.info(e, file=sys.stderr)
                time.sleep(1)

    def set_lang_eng(self):
        self.gui_lang = 'english'
        self.config['client']['gui_language'] = self.gui_lang
        self.save_config()
        messagebox.showinfo(title='Command Send', message='Closing RAB, please restart to change language')
        sys.exit(1)
        # refresh()

    def set_lang_ger(self):
        self.gui_lang = 'german'
        self.config['client']['gui_language'] = self.gui_lang
        self.save_config()
        messagebox.showinfo(title='Command Send', message='Closing RAB, please restart to change language')
        sys.exit(1)
        # refresh()

    def start_rab(self):
        self.save_config()
        self.win_main.withdraw()
        if config['telegram'].get('enabled'):
            rab.call_main(events, self.client, self.telegram_id, self.donor_until)
        else:
            rab.call_main()

    def close_win(self):
        self.win_main.destroy()

    def on_enter(self, event, msg):
        self.results.config(text=msg, foreground='Blue')

    def on_leave(self, event):
        self.results.config(text='')

    def save_config(self):
        with open(self.config_path, 'w') as file:
            documents = yaml.dump(self.config, file)
        self.results.config(text=self.lang[self.gui_lang]['infoConfigSaved'].replace(
            '\\n', '\n').replace('\\t', '\t'), foreground='Blue')

    # def set_resolution(self):
    #    x = 1080
    #    y = 1920
    #    args = [
    #        "adb",
    #        "-s",
    #        await self.get_device(),
    #        "shell",
    #        "wm",
    #        "size",
    #        str(x)+"x"+str(y)
    #    ]
    #    await self.run(args)

    def reset_resolution(self):
        adb_path = rab.get_adb(self.config['client']['type'])
        print(adb_path)
        args = [
            adb_path,
            "-s",
            self.device_id,
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
            self.device_id,
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
            self.device_id,
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
            self.device_id,
            "shell",
            "wm",
            "overscan",
            "0,0,0,0"
        ]
        p = subprocess.Popen([str(arg) for arg in args], stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()

        messagebox.showinfo(title='Command Send', message=self.lang[self.gui_lang]['infoResolutionReset'].replace(
            '\\n', '\n').replace('\\t', '\t'))

    def default_disable(self):
        networkStatus = tk.DISABLED
        if self.config['client']['client'] == 'None':
            self.tab2Frame1TeamRocket.config(state=tk.DISABLED)
            self.tab2Frame1InstantSpin.config(state=tk.DISABLED)
            self.tab2Frame1SkipIntro.config(state=tk.DISABLED)
            self.tab2Frame1EncounterIV.config(state=tk.DISABLED)
            self.tab2Frame1QuickCatch.config(state=tk.DISABLED)
            self.tab2Frame2AutoRoute.config(state=tk.DISABLED)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.DISABLED)

            self.tab4Frame1InventoryIV.config(state=tk.DISABLED)
            self.tab2Frame2PGSharpShunoHunt.config(state=tk.DISABLED)

            self.tab4Frame2AutoMax.config(state=tk.DISABLED)
            self.enableChildren(self.tab5)
        elif self.config['client']['client'] == 'PGSharp':
            self.tab2Frame1TeamRocket.config(state=tk.DISABLED)
            self.tab2Frame1InstantSpin.config(state=tk.DISABLED)
            self.tab2Frame1SkipIntro.config(state=tk.DISABLED)
            self.tab2Frame1EncounterIV.config(state=tk.NORMAL)
            self.tab2Frame1QuickCatch.config(state=tk.DISABLED)
            self.tab2Frame2AutoRoute.config(state=tk.NORMAL)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.NORMAL)

            self.tab4Frame1InventoryIV.config(state=tk.NORMAL)
            self.tab2Frame2PGSharpShunoHunt.config(state=tk.NORMAL)

            self.tab4Frame2AutoMax.config(state=tk.DISABLED)
            self.disableChildren(self.tab5Frame2)
            self.disableChildren(self.tab5Frame3)
        elif self.config['client']['client'] == 'PGSharp Paid':
            self.tab2Frame1TeamRocket.config(state=tk.NORMAL)
            self.tab2Frame1InstantSpin.config(state=tk.DISABLED)
            self.tab2Frame1SkipIntro.config(state=tk.NORMAL)
            self.tab2Frame1EncounterIV.config(state=tk.NORMAL)
            self.tab2Frame1QuickCatch.config(state=tk.NORMAL)
            self.tab2Frame2AutoRoute.config(state=tk.NORMAL)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.NORMAL)

            self.tab4Frame1InventoryIV.config(state=tk.NORMAL)
            self.tab2Frame2PGSharpShunoHunt.config(state=tk.NORMAL)

            self.tab4Frame2AutoMax.config(state=tk.DISABLED)
            self.disableChildren(self.tab5Frame2)
            self.disableChildren(self.tab5Frame3)
        elif self.config['client']['client'] == 'MAD':
            self.tab2Frame1TeamRocket.config(state=tk.DISABLED)
            self.tab2Frame1InstantSpin.config(state=tk.DISABLED)
            self.tab2Frame1SkipIntro.config(state=tk.DISABLED)
            self.tab2Frame1EncounterIV.config(state=tk.NORMAL)
            self.tab2Frame1QuickCatch.config(state=tk.NORMAL)
            self.tab2Frame2AutoRoute.config(state=tk.NORMAL)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.DISABLED)

            self.tab4Frame1InventoryIV.config(state=tk.DISABLED)
            self.tab2Frame2PGSharpShunoHunt.config(state=tk.DISABLED)

            self.tab4Frame2AutoMax.config(state=tk.NORMAL)
            self.enableChildren(self.tab5)
        elif self.config['client']['client'] == 'Pokemod':
            self.tab2Frame1TeamRocket.config(state=tk.DISABLED)
            self.tab2Frame1InstantSpin.config(state=tk.NORMAL)
            self.tab2Frame1SkipIntro.config(state=tk.NORMAL)
            self.tab2Frame1EncounterIV.config(state=tk.NORMAL)
            self.tab2Frame1QuickCatch.config(state=tk.NORMAL)
            self.tab2Frame2AutoRoute.config(state=tk.NORMAL)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.DISABLED)

            self.tab4Frame1InventoryIV.config(state=tk.DISABLED)
            self.tab2Frame2PGSharpShunoHunt.config(state=tk.DISABLED)

            self.tab4Frame2AutoMax.config(state=tk.DISABLED)
            self.enableChildren(self.tab5)
        elif self.config['client']['client'] == 'HAL':
            self.tab2Frame1TeamRocket.config(state=tk.NORMAL)
            self.tab2Frame1InstantSpin.config(state=tk.NORMAL)
            self.tab2Frame1SkipIntro.config(state=tk.NORMAL)
            self.tab2Frame1EncounterIV.config(state=tk.NORMAL)
            self.tab2Frame1QuickCatch.config(state=tk.NORMAL)
            self.tab2Frame2AutoRoute.config(state=tk.NORMAL)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.DISABLED)

            self.tab4Frame1InventoryIV.config(state=tk.DISABLED)
            self.tab2Frame2PGSharpShunoHunt.config(state=tk.DISABLED)

            self.tab4Frame2AutoMax.config(state=tk.NORMAL)
            self.enableChildren(self.tab5)
        elif self.config['client']['client'] == 'Polygon':
            self.tab2Frame1TeamRocket.config(state=tk.NORMAL)
            self.tab2Frame1InstantSpin.config(state=tk.NORMAL)
            self.tab2Frame1SkipIntro.config(state=tk.NORMAL)
            self.tab2Frame1EncounterIV.config(state=tk.NORMAL)
            self.tab2Frame1QuickCatch.config(state=tk.NORMAL)
            self.tab2Frame2AutoRoute.config(state=tk.NORMAL)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.DISABLED)

            self.tab4Frame1InventoryIV.config(state=tk.DISABLED)

            self.tab2Frame2PGSharpShunoHunt.config(state=tk.DISABLED)

            self.tab4Frame2AutoMax.config(state=tk.DISABLED)
            self.enableChildren(self.tab5)
        elif self.config['client']['client'] == 'Polygon Paid':
            self.tab2Frame1TeamRocket.config(state=tk.NORMAL)
            self.tab2Frame1InstantSpin.config(state=tk.NORMAL)
            self.tab2Frame1SkipIntro.config(state=tk.NORMAL)
            self.tab2Frame1EncounterIV.config(state=tk.NORMAL)
            self.tab2Frame1QuickCatch.config(state=tk.NORMAL)
            self.tab2Frame2AutoRoute.config(state=tk.DISABLED)
            self.tab2Frame2ShinyAutoCatch.config(state=tk.DISABLED)

            self.tab2Frame2PGSharpShunoHunt.config(state=tk.DISABLED)

            self.tab2Frame2PokestopPriority.config(state=tk.DISABLED)
            self.txtPoke2Chase.config(state=tk.NORMAL)
            self.tab3Frame1StopAtBall.config(state=tk.NORMAL)
            self.tab3Frame1ResumeAtBall.config(state=tk.NORMAL)
            self.tab3Frame1CatchEveryXSpin.config(state=tk.NORMAL)
            self.tab3Frame1GoAfterShiny.config(state=tk.NORMAL)
            self.tab3Frame1GoAfterMaxIV.config(state=tk.NORMAL)
            self.tab3Frame1ShinyMode.config(state=tk.NORMAL)
            self.tab2Frame2AutoSlotGym.config(state=tk.NORMAL)
            self.tab4Frame1InventoryIV.config(state=tk.DISABLED)

            self.tab4Frame2AutoMax.config(state=tk.DISABLED)
            self.enableChildren(self.tab5)

            self.boolAutoRoute.set(0)
            networkStatus = tk.NORMAL
        elif self.config['client']['client'] == 'Polygon Farmer':
            messagebox.showinfo(
                title='Information', message='Please note that all catch will be send to your webhook in this version. More options for farmer will be availible in next version')

        if self.config['client']['client'] != 'Polygon Paid':
            self.tab2Frame2PokestopPriority.config(state=tk.NORMAL)
            self.tab2Frame2AutoSlotGym.config(state=tk.DISABLED)

            self.tab3Frame1StopAtBall.config(state=tk.DISABLED)
            self.txtPoke2Chase.config(state=tk.DISABLED)
            self.tab3Frame1ResumeAtBall.config(state=tk.DISABLED)
            self.tab3Frame1CatchEveryXSpin.config(state=tk.DISABLED)
            self.tab3Frame1GoAfterShiny.config(state=tk.DISABLED)
            self.tab3Frame1GoAfterMaxIV.config(state=tk.DISABLED)
            self.tab3Frame1ShinyMode.config(state=tk.DISABLED)
        self.tab2Frame2Host.config(state=networkStatus)
        self.tab2Frame2Port.config(state=networkStatus)

    # Tab 2 Frame 1
    def change_dropdown(self, *args):
        self.config['client']['client'] = self.clientVar.get()
        self.config['client']['type'] = self.typeVar.get()

        if self.config['client']['client'] == 'None':
            self.config['client']['team_rocket_blastoff'] = False
            self.boolTeamRocket.set(0)
            self.config['client']['instant_spin'] = False
            self.boolInstantSpin.set(0)
            self.config['client']['skip_encounter_intro'] = False
            self.boolSkipIntro.set(0)
            self.config['client']['encounter_iv'] = False
            self.boolEncounterIV.set(0)
            self.config['client']['transfer_on_catch'] = False
            self.boolQuickCatch.set(0)
            self.config['client']['auto_route'] = True
            self.boolAutoRoute.set(1)

            self.config['item_management']['auto_max'] = False
            self.boolAutoMax.set(0)
        elif self.config['client']['client'] == 'PGSharp':
            #self.config['client']['team_rocket_blastoff'] = False
            # self.boolTeamRocket.set(0)
            self.config['client']['instant_spin'] = False
            self.boolInstantSpin.set(0)
            self.config['client']['skip_encounter_intro'] = False
            self.boolSkipIntro.set(0)
            self.config['client']['encounter_iv'] = True
            self.boolEncounterIV.set(1)
            self.config['client']['transfer_on_catch'] = False
            self.boolQuickCatch.set(0)
            self.config['client']['auto_route'] = False
            self.boolAutoRoute.set(0)

            self.config['item_management']['auto_max'] = False
            self.boolAutoMax.set(0)
        elif self.config['client']['client'] == 'PGSharp Paid':
            self.config['client']['team_rocket_blastoff'] = False
            self.boolTeamRocket.set(0)
            self.config['client']['instant_spin'] = False
            self.boolInstantSpin.set(0)
            self.config['client']['skip_encounter_intro'] = True
            self.boolSkipIntro.set(1)
            self.config['client']['encounter_iv'] = True
            self.boolEncounterIV.set(1)
            self.config['client']['transfer_on_catch'] = True
            self.boolQuickCatch.set(1)
            self.config['client']['auto_route'] = True
            self.boolAutoRoute.set(1)

            self.config['item_management']['auto_max'] = False
            self.boolAutoMax.set(0)
        elif self.config['client']['client'] == 'MAD':
            self.config['client']['team_rocket_blastoff'] = False
            self.boolTeamRocket.set(0)
            self.config['client']['instant_spin'] = False
            self.boolInstantSpin.set(0)
            self.config['client']['skip_encounter_intro'] = False
            self.boolSkipIntro.set(0)
            self.config['client']['encounter_iv'] = True
            self.boolEncounterIV.set(1)
            self.config['client']['transfer_on_catch'] = True
            self.boolQuickCatch.set(1)
            self.config['client']['auto_route'] = True
            self.boolAutoRoute.set(1)

            self.config['item_management']['auto_max'] = False
            self.boolAutoMax.set(0)
        elif self.config['client']['client'] == 'Pokemod':
            self.config['client']['team_rocket_blastoff'] = False
            self.boolTeamRocket.set(0)
            self.config['client']['instant_spin'] = True
            self.boolInstantSpin.set(1)
            self.config['client']['skip_encounter_intro'] = True
            self.boolSkipIntro.set(1)
            self.config['client']['encounter_iv'] = True
            self.boolEncounterIV.set(1)
            self.config['client']['transfer_on_catch'] = True
            self.boolQuickCatch.set(1)
            self.config['client']['auto_route'] = True
            self.boolAutoRoute.set(1)

            self.config['item_management']['auto_max'] = False
            self.boolAutoMax.set(0)
        elif self.config['client']['client'] == 'HAL':
            self.config['client']['team_rocket_blastoff'] = True
            self.boolTeamRocket.set(1)
            self.config['client']['instant_spin'] = True
            self.boolInstantSpin.set(1)
            self.config['client']['skip_encounter_intro'] = True
            self.boolSkipIntro.set(1)
            self.config['client']['encounter_iv'] = True
            self.boolEncounterIV.set(1)
            self.config['client']['transfer_on_catch'] = True
            self.boolQuickCatch.set(1)
            self.config['client']['auto_route'] = True
            self.boolAutoRoute.set(1)

            self.config['item_management']['auto_max'] = True
            self.boolAutoMax.set(1)
        elif self.config['client']['client'] == 'Polygon':
            self.config['client']['team_rocket_blastoff'] = True
            self.boolTeamRocket.set(1)
            self.config['client']['instant_spin'] = True
            self.boolInstantSpin.set(1)
            self.config['client']['skip_encounter_intro'] = True
            self.boolSkipIntro.set(1)
            self.config['client']['encounter_iv'] = True
            self.boolEncounterIV.set(1)
            self.config['client']['transfer_on_catch'] = True
            self.boolQuickCatch.set(1)
            self.config['client']['auto_route'] = True
            self.boolAutoRoute.set(1)

            self.config['item_management']['auto_max'] = False
            self.boolAutoMax.set(0)
        elif self.config['client']['client'] == 'Polygon Paid':
            self.config['client']['team_rocket_blastoff'] = True
            self.boolTeamRocket.set(1)
            self.config['client']['instant_spin'] = True
            self.boolInstantSpin.set(1)
            self.config['client']['skip_encounter_intro'] = True
            self.boolSkipIntro.set(1)
            self.config['client']['encounter_iv'] = True
            self.boolEncounterIV.set(1)
            self.config['client']['transfer_on_catch'] = True
            self.boolQuickCatch.set(1)
            self.config['client']['auto_route'] = False
            self.boolAutoRoute.set(0)

            self.config['item_management']['auto_max'] = False
            self.boolAutoMax.set(0)

        elif self.config['client']['client'] == 'Polygon Farmer':
            messagebox.showinfo(
                title='Information', message='Please note that all catch will be send to your webhook in this version. More options for farmer will be availible in next version')

        if self.config['client']['client'] != 'Polygon Paid':
            self.boolPokestopPriority.set(1)
            self.config['spin_pokestop'] = True

            self.config['client']['auto_slot'] = False
            self.boolAutoSlotGym.set(0)

        self.default_disable()
        # ['None', 'PGSharp', 'PGSharp Paid', 'Pokemod', 'HAL' ,'Polygon' ,'Polygon Paid']

    def teamRocket_checkbox(self):
        self.config['client']['team_rocket_blastoff'] = bool(self.boolTeamRocket.get())

    def instantSpin_checkbox(self):
        self.config['client']['instant_spin'] = bool(self.boolInstantSpin.get())

    def skipIntro_checkbox(self):
        self.config['client']['skip_encounter_intro'] = bool(self.boolSkipIntro.get())

    def encounterIV_checkbox(self):
        self.config['client']['encounter_iv'] = bool(self.boolEncounterIV.get())

    def quickCatch_checkbox(self):
        self.config['client']['transfer_on_catch'] = bool(self.boolQuickCatch.get())

    def autoRoute_checkbox(self):
        self.config['client']['auto_route'] = bool(self.boolAutoRoute.get())

    def pokestopPriority_checkbox(self):
        self.config['spin_pokestop'] = bool(self.boolPokestopPriority.get())

    def autoGoplus_checkbox(self):
        self.config['client']['auto_goplus'] = bool(self.boolAutoGoplus.get())

    def Host_entry(self, event):
        self.config['network']['host'] = self.strHost.get()

    def Port_entry(self, event):
        try:
            self.config['network']['port'] = int(self.strPort.get())
            self.results.config(text='', foreground='Blue')
        except:
            self.results.config(text=self.lang[self.gui_lang]['errorNumbers'].replace(
                '\\n', '\n').replace('\\t', '\t'), foreground='Red')

    def autoSlotGym_checkbox(self):
        self.config['client']['auto_slot'] = bool(self.boolAutoSlotGym.get())

    def advanceBerryCheck_checkbox(self):
        self.config['client']['advance_berry_check'] = bool(self.boolAdvanceBerryCheck.get())

    def zoomMethod_dropdown(self, *args):
        self.config['client']['zoom_option'] = self.ZoomOutVar.get()

    def pgsharpShuno_checkbox(self):
        self.config['client']['pgsharp_shuno_hunt'] = bool(self.boolPGSharpShuno.get())

    def pgsharpReposition_checkbox(self):
        self.config['client']['pgsharp_reposition'] = bool(self.boolPGSharpReposition.get())

    def disableAutoRestart_checkbox(self):
        self.config['client']['disable_auto_restart'] = bool(self.boolDisableAutoRestart.get())

    # Tab 2 Frame 2
    def manualResolution_checkbox(self):
        self.config['client']['manual_set_resolution'] = bool(self.boolManualResolution.get())

    def autoOffset_checkbox(self):
        self.config['client']['auto_offset'] = bool(self.boolAutoOffset.get())

    def screenOffset_scale(self, *args):
        self.config['client']['screen_offset'] = self.intScreenOffset.get()

    def navigationOffset_scale(self, *args):
        self.config['client']['navigation_offset'] = self.intNavigationOffset.get()

    def screenshotOffset_scale(self, *args):
        self.config['client']['screenshot_shift'] = self.intScreenshotOffset.get()

    def lowerResolution_checkbox(self):
        self.config['client']['lower_resolution'] = bool(self.boolLowerResolution.get())

    def delayTime_entry(self, event):
        try:
            self.config['client']['delay'] = float(self.strDelayTime.get())
            self.results.config(text='Vaild Entry', foreground='Blue')
        except:
            self.results.config(text='Invaild numbers', foreground='Red')

    def density_entry(self, event):
        try:
            self.config['client']['dpi'] = float(self.strDensity.get())
            self.results.config(text='Vaild Entry', foreground='Blue')
        except:
            self.results.config(text='Invaild numbers', foreground='Red')

    def shinyHuntAutoCatch_checkbox(self):
        self.config['shiny_check']['auto_catch'] = bool(self.boolShinyHuntAutoCatch.get())

    def dimPhone_checkbox(self):
        self.config['client']['dim_phone'] = bool(self.boolDimPhone.get())

    # Tab 2 Frame 3
    def discordEnabled_checkbox(self):
        self.config['discord']['enabled'] = bool(self.boolDiscordEnabled.get())

    def webhookAddress_entry(self, event):
        self.config['discord']['webhook_url'] = self.strWebhookAddress.get()

    def manualDiscordAll_checkbox(self):
        self.config['discord']['notify_all_caught'] = bool(self.boolDiscordAll.get())

    def manualDiscordAllEncountered_checkbox(self):
        self.config['discord']['notify_all_encountered'] = bool(self.boolDiscordAllEncountered.get())

    def manualDiscordEncountered_checkbox(self):
        self.config['discord']['notify_encountered'] = bool(self.boolDiscordEncountered.get())

    def manualDiscordCaughtOrFled_checkbox(self):
        self.config['discord']['notify_caught_fled'] = bool(self.boolDiscordCaughtOrFled.get())

    def manualDiscordShiny_checkbox(self):
        self.config['discord']['notify_shiny'] = bool(self.boolDiscordShiny.get())

    def manualDiscord100IV_checkbox(self):
        self.config['discord']['notify_max_iv'] = bool(self.boolDiscord100IV.get())

    def manualDiscordPVP_checkbox(self):
        self.config['discord']['notify_pvp_iv'] = bool(self.boolDiscordPVP.get())

    def manualDiscordRestart_checkbox(self):
        self.config['discord']['restart'] = bool(self.boolDiscordRestart.get())

    # Tab 2 Frame 4
    def questEnabled_checkbox(self):
        self.config['quest']['enable_check_quest'] = bool(self.boolQuestEnabled.get())

    def powerUp_scale(self, *args):
        self.config['quest']['power_up_lvl'] = self.intPowerUp.get()

    def clearQuest_scale(self, *args):
        self.config['quest']['clear_quest_interval'] = self.intClearQuest.get()

    def QuestToday_entry(self, event):
        self.config['quest']['last_quest_quit_today'] = self.strQuestToday.get()

    def QuestSpecial_entry(self, event):
        self.config['quest']['last_quest_quit'] = self.strQuestSpecial.get()

    # Tab 3
    # Tab 3 Frame 1
    def keepMon_checkbox(self):
        self.config['catch']['enable_keep_mon'] = bool(self.boolKeepMon.get())

    def minAtk_scale(self, *args):
        self.config['catch']['min_atk'] = self.intMinAtk.get()

    def minDef_scale(self, *args):
        self.config['catch']['min_def'] = self.intMinDef.get()

    def minSta_scale(self, *args):
        self.config['catch']['min_sta'] = self.intMinSta.get()

    def useOr_checkbox(self):
        self.config['catch']['or_condition'] = bool(self.boolUseOr.get())

    def minLvl_scale(self, *args):
        self.config['catch']['min_lvl'] = self.intMinLvl.get()

    def keepShiny_checkbox(self):
        self.config['catch']['enable_keep_shiny'] = bool(self.boolKeepShiny.get())

    def keepStrongShadow_checkbox(self):
        self.config['catch']['keep_strong_shadow'] = bool(self.boolKeepStrongShadow.get())

    def keepLegendary_checkbox(self):
        self.config['catch']['keep_legendary'] = bool(self.boolKeepLegendary.get())

    def keepLucky_checkbox(self):
        self.config['catch']['keep_lucky'] = bool(self.boolKeepLucky.get())

    def keepEvent_checkbox(self):
        self.config['catch']['keep_event'] = bool(self.boolKeepEvent.get())

    def shinyTap_checkbox(self):
        self.config['catch']['only_shiny'] = bool(self.boolShinyTap.get())

    def appraisalDelay_scale(self, *args):
        self.config['catch']['delay_before_appraisal'] = self.dblAppraisalDelay.get()

    def highFarPokemon_entry(self, event):
        self.config['catch']['high_far_pokemon'] = self.text2list(self.txtHighFarPokemon.get("1.0", tk.END))

    def mon2Keep_entry(self, event):
        self.config['catch']['mon_to_keep'] = self.text2list(self.txtMon2Keep.get("1.0", tk.END))

    def shadow2Keep_entry(self, event):
        self.config['catch']['shadow_mon_to_keep'] = self.text2list(self.txtShadow2Keep.get("1.0", tk.END))

    def poke2Chase_entry(self, event):
        self.config['catch']['mon_to_chase'] = self.text2list(self.txtPoke2Chase.get("1.0", tk.END))

    def stopAtBall_scale(self, *args):
        self.config['catch']['stop_at_ball'] = self.intStopAtBall.get()

    def resumeAtBall_scale(self, *args):
        self.config['catch']['resume_at_ball'] = self.intResumeAtBall.get()

    def catchEveryXSpin_scale(self, *args):
        self.config['catch']['catchpoke_every_x_spin'] = self.intCatchEveryXSpin.get()

    def goAfterShiny_checkbox(self):
        self.config['catch']['go_after_shiny'] = bool(self.boolGoAfterShiny.get())

    def goAfterMaxIV_checkbox(self):
        self.config['catch']['go_after_100IV'] = bool(self.boolGoAfterMaxIV.get())

    def shinyMode_checkbox(self):
        self.config['catch']['shiny_mode'] = bool(self.boolShinyMode.get())

    # Tab 3 Frame 2
    def useBerry_checkbox(self):
        self.config['berry_selection']['use_berry'] = bool(self.boolUseBerry.get())

    def berryP1_entry(self, event):
        self.config['berry_selection']['shiny_or_high_lvl'] = self.text2list(self.txtBerryP1.get("1.0", tk.END))

    def berryP2_entry(self, event):
        self.config['berry_selection']['mid_lvl'] = self.text2list(self.txtBerryP2.get("1.0", tk.END))

    def berryP3_entry(self, event):
        self.config['berry_selection']['low_lvl_or_unknown'] = self.text2list(self.txtBerryP3.get("1.0", tk.END))

    def pinapExclusive_entry(self, event):
        self.config['berry_selection']['pinap_exclusive'] = self.text2list(self.txtPinapExclusive.get("1.0", tk.END))

    # Tab 3 Frame 3
    def selectBall_checkbox(self):
        self.config['ball_selection']['select_ball'] = bool(self.boolSelectBall.get())

    def takeSnapshot_checkbox(self):
        self.config['ball_selection']['take_snapshot'] = bool(self.booltakeSnapshot.get())

    def selectBallP1_entry(self, event):
        self.config['ball_selection']['shiny_or_high_lvl'] = self.text2list(self.txtSelectBallP1.get("1.0", tk.END))

    def selectBallP2_entry(self, event):
        self.config['ball_selection']['mid_lvl'] = self.text2list(self.txtSelectBallP2.get("1.0", tk.END))

    def selectBallP3_entry(self, event):
        self.config['ball_selection']['low_lvl_or_unknown'] = self.text2list(self.txtSelectBallP3.get("1.0", tk.END))

    # Tab 3 Frame 4
    def enablePVP_checkbox(self):
        self.config['pvp']['enable_keep_pvp'] = bool(self.boolEnablePVP.get())

    def gl2Keep_entry(self, event):
        self.config['pvp']['gl_to_keep'] = self.text2list(self.txtGL2Keep.get("1.0", tk.END))

    def glRating_scale(self, *args):
        self.config['pvp']['gl_rating'] = self.dblGLRating.get()

    def glCP_scale(self, *args):
        self.config['pvp']['gl_cp'] = self.intGLCP.get()

    def ul2Keep_entry(self, event):
        self.config['pvp']['ul_to_keep'] = self.text2list(self.txtUL2Keep.get("1.0", tk.END))

    def ulRating_scale(self, *args):
        self.config['pvp']['ul_rating'] = self.dblULRating.get()

    def ulCP_scale(self, *args):
        self.config['pvp']['ul_cp'] = self.intULCP.get()

    # Tab 4
    # Tab 4 Frame 1
    def enablePokeManagement_checkbox(self):
        self.config['poke_management']['enable_poke_management'] = bool(self.boolEnablePokeManagement.get())

    def manageOnStart_checkbox(self):
        self.config['poke_management']['manage_poke_on_start'] = bool(self.boolManageOnStart.get())

    def inventoryIV_checkbox(self):
        self.config['poke_management']['inventory_iv'] = bool(self.boolInventoryIV.get())

    def stopCheck_scale(self, *args):
        self.config['poke_management']['stop_check_at'] = self.intStopCheck.get()

    def massTransfer_checkbox(self):
        self.config['poke_management']['mass_transfer'] = bool(self.boolMassTransfer.get())

    def pokeBagSearch_entry(self, *args):
        self.config['poke_management']['poke_search_string'] = self.strPokeBagSearch.get()

    # Tab 4 Frame 2
    def enableItemManagement_checkbox(self):
        self.config['item_management']['enable_item_management'] = bool(self.boolEnableItemManagement.get())

    def clearItemOnStart_checkbox(self):
        self.config['item_management']['clear_item_on_start'] = bool(self.boolClearItemOnStart.get())

    def manageGiftsOnStart_checkbox(self):
        self.config['item_management']['manage_gifts_on_start'] = bool(self.boolManageGiftsOnStart.get())

    def giftInterval_scale(self, *args):
        self.config['item_management']['gift_interval'] = self.intGiftInterval.get()

    def autoMax_checkbox(self):
        self.config['item_management']['auto_max'] = bool(self.boolAutoMax.get())

    def itemInterval_scale(self, *args):
        self.config['item_management']['item_management_interval'] = self.intItemInterval.get()

    def bagFullInterval_scale(self, *args):
        self.config['item_management']['reset_bagfull_interval'] = self.intBagFullInterval.get()

    def item2Quit_entry(self, *args):
        self.config['item_management']['last_item_quit'] = self.strItem2Quit.get()

    def itemCallback(self, key, var):
        self.config['item_config'][key] = int(var.get())
        # print('{}:{}'.format(key,var.get()))

    def itemAction(self, ix, key, event):
        text = self.itemEntries[ix].get()
        try:
            self.config['item_config'][key] = int(text)
        except:
            logger.warning("Please ensure only numbers are entered")

    # Tab 5 Frame 1
    def enableTelegramFeed_checkbox(self):
        self.config['telegram']['enabled'] = bool(self.boolEnableTelegramFeed.get())
        if self.config['telegram']['enabled']:
            if self.config['telegram']['telegram_api_id'] and self.config['telegram']['telegram_api_hash']:
                self.start_telegram()
            else:
                messagebox.showinfo(title='Telegram API ID Needed',
                                    message='Please enter Telegram API ID before enable this option')
                self.boolEnableTelegramFeed.set(0)
                self.config['telegram']['enabled'] = False
        else:
            if self.client:
                self.shutdown_telegram()

        self.tab5Frame2Feed100IVShiny.config(state=tk.NORMAL)
        self.tab5Frame2Feed82IVShiny.config(state=tk.NORMAL)
        self.tab5Frame2FeedRare100IV.config(state=tk.NORMAL)
        self.tab5Frame3Feed100IVShiny.config(state=tk.NORMAL)
        self.tab5Frame3Feed82IVShiny.config(state=tk.NORMAL)
        self.tab5Frame3FeedRare100IV.config(state=tk.NORMAL)

    def telegramApiID_entry(self, event):
        try:
            tmpNum = int(self.strTelegramApiID.get())
            self.config['telegram']['telegram_api_id'] = tmpNum
            self.results.config(text='', foreground='Blue')
        except:
            self.results.config(text=self.lang[self.gui_lang]['errorNumbers'].replace(
                '\\n', '\n').replace('\\t', '\t'), foreground='Red')

    def telegramApiHash_entry(self, event):
        self.config['telegram']['telegram_api_hash'] = self.strTelegramApiHash.get()

    def telegramProxy_entry(self, event):
        self.config['telegram']['proxy'] = self.strTelegramProxy.get()

    # Tab 5 Frame 2
    def enableShinyCheck_checkbox(self):
        self.config['shiny_check']['enabled'] = bool(self.boolEnableShinyCheck.get())

    def feedFree_checkbox(self):
        if bool(self.boolFeedFree.get()):
            if 'Free Feed' not in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].append('Free Feed')
        else:
            if 'Free Feed' in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].remove('Free Feed')

    def feed100IVShiny_checkbox(self):
        if bool(self.boolFeed100IVShiny.get()):
            if '100IV Shiny' not in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].append('100IV Shiny')
        else:
            if '100IV Shiny' in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].remove('100IV Shiny')

    def feed82IVShiny_checkbox(self):
        if bool(self.boolFeed82IVShiny.get()):
            if '82IV Shiny' not in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].append('82IV Shiny')
        else:
            if '82IV Shiny' in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].remove('82IV Shiny')

    def feedRare100IV_checkbox(self):
        if bool(self.boolFeedRare100IV.get()):
            if 'Rare 100IV' not in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].append('Rare 100IV')
        else:
            if 'Rare 100IV' in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].remove('Rare 100IV')

    def feedPVP_checkbox(self):
        if bool(self.boolFeedPVP.get()):
            if 'PVP' not in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].append('PVP')
        else:
            if 'PVP' in self.config['shiny_check']['src_telegram']:
                self.config['shiny_check']['src_telegram'].remove('PVP')

    def shinyAutoCatch_checkbox(self):
        self.config['shiny_check']['auto_catch'] = bool(self.boolShinyAutoCatch.get())

    def shinyMon2Catch_entry(self, event):
        self.config['shiny_check']['mon_to_check'] = self.text2list(self.txtShinyMon2Catch.get("1.0", tk.END))

    def shinyMon2Ignore_entry(self, event):
        self.config['shiny_check']['mon_to_ignore'] = self.text2list(self.txtShinyMon2Ignore.get("1.0", tk.END))

    # Tab 5 Frame 3

    def enableSnipeCheck_checkbox(self):
        self.config['snipe']['enabled'] = bool(self.boolEnableSnipeCheck.get())

    def snipeAutoCatch_checkbox(self):
        self.config['snipe']['auto_catch'] = bool(self.boolSnipeAutoCatch.get())

    def snipeMaxCD_entry(self, event):
        try:
            self.config['snipe']['snipe_max_cd'] = int(self.strSnipeMaxCD.get())
        except:
            self.config['snipe']['snipe_max_cd'] = 120  # default

    def snipeList_entry(self, event):
        covertedResult = self.text2json(self.tab5Frame3SnipeList.get("1.0", tk.END))
        if isinstance(covertedResult, dict):
            self.config['snipe']['snipe_list'] = covertedResult
            self.results.config(text='Entry is vaild', foreground='Blue')
        else:
            self.results.config(text='Invaild Entry, please double check', foreground='Red')

    def feedSnipeFree_checkbox(self):
        if bool(self.boolSnipeFeedFree.get()):
            if 'Free Feed' not in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].append('Free Feed')
        else:
            if 'Free Feed' in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].remove('Free Feed')

    def feedSnipe100IV_checkbox(self):
        if bool(self.boolSnipeFeed100IVShiny.get()):
            if '100IV Shiny' not in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].append('100IV Shiny')
        else:
            if '100IV Shiny' in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].remove('100IV Shiny')

    def feedSnipe82IV_checkbox(self):
        if bool(self.boolSnipeFeed82IVShiny.get()):
            if '82IV Shiny' not in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].append('82IV Shiny')
        else:
            if '82IV Shiny' in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].remove('82IV Shiny')

    def feedSnipeRare100IV_checkbox(self):
        if bool(self.boolSnipeFeedRare100IV.get()):
            if 'Rare 100IV' not in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].append('Rare 100IV')
        else:
            if 'Rare 100IV' in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].remove('Rare 100IV')

    def feedSnipePVP_checkbox(self):
        if bool(self.boolSnipeFeedPVP.get()):
            if 'PVP' not in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].append('PVP')
        else:
            if 'PVP' in self.config['snipe']['src_telegram']:
                self.config['snipe']['src_telegram'].remove('PVP')

    def snipeRouteName_entry(self, event):
        self.config['snipe']['default_route_name'] = self.strSnipeRouteName.get()

    def snipeCoordinates_entry(self, event):
        self.config['snipe']['default_location'] = self.text2list(self.tab5Frame3SnipeCoordinates.get("1.0", tk.END))

    # Others
    def openBrowser(self, url):
        webbrowser.open_new(url)

    def list2text(self, list2convert):
        convertedText = ''
        for i, eachEntry in enumerate(list2convert):
            if i > 0:
                convertedText += ', '
            convertedText += str(eachEntry)
        return convertedText

    def json2text(self, jsonList):
        try:
            return json.dumps(jsonList)
        except:
            return False

    def text2json(self, jsonText):
        if jsonText == "":
            return {}
        try:
            return json.loads(jsonText)
        except:
            return False

    def text2list(self, text2convert):
        convertedList = []
        try:
            temptList = text2convert.split(',')
            for eachEntry in temptList:
                try:
                    convertedList.append(float(eachEntry.strip()))
                except:
                    convertedList.append(eachEntry.strip())
            return convertedList
        except:
            return []

    def constructTab1(self):
        # Tab 1 Instructions
        lang_frame = tk.Frame(self.tab1)
        lang_frame.pack(side=tk.TOP, anchor=tk.NE)
        but_ENG = tk.Button(lang_frame, text="English", command=self.set_lang_eng)
        but_ENG.pack(side=tk.RIGHT)
        but_TEST = tk.Button(lang_frame, text="Deutsch", command=self.set_lang_ger)
        but_TEST.pack(side=tk.RIGHT)

        instructions1title = tk.Label(self.tab1, text=self.lang[self.gui_lang]['tab1text1'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, wraplength=800, font='-weight bold')
        instructions1title.pack(side=tk.TOP, anchor=tk.W)

        #link1 = tk.Label(self.tab1, text="Phone Setup Instructions", foreground='Blue', cursor="hand2")
        #link1.pack(side=tk.TOP, anchor=tk.NW)
        # link1.bind("<Button-1>", lambda e: self.openBrowser("https://github.com/MerlionRock/RealAndroidBot#phone-requirements"))
        instructions1 = tk.Label(self.tab1, text=self.lang[self.gui_lang]['tab1text2'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, wraplength=800)
        instructions1.pack(side=tk.TOP, anchor=tk.W)

        xiaomiInstructions = tk.Label(self.tab1, text=self.lang[self.gui_lang]['tab1text3'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        xiaomiInstructions.pack(side=tk.TOP, anchor=tk.W)

        basewidth = 400
        img = Image.open("img/usb_debugging2.jpg")
        wpercent = (basewidth / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), Image.LANCZOS)
        self.imgInstructions = ImageTk.PhotoImage(img)
        xiaomiImage = tk.Label(self.tab1, image=self.imgInstructions)
        xiaomiImage.pack(side=tk.TOP, anchor=tk.W)

        samsungInstructions = tk.Label(self.tab1, text=self.lang[self.gui_lang]['samsungInstructions'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        samsungInstructions.pack(side=tk.TOP, anchor=tk.W)

        instructions2title = tk.Label(self.tab1, text=self.lang[self.gui_lang]['tab1text4'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, font='-weight bold')
        instructions2title.pack(side=tk.TOP, anchor=tk.W)

        instructions2 = tk.Label(self.tab1, text=self.lang[self.gui_lang]['tab1text5'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, wraplength=800)
        instructions2.pack(side=tk.TOP, anchor=tk.W)

        instructions3 = tk.Label(self.tab1, text=self.lang[self.gui_lang]['tab1text7'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, wraplength=800, foreground='Red')
        instructions3.pack(side=tk.TOP, anchor=tk.W)

        butStartRAB = tk.Button(self.tab1, text=self.lang[self.gui_lang]['tab1text6'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.start_rab)
        butStartRAB.pack()

        #self.console_box = tk.Text(self.tab1, wrap='word')
        #self.console_box.pack(expand=True, fill='both')

    def constructTab2(self):
        # Tab 2 Configurations
        tab2Frame1 = tk.LabelFrame(self.tab2, text=self.lang[self.gui_lang]['tab2Frame1'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab2Frame1.grid(row=0, columnspan=4, sticky='W')
        tab2Frame1.columnconfigure([0, 1, 2, 3], minsize=200)
        tab2Frame1.rowconfigure([0, 1, 2], minsize=25)

        # Tab 2 Frame 1
        # Client Preset
        tempF1ClientOption = tk.Frame(tab2Frame1)
        tempF1ClientOption.grid(row=0, column=0, columnspan=2, sticky="NSEW")

        self.clientVar = StringVar()
        clientChoices = ['None', 'MAD', 'PGSharp', 'PGSharp Paid',
                         'Pokemod', 'HAL', 'Polygon', 'Polygon Paid', 'Polygon Farmer']
        tab2Frame1Label1 = tk.Label(
            tempF1ClientOption, text=self.lang[self.gui_lang]['tab2Frame1Label1'].replace('\\n', '\n').replace('\\t', '\t'))

        tab2Frame1Options = ttk.OptionMenu(tempF1ClientOption, self.clientVar, self.config['client'].get(
            'client', 'PGSharp'), *clientChoices, command=self.change_dropdown)
        tab2Frame1Label1.pack(side=tk.LEFT)
        tab2Frame1Options.pack(side=tk.LEFT)
        tab2Frame1Options.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1OptionsMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame1Options.bind('<Leave>', self.on_leave)

        # Client type
        self.typeVar = StringVar()
        typeChoices = ['Real', 'Nox', 'MuMu']
        tab2Frame1Label2 = tk.Label(
            tempF1ClientOption, text=self.lang[self.gui_lang]['tab2Frame1Label2'].replace('\\n', '\n').replace('\\t', '\t'))

        tab2Frame1Options2 = ttk.OptionMenu(tempF1ClientOption, self.typeVar, self.config['client'].get(
            'type', 'Real'), *typeChoices, command=self.change_dropdown)
        tab2Frame1Label2.pack(side=tk.LEFT)
        tab2Frame1Options2.pack(side=tk.LEFT)
        tab2Frame1Options2.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1Option2Msg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame1Options2.bind('<Leave>', self.on_leave)

        # Team Rocket
        self.boolTeamRocket = IntVar()
        self.boolTeamRocket.set(self.config['client'].get('team_rocket_blastoff', 0))
        self.tab2Frame1TeamRocket = tk.Checkbutton(tab2Frame1, variable=self.boolTeamRocket, command=self.teamRocket_checkbox,
                                                   text=self.lang[self.gui_lang]['tab2Frame1TeamRocket'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame1TeamRocket.grid(row=1, column=0, sticky="W")
        self.tab2Frame1TeamRocket.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1TeamRocketMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame1TeamRocket.bind('<Leave>', self.on_leave)

        # Instant Spin
        self.boolInstantSpin = IntVar()
        self.boolInstantSpin.set(self.config['client'].get('instant_spin', 0))
        self.tab2Frame1InstantSpin = tk.Checkbutton(tab2Frame1, variable=self.boolInstantSpin, command=self.instantSpin_checkbox,
                                                    text=self.lang[self.gui_lang]['tab2Frame1InstantSpin'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame1InstantSpin.grid(row=1, column=1, sticky="W")
        self.tab2Frame1InstantSpin.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1InstantSpinMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame1InstantSpin.bind('<Leave>', self.on_leave)

        # Skip Encounter Intro
        self.boolSkipIntro = IntVar()
        self.boolSkipIntro.set(self.config['client'].get('skip_encounter_intro', 0))
        self.tab2Frame1SkipIntro = tk.Checkbutton(tab2Frame1, variable=self.boolSkipIntro, command=self.skipIntro_checkbox,
                                                  text=self.lang[self.gui_lang]['tab2Frame1SkipIntro'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame1SkipIntro.grid(row=1, column=2, sticky="W")
        self.tab2Frame1SkipIntro.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1SkipIntroMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame1SkipIntro.bind('<Leave>', self.on_leave)

        # Encounter IV
        self.boolEncounterIV = IntVar()
        self.boolEncounterIV.set(self.config['client'].get('encounter_iv', 0))
        self.tab2Frame1EncounterIV = tk.Checkbutton(tab2Frame1, variable=self.boolEncounterIV, command=self.encounterIV_checkbox,
                                                    text=self.lang[self.gui_lang]['tab2Frame1EncounterIV'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame1EncounterIV.grid(row=1, column=3, sticky="W")
        self.tab2Frame1EncounterIV.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1EncounterIVMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame1EncounterIV.bind('<Leave>', self.on_leave)

        # Quick Catch
        self.boolQuickCatch = IntVar()
        self.boolQuickCatch.set(self.config['client'].get('transfer_on_catch', 0))
        self.tab2Frame1QuickCatch = tk.Checkbutton(tab2Frame1, variable=self.boolQuickCatch, command=self.quickCatch_checkbox,
                                                   text=self.lang[self.gui_lang]['tab2Frame1QuickCatch'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame1QuickCatch.grid(row=2, column=0, sticky="W")
        self.tab2Frame1QuickCatch.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1QuickCatchMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame1QuickCatch.bind('<Leave>', self.on_leave)

        # Auto Route
        self.boolAutoRoute = IntVar()
        self.boolAutoRoute.set(self.config['client'].get('auto_route', 0))
        self.tab2Frame2AutoRoute = tk.Checkbutton(tab2Frame1, variable=self.boolAutoRoute, command=self.autoRoute_checkbox,
                                                  text=self.lang[self.gui_lang]['tab2Frame2AutoRoute'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame2AutoRoute.grid(row=2, column=1, sticky="W")
        self.tab2Frame2AutoRoute.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2AutoRouteMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame2AutoRoute.bind('<Leave>', self.on_leave)

        # Tab 2 RAB Setting Frame
        tab2FrameRAB = tk.LabelFrame(self.tab2, text=self.lang[self.gui_lang]['tab2FrameRAB'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab2FrameRAB.grid(row=1, columnspan=4, sticky='W')
        tab2FrameRAB.columnconfigure([0, 1, 2, 3], minsize=200)
        tab2FrameRAB.rowconfigure([0, 1, 2], minsize=25)

        # Pokestop Priority
        self.boolPokestopPriority = IntVar()
        self.boolPokestopPriority.set(self.config.get('spin_pokestop', 0))
        if self.config['client']['client'] != 'Polygon Paid':
            self.tab2Frame2PokestopPriority = tk.Checkbutton(tab2FrameRAB, variable=self.boolPokestopPriority, command=self.pokestopPriority_checkbox,
                                                             text=self.lang[self.gui_lang]['tab2Frame2PokestopPriority'].replace('\\n', '\n').replace('\\t', '\t'))
        else:
            self.tab2Frame2PokestopPriority = tk.Checkbutton(tab2FrameRAB, variable=self.boolPokestopPriority, command=self.pokestopPriority_checkbox,
                                                             text=self.lang[self.gui_lang]['tab2Frame2PokestopPriority'].replace('\\n', '\n').replace('\\t', '\t'), state=tk.DISABLED)
        self.tab2Frame2PokestopPriority.grid(row=0, column=0, columnspan=2, sticky="W")
        self.tab2Frame2PokestopPriority.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2PokestopPriorityMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame2PokestopPriority.bind('<Leave>', self.on_leave)

        # Auto Go Plus Reconnect
        self.boolAutoGoplus = IntVar()
        self.boolAutoGoplus.set(self.config['client'].get('auto_goplus', 0))
        tab2Frame1AutoGoplus = tk.Checkbutton(tab2FrameRAB, variable=self.boolAutoGoplus, command=self.autoGoplus_checkbox,
                                              text=self.lang[self.gui_lang]['tab2Frame1AutoGoplus'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame1AutoGoplus.grid(row=0, column=1, sticky="W")
        tab2Frame1AutoGoplus.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame1AutoGoplusMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame1AutoGoplus.bind('<Leave>', self.on_leave)

        # Slot Gym
        self.boolAutoSlotGym = IntVar()
        self.boolAutoSlotGym.set(self.config['client'].get('auto_slot', 0))
        if self.config['client']['client'] != 'Polygon Paid':
            self.tab2Frame2AutoSlotGym = tk.Checkbutton(tab2FrameRAB, variable=self.boolAutoSlotGym, command=self.autoSlotGym_checkbox,
                                                        text=self.lang[self.gui_lang]['tab2Frame2AutoSlotGym'].replace('\\n', '\n').replace('\\t', '\t'), state=tk.DISABLED)
        else:
            self.tab2Frame2AutoSlotGym = tk.Checkbutton(tab2FrameRAB, variable=self.boolAutoSlotGym, command=self.autoSlotGym_checkbox,
                                                        text=self.lang[self.gui_lang]['tab2Frame2AutoSlotGym'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame2AutoSlotGym.grid(row=0, column=2, sticky="W")
        self.tab2Frame2AutoSlotGym.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2AutoSlotGymMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame2AutoSlotGym.bind('<Leave>', self.on_leave)

        # Berry Check Method
        self.boolAdvanceBerryCheck = IntVar()
        self.boolAdvanceBerryCheck.set(self.config['client'].get('advance_berry_check', 0))
        tab2Frame2AdvanceBerryCheck = tk.Checkbutton(tab2FrameRAB, variable=self.boolAdvanceBerryCheck, command=self.advanceBerryCheck_checkbox,
                                                     text=self.lang[self.gui_lang]['tab2Frame2AdvanceBerryCheck'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2AdvanceBerryCheck.grid(row=0, column=3, sticky="W")
        tab2Frame2AdvanceBerryCheck.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2AdvanceBerryCheckMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2AdvanceBerryCheck.bind('<Leave>', self.on_leave)

        # Zooming Out Method
        tempF2ZoomOutMethod = tk.Frame(tab2FrameRAB)
        tempF2ZoomOutMethod.grid(row=1, column=0, columnspan=2, sticky="NSEW")

        self.ZoomOutVar = StringVar()
        ZoomOutMethodChoices = ['Pinch In', 'Pinch Out']
        tab2Frame2ZoomOutMethod = tk.Label(
            tempF2ZoomOutMethod, text=self.lang[self.gui_lang]['tab2Frame2ZoomOutMethod'].replace('\\n', '\n').replace('\\t', '\t'))
        #tab2Frame1Label1.grid(row=0, column=0, sticky="E")

        tab2Frame2ZoomOutMethodDropDown = ttk.OptionMenu(tempF2ZoomOutMethod, self.ZoomOutVar, self.config['client'].get(
            'zoom_option', 'Pinch In'), *ZoomOutMethodChoices, command=self.zoomMethod_dropdown)
        tab2Frame2ZoomOutMethod.pack(side=tk.LEFT)
        tab2Frame2ZoomOutMethodDropDown.pack(side=tk.LEFT)
        #tab2Frame1Options.grid(row=0, column=1,sticky="EW")
        tab2Frame2ZoomOutMethodDropDown.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2ZoomOutMethodMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2ZoomOutMethodDropDown.bind('<Leave>', self.on_leave)

        # PGSharp Shuno hunting
        self.boolPGSharpShuno = IntVar()
        self.boolPGSharpShuno.set(self.config['client'].get('pgsharp_shuno_hunt', 0))
        self.tab2Frame2PGSharpShunoHunt = tk.Checkbutton(tab2FrameRAB, variable=self.boolPGSharpShuno, command=self.pgsharpShuno_checkbox,
                                                         text=self.lang[self.gui_lang]['tab2Frame2PGSharpShunoHunt'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame2PGSharpShunoHunt.grid(row=1, column=2, sticky="W")
        self.tab2Frame2PGSharpShunoHunt.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2PGSharpShunoHuntMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame2PGSharpShunoHunt.bind('<Leave>', self.on_leave)

        # Disable Auto Restart
        self.boolDisableAutoRestart = IntVar()
        self.boolDisableAutoRestart.set(self.config['client'].get('disable_auto_restart', 0))
        tab2Frame2DisableAutoRestart = tk.Checkbutton(tab2FrameRAB, variable=self.boolDisableAutoRestart, command=self.disableAutoRestart_checkbox,
                                                      text=self.lang[self.gui_lang]['tab2Frame2DisableAutoRestart'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2DisableAutoRestart.grid(row=1, column=3, sticky="W")
        tab2Frame2DisableAutoRestart.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2DisableAutoRestartMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2DisableAutoRestart.bind('<Leave>', self.on_leave)

        # Host IP
        tab2Frame2HostLabel = tk.Label(
            tab2FrameRAB, text=self.lang[self.gui_lang]['tab2Frame2HostLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2HostLabel.grid(row=2, column=0, sticky="W")
        self.strHost = StringVar()
        self.strHost.set(self.config['network'].get('host', 0))
        if self.clientVar.get() == 'Polygon Paid':
            networkStatus = tk.NORMAL
        else:
            networkStatus = tk.DISABLED
        self.tab2Frame2Host = tk.Entry(tab2FrameRAB, textvariable=self.strHost, state=networkStatus)
        self.tab2Frame2Host.grid(row=3, column=0, sticky="W")
        self.tab2Frame2Host.bind('<KeyRelease>', self.Host_entry)
        self.tab2Frame2Host.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2HostMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame2Host.bind('<Leave>', self.on_leave)

        # Port
        tab2Frame2PortLabel = tk.Label(
            tab2FrameRAB, text=self.lang[self.gui_lang]['tab2Frame2PortLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2PortLabel.grid(row=2, column=1, sticky="W")
        self.strPort = StringVar()
        self.strPort.set(self.config['network'].get('port', 0))
        self.tab2Frame2Port = tk.Entry(tab2FrameRAB, textvariable=self.strPort, state=networkStatus)
        self.tab2Frame2Port.grid(row=3, column=1, sticky="W")
        self.tab2Frame2Port.bind('<KeyRelease>', self.Port_entry)
        self.tab2Frame2Port.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2PortMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame2Port.bind('<Leave>', self.on_leave)

        # Timedelay
        tab2Frame2DelayTimeLabel = tk.Label(
            tab2FrameRAB, text=self.lang[self.gui_lang]['tab2Frame2DelayTimeLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2DelayTimeLabel.grid(row=2, column=2, sticky="W")
        self.strDelayTime = StringVar()
        self.strDelayTime.set(self.config['client'].get('delay', 1.5))
        tab2Frame2DelayTime = tk.Entry(tab2FrameRAB, textvariable=self.strDelayTime)
        tab2Frame2DelayTime.grid(row=3, column=2, sticky="W")
        tab2Frame2DelayTime.bind('<KeyRelease>', self.delayTime_entry)
        tab2Frame2DelayTime.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2DelayTimeMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2DelayTime.bind('<Leave>', self.on_leave)

        # Shuno hunt auto catch
        self.boolShinyHuntAutoCatch = IntVar()
        self.boolShinyHuntAutoCatch.set(self.config['shiny_check'].get('auto_catch', 0))
        self.tab2Frame2ShinyAutoCatch = tk.Checkbutton(tab2FrameRAB, variable=self.boolShinyHuntAutoCatch, command=self.shinyHuntAutoCatch_checkbox,
                                                       text='Shiny Hunt ' + self.lang[self.gui_lang]['tab5Frame2ShinyAutoCatch'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab2Frame2ShinyAutoCatch.grid(row=2, column=3, sticky="W")
        self.tab2Frame2ShinyAutoCatch.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame2ShinyAutoCatchMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab2Frame2ShinyAutoCatch.bind('<Leave>', self.on_leave)

        # PGSharp Reposition
        self.boolPGSharpReposition = IntVar()
        self.boolPGSharpReposition.set(self.config['client'].get('pgsharp_reposition', 1))
        self.tab2Frame2PGSharpReposition = tk.Checkbutton(
            tab2FrameRAB, variable=self.boolPGSharpReposition, command=self.pgsharpReposition_checkbox, text='PGSharp Reposition')
        self.tab2Frame2PGSharpReposition.grid(row=3, column=3, sticky="W")
        self.tab2Frame2PGSharpReposition.bind('<Enter>', lambda event: self.on_enter(
            event, msg='RAB will auto shift PGSharp icons if this is enabled. Disable it to manually shift it yourself'))

        # Tab 2 Frame 2
        # Phone Settings
        tab2Frame2 = tk.LabelFrame(self.tab2, text=self.lang[self.gui_lang]['tab2Frame2'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab2Frame2.grid(row=2, columnspan=4, sticky='W')
        tab2Frame2.columnconfigure([0, 1, 2, 3], minsize=200)
        tab2Frame2.rowconfigure([0, 1, 2], minsize=25)

        # Manual Resolution
        self.boolManualResolution = IntVar()
        self.boolManualResolution.set(self.config['client'].get('manual_set_resolution', 0))
        tab2Frame2ManualResolution = tk.Checkbutton(tab2Frame2, variable=self.boolManualResolution, command=self.manualResolution_checkbox,
                                                    text=self.lang[self.gui_lang]['tab2Frame2ManualResolution'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2ManualResolution.grid(row=0, column=0, sticky="W")
        tab2Frame2ManualResolution.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2ManualResolutionMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2ManualResolution.bind('<Leave>', self.on_leave)

        # Auto Offset
        self.boolAutoOffset = IntVar()
        self.boolAutoOffset.set(self.config['client'].get('auto_offset', 0))
        tab2Frame2AutoOffset = tk.Checkbutton(tab2Frame2, variable=self.boolAutoOffset, command=self.autoOffset_checkbox,
                                              text=self.lang[self.gui_lang]['tab2Frame2AutoOffset'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2AutoOffset.grid(row=0, column=1, sticky="W")
        tab2Frame2AutoOffset.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2AutoOffsetMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2AutoOffset.bind('<Leave>', self.on_leave)

        # On Screen Offset
        self.intScreenOffset = IntVar()
        self.intScreenOffset.set(self.config['client'].get('screen_offset', 0))
        tab2Frame2ScreenOffset = tk.Scale(tab2Frame2, orient=tk.HORIZONTAL, variable=self.intScreenOffset, from_=-140, to=140, length=150,
                                          command=self.screenOffset_scale, label=self.lang[self.gui_lang]['tab2Frame2ScreenOffset'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2ScreenOffset.grid(row=1, column=0, sticky="W")
        tab2Frame2ScreenOffset.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2ScreenOffsetMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2ScreenOffset.bind('<Leave>', self.on_leave)

        # Navigation Offset
        self.intNavigationOffset = IntVar()
        self.intNavigationOffset.set(self.config['client'].get('navigation_offset', 0))
        tab2Frame2NavigationOffset = tk.Scale(tab2Frame2, orient=tk.HORIZONTAL, variable=self.intNavigationOffset, from_=0, to=200, length=150,
                                              command=self.navigationOffset_scale, label=self.lang[self.gui_lang]['tab2Frame2NavigationOffset'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2NavigationOffset.grid(row=1, column=1, sticky="W")
        tab2Frame2NavigationOffset.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2NavigationOffsetMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2NavigationOffset.bind('<Leave>', self.on_leave)

        # Screenshot Offset
        self.intScreenshotOffset = IntVar()
        self.intScreenshotOffset.set(self.config['client'].get('screenshot_shift', 0))
        tab2Frame2ScreenshotOffset = tk.Scale(tab2Frame2, orient=tk.HORIZONTAL, variable=self.intScreenshotOffset, from_=0, to=200, length=150,
                                              command=self.screenshotOffset_scale, label=self.lang[self.gui_lang]['tab2Frame2ScreenshotOffset'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2ScreenshotOffset.grid(row=1, column=2, sticky="W")
        tab2Frame2ScreenshotOffset.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2ScreenshotOffsetMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2ScreenshotOffset.bind('<Leave>', self.on_leave)

        # Resize to lower resolution
        self.boolLowerResolution = IntVar()
        self.boolLowerResolution.set(self.config['client'].get('lower_resolution', 0))
        tab2Frame2LowerResolution = tk.Checkbutton(tab2Frame2, variable=self.boolLowerResolution, command=self.lowerResolution_checkbox,
                                                   text=self.lang[self.gui_lang]['tab2Frame2LowerResolution'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2LowerResolution.grid(row=0, column=2, sticky="W")
        tab2Frame2LowerResolution.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2LowerResolutionMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2LowerResolution.bind('<Leave>', self.on_leave)

        # Density
        tab2Frame2DensityLabel = tk.Label(
            tab2Frame2, text=self.lang[self.gui_lang]['tab2Frame2Density'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2DensityLabel.grid(row=0, column=3, sticky="W")
        self.strDensity = StringVar()
        self.strDensity.set(self.config['client'].get('dpi', 0))
        tab2Frame2Density = tk.Entry(tab2Frame2, textvariable=self.strDensity)
        tab2Frame2Density.grid(row=1, column=3, sticky="NW")
        tab2Frame2Density.bind('<KeyRelease>', self.density_entry)
        tab2Frame2Density.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2DensityMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2Density.bind('<Leave>', self.on_leave)

        # Dim Phone Screen
        self.boolDimPhone = IntVar()
        self.boolDimPhone.set(self.config['client'].get('dim_phone', 1))
        tab2Frame2DimPhone = tk.Checkbutton(tab2Frame2, variable=self.boolDimPhone, command=self.dimPhone_checkbox,
                                            text=self.lang[self.gui_lang]['tab2Frame2DimPhone'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame2DimPhone.grid(row=2, column=0, sticky="W")
        tab2Frame2DimPhone.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame2DimPhoneMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame2DimPhone.bind('<Leave>', self.on_leave)

        # Tab 2 Frame 3
        # Discord Notifications
        tab2Frame3 = tk.LabelFrame(self.tab2, text=self.lang[self.gui_lang]['tab2Frame3'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab2Frame3.grid(row=3, columnspan=4, sticky='W')
        tab2Frame3.columnconfigure([0, 1, 2, 3], minsize=200)
        tab2Frame3.rowconfigure([0, 1, 2], minsize=25)

        # Enabled
        self.boolDiscordEnabled = IntVar()
        self.boolDiscordEnabled.set(self.config['discord'].get('enabled', 0))
        tab2Frame3DiscordEnabled = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordEnabled, command=self.discordEnabled_checkbox,
                                                  text=self.lang[self.gui_lang]['tab2Frame3DiscordEnabled'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordEnabled.grid(row=0, column=0, sticky="W")
        tab2Frame3DiscordEnabled.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordEnabledMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordEnabled.bind('<Leave>', self.on_leave)

        # Webhook Address
        tempWebhook = tk.Frame(tab2Frame3)
        tempWebhook.grid(row=0, column=1, columnspan=3, sticky="NSEW")
        tab2Frame3WebhookLabel = tk.Label(
            tempWebhook, text=self.lang[self.gui_lang]['tab2Frame3WebhookLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        #tab2Frame3WebhookLabel.grid(row=0, column=1, sticky="E")
        self.strWebhookAddress = StringVar()
        self.strWebhookAddress.set(self.config['discord'].get('webhook_url', 0))
        tab2Frame3WebhookAddress = tk.Entry(tempWebhook, textvariable=self.strWebhookAddress)
        #tab2Frame3WebhookAddress.grid(row=0, column=2,columnspan=2, sticky="WE")
        tab2Frame3WebhookAddress.bind('<KeyRelease>', self.webhookAddress_entry)
        tab2Frame3WebhookLabel.pack(side=tk.LEFT)
        tab2Frame3WebhookAddress.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        tab2Frame3WebhookAddress.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3WebhookAddressMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3WebhookAddress.bind('<Leave>', self.on_leave)

        # Notify All Caught
        self.boolDiscordAll = IntVar()
        self.boolDiscordAll.set(self.config['discord'].get('notify_all_caught', 0))
        tab2Frame3DiscordAll = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordAll, command=self.manualDiscordAll_checkbox,
                                              text=self.lang[self.gui_lang]['tab2Frame3DiscordAll'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordAll.grid(row=1, column=0, sticky="W")
        tab2Frame3DiscordAll.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordAllMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordAll.bind('<Leave>', self.on_leave)

        # Notify All Caught
        self.boolDiscordAllEncountered = IntVar()
        self.boolDiscordAllEncountered.set(self.config['discord'].get('notify_all_encountered', 0))
        tab2Frame3DiscordAllEncountered = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordAllEncountered, command=self.manualDiscordAllEncountered_checkbox,
                                                         text=self.lang[self.gui_lang]['tab2Frame3DiscordAllEncountered'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordAllEncountered.grid(row=1, column=1, sticky="W")
        tab2Frame3DiscordAllEncountered.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordAllEncounteredMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordAllEncountered.bind('<Leave>', self.on_leave)

        # Notify Encountered
        self.boolDiscordEncountered = IntVar()
        self.boolDiscordEncountered.set(self.config['discord'].get('notify_encountered', 0))
        tab2Frame3DiscordEncountered = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordEncountered, command=self.manualDiscordEncountered_checkbox,
                                                      text=self.lang[self.gui_lang]['tab2Frame3DiscordEncountered'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordEncountered.grid(row=1, column=2, sticky="W")
        tab2Frame3DiscordEncountered.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordEncounteredMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordEncountered.bind('<Leave>', self.on_leave)

        # Notify CaughtOrFled
        self.boolDiscordCaughtOrFled = IntVar()
        self.boolDiscordCaughtOrFled.set(self.config['discord'].get('notify_caught_fled', 0))
        tab2Frame3DiscordCaughtOrFled = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordCaughtOrFled, command=self.manualDiscordCaughtOrFled_checkbox,
                                                       text=self.lang[self.gui_lang]['tab2Frame3DiscordCaughtOrFled'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordCaughtOrFled.grid(row=1, column=3, sticky="W")
        tab2Frame3DiscordCaughtOrFled.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordCaughtOrFledMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordCaughtOrFled.bind('<Leave>', self.on_leave)

        # Notify shiny
        self.boolDiscordShiny = IntVar()
        self.boolDiscordShiny.set(self.config['discord'].get('notify_shiny', 0))
        tab2Frame3DiscordShiny = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordShiny, command=self.manualDiscordShiny_checkbox,
                                                text=self.lang[self.gui_lang]['tab2Frame3DiscordShiny'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordShiny.grid(row=2, column=0, sticky="W")
        tab2Frame3DiscordShiny.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordShinyMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordShiny.bind('<Leave>', self.on_leave)

        # Notify 100IV
        self.boolDiscord100IV = IntVar()
        self.boolDiscord100IV.set(self.config['discord'].get('notify_max_iv', 0))
        tab2Frame3Discord100IV = tk.Checkbutton(tab2Frame3, variable=self.boolDiscord100IV, command=self.manualDiscord100IV_checkbox,
                                                text=self.lang[self.gui_lang]['tab2Frame3Discord100IV'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3Discord100IV.grid(row=2, column=1, sticky="W")
        tab2Frame3Discord100IV.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3Discord100IVMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3Discord100IV.bind('<Leave>', self.on_leave)

        # Notify PVP IV
        self.boolDiscordPVP = IntVar()
        self.boolDiscordPVP.set(self.config['discord'].get('notify_pvp_iv', 0))
        tab2Frame3DiscordPVPIV = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordPVP, command=self.manualDiscordPVP_checkbox,
                                                text=self.lang[self.gui_lang]['tab2Frame3DiscordPVPIV'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordPVPIV.grid(row=2, column=2, sticky="W")
        tab2Frame3DiscordPVPIV.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordPVPIVMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordPVPIV.bind('<Leave>', self.on_leave)

        # Notify Restart
        self.boolDiscordRestart = IntVar()
        self.boolDiscordRestart.set(self.config['discord'].get('restart', 0))
        tab2Frame3DiscordRestart = tk.Checkbutton(tab2Frame3, variable=self.boolDiscordRestart, command=self.manualDiscordRestart_checkbox,
                                                text=self.lang[self.gui_lang]['tab2Frame3DiscordRestart'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame3DiscordRestart.grid(row=2, column=2, sticky="W")
        tab2Frame3DiscordRestart.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame3DiscordRestartMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame3DiscordRestart.bind('<Leave>', self.on_leave)

        # Frame 4
        # Quest Settings
        tab2Frame4 = tk.LabelFrame(self.tab2, text=self.lang[self.gui_lang]['tab2Frame4'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab2Frame4.grid(row=4, columnspan=4, sticky='W')
        tab2Frame4.columnconfigure([0, 1, 2, 3], minsize=200)
        tab2Frame4.rowconfigure([0, 1], minsize=25)

        # Enabled
        self.boolQuestEnabled = IntVar()
        self.boolQuestEnabled.set(self.config['quest'].get('enable_check_quest', 0))
        tab2Frame4QuestEnabled = tk.Checkbutton(tab2Frame4, variable=self.boolQuestEnabled, command=self.questEnabled_checkbox,
                                                text=self.lang[self.gui_lang]['tab2Frame4QuestEnabled'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame4QuestEnabled.grid(row=0, column=0, sticky="W")
        tab2Frame4QuestEnabled.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame4QuestEnabledMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame4QuestEnabled.bind('<Leave>', self.on_leave)

        # Powerup Level
        self.intPowerUp = IntVar()
        self.intPowerUp.set(self.config['quest'].get('power_up_lvl', 0))
        tab2Frame4PowerUpScale = tk.Scale(tab2Frame4, orient=tk.HORIZONTAL, variable=self.intPowerUp, from_=0, to=50, length=150,
                                          command=self.powerUp_scale, label=self.lang[self.gui_lang]['tab2Frame4PowerUpScale'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame4PowerUpScale.grid(row=1, column=0, sticky="W")
        tab2Frame4PowerUpScale.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame4PowerUpScaleMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame4PowerUpScale.bind('<Leave>', self.on_leave)

        # Clear Quest Interval
        self.intClearQuest = IntVar()
        self.intClearQuest.set(self.config['quest'].get('clear_quest_interval', 0))
        tab2Frame4ClearQuestScale = tk.Scale(tab2Frame4, orient=tk.HORIZONTAL, variable=self.intClearQuest, from_=0, to=120, length=150,
                                             command=self.clearQuest_scale, label=self.lang[self.gui_lang]['tab2Frame4ClearQuestScale'].replace('\\n', '\n').replace('\\t', '\t'))
        tab2Frame4ClearQuestScale.grid(row=1, column=1, sticky="W")
        tab2Frame4ClearQuestScale.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2Frame4ClearQuestScaleMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2Frame4ClearQuestScale.bind('<Leave>', self.on_leave)

        # last_quest_quit_today
        tmpFrameF4 = tk.Frame(tab2Frame4)
        tmpFrameF4.grid(row=1, column=2, sticky="W")
        labQuitToday = tk.Label(tmpFrameF4, text=self.lang[self.gui_lang]['labQuitToday'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, wraplength=200)
        labQuitToday.pack(side=tk.TOP, anchor=tk.W)

        self.strQuestToday = StringVar()
        self.strQuestToday.set(self.config['quest'].get('last_quest_quit_today', 0))
        tab2QuestTodayEntry = tk.Entry(tmpFrameF4, textvariable=self.strQuestToday)
        tab2QuestTodayEntry.bind('<KeyRelease>', self.QuestToday_entry)
        tab2QuestTodayEntry.pack(side=tk.TOP)
        tab2QuestTodayEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2QuestTodayEntryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2QuestTodayEntry.bind('<Leave>', self.on_leave)

        # last_quest_quit
        tmpFrameF4_2 = tk.Frame(tab2Frame4)
        tmpFrameF4_2.grid(row=1, column=3, sticky="W")
        labQuitSpecial = tk.Label(tmpFrameF4_2, text='Trigger Quit Text\n(Special Quest):', justify=tk.LEFT, wraplength=200)
        labQuitSpecial.pack(side=tk.TOP, anchor=tk.W)

        self.strQuestSpecial = StringVar()
        self.strQuestSpecial.set(self.config['quest'].get('last_quest_quit', 0))
        tab2QuestSpecialEntry = tk.Entry(tmpFrameF4_2, textvariable=self.strQuestSpecial)
        tab2QuestSpecialEntry.bind('<KeyRelease>', self.QuestSpecial_entry)
        tab2QuestSpecialEntry.pack(side=tk.TOP)
        tab2QuestSpecialEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab2QuestSpecialEntryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab2QuestSpecialEntry.bind('<Leave>', self.on_leave)

        but_save = tk.Button(self.tab2, text=self.lang[self.gui_lang]['but_save'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.save_config)
        but_save.grid(row=5, column=1)
        but_close = tk.Button(self.tab2, text=self.lang[self.gui_lang]['but_close'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.close_win)
        but_close.grid(row=5, column=2)
        butStartRAB = tk.Button(self.tab2, text=self.lang[self.gui_lang]['tab1text6'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.start_rab)
        butStartRAB.grid(row=5, column=3)
        # but_close.pack()

    def constructTab3(self):

        # Tab 3 Configurations
        tab3Frame1 = tk.LabelFrame(self.tab3, text=self.lang[self.gui_lang]['tab3Frame1'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab3Frame1.grid(row=0, columnspan=4, sticky='W')
        tab3Frame1.columnconfigure([0, 1, 2, 3], minsize=200)
        tab3Frame1.rowconfigure([0, 1, 2, 3, 4, 5, 6, 7, 8, 9], minsize=25)

        # Enable keep monster base on settings?
        self.boolKeepMon = IntVar()
        self.boolKeepMon.set(self.config['catch'].get('enable_keep_mon', 0))
        tab3Frame1KeepMon = tk.Checkbutton(tab3Frame1, variable=self.boolKeepMon, command=self.keepMon_checkbox,
                                           text=self.lang[self.gui_lang]['tab3Frame1KeepMon'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1KeepMon.grid(row=0, column=0, sticky="W")
        tab3Frame1KeepMon.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1KeepMonMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1KeepMon.bind('<Leave>', self.on_leave)

        self.boolUseOr = IntVar()
        self.boolUseOr.set(self.config['catch'].get('or_condition', 0))
        tab3Frame1OrCondition = tk.Checkbutton(tab3Frame1, variable=self.boolUseOr, command=self.useOr_checkbox,
                                               text=self.lang[self.gui_lang]['tab3Frame1OrCondition'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1OrCondition.grid(row=0, column=3, sticky="W")
        tab3Frame1OrCondition.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1OrConditionMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1OrCondition.bind('<Leave>', self.on_leave)

        # On Screen Offset
        self.intMinAtk = IntVar()
        self.intMinAtk.set(self.config['catch'].get('min_atk', 15))
        tab3Frame1MinAtk = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.intMinAtk, from_=0, to=15, length=150,
                                    command=self.minAtk_scale, label=self.lang[self.gui_lang]['tab3Frame1MinAtk'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1MinAtk.grid(row=1, column=0, sticky="W")
        tab3Frame1MinAtk.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1MinAtkMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1MinAtk.bind('<Leave>', self.on_leave)

        self.intMinDef = IntVar()
        self.intMinDef.set(self.config['catch'].get('min_def', 15))
        tab3Frame1MinDef = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.intMinDef, from_=0, to=15, length=150,
                                    command=self.minDef_scale, label=self.lang[self.gui_lang]['tab3Frame1MinDef'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1MinDef.grid(row=1, column=1, sticky="W")
        tab3Frame1MinDef.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1MinDefMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1MinDef.bind('<Leave>', self.on_leave)

        self.intMinSta = IntVar()
        self.intMinSta.set(self.config['catch'].get('min_sta', 15))
        tab3Frame1MinSta = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.intMinSta, from_=0, to=15, length=150,
                                    command=self.minSta_scale, label=self.lang[self.gui_lang]['tab3Frame1MinSta'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1MinSta.grid(row=1, column=2, sticky="W")
        tab3Frame1MinSta.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1MinStaMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1MinSta.bind('<Leave>', self.on_leave)

        self.intMinLvl = IntVar()
        self.intMinLvl.set(self.config['catch'].get('min_lvl', 1))
        tab3Frame1MinLvl = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.intMinLvl, from_=0, to=35, length=150,
                                    command=self.minLvl_scale, label=self.lang[self.gui_lang]['tab3Frame1MinLvl'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1MinLvl.grid(row=1, column=3, sticky="W")
        tab3Frame1MinLvl.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1MinLvlMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1MinLvl.bind('<Leave>', self.on_leave)

        # Enable keep monster base on settings?
        self.boolKeepShiny = IntVar()
        self.boolKeepShiny.set(self.config['catch'].get('enable_keep_shiny', 0))
        tab3Frame1KeepShiny = tk.Checkbutton(tab3Frame1, variable=self.boolKeepShiny, command=self.keepShiny_checkbox,
                                             text=self.lang[self.gui_lang]['tab3Frame1KeepShiny'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1KeepShiny.grid(row=2, column=0, sticky="W")
        tab3Frame1KeepShiny.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1KeepShinyMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1KeepShiny.bind('<Leave>', self.on_leave)

        self.boolKeepStrongShadow = IntVar()
        self.boolKeepStrongShadow.set(self.config['catch'].get('keep_strong_shadow', 0))
        tab3Frame1KeepStrongShadow = tk.Checkbutton(tab3Frame1, variable=self.boolKeepStrongShadow, command=self.keepStrongShadow_checkbox,
                                                    text=self.lang[self.gui_lang]['tab3Frame1KeepStrongShadow'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1KeepStrongShadow.grid(row=2, column=1, sticky="W")
        tab3Frame1KeepStrongShadow.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1KeepStrongShadowMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1KeepStrongShadow.bind('<Leave>', self.on_leave)

        self.boolKeepLegendary = IntVar()
        self.boolKeepLegendary.set(self.config['catch'].get('keep_legendary', 0))
        tab3Frame1KeepLegendary = tk.Checkbutton(tab3Frame1, variable=self.boolKeepLegendary, command=self.keepLegendary_checkbox,
                                                 text=self.lang[self.gui_lang]['tab3Frame1KeepLegendary'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1KeepLegendary.grid(row=2, column=2, sticky="W")
        tab3Frame1KeepLegendary.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1KeepLegendaryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1KeepLegendary.bind('<Leave>', self.on_leave)

        self.boolKeepLucky = IntVar()
        self.boolKeepLucky.set(self.config['catch'].get('keep_lucky', 0))
        tab3Frame1KeepLucky = tk.Checkbutton(tab3Frame1, variable=self.boolKeepLucky, command=self.keepLucky_checkbox,
                                             text=self.lang[self.gui_lang]['tab3Frame1KeepLucky'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1KeepLucky.grid(row=2, column=3, sticky="W")
        tab3Frame1KeepLucky.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1KeepLuckyMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1KeepLucky.bind('<Leave>', self.on_leave)

        self.boolKeepEvent = IntVar()
        self.boolKeepEvent.set(self.config['catch'].get('keep_event', 0))
        tab3Frame1KeepEvent = tk.Checkbutton(tab3Frame1, variable=self.boolKeepEvent, command=self.keepEvent_checkbox,
                                             text=self.lang[self.gui_lang]['tab3Frame1KeepEvent'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1KeepEvent.grid(row=3, column=0, sticky="W")
        tab3Frame1KeepEvent.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1KeepEventMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1KeepEvent.bind('<Leave>', self.on_leave)

        self.boolShinyTap = IntVar()
        self.boolShinyTap.set(self.config['catch'].get('only_shiny', 0))
        tab3Frame1ShinyTap = tk.Checkbutton(tab3Frame1, variable=self.boolShinyTap, command=self.shinyTap_checkbox,
                                            text=self.lang[self.gui_lang]['tab3Frame1ShinyTap'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1ShinyTap.grid(row=4, column=0, sticky="W")
        tab3Frame1ShinyTap.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1ShinyTapMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1ShinyTap.bind('<Leave>', self.on_leave)

        self.dblAppraisalDelay = DoubleVar()
        self.dblAppraisalDelay.set(self.config['catch'].get('delay_before_appraisal', 1.0))
        tab3Frame1AppraisalDelay = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.dblAppraisalDelay, from_=0.0, to=5.0, resolution=0.1, length=150,
                                            command=self.appraisalDelay_scale, label=self.lang[self.gui_lang]['tab3Frame1AppraisalDelay'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame1AppraisalDelay.grid(row=4, column=1, sticky="W")
        tab3Frame1AppraisalDelay.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1AppraisalDelay'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame1AppraisalDelay.bind('<Leave>', self.on_leave)

        tempHighFarPokemon = tk.Frame(tab3Frame1)
        tempHighFarPokemon.grid(row=5, column=1, columnspan=3, sticky="NSEW")
        tab3Frame1HighFarPokemonLabel = tk.Label(
            tab3Frame1, text=self.lang[self.gui_lang]['tab3Frame1HighFarPokemonLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['catch'].get('high_far_pokemon', []))
        self.txtHighFarPokemon = tk.Text(tempHighFarPokemon, height='5')
        self.txtHighFarPokemon.insert(tk.INSERT, convertedText)
        self.txtHighFarPokemon.bind('<KeyRelease>', self.highFarPokemon_entry)
        self.txtHighFarPokemon.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtHighFarPokemonMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtHighFarPokemon.bind('<Leave>', self.on_leave)
        tab3Frame1HighFarPokemonLabel.grid(row=5, column=0, sticky="W")
        self.txtHighFarPokemon.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        tempMon2Keep = tk.Frame(tab3Frame1)
        tempMon2Keep.grid(row=6, column=1, columnspan=3, sticky="NSEW")
        tab3Frame1Mon2Keep = tk.Label(
            tab3Frame1, text=self.lang[self.gui_lang]['tab3Frame1Mon2Keep'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['catch'].get('mon_to_keep', []))
        self.txtMon2Keep = tk.Text(tempMon2Keep, height='2')
        self.txtMon2Keep.insert(tk.INSERT, convertedText)
        self.txtMon2Keep.bind('<KeyRelease>', self.mon2Keep_entry)
        self.txtMon2Keep.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtMon2KeepMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtMon2Keep.bind('<Leave>', self.on_leave)
        tab3Frame1Mon2Keep.grid(row=6, column=0, sticky="W")
        self.txtMon2Keep.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        tempShadow2Keep = tk.Frame(tab3Frame1)
        tempShadow2Keep.grid(row=7, column=1, columnspan=3, sticky="NSEW")
        tab3Frame1Shadow2Keep = tk.Label(
            tab3Frame1, text=self.lang[self.gui_lang]['tab3Frame1Shadow2Keep'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['catch'].get('shadow_mon_to_keep', []))
        self.txtShadow2Keep = tk.Text(tempShadow2Keep, height='2')
        self.txtShadow2Keep.insert(tk.INSERT, convertedText)
        self.txtShadow2Keep.bind('<KeyRelease>', self.shadow2Keep_entry)
        self.txtShadow2Keep.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtShadow2KeepMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtShadow2Keep.bind('<Leave>', self.on_leave)
        tab3Frame1Shadow2Keep.grid(row=7, column=0, sticky="W")
        self.txtShadow2Keep.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        # txtPoke2Chase

        if self.config['client']['client'] != 'Polygon Paid':
            state = tk.DISABLED
        else:
            state = tk.NORMAL

        tempPoke2Chase = tk.Frame(tab3Frame1)
        tempPoke2Chase.grid(row=8, column=1, columnspan=3, sticky="NSEW")
        tab3Frame1Poke2Chase = tk.Label(
            tab3Frame1, text=self.lang[self.gui_lang]['tab3Frame1Poke2Chase'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['catch'].get('mon_to_chase', []))
        self.txtPoke2Chase = tk.Text(tempPoke2Chase, height='2', state=state)
        self.txtPoke2Chase.insert(tk.INSERT, convertedText)
        self.txtPoke2Chase.bind('<KeyRelease>', self.poke2Chase_entry)
        self.txtPoke2Chase.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1Poke2ChaseMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtPoke2Chase.bind('<Leave>', self.on_leave)
        tab3Frame1Poke2Chase.grid(row=8, column=0, sticky="W")
        self.txtPoke2Chase.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        self.intStopAtBall = IntVar()
        self.intStopAtBall.set(self.config['catch'].get('stop_at_ball', 100))
        self.tab3Frame1StopAtBall = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.intStopAtBall, from_=0, to=100, resolution=5, length=150,
                                             command=self.stopAtBall_scale, label=self.lang[self.gui_lang]['tab3Frame1StopAtBall'].replace('\\n', '\n').replace('\\t', '\t'), state=state)
        self.tab3Frame1StopAtBall.grid(row=9, column=0, sticky="W")
        self.tab3Frame1StopAtBall.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1StopAtBallMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab3Frame1StopAtBall.bind('<Leave>', self.on_leave)

        self.intResumeAtBall = IntVar()
        self.intResumeAtBall.set(self.config['catch'].get('resume_at_ball', 100))
        self.tab3Frame1ResumeAtBall = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.intResumeAtBall, from_=0, to=300, resolution=10, length=150,
                                               command=self.resumeAtBall_scale, label=self.lang[self.gui_lang]['tab3Frame1ResumeAtBall'].replace('\\n', '\n').replace('\\t', '\t'), state=state)
        self.tab3Frame1ResumeAtBall.grid(row=9, column=1, sticky="W")
        self.tab3Frame1ResumeAtBall.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1ResumeAtBallMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab3Frame1ResumeAtBall.bind('<Leave>', self.on_leave)

        self.intCatchEveryXSpin = IntVar()
        self.intCatchEveryXSpin.set(self.config['catch'].get('catchpoke_every_x_spin', 100))
        self.tab3Frame1CatchEveryXSpin = tk.Scale(tab3Frame1, orient=tk.HORIZONTAL, variable=self.intCatchEveryXSpin, from_=0, to=20, resolution=1, length=150,
                                                  command=self.catchEveryXSpin_scale, label=self.lang[self.gui_lang]['tab3Frame1CatchEveryXSpin'].replace('\\n', '\n').replace('\\t', '\t'), state=state)
        self.tab3Frame1CatchEveryXSpin.grid(row=9, column=2, sticky="W")
        self.tab3Frame1CatchEveryXSpin.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1CatchEveryXSpinMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab3Frame1CatchEveryXSpin.bind('<Leave>', self.on_leave)

        self.boolGoAfterShiny = IntVar()
        self.boolGoAfterShiny.set(self.config['catch'].get('go_after_shiny', 0))
        self.tab3Frame1GoAfterShiny = tk.Checkbutton(tab3Frame1, variable=self.boolGoAfterShiny, command=self.goAfterShiny_checkbox,
                                                     text=self.lang[self.gui_lang]['tab3Frame1GoAfterShiny'].replace('\\n', '\n').replace('\\t', '\t'), state=state)
        self.tab3Frame1GoAfterShiny.grid(row=10, column=0, sticky="W")
        self.tab3Frame1GoAfterShiny.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1GoAfterShinyMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab3Frame1GoAfterShiny.bind('<Leave>', self.on_leave)

        self.boolGoAfterMaxIV = IntVar()
        self.boolGoAfterMaxIV.set(self.config['catch'].get('go_after_100IV', 0))
        self.tab3Frame1GoAfterMaxIV = tk.Checkbutton(tab3Frame1, variable=self.boolGoAfterMaxIV, command=self.goAfterMaxIV_checkbox,
                                                     text=self.lang[self.gui_lang]['tab3Frame1GoAfterMaxIV'].replace('\\n', '\n').replace('\\t', '\t'), state=state)
        self.tab3Frame1GoAfterMaxIV.grid(row=10, column=1, sticky="W")
        self.tab3Frame1GoAfterMaxIV.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1GoAfterMaxIVMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab3Frame1GoAfterMaxIV.bind('<Leave>', self.on_leave)

        self.boolShinyMode = IntVar()
        self.boolShinyMode.set(self.config['catch'].get('shiny_mode', 0))
        self.tab3Frame1ShinyMode = tk.Checkbutton(tab3Frame1, variable=self.boolShinyMode, command=self.shinyMode_checkbox,
                                                  text=self.lang[self.gui_lang]['tab3Frame1ShinyMode'].replace('\\n', '\n').replace('\\t', '\t'), state=state)
        self.tab3Frame1ShinyMode.grid(row=10, column=2, sticky="W")
        self.tab3Frame1ShinyMode.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame1ShinyModeMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab3Frame1ShinyMode.bind('<Leave>', self.on_leave)

        # Enable Use Berry?
        tab3Frame2 = tk.LabelFrame(self.tab3, text=self.lang[self.gui_lang]['tab3Frame2'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab3Frame2.grid(row=1, columnspan=4, sticky='W')
        tab3Frame2.columnconfigure([0, 1, 2, 3], minsize=200)
        tab3Frame2.rowconfigure([0, 1, 2, 3], minsize=25)

        self.boolUseBerry = IntVar()
        self.boolUseBerry.set(self.config['berry_selection'].get('use_berry', 0))
        tab3Frame2UseBerry = tk.Checkbutton(tab3Frame2, variable=self.boolUseBerry, command=self.useBerry_checkbox,
                                            text=self.lang[self.gui_lang]['tab3Frame2UseBerry'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame2UseBerry.grid(row=0, column=0, sticky="W")
        tab3Frame2UseBerry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame2UseBerryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame2UseBerry.bind('<Leave>', self.on_leave)

        tempBerryP1 = tk.Frame(tab3Frame2)
        tempBerryP1.grid(row=0, column=1, columnspan=3, sticky="NSEW")
        tab3Frame2BerryP1 = tk.Label(tempBerryP1, text=self.lang[self.gui_lang]
                                     ['tab3Frame2BerryP1'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['berry_selection'].get('shiny_or_high_lvl', []))
        self.txtBerryP1 = tk.Text(tempBerryP1, height='1', width='50')
        self.txtBerryP1.insert(tk.INSERT, convertedText)
        self.txtBerryP1.bind('<KeyRelease>', self.berryP1_entry)
        self.txtBerryP1.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtBerryP1'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtBerryP1.bind('<Leave>', self.on_leave)
        tab3Frame2BerryP1.pack(side=tk.LEFT)
        self.txtBerryP1.pack(side=tk.LEFT)

        tempBerryP2 = tk.Frame(tab3Frame2)
        tempBerryP2.grid(row=1, column=1, columnspan=3, sticky="NSEW")
        tab3Frame2BerryP2 = tk.Label(tempBerryP2, text=self.lang[self.gui_lang]
                                     ['tab3Frame2BerryP2'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['berry_selection'].get('mid_lvl', []))
        self.txtBerryP2 = tk.Text(tempBerryP2, height='1', width='50')
        self.txtBerryP2.insert(tk.INSERT, convertedText)
        self.txtBerryP2.bind('<KeyRelease>', self.berryP2_entry)
        self.txtBerryP2.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtBerryP2'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtBerryP2.bind('<Leave>', self.on_leave)
        tab3Frame2BerryP2.pack(side=tk.LEFT)
        self.txtBerryP2.pack(side=tk.LEFT)

        tempBerryP3 = tk.Frame(tab3Frame2)
        tempBerryP3.grid(row=2, column=1, columnspan=3, sticky="NSEW")
        tab3Frame2BerryP3 = tk.Label(tempBerryP3, text=self.lang[self.gui_lang]
                                     ['tab3Frame2BerryP3'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['berry_selection'].get('low_lvl_or_unknown', []))
        self.txtBerryP3 = tk.Text(tempBerryP3, height='1', width='50')
        self.txtBerryP3.insert(tk.INSERT, convertedText)
        self.txtBerryP3.bind('<KeyRelease>', self.berryP3_entry)
        self.txtBerryP3.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtBerryP3'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtBerryP3.bind('<Leave>', self.on_leave)
        tab3Frame2BerryP3.pack(side=tk.LEFT)
        self.txtBerryP3.pack(side=tk.LEFT)

        tempBerryPinapExclusive = tk.Frame(tab3Frame2)
        tempBerryPinapExclusive.grid(row=3, column=1, columnspan=3, sticky="NSEW")
        tab3Frame2PinapExclusive = tk.Label(
            tempBerryPinapExclusive, text=self.lang[self.gui_lang]['tab3Frame2PinapExclusive'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['berry_selection'].get('pinap_exclusive', []))
        self.txtPinapExclusive = tk.Text(tempBerryPinapExclusive, height='1', width='50')
        self.txtPinapExclusive.insert(tk.INSERT, convertedText)
        self.txtPinapExclusive.bind('<KeyRelease>', self.pinapExclusive_entry)
        self.txtPinapExclusive.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtPinapExclusive'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtPinapExclusive.bind('<Leave>', self.on_leave)
        tab3Frame2PinapExclusive.pack(side=tk.LEFT)
        self.txtPinapExclusive.pack(side=tk.LEFT)

        # Enable change pokeball?
        tab3Frame3 = tk.LabelFrame(self.tab3, text=self.lang[self.gui_lang]['tab3Frame3'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab3Frame3.grid(row=2, columnspan=4, sticky='W')
        tab3Frame3.columnconfigure([0, 1, 2, 3], minsize=200)
        tab3Frame3.rowconfigure([0, 1, 2], minsize=25)

        self.boolSelectBall = IntVar()
        self.boolSelectBall.set(self.config['ball_selection'].get('select_ball', 0))
        tab3Frame3SelectBall = tk.Checkbutton(tab3Frame3, variable=self.boolSelectBall, command=self.selectBall_checkbox,
                                              text=self.lang[self.gui_lang]['tab3Frame3SelectBall'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame3SelectBall.grid(row=0, column=0, sticky="W")
        tab3Frame3SelectBall.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame3SelectBallMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame3SelectBall.bind('<Leave>', self.on_leave)

        self.booltakeSnapshot = IntVar()
        self.booltakeSnapshot.set(self.config['ball_selection'].get('take_snapshot', 0))
        tab3Frame3takeSnapshot = tk.Checkbutton(tab3Frame3, variable=self.booltakeSnapshot, command=self.takeSnapshot_checkbox,
                                              text=self.lang[self.gui_lang]['tab3Frame3takeSnapshot'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame3takeSnapshot.grid(row=1, column=0, sticky="W")
        tab3Frame3takeSnapshot.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame3takeSnapshotMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame3takeSnapshot.bind('<Leave>', self.on_leave)

        tempSelectBallP1 = tk.Frame(tab3Frame3)
        tempSelectBallP1.grid(row=0, column=1, columnspan=3, sticky="NSEW")
        tab3Frame3SelectBallP1 = tk.Label(
            tempSelectBallP1, text=self.lang[self.gui_lang]['tab3Frame3SelectBallP1'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['ball_selection'].get('shiny_or_high_lvl', []))
        self.txtSelectBallP1 = tk.Text(tempSelectBallP1, height='1', width='50')
        self.txtSelectBallP1.insert(tk.INSERT, convertedText)
        self.txtSelectBallP1.bind('<KeyRelease>', self.selectBallP1_entry)
        self.txtSelectBallP1.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtSelectBallP1'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtSelectBallP1.bind('<Leave>', self.on_leave)
        tab3Frame3SelectBallP1.pack(side=tk.LEFT)
        self.txtSelectBallP1.pack(side=tk.LEFT)

        tempSelectBallP2 = tk.Frame(tab3Frame3)
        tempSelectBallP2.grid(row=1, column=1, columnspan=3, sticky="NSEW")
        tab3Frame3SelectBallP2 = tk.Label(
            tempSelectBallP2, text=self.lang[self.gui_lang]['tab3Frame3SelectBallP2'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['ball_selection'].get('mid_lvl', []))
        self.txtSelectBallP2 = tk.Text(tempSelectBallP2, height='1', width='50')
        self.txtSelectBallP2.insert(tk.INSERT, convertedText)
        self.txtSelectBallP2.bind('<KeyRelease>', self.selectBallP2_entry)
        self.txtSelectBallP2.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtSelectBallP2'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtSelectBallP2.bind('<Leave>', self.on_leave)
        tab3Frame3SelectBallP2.pack(side=tk.LEFT)
        self.txtSelectBallP2.pack(side=tk.LEFT)

        tempSelectBallP3 = tk.Frame(tab3Frame3)
        tempSelectBallP3.grid(row=2, column=1, columnspan=3, sticky="NSEW")
        tab3Frame3SelectBallP3 = tk.Label(
            tempSelectBallP3, text=self.lang[self.gui_lang]['tab3Frame3SelectBallP3'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['ball_selection'].get('low_lvl_or_unknown', []))
        self.txtSelectBallP3 = tk.Text(tempSelectBallP3, height='1', width='50')
        self.txtSelectBallP3.insert(tk.INSERT, convertedText)
        self.txtSelectBallP3.bind('<KeyRelease>', self.selectBallP3_entry)
        self.txtSelectBallP3.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtSelectBallP3'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtSelectBallP3.bind('<Leave>', self.on_leave)
        tab3Frame3SelectBallP3.pack(side=tk.LEFT)
        self.txtSelectBallP3.pack(side=tk.LEFT)

        # Enable Keep pvp?
        tab3Frame4 = tk.LabelFrame(self.tab3, text=self.lang[self.gui_lang]['tab3Frame4'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab3Frame4.grid(row=3, columnspan=4, sticky='W')
        tab3Frame4.columnconfigure([0, 1, 2, 3], minsize=200)
        tab3Frame4.rowconfigure([0, 1, 2], minsize=25)

        self.boolEnablePVP = IntVar()
        self.boolEnablePVP.set(self.config['pvp'].get('enable_keep_pvp', 0))
        tab3Frame4EnablePVP = tk.Checkbutton(tab3Frame4, variable=self.boolEnablePVP, command=self.enablePVP_checkbox,
                                             text=self.lang[self.gui_lang]['tab3Frame4EnablePVP'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame4EnablePVP.grid(row=0, column=0, sticky="W")
        tab3Frame4EnablePVP.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame4EnablePVPMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame4EnablePVP.bind('<Leave>', self.on_leave)

        tempGL2Keep = tk.Frame(tab3Frame4)
        tempGL2Keep.grid(row=1, column=0, columnspan=2, sticky="NSEW")
        tab3Frame4GL2Keep = tk.Label(tempGL2Keep, text=self.lang[self.gui_lang]
                                     ['tab3Frame4GL2Keep'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['pvp'].get('gl_to_keep', []))
        self.txtGL2Keep = tk.Text(tempGL2Keep, height='3', width='50')
        self.txtGL2Keep.insert(tk.INSERT, convertedText)
        self.txtGL2Keep.bind('<KeyRelease>', self.gl2Keep_entry)
        self.txtGL2Keep.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtGL2Keep'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtGL2Keep.bind('<Leave>', self.on_leave)
        tab3Frame4GL2Keep.pack(side=tk.TOP, anchor=tk.W)
        self.txtGL2Keep.pack(side=tk.LEFT)

        self.dblGLRating = DoubleVar()
        self.dblGLRating.set(self.config['pvp'].get('gl_rating', 99.0))
        tab3Frame4GLRating = tk.Scale(tab3Frame4, orient=tk.HORIZONTAL, variable=self.dblGLRating, from_=88.0, to=100.0, resolution=0.1, length=150,
                                      command=self.glRating_scale, label=self.lang[self.gui_lang]['tab3Frame4GLRating'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame4GLRating.grid(row=1, column=2, sticky="W")
        tab3Frame4GLRating.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame4GLRatingMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame4GLRating.bind('<Leave>', self.on_leave)

        self.intGLCP = IntVar()
        self.intGLCP.set(self.config['pvp'].get('gl_cp', 1400))
        tab3Frame4GLCP = tk.Scale(tab3Frame4, orient=tk.HORIZONTAL, variable=self.intGLCP, from_=1000, to=1500, resolution=10, length=150,
                                  command=self.glCP_scale, label=self.lang[self.gui_lang]['tab3Frame4GLCP'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame4GLCP.grid(row=1, column=3, sticky="W")
        tab3Frame4GLCP.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame4GLCPMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame4GLCP.bind('<Leave>', self.on_leave)

        tempUL2Keep = tk.Frame(tab3Frame4)
        tempUL2Keep.grid(row=2, column=0, columnspan=2, sticky="NSEW")
        tab3Frame4UL2Keep = tk.Label(tempUL2Keep, text=self.lang[self.gui_lang]
                                     ['tab3Frame4UL2Keep'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['pvp'].get('ul_to_keep', []))
        self.txtUL2Keep = tk.Text(tempUL2Keep, height='3', width='50')
        self.txtUL2Keep.insert(tk.INSERT, convertedText)
        self.txtUL2Keep.bind('<KeyRelease>', self.ul2Keep_entry)
        self.txtUL2Keep.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['txtUL2Keep'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtUL2Keep.bind('<Leave>', self.on_leave)
        tab3Frame4UL2Keep.pack(side=tk.TOP, anchor=tk.W)
        self.txtUL2Keep.pack(side=tk.LEFT)

        self.dblULRating = DoubleVar()
        self.dblULRating.set(self.config['pvp'].get('ul_rating', 99.0))
        tab3Frame4ULRating = tk.Scale(tab3Frame4, orient=tk.HORIZONTAL, variable=self.dblULRating, from_=88.0, to=100.0, resolution=0.1, length=150,
                                      command=self.ulRating_scale, label=self.lang[self.gui_lang]['tab3Frame4ULRating'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame4ULRating.grid(row=2, column=2, sticky="W")
        tab3Frame4ULRating.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame4ULRatingMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame4ULRating.bind('<Leave>', self.on_leave)

        self.intULCP = IntVar()
        self.intULCP.set(self.config['pvp'].get('ul_cp', 1400))
        tab3Frame4ULCP = tk.Scale(tab3Frame4, orient=tk.HORIZONTAL, variable=self.intULCP, from_=2000, to=2500, resolution=10, length=150,
                                  command=self.ulCP_scale, label=self.lang[self.gui_lang]['tab3Frame4ULCP'].replace('\\n', '\n').replace('\\t', '\t'))
        tab3Frame4ULCP.grid(row=2, column=3, sticky="W")
        tab3Frame4ULCP.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab3Frame4ULCPMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab3Frame4ULCP.bind('<Leave>', self.on_leave)

        but_save = tk.Button(self.tab3, text=self.lang[self.gui_lang]['but_save'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.save_config)
        but_save.grid(row=4, column=1)
        but_close = tk.Button(self.tab3, text=self.lang[self.gui_lang]['but_close'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.close_win)
        but_close.grid(row=4, column=2)
        butStartRAB = tk.Button(self.tab3, text=self.lang[self.gui_lang]['tab1text6'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.start_rab)
        butStartRAB.grid(row=4, column=3)

    def constructTab4(self):

        # Tab 4 Configurations
        tab4Frame1 = tk.LabelFrame(self.tab4, text=self.lang[self.gui_lang]['tab4Frame1'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab4Frame1.grid(row=0, columnspan=4, sticky='W')
        tab4Frame1.columnconfigure([0, 1, 2, 3], minsize=200)
        tab4Frame1.rowconfigure([0, 1], minsize=25)

        # Pokemon Management
        # Enable Pokemon Management
        self.boolEnablePokeManagement = IntVar()
        self.boolEnablePokeManagement.set(self.config['poke_management'].get('enable_poke_management', 0))
        tab4Frame1EnablePokeManagement = tk.Checkbutton(tab4Frame1, variable=self.boolEnablePokeManagement, command=self.enablePokeManagement_checkbox,
                                                        text=self.lang[self.gui_lang]['tab4Frame1EnablePokeManagement'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame1EnablePokeManagement.grid(row=0, column=0, sticky="W")
        tab4Frame1EnablePokeManagement.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame1EnablePokeManagementMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame1EnablePokeManagement.bind('<Leave>', self.on_leave)

        self.boolManageOnStart = IntVar()
        self.boolManageOnStart.set(self.config['poke_management'].get('manage_poke_on_start', 0))
        tab4Frame1ManageOnStart = tk.Checkbutton(tab4Frame1, variable=self.boolManageOnStart, command=self.manageOnStart_checkbox,
                                                 text=self.lang[self.gui_lang]['tab4Frame1ManageOnStart'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame1ManageOnStart.grid(row=0, column=1, sticky="W")
        tab4Frame1ManageOnStart.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame1ManageOnStartMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame1ManageOnStart.bind('<Leave>', self.on_leave)

        self.boolInventoryIV = IntVar()
        self.boolInventoryIV.set(self.config['poke_management'].get('inventory_iv', 0))
        self.tab4Frame1InventoryIV = tk.Checkbutton(tab4Frame1, variable=self.boolInventoryIV, command=self.inventoryIV_checkbox,
                                                    text=self.lang[self.gui_lang]['tab4Frame1InventoryIV'].replace('\\n', '\n').replace('\\t', '\t'))
        if self.config['client'].get('client', 'None').lower() not in ['pgsharp', 'pgsharp paid', 'pgsharppaid']:
            self.tab4Frame1InventoryIV.config(state=tk.DISABLED)
        self.tab4Frame1InventoryIV.grid(row=0, column=2, sticky="W")
        self.tab4Frame1InventoryIV.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame1InventoryIVMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab4Frame1InventoryIV.bind('<Leave>', self.on_leave)

        self.intStopCheck = IntVar()
        self.intStopCheck.set(self.config['poke_management'].get('stop_check_at', 50))
        tab4Frame1StopCheck = tk.Scale(tab4Frame1, orient=tk.HORIZONTAL, variable=self.intStopCheck, from_=0, to=300, resolution=10, length=150,
                                       command=self.stopCheck_scale, label=self.lang[self.gui_lang]['tab4Frame1StopCheck'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame1StopCheck.grid(row=0, column=3, sticky="W")
        tab4Frame1StopCheck.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame1StopCheckMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame1StopCheck.bind('<Leave>', self.on_leave)

        # Mass Transfer
        self.boolMassTransfer = IntVar()
        self.boolMassTransfer.set(self.config['poke_management'].get('mass_transfer', 0))
        tab4Frame1MassTransfer = tk.Checkbutton(tab4Frame1, variable=self.boolMassTransfer, command=self.massTransfer_checkbox,
                                                text=self.lang[self.gui_lang]['tab4Frame1MassTransfer'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame1MassTransfer.grid(row=1, column=0, sticky="W")
        tab4Frame1MassTransfer.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame1MassTransferMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame1MassTransfer.bind('<Leave>', self.on_leave)

        # Search String
        tab4Frame1PokeBagSearchLabel = tk.Label(
            tab4Frame1, text=self.lang[self.gui_lang]['tab4Frame1PokeBagSearchLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame1PokeBagSearchLabel.grid(row=1, column=2, sticky="E")
        self.strPokeBagSearch = StringVar()
        self.strPokeBagSearch.set(self.config['poke_management'].get('poke_search_string', "age0-1"))
        tab4Frame1PokeBagSearchEntry = tk.Entry(tab4Frame1, textvariable=self.strPokeBagSearch)
        tab4Frame1PokeBagSearchEntry.grid(row=1, column=3, sticky="W")
        tab4Frame1PokeBagSearchEntry.bind('<KeyRelease>', self.pokeBagSearch_entry)
        tab4Frame1PokeBagSearchEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame1PokeBagSearchMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame1PokeBagSearchEntry.bind('<Leave>', self.on_leave)

        # Item Management
        # Tab 4 Configurations
        tab4Frame2 = tk.LabelFrame(self.tab4, text=self.lang[self.gui_lang]['tab4Frame2'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab4Frame2.grid(row=1, columnspan=4, sticky='W')
        tab4Frame2.columnconfigure([0, 1, 2, 3], minsize=200)
        tab4Frame2.rowconfigure([0, 1, 2, 3, 4], minsize=25)

        # Enable Item Management
        self.boolEnableItemManagement = IntVar()
        self.boolEnableItemManagement.set(self.config['item_management'].get('enable_item_management', 0))
        tab4Frame2EnableItemManagement = tk.Checkbutton(tab4Frame2, variable=self.boolEnableItemManagement, command=self.enableItemManagement_checkbox,
                                                        text=self.lang[self.gui_lang]['tab4Frame2EnableItemManagement'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame2EnableItemManagement.grid(row=0, column=0, sticky="W")
        tab4Frame2EnableItemManagement.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2EnableItemManagementMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame2EnableItemManagement.bind('<Leave>', self.on_leave)

        self.boolClearItemOnStart = IntVar()
        self.boolClearItemOnStart.set(self.config['item_management'].get('clear_item_on_start', 0))
        tab4Frame2ClearItemOnStart = tk.Checkbutton(tab4Frame2, variable=self.boolClearItemOnStart, command=self.clearItemOnStart_checkbox,
                                                    text=self.lang[self.gui_lang]['tab4Frame2ClearItemOnStart'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame2ClearItemOnStart.grid(row=0, column=1, sticky="W")
        tab4Frame2ClearItemOnStart.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2ClearItemOnStartMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame2ClearItemOnStart.bind('<Leave>', self.on_leave)

        self.boolManageGiftsOnStart = IntVar()
        self.boolManageGiftsOnStart.set(self.config['item_management'].get('manage_gifts_on_start', 0))
        tab4Frame2ManageGiftsOnStart = tk.Checkbutton(tab4Frame2, variable=self.boolManageGiftsOnStart, command=self.manageGiftsOnStart_checkbox,
                                                    text=self.lang[self.gui_lang]['tab4Frame2ManageGiftsOnStart'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame2ManageGiftsOnStart.grid(row=0, column=2, sticky="W")
        tab4Frame2ManageGiftsOnStart.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2ManageGiftsOnStartMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame2ManageGiftsOnStart.bind('<Leave>', self.on_leave)

        self.intGiftInterval = IntVar()
        self.intGiftInterval.set(self.config['item_management'].get('gift_interval', 60))
        tab4Frame2GiftInterval = tk.Scale(tab4Frame2, orient=tk.HORIZONTAL, variable=self.intGiftInterval, from_=0, to=120, resolution=10, length=150,
                                          command=self.itemInterval_scale, label=self.lang[self.gui_lang]['tab4Frame2GiftInterval'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame2GiftInterval.grid(row=1, column=2, sticky="W")
        tab4Frame2GiftInterval.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2GiftIntervalMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame2GiftInterval.bind('<Leave>', self.on_leave)

        self.boolAutoMax = IntVar()
        self.boolAutoMax.set(self.config['item_management'].get('auto_max', 0))
        self.tab4Frame2AutoMax = tk.Checkbutton(tab4Frame2, variable=self.boolAutoMax, command=self.autoMax_checkbox,
                                                text=self.lang[self.gui_lang]['tab4Frame2AutoMax'].replace('\\n', '\n').replace('\\t', '\t'))
        if self.config['client'].get('client', 'None').lower() not in ['HAL']:
            self.tab4Frame2AutoMax.config(state=tk.DISABLED)
        self.tab4Frame2AutoMax.grid(row=0, column=3, sticky="W")
        self.tab4Frame2AutoMax.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2AutoMaxMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab4Frame2AutoMax.bind('<Leave>', self.on_leave)

        self.intItemInterval = IntVar()
        self.intItemInterval.set(self.config['item_management'].get('item_management_interval', 60))
        tab4Frame2ItemInterval = tk.Scale(tab4Frame2, orient=tk.HORIZONTAL, variable=self.intItemInterval, from_=0, to=120, resolution=10, length=150,
                                          command=self.itemInterval_scale, label=self.lang[self.gui_lang]['tab4Frame2ItemInterval'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame2ItemInterval.grid(row=1, column=0, sticky="W")
        tab4Frame2ItemInterval.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2ItemIntervalMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame2ItemInterval.bind('<Leave>', self.on_leave)

        self.intBagFullInterval = IntVar()
        self.intBagFullInterval.set(self.config['item_management'].get('reset_bagfull_interval', 60))
        tab4Frame2BallFullInterval = tk.Scale(tab4Frame2, orient=tk.HORIZONTAL, variable=self.intBagFullInterval, from_=0, to=120, resolution=10, length=150,
                                              command=self.bagFullInterval_scale, label=self.lang[self.gui_lang]['tab4Frame2BallFullInterval'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame2BallFullInterval.grid(row=1, column=1, sticky="W")
        tab4Frame2BallFullInterval.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2BallFullIntervalMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame2BallFullInterval.bind('<Leave>', self.on_leave)

        tab4Frame2Item2QuitLabel = tk.Label(
            tab4Frame2, text=self.lang[self.gui_lang]['tab4Frame2Item2QuitLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        tab4Frame2Item2QuitLabel.grid(row=1, column=2, sticky="E")
        self.strItem2Quit = StringVar()
        self.strItem2Quit.set(self.config['item_management'].get('last_item_quit', 0))
        tab4Frame2Item2QuitEntry = tk.Entry(tab4Frame2, textvariable=self.strItem2Quit)
        tab4Frame2Item2QuitEntry.grid(row=1, column=3, sticky="W")
        tab4Frame2Item2QuitEntry.bind('<KeyRelease>', self.item2Quit_entry)
        tab4Frame2Item2QuitEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab4Frame2Item2QuitEntryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab4Frame2Item2QuitEntry.bind('<Leave>', self.on_leave)

        self.itemEntries = []
        all_items = self.config.get('item_config', {})
        i = 0
        pos_x = 0
        pos_y = 0

        for key, value in all_items.items():
            tmpItem = tk.Frame(tab4Frame2)
            tmpItem.grid(row=2+pos_x, column=0+pos_y, sticky="W")
            tmpItemLabel = tk.Label(tmpItem, text=f'{key}: ')
            self.itemEntries.append(tk.Entry(tmpItem))
            #self.entries[i].delete(0, 'end')
            self.itemEntries[i].insert('end', str(int(value)))
            self.itemEntries[i].bind('<KeyRelease>', partial(self.itemAction, i, key))
            self.itemEntries[i].bind('<Enter>', lambda event: self.on_enter(
                event, msg=self.lang[self.gui_lang]['itemCheckbox'].replace('\\n', '\n').replace('\\t', '\t')))
            self.itemEntries[i].bind('<Leave>', self.on_leave)
            tmpItemLabel.pack(side=tk.TOP, anchor=tk.W)
            self.itemEntries[i].pack(side=tk.LEFT)
            i += 1
            pos_y += 1
            if i % 4 == 0:
                pos_x += 1
                pos_y = 0

        # Items
        #self.var1 = tk.IntVar()
        #self.var2 = tk.IntVar()
        #self.var3 = tk.IntVar()
        #self.var4 = tk.IntVar()
        #self.var5 = tk.IntVar()
        #self.var6 = tk.IntVar()
        #self.var7 = tk.IntVar()
        #self.var8 = tk.IntVar()
        #self.var9 = tk.IntVar()
        #self.var10 = tk.IntVar()
        #self.var11 = tk.IntVar()
        #self.var12 = tk.IntVar()
        #self.var13 = tk.IntVar()
        #self.var14 = tk.IntVar()

        #allvar = [self.var1,self.var2,self.var3,self.var4,self.var5,self.var6,self.var7,self.var8,self.var9,self.var10,self.var11,self.var12,self.var13,self.var14]
        #i = 0
        #pos_x = 0
        #pos_y = 0
        # for key, value in self.config['item_config'].items():
        #    allvar[i].set(int(value))
        #    itemCheckbox = tk.Checkbutton(tab4Frame2, variable=allvar[i], command=lambda itemkey=key, indice=i: self.itemCallback(itemkey, allvar[indice]),text=key)
        #    itemCheckbox.grid(row=2+pos_x, column=0+pos_y,sticky="W")
        #    itemCheckbox.bind('<Enter>', lambda event: self.on_enter(event, msg=self.lang[self.gui_lang]['itemCheckbox'].replace('\\n','\n').replace('\\t','\t')))
        #    itemCheckbox.bind('<Leave>',self.on_leave)
        #    i+=1
        #    pos_y += 1
        #    if i % 4 == 0:
        #        pos_x += 1
        #        pos_y = 0

        # The tool tips

        but_save = tk.Button(self.tab4, text=self.lang[self.gui_lang]['but_save'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.save_config)
        but_save.grid(row=4, column=1)
        but_close = tk.Button(self.tab4, text=self.lang[self.gui_lang]['but_close'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.close_win)
        but_close.grid(row=4, column=2)
        butStartRAB = tk.Button(self.tab4, text=self.lang[self.gui_lang]['tab1text6'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.start_rab)
        butStartRAB.grid(row=4, column=3)

    def constructTab5(self):
        # Tab 5 Telegram Feed
        tab5TempFrame = tk.Frame(self.tab5)
        tab5TempFrame.grid(row=0, columnspan=4, sticky='W')
        tab5TempFrame1 = tk.Frame(tab5TempFrame)
        tab5TempFrame2 = tk.Frame(tab5TempFrame)
        tab5TempFrame3 = tk.Frame(tab5TempFrame)
        tab5TempFrame4 = tk.Frame(tab5TempFrame)
        tab5TempFrame1.pack(fill=tk.X)
        tab5TempFrame2.pack(fill=tk.X)
        tab5TempFrame3.pack(fill=tk.X)
        tab5TempFrame4.pack(fill=tk.X)
        feedInstructionsP1 = tk.Label(tab5TempFrame1, text=self.lang[self.gui_lang]['tab5text1'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        feedInstructionsP2 = tk.Label(tab5TempFrame1, text=self.lang[self.gui_lang]['tab5text2'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, foreground='Blue', cursor="hand2")
        feedInstructionsP3 = tk.Label(tab5TempFrame1, text=self.lang[self.gui_lang]['tab5text3'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        feedInstructionsP4 = tk.Label(tab5TempFrame2, text=self.lang[self.gui_lang]['tab5text4'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        feedInstructionsP5 = tk.Label(tab5TempFrame3, text=self.lang[self.gui_lang]['tab5text5'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        feedInstructionsP6 = tk.Label(tab5TempFrame4, text=self.lang[self.gui_lang]['tab5text6'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        feedInstructionsP7 = tk.Label(tab5TempFrame4, text=self.lang[self.gui_lang]['tab5text7'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, foreground='Blue', cursor="hand2")
        feedInstructionsP8 = tk.Label(tab5TempFrame4, text=self.lang[self.gui_lang]['tab5text8'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT)
        feedInstructionsP9 = tk.Label(tab5TempFrame4, text=self.lang[self.gui_lang]['tab5text9'].replace(
            '\\n', '\n').replace('\\t', '\t'), justify=tk.LEFT, foreground='Blue', cursor="hand2")

        feedInstructionsP1.pack(side=tk.LEFT, anchor=tk.NW)
        feedInstructionsP2.pack(side=tk.LEFT, anchor=tk.NW)
        feedInstructionsP3.pack(side=tk.LEFT, anchor=tk.NW)
        feedInstructionsP4.pack(side=tk.TOP, anchor=tk.NW)
        feedInstructionsP5.pack(side=tk.TOP, anchor=tk.NW)
        feedInstructionsP6.pack(side=tk.LEFT, anchor=tk.NW)
        feedInstructionsP7.pack(side=tk.LEFT, anchor=tk.NW)
        feedInstructionsP8.pack(side=tk.LEFT, anchor=tk.NW)
        feedInstructionsP9.pack(side=tk.LEFT, anchor=tk.NW)

        feedInstructionsP2.bind("<Button-1>", lambda e: self.openBrowser("https://my.telegram.org"))
        feedInstructionsP7.bind("<Button-1>", lambda e: self.openBrowser("https://t.me/RealAndroidBotFeed"))
        feedInstructionsP9.bind("<Button-1>", lambda e: self.openBrowser("https://t.me/rab_feed_bot"))

        # Tab 5 Telegram
        tab5Frame1 = tk.LabelFrame(self.tab5, text=self.lang[self.gui_lang]['tab5Frame1'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab5Frame1.grid(row=1, columnspan=4, sticky='W')
        tab5Frame1.columnconfigure([0, 1, 2, 3], minsize=200)
        tab5Frame1.rowconfigure([0, 1], minsize=25)

        # Enable Telegram Feed
        self.boolEnableTelegramFeed = IntVar()
        self.boolEnableTelegramFeed.set(self.config['telegram'].get('enabled', 0))
        tab5Frame1EnableTelegramFeed = tk.Checkbutton(tab5Frame1, variable=self.boolEnableTelegramFeed, command=self.enableTelegramFeed_checkbox,
                                                      text=self.lang[self.gui_lang]['tab5Frame1EnableTelegramFeed'].replace('\\n', '\n').replace('\\t', '\t'))
        tab5Frame1EnableTelegramFeed.grid(row=0, column=0, sticky="W")
        tab5Frame1EnableTelegramFeed.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame1EnableTelegramFeedMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame1EnableTelegramFeed.bind('<Leave>', self.on_leave)

        tab5Frame1TmpFrame1 = tk.Frame(tab5Frame1)
        tab5Frame1TmpFrame1.grid(row=0, column=1, sticky="W")
        tab5Frame1TelegramApiIDLabel = tk.Label(
            tab5Frame1TmpFrame1, text=self.lang[self.gui_lang]['tab5Frame1TelegramApiIDLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        self.strTelegramApiID = StringVar()
        self.strTelegramApiID.set(self.config['telegram'].get('telegram_api_id', '0'))
        tab5Frame1TelegramApiIDEntry = tk.Entry(tab5Frame1TmpFrame1, textvariable=self.strTelegramApiID)
        tab5Frame1TelegramApiIDLabel.pack(side=tk.TOP, anchor=tk.NW)
        tab5Frame1TelegramApiIDEntry.pack(side=tk.TOP, anchor=tk.NW)
        #tab4Frame2Item2QuitEntry.grid(row=1, column=3,sticky="W")
        tab5Frame1TelegramApiIDEntry.bind('<KeyRelease>', self.telegramApiID_entry)
        tab5Frame1TelegramApiIDEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame1TelegramApiIDEntryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame1TelegramApiIDEntry.bind('<Leave>', self.on_leave)

        tab5Frame1TmpFrame2 = tk.Frame(tab5Frame1)
        tab5Frame1TmpFrame2.grid(row=0, column=2, columnspan=2, sticky="WE")
        tab5Frame1TelegramApiHashLabel = tk.Label(
            tab5Frame1TmpFrame2, text=self.lang[self.gui_lang]['tab5Frame1TelegramApiHashLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        self.strTelegramApiHash = StringVar()
        self.strTelegramApiHash.set(self.config['telegram'].get('telegram_api_hash', '0'))
        tab5Frame1TelegramApiHashEntry = tk.Entry(tab5Frame1TmpFrame2, textvariable=self.strTelegramApiHash)
        tab5Frame1TelegramApiHashLabel.pack(side=tk.TOP, anchor=tk.NW)
        tab5Frame1TelegramApiHashEntry.pack(fill=tk.BOTH, side=tk.TOP, anchor=tk.NW)
        #tab4Frame2Item2QuitEntry.grid(row=1, column=3,sticky="W")
        tab5Frame1TelegramApiHashEntry.bind('<KeyRelease>', self.telegramApiHash_entry)
        tab5Frame1TelegramApiHashEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame1TelegramApiHashEntryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame1TelegramApiHashEntry.bind('<Leave>', self.on_leave)

        tab5Frame1TmpFrame3 = tk.Frame(tab5Frame1)
        tab5Frame1TmpFrame3.grid(row=1, column=0, columnspan=2, sticky="WE")
        tab5Frame1TelegramProxyLabel = tk.Label(
            tab5Frame1TmpFrame3, text=self.lang[self.gui_lang]['tab5Frame1TelegramProxyLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        self.strTelegramProxy = StringVar()
        self.strTelegramProxy.set(self.config['telegram'].get('proxy', ''))
        tab5Frame1TelegramProxyEntry = tk.Entry(tab5Frame1TmpFrame3, textvariable=self.strTelegramProxy)
        tab5Frame1TelegramProxyLabel.pack(side=tk.TOP, anchor=tk.NW)
        tab5Frame1TelegramProxyEntry.pack(fill=tk.BOTH, side=tk.TOP, anchor=tk.NW)
        #tab4Frame2Item2QuitEntry.grid(row=1, column=3,sticky="W")
        tab5Frame1TelegramProxyEntry.bind('<KeyRelease>', self.telegramProxy_entry)
        tab5Frame1TelegramProxyEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame1TelegramProxyEntryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame1TelegramProxyEntry.bind('<Leave>', self.on_leave)

        # Tab 5 Frame 2 Shiny Check
        self.tab5Frame2 = tk.LabelFrame(self.tab5, text=self.lang[self.gui_lang]['tab5Frame2'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        self.tab5Frame2.grid(row=2, columnspan=4, sticky='W')
        self.tab5Frame2.columnconfigure([0, 1, 2, 3], minsize=200)
        self.tab5Frame2.rowconfigure([0, 1], minsize=25)

        self.boolEnableShinyCheck = IntVar()
        self.boolEnableShinyCheck.set(self.config['shiny_check'].get('enabled', 0))
        tab5Frame2EnableShinyCheck = tk.Checkbutton(self.tab5Frame2, variable=self.boolEnableShinyCheck, command=self.enableShinyCheck_checkbox,
                                                    text=self.lang[self.gui_lang]['tab5Frame2EnableShinyCheck'].replace('\\n', '\n').replace('\\t', '\t'))
        tab5Frame2EnableShinyCheck.grid(row=0, column=0, sticky="W")
        tab5Frame2EnableShinyCheck.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame2EnableShinyCheckMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame2EnableShinyCheck.bind('<Leave>', self.on_leave)

        self.boolShinyAutoCatch = IntVar()
        self.boolShinyAutoCatch.set(self.config['shiny_check'].get('auto_catch', 0))
        tab5Frame2ShinyAutoCatch = tk.Checkbutton(self.tab5Frame2, variable=self.boolShinyAutoCatch, command=self.shinyAutoCatch_checkbox,
                                                  text=self.lang[self.gui_lang]['tab5Frame2ShinyAutoCatch'].replace('\\n', '\n').replace('\\t', '\t'))
        tab5Frame2ShinyAutoCatch.grid(row=0, column=1, sticky="W")
        tab5Frame2ShinyAutoCatch.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame2ShinyAutoCatchMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame2ShinyAutoCatch.bind('<Leave>', self.on_leave)

        tab5Frame2FeedOption = tk.LabelFrame(self.tab5Frame2, text=self.lang[self.gui_lang]['tab5Frame2FeedOption'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab5Frame2FeedOption.grid(row=1, columnspan=4, sticky='WE')
        tab5Frame2FeedOption.columnconfigure([0, 1, 2, 3, 4], minsize=150)
        tab5Frame2FeedOption.rowconfigure([0], minsize=25)

        self.boolFeedFree = IntVar()
        if 'Free Feed' in self.config['shiny_check'].get('src_telegram', []):
            self.boolFeedFree.set(1)
        else:
            self.boolFeedFree.set(0)
        tab5Frame2FeedFree = tk.Checkbutton(tab5Frame2FeedOption, variable=self.boolFeedFree, command=self.feedFree_checkbox,
                                            text=self.lang[self.gui_lang]['tab5Frame2FeedFree'].replace('\\n', '\n').replace('\\t', '\t'))
        tab5Frame2FeedFree.grid(row=0, column=0, sticky="W")

        self.boolFeed100IVShiny = IntVar()
        if '100IV Shiny' in self.config['shiny_check'].get('src_telegram', []):
            self.boolFeed100IVShiny.set(1)
        else:
            self.boolFeed100IVShiny.set(0)
        self.tab5Frame2Feed100IVShiny = tk.Checkbutton(tab5Frame2FeedOption, variable=self.boolFeed100IVShiny, command=self.feed100IVShiny_checkbox,
                                                       text=self.lang[self.gui_lang]['tab5Frame2Feed100IVShiny'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab5Frame2Feed100IVShiny.grid(row=0, column=1, sticky="W")

        self.boolFeed82IVShiny = IntVar()
        if '82IV Shiny' in self.config['shiny_check'].get('src_telegram', []):
            self.boolFeed82IVShiny.set(1)
        else:
            self.boolFeed82IVShiny.set(0)
        self.tab5Frame2Feed82IVShiny = tk.Checkbutton(tab5Frame2FeedOption, variable=self.boolFeed82IVShiny, command=self.feed82IVShiny_checkbox,
                                                      text=self.lang[self.gui_lang]['tab5Frame2Feed82IVShiny'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab5Frame2Feed82IVShiny.grid(row=0, column=2, sticky="W")

        self.boolFeedPVP = IntVar()
        if 'PVP' in self.config['shiny_check'].get('src_telegram', []):
            self.boolFeedPVP.set(1)
        else:
            self.boolFeedPVP.set(0)
        self.tab5Frame2PVPShiny = tk.Checkbutton(
            tab5Frame2FeedOption, variable=self.boolFeedPVP, command=self.feedPVP_checkbox, text='PVP')
        self.tab5Frame2PVPShiny.grid(row=0, column=3, sticky="W")

        self.boolFeedRare100IV = IntVar()
        if 'Rare 100IV' in self.config['shiny_check'].get('src_telegram', []):
            self.boolFeedRare100IV.set(1)
        else:
            self.boolFeedRare100IV.set(0)
        self.tab5Frame2FeedRare100IV = tk.Checkbutton(tab5Frame2FeedOption, variable=self.boolFeedRare100IV, command=self.feedRare100IV_checkbox,
                                                      text=self.lang[self.gui_lang]['tab5Frame2FeedRare100IV'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab5Frame2FeedRare100IV.grid(row=0, column=4, sticky="W")

        self.tab5Frame2Feed100IVShiny.config(state=tk.NORMAL)
        self.tab5Frame2Feed82IVShiny.config(state=tk.NORMAL)
        self.tab5Frame2PVPShiny.config(state=tk.NORMAL)
        self.tab5Frame2FeedRare100IV.config(state=tk.NORMAL)

        tempShinyMon2Catch = tk.Frame(self.tab5Frame2)
        tempShinyMon2Catch.grid(row=2, column=1, columnspan=3, sticky="NSEW")
        tab5Frame2ShinyMon2Catch = tk.Label(
            self.tab5Frame2, text=self.lang[self.gui_lang]['tab5Frame2ShinyMon2Catch'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['shiny_check'].get('mon_to_check', []))
        self.txtShinyMon2Catch = tk.Text(tempShinyMon2Catch, height='2')
        self.txtShinyMon2Catch.insert(tk.INSERT, convertedText)
        self.txtShinyMon2Catch.bind('<KeyRelease>', self.shinyMon2Catch_entry)
        self.txtShinyMon2Catch.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame2ShinyMon2CatchMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtShinyMon2Catch.bind('<Leave>', self.on_leave)
        tab5Frame2ShinyMon2Catch.grid(row=2, column=0, sticky="W")
        self.txtShinyMon2Catch.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        tempShinyMon2Ignore = tk.Frame(self.tab5Frame2)
        tempShinyMon2Ignore.grid(row=3, column=1, columnspan=3, sticky="NSEW")
        tab5Frame2ShinyMon2Ignore = tk.Label(
            self.tab5Frame2, text=self.lang[self.gui_lang]['tab5Frame2ShinyMon2Ignore'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['shiny_check'].get('mon_to_ignore', []))
        self.txtShinyMon2Ignore = tk.Text(tempShinyMon2Ignore, height='2')
        self.txtShinyMon2Ignore.insert(tk.INSERT, convertedText)
        self.txtShinyMon2Ignore.bind('<KeyRelease>', self.shinyMon2Ignore_entry)
        self.txtShinyMon2Ignore.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame2ShinyMon2IgnoreMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtShinyMon2Ignore.bind('<Leave>', self.on_leave)
        tab5Frame2ShinyMon2Ignore.grid(row=3, column=0, sticky="W")
        self.txtShinyMon2Ignore.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        # Tab 5 Frame 3 Snipping
        self.tab5Frame3 = tk.LabelFrame(self.tab5, text=self.lang[self.gui_lang]['tab5Frame3'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        self.tab5Frame3.grid(row=3, columnspan=4, sticky='W')
        self.tab5Frame3.columnconfigure([0, 1, 2, 3], minsize=200)
        self.tab5Frame3.rowconfigure([0, 1], minsize=25)

        self.boolEnableSnipeCheck = IntVar()
        self.boolEnableSnipeCheck.set(self.config['snipe'].get('enabled', 0))
        tab5Frame3EnableSnipeCheck = tk.Checkbutton(self.tab5Frame3, variable=self.boolEnableSnipeCheck, command=self.enableSnipeCheck_checkbox,
                                                    text=self.lang[self.gui_lang]['tab5Frame3EnableSnipeCheck'].replace('\\n', '\n').replace('\\t', '\t'))
        tab5Frame3EnableSnipeCheck.grid(row=0, column=0, sticky="W")
        tab5Frame3EnableSnipeCheck.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame3EnableSnipeCheckMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame3EnableSnipeCheck.bind('<Leave>', self.on_leave)

        self.boolSnipeAutoCatch = IntVar()
        self.boolSnipeAutoCatch.set(self.config['snipe'].get('auto_catch', 0))
        tab5Frame3SnipeAutoCatch = tk.Checkbutton(self.tab5Frame3, variable=self.boolSnipeAutoCatch, command=self.snipeAutoCatch_checkbox,
                                                  text=self.lang[self.gui_lang]['tab5Frame3SnipeAutoCatch'].replace('\\n', '\n').replace('\\t', '\t'))
        tab5Frame3SnipeAutoCatch.grid(row=0, column=1, sticky="W")
        tab5Frame3SnipeAutoCatch.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame3SnipeAutoCatchMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame3SnipeAutoCatch.bind('<Leave>', self.on_leave)

        tab5Frame3TmpFrame1 = tk.Frame(self.tab5Frame3)
        tab5Frame3TmpFrame1.grid(row=0, column=2, sticky="W")
        tab5Frame3SnipeMaxCDLabel = tk.Label(
            tab5Frame3TmpFrame1, text=self.lang[self.gui_lang]['tab5Frame3SnipeMaxCDLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        self.strSnipeMaxCD = StringVar()
        self.strSnipeMaxCD.set(self.config['snipe'].get('snipe_max_cd', ''))
        tab5Frame3SnipeMaxCDEntry = tk.Entry(tab5Frame3TmpFrame1, textvariable=self.strSnipeMaxCD)
        tab5Frame3SnipeMaxCDLabel.pack(side=tk.TOP, anchor=tk.NW)
        tab5Frame3SnipeMaxCDEntry.pack(side=tk.TOP, anchor=tk.NW)
        #tab4Frame2Item2QuitEntry.grid(row=1, column=3,sticky="W")
        tab5Frame3SnipeMaxCDEntry.bind('<KeyRelease>', self.snipeMaxCD_entry)
        tab5Frame3SnipeMaxCDEntry.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame3SnipeMaxCDEntryMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame3SnipeMaxCDEntry.bind('<Leave>', self.on_leave)

        tab5Frame3FeedOption = tk.LabelFrame(self.tab5Frame3, text=self.lang[self.gui_lang]['tab5Frame3FeedSnipeOption'].replace(
            '\\n', '\n').replace('\\t', '\t'), padx=5, pady=5)
        tab5Frame3FeedOption.grid(row=1, columnspan=4, sticky='WE')
        tab5Frame3FeedOption.columnconfigure([0, 1, 2, 3, 4], minsize=150)
        tab5Frame3FeedOption.rowconfigure([0], minsize=25)

        self.boolSnipeFeedFree = IntVar()
        if 'Free Feed' in self.config['snipe'].get('src_telegram', []):
            self.boolSnipeFeedFree.set(1)
        else:
            self.boolSnipeFeedFree.set(0)
        tab5Frame3FeedFree = tk.Checkbutton(tab5Frame3FeedOption, variable=self.boolSnipeFeedFree, command=self.feedSnipeFree_checkbox,
                                            text=self.lang[self.gui_lang]['tab5Frame3FeedSnipeFree'].replace('\\n', '\n').replace('\\t', '\t'))
        tab5Frame3FeedFree.grid(row=0, column=0, sticky="W")

        self.boolSnipeFeed100IVShiny = IntVar()
        if '100IV Shiny' in self.config['snipe'].get('src_telegram', []):
            self.boolSnipeFeed100IVShiny.set(1)
        else:
            self.boolSnipeFeed100IVShiny.set(0)
        self.tab5Frame3Feed100IVShiny = tk.Checkbutton(tab5Frame3FeedOption, variable=self.boolSnipeFeed100IVShiny, command=self.feedSnipe100IV_checkbox,
                                                       text=self.lang[self.gui_lang]['tab5Frame3FeedSnipe100IVShiny'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab5Frame3Feed100IVShiny.grid(row=0, column=1, sticky="W")

        self.boolSnipeFeed82IVShiny = IntVar()
        if '82IV Shiny' in self.config['snipe'].get('src_telegram', []):
            self.boolSnipeFeed82IVShiny.set(1)
        else:
            self.boolSnipeFeed82IVShiny.set(0)
        self.tab5Frame3Feed82IVShiny = tk.Checkbutton(tab5Frame3FeedOption, variable=self.boolSnipeFeed82IVShiny, command=self.feedSnipe82IV_checkbox,
                                                      text=self.lang[self.gui_lang]['tab5Frame3FeedSnipe82IVShiny'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab5Frame3Feed82IVShiny.grid(row=0, column=2, sticky="W")

        self.boolSnipeFeedPVP = IntVar()
        if 'PVP' in self.config['snipe'].get('src_telegram', []):
            self.boolSnipeFeedPVP.set(1)
        else:
            self.boolSnipeFeedPVP.set(0)
        self.tab5Frame3PVP = tk.Checkbutton(tab5Frame3FeedOption, variable=self.boolSnipeFeedPVP,
                                            command=self.feedSnipePVP_checkbox, text='PVP')
        self.tab5Frame3PVP.grid(row=0, column=3, sticky="W")

        self.boolSnipeFeedRare100IV = IntVar()
        if 'Rare 100IV' in self.config['snipe'].get('src_telegram', []):
            self.boolSnipeFeedRare100IV.set(1)
        else:
            self.boolSnipeFeedRare100IV.set(0)
        self.tab5Frame3FeedRare100IV = tk.Checkbutton(tab5Frame3FeedOption, variable=self.boolSnipeFeedRare100IV, command=self.feedSnipeRare100IV_checkbox,
                                                      text=self.lang[self.gui_lang]['tab5Frame3FeedSnipeRare100IV'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tab5Frame3FeedRare100IV.grid(row=0, column=4, sticky="W")

        self.tab5Frame3Feed100IVShiny.config(state=tk.NORMAL)
        self.tab5Frame3Feed82IVShiny.config(state=tk.NORMAL)
        self.tab5Frame3PVP.config(state=tk.NORMAL)
        self.tab5Frame3FeedRare100IV.config(state=tk.NORMAL)

        tab5Frame3SnipeFrame = tk.Frame(self.tab5Frame3)
        tab5Frame3SnipeFrame.grid(row=2, column=1, columnspan=3, sticky="NSEW")
        tab5Frame3SnipeListLabel = tk.Label(
            self.tab5Frame3, text=self.lang[self.gui_lang]['tab5Frame3SnipeListLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        #convertedText = self.list2text(self.config['snipe'].get('snipe_list',[]))
        convertedTextResult = self.json2text(self.config['snipe'].get('snipe_list', {}))
        if convertedTextResult:
            convertedText = convertedTextResult
        else:
            convertedText = "{}"
        self.tab5Frame3SnipeList = tk.Text(tab5Frame3SnipeFrame, height='5')
        self.tab5Frame3SnipeList.insert(tk.INSERT, convertedText)
        self.tab5Frame3SnipeList.bind('<KeyRelease>', self.snipeList_entry)
        self.tab5Frame3SnipeList.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame3SnipeListMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab5Frame3SnipeList.bind('<Leave>', self.on_leave)
        tab5Frame3SnipeListLabel.grid(row=2, column=0, sticky="W")
        self.tab5Frame3SnipeList.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        tab5Frame3TmpFrame2 = tk.Frame(self.tab5Frame3)
        tab5Frame3TmpFrame2.grid(row=3, column=0, sticky="W")
        tab5Frame3SnipeRouteNameLabel = tk.Label(
            tab5Frame3TmpFrame2, text=self.lang[self.gui_lang]['tab5Frame3SnipeRouteNameLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        self.strSnipeRouteName = StringVar()
        self.strSnipeRouteName.set(self.config['snipe'].get('default_route_name', ''))
        tab5Frame3SnipeRouteName = tk.Entry(tab5Frame3TmpFrame2, textvariable=self.strSnipeRouteName)
        tab5Frame3SnipeRouteNameLabel.pack(side=tk.TOP, anchor=tk.NW)
        tab5Frame3SnipeRouteName.pack(side=tk.TOP, anchor=tk.NW)
        #tab4Frame2Item2QuitEntry.grid(row=1, column=3,sticky="W")
        tab5Frame3SnipeRouteName.bind('<KeyRelease>', self.snipeRouteName_entry)
        tab5Frame3SnipeRouteName.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame3SnipeRouteNameMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        tab5Frame3SnipeRouteName.bind('<Leave>', self.on_leave)

        tempShinyMon2Ignore = tk.Frame(self.tab5Frame2)
        tempShinyMon2Ignore.grid(row=3, column=1, columnspan=3, sticky="NSEW")
        tab5Frame2ShinyMon2Ignore = tk.Label(
            self.tab5Frame2, text=self.lang[self.gui_lang]['tab5Frame2ShinyMon2Ignore'].replace('\\n', '\n').replace('\\t', '\t'))
        convertedText = self.list2text(self.config['shiny_check'].get('mon_to_ignore', []))
        self.txtShinyMon2Ignore = tk.Text(tempShinyMon2Ignore, height='2')
        self.txtShinyMon2Ignore.insert(tk.INSERT, convertedText)
        self.txtShinyMon2Ignore.bind('<KeyRelease>', self.shinyMon2Ignore_entry)
        self.txtShinyMon2Ignore.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame2ShinyMon2IgnoreMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.txtShinyMon2Ignore.bind('<Leave>', self.on_leave)
        tab5Frame2ShinyMon2Ignore.grid(row=3, column=0, sticky="W")
        self.txtShinyMon2Ignore.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)

        tab5Frame3TmpFrame3 = tk.Frame(self.tab5Frame3)
        tab5Frame3TmpFrame3.grid(row=3, column=1, sticky="W")
        tab5Frame3SnipeCoordinatesLabel = tk.Label(
            tab5Frame3TmpFrame3, text=self.lang[self.gui_lang]['tab5Frame3SnipeCoordinatesLabel'].replace('\\n', '\n').replace('\\t', '\t'))
        #self.strSnipeCoordinates = StringVar()
        convertedText = self.list2text(self.config['snipe'].get('default_location', []))
        # self.strSnipeCoordinates.set(convertedText)
        # self.strSnipeCoordinates.set(self.config['snipe'].get('default_route_name',''))
        self.tab5Frame3SnipeCoordinates = tk.Text(tab5Frame3TmpFrame3, height='1', width='25')
        self.tab5Frame3SnipeCoordinates.insert(tk.INSERT, convertedText)
        tab5Frame3SnipeCoordinatesLabel.pack(side=tk.TOP, anchor=tk.NW)
        self.tab5Frame3SnipeCoordinates.pack(side=tk.TOP, anchor=tk.NW)
        #tab4Frame2Item2QuitEntry.grid(row=1, column=3,sticky="W")
        self.tab5Frame3SnipeCoordinates.bind('<KeyRelease>', self.snipeCoordinates_entry)
        self.tab5Frame3SnipeCoordinates.bind('<Enter>', lambda event: self.on_enter(
            event, msg=self.lang[self.gui_lang]['tab5Frame3SnipeCoordinatesMsg'].replace('\\n', '\n').replace('\\t', '\t')))
        self.tab5Frame3SnipeCoordinates.bind('<Leave>', self.on_leave)

        but_save = tk.Button(self.tab5, text=self.lang[self.gui_lang]['but_save'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.save_config)
        but_save.grid(row=4, column=1)
        but_close = tk.Button(self.tab5, text=self.lang[self.gui_lang]['but_close'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.close_win)
        but_close.grid(row=4, column=2)
        butStartRAB = tk.Button(self.tab5, text=self.lang[self.gui_lang]['tab1text6'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.start_rab)
        butStartRAB.grid(row=4, column=3)

        if self.config['client'].get('client', '').lower() in ['pgsharp', 'pgsharp paid']:
            self.disableChildren(self.tab5Frame2)
            self.disableChildren(self.tab5Frame3)

    def constructTab6(self):
        # last_saved_image = 'screenshots/'+self.+'png'
        # if os.path.exists(device_config_path):

        #basewidth = 400
        #img = Image.open("img/usb_debugging2.jpg")
        #wpercent = (basewidth / float(img.size[0]))
        #hsize = int((float(img.size[1]) * float(wpercent)))
        #img = img.resize((basewidth, hsize), Image.ANTIALIAS)
        #self.imgInstructions = ImageTk.PhotoImage(img)
        #xiaomiImage = tk.Label(self.tab1,image=self.imgInstructions)
        #xiaomiImage.pack(side=tk.TOP, anchor=tk.W)
        #openImageFile = tk.Button(self.tab6,text='Open Image',command=self.reset_resolution)

        # Tab 6 Tools
        resetPhoneResolution = tk.Button(self.tab6, text=self.lang[self.gui_lang]['resetPhoneResolution'].replace(
            '\\n', '\n').replace('\\t', '\t'), command=self.reset_resolution)
        resetPhoneResolution.pack()

        #setPhoneResolution = tk.Button(self.tab6,text='1080x1920',command=self.set_resolution)
        # setPhoneResolution.pack()

    def start_win(self, parent):
        self.win_main = parent
        if not self.photo:
            self.photo = PhotoImage(file="icon.png")
        self.win_main.iconphoto(False, self.photo)

        self.tabControl = ttk.Notebook(self.win_main)
        self.results = tk.Label(self.win_main, foreground='Blue', text='', wraplength=800, height=3)
        self.tab1 = tk.Frame(self.tabControl)
        self.tab2 = tk.Frame(self.tabControl)
        #self.tab3 = tk.Frame(self.tabControl)
        self.ContainerThree = tk.Frame(self.tabControl)
        self.tab4 = tk.Frame(self.tabControl)
        self.tab5 = tk.Frame(self.tabControl)

        self.tab6 = tk.Frame(self.tabControl)
        self.tabControl.add(self.tab1, text=self.lang[self.gui_lang]['tab1'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tabControl.add(self.tab2, text=self.lang[self.gui_lang]['tab2'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tabControl.add(self.ContainerThree, text=self.lang[self.gui_lang]
                            ['tab3'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tabControl.add(self.tab4, text=self.lang[self.gui_lang]['tab4'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tabControl.add(self.tab5, text=self.lang[self.gui_lang]['tab5'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tabControl.add(self.tab6, text=self.lang[self.gui_lang]['tab6'].replace('\\n', '\n').replace('\\t', '\t'))
        self.tabControl.pack(expand=1, fill="both")

        canvas3 = tk.Canvas(self.ContainerThree, width=850, height=700)
        scroll = tk.Scrollbar(self.ContainerThree, command=canvas3.yview)
        canvas3.config(yscrollcommand=scroll.set, scrollregion=(0, 0, 0, 1000))
        canvas3.pack(side=tk.LEFT, fill=tk.BOTH, expand=1)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.tab3 = tk.Frame(canvas3, width=600, height=800)
        canvas3.create_window(420, 470, window=self.tab3)

        self.results.pack()

        OwnerInfo1 = tk.Label(self.win_main, text='Discord: ', justify=tk.LEFT, wraplength=800)
        OwnerInfo1.pack(side=tk.LEFT, anchor=tk.SW)
        link1 = tk.Label(self.win_main, text="RAB Discord Channel", foreground='Blue', cursor="hand2")
        link1.pack(side=tk.LEFT, anchor=tk.SW)
        link1.bind("<Button-1>", lambda e: self.openBrowser("https://discord.gg/ZVesHeBzYD"))

        OwnerInfo2 = tk.Label(self.win_main, text='Github: ', justify=tk.LEFT, wraplength=800)
        OwnerInfo2.pack(side=tk.LEFT, anchor=tk.SW)
        link2 = tk.Label(self.win_main, text="Github Page", foreground='Blue', cursor="hand2")
        link2.pack(side=tk.LEFT, anchor=tk.SW)
        link2.bind("<Button-1>", lambda e: self.openBrowser("https://github.com/stonedDiscord/RealAndroidBot/"))

        link2 = tk.Label(self.win_main, text='v'+self.version)
        link2.pack(side=tk.RIGHT, anchor=tk.SE)

        self.constructTab1()
        self.constructTab2()
        self.constructTab3()
        self.constructTab4()
        self.constructTab5()
        self.constructTab6()
        self.default_disable()

        # Position
        self.win_main.wm_title("RealAndroidBot (RAB)")
        self.win_main.withdraw()
        self.win_main.update_idletasks()  # Update "requested size" from geometry manager
        #self.win_main.eval('tk::PlaceWindow . center')
        windowWidth = self.win_main.winfo_reqwidth()
        windowHeight = self.win_main.winfo_reqheight()

        positionRight = int(self.win_main.winfo_screenwidth()/2 - windowWidth/2)
        positionDown = int(self.win_main.winfo_screenheight()/2 - windowHeight/2)

        self.win_main.geometry("+{}+{}".format(positionRight, positionDown))
        self.win_main.deiconify()
        if self.win_main.winfo_screenwidth() < 1920 or self.win_main.winfo_screenheight() < 1080:
            logger.warning(self.lang[self.gui_lang]['screenSizeWarning'].replace('\\n', '\n').replace(
                '\\t', '\t') + '{} x {}'.format(self.win_main.winfo_screenwidth(), self.win_main.winfo_screenheight()))

        self.win_main.resizable(False, False)

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

# Comment these off after deployment
Loader.add_constructor('!include', Loader.include)

logger.setLevel(args.log_level)

# load config
default_config_path = "config.yaml"
if args.device_id:
    device_config_path = args.device_id + ".yaml"
else:
    device_config_path = "config.yaml"

if args.config_filename:
    config_path = args.config_filename
else:
    config_path = default_config_path
    if os.path.exists(device_config_path):
        config_path = device_config_path

if not os.path.exists(config_path):
    # Use default config.example.yaml
    config_path = 'config.example.yaml'
    #raise ValueError("Config file {} doesn't exist.".format(self.args.config_filename))

with open(config_path, "r", encoding='utf8') as f:
    config = yaml.load(f, Loader)

if args.headless:
    rab.call_main()
else:
    with open('lang.yaml', "r", encoding='utf8') as f:
        lang = yaml.load(f, Loader)
    root = tk.Tk()
    rabwindow = RABGui(config, lang, config_path, args.device_id)
    rabwindow.start_win(root)

    root.mainloop()
