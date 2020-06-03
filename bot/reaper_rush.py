import sc2
from basic_manager.strategy_manager import TerranStrategyManager
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
        self.strategy_manager      = TerranStrategyManager(self)
        self.resources_manager     = TerranResourcesManager(self)
        self.building_manager      = TerranBuildingManager(self)
        self.production_manager    = TerranProductionManager(self)
        self.macro_control_manager = TerranMacroControlManager(self)
        self.micro_control_manager = TerranMicroControlManager(self)

        # phase control initializations
        self.strategy_manager.phase[1]     = 'Start'
        self.strategy_manager.phase[2]     = 'Rush'
        self.strategy_manager.phase[3]     = 'Develop'
        self.strategy_manager.phase_number = 1

        # strategy_manager initializations
        self.strategy_manager.initialize(
            [
                UnitTypeId.MARINE,
                UnitTypeId.REFINERY,
                UnitTypeId.FACTORY,
            ]
        )

        # resources_manager initializations
        self.resources_manager.workers_limitation   = 144
        self.resources_manager.resource_ratio       = 100
        self.resources_manager.townhalls_limitation = 3

        # building_manager initializations
        self.building_manager.proxy_barracks                         = True
        self.building_manager.amount_limitation[UnitTypeId.BARRACKS] = 3
        self.building_manager.ramp_wall                              = True
        self.building_manager.ramp_middle_barrack                    = False

        # macro_control_manager initializations
        self.macro_control_manager.amount_reapers = 1

    async def on_start(self):
        self.building_manager.initialize()
        self.macro_control_manager.initialize()

    async def on_step(self, iteration):
        await self.bot_manager()
        await self.strategy_manager.manage_baisc_strategy()
        await self.resources_manager.manage_resources(iteration)
        await self.building_manager.manage_building()
        await self.production_manager.manage_production()
        await self.macro_control_manager.manage_macro_control()
        await self.micro_control_manager.manage_micro_control()

    async def bot_manager(self):
        phase_now = self.strategy_manager.phase.get(
            self.strategy_manager.phase_number
        )

        if phase_now  == 'Start':
            start_location  = self.start_location
            enemy_location  = self.enemy_start_locations[0]
            barracks_amount = self.structures(UnitTypeId.BARRACKS).ready.amount

            if self.building_manager.proxy_barracks_positions == (0, 0):
                proxy_position = enemy_location.towards(
                    self.game_info.map_center,
                    35
                )
                self.building_manager.proxy_barracks_positions = proxy_position

            if not self.building_manager.proxy_workers:
                self.building_manager.proxy_workers.append(self.workers[0])

            if self.macro_control_manager.attack_target == (0, 0):
                self.macro_control_manager.attack_target = enemy_location

            if (
                len(self.building_manager.proxy_workers) <= 1
                and self.structures(UnitTypeId.SUPPLYDEPOT).ready.amount >= 1
            ):
                self.building_manager.proxy_workers.append(
                    self.select_build_worker(start_location)
                )

            for worker in self.units(UnitTypeId.SCV).filter(
                lambda w: w in self.building_manager.proxy_workers
            ):
                positions = self.building_manager.proxy_barracks_positions
                if (worker.distance_to(positions) > 75):
                    worker.move(positions)

            if (
                barracks_amount
                + self.already_pending(UnitTypeId.BARRACKS) >= 1
            ):
                self.resources_manager.resource_ratio = 3.5

            if barracks_amount >= 1:
                self.resources_manager.resource_ratio = 2.7

            if barracks_amount == 3:
                self.strategy_manager.phase_number += 1

        elif phase_now == "Rush":
            self.proxy_workers = []
            self.building_manager.proxy_barracks = False
            if (
                self.already_pending(UnitTypeId.COMMANDCENTER) == 1
            ):
                self.strategy_manager.phase_number += 1

        elif phase_now == "Develop":
            self.building_manager.amount_limitation[UnitTypeId.BARRACKS] = 8
            self.macro_control_manager.amount_reapers = 15
