from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.unit_typeid import UnitTypeId
from sc2.dicts.unit_trained_from import UNIT_TRAINED_FROM


class TerranProductionManager():
    """
    - Basic production management for Terran
    """

    def __init__(self, bot=None):
        self.__bot             = bot
        self.__training_amount = {
            "Base Structures": {
                UnitTypeId.MARINE       : 0,
                UnitTypeId.MARAUDER     : 0,
                UnitTypeId.REAPER       : 0,
                UnitTypeId.MEDIVAC      : 0,
                UnitTypeId.VIKINGFIGHTER: 0,
            },
            "Proxy Structures": {
                UnitTypeId.MARINE       : 0,
                UnitTypeId.MARAUDER     : 0,
                UnitTypeId.REAPER       : 0,
                UnitTypeId.MEDIVAC      : 0,
                UnitTypeId.VIKINGFIGHTER: 0,
            }
        }
        self.__research_type_id = [
            UpgradeId.STIMPACK,
            UpgradeId.SHIELDWALL,
            UpgradeId.PUNISHERGRENADES,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL1,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL2,
            UpgradeId.TERRANINFANTRYWEAPONSLEVEL3,
            UpgradeId.TERRANINFANTRYARMORSLEVEL1,
            UpgradeId.TERRANINFANTRYARMORSLEVEL2,
            UpgradeId.TERRANINFANTRYARMORSLEVEL3,
        ]

    async def manage_production(self, iteration):
        """
        - Manage basic production
        - Including training units and upgrade tech
        """

        await self.manage_structures_training("Base Structures")
        await self.manage_structures_training("Proxy Structures")
        await self.manage_research()

    async def manage_structures_training(self, structures_group):
        assert structures_group == "Base Structures" or "Proxy Structures"

        structures = self.__bot.building_manager.structures[structures_group]
        for type_id , amount in self.__training_amount[structures_group].items():
            traning_structure = structures[next(iter(UNIT_TRAINED_FROM[type_id]))]
            if (
                amount > 0
                and traning_structure
                and not self.__bot.strategy_manager.check_block(type_id)
            ):
                self.__bot.train(type_id, amount, assigned_training_structures=traning_structure)

    async def manage_research(self):
        for type_id in self.__research_type_id:
            if (
                not self.__bot.strategy_manager.check_block(type_id)
                and self.__bot.already_pending_upgrade(type_id) == 0
            ):
                self.__bot.research(type_id)

    def set_base_training_amount(self, type_id, amount):
        self.__training_amount["Base Structures"][type_id] = amount

    def set_proxy_training_amount(self, type_id, amount):
        self.__training_amount["Proxy Structures"][type_id] = amount

    def get_base_training_amount(self, type_id):
        return self.__training_amount["Base Structures"][type_id]

    def get_proxy_training_amount(self, type_id):
        return self.__training_amount["Proxy Structures"][type_id]
