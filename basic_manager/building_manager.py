from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.position import Point2
from sc2.units import Units


class TerranBuildingManager():
    """
    - Basic building control for Terran
    """

    def __init__(self, bot=None):
        self.bot                      = bot

        # ramp wall parametes
        self.ramp_wall                = True
        self.ramp_middle_barrack      = True
        self.depot_ramp_positions     = []
        self.barrack_ramp_position    = []

        # proxy rax parameters
        self.proxy_barracks           = False
        self.proxy_barracks_position = (0, 0)
        self.proxy_workers            = []
        self.proxy_barracks_back = False
        self.landing_buidlings: Units = []
        self.landing_positions_offset = sorted(
            (
                Point2((x, y))
                for x in range(-15, 15)
                for y in range(-15, 15)
            ),
            key=lambda point: point.x ** 2 + point.y ** 2,
        )

        # buildings' amount limitations
        self.amount_limitation        = {
            UnitTypeId.SUPPLYDEPOT    : 100,
            UnitTypeId.BARRACKS       : 1,
            UnitTypeId.FACTORY        : 1,
            UnitTypeId.STARPORT       : 1,
            UnitTypeId.BARRACKSTECHLAB: 1,
            UnitTypeId.BARRACKSREACTOR: 1,
            UnitTypeId.FACTORYTECHLAB : 1,
            UnitTypeId.FACTORYREACTOR : 1,
            UnitTypeId.STARPORTTECHLAB: 1,
            UnitTypeId.STARPORTREACTOR: 1,
        }

    def initialize(self):
        """
        - Initialize building paramenters
        - Need map info so should be called in on_start
        """

        self.depot_ramp_positions.extend(
            self.bot.main_base_ramp.corner_depots
        )
        if self.ramp_middle_barrack:
            self.barrack_ramp_position.append(
                self.bot.main_base_ramp.barracks_correct_placement
            )
        else:
            self.depot_ramp_positions.append(
                self.bot.main_base_ramp.depot_in_middle
            )

        proxy_position = self.bot.enemy_start_locations[0].towards(
            self.bot.game_info.map_center,
            35
        )
        self.proxy_barracks_position = proxy_position
        self.proxy_workers.append(self.bot.workers[0])

    async def manage_building(self, iteration):
        """
        - Manage building, call in on_step
        - Including build Terran building
        - Some buildings can be proxy rax
        """

        await self.build_depot()
        await self.build_barrack()
        await self.build_factory()
        await self.build_starport()
        await self.manager_building_back_to_base(iteration)
        await self.build_addons()
        await self.manage_buildings_landing(iteration)
        await self.manage_supplydepots()

    def check_available(self, type_id):
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

    async def get_position_near_townhall(self, type_id):
        townhall = self.bot.townhalls[-1].position
        position = await self.bot.find_placement(
            type_id,
            near=townhall,
            min_distance=7
        )
        return position

    async def build_depot(self):
        if(
            self.bot.supply_left < 4
            and not self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
            and self.check_available(UnitTypeId.SUPPLYDEPOT)
        ):
            if (
                self.ramp_wall
                and self.depot_ramp_positions
            ):
                depot_position = self.depot_ramp_positions.pop()
            else:
                depot_position = await self.get_position_near_townhall(
                    UnitTypeId.SUPPLYDEPOT
                )
            worker = self.bot.select_build_worker(depot_position)
            if worker:
                worker.build(UnitTypeId.SUPPLYDEPOT, depot_position)

    async def build_barrack(self):
        if self.check_available(UnitTypeId.BARRACKS):
            if (
                self.ramp_middle_barrack
                and self.barrack_ramp_position
                and self.ramp_wall
                and (
                    not self.proxy_barracks
                    or self.bot.macro_control_manager.worker_rush_defense
                )
            ):
                barrack_position = self.barrack_ramp_position.pop()
                worker = self.bot.select_build_worker(barrack_position)
            elif (
                self.proxy_barracks
                and self.proxy_workers
                and self.proxy_barracks_position != (0, 0)
                and not self.bot.macro_control_manager.worker_rush_defense
            ):
                barrack_position = await self.bot.find_placement(
                    UnitTypeId.BARRACKS,
                    near=self.proxy_barracks_position
                )
                worker = next(
                    (
                        w
                        for w in self.bot.units(UnitTypeId.SCV).filter(
                            lambda w: w in self.proxy_workers
                        )
                        if (
                            not w.is_constructing_scv
                            and w.distance_to(barrack_position) < 75
                        )
                    ),
                    None
                )
            else:
                barrack_position = await self.get_position_near_townhall(
                    UnitTypeId.BARRACKS
                )
                worker = self.bot.select_build_worker(barrack_position)
            if worker:
                worker.build(UnitTypeId.BARRACKS, barrack_position)

    async def build_factory(self):
        if self.check_available(UnitTypeId.FACTORY):
            factory_position = await self.get_position_near_townhall(
                UnitTypeId.FACTORY
            )
            worker = self.bot.select_build_worker(factory_position)
            if worker:
                worker.build(UnitTypeId.FACTORY, factory_position)

    async def build_starport(self):
        if self.check_available(UnitTypeId.STARPORT):
            starport_position = await self.get_position_near_townhall(
                UnitTypeId.STARPORT
            )
            worker = self.bot.select_build_worker(starport_position)
            if worker:
                worker.build(UnitTypeId.STARPORT, starport_position)

    async def manage_supplydepots(self):
        for d in self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready:
            if (
                not self.bot.enemy_units
                or (
                    self.bot.enemy_units
                    and self.bot.enemy_units.closest_distance_to(d) > 15
                )
                or self.bot.macro_control_manager.worker_rush_detected
            ):
                d(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        for d in self.bot.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            if (
                self.bot.enemy_units
                and self.bot.enemy_units.closest_distance_to(d) < 10
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
            lambda b: not b.has_add_on
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
                lambda b: b in self.landing_buidlings
            ):
                self.find_place_to_land(b, addon=True)

            for f in self.bot.structures(UnitTypeId.FACTORYFLYING).filter(
                lambda f: f in self.landing_buidlings
            ):
                self.find_place_to_land(f, addon=True)

            for s in self.bot.structures(UnitTypeId.STARPORTFLYING).filter(
                lambda s: s in self.landing_buidlings
            ):
                self.find_place_to_land(s, addon=True)

    def find_place_to_land(self, building, addon: bool = True):
        offset_point = Point2((-0.5, -0.5))
        possible_land_positions = (
            building.position.rounded + p + offset_point
            for p in self.landing_positions_offset
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
                for p in land_points
            ):
                building(AbilityId.LAND, l)
                if building in self.landing_buidlings:
                    self.landing_buidlings.remove(building)
                break

    async def manager_building_back_to_base(self, iteration):
        if self.proxy_barracks_back:
            for b in self.bot.structures(UnitTypeId.BARRACKS).filter(
                lambda b: b.distance_to(self.bot.start_location) > 70
            ):
                b(AbilityId.LIFT)

            for b in self.bot.structures(UnitTypeId.BARRACKSFLYING).filter(
                lambda b: b.distance_to(self.bot.start_location) > 70
            ):
                b.move(self.bot.start_location)

            if iteration % 13 == 0:
                for b in self.bot.structures(UnitTypeId.BARRACKSFLYING).filter(
                    lambda b: b.distance_to(self.bot.start_location) < 20
                ):
                    self.landing_buidlings.append(b)

    def set_limitation(self, unit, amount):
        self.amount_limitation[unit] = amount
