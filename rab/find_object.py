import logging
import random

from utils import get_average_color

logger = logging.getLogger('rab')


def walk_towards_pokestops(im_rgb, min_x=90, max_x=980, x_steps=8, min_y=200, max_y=750, y_steps=8):
    # To be added in future
    location_found = False
    x = 0
    y = 0
    for s in range(min_x, max_x, int(x_steps/2)):
        if location_found:
            break
        for t in range(min_y, max_y, int(y_steps/2)):
            r, g, b = get_average_color(s, t, abs(x_steps), im_rgb)
            if (40 <= r <= 100) and (210 <= g <= 255) and (250 <= b <= 255):
                location_found = True
                x = s
                y = t
                break

    if location_found:
        if x_steps >= 0 and y_steps >= 0:
            x = x - 25
            y = y - 25
        elif x_steps < 0 and y_steps < 0:
            x = x + 25
            y = y + 25
        elif x_steps >= 0 and y_steps < 0:
            x = x - 25
            y = y + 25
        elif x_steps < 0 and y_steps >= 0:
            x = x + 25
            y = y - 25

    return location_found, x, y


def is_pokestop_color(r, g, b):
    if (( 28 <= r <= 110) and (233 <= g <= 255) and (250 <= b <= 255)):
        return 'bright'
    if ((252 <= r <= 255) and (200 <= g <= 255) and ( 25 <= b <=  35)):
        return 'bright'  # fall season
    if (( 28 <= r <=  40) and (100 <= g <= 110) and (215 <= b <= 225)):
        return 'dark'
    if ((219 <= r <= 255) and (170 <= g <= 175) and ( 30 <= b <=  35)):
        return 'dark'    # fall season
    return False


def is_rocketstop_color(r, g, b):
    if ((95 <= r <= 105) and (95 <= g <= 105) and (95 <= b <= 105)):
        return 'bright'
    if ((60 <= r <= 70) and (60 <= g <= 70) and (60 <= b <= 70)):
        return 'dark'
    return False


def is_gym_color(r, g, b):
    if (0 <= r <= 60) and (0 <= g <= 50) and (245 <= b <= 255):
        return 'blue'
    if (240 <= r <= 255) and (0 <= g <= 60) and (0 <= b <= 60):
        return 'red'
    if (240 <= r <= 255) and (220 <= g <= 255) and (0 <= b <= 5):
        return 'yellow'
    if (190 <= r <= 210) and (190 <= g <= 210) and (200 <= b <= 220):
        return 'grey'
    return False


def find_pokestop(im_rgb, min_x, max_x, x_steps, min_y, max_y, y_steps, bag_full=False, find_team_rocket=False):

    pokestop_found, x, y, r, g, b = False, 0, 0, 0, 0, 0

    if not bag_full:
        for s in range(min_x, max_x, int(x_steps/2)):
            if pokestop_found:
                break
            for t in range(min_y, max_y, int(y_steps/2)):
                # let exclude char position
                if not ((520 <= s <= 570) and (1160 <= t <= 1240)):
                    r, g, b = get_average_color(s, t, abs(x_steps), im_rgb)

                    if (find_team_rocket and is_rocketstop_color(r, g, b)):
                        pokestop_found = True
                        x = int(s + (x_steps/2))
                        y = int(t + (y_steps/2))
                    elif (is_pokestop_color(r, g, b)):
                        pokestop_found = True
                        x = int(s + (x_steps/2))
                        y = int(t + (y_steps/2))

                    if pokestop_found:
                        break

    return pokestop_found, x, y, r, g, b


def find_object_to_tap(im_rgb, min_x, max_x, x_steps, min_y, max_y, y_steps, bag_full=False, missedcolors=[], skip_pokestop=False):
    x = random.randrange(460, 630)
    y = random.randrange(1000, 1300)
    r, g, b = None, None, None
    pokefound = False
    for s in range(min_x, max_x, int(x_steps/2)):
        if pokefound:
            break
        for t in range(min_y, max_y, int(y_steps/2)):
            # let exclude char position
            if not ((520 <= s <= 570) and (1160 <= t <= 1240)):
                r, g, b = get_average_color(s, t, abs(x_steps), im_rgb)
                # Set of colors we wll skip, and exclude them from checking
                foundmissed = False
                for missed in missedcolors:
                    if ((missed[0]-10) <= r <= (missed[0]+10)) and ((missed[1]-10) <= g <= (missed[1]+10)) and ((missed[2]-10) <= b <= (missed[2]+10)):
                        foundmissed = True
                        break
                if foundmissed:
                    continue

                # comment out first, see how well the AI will perform
                if (110 <= r <= 115) and (90 <= g <= 100) and (125 <= b <= 130):
                    continue

                if (100 <= r <= 110) and (80 <= g <= 90) and (110 <= b <= 120):
                    continue

                if (250 <= r <= 255) and (250 <= g <= 255) and (130 <= b <= 135):
                    continue

                if (210 <= r <= 230) and (230 <= g <= 255) and (225 <= b <= 250):
                    continue

                if (80 <= r <= 90) and (220 <= g <= 230) and (250 <= b <= 255):
                    continue

                if (40 <= r <= 65) and (200 <= g <= 215) and (250 <= b <= 255):
                    continue

                if (235 <= r <= 255) and (250 <= g <= 255) and (230 <= b <= 240):
                    continue

                if (235 <= r <= 255) and (250 <= g <= 255) and (130 <= b <= 145):
                    continue

                if (70 <= r <= 90) and (230 <= g <= 254) and (250 <= b <= 254):
                    continue

                if (240 <= r <= 253) and (225 <= g <= 250) and (230 <= b <= 250):
                    continue

                if (200 <= r <= 215) and (150 <= g <= 155) and (225 <= b <= 245):
                    continue

                # Gyms
                if (is_gym_color(r, g, b)):
                    continue

                # Set of colors considered as vaild
                if (210 <= r <= 220) and (110 <= g <= 120) and (5 <= b <= 15):
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (180 <= r <= 190) and (225 <= g <= 245) and (250 <= b <= 255):  # light blue pokemon, Cubchoo
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))

                elif (60 <= r <= 65) and (175 <= g <= 185) and (254 <= b <= 255):  # Marine pokemon, Marill
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (165 <= r <= 170) and (250 <= g <= 255) and (250 <= b <= 255):  # dirty blue pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (190 <= r <= 200) and (230 <= g <= 250) and (250 <= b <= 255):  # light grey pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (180 <= r <= 190) and (160 <= g <= 220) and (220 <= b <= 255):  # grey pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (130 <= r <= 140) and (138 <= g <= 142) and (130 <= b <= 140):  # grey pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (130 <= r <= 150) and (170 <= g <= 175) and (195 <= b <= 200):  # dark grey pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (169 <= r <= 172) and (209 <= g <= 212) and (254 <= b <= 255):  # dark grey pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (190 <= r <= 210) and (150 <= g <= 180) and (120 <= b <= 130):  # light brown pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (250 <= r <= 255) and (160 <= g <= 170) and (170 <= b <= 180):  # pink pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (250 <= r <= 255) and (190 <= g <= 210) and (230 <= b <= 240):  # bright pink pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (220 <= r <= 250) and (150 <= g <= 190) and (160 <= b <= 230):  # dull pink pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (200 <= r <= 220) and (150 <= g <= 170) and (220 <= b <= 250):  # dull purple pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (125 <= r <= 135) and (90 <= g <= 110) and (200 <= b <= 220):  # purple pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (150 <= r <= 160) and (165 <= g <= 170) and (200 <= b <= 205):  # grey pokemon - Ryhorn
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (245 <= r <= 255) and (215 <= g <= 225) and (105 <= b <= 115):  # light brown pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (240 <= r <= 255) and (110 <= g <= 140) and (50 <= b <= 80):  # redish brown pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (220 <= r <= 230) and (215 <= g <= 225) and (105 <= b <= 115):  # light brown pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                # elif ((230 <= r <= 255) and (230 <= g <= 255) and (
                #        (130 <= b <= 140) or (170 <= b <= 210))):  # light yellow pokemon
                #    pokefound = True
                #    x = int(s + (x_steps/2))
                #    y = int(t + (y_steps/2))
                elif (215 <= r <= 225) and (70 <= g <= 85) and (100 <= b <= 110):  # Dark Red pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (220 <= r <= 255) and (220 <= g <= 255) and (220 <= b <= 255):  # White pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (230 <= r <= 255) and (140 <= g <= 180) and (40 <= b <= 90):  # orange pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (50 <= r <= 60) and (190 <= g <= 200) and (70 <= b <= 80):  # bright Green
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (150 <= r <= 175) and (120 <= g <= 130) and (85 <= b <= 140):  # dark brown pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (200 <= r <= 255) and (160 <= g <= 190) and (85 <= b <= 140):  # brown pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (220 <= r <= 230) and (200 <= g <= 230) and (180 <= b <= 190):  # Light brown pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (85 <= r <= 150) and (80 <= g <= 100) and (85 <= b <= 160):  # Dark pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (110 <= r <= 120) and (170 <= g <= 180) and (210 <= b <= 230):  # Dark blue pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (140 <= r <= 150) and (220 <= g <= 230) and (230 <= b <= 240):  # blue pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (80 <= r <= 100) and (120 <= g <= 150) and (200 <= b <= 220):  # Dark blue pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif ((30 <= r <= 90) and (200 <= g <= 255) and (
                        250 <= b <= 255) and not (bag_full or skip_pokestop)):  # pokestop
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif ((30 <= r <= 50) and (100 <= g <= 120) and (
                        220 <= b <= 255) and not (bag_full or skip_pokestop)):  # pokestop
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (240 <= r <= 255) and (0 <= g <= 120) and (0 <= b <= 120):  # red pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (158 <= r <= 162) and (205 <= g <= 210) and (80 <= b <= 85):  # Lotad Green
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (155 <= r <= 160) and (200 <= g <= 240) and (65 <= b <= 75):  # green pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (140 <= r <= 150) and (200 <= g <= 210) and (210 <= b <= 225):  # machop
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (50 <= r <= 60) and (60 <= g <= 70) and (60 <= b <= 70):  # Very Dark Pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                # elif (240 <= r <= 255) and (240 <= g <= 255) and (70 <= b <= 100):  # yellow pokemon
                #    pokefound = True
                #    x = int(s + (x_steps/2))
                #    y = int(t + (y_steps/2))
                elif (250 <= r <= 255) and (230 <= g <= 255) and (130 <= b <= 150):  # dark yellow pokemon
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))
                elif (200 <= r <= 215) and (220 <= g <= 230) and (180 <= b <= 190):  # durty yellow
                    pokefound = True
                    x = int(s + (x_steps/2))
                    y = int(t + (y_steps/2))

                if pokefound:
                    break

    if not pokefound:
        # let's do much smaller pixel check, but very specific color and smaller area
        for s in range(345, 845, 2):
            if pokefound:
                break
            for t in range(1050, 1400, 2):
                # let exclude char position
                if not ((520 <= s <= 570) and (1160 <= t <= 1240)):
                    r, g, b = get_average_color(s, t, 2, im_rgb)
                    if (250 <= r <= 255) and (250 <= g <= 255) and (250 <= b <= 255):  # close to extreme white
                        pokefound = True
                        logger.debug("Found with white pixel...")
                        x = s
                        y = t
                    if (230 <= r <= 232) and (80 <= g <= 85) and (95 <= b <= 100):  # Dark Red
                        pokefound = True
                        logger.debug("Found with red pixel...")
                        x = s
                        y = t
                    if (250 <= r <= 255) and (175 <= g <= 180) and (165 <= b <= 175):  # Dark Pink
                        pokefound = True
                        logger.debug("Found with dark pink pixel...")
                        x = s
                        y = t
                    if (185 <= r <= 190) and (179 <= g <= 182) and (160 <= b <= 162):  # brown
                        pokefound = True
                        logger.debug("Found with dark brown pixel...")
                        x = s
                        y = t
                    if (150 <= r <= 155) and (110 <= g <= 120) and (90 <= b <= 100):  # brown 2
                        pokefound = True
                        logger.debug("Found with dark brown pixel...")
                        x = s
                        y = t
                    if (115 <= r <= 125) and (130 <= g <= 135) and (125 <= b <= 130):  # Dark grey
                        pokefound = True
                        logger.debug("Found with dark grey pixel...")
                        x = s
                        y = t
                    if (250 <= r <= 255) and (210 <= g <= 220) and (40 <= b <= 45):  # Bright Yellow
                        pokefound = True
                        logger.debug("Found with bright yellow pixel...")
                        x = s
                        y = t
                    if (250 <= r <= 255) and (140 <= g <= 150) and (75 <= b <= 85):  # Orange
                        pokefound = True
                        logger.debug("Found with orange pixel...")
                        x = s
                        y = t
                if pokefound:
                    break
    return pokefound, x, y, r, g, b
