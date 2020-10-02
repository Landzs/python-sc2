import numpy as np
from numpy import math
from random import randint
from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId


class TerranMacroControlManager():
    """
    - Basic macro unit control management for Terran
    """

    def __init__(self, bot=None):
        self.__bot = bot

        # SCV scout parameters
        self.__scout               = False
        self.__scout_SCV           = None
        self.__scout_SCV_got_order = False
        self.__scout_after         = None

        # repair structure parameters
        self.__repair_defense_structure = False
        self.__repair_SCVs              = Units([], self)
        self.__SCV_repair_range         = 30

        # attack parameter
        self.__no_enemy_structure_detected = False
        self.__supply_to_attack            = 150
        self.__supply_to_make              = 0

        # defense parameter
        self.__need_scan     = False
        self.__defense_range = 30
        self.__worker_rush_defense_range = 20

        # units
        self.__SCVs          = Units([], self)
        self.__attack_units  = Units([], self)
        self.__defense_units = Units([], self)

        self.__unit_attack_amount = {
            UnitTypeId.MARINE       : 100,
            UnitTypeId.REAPER       : 100,
            UnitTypeId.MARAUDER     : 100,
            UnitTypeId.VIKINGFIGHTER: 100
        }

        # position parameters
        self.__attack_target = Point2((0, 0))
        self.__searched_area = np.array(bool)

        # map parameters
        self.__map_min_x = 0
        self.__map_max_x = 0
        self.__map_min_y = 0
        self.__map_max_y = 0

    async def manage_macro_control(self):
        """
        - Manage macro unit control management, call in on_step
        - Including when and where to attack for different units
        """

        await self.__update_remain_enemy_position()
        await self.__defense_units_control()
        await self.__attack_units_control()
        await self.__SCVs_control()
        await self.__kill_own_unit()
        await self.__search_enemy()

    def initialize(self):
        """
        - Initialize macro unit control paramenters
        - Need map info so should be called in on_start
        """

        self.__attack_target = self.__bot.enemy_start_locations[0]
        self.__map_min_x     = self.__bot.game_info.playable_area.x
        self.__map_max_x     = self.__bot.game_info.playable_area.x + self.__bot.game_info.playable_area.width
        self.__map_min_y     = self.__bot.game_info.playable_area.y
        self.__map_max_y     = self.__bot.game_info.playable_area.y + self.__bot.game_info.playable_area.height
        self.__searched_area = np.full((self.__map_max_x + 1, self.__map_max_y + 1), False)

    async def __update_remain_enemy_position(self):
        """
        - Update remain enemy position as attack_target
        - Update no_enemy_structure_detected if no enemy structures remain detection
        """

        enemy_units      = self.__bot.enemy_units
        enemy_structures = self.__bot.enemy_structures
        all_enemy_units  = self.__bot.all_enemy_units

        # check if there is enemy building detected in attack target
        if self.__bot.units:
            if self.__bot.phase_manager.current_phase == "Search Enemies" and not all_enemy_units:
                self.__no_enemy_structure_detected = True

            if self.__no_enemy_structure_detected and all_enemy_units:
                self.__no_enemy_structure_detected = False
                self.__attack_target = enemy_units[0].position if enemy_units else enemy_structures[0].position

    async def __defense_units_control(self):
        closest_distance = self.__bot.enemy_unit_closest_distance

        # defense attack
        if closest_distance < self.__defense_range:
            for u in self.__bot.units.filter(
                lambda u:
                    u.distance_to(self.__bot.start_location) < self.__defense_range * 2
                    and u.type_id in self.__unit_attack_amount
            ):
                self.defense_units += u
        else:
            self.defense_units = Units([], self)

        # assemble idle troops
        if self.__supply_to_attack > self.__bot.supply_used and self.__bot.townhalls:
            new_townhall = self.__bot.townhalls.closest_to(self.__bot.resource_manager.newly_expanded_position)
            bunkers      = self.__bot.structures.filter(lambda s: s.type_id == UnitTypeId.BUNKER)

            for u in self.__bot.units.idle.filter(
                lambda u:
                    u.type_id in self.__unit_attack_amount
                    and u not in self.__attack_units
                    and u not in self.__defense_units
            ):
                # if there are bunkers, assemble to bunker
                if bunkers:
                    u.smart(bunkers[0])
                # if no bunkers, assemble to newly expanded base
                else:
                    u.move(new_townhall.position.towards(self.__bot.game_info.map_center, 6))

    async def __attack_units_control(self):
        for u in self.__bot.units.idle.filter(lambda u: u in self.__unit_attack_amount):
            if (
                self.__supply_to_attack <= self.__bot.supply_used
                or self.__unit_attack_amount[u.type_id] > self.__bot.units(u.type_id).amount
            ):
                # exclude reapers who is self healing
                if u.type_id != UnitTypeId.REAPER or u.health_percentage > 4 / 5:
                    self.__attack_units += u

                    #############
                    # no sure needed
                    # if (
                    #     self.__bot.in_pathing_grid(self.__attack_target)
                    #     and not self.__bot.enemy_structures
                    # ):
                        ####################
                    u.attack(self.__attack_target)

    async def __SCVs_control(self):
        if self.__bot.phase_manager.current_phase == "Defense Worker Rush" and self.__bot.townhalls:
            closest_distance = self.__bot.closest_distance
            if closest_distance < self.__worker_rush_defense_range:
                SCVs        = self.__bot.units(UnitTypeId.SCV).collecting | self.__bot.units(UnitTypeId.SCV).idle
                self.__SCVs += SCVs
                [s.attack(self.__attack_target) for s in SCVs]
            else:
                [s.move(self.__bot.townhalls[-1].position) for s in self.__SCVs]
                if closest_distance >= self.__worker_rush_defense_range * 2:
                    self.__SCVs = Units([], self)

        # if self.__bot.phase_manager.current_phase == "Defense Worker Rush" and self.closest_distance < 20:
        #     self.worker_rush_defense = True
        # if (
        #     self.worker_rush_defense
        #     and self.closest_distance >= 20
        #     and townhalls
        # ):
        #     [s.move(townhalls[-1].position) for s in self.__SCVs]

        # if (
        #     self.worker_rush_defense
        #     and self.closest_distance >= 40
        # ):
        #     self.worker_rush_defense = False
        #     self.__SCVs = []

        # if self.worker_rush_defense:
        #     SCVs = self.__bot.units(UnitTypeId.SCV).collecting
        #     SCVs |= self.__bot.units(UnitTypeId.SCV).idle
        #     self.__SCVs += SCVs
        #     [s.attack(self.__attack_target) for s in SCVs]

        if self.__scout_SCV and not self.__scout_SCV_got_order:
            length = 12.0
            point  = self.__bot.enemy_start_locations[0]
            for a in range(0, 180, 30):
                point   = self.__bot.enemy_start_locations[0]
                offset  = Point2((length * math.cos(a), length * math.sin(a)))
                point   += offset
                if self.__bot.in_pathing_grid(point):
                    self.__scout_SCV.move(point, queue=True)
            self.__scout_SCV_got_order = True

        for s in self.__bot.structures.ready.filter(lambda s: s.health_percentage < 1):
            for w in self.__repair_SCVs.filter(
                lambda w:
                    not w.is_repairing
                    and not w.is_moving
                    and w.distance_to(s) < self.__SCV_repair_range
            ):
                w.repair(s)

    async def __kill_own_unit(self):
        if self.__supply_to_make + self.__bot.supply_used > 200:
            scv_to_kill = self.__bot.units(UnitTypeId.SCV).ready.random
            for u in self.__bot.units.filter(lambda u: u.distance_to(scv_to_kill) < 20):
                u.attack(scv_to_kill)
            self.__supply_to_make -= 1

    async def __search_enemy(self):
        if self.__no_enemy_structure_detected:
            for u in self.__bot.units.filter(lambda u: not u.is_attacking and u.type_id in self.__unit_attack_amount):
                p : Point2 = Point2((0, 0))
                times = 0
                while (
                    not self.__bot.in_map_bounds(p)
                    or self.__searched_area[p.x][p.y]
                    and times <= 3
                    or (
                        not self.__bot.in_pathing_grid(p)
                        and not u.is_flying
                    )
                ):
                    p = Point2((randint(self.__map_min_x, self.__map_max_x), randint(self.__map_min_y, self.__map_max_y)))
                    times += 1
                self.__searched_area[p.x][p.y] = True
                u.attack(p)

    @property
    def scout(self):
        return self.__scout

    @property
    def scout_SCV(self):
        return self.__scout_SCV

    @property
    def scout_SCV_got_order(self):
        return self.__scout_SCV_got_order

    @property
    def scout_after(self):
        return self.__scout_after

    @property
    def repair_defense_structure(self):
        return self.__repair_defense_structure

    @property
    def repair_SCVs(self):
        return self.__repair_SCVs

    @property
    def SCV_repair_range(self):
        return self.__SCV_repair_range

    @property
    def no_enemy_structure_detected(self):
        return self.__no_enemy_structure_detected

    @property
    def supply_to_attack(self):
        return self.__supply_to_attack

    @property
    def supply_to_make(self):
        return self.__supply_to_make

    @property
    def need_scan(self):
        return self.__need_scan

    @property
    def attack_units(self):
        return self.__attack_units

    @property
    def defense_units(self):
        return self.__defense_units

    @property
    def SCVs(self):
        return self.__SCVs

    @property
    def defense_range(self):
        return self.__defense_range

    @property
    def worker_rush_defense_range(self):
        return self.__worker_rush_defense_range

    @property
    def attack_target(self):
        return self.__attack_target

    @property
    def searched_area(self):
        return self.__searched_area

    @property
    def map_min_x(self):
        return self.__map_min_x

    @property
    def map_max_x(self):
        return self.__map_max_x

    @property
    def map_min_y(self):
        return self.__map_min_y

    @property
    def map_max_y(self):
        return self.__map_max_y

    def unit_attack_amount(self):
        return self.__unit_attack_amount

    @supply_to_attack.setter
    def supply_to_attack(self, value: int):
        self.__supply_to_attack = value

    @defense_range.setter
    def defense_range(self, value: float):
        self.__defense_range = value

    @attack_target.setter
    def attack_target(self, value: Point2):
        self.attack_target = value

    @worker_rush_defense_range.setter
    def worker_rush_defense_range(self, value: float):
        self.worker_rush_defense_range = value

    @need_scan.setter
    def need_scan(self, value: bool):
        self.__need_scan = value

    @supply_to_make.setter
    def supply_to_make(self, value: int):
        self.__supply_to_make = value

    @scout_SCV.setter
    def scout_SCV(self, value: Unit):
        assert isinstance(value, Unit)
        assert value.type_id == UnitTypeId.SCV
        self.__bot.building_manager.remove_proxy_worker(value.tag)
        self.__scout_SCV = value

    def set_unit_attack_amount(self, type_id ,value: int):
        assert type.id in self.__unit_attack_amount
        self.__unit_attack_amount[type_id] = value

    def set_scout_parameters(
        self,
        scout: bool = True,
        scout_after: UnitTypeId = UnitTypeId.BARRACKS
    ):
        self.__scout = scout
        self.__scout_after = scout_after

    def set_repair_SCVs_parameters(self, repair=False, amount_of_SCV=0, SCV_repair_range=30):
        if not self.__repair_defense_structure and repair:
            self.__repair_defense_structure = True
            self.SCV_repair_range = SCV_repair_range
            for s in self.__bot.units(UnitTypeId.SCV).filter(lambda s: s.is_collecting):
                self.__repair_SCVs.append(s)
                if len(self.__repair_SCVs) >= amount_of_SCV:
                    break
        elif not repair:
            self.__repair_defense_structure = False
            self.__repair_SCVs.clear()
