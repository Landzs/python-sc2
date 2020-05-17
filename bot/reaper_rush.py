import sc2
from basic_manager.priority_manager import TerranPriorityManager
from basic_manager.resources_manager import TerranResourcesManager
from basic_manager.building_manager import TerranBuildingManager
from basic_manager.production_manager import TerranProductionManager
from basic_manager.macro_control_manager import TerranMacroControlManager
from basic_manager.micro_control_manager import TerranMicroControlManager
from sc2.ids.unit_typeid import UnitTypeId


class ReaperRushBot(sc2.BotAI):
    """
    - Reaper rush bot
    - Proxy rax Barracks
    - If rush fail, keep training reapers
    """

    def __init__(self):
        super()._initialize_variables()

        # basic managers
        self.priority_manager      = TerranPriorityManager(self)
        self.resources_manager     = TerranResourcesManager(self)
        self.building_manager      = TerranBuildingManager(self)
        self.production_manager    = TerranProductionManager(self)
        self.macro_control_manager = TerranMacroControlManager(self)
        self.micro_control_manager = TerranMicroControlManager(self)

        # phase control
        self.phase = {
            0: 'Start',
            1: 'Rush',
            2: 'Develop',
        }
        self.phase_number = 0

        # basic setting
        self.priority_manager.initialize(
            [
                "build_marines",
                "build_refinery"
            ]
        )
        self.building_manager.barracks_limit      = 3
        self.resources_manager.workers_limit      = 144
        self.resources_manager.resource_ratio     = 100
        self.macro_control_manager.amount_reapers = 5
        self.barrack_proxyrax_position            = (0, 0)
        self.number_of_workers_proxyrax           = 2
        self.workers_proxyrax                     = []
        self.townhalls_limit                      = 3

    async def on_step(self, iteration):
        await self.bot_manager()
        await self.priority_manager.manage_priority()
        await self.resources_manager.manage_resources(iteration)
        await self.building_manager.manage_building()
        await self.production_manager.manage_production()
        await self.macro_control_manager.manage_macro_control()
        await self.micro_control_manager.manage_micro_control()

    async def bot_manager(self):
        phase_now = self.phase.get(self.phase_number)

        if phase_now  == 'Start':
            townhall_location = self.townhalls[0].position
            enemy_location    = self.enemy_start_locations[0]
            barracks_amount = self.structures(UnitTypeId.BARRACKS).ready.amount
            if self.barrack_proxyrax_position == (0, 0):
                self.barrack_proxyrax_position = enemy_location.towards(
                    self.game_info.map_center,
                    35
                )

            if not self.workers_proxyrax:
                self.workers_proxyrax.append(self.workers[0])

            if self.macro_control_manager.attack_target == (0, 0):
                self.macro_control_manager.attack_target = enemy_location

            if (
                len(self.workers_proxyrax) == 1
                and self.structures(UnitTypeId.SUPPLYDEPOT).ready.amount >= 1
            ):
                self.workers_proxyrax.append(
                    self.select_build_worker(townhall_location)
                )

            for worker in self.units(UnitTypeId.SCV).filter(
                lambda w: w in self.workers_proxyrax
            ):
                if (worker.distance_to(self.barrack_proxyrax_position) > 75):
                    worker.move(self.barrack_proxyrax_position)

            if (
                barracks_amount
                + self.already_pending(UnitTypeId.BARRACKS) >= 1
            ):
                self.resources_manager.resource_ratio = 3.5

            if barracks_amount >= 1:
                self.resources_manager.resource_ratio = 2.7

            if barracks_amount == 2:
                self.phase_number += 1

        elif phase_now == "Rush":
            self.workers_proxyrax = []
            self.building_manager.barracks_limit = 5
            if (
                self.structures(UnitTypeId.COMMANDCENTER).ready.amount == 1
            ):
                self.phase_number += 1

        elif phase_now == "Develop":
            self.barrack_proxyrax_position = (0, 0)
            self.building_manager.barracks_limit = 8
            self.macro_control_manager.amount_reapers = 15
