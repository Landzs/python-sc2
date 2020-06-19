from collections.abc import Callable
from pyglet.media.buffered_logger import logger
import logging



class Phase():

    def __init__(
        self,
        phase_function=None,
        phase_number: int = None,
        phase_name  : str = None

    ):
        assert isinstance(phase_number, int)
        assert isinstance(phase_name, str)
        assert isinstance(phase_function, Callable)

        self.__phase_function = phase_function
        self.__number = phase_number
        self.__name = phase_name

    def get_number(self):
        return self.__number

    def get_name(self):
        return self.__name

    async def run_phase(self):
        return await self.__phase_function()


class TerranPhaseManager():
    """
    - Basic phase management for Terran
    """

    def __init__(self, bot=None):

        self.__phase_list = {}
        self.__current_phase_number = 1

    def add_phase(self, phase_list):
        assert all(isinstance(phase, Phase) for phase in phase_list)
        for p in phase_list:
            self.__phase_list[p.get_number()] = p
            logging.info(f"Add Phase {p.get_number()} : {p.get_name()}")

    async def run_current_phase(self):
        assert self.__current_phase_number in self.__phase_list
        current_phase = self.__phase_list[self.__current_phase_number]
        return await current_phase.run_phase()

    def go_next_phase(self):
        self.__current_phase_number += 1
        logging.info(f"Move to next phase : {self.__current_phase_number}")

    def switch_to_phase(self, phase_id):
        old_phase_number = self.__current_phase_number
        self.__current_phase_number = phase_id
        logging.info(f"Swtich phase from {old_phase_number} to {phase_id}")

    async def manage_phases(self):
        phase_result = await self.run_current_phase()
        if phase_result:
            self.go_next_phase()
