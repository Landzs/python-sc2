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

        await self.manage_barracks_training()

    def check_available(self, type_id):
        if(
            self.bot.supply_left > 0
            and self.bot.can_afford(type_id)
            and not self.bot.priority_manager.check_block(type_id)
        ):
            return True
        else:
            return False

    async def manage_barracks_training(self):
        for b in self.bot.structures(UnitTypeId.BARRACKS).idle:
            if self.check_available(UnitTypeId.REAPER):
                b.build(UnitTypeId.REAPER)
            elif self.check_available(UnitTypeId.MARINE):
                b.build(UnitTypeId.MARINE)
