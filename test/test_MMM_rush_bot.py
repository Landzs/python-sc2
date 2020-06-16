from subprocess import check_output
import random
from os.path import isfile, join
from bot.worker_rush import WorkerRushBot
from bot.MMM import MMMBot
import sc2
import os
import pytest
import logging
from os import listdir
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer

logger = logging.getLogger(__name__)


def get_maps():
    map_dir = r"C:\Software\Blizzard App\Blizzard Games\StarCraft II\Maps"
    maps = [map for map in listdir(map_dir) if isfile(join(map_dir, map))]
    maps = [os.path.splitext(map)[0] for map in maps]
    return maps


def vs_computer(caplog, race, bot, computer_race):
    maps = get_maps()
    win = 0
    game = 0
    for m in maps:
        result = sc2.run_game(
            sc2.maps.get(m),
            [
                Bot(Race.Terran, bot()),
                Computer(computer_race, Difficulty.VeryHard)
            ],
            realtime=False
        )
        game += 1
        for rec in caplog.records:
            if "AI step threw an error" in rec.msg:
                raise RuntimeError("Erroneous behavior logged in a")

        print(f"result = {result !r}")
        assert result in [
            sc2.Result.Victory,
            sc2.Result.Defeat,
            sc2.Result.Tie
        ]
        if result == sc2.Result.Victory:
            win += 1
    win_rate = win / game
    assert win_rate > 0.9, "Win rate againts computer: {}".format(win_rate)
    print("Win rate againts computer: {}".format(win_rate))


def vs_bot(caplog, bot, opponent):
    maps = get_maps()
    for m in maps:
        command = "python test\\run_game.py"
        command += " -m " + m
        command += " -b " + bot
        command += " -o " + opponent
        output = str(check_output(command.split(" "), timeout=1200))
        start = r"Result for player 1 - Bot "
        start += bot + "(Terran): "
        end = r"\r"
        result = (output.split(start))[1].split(end)[0]
        assert result == "Victory" , "Output is {}".format(output)


def test_vs_worker_rush_bot(caplog):
    vs_bot(caplog, "MMMBot", "WorkerRushBot")


def test_vs_expand_bot(caplog):
    vs_bot(caplog, "MMMBot", "ExpandBot")


def test_vs_protoss_computer(caplog):
    vs_computer(caplog, Race.Terran, MMMBot, Race.Protoss)


def test_vs_terran_computer(caplog):
    vs_computer(caplog, Race.Terran, MMMBot, Race.Terran)


def test_vs_zerg_computer(caplog):
    vs_computer(caplog, Race.Terran, MMMBot, Race.Zerg)
