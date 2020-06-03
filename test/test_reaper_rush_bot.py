import sc2
import os
import pytest
from os import listdir
from sc2 import Race, Difficulty
from sc2.player import Bot, Computer

# Load bot
from bot.reaper_rush import ReaperRushBot
from bot.worker_rush import WorkerRushBot
from os.path import isfile, join
import random
from subprocess import check_output


def get_maps():
    map_dir = r"C:\Software\Blizzard App\Blizzard Games\StarCraft II\Maps"
    maps = [map for map in listdir(map_dir) if isfile(join(map_dir, map))]
    maps = [os.path.splitext(map)[0] for map in maps]
    return maps


def vs_computer(caplog, race, bot):
    maps = get_maps()
    for m in maps:
        result = sc2.run_game(
            sc2.maps.get(m),
            [
                Bot(Race.Terran, bot()),
                Computer(Race.Terran, Difficulty.VeryHard)
            ],
            realtime=False
        )

        for rec in caplog.records:
            if "AI step threw an error" in rec.msg:
                raise RuntimeError("Erroneous behavior logged in a")

        print(f"result = {result !r}")
        assert result in [
            sc2.Result.Victory,
            sc2.Result.Defeat,
            sc2.Result.Tie
        ]


def vs_bot(caplog, bot, opponent):
    maps = get_maps()
    for m in maps:
        command = "python test\\run_game.py"
        command += " -m " + m
        command += " -b " + bot
        command += " -o " + opponent
        result = str(check_output(command.split(" ")), timeout = 600)
        start = r"Result for player 1 - Bot "
        start += bot + "(Terran): "
        end = r"\r"
        result = (result.split(start))[1].split(end)[0]
        assert result == "Victory"


def test_vs_computer(caplog):
    vs_computer(caplog, Race.Terran, ReaperRushBot)


def test_vs_worker_rush_bot(caplog):
    vs_bot(caplog, "ReaperRushBot", "WorkerRushBot")


def test_vs_expand_bot(caplog):
    vs_bot(caplog, "ReaperRushBot", "ExpandBot")
