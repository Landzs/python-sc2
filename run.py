import sc2
import sys
from __init__ import run_ladder_game
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer

import os
from os import listdir
from os.path import isfile, join
import random

# Load bot
from bot.reaper_rush import ReaperRushBot

bot = Bot(Race.Terran, ReaperRushBot())


def get_map():
    map_dir = r"C:\Software\Blizzard App\Blizzard Games\StarCraft II\Maps"
    maps = [map for map in listdir(map_dir) if isfile(join(map_dir, map))]
    maps = [os.path.splitext(map)[0] for map in maps]
    return random.choice(maps)


# Start game
if __name__ == "__main__":
    if "--LadderServer" in sys.argv:
        # Ladder game started by LadderManager
        print("Starting ladder game...")
        result, opponentid = run_ladder_game(bot)
        print(result, " against opponent ", opponentid)
    else:
        # Local game
        print("Starting local game...")
        map = get_map()
        sc2.run_game(
            sc2.maps.get(map),
            [
                bot, Computer(
                    Race.Zerg,
                    Difficulty.Easy
                )
            ],
            realtime=True
        )
