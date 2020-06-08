from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.ability_id import AbilityId


class TerranStrategyManager():
    """
    - Basic strategy management for Terran
    """

    def __init__(self, bot=None):
        self.bot         = bot
        self.block_table = {
            UnitTypeId.SCV            : False,
            UnitTypeId.MARINE         : False,
            UnitTypeId.MARAUDER       : False,
            UnitTypeId.REAPER         : False,
            UnitTypeId.MEDIVAC        : False,
            UnitTypeId.VIKINGFIGHTER  : False,
            UnitTypeId.SUPPLYDEPOT    : False,
            UnitTypeId.BARRACKS       : False,
            UnitTypeId.FACTORY        : False,
            UnitTypeId.STARPORT       : False,
            UnitTypeId.COMMANDCENTER  : False,
            UnitTypeId.REFINERY       : False,
            UnitTypeId.ORBITALCOMMAND : False,
            UnitTypeId.BARRACKSTECHLAB: False,
            UnitTypeId.BARRACKSREACTOR: False,
            UnitTypeId.FACTORYTECHLAB : False,
            UnitTypeId.FACTORYREACTOR : False,
            UnitTypeId.STARPORTTECHLAB: False,
            UnitTypeId.STARPORTREACTOR: False,
            UpgradeId.STIMPACK        : False,
            UpgradeId.SHIELDWALL      : False,
            UpgradeId.PUNISHERGRENADES: False,
            
        }
        self.helper_table = self.block_table.copy()

        # phase control initializations
        self.phase = {
            0: 'Defense Worker Rush',
            100: 'Searching Remain Enemies'
        }
        self.phase_number = 1

    async def manage_baisc_strategy(self):
        """
        - Manage strategy, call in on_step
        - Including prioritize morphing orbital command
        """

        await self.counter_workers_rush()
        await self.prioritize_morph_orbital_command()
        await self.search_remain_enemies()

    async def counter_workers_rush(self):
        if (
            self.bot.macro_control_manager.worker_rush_detected
            and self.phase_number != 0
        ):
            self.phase_number = 0
            self.bot.resources_manager.resource_ratio    = 100
            self.block_all_build_hard()
            self.allow(UnitTypeId.SCV)
            self.allow(UnitTypeId.SUPPLYDEPOT)
            self.allow(UnitTypeId.MARINE)
            self.allow(UnitTypeId.BARRACKS)
            self.bot.building_manager.amount_limitation[
                UnitTypeId.BARRACKS
            ] = 1
            self.bot.building_manager.proxy_workers = []
            self.bot.building_manager.proxy_rax          = False
            self.bot.building_manager.ramp_wall          = False

    async def prioritize_morph_orbital_command(self):
        if (
            self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.amount >= 1
            and self.bot.already_pending(UnitTypeId.ORBITALCOMMAND)
                < self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.amount
            and (
                self.bot.structure_type_build_progress(
                    UnitTypeId.BARRACKS
                ) > 0.75
                or self.bot.structures(UnitTypeId.BARRACKS).ready.amount >= 1
            )
            and self.phase_number != 0
        ):
            self.only_allow(UnitTypeId.ORBITALCOMMAND)

        if self.bot.already_pending(UnitTypeId.ORBITALCOMMAND) >= 1:
            self.allow_all_build()

    async def search_remain_enemies(self):
        if (
            not self.check_only_allow(UnitTypeId.ORBITALCOMMAND)
            and self.phase_number != 100
            and self.bot.macro_control_manager.start_searching_phase
        ):
            self.phase_number = 100
            self.allow(UnitTypeId.MARINE)
            self.allow(UnitTypeId.FACTORY)
            self.allow(UnitTypeId.STARPORT)
            self.allow(UnitTypeId.VIKING)
            self.block(UnitTypeId.REAPER)
            self.bot.macro_control_manager.unit_attack_amount = dict.fromkeys(
                self.bot.macro_control_manager.unit_attack_amount,
                1
            )

    def initialize(self, block_list=[UnitTypeId.REFINERY]):
        [self.block(u) for u in block_list]

    def block_all_build(self):
        self.block_table = self.block_table.fromkeys(self.block_table, True)

    def allow_all_build(self):
        self.block_table = {
            k: (True if self.helper_table[k] == True else False)
            for (k, v) in self.block_table.items()
        }

    def block_all_build_hard(self):
        self.block_table = self.block_table.fromkeys(self.block_table, True)

    def allow_all_build_hard(self):
        self.block_table = self.block_table.fromkeys(self.block_table, False)

    def only_allow(self, id):
        self.block_table = {
            k: (True if k != id else False)
            for (k, v) in self.block_table.items()
        }

    def only_block(self, id):
        self.block_table = {
            k: (False if k != id else True)
            for (k, v) in self.block_table.items()
        }

    def allow(self, id):
        self.block_table[id]  = False
        self.helper_table[id] = False

    def block(self, id):
        self.block_table[id]  = True
        self.helper_table[id] = True

    def check_block(self, id):
        return self.block_table[id]

    def check_only_allow(self, id):
        others = all(
            self.block_table[i]
            for i in self.block_table
            if i != id
        )
        return not self.block_table[id] and others
