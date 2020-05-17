import inspect
from sc2.ids.unit_typeid import UnitTypeId


class TerranBuildingManager():
    """
    - Basic building control for Terran
    """

    def __init__(self, bot=None):
        self.bot            = bot
        self.barracks_limit = 1

    async def manage_building(self):
        """
        - Manage building, call in on_step
        - Including build Terran building
        - Can be proxy rax for some buildings
        """

        await self.build_supply()

        if self.bot.barrack_proxyrax_position == (0, 0):
            await self.build_barrack()
        else:
            await self.build_barrack_proxyrax()

    async def build_supply(self):
        if not self.bot.priority_manager.check_block(
            inspect.currentframe().f_code.co_name
        ):
            if(
                self.bot.townhalls.ready.exists
                and self.bot.supply_left < 4
                and not self.bot.already_pending(UnitTypeId.SUPPLYDEPOT)
                and self.bot.can_afford(UnitTypeId.SUPPLYDEPOT)
            ):
                townhall = self.bot.townhalls[0].position
                supply_position = await self.bot.find_placement(
                    UnitTypeId.SUPPLYDEPOT,
                    near=townhall,
                    min_distance=7
                )
                worker = self.bot.select_build_worker(supply_position)
                if worker:
                    worker.build(UnitTypeId.SUPPLYDEPOT, supply_position)

    async def build_barrack(self):
        if not self.bot.priority_manager.check_block(
            inspect.currentframe().f_code.co_name
        ):
            if (
                self.bot.tech_requirement_progress(UnitTypeId.BARRACKS) == 1
                and self.bot.townhalls.ready.exists
                and (
                    self.bot.structures(UnitTypeId.BARRACKS).ready.amount
                    + self.bot.already_pending(UnitTypeId.BARRACKS)
                    <= self.barracks_limit
                    )
                and self.bot.can_afford(UnitTypeId.BARRACKS)
            ):
                townhall = self.bot.townhalls.ready[-1].position
                barrack_position = await self.bot.find_placement(
                    UnitTypeId.BARRACKS,
                    near=townhall,
                    min_distance=7
                )
                worker = self.bot.select_build_worker(barrack_position)
                if worker:
                    worker.build(UnitTypeId.BARRACKS, barrack_position)

    async def build_barrack_proxyrax(self):
        if not self.bot.priority_manager.check_block(
            inspect.currentframe().f_code.co_name
        ):
            if (
                self.bot.tech_requirement_progress(UnitTypeId.BARRACKS) == 1
                and self.bot.townhalls.ready.exists
                and (
                    self.bot.structures(UnitTypeId.BARRACKS).ready.amount
                    + self.bot.already_pending(UnitTypeId.BARRACKS)
                    <= self.barracks_limit
                )
                and self.bot.can_afford(UnitTypeId.BARRACKS)
            ):
                proxyrax_position = self.bot.barrack_proxyrax_position
                worker = next(
                    (
                        worker
                        for worker in self.bot.units(UnitTypeId.SCV).filter(
                            lambda worker: worker in self.bot.workers_proxyrax
                        )
                            if (
                                not worker.is_constructing_scv
                                and worker.distance_to(proxyrax_position) < 75
                            )
                    ),
                    None
                )
                barrack_position = await self.bot.find_placement(
                    UnitTypeId.BARRACKS,
                    near=proxyrax_position
                )
                if worker:
                    worker.build(UnitTypeId.BARRACKS, barrack_position)
