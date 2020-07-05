import logging
from collections.abc import Callable


class Phase():

    def __init__(
        self,
        phase_name    : str      = None,
        phase_function: Callable = None,
    ):
        assert isinstance(phase_name, str)
        assert isinstance(phase_function, Callable)

        self.__phase_function = phase_function
        self.__name = phase_name

    @property
    def name(self):
        return self.__name

    async def run_phase(self):
        return await self.__phase_function()


class TerranPhaseManager():
    """
    - Basic phase management for Terran
    """

    def __init__(self, bot=None):
        self.__bot           = bot
        self.__phase_list    = {}
        self.__current_phase = None

    async def __run_current_phase(self):
        current_phase = self.__phase_list[self.__current_phase]
        return await current_phase.run_phase()

    def add_phase(self, phase_list):
        assert all(isinstance(phase, Phase) for phase in phase_list)

        for p in phase_list:
            self.__phase_list[p.name] = p
            logging.info(f"Add Phase : {p.name}")

    def switch_to_phase(self, phase):
        assert phase in self.__phase_list

        if phase == self.__current_phase:
            return

        time = self.__bot.time_formatted
        old_phase, self.__current_phase = self.__current_phase, phase

        if old_phase:
            logging.info(f"{time} Swtich phase from {old_phase} to {phase}")
        else:
            logging.info(f"{time} Start phase: {phase}")

    async def manage_phases(self):
        self.__bot.current_phase = self.__current_phase
        await self.__run_current_phase()

    @property
    def current_phase(self):
        return self.__current_phase
