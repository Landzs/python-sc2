import sc2
import sys
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer, Human

import os
from os import listdir
from os.path import isfile, join
import random

# Load bot
from bot.reaper_rush import ReaperRushBot
from bot.worker_rush import WorkerRushBot
from bot.expand_bot import ExpandBot
from bot.MMM import MMMBot
import getopt
bot = Bot(Race.Terran, ReaperRushBot())


def get_bot(bot_name):
    if bot_name == "ReaperRushBot":
        return Bot(Race.Terran, ReaperRushBot())
    elif bot_name == "WorkerRushBot":
        return Bot(Race.Protoss, WorkerRushBot())
    elif bot_name == "MMMBot":
        return Bot(Race.Terran, MMMBot())
    elif bot_name == "ExpandBot":
        return Bot(Race.Terran, ExpandBot())
    else:
        return None


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "m:b:o:")
    except getopt.GetoptError as err:
        sys.exit(2)

    map = "AcropolisLE"
    player1 = Bot(Race.Protoss, WorkerRushBot())
    player2 = Bot(Race.Protoss, WorkerRushBot())
    for o, a in opts:
        if o == "-m":
            map = a
        elif o == "-b":
            player1 = get_bot(a)
        elif o == "-o":
            player2 = get_bot(a)
        else:
            assert False, "unhandled option"

    sc2.run_game(
        sc2.maps.get(map),
        [
            player1,
            player2
            ],
        realtime=False
        )


if __name__ == "__main__":
    main()
