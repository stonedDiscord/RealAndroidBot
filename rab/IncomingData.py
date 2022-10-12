import socket
import sys
import struct
import time
import logging
import threading
from datetime import datetime  # to be removed
from math import sqrt
from utils import calculate_cooldown, POKEMON

# using single file rpc
from rpc.Rpc_pb2 import GetMapObjectsOutProto as GetMapObjectsResponse
from rpc.Rpc_pb2 import EncounterOutProto as EncounterResponse
from rpc.Rpc_pb2 import IncenseEncounterOutProto as IncenseEncounterResponse
from rpc.Rpc_pb2 import GetHoloholoInventoryOutProto as GetHoloInventoryResponse
from rpc.Rpc_pb2 import InvasionEncounterOutProto as InvasionEncounterResponse
from rpc.Rpc_pb2 import CatchPokemonOutProto as CatchPokemonResponse
from rpc.Rpc_pb2 import StartIncidentOutProto as StartIncidentResponse
from rpc.Rpc_pb2 import FortDetailsOutProto as FortDetailsResponse
from rpc.Rpc_pb2 import GymGetInfoOutProto as GymGetInfoResponse
from rpc.Rpc_pb2 import GetHatchedEggsOutProto as GetHatchedEggsResponse
from rpc.Rpc_pb2 import GetPlayerOutProto as GetPlayerOutResponse
from rpc.Rpc_pb2 import GetNewQuestsOutProto as GetNewQuestsResponse
from rpc.Rpc_pb2 import GetIncensePokemonOutProto as GetIncensePokemonResponse
from rpc.Rpc_pb2 import FortSearchOutProto as FortSearchResponse
# Google protopuf
from google.protobuf.json_format import MessageToJson

import base64
import json
import s2sphere

logger = logging.getLogger('rab')

socket.setdefaulttimeout(150)
SOCKSIZE = 8192

# before i forget, let's do a simple one
# everytime got data, save it in global varible with timestamp
# main program simply check timestamp to confirm it's the latest data it need after an action


class LocalNetworkHandler(object):
    def __init__(self, host='0.0.0.0', port=5120):
        self.conn = None
        self.mode = 1  # 1 = catch mode, 0 = spin mode
        self.account_name = None
        self.level = None
        self.team = None
        self.last_lat = 0
        self.last_lng = 0
        self.lat = 0
        self.lng = 0
        self.wild = []
        self.encounter = []
        self.repeat_encounter = []
        self.catch = []
        self.hatched = []
        self.rejected = []
        self.rejected_chase = []
        self.incident = []
        self.fort = []  # This is to hold pokestop data
        self.hitPokestopCount = 0
        self.gym = []
        self.slotable_gym = []
        self.gym_sloted = []
        self.slot_gym = True
        self.items = {}  # in this format {'pokeball': 0, 'greatball': 0, 'ultraball':0, '}
        self.total_berries_count = 0
        self.total_ball_count = 0
        self.priorityList = []  # for main program to pick up priorities and teleport directly to catch
        self.perfectList = []  # for main program to pick up 100 IV and teleport directly to catch
        self.pokestop = []  # This is striped down gmo to have only pokestops locations, arranged by distance. Get new ones when empty
        self.pokestop_spin_result = []
        self.inventory_full = False
        self.pokemon_inventory_full = False
        self.incense_pokemon = []
        self.incense_pokemon_encounter = []
        self.chase_after_poke = []
        self.chase_after_poke_check = False
        self.temp_incense_encounter = []
        self.first_gmo = False
        self.End = b'\r\n'
        self.config = None

        socket_thread = threading.Thread(target=self.start_connection, name="IncomingData", args=(host, port, 'end'))
        socket_thread.daemon = True
        socket_thread.start()

    def decode_raw(self, data):
        raw_gmo = []
        raw_fort_search = []
        raw_encounters = []
        raw_invasion_encounters = []
        raw_fort_detail = []
        raw_trainer_data = []
        raw_catch_data = []
        raw_holo_inventory = []
        raw_gym_info = []
        raw_incident = []
        raw_hatched_eggs = []
        raw_incense_pokemon = []
        raw_incense_pokemon_encounter = []
        raw_new_quests = []

        # Things that need to check 900

        raw_content = data.get('payloads', [])
        for each_raw in raw_content:
            logger.debug('{}: Data Recieved on: {}'.format(each_raw.get('type'), datetime.now()))
            raw_data = each_raw.get('proto', '')
            if not self.account_name or self.account_name != each_raw.get('account_name'):
                self.account_name = each_raw.get('account_name')
            if not self.level or self.level != each_raw.get('level'):
                self.level = each_raw.get('level')
                logger.info('Player Level: {}\n'.format(self.level))

            self.lat = each_raw.get('lat')
            self.lng = each_raw.get('lng')

            if each_raw.get('type') == 2:
                raw_trainer_data.append(raw_data)
            elif each_raw.get('type') == 4:
                raw_holo_inventory.append(raw_data)
            elif each_raw.get('type') == 101:
                raw_fort_search.append(raw_data)
            elif each_raw.get('type') == 102:
                raw_encounters.append(raw_data)
            elif each_raw.get('type') == 103:
                raw_catch_data.append(raw_data)
            elif each_raw.get('type') == 104:
                raw_fort_detail.append(raw_data)
            elif each_raw.get('type') == 106:
                raw_gmo.append(raw_data)
            elif each_raw.get('type') == 126:
                raw_hatched_eggs.append(raw_data)
            elif each_raw.get('type') == 142:
                raw_incense_pokemon.append(raw_data)
            elif each_raw.get('type') == 143:
                raw_incense_pokemon_encounter.append(raw_data)
            elif each_raw.get('type') == 156:
                raw_gym_info.append(raw_data)
            elif each_raw.get('type') == 900:
                raw_new_quests.append(raw_data)
            elif each_raw.get('type') == 1024:
                raw_invasion_encounters.append(raw_data)
            elif each_raw.get('type') == 1200:
                raw_incident.append(raw_data)
            # else:
            #    print('Proto Type: {}\n'.format(each_raw.get('type')))

        # 2 GetPlayerOutResponse
        for each_player in raw_trainer_data:
            trainerData = GetPlayerOutResponse()
            data = base64.b64decode(each_player)

            try:
                trainerData.ParseFromString(data)
                trainer_json = json.loads(MessageToJson(trainerData))
            except:
                logger.error('Error in pharsing Player Data...')
                continue

            if not self.team or self.team != trainer_json['player'].get('team', 'NEUTRAL'):
                self.team = trainer_json['player'].get('team', 'NEUTRAL')
                logger.info('Player Team: {}\n'.format(self.team))
            logger.debug('Player Data: {}\n'.format(trainer_json))

        # 900 GetNewQuestsResponse
        for each_quest in raw_new_quests:
            questData = GetNewQuestsResponse()
            data = base64.b64decode(each_quest)

            try:
                questData.ParseFromString(data)
                quest_json = json.loads(MessageToJson(questData))
            except:
                logger.error('Error in pharsing Player Data...')
                continue

            logger.debug('Quest Data: {}\n'.format(quest_json))

        for fort_search in raw_fort_search:
            spinData = FortSearchResponse()
            data = base64.b64decode(fort_search)

            try:
                spinData.ParseFromString(data)
                spin_json = json.loads(MessageToJson(spinData))
            except:
                logger.error('Error in pharsing Spin Pokestop Data...')
                continue

            logger.debug('Spin Pokestop Data: {}\n'.format(spin_json))
            if spin_json.get('result', 'NO_RESULT_SET') == 'INVENTORY_FULL':
                self.inventory_full = True
            elif spin_json.get('result', 'NO_RESULT_SET') == 'SUCCESS':
                self.inventory_full = False

            self.pokestop_spin_result.append(spin_json)

        # 126 GetHatchedEggsResponse
        for hatched_egg in raw_hatched_eggs:
            hatchedEggData = GetHatchedEggsResponse()
            data = base64.b64decode(hatched_egg)

            try:
                hatchedEggData.ParseFromString(data)
                hatched_json = json.loads(MessageToJson(hatchedEggData))
            except:
                logger.error('Error in pharsing Get Hatched Egg...')
                continue
            if 'pokemon_id' in hatched_json:
                self.hatched.append(hatched_json)
                logger.info('Egg Hatched: {}\n'.format(hatched_json))  # Remember to change this back to debug

        # 142 GetIncensePokemonResponse
        for each_incense_pokemon in raw_incense_pokemon:
            incensePokemonData = GetIncensePokemonResponse()
            data = base64.b64decode(each_incense_pokemon)

            try:
                incensePokemonData.ParseFromString(data)
                incense_pokemon_json = json.loads(MessageToJson(incensePokemonData))
            except:
                logger.error('Error in pharsing Get Incense Pokemon...')
                continue
            # {'result': 'INCENSE_ENCOUNTER_AVAILABLE', 'pokemonTypeId': 'MILTANK', 'lat': 1.3038122631878932, 'lng': 103.83317396792022, 'encounterLocation': '31da198df7f', 'encounterId': '8342348775075069043', 'disappearTimeMs': '1615715649852', 'pokemonDisplay': {'gender': 'FEMALE', 'weatherBoostedCondition': 'PARTLY_CLOUDY', 'displayId': '8342348775075069043'}}
            if 'INCENSE_ENCOUNTER_AVAILABLE' in incense_pokemon_json.get('result', 'INCENSE_ENCOUNTER_UNKNOWN'):
                # Wild will include those from GMO
                if self.check_duplicate(self.incense_pokemon, 'encounterId', incense_pokemon_json.get('encounterId')) < 0:
                    # pass
                    cell = s2sphere.Cell(s2sphere.CellId.from_token(incense_pokemon_json.get('encounterLocation')))
                    centerpoint = s2sphere.LatLng.from_point(cell.get_center())
                    topleft = s2sphere.LatLng.from_point(cell.get_vertex(2))
                    incense_pokemon_json['latitude'] = topleft.lat().degrees
                    incense_pokemon_json['longitude'] = topleft.lng().degrees
                    self.incense_pokemon.append(incense_pokemon_json)
            logger.debug('Incense Pokemon: {}\n'.format(incense_pokemon_json))

        # 4 GetHoloInventoryResponse
        for inventory in raw_holo_inventory:
            poke_ball = 0
            great_ball = 0
            ultra_ball = 0

            inventoryData = GetHoloInventoryResponse()
            data = base64.b64decode(inventory)

            try:
                inventoryData.ParseFromString(data)
                inventory_data_json = json.loads(MessageToJson(inventoryData))
            except:
                logger.error('Error in pharsing Holo Inventory...')
                continue
            logger.debug('Item Detail: {}\n'.format(inventory_data_json))

            # Let see anything interesting from here, check if
            if 'inventoryItem' in inventory_data_json.get('inventoryDelta', ''):
                for eaInventoryItem in inventory_data_json['inventoryDelta'].get('inventoryItem', []):
                    if eaInventoryItem.get('inventoryItemData'):
                        if eaInventoryItem['inventoryItemData'].get('item'):
                            self.items[eaInventoryItem['inventoryItemData']['item'].get(
                                'itemId')] = eaInventoryItem['inventoryItemData']['item'].get('count', 0)

            # Every round of holo inventory, add up all the balls
            self.total_ball_count = self.items.get('ITEM_POKE_BALL', 0) + \
                self.items.get('ITEM_GREAT_BALL', 0) + self.items.get('ITEM_ULTRA_BALL', 0)

        # 104 Fort Details
        for fort_detail in raw_fort_detail:
            fortData = FortDetailsResponse()
            data = base64.b64decode(fort_detail)

            try:
                fortData.ParseFromString(data)
                fort_details_json = json.loads(MessageToJson(fortData))
            except:
                # data can't be parse, move on in loop
                logger.error('Error in parsing fort details data...')
                continue
            # Check not multiple entries
            if self.check_duplicate(self.fort, 'id', fort_details_json.get('id')) < 0:
                self.fort.append(fort_details_json)

            logger.debug('Fort Detail: {}\n'.format(fort_details_json))

        # 106 GMO
        # {'fortId': '16a81842b9c94a20ab156608157a71c1.16', 'lastModifiedMs': '1610164083824', 'latitude': 1.300738, 'longitude': 103.855647, 'enabled': True, 'fortType': 'CHECKPOINT', 'visited': True},
        # {'fortId': '240b492cb4b74345a738cafdd98a646f.11', 'lastModifiedMs': '1610164261333', 'latitude': 1.300833, 'longitude': 103.854444, 'enabled': True, 'fortType': 'CHECKPOINT', 'visited': True},

        for gmoData in raw_gmo:
            gmo = GetMapObjectsResponse()
            data = base64.b64decode(gmoData)

            try:
                gmo.ParseFromString(data)
                gmo_json = json.loads(MessageToJson(gmo))
            except:
                logger.error('Error in pharsing GMO...')
                continue

            if not self.pokestop and 'mapCell' in gmo_json:
                # Add only pokestops
                for mapcell in gmo_json['mapCell']:
                    if 'fort' in mapcell:
                        for fort in mapcell['fort']:
                            # Let's get all nearby pokestops
                            if 'fortType' in fort:
                                self.pokestop.append(fort)
                if self.pokestop:
                    self.sort_pokestops()
                # print('{}'.format(gmo_json))

            # Gym Detaisl: {'fortId': 'cb6496916fbe46cf9acc2affd9337872.16', 'lastModifiedMs': '1614308171030', 'latitude': 1.285035, 'longitude': 103.844354, 'team': 'TEAM_YELLOW', 'guardPokemonId': 'EXEGGUTOR', 'enabled': True, 'guardPokemonDisplay': {'gender': 'FEMALE', 'form': 'EXEGGUTOR_NORMAL'}, 'closed': True, 'gymDisplay': {'totalGymCp': 12988, 'lowestPokemonMotivation': 0.9982962012290955, 'slotsAvailable': 1, 'occupiedMillis': '88633'}, 'sameTeamDeployLockoutEndMs': '1614308538505'}
            if 'mapCell' in gmo_json:
                temp_pokestop = []
                # if not self.first_gmo:
                #    logger.info(f'First GMO: {gmo_json}')
                #    self.first_gmo = True
                for mapcell in gmo_json['mapCell']:
                    if 'fort' in mapcell:
                        for fort in mapcell['fort']:
                            # Let's get all nearby gyms
                            if 'fortType' not in fort:
                                if fort['gymDisplay'].get('slotsAvailable', 0) >= 1 and fort.get('team') == self.team and not fort.get('isInBattle', False) and self.config['client'].get('auto_slot', False):
                                    # check distance, if within 10 secs cooldown, add it
                                    default_CD = calculate_cooldown(self.last_lat,
                                                                    self.last_lng,
                                                                    fort.get('latitude'),
                                                                    fort.get('longitude'))
                                    if default_CD <= 60:  # let's only slot if it's within 60 sec reach
                                        # A few more checks before accepting it
                                        if 'raidInfo' in fort:
                                            if 'raidPokemon' in fort['raidInfo']:
                                                # Raid started, dont bother to slot this.
                                                continue
                                        if self.check_duplicate(self.gym_sloted, 'fortId', fort.get('fortId')) < 0:
                                            self.slotable_gym.append(fort)
                                            self.gym_sloted.append(fort)
                                            if len(self.gym_sloted) >= 20:
                                                self.gym_sloted.pop(0)
                                            logger.debug('Gym Detail: {}\n'.format(fort))
                            elif 'fortType' in fort:
                                # Store pokestop for later compare (assuming fort data ALWAYS come before pokemon data)
                                temp_pokestop.append(fort)

                    if 'wildPokemon' in mapcell:
                        for eachWildPoke in mapcell['wildPokemon']:
                            despawntime = eachWildPoke.get('timeTillHiddenMs', 999999)
                            if int(despawntime) >= 90000:
                                # Wild will include those from GMO
                                if self.check_duplicate(self.wild, 'encounterId', eachWildPoke.get('encounterId')) < 0:
                                    # Make sure it's not in rejected list
                                    if self.check_duplicate(self.rejected, 'encounterId', eachWildPoke.get('encounterId')) < 0:
                                        self.wild.append(eachWildPoke)

                    # This section handles chase after poke. User only wants to collect candies. automatic resume normal opertion if wanted pokemon not in nearby
                    if not self.chase_after_poke:
                        # Empty list, reset check
                        self.chase_after_poke_check = False

                    #{'pokedexNumber': 676, 'distanceMeters': 508.0328, 'encounterId': '17839549244592272445', 'fortId': '8517a1b4aa604691b4d0113472afaa6f.16', 'fortImageUrl': 'http://lh3.googleusercontent.com/ugz-WVfwvaYmyqtEF79318Bsk80AnCemP_vMYetu8x1ehPrnAh9aRUFfUxAlRoZl1DfXJaFqVvEEA2QCSuqqUvVT1REr', 'pokemonDisplay': {'gender': 'FEMALE', 'form': 'FURFROU_NATURAL', 'displayId': '-607194829117279171'}}

                    if 'nearbyPokemon' in mapcell and self.config['catch'].get('mon_to_chase', []) and not self.chase_after_poke:
                        for nearbyPoke in mapcell['nearbyPokemon']:
                            #encounter_id = int(nearbyPoke.get('encounterId'))
                            # if encounter_id < 0:
                            #    encounter_id = encounter_id + 2 ** 64
                            pokemon_name = POKEMON[nearbyPoke.get('pokedexNumber', 0)]
                            if self.check_if_in_list(self.config['catch'].get('mon_to_chase', []), pokemon_name):
                                # Make sure it's not in rejected list
                                if self.check_duplicate(self.rejected_chase, 'encounterId', nearbyPoke.get('encounterId')) < 0:
                                    self.chase_after_poke.append(nearbyPoke)

                # Logic: if chase_after_poke is not empty list and chase_after_poke_check is not True, search pokestop for lat and lon and add them to the dict
                if self.chase_after_poke and not self.chase_after_poke_check and temp_pokestop:
                    self.chase_after_poke_check = True
                    # Loop chase after poke list
                    i = 0
                    for each_nearby in self.chase_after_poke:
                        for each_pokestop in temp_pokestop:
                            if each_nearby.get('fortId') == each_pokestop.get('fortId'):
                                self.chase_after_poke[i]['latitude'] = each_pokestop.get('latitude')
                                self.chase_after_poke[i]['longitude'] = each_pokestop.get('longitude')
                                break  # go to next check
                        i += 1

                    logger.debug(f'List of pokemon to chase after: {self.chase_after_poke}')
                    logger.debug(f'List of pokestop: {temp_pokestop}')

        # 156 Gym Details
        for gym_detail in raw_gym_info:
            gymData = GymGetInfoResponse()
            data = base64.b64decode(gym_detail)

            try:
                gymData.ParseFromString(data)
                gym_details_json = json.loads(MessageToJson(gymData))
            except:
                logger.error('Error in parsing gym details data...')
                continue
            # Check not multiple entries
            if self.check_duplicate(self.gym, 'id', gym_details_json.get('id')) < 0:
                self.gym.append(gym_details_json)

            logger.debug('Gym Detail: {}\n'.format(gym_details_json))

        # 1024 Invasion Encounter
        for encounter in raw_invasion_encounters:
            encounterData = InvasionEncounterResponse()
            data = base64.b64decode(encounter)

            try:
                encounterData.ParseFromString(data)
                encounter_json = json.loads(MessageToJson(encounterData))
            except:
                logger.error('Error in parsing encounters...')
                continue

            # if encounter_json['pokemon'].get('pokemon'):
            #    if 'shiny' in encounter_json['pokemon']['pokemon'].get('pokemonDisplay'):
            #        print('\n\nSHINY FOUND')
            logger.debug('Invasion Encounter: {}\n'.format(encounter_json))

        # 102 Raw Encounter
        #  {'encounterId': '8936463579242595769', 'lastModifiedMs': '1610179747013', 'latitude': 1.286469496093757, 'longitude': 103.84821031734839, 'spawnPointId': '31da190bac3', 'pokemon': {'pokemonId': 'TEPIG', 'cp': 355, 'stamina': 82, 'maxStamina': 82, 'move1': 'EMBER_FAST', 'move2': 'BODY_SLAM', 'heightM': 0.44663072, 'weightKg': 7.4231, 'individualAttack': 2, 'individualDefense': 4, 'individualStamina': 3, 'cpMultiplier': 0.49985844, 'pokemonDisplay': {'gender': 'FEMALE', 'displayId': '8936463579242595769'}, 'originDetail': {}}, 'timeTillHiddenMs': 51663}
        # Self reminder, if got timeTillHiddenMs and >=15000 (15secs), add to front of list, less than that value don't add

        for incense_encounter in raw_incense_pokemon_encounter:
            incenseEncounterData = IncenseEncounterResponse()
            data = base64.b64decode(incense_encounter)

            try:
                incenseEncounterData.ParseFromString(data)
                encounter_json = json.loads(MessageToJson(incenseEncounterData))
            except:
                logger.error('Error in parsing encounters...')
                continue
            logger.debug('Incense Encounter Detail: {}\n'.format(encounter_json))
            if encounter_json.get('status', 'INCENSE_ENCOUNTER_UNKNOWN') == 'POKEMON_INVENTORY_FULL':
                self.pokemon_inventory_full = True
                logger.warning('Pokemon Inventory is Full')
            elif encounter_json.get('status', 'INCENSE_ENCOUNTER_UNKNOWN') == 'INCENSE_ENCOUNTER_SUCCESS':
                self.pokemon_inventory_full = False

            if self.check_duplicate(self.temp_incense_encounter, 'displayId', encounter_json['pokemon']['pokemonDisplay'].get('displayId')) < 0:
                self.temp_incense_encounter.append(encounter_json['pokemon'].get('pokemonDisplay'))
            else:
                self.incense_pokemon_encounter.append(encounter_json)
                self.temp_incense_encounter[:] = []

        for encounter in raw_encounters:
            encounterData = EncounterResponse()
            data = base64.b64decode(encounter)

            try:
                encounterData.ParseFromString(data)
                encounter_json = json.loads(MessageToJson(encounterData))
            except:
                logger.error('Error in parsing encounters...')
                continue
            logger.debug('Encounter Detail: {}\n'.format(encounter_json))
            if encounter_json.get('status', 'ENCOUNTER_ERROR') == 'POKEMON_INVENTORY_FULL':
                self.pokemon_inventory_full = True
                logger.warning('Pokemon Inventory is Full')
            elif encounter_json.get('status', 'ENCOUNTER_ERROR') == 'ENCOUNTER_SUCCESS':
                self.pokemon_inventory_full = False

            if encounter_json.get('pokemon'):
                if encounter_json['pokemon'].get('pokemon'):
                    despawntime = int(encounter_json['pokemon'].get('timeTillHiddenMs', 99999))

                    # Check not in wild
                    # Wild will include those from GMO
                    if self.check_duplicate(self.wild, 'encounterId', encounter_json['pokemon'].get('encounterId')) < 0:
                        if 'shiny' in encounter_json['pokemon']['pokemon'].get('pokemonDisplay'):
                            self.wild.insert(0, encounter_json.get('pokemon'))
                        else:
                            # Make sure it's not in rejected list
                            if self.check_duplicate(self.rejected, 'encounterId', encounter_json['pokemon'].get('encounterId')) < 0:
                                if despawntime >= 90000:
                                    self.wild.append(encounter_json.get('pokemon'))
                    else:
                        logger.debug('Encounter Detail: {}\n'.format(encounter_json.get('pokemon')))
                        encounterIndex = self.check_duplicate(
                            self.encounter, 'encounterId', encounter_json['pokemon'].get('encounterId'))
                        if encounterIndex < 0:
                            self.encounter.append(encounter_json.get('pokemon'))
                        else:
                            self.repeat_encounter.append(encounter_json.get('pokemon'))

                    if 'shiny' in encounter_json['pokemon']['pokemon'].get('pokemonDisplay') and self.config['catch'].get('go_after_shiny', True):
                        logger.debug('>>>> SHINY FOUND <<<<')
                        self.priorityList.append(encounter_json['pokemon'])
                        logger.info('Wild Count: {} | Encounter Count: {} SHINY {} at ({},{})'.format(len(self.wild), len(self.encounter), encounter_json['pokemon']['pokemon'].get(
                            'pokemonId'), encounter_json['pokemon'].get('latitude'), encounter_json['pokemon'].get('longitude')))
                        logger.debug('Wild Encounter: {}\n'.format(encounter_json.get('pokemon')))
                    elif encounter_json['pokemon']['pokemon'].get('individualAttack', 0) == 15 and encounter_json['pokemon']['pokemon'].get('individualDefense', 0) == 15 and encounter_json['pokemon']['pokemon'].get('individualStamina', 0) == 15 and self.config['catch'].get('go_after_100IV', True):
                        logger.debug('>>>> 100IV FOUND <<<<')
                        self.priorityList.append(encounter_json['pokemon'])
                        logger.info('Wild Count: {} | Encounter Count: {} 100IV {} at ({},{})'.format(len(self.wild), len(self.encounter), encounter_json['pokemon']['pokemon'].get(
                            'pokemonId'), encounter_json['pokemon'].get('latitude'), encounter_json['pokemon'].get('longitude')))
                        logger.debug('Wild Encounter: {}\n'.format(encounter_json.get('pokemon')))
                    else:
                        logger.info('Wild Count: {} | Encounter Count: {}'.format(len(self.wild), len(self.encounter)))

        # 103 Catch
        for raw_catch in raw_catch_data:
            catchData = CatchPokemonResponse()
            data = base64.b64decode(raw_catch)

            try:
                catchData.ParseFromString(data)
                catch_details_json = json.loads(MessageToJson(catchData))
            except:
                logger.error('Error in parsing catch...')
                continue
            # {'status': 'CATCH_SUCCESS', 'capturedPokemonId': '9366075914858421954', 'captureAward': {'activityType': ['ACTIVITY_CATCH_POKEMON', 'ACTIVITY_CATCH_CURVEBALL', 'ACTIVITY_CATCH_FIRST_THROW'], 'xp': [100, 10, 50], 'candy': [3, 0, 0], 'stardust': [100, 0, 0]}, 'captureReason': 'DEFAULT', 'displayPokedexId': 163, 'pokemonDisplay': {'gender': 'GENDERLESS'}}

            # {'status': 'CATCH_SUCCESS', 'capturedPokemonId': '1542421654208417548', 'captureAward': {'activityType': ['ACTIVITY_CATCH_POKEMON', 'ACTIVITY_CATCH_CURVEBALL', 'ACTIVITY_CATCH_FIRST_THROW'], 'xp': [100, 10, 50], 'candy': [3, 0, 0], 'stardust': [125, 0, 0]}, 'captureReason': 'DEFAULT', 'pokemonDisplay': {'gender': 'MALE', 'weatherBoostedCondition': 'RAINY'}}

            # Catch Result: {'status': 'CATCH_ESCAPE', 'missPercent': 0.03241342306137085, 'scores': {}}
            self.catch.append(catch_details_json)
            logger.debug('Catch Result: {}\n'.format(catch_details_json))

        # 1200 Incident Report
        for start_incident in raw_incident:
            rawIncidentData = StartIncidentResponse()
            data = base64.b64decode(start_incident)

            try:
                rawIncidentData.ParseFromString(data)
                start_incident_json = json.loads(MessageToJson(rawIncidentData))
            except:
                logger.error('Error in parsing Start Incident data...')
                continue

            if 'ERROR' not in start_incident_json.get('status'):
                self.incident.append(start_incident_json)
            logger.debug('Incident: {}\n'.format(start_incident_json))

    def sort_pokestops(self):
        logger.info('Sorting Pokestops, please wait...')
        for_sort = self.pokestop.copy()
        self.pokestop[:] = []
        x = self.lat
        y = self.lng

        while True:
            if len(for_sort) <= 0:
                break

            for_sort[:] = self.get_ordered_list(for_sort, x, y)
            x = for_sort[0].get('latitude')
            y = for_sort[0].get('longitude')
            self.pokestop.append(for_sort.pop(0))

        logger.info('Total Number of Pokestops: {}'.format(len(self.pokestop)))

    def get_ordered_list(self, coords, x, y):
        #global poke_spawn_points
        # {'fortId': '240b492cb4b74345a738cafdd98a646f.11', 'lastModifiedMs': '1610164261333', 'latitude': 1.300833, 'longitude': 103.854444, 'enabled': True, 'fortType': 'CHECKPOINT', 'visited': True},
        coords.sort(key=lambda p: sqrt((p.get('latitude') - x)**2 + (p.get('longitude') - y)**2))
        return coords

    def check_if_in_list(self, data_list, match_value, data_type='string'):
        for each_value in data_list:
            if data_type == 'string':
                if each_value.strip().replace(' ', '_').lower() == match_value.lower():
                    return True

        return False

    def check_duplicate(self, data_dict, match_key, match_value, key_name2=None):
        i = 0
        for each_dict in data_dict:
            if not key_name2:
                if each_dict.get(match_key) == match_value:
                    return i
            else:
                if each_dict.get(match_key):
                    if each_dict[match_key].get(key_name2) == match_value:
                        return i
            i += 1
        return -1

    def get_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except Exception:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP

    # assume a socket disconnect (data returned is empty string) means  all data was #done being sent.
    def recv_basic(self, the_socket):
        total_data = []
        while True:
            data = the_socket.recv(SOCKSIZE)
            if not data:
                break
            total_data.append(data)
        return b''.join(total_data)

    def recv_timeout(self, the_socket, timeout=2):
        the_socket.setblocking(0)
        total_data = []
        data = ''
        begin = time.time()
        while 1:
            # if you got some data, then break after wait sec
            if total_data and time.time()-begin > timeout:
                break
            # if you got no data at all, wait a little longer
            elif time.time()-begin > timeout*2:
                break
            try:
                data = the_socket.recv(SOCKSIZE)
                if data:
                    total_data.append(data)
                    begin = time.time()
                else:
                    time.sleep(0.1)
            except:
                pass
        return b''.join(total_data)

    def recv_end(self, the_socket):
        total_data = []
        data = ''
        while True:
            data = the_socket.recv(SOCKSIZE)
            if self.End in data:
                total_data.append(data[:data.find(self.End)])
                break
            total_data.append(data)
            if len(total_data) > 1:
                # check if end_of_data was split
                last_pair = total_data[-2]+total_data[-1]
                if self.End in last_pair:
                    total_data[-2] = last_pair[:last_pair.find(self.End)]
                    total_data.pop()
                    break
        return b''.join(total_data)

    def recv_size(self, the_socket):
        # data length is packed into 4 bytes
        total_len = 0
        total_data = []
        size = sys.maxint
        size_data = sock_data = ''
        recv_size = SOCKSIZE
        while total_len < size:
            sock_data = the_socket.recv(recv_size)
            if not total_data:
                if len(sock_data) > 4:
                    size_data += sock_data
                    size = struct.unpack('>i', size_data[:4])[0]
                    recv_size = size
                    if recv_size > 524288:
                        recv_size = 524288
                    total_data.append(size_data[4:])
                else:
                    size_data += sock_data
            else:
                total_data.append(sock_data)
            total_len = sum([len(i) for i in total_data])
        return b''.join(total_data)

    def start_connection(self, host, port, recv_type='end'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))

        mac_ip = self.get_ip()
        logger.info("Server {} started on port: {}".format(mac_ip, port))

        sock.listen(5)
        logger.info("Please wait... getting pokestops... \n")
        self.conn, address = sock.accept()
        while True:
            if recv_type == 'size':
                result = self.recv_size(self.conn)
            elif recv_type == 'end':
                result = self.recv_end(self.conn)
            elif recv_type == 'timeout':
                result = self.recv_timeout(self.conn)
            else:
                result = self.conn.recv(SOCKSIZE)
            try:
                self.decode_raw(json.loads(result.decode("utf-8")))
            except Exception as e:
                # Change exception to error for depolyment (so client wont see chuck of erros during exit)
                logger.error("Error Pharsing data: {}".format(e))
                continue  # Skip

    def close_connection(self):
        self.conn.close()
