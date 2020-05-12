import inspect
from sc2.ids.unit_typeid import UnitTypeId


class TerranProductionManager():
    """
    - Basic production management for Terran
    """

    def __init__(self, bot=None):
        self.bot = bot

    async def manage_production(self):
        """
        - Manage basic production
        - Including training units and upgrade tech
        """

        await self.build_marines()
        await self.build_reapers()

    async def build_marines(self):
        if not self.bot.priority_manager.check_block(
            inspect.currentframe().f_code.co_name
        ):
            if self.bot.supply_left > 0:
                for barrack in self.bot.structures(UnitTypeId.BARRACKS).idle:
                    if self.bot.can_afford(UnitTypeId.MARINE):
                        barrack.build(UnitTypeId.MARINE)

    async def build_reapers(self):
        if not self.bot.priority_manager.check_block(
            inspect.currentframe().f_code.co_name
        ):
            if self.bot.supply_left > 0:
                for barrack in self.bot.structures(UnitTypeId.BARRACKS).idle:
                    if self.bot.can_afford(UnitTypeId.REAPER):
                        barrack.build(UnitTypeId.REAPER)
