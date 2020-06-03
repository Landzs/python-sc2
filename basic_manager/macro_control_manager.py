from sc2.units import Units
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
import numpy as np
from random import randint


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
        self.standby_position = (0, 0)
        self.attack_target    = (0, 0)
        self.searched_area    = np.array(bool)

        self.no_enemy_building_detected = False
        self.start_searching_phase      = False

    async def manage_macro_control(self):
        """
        - Manage macro unit control management, call in on_step
        - Including when and where to attack for different units
        """

        await self.enemies_monitor()
        await self.workers_control()
        await self.marines_control()
        await self.reapers_control()
        await self.search()

    def initialize(self):
        """
        - Initialize macro unit control paramenters
        - Need map info so should be called once in on_step
        """

        if self.attack_target == (0, 0):
            self.attack_target = self.bot.enemy_start_locations[0]
        x = self.bot._game_info.playable_area.x
        x += self.bot.game_info.playable_area.width
        y = self.bot._game_info.playable_area.y
        y += self.bot.game_info.playable_area.height
        self.searched_area = np.full((x + 1, y + 1), False)

    async def enemies_monitor(self):
        """
        - Monitor enemies' locations
        - Including worker rush detection and no enemy building 
        remain  detection
        """

        enemies_units      = self.bot.all_enemy_units
        enemies_structures = self.bot.enemy_structures
        enemies = enemies_units | enemies_structures
        enemies_no_flying = enemies_units.not_flying
        enemies_no_flying |= enemies_structures.not_flying

        own_units          = self.bot.units
        townhalls          = self.bot.townhalls

        closest_distance = 1000
        if (
            enemies_units
            and townhalls
        ):
            closest_distance = enemies_units.closest_distance_to(townhalls[0])

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

        # check if there is enemy building detected in enemy start location
        if own_units:
            if (
                own_units.closest_distance_to(self.attack_target) < 5
                and not enemies_no_flying
            ):
                self.start_searching_phase = True
                if not enemies:
                    self.no_enemy_building_detected = True

            if (
                self.no_enemy_building_detected
                and (
                    enemies_structures
                    or enemies_units
                )
            ):
                self.no_enemy_building_detected = False
                if enemies_units:
                    self.attack_target = enemies_units[0].position
                else:
                    self.attack_target = enemies_structures[0].position

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
            if self.bot.in_pathing_grid(self.attack_target):
                [m.attack(self.attack_target) for m in marines]

    async def reapers_control(self):
        reapers = self.bot.units(UnitTypeId.REAPER).idle.filter(
            lambda r: r.health_percentage > 4 / 5
        )
        if reapers.amount >= self.unit_attack_amount[UnitTypeId.REAPER]:
            self.reapers += reapers
            if self.bot.in_pathing_grid(self.attack_target):
                [r.attack(self.attack_target) for r in reapers]

    async def search(self):
        if self.no_enemy_building_detected:
            own_units = self.bot.units
            min_x = self.bot.game_info.playable_area.x
            max_x = self.bot.game_info.playable_area.x
            max_x += self.bot.game_info.playable_area.width
            min_y = self.bot.game_info.playable_area.y
            max_y = self.bot.game_info.playable_area.y
            max_y += self.bot.game_info.playable_area.height
            for u in own_units.filter(
                lambda u:
                    not u.is_attacking
                    and u not in self.bot.workers
                    and u not in self.bot.units(UnitTypeId.MULE)
            ):
                p : Point2 = Point2((0, 0))
                times = 0
                while (
                    not self.bot.in_map_bounds(p)
                    or self.searched_area[p.x][p.y]
                    and times <= 10
                    or (
                        not self.bot.in_pathing_grid(p)
                        and not u.is_flying
                    )
                ):
                    p = Point2((randint(min_x, max_x), randint(min_y, max_y)))
                    times += 1
                self.searched_area[p.x][p.y] = True
                u.attack(p)
