from sc2.ids.unit_typeid import UnitTypeId


class TerranMacroControlManager():
    """
    - Basic macro unit control management for Terran
    """

    def __init__(self, bot=None):
        self.bot            = bot
        self.marines        = []
        self.reapers        = []
        self.attack_target  = (0, 0)
        self.amount_marines = 15
        self.amount_reapers = 1

    async def manage_macro_control(self):
        """
        - Manage macro unit control management, call in on_step
        - Including when and where to attack for different units
        """

        await self.marines_attack()
        await self.reapers_attack()

    async def marines_attack(self):
        marines = self.bot.units(UnitTypeId.MARINE).idle
        if marines.amount >= self.amount_marines:
            self.marines += marines
            [m.attack(self.attack_target) for m in marines]

    async def reapers_attack(self):
        reapers = self.bot.units(UnitTypeId.REAPER).idle.filter(
            lambda r: r.health_percentage > 4 / 5
        )
        if reapers.amount >= self.amount_reapers:
            self.reapers += reapers
            [r.attack(self.attack_target) for r in reapers]
