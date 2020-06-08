from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId


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
        await self.manage_techlab_research()
        await self.manage_starpots_training()

    def check_available(self, type_id):
        if(
            self.bot.can_afford(type_id)
            and not self.bot.strategy_manager.check_block(type_id)
        ):
            return True
        else:
            return False

    async def manage_barracks_training(self):
        for b in self.bot.structures(UnitTypeId.BARRACKS).ready.idle:
            if self.check_available(UnitTypeId.REAPER):
                b.build(UnitTypeId.REAPER)
            elif self.check_available(UnitTypeId.MARAUDER):
                b.build(UnitTypeId.MARAUDER)
            elif self.check_available(UnitTypeId.MARINE):
                b.build(UnitTypeId.MARINE)

    async def manage_starpots_training(self):
        for s in self.bot.structures(UnitTypeId.STARPORT).ready.idle:
            if self.check_available(UnitTypeId.VIKINGFIGHTER):
                s.build(UnitTypeId.VIKINGFIGHTER)
            elif self.check_available(UnitTypeId.MEDIVAC):
                s.build(UnitTypeId.MEDIVAC)

    async def manage_techlab_research(self):
        if (
            self.bot.already_pending_upgrade(UpgradeId.STIMPACK) == 0
            and self.check_available(UpgradeId.STIMPACK)
        ):
            self.bot.research(UpgradeId.STIMPACK)
        if (
            self.bot.already_pending_upgrade(UpgradeId.SHIELDWALL) == 0
            and self.check_available(UpgradeId.SHIELDWALL)
        ):
            self.bot.research(UpgradeId.SHIELDWALL)
        if (
            self.bot.already_pending_upgrade(UpgradeId.PUNISHERGRENADES) == 0
            and self.check_available(UpgradeId.PUNISHERGRENADES)
        ):
            self.bot.research(UpgradeId.PUNISHERGRENADES)
