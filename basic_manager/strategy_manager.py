from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.unit_typeid import UnitTypeId


class TerranStrategyManager():
    """
    - Basic strategy management for Terran
    - Including defense rush, prioritize morph orbital command and search remain enemies strategy
    """

    def __init__(self, bot=None):
        self.__bot         = bot
        self.__block_table = {
            UnitTypeId.SCV                       : False,
            UnitTypeId.MARINE                    : False,
            UnitTypeId.MARAUDER                  : False,
            UnitTypeId.REAPER                    : False,
            UnitTypeId.MEDIVAC                   : False,
            UnitTypeId.VIKINGFIGHTER             : False,
            UnitTypeId.SUPPLYDEPOT               : False,
            UnitTypeId.ENGINEERINGBAY            : False,
            UnitTypeId.ARMORY                    : False,
            UnitTypeId.BARRACKS                  : False,
            UnitTypeId.FACTORY                   : False,
            UnitTypeId.STARPORT                  : False,
            UnitTypeId.COMMANDCENTER             : False,
            UnitTypeId.REFINERY                  : False,
            UnitTypeId.BUNKER                    : False,
            UnitTypeId.ORBITALCOMMAND            : False,
            UnitTypeId.BARRACKSTECHLAB           : False,
            UnitTypeId.BARRACKSREACTOR           : False,
            UnitTypeId.FACTORYTECHLAB            : False,
            UnitTypeId.FACTORYREACTOR            : False,
            UnitTypeId.STARPORTTECHLAB           : False,
            UnitTypeId.STARPORTREACTOR           : False,
            UpgradeId.STIMPACK                   : False,
            UpgradeId.SHIELDWALL                 : False,
            UpgradeId.PUNISHERGRENADES           : False,
            UpgradeId.TERRANINFANTRYARMORSLEVEL1 : False,
            UpgradeId.TERRANINFANTRYARMORSLEVEL2 : False,
            UpgradeId.TERRANINFANTRYARMORSLEVEL3 : False,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL1: False,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL2: False,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL3: False,
        }
        self.__helper_table = self.__block_table.copy()

    async def manage_baisc_strategy(self):
        """
        - Manage strategy, call in on_step
        - Including prioritize morphing orbital command
        """

        await self.__defense_rush()
        await self.__prioritize_morph_orbital_command()
        await self.__search_remain_enemies()

    async def __defense_rush(self):
        if (
            self.__bot.macro_control_manager.close_enemy_units
            and self.__bot.macro_control_manager.closest_distance < 90
            and all(e.type_id in self.__bot.worker_typeid for e in self.__bot.enemy_units)
            and all(o.type_id in self.__bot.worker_typeid for o in self.__bot.units)
            and len(self.__bot.macro_control_manager.close_enemy_units) >= 3
        ):
            self.__bot.phase_manager.switch_to_phase("Defense Worker Rush")

        if (
            self.__bot.supply_used <= 23
            and len(self.__bot.enemy_townhalls) < 2
            and len(self.__bot.enemy_combat_units[UnitTypeId.ZERGLING])
            and not self.__bot.enemy_tech_structure[UnitTypeId.ROACHWARREN]
        ):
            self.__bot.phase_manager.switch_to_phase("Defense Zergling Rush")

        if (
            self.__bot.supply_used <= 29
            and self.__bot.enemy_tech_structure[UnitTypeId.ROACHWARREN]
        ):
            self.__bot.phase_manager.switch_to_phase("Defense Roach Rush")

    async def __prioritize_morph_orbital_command(self):
        if (
            self.__bot.townhalls(UnitTypeId.COMMANDCENTER).ready.amount >= 1
            and self.__bot.already_pending(UnitTypeId.ORBITALCOMMAND)
                < self.__bot.townhalls(UnitTypeId.COMMANDCENTER).ready.amount
            and (
                self.__bot.structure_type_build_progress(UnitTypeId.BARRACKS) > 0.75
                or self.__bot.structures(UnitTypeId.BARRACKS).ready.amount >= 1
            )
            and self.__bot.current_phase != "Defense Worker Rush"
        ):
            self.only_allow(UnitTypeId.ORBITALCOMMAND)

        if self.__bot.already_pending(UnitTypeId.ORBITALCOMMAND) >= 1:
            self.allow_all_build()

    async def __search_remain_enemies(self):
        if (
            self.__bot.units.closest_distance_to(self.__bot.macro_control_manager.attack_target) < 5
            and not self.__bot.enemy_units_ground
        ):
            self.__bot.phase_manager.switch_to_phase("Search Enemies")

    def initialize_block_list(self, block_list=[UnitTypeId.REFINERY]):
        [self.block(u) for u in block_list]

    def block_all_build(self):
        self.__block_table = self.__block_table.fromkeys(self.__block_table, True)

    def allow_all_build(self):
        self.__block_table = {k: (True if self.__helper_table[k] == True else False) for k in self.__block_table}

    def block_all_build_hard(self):
        self.__block_table = self.__block_table.fromkeys(self.__block_table, True)

    def allow_all_build_hard(self):
        self.__block_table = self.__block_table.fromkeys(self.__block_table, False)

    def only_allow(self, id):
        self.__block_table = {k: (True if k != id else False) for k in self.__block_table}

    def only_block(self, id):
        self.__block_table = {k: (False if k != id else True) for k in self.__block_table}

    def allow(self, id: UnitTypeId):
        if not self.check_only_allow(UnitTypeId.ORBITALCOMMAND):
            self.__block_table[id] = self.__helper_table[id] = False

    def block(self, id):
        if not self.check_only_allow(UnitTypeId.ORBITALCOMMAND):
            self.__block_table[id]  = self.__helper_table[id] = True

    def check_block(self, id):
        return self.__block_table[id]

    def check_only_allow(self, id):
        others_status = all(self.__block_table[i] for i in self.__block_table if i != id)
        return not self.__block_table[id] and others_status
