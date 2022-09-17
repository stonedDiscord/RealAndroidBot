# Config file
### All lines that are commented out (and some that aren't) are optional ###
# DATABASE REALTED
# MYSQL Address Example: mysql://SGEXRAID:mypassword@127.0.0.1:3306/hydro_monocle?charset=utf8mb4
# DB_ENGINE = 'mysql+pymysql://thomaspoi:Mgelhjky&12@127.0.0.1:3306/hydro_monocle?charset=utf8mb4'  ## don't forget ?charset=utf8mb4 after your DB name !
# don't forget ?charset=utf8mb4 after your DB name !
DB_ENGINE = 'mysql+pymysql://thomaspoi:Mgelhjky&12@119.161.100.154/rab?charset=utf8mb4'
# don't forget ?charset=utf8mb4 after your DB name !
DB_ENGINE2 = 'mysql+pymysql://thomaspoi:Mgelhjky&12@119.161.100.154/hydro_monocle?charset=utf8mb4'
# DB queue/pool size settings
# These are to be used if you see errors relating to pool_size from sqlalchemy
# DO not set extremely high
#
DB_POOL_SIZE = 100     # sqlalchemy defualt
DB_MAX_OVERFLOW = 50  # sqlalchemy default

# Reconnect db session after x seconds. It solves lost connection error if DB wait_timeout is set to lower values.
DB_POOL_RECYCLE = 60

# POSITION ON SCREEN
# DO NOT CHANGE THE VALUES unless instructed to do so
# Or if you are debuging
# THESE NEED TO REDO
SCREENSHOT_POSITIONS = {
    "rename": [539, 936],
    "next": [980, 280],
    "keyboard_ok": [933, 1085],
    "rename_ok": [540, 1050],
    "close_calcy_dialog": [966, 1092],
    "edit_box": [90, 1090],
    "paste": [483, 1092],
    "favorite_button": [980, 156],
    "favorite_button_box": [960, 142, 1001, 180],
    "pokemon_menu_button": [933, 1777],
    "appraise_button": [934, 1377],
    "continue_appraisal": [590, 1770],
    "dismiss_calcy": [555, 1296],
    "appraisal_box": [45, 1664, 1032, 1872],
    "pokestop": [540, 1250],
    "spin_swipe": [150, 1040, 540, 1040],
    "x_button": [540, 1750],
    "quest_button": [1000, 1870],
    "claim_reward_box": [320, 1230, 750, 1310],
    "exit_encounter": [90, 150],
    "im_a_passenger_button_box": [320, 1425, 760, 1490],
    "exit_other": [550, 830],
    "oh_hatching_box": [430, 430, 700, 640],
    "shop_button_text_box": [470, 1130, 615, 1200],
    "bottom_pokestop_bar": [240, 1958, 300, 1985],
    "char_box": [500, 1160, 590, 1260],
    "char": [550, 1240]
}
# CLIENT RELATED
# Set True if using Pokemod Beta (Donation Version) Currently ONLY accept this mode
BETA_CLIENT = True

# POKEMON CATCH RELATED
# IV/LVL to keep
ENABLE_KEEP_MON = True  # True to keep pokemon that meet the min iv/lvl requirements, False to transfer all
# The settings below allow you to decide exactly what IV conditions are met before keeping
MIN_ATK = 15
MIN_DEF = 15
MIN_STA = 15
MIN_LVL = 1
ENABLE_KEEP_SHINY = True  # True to keep all shiny found

# PVP Options
ENABLE_KEEP_PVP = True  # True to keep pvp pokemon, false to disable this option
GL_TO_KEEP = []  # Example: [3,6,9] List of Pokedex number of Pokemons to keep if they meet conditions. You only need to add the pokemon that you want to use in GBL and we will keep pre-evolved if they meet conditions. Leave it empty for all Pokemon that meet conditions. Empty list means keep all poke that meet condition
GL_RATING = 99.9  # Keep rating equal to or above this value and
GL_CP = 1450  # Keep PVP CP equal to or above this value
UL_TO_KEEP = []  # Example: [3,6,9] List of Pokedex number of Pokemons to keep if they meet conditions. You only need to add the pokemon that you want to use in GBL and we will keep pre-evolved if they meet conditions. Leave it empty for all Pokemon that meet conditions
UL_RATING = 99.9  # Keep rating equal to or above this value and
UL_CP = 1300  # Keep PVP CP equal to or above this value

# ITEM MANAGEMENT
ENABLE_ITEM_MANAGEMENT = True
ITEM_MANAGEMENT_INTERVAL = 60  # Every x mins open item inventory and delete items
# Set what item to be deleted
# You can also add in items not in this list, please follow exactly what is shown on screen
ITEM_CONFIG = {
    "Potion": True,
    "Super Potion": True,
    "Hyper Potion": False,
    "Max Potion": False,
    "Revive": False,
    "Max Revive": False,
    "Lucky Egg": False,
    "Incense": False,
    "Fast TM": False,
    "Charged TM": False,
    "Elite Fast TM": False,
    "Elite Charged TM": False,
    "Rare Candy": False,
    "Raid Pass": False,
    "Premium Battle Pass": False,
    "Remote Raid Pass": False,
    "Star Piece": False,
    "Rocket Radar": False,
    "Poké Ball": False,
    "Great Ball": False,
    "Ultra Ball": False,
    "Lure Module": False,
    "Lure Module": False,
    "Razz Berry": True,
    "Nanab Berry": True,
    "Pinap Berry": False,
    "Golden Razz Berry": False,
    "Silver Pinap Berry": False,
    "Poffin": False,
    "Sun Stone": False,
    "King's Rock": False,
    "Metal Coat": False,
    "Dragon Scale": False,
    "Sinnoh Stone": False,
    "Unova Stone": False
}

# HATCHING REALTED
