from sc2.ids.unit_typeid import UnitTypeId


class TerranPriorityManager():
    """
    - Basic priority management for Terran
    """

    def __init__(self, bot=None):
        self.bot         = bot
        self.block_table = {
            UnitTypeId.SCV           : False,
            UnitTypeId.MARINE        : False,
            UnitTypeId.REAPER        : False,
            UnitTypeId.SUPPLYDEPOT   : False,
            UnitTypeId.BARRACKS      : False,
            UnitTypeId.COMMANDCENTER : False,
            UnitTypeId.REFINERY      : False,
            UnitTypeId.ORBITALCOMMAND: False,
        }
        self.helper_table = self.block_table.copy()

    async def manage_priority(self):
        """
        - Manage priority, call in on_step
        - Including prioritize building orbital
        """

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
        ):
            self.only_allow(UnitTypeId.ORBITALCOMMAND)

        if (
            self.check_only_allow(UnitTypeId.ORBITALCOMMAND)
            and self.bot.already_pending(UnitTypeId.ORBITALCOMMAND) >= 1
        ):
            self.allow_all_build()

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
