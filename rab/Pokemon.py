import logging
import sys

from PokemonUtils import get_stats_from_pokemod, get_stats_from_catch_screen, get_stats_from_mon_details, \
    get_stats_from_polygon, get_stats_from_text, check_pm_gender, level_from_cp, \
    cp_from_level, get_stats_from_mon
from PvpUtils import get_pvp_info
from names import POKEMON
from utils import get_id_from_names, Unknown

from pathlib import Path

logger = logging.getLogger('rab')

class Pokemon(object):
    def __init__(self):
        self.type = None
        self.status = None
        self.dex = Unknown.TINY
        self.name = Unknown.SMALL
        self.form = Unknown.SMALL
        self.shiny = False
        self.iv = Unknown.TINY
        self.atk_iv = Unknown.TINY
        self.def_iv = Unknown.TINY
        self.sta_iv = Unknown.TINY
        self.cp = Unknown.TINY
        self.level = Unknown.TINY
        self.gender = Unknown.TINY
        self.pvp_info = {}
        self.screen_x = 0
        self.screen_y = 0
        self.latitude = 0
        self.longitude = 0

    def __dict__(self):
        return dict({
            'type': self.type,
            'status': self.status,
            'dex': self.dex,
            'name': self.name,
            'form': self.form,
            'shiny': self.shiny,
            'iv': self.iv,
            'atk_iv': self.atk_iv,
            'def_iv': self.def_iv,
            'sta_iv': self.sta_iv,
            'cp': self.cp,
            'level': self.level,
            'gender': self.gender,
            'pvp_info': self.pvp_info,
            'screen_x': self.screen_x,
            'screen_y': self.screen_y,
            'latitude': self.latitude,
            'longitude': self.longitude
        })

    def update_stats_from_polygon(self, data):
        poke_stats = get_stats_from_polygon(data)
        dict_old = self.__dict__()
        if Unknown.is_not(poke_stats.get('name', Unknown.SMALL)):
            self.name = poke_stats.get('name', Unknown.SMALL)
            self.dex = get_id_from_names(self.name)
        if Unknown.is_not(poke_stats.get('form', Unknown.SMALL)):
            self.form = poke_stats.get('form', Unknown.SMALL)
        if not self.shiny:
            self.shiny = poke_stats.get('shiny', False)
        if Unknown.is_not(poke_stats.get('cp', Unknown.TINY)):
            self.cp = poke_stats.get('cp', Unknown.TINY)
        if Unknown.is_not(poke_stats.get('atk_iv', Unknown.TINY)):
            self.atk_iv = poke_stats.get('atk_iv', Unknown.TINY)
        if Unknown.is_not(poke_stats.get('def_iv', Unknown.TINY)):
            self.def_iv = poke_stats.get('def_iv', Unknown.TINY)
        if Unknown.is_not(poke_stats.get('sta_iv', Unknown.TINY)):
            self.sta_iv = poke_stats.get('sta_iv', Unknown.TINY)
        if Unknown.is_not(poke_stats.get('level', Unknown.TINY)):
            self.level = poke_stats.get('level', Unknown.TINY)
        if Unknown.is_not(poke_stats.get('gender', Unknown.TINY)):
            self.gender = poke_stats.get('gender', Unknown.TINY)
        try:
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                self.iv = round((self.atk_iv + self.def_iv + self.sta_iv) * 100 / 45)
                if Unknown.is_not(self.dex):
                    level = self.level if Unknown.is_not(self.level) else 1.0
                    great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = \
                        get_pvp_info(self.dex, self.atk_iv, self.def_iv, self.sta_iv, level)
                    self.pvp_info = {
                        'GL': {
                            'dex': great_id,
                            'name': POKEMON[great_id],
                            'rating': great_rating,
                            'cp': great_cp,
                            'level': great_level
                        },
                        'UL': {
                            'dex': ultra_id,
                            'name': POKEMON[great_id],
                            'rating': ultra_rating,
                            'cp': ultra_cp,
                            'level': ultra_level
                        }
                    }
        except:
            logger.error('Error Getting PVP Stats: {}'.format(poke_stats))
            pass
        if self.__dict__() != dict_old:
            logger.info(self.__dict__())
        else:
            logger.debug('No extra info was extracted.')

    def update_stats_from_pokemod(self, im):
        try:
            poke_stats = get_stats_from_pokemod(im)
            dict_old = self.__dict__()
            if Unknown.is_not(poke_stats.get('name', Unknown.SMALL)):
                self.name = poke_stats.get('name', Unknown.SMALL)
                self.dex = get_id_from_names(self.name)
            if not self.shiny:
                self.shiny = poke_stats.get('shiny', False)
            if Unknown.is_not(poke_stats.get('cp', Unknown.TINY)):
                self.cp = poke_stats.get('cp', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('atk_iv', Unknown.TINY)):
                self.atk_iv = poke_stats.get('atk_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('def_iv', Unknown.TINY)):
                self.def_iv = poke_stats.get('def_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('sta_iv', Unknown.TINY)):
                self.sta_iv = poke_stats.get('sta_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('level', Unknown.TINY)):
                self.level = poke_stats.get('level', Unknown.TINY)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                self.iv = round((self.atk_iv + self.def_iv + self.sta_iv) * 100 / 45)
                if Unknown.is_not(self.dex):
                    level = self.level if Unknown.is_not(self.level) else 1.0
                    great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = \
                        get_pvp_info(self.dex, self.atk_iv, self.def_iv, self.sta_iv, level)
                    self.pvp_info = {
                        'GL': {
                            'dex': great_id,
                            'name': POKEMON[great_id],
                            'rating': great_rating,
                            'cp': great_cp,
                            'level': great_level
                        },
                        'UL': {
                            'dex': ultra_id,
                            'name': POKEMON[great_id],
                            'rating': ultra_rating,
                            'cp': ultra_cp,
                            'level': ultra_level
                        }
                    }

            if Unknown.is_not(self.dex) and Unknown.is_not(self.cp) and Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_(self.level):
                logger.info('Unknown Level. Attempt to retrieve it from known values...')
                poke_level = level_from_cp(self.dex, self.cp, self.atk_iv, self.def_iv, self.sta_iv)
                if poke_level:
                    self.level = poke_level

            if self.__dict__() != dict_old:
                if Unknown.is_not(poke_stats.get('gender', Unknown.TINY)):
                    self.gender = poke_stats.get('gender', Unknown.TINY)
                logger.info(self.__dict__())
            else:
                logger.debug('No extra info was extracted.')
        except:
            pass

    def update_stats_from_catch_screen(self, im):
        try:
            poke_stats = get_stats_from_catch_screen(im)
            dict_old = self.__dict__()
            if Unknown.is_not(poke_stats.get('name', Unknown.SMALL)):
                self.name = poke_stats.get('name', Unknown.SMALL)
                self.dex = get_id_from_names(self.name)
            if not self.shiny:
                self.shiny = poke_stats.get('shiny', False)
            if Unknown.is_not(poke_stats.get('atk_iv', Unknown.TINY)):
                self.atk_iv = poke_stats.get('atk_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('def_iv', Unknown.TINY)):
                self.def_iv = poke_stats.get('def_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('sta_iv', Unknown.TINY)):
                self.sta_iv = poke_stats.get('sta_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('level', Unknown.TINY)):
                self.level = poke_stats.get('level', Unknown.TINY)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_not(self.level) and Unknown.is_(self.cp) and Unknown.is_not(self.dex):
                logger.info('CP is caculated value, might not be accurate')
                self.cp = cp_from_level(self.dex, self.level, self.atk_iv, self.def_iv, self.sta_iv)
            if Unknown.is_not(poke_stats.get('cp', Unknown.TINY)):
                self.cp = poke_stats.get('cp', Unknown.TINY)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                self.iv = round((self.atk_iv + self.def_iv + self.sta_iv) * 100 / 45)
                if Unknown.is_not(self.dex):
                    level = self.level if Unknown.is_not(self.level) else 1.0
                    great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = \
                        get_pvp_info(self.dex, self.atk_iv, self.def_iv, self.sta_iv, level)
                    self.pvp_info = {
                        'GL': {
                            'dex': great_id,
                            'name': POKEMON[great_id],
                            'rating': great_rating,
                            'cp': great_cp,
                            'level': great_level
                        },
                        'UL': {
                            'dex': ultra_id,
                            'name': POKEMON[great_id],
                            'rating': ultra_rating,
                            'cp': ultra_cp,
                            'level': ultra_level
                        }
                    }

            if Unknown.is_not(self.dex) and Unknown.is_not(self.cp) and Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_(self.level):
                logger.info('Unknown Level. Attempt to retrieve it from known values...')
                poke_level = level_from_cp(self.dex, self.cp, self.atk_iv, self.def_iv, self.sta_iv)
                if poke_level:
                    self.level = poke_level

            if self.__dict__() != dict_old:
                logger.info(self.__dict__())
            else:
                logger.debug('No extra info was extracted.')
        except Exception as e:
            logger.exception("Encounter unexpected error: {}".format(e))

    def get_stats_from_pgsharp(self, p, d, detail=True):
        # only works when nearby is enabled
        try:
            if detail:
                d(resourceId='me.underw.hp:id/hl_ec', packageName='com.nianticlabs.pokemongo').click()
            if Unknown.is_not(self.name):
                self.dex = get_id_from_names(self.name)
            else:
                if detail:
                    if d(resourceId='me.underw.hp:id/hl_ec_pvp_name', packageName='com.nianticlabs.pokemongo').exists:
                        self.name = d(resourceId='me.underw.hp:id/hl_ec_pvp_name', packageName='com.nianticlabs.pokemongo').child(
                            packageName='com.nianticlabs.pokemongo')[0].info.get('text', '')
                        self.dex = get_id_from_names(self.name)
            self.level = int(d(resourceId='me.underw.hp:id/hl_ec_sum_lvv',
                             packageName='com.nianticlabs.pokemongo').info.get('text', '0').replace('½', '.5'))
            raw_iv = d(resourceId='me.underw.hp:id/hl_ec_sum_ads',
                       packageName='com.nianticlabs.pokemongo').info.get('text', '0/0/0')
            raw_iv_list = raw_iv.split('/')
            self.iv = int(d(resourceId='me.underw.hp:id/hl_ec_sum_ivv',
                          packageName='com.nianticlabs.pokemongo').info.get('text', '0'))
            self.atk_iv = int(raw_iv_list[0])
            self.def_iv = int(raw_iv_list[1])
            self.sta_iv = int(raw_iv_list[2])
            if d(resourceId='me.underw.hp:id/hl_ec_sum_shiny', packageName='com.nianticlabs.pokemongo').exists:
                self.shiny = True
            if detail:
                if d(resourceId='me.underw.hp:id/hl_ec_detail_gender', packageName='com.nianticlabs.pokemongo').exists:
                    gender = d(resourceId='me.underw.hp:id/hl_ec_detail_gender',
                               packageName='com.nianticlabs.pokemongo').info.get('text', '').strip()
                    self.gender = check_pm_gender(gender)
                d(resourceId='me.underw.hp:id/hl_ec', packageName='com.nianticlabs.pokemongo').click()
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                if Unknown.is_not(self.dex):
                    level = self.level if Unknown.is_not(self.level) else 1.0
                    great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = \
                        get_pvp_info(self.dex, self.atk_iv, self.def_iv, self.sta_iv, level)
                    self.pvp_info = {
                        'GL': {
                            'dex': great_id,
                            'name': POKEMON[great_id],
                            'rating': great_rating,
                            'cp': great_cp,
                            'level': great_level
                        },
                        'UL': {
                            'dex': ultra_id,
                            'name': POKEMON[great_id],
                            'rating': ultra_rating,
                            'cp': ultra_cp,
                            'level': ultra_level
                        }
                    }
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_not(self.level) and Unknown.is_(self.cp) and Unknown.is_not(self.dex):
                logger.info('CP is caculated value, might not be accurate')
                self.cp = cp_from_level(self.dex, self.level, self.atk_iv, self.def_iv, self.sta_iv)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_not(self.level):
                logger.info(self.__dict__())
        except Exception as e:
            logger.exception("PGSharp get stats error: {}".format(e))
            pass

    def update_stats_from_pokemod_toast(self, p, d):
        try:
            raw_info = d.toast.get_message(2.0, 5.0, "")
            poke_stats = get_stats_from_text(raw_info)
            logger.debug(f'{raw_info}')
            logger.debug(f'{poke_stats}')
            dict_old = self.__dict__()
            if Unknown.is_not(poke_stats.get('name', Unknown.SMALL)):
                self.name = poke_stats.get('name', Unknown.SMALL)
                self.dex = get_id_from_names(self.name)
            if Unknown.is_not(poke_stats.get('cp', Unknown.TINY)):
                self.cp = poke_stats.get('cp', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('atk_iv', Unknown.TINY)):
                self.atk_iv = poke_stats.get('atk_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('def_iv', Unknown.TINY)):
                self.def_iv = poke_stats.get('def_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('sta_iv', Unknown.TINY)):
                self.sta_iv = poke_stats.get('sta_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('level', Unknown.TINY)):
                self.level = poke_stats.get('level', Unknown.TINY)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                self.iv = round((self.atk_iv + self.def_iv + self.sta_iv) * 100 / 45)
            if Unknown.is_not(poke_stats.get('gender', Unknown.TINY)):
                self.gender = poke_stats.get('gender', Unknown.TINY)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_not(self.level) and Unknown.is_(poke_stats.get('cp', Unknown.TINY)):
                logger.info('CP is caculated value, might not be accurate')
                self.cp = cp_from_level(self.dex, self.level, self.atk_iv, self.def_iv, self.sta_iv)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                if Unknown.is_not(self.dex):
                    level = self.level if Unknown.is_not(self.level) else 1.0
                    great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = \
                        get_pvp_info(self.dex, self.atk_iv, self.def_iv, self.sta_iv, level)
                    self.pvp_info = {
                        'GL': {
                            'dex': great_id,
                            'name': POKEMON[great_id],
                            'rating': great_rating,
                            'cp': great_cp,
                            'level': great_level
                        },
                        'UL': {
                            'dex': ultra_id,
                            'name': POKEMON[great_id],
                            'rating': ultra_rating,
                            'cp': ultra_cp,
                            'level': ultra_level
                        }
                    }
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_not(self.level):
                logger.info(self.__dict__())
            if self.__dict__() != dict_old:
                logger.debug(self.__dict__())
            else:
                logger.debug('No extra info was extracted.')
        except Exception as e:
            logger.exception("Encounter unexpected error: {}".format(e))
            pass

    def update_stats_from_mad(self, p, d):
        try:
            if d(resourceId='com.mad.pogoenhancer:id/custom_toast_message', packageName='com.mad.pogoenhancer').exists:
                raw_info = d(resourceId='com.mad.pogoenhancer:id/custom_toast_message',
                             packageName='com.mad.pogoenhancer').info.get('text', {})
                poke_stats = get_stats_from_text(raw_info)
                if Unknown.is_not(poke_stats.get('atk_iv', Unknown.TINY)):
                    self.atk_iv = poke_stats.get('atk_iv', Unknown.TINY)
                if Unknown.is_not(poke_stats.get('def_iv', Unknown.TINY)):
                    self.def_iv = poke_stats.get('def_iv', Unknown.TINY)
                if Unknown.is_not(poke_stats.get('sta_iv', Unknown.TINY)):
                    self.sta_iv = poke_stats.get('sta_iv', Unknown.TINY)
                if Unknown.is_not(poke_stats.get('level', Unknown.TINY)):
                    self.level = poke_stats.get('level', Unknown.TINY)
                if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                    self.iv = round((self.atk_iv + self.def_iv + self.sta_iv) * 100 / 45)
                if Unknown.is_not(poke_stats.get('gender', Unknown.TINY)):
                    self.gender = poke_stats.get('gender', Unknown.TINY)
                return True
            else:
                return False
        except Exception as e:
            logger.exception("Encounter unexpected error: {}".format(e))
            return False

    def update_stats_from_mon_page(self, im):
        try:
            poke_stats = get_stats_from_mon(im)
            dict_old = self.__dict__()
            if Unknown.is_not(poke_stats.get('name', Unknown.SMALL)):
                self.name = poke_stats.get('name', Unknown.SMALL)
                self.dex = get_id_from_names(self.name)
            if Unknown.is_not(poke_stats.get('atk_iv', Unknown.TINY)):
                self.atk_iv = poke_stats.get('atk_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('def_iv', Unknown.TINY)):
                self.def_iv = poke_stats.get('def_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('sta_iv', Unknown.TINY)):
                self.sta_iv = poke_stats.get('sta_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('level', Unknown.TINY)):
                self.level = poke_stats.get('level', Unknown.TINY)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                self.iv = round((self.atk_iv + self.def_iv + self.sta_iv) * 100 / 45)
                if Unknown.is_not(self.dex):
                    level = self.level if Unknown.is_not(self.level) else 1.0
                    great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = \
                        get_pvp_info(self.dex, self.atk_iv, self.def_iv, self.sta_iv, level)
                    self.pvp_info = {
                        'GL': {
                            'dex': great_id,
                            'name': POKEMON[great_id],
                            'rating': great_rating,
                            'cp': great_cp,
                            'level': great_level
                        },
                        'UL': {
                            'dex': ultra_id,
                            'name': POKEMON[great_id],
                            'rating': ultra_rating,
                            'cp': ultra_cp,
                            'level': ultra_level
                        }
                    }

            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_not(self.level) and Unknown.is_(self.cp) and Unknown.is_not(self.dex):
                logger.info('CP is caculated value, might not be accurate')
                self.cp = cp_from_level(self.dex, self.level, self.atk_iv, self.def_iv, self.sta_iv)

            if Unknown.is_not(poke_stats.get('cp', Unknown.TINY)):
                self.cp = poke_stats.get('cp', Unknown.TINY)

            if self.__dict__() != dict_old:
                logger.info(self.__dict__())
            else:
                logger.debug('No extra info was extracted.')
        except Exception as e:
            logger.exception("Encounter unexpected error: {}".format(e))
            pass

    def update_stats_from_mon_details(self, im, offset=None):
        try:
            poke_stats = get_stats_from_mon_details(im, offset)
            dict_old = self.__dict__()
            if Unknown.is_not(poke_stats.get('name', Unknown.SMALL)):
                self.name = poke_stats.get('name', Unknown.SMALL)
                self.dex = get_id_from_names(self.name)
            if Unknown.is_not(poke_stats.get('cp', Unknown.TINY)):
                self.cp = poke_stats.get('cp', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('atk_iv', Unknown.TINY)):
                self.atk_iv = poke_stats.get('atk_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('def_iv', Unknown.TINY)):
                self.def_iv = poke_stats.get('def_iv', Unknown.TINY)
            if Unknown.is_not(poke_stats.get('sta_iv', Unknown.TINY)):
                self.sta_iv = poke_stats.get('sta_iv', Unknown.TINY)
            if Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv):
                self.iv = round((self.atk_iv + self.def_iv + self.sta_iv) * 100 / 45)
                if Unknown.is_not(self.dex):
                    level = self.level if Unknown.is_not(self.level) else 1.0
                    great_rating, great_id, great_cp, great_level, ultra_rating, ultra_id, ultra_cp, ultra_level = \
                        get_pvp_info(self.dex, self.atk_iv, self.def_iv, self.sta_iv, level)
                    self.pvp_info = {
                        'GL': {
                            'dex': great_id,
                            'name': POKEMON[great_id],
                            'rating': great_rating,
                            'cp': great_cp,
                            'level': great_level
                        },
                        'UL': {
                            'dex': ultra_id,
                            'name': POKEMON[great_id],
                            'rating': ultra_rating,
                            'cp': ultra_cp,
                            'level': ultra_level
                        }
                    }

            if Unknown.is_not(self.dex) and Unknown.is_not(self.cp) and Unknown.is_not(self.atk_iv) and Unknown.is_not(self.def_iv) and Unknown.is_not(self.sta_iv) and Unknown.is_(self.level):
                logger.info('Unknown Level. Attempt to retrieve it from known values...')
                poke_level = level_from_cp(self.dex, self.cp, self.atk_iv, self.def_iv, self.sta_iv)
                if poke_level:
                    self.level = poke_level

            if self.__dict__() != dict_old:
                logger.info(self.__dict__())
            else:
                logger.debug('No extra info was extracted.')
        except Exception as e:
            logger.exception("Encounter unexpected error: {}".format(e))
            pass
