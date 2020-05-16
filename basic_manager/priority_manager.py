import numpy as np
from sc2.ids.unit_typeid import UnitTypeId


class TerranPriorityManager():
    """
    - Basic priority management for Terran
    """

    def __init__(self, bot=None):
        self.bot                = bot
        self.cost_table         = np.array([], dtype=np.bool)
        self.block_table        = np.array([], dtype=np.bool)
        self.block_helper_table = np.array([], dtype=np.bool)
        self.name_table         = np.array([], dtype=np.str)

    async def manage_priority(self):
        """
        - Manage priority, call in on_step
        - Including prioritize building orbital
        """

        cc_amt  = self.bot.townhalls(UnitTypeId.COMMANDCENTER).ready.amount
        oc_pdg  = self.bot.already_pending(UnitTypeId.ORBITALCOMMAND)
        bks_prg = self.bot.structure_type_build_progress(UnitTypeId.BARRACKS)
        bks_amt = self.bot.structures(UnitTypeId.BARRACKS).ready.amount

        if (
            cc_amt >= 1
            and oc_pdg < cc_amt
            and (
                bks_prg > 0.75
                or bks_amt >= 1
            )
        ):
            self.block_all_build_except("build_orbital")

        if (
            self.check_only_allow("build_orbital")
            and oc_pdg >= 1
        ):
            self.allow_all_build()

    def initialize(self, block_list=["build_refinery"]):
        self.generate_name_table(self.bot.resources_manager)
        self.generate_name_table(self.bot.building_manager)
        self.generate_name_table(self.bot.production_manager)
        self.block_table        = np.full(np.size(self.name_table), False)
        self.block_helper_table = np.full(np.size(self.name_table), False)
        [self.block(s) for s in block_list]

    def generate_name_table(self, manager):
        function_list = [
            func
            for func in dir(manager)
            if callable(getattr(manager, func)) and not func.startswith("__")
        ]
        function_list = list(filter(lambda i: "build" in i, function_list))
        self.name_table = np.append(self.name_table, function_list)

    def block_all_build(self):
        self.block_table[self.block_helper_table == True]  = True
        self.block_table[self.block_helper_table == False] = True

    def allow_all_build(self):
        self.block_table[self.block_helper_table == True]  = True
        self.block_table[self.block_helper_table == False] = False

    def block_all_build_hard(self):
        self.block_table = np.full(np.size(self.block_table), True)

    def allow_all_build_hard(self):
        self.block_table = np.full(np.size(self.block_table), False)

    def block_all_build_except(self, action):
        self.block_table[self.name_table != action] = True

    def allow_all_build_except(self, action):
        self.block_table[self.name_table != action] = False

    def allow(self, action):
        self.block_table[self.name_table == action]        = False
        self.block_helper_table[self.name_table == action] = False

    def block(self, action):
        self.block_table[self.name_table == action]        = True
        self.block_helper_table[self.name_table == action] = True

    def check_block(self, action):
        return self.block_table[self.name_table == action]

    def check_only_allow(self, action):
        others = all(
            x
            for x in self.block_table[self.name_table != action]
        )
        return not self.block_table[self.name_table == action] and others
