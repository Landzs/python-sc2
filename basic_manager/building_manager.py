from sc2.unit import Unit
from sc2.units import Units
from sc2.position import Point2
from typing import Union, Optional
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class TerranBuildingManager():
    """
    - Basic building control for Terran
    """

    def __init__(self, bot=None):
        self.bot                        = bot

        # ramp wall parametes
        self.__ramp_wall                = True
        self.__ramp_middle_barrack      = True
        self.__depot_ramp_positions     = []
        self.__barrack_ramp_position    = []

        # proxy rax parameters
        self.__proxy                    = {
            UnitTypeId.BARRACKS       : False,
            UnitTypeId.FACTORY        : False,
            UnitTypeId.STARPORT       : False,
        }
        self.__proxy_position  = (0, 0)
        self.__proxy_workers            = []
        self.__proxy_workers_amount     = 2
        self.__proxy_barracks_back      = False
        self.__proxy_barracks = False
        self.__proxy_position_map       = {
            "Acropolis LE"        : [Point2((71, 133)), Point2((103, 37))],
            "滨海卫城 - 天梯版"     : [Point2((71, 133)), Point2((103, 37))],
            "Disco Bloodbath LE"  : [Point2((62, 95)), Point2((138, 85))],
            "浴血迪斯科 - 天梯版"   : [Point2((62, 95)), Point2((138, 85))],
            "Ephemeron LE"        : [Point2((63, 135)), Point2((98, 25))],
            "伊菲莫隆 - 天梯版"     : [Point2((63, 135)), Point2((98, 25))],
            "Eternal Empire LE"   : [Point2((115, 135)), Point2((61, 37))],
            "永恒帝国-天梯版"       : [Point2((115, 135)), Point2((61, 37))],
            "Ever Dream LE"       : [Point2((45, 99)), Point2((154, 114))],
            "永恒梦境-天梯版"       : [Point2((45, 99)), Point2((154, 114))],
            "Golden Wall LE"      : [Point2((42, 111)), Point2((166, 111))],
            "黄金墙-天梯版"         : [Point2((42, 111)), Point2((166, 111))],
            "Nightshade LE"       : [Point2((85, 135)), Point2((105, 38))],
            "紫夜-天梯版"           : [Point2((85, 135)), Point2((105, 38))],
            "Simulacrum LE"       : [Point2((98, 140)), Point2((115, 42))],
            "虚拟幻境-天梯版"       : [Point2((98, 140)), Point2((115, 42))],
            "Thunderbird LE"      : [Point2((73, 130)), Point2((120, 25))],
            "雷鸟 - 天梯版"         : [Point2((73, 130)), Point2((120, 25))],
            "Triton LE"           : [Point2((152, 76)), Point2((64, 128))],
            "特里同 - 天梯版"       : [Point2((152, 76)), Point2((64, 128))],
            "Winter's Gate LE"    : [Point2((88, 130)), Point2((103, 34))],
            "黑冬隘口 - 天梯版"     : [Point2((88, 130)), Point2((103, 34))],
            "World of Sleepers LE": [Point2((123, 136)), Point2((60, 34))],
            "梦境世界 - 天梯版"     : [Point2((123, 136)), Point2((60, 34))],
            "Zen LE"              : [Point2((80, 26)), Point2((110, 148))],
            "禅园-天梯版"          : [Point2((80, 26)), Point2((110, 148))],
            "Deathaura LE"        : [Point2((54, 119)), Point2((138, 70))],
            "死亡光环-天梯版"       : [Point2((54, 119)), Point2((138, 70))],
            "Ice and Chrome LE"   : [Point2((144, 174)), Point2((118, 66))],
            "冰雪合金-天梯版"       : [Point2((144, 174)), Point2((118, 66))],
            "Pillars of Gold LE"  : [Point2((139, 92)), Point2((31, 76))],
            "黄金之柱-天梯版"       : [Point2((139, 92)), Point2((31, 76))],
            "Submarine LE"        : [Point2((63, 124)), Point2((104, 40))],
            "潜水艇-天梯版"         : [Point2((63, 124)), Point2((104, 40))],
        }

        # landing parameters
        self.landing_buidlings: Units    = []
        self.__landing_positions_offset = sorted(
            (
                Point2((x, y))
                for x in range(-20, 20)
                for y in range(-20, 20)
            ),
            key=lambda point: point.x ** 2 + point.y ** 2,
        )

        # buildings' amount limitations
        self.amount_limitation        = {
            UnitTypeId.SUPPLYDEPOT    : 100,
            UnitTypeId.BARRACKS       : 1,
            UnitTypeId.FACTORY        : 1,
            UnitTypeId.STARPORT       : 1,
            UnitTypeId.ENGINEERINGBAY : 2,
            UnitTypeId.ARMORY         : 1,
            UnitTypeId.BUNKER         : 1,
            UnitTypeId.BARRACKSTECHLAB: 1,
            UnitTypeId.BARRACKSREACTOR: 1,
            UnitTypeId.FACTORYTECHLAB : 1,
            UnitTypeId.FACTORYREACTOR : 1,
            UnitTypeId.STARPORTTECHLAB: 1,
            UnitTypeId.STARPORTREACTOR: 1,
        }

        self.__already_moved = False

    def initialize(self):
        """
        - Initialize building paramenters
        - Need map info so should be called in on_start
        """

        # ramp wall parameters
        if self.__ramp_middle_barrack:
            self.__barrack_ramp_position.append(
                self.bot.main_base_ramp.barracks_correct_placement
            )
        else:
            self.__depot_ramp_positions.append(
                self.bot.main_base_ramp.depot_in_middle
            )
        self.__depot_ramp_positions.extend(
            self.bot.main_base_ramp.corner_depots
        )

        # proxy rax parameters
        map_name = self.bot.game_info.map_name
        if map_name in self.__proxy_position_map:
            proxy_position = min(
                self.__proxy_position_map[map_name],
                key=lambda p: p.distance_to(self.bot.enemy_start_locations[0])
            )
        else:
            proxy_position = self.bot.enemy_start_locations[0].towards(
                self.bot.game_info.map_center,
                35
            )
        self.__proxy_position = proxy_position
        self.__proxy_workers.append(self.bot.workers[0])

    async def manage_building(self, iteration):
        """
        - Manage building, called in on_step
        - Including build Terran building
        - Some buildings can be proxy rax
        """

        await self.move_first_workers_to_build()

        await self.build(UnitTypeId.SUPPLYDEPOT)
        await self.build(UnitTypeId.BARRACKS)
        await self.build(UnitTypeId.FACTORY)
        await self.build(UnitTypeId.STARPORT)
        await self.build(UnitTypeId.ENGINEERINGBAY)
        await self.build(UnitTypeId.ARMORY)
        await self.build(UnitTypeId.BUNKER)
        await self.build_addons()

        await self.manage_supplydepots()
        await self.manage_proxy_workers()
        await self.manager_building_back_to_base(iteration)
        await self.manage_buildings_landing(iteration)
        await self.manage_structures_without_construction_SCVs()

    def check_available(self, type_id):
        # supplydepot need special conditions
        if type_id == UnitTypeId.SUPPLYDEPOT:
            pending_limitation = 1 if self.bot.supply_used < 70 else 2
            supply_left_threshold = 4 if self.bot.supply_used < 70 else 7
            if(
                not self.bot.supply_left < supply_left_threshold
                or self.bot.supply_used >= 200
                or self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
                    >= pending_limitation
            ):
                return False

        # add flying buildings amount
        ready_amount = self.bot.structures(type_id).ready.amount
        pending_amount = self.bot.already_pending(type_id)
        if type_id == UnitTypeId.BARRACKS:
            ready_amount += self.bot.structures(
                UnitTypeId.BARRACKSFLYING
            ).ready.amount
        elif type_id == UnitTypeId.FACTORY:
            ready_amount += self.bot.structures(
                UnitTypeId.FACTORYFLYING
            ).ready.amount
        elif type_id == UnitTypeId.STARPORT:
            ready_amount += self.bot.structures(
                UnitTypeId.STARPORTFLYING
            ).ready.amount

        if(
            self.bot.townhalls.ready.exists
            and self.bot.tech_requirement_progress(type_id) == 1
            and self.bot.can_afford(type_id)
            and not self.bot.strategy_manager.check_block(type_id)
            and ready_amount + pending_amount < self.amount_limitation[type_id]
        ):
            return True
        else:
            return False

    async def move_first_workers_to_build(self):
        if (
            not self.__already_moved
            and self.bot.supply_used == 14
        ):
            target_position = self.__depot_ramp_positions[0].towards(
                self.bot.start_location,
                0.75
            )
            worker = self.bot.select_build_worker(target_position)
            if worker:
                worker.move(target_position)
                self.__already_moved = True

    async def build(self, type_id):
        if self.check_available(type_id):
            if(
                type_id in self.__proxy
                and self.__proxy[type_id]
                and self.__proxy_workers
            ):
                position = await self.bot.find_placement(
                    type_id,
                    near=self.__proxy_position
                )
                worker = next(
                    (
                        w
                        for w in self.bot.units(UnitTypeId.SCV).filter(
                            lambda w: w in self.__proxy_workers
                        )
                        if (
                            not w.is_constructing_scv
                            and w.distance_to(position) < 75
                        )
                    ),
                    None
                )
            elif (
                self.__ramp_wall
                and (
                    self.__barrack_ramp_position
                    and self.__ramp_middle_barrack
                    and type_id == UnitTypeId.BARRACKS
                )
                or (
                    self.__depot_ramp_positions
                    and type_id == UnitTypeId.SUPPLYDEPOT
                )
            ):
                if type_id == UnitTypeId.BARRACKS:
                    position  = self.__barrack_ramp_position[0]
                    worker = self.bot.select_build_worker(position)
                    if worker:
                        self.__barrack_ramp_position.pop()
                elif type_id == UnitTypeId.SUPPLYDEPOT:
                    position = self.__depot_ramp_positions[-1]
                    worker = self.bot.select_build_worker(position)
                    if worker:
                        self.__depot_ramp_positions.pop()  
            elif type_id == UnitTypeId.BUNKER:
                if self.__depot_ramp_positions:
                    position = await self.bot.find_placement(
                        type_id,
                        near=self.__depot_ramp_positions[-1]
                    )
                    worker = self.bot.select_build_worker(position)
                    if worker:
                        self.__depot_ramp_positions.pop()
                else:
                    position = await self.bot.find_placement(
                        type_id,
                        near=self.bot.macro_control_manager.assembing_point
                    )
                    worker = self.bot.select_build_worker(position)
            else:
                townhall = self.bot.townhalls[-1].position
                position = await self.bot.find_placement(
                    type_id,
                    near=townhall,
                    min_distance=8
                )
                worker = self.bot.select_build_worker(position)
            if worker:
                worker.build(type_id, position)

    async def manage_supplydepots(self):
        enemies_ground = self.bot.enemy_units.filter(
            lambda e: not e.is_flying
        )
        for d in self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready:
            if (
                not enemies_ground
                or (
                    enemies_ground
                    and enemies_ground.closest_distance_to(d) > 15
                )
                or self.bot.macro_control_manager.worker_rush_detected
            ):
                d(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        for d in self.bot.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            if (
                enemies_ground
                and enemies_ground.closest_distance_to(d) < 10
                and not self.bot.macro_control_manager.worker_rush_detected
            ):
                d(AbilityId.MORPH_SUPPLYDEPOT_RAISE)

    def get_addon_points(self, position):
        addon_offset: Point2 = Point2((2.5, -0.5))
        addon_position: Point2 = position + addon_offset
        return [
            (addon_position + Point2((x - 0.5, y - 0.5))).rounded
            for x in range(0, 2) for y in range(0, 2)
        ]

    def build_addon(self, building, addon_type):
        addon_points = self.get_addon_points(building.position)
        if all(
            self.bot.in_map_bounds(addon_point)
            and self.bot.in_placement_grid(addon_point)
            and self.bot.in_pathing_grid(addon_point)
            for addon_point in addon_points
        ):
            building.build(addon_type)
        else:
            building(AbilityId.LIFT)
            self.landing_buidlings.append(building)

    async def build_addons(self):
        for b in self.bot.structures(UnitTypeId.BARRACKS).ready.idle.filter(
            lambda b:
                not b.has_add_on
                and b.distance_to(self.bot.start_location) < 30
        ):
            if self.check_available(UnitTypeId.BARRACKSTECHLAB):
                self.build_addon(b, UnitTypeId.BARRACKSTECHLAB)
            elif self.check_available(UnitTypeId.BARRACKSREACTOR):
                self.build_addon(b, UnitTypeId.BARRACKSREACTOR)

        for f in self.bot.structures(UnitTypeId.FACTORY).ready.idle.filter(
            lambda f: not f.has_add_on
        ):
            if self.check_available(UnitTypeId.FACTORYTECHLAB):
                self.build_addon(f, UnitTypeId.FACTORYTECHLAB)
            elif self.check_available(UnitTypeId.FACTORYREACTOR):
                self.build_addon(f, UnitTypeId.FACTORYREACTOR)

        for s in self.bot.structures(UnitTypeId.STARPORT).ready.idle.filter(
            lambda s: not s.has_add_on
        ):
            if self.check_available(UnitTypeId.STARPORTTECHLAB):
                self.build_addon(s, UnitTypeId.STARPORTTECHLAB)
            elif self.check_available(UnitTypeId.STARPORTREACTOR):
                self.build_addon(s, UnitTypeId.STARPORTREACTOR)

    async def manage_buildings_landing(self, iteration):
        if iteration % 17 == 0:
            for b in self.bot.structures(UnitTypeId.BARRACKSFLYING).filter(
                lambda b: b in self.landing_buidlings or b.is_idle
            ):
                self.find_place_to_land(b, addon=True)

            for f in self.bot.structures(UnitTypeId.FACTORYFLYING).filter(
                lambda f: f in self.landing_buidlings or f.is_idle
            ):
                self.find_place_to_land(f, addon=True)

            for s in self.bot.structures(UnitTypeId.STARPORTFLYING).filter(
                lambda s: s in self.landing_buidlings or s.is_idle
            ):
                self.find_place_to_land(s, addon=True)

    def find_place_to_land(self, building, addon: bool = True):
        offset_point = Point2((-0.5, -0.5))
        possible_land_positions = (
            building.position.rounded + p + offset_point
            for p in self.__landing_positions_offset
        )
        for l in possible_land_positions:
            land_points = [
                (l + Point2((x, y))).rounded
                for x in range(-1, 2)
                for y in range(-1, 2)
            ]

            if addon:
                land_points += self.get_addon_points(l)
            if all(
                self.bot.in_map_bounds(p)
                and self.bot.in_placement_grid(p)
                and self.bot.in_pathing_grid(p)
                and p not in self.bot.expansion_locations_list
                for p in land_points
            ):
                building(AbilityId.LAND, l)
                if building in self.landing_buidlings:
                    self.landing_buidlings.remove(building)
                break

    async def manager_building_back_to_base(self, iteration):
        if self.__proxy_barracks_back:
            for b in self.bot.structures(UnitTypeId.BARRACKS).filter(
                lambda b: b.distance_to(self.bot.start_location) > 70
            ):
                b(AbilityId.LIFT)

            for b in self.bot.structures(UnitTypeId.BARRACKSFLYING).filter(
                lambda b: b.distance_to(self.bot.start_location) > 60
            ):
                b.move(self.bot.start_location)

            if iteration % 13 == 0:
                for b in self.bot.structures(UnitTypeId.BARRACKSFLYING).filter(
                    lambda b: b.distance_to(self.bot.start_location) < 20
                ):
                    self.landing_buidlings.append(b)

    async def manage_proxy_workers(self):
        if any(self.__proxy):
            if (
                len(self.__proxy_workers) < self.__proxy_workers_amount
                and self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready.amount >= 1
            ):
                self.__proxy_workers.append(
                    self.bot.select_build_worker(self.bot.start_location)
                )

            for w in self.bot.units(UnitTypeId.SCV).filter(
                lambda w:
                    w in self.__proxy_workers
                    and w.distance_to(self.__proxy_position) > 75
            ):
                w.move(self.__proxy_position)

    async def manage_structures_without_construction_SCVs(self):
        structures = self.bot.structures_without_construction_SCVs()

        for s in structures:
            if s.health_percentage < 0.1:
                s(AbilityId.CANCEL)
            else:
                enemies = self.bot.enemy_units | self.bot.enemy_structures
                close_enemies = enemies.filter(
                    lambda u:
                        u.can_attack_ground
                        and u.distance_to(s) <= 10
                )
                if not close_enemies:
                    worker = self.bot.select_build_worker(s.position)
                    if worker:
                        worker(AbilityId.SMART, s)

    def set_limitation(self, unit, amount):
        self.amount_limitation[unit] = amount

    def set_proxy_parameters(
        self,
        type_id,
        proxy=False,
        back=False,
        workers_amount=0
    ):
        if proxy:
            self.__proxy[type_id] = True
            self.__proxy_workers_amount = workers_amount
        else:
            self.__proxy[type_id] = False
            self.__proxy_workers_amount = 0
            self.__proxy_workers = []
            if back:
                self.__proxy_barracks_back = True

    def set_ramp_parameters(self, ramp, middle_barrack):
        self.__ramp_wall = ramp
        self.__ramp_middle_barrack = middle_barrack

    def get_proxy_workers(self):
        return self.__proxy_workers

    def get_proxy_parameters(self, type_id):
        return self.__proxy[type_id]
