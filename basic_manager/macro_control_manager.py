from sc2.ids.unit_typeid import UnitTypeId


class TerranMacroControlManager():
    """
    - Basic macro unit control management for Terran
    """

    def __init__(self, bot=None):
        self.bot            = bot
        self.attack_target  = self.bot.enemy_start_locations[0]
        self.amount_marines = 15
        self.amount_reapers = 5

    async def manage_macro_control(self):
        """
        - Manage macro unit control management, call in on_step
        - Including when and where to attack for different units
        """
        await self.marines_attack()
        await self.reapers_attack()

    async def marines_attack(self):
        marines = self.bot.units(UnitTypeId.MARINE).idle
        if marines.amount  > self.amount_marines:
            target = self.bot.enemy_structures.random_or(
                self.attack_target).position
            for marine in marines:
                marine.attack(target)

    async def reapers_attack(self):
        reapers = self.bot.units(UnitTypeId.REAPER).idle
        if reapers.amount > self.amount_reapers:
            target = self.bot.enemy_structures.random_or(
                self.attack_target).position
            for reaper in reapers:
                reaper.attack(target)
