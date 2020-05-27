from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId


class TerranMacroControlManager():
    """
    - Basic macro unit control management for Terran
    """

    def __init__(self, bot=None):
        self.bot                  = bot

        # worker rush defense parameters
        self.worker_rush_defense  = False
        self.worker_rush_detected = False

        # units
        self.SCVs   : Units       = []
        self.marines: Units       = []
        self.reapers: Units       = []
        self.unit_attack_amount   = {
            UnitTypeId.MARINE: 1,
            UnitTypeId.REAPER: 1,
        }
        self.worker_typeid        = [
            UnitTypeId.SCV,
            UnitTypeId.PROBE,
            UnitTypeId.DRONE
        ]

        # position parameters
        self.standby_position     = (0, 0)
        self.attack_target        = (0, 0)

    async def manage_macro_control(self):
        """
        - Manage macro unit control management, call in on_step
        - Including when and where to attack for different units
        """

        await self.enemies_monitor()
        await self.workers_control()
        await self.marines_control()
        await self.reapers_control()

    def initialize(self):
        """
        - Initialize macro unit control paramenters
        - Need map info so should be called once in on_step
        """

        if self.attack_target == (0, 0):
            self.attack_target = self.bot.enemy_start_locations[0]

    async def enemies_monitor(self):
        enemies_units      = self.bot.all_enemy_units
        enemies_structures = self.bot.enemy_structures

        own_units          = self.bot.units
        townhalls          = self.bot.townhalls

        if (
            enemies_units
            and townhalls
        ):
            closest_enemies = enemies_units.closest_to(townhalls[-1])
            closest_distance = min(
                [enemies_units.closest_distance_to(t)for t in townhalls]
            )
        else:
            closest_distance = 1000

        # check if worker rush
        if (
            enemies_units
            and closest_distance < 90
            and all(e.type_id in self.worker_typeid for e in enemies_units)
            and all(o.type_id in self.worker_typeid for o in own_units)
            and len(enemies_units) >= 3
        ):
            self.worker_rush_detected = True
            if closest_distance < 20:
                self.worker_rush_defense = True

        if (
            self.worker_rush_defense
            and closest_distance >= 20
            and townhalls
        ):
            [s.move(townhalls[-1].position) for s in self.SCVs]

        if (
            self.worker_rush_defense
            and closest_distance >= 40
        ):
            self.worker_rush_defense = False
            self.SCVs = []

    async def workers_control(self):
        if self.worker_rush_defense:
            SCVs = self.bot.units(UnitTypeId.SCV).collecting
            SCVs |= self.bot.units(UnitTypeId.SCV).idle
            self.SCVs += SCVs
            [s.attack(self.attack_target) for s in SCVs]

    async def marines_control(self):
        marines = self.bot.units(UnitTypeId.MARINE).idle
        if marines.amount >= self.unit_attack_amount[UnitTypeId.MARINE]:
            self.marines += marines
            [m.attack(self.attack_target) for m in marines]

    async def reapers_control(self):
        reapers = self.bot.units(UnitTypeId.REAPER).idle.filter(
            lambda r: r.health_percentage > 4 / 5
        )
        if reapers.amount >= self.unit_attack_amount[UnitTypeId.REAPER]:
            self.reapers += reapers
            [r.attack(self.attack_target) for r in reapers]
