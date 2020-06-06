import sc2
from basic_manager.strategy_manager import TerranStrategyManager
from basic_manager.resources_manager import TerranResourcesManager
from basic_manager.building_manager import TerranBuildingManager
from basic_manager.production_manager import TerranProductionManager
from basic_manager.macro_control_manager import TerranMacroControlManager
from basic_manager.micro_control_manager import TerranMicroControlManager
from sc2.ids.unit_typeid import UnitTypeId


class TerranBot(sc2.BotAI):
    """
    - Basic Terran bot Template
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
        self.strategy_manager.phase[1] = 'Start'
        self.strategy_manager.phase_number = 1

        # strategy_manager initializations
        self.strategy_manager.initialize(
            [
                UnitTypeId.MARINE,
                UnitTypeId.REFINERY,
                UnitTypeId.FACTORY,
            ]
        )

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
        pass