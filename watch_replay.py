import logging
from sc2 import run_replay
from sc2.observer_ai import ObserverAI


logger = logging.getLogger(__name__)


class ObserverBot(ObserverAI):
    """
    A replay bot that can run replays.
    Check sc2/observer_ai.py for more available functions
    """

    async def on_start(self):
        print("Replay on_start() was called")

    async def on_step(self, iteration: int):
        print(f"Replay iteration: {iteration}")


if __name__ == "__main__":
    my_observer_ai = ObserverBot()
    directory = r"C:\Software\Blizzard App\Blizzard Games\StarCraft II\Replays"
    replay_name = r"\235831_AdditionalPylons_Fire_TritonLE.SC2Replay"
    replay_path = directory + replay_name
    run_replay(my_observer_ai, replay_path=replay_path, realtime=False)
