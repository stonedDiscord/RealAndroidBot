import asyncio
import logging
import time
import datetime
import sys

from utils import get_id_from_names, Unknown

class MADClass:
    def __init__(self):
        self.nearby_count = 0
        self.current_index = 0

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
    
    async def pokemon_encountered(self, p, d, pokemon):
        if d(resourceId='com.mad.pogoenhancer:id/custom_toast_message', packageName='com.mad.pogoenhancer').exists:
            pokemon.update_stats_from_mad(p,d) 
            return True
        else:
            return False