import inspect
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class TerranBuildingManager():
    """
    - Basic building control for Terran
    """

    def __init__(self, bot=None):
        self.bot                   = bot
        self.ramp_wall             = True
        self.ramp_middle_barrack   = True
        self.proxy_rax             = False
        self.amount_limitation     = {
            UnitTypeId.SUPPLYDEPOT: 100,
            UnitTypeId.BARRACKS   : 1,
        }
        self.depot_ramp_positions  = []
        self.barrack_ramp_position = []

    def initialize(self):
        """
        - Initialize building paramenters
        - Need map info so should be called once in on_step
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

    async def manage_building(self):
        """
        - Manage building, call in on_step
        - Including build Terran building
        - Can be proxy rax for some buildings
        """

        await self.build_depot()
        await self.build_barrack()
        await self.manage_supplydepot()

    def check_available(self, type_id):
        if(
            self.bot.townhalls.ready.exists
            and self.bot.tech_requirement_progress(type_id) == 1
            and self.bot.can_afford(type_id)
            and (
                self.bot.structures(type_id).ready.amount
                + self.bot.already_pending(type_id)
                < self.amount_limitation[type_id]
            )
        ):
            return True
        else:
            return False

    async def get_position_near_th(self, type_id):
        townhall = self.bot.townhalls[-1].position
        position = await self.bot.find_placement(
            type_id,
            near=townhall,
            min_distance=7
        )
        return position

    async def build_depot(self):
        if not self.bot.priority_manager.check_block(
            inspect.currentframe().f_code.co_name
        ):
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
                    depot_position = await self.get_position_near_th(
                        UnitTypeId.SUPPLYDEPOT
                    )
                worker = self.bot.select_build_worker(depot_position)
                if worker:
                    worker.build(UnitTypeId.SUPPLYDEPOT, depot_position)

    async def build_barrack(self):
        if not self.bot.priority_manager.check_block(
            inspect.currentframe().f_code.co_name
        ):
            if self.check_available(UnitTypeId.BARRACKS):
                if (
                    self.ramp_middle_barrack
                    and self.barrack_ramp_position
                    and self.ramp_wall
                    and not self.proxy_rax
                ):
                    barrack_position = self.barrack_ramp_position.pop()
                    worker = self.bot.select_build_worker(barrack_position)
                elif self.proxy_rax:
                    barrack_position = await self.bot.find_placement(
                        UnitTypeId.BARRACKS,
                        near=self.bot.barracks_proxyrax_position
                    )
                    worker = next(
                        worker
                        for worker in self.bot.units(UnitTypeId.SCV).filter(
                            lambda worker: worker in self.bot.workers_proxyrax
                        )
                        if (
                            not worker.is_constructing_scv
                            and worker.distance_to(barrack_position) < 75
                        )
                    )
                else:
                    barrack_position = await self.get_position_near_th(
                        UnitTypeId.BARRACKS
                    )
                    worker = self.bot.select_build_worker(barrack_position)
                if worker:
                    worker.build(UnitTypeId.BARRACKS, barrack_position)

    async def manage_supplydepot(self):
        for d in self.bot.structures(UnitTypeId.SUPPLYDEPOT).ready:
            if (
                self.bot.enemy_units
                and self.bot.enemy_units.closest_distance_to(d) > 15
            ):
                d(AbilityId.MORPH_SUPPLYDEPOT_LOWER)

        for d in self.bot.structures(UnitTypeId.SUPPLYDEPOTLOWERED).ready:
            if (
                self.bot.enemy_units
                and self.bot.enemy_units.closest_distance_to(d) < 10
            ):
                d(AbilityId.MORPH_SUPPLYDEPOT_RAISE)
