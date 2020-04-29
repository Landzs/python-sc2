import asyncio

import sc2
from sc2 import Difficulty, Race, maps, run_game
from sc2.constants import *
from sc2.player import Bot, Computer



class TerranEconomyAI(sc2.BotAI):
    """
    - basic economy control for Terran
    """
    def __init__(self):
        self.worker_limit    = 50
        self.townhalls_limit = 3
        
        self.block_distribute_workers = False
        self.block_build_supply       = False
        self.block_build_workers      = False
        self.block_expand             = False
        self.block_build_barracks     = False
        self.block_morph_orbital      = False
        self.block_manage_orbital     = False
        self.block_barracks= False
    async def on_step(self, iteration):
        
        if not self.block_distribute_workers:
            await self.distribute_workers()
        
        if not self.block_build_supply:
            await self.build_supply()
        
        if not self.block_build_workers:
            await self.build_workers()
        
        if not self.block_expand:    
            await self.expand()
        
        if not self.block_barracks:
            await self.build_barracks()
            
        if not self.block_morph_orbital:
            await self.morph_orbital()
            
        if not self.block_manage_orbital:
            await self.manage_orbital()

        await self.update_priority()

    async def update_priority(self):
        
        # Stop scv production when barracks is complete but we still have a command center (prioritize morphing to orbital command)
        if  (
            self.block_build_workers == False
            and self.townhalls(UnitTypeId.COMMANDCENTER)
            and self.structure_type_build_progress(UnitTypeId.BARRACKS) > 0.8
        ):
            self.block_build_workers = True
        
        if  (
            self.block_build_workers == True
            and (
                self.structures(UnitTypeId.BARRACKS).ready.amount < 1
                or not self.townhalls(UnitTypeId.COMMANDCENTER)
            )
        ):
            self.block_build_workers = False

    async def build_workers(self):
        
        if (
            self.can_afford(UnitTypeId.SCV)
            and self.supply_left > 0
            and self.supply_workers <= self.worker_limit
            and self.townhalls.ready.idle
        ):
            for th in self.townhalls.ready.idle:
                if self.can_afford(UnitTypeId.SCV):
                    th.train(UnitTypeId.SCV)

    async def expand(self):
        if (
            self.townhalls_limit > self.townhalls.amount
            and self.already_pending(UnitTypeId.COMMANDCENTER) == 0 
            and self.can_afford(UnitTypeId.COMMANDCENTER)
        ):
            await self.expand_now()

    async def build_supply(self):
        ccs = self.townhalls(UnitTypeId.COMMANDCENTER).ready
        if ccs.exists:
            cc = ccs.first
            if self.supply_left < 4 and not self.already_pending(UnitTypeId.SUPPLYDEPOT):
                if self.can_afford(UnitTypeId.SUPPLYDEPOT):
                    await self.build(UnitTypeId.SUPPLYDEPOT, near=cc.position.towards(self.game_info.map_center, 5))
                    
    async def build_barracks(self):
        # Build up to 4 barracks if we can afford them
        # Check if we have a supply depot (tech requirement) before trying to make barracks
        barracks_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.BARRACKS)
        if (
            barracks_tech_requirement == 1
            # self.structures.of_type(
            #     [UnitTypeId.SUPPLYDEPOT, UnitTypeId.SUPPLYDEPOTLOWERED, UnitTypeId.SUPPLYDEPOTDROP]
            # ).ready
            and self.structures(UnitTypeId.BARRACKS).ready.amount + self.already_pending(UnitTypeId.BARRACKS) < 1
            and self.can_afford(UnitTypeId.BARRACKS)
        ):
            workers: Units = self.workers.gathering
            if (
                workers and self.townhalls
            ):  # need to check if townhalls.amount > 0 because placement is based on townhall location
                worker: Unit = workers.furthest_to(workers.center)
                # I chose placement_step 4 here so there will be gaps between barracks hopefully
                location: Point2 = await self.find_placement(
                    UnitTypeId.BARRACKS, self.townhalls.random.position, placement_step=4
                )
                if location:
                    worker.build(UnitTypeId.BARRACKS, location)
    
    
    async def morph_orbital(self):
        # Morph commandcenter to orbitalcommand
        # Check if tech requirement for orbital is complete (e.g. you need a barracks to be able to morph an orbital)
        orbital_tech_requirement: float = self.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND)
        if orbital_tech_requirement == 1:
            # Loop over all idle command centers (CCs that are not building SCVs or morphing to orbital)
            for cc in self.townhalls(UnitTypeId.COMMANDCENTER).idle:
                # Check if we have 150 minerals; this used to be an issue when the API returned 550 (value) of the orbital, but we only wanted the 150 minerals morph cost
                if self.can_afford(UnitTypeId.ORBITALCOMMAND):
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)
        
        
    async def manage_orbital(self):
        # Manage orbital energy and drop mules
        for oc in self.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
            mfs: Units = self.mineral_field.closer_than(10, oc)
            if mfs:
                mf: Unit = max(mfs, key=lambda x: x.mineral_contents)
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)


run_game(
    maps.get("AcropolisLE"),
    [Bot(Race.Terran, TerranEconomyAI()), Computer(Race.Terran, Difficulty.Easy)],
    realtime=True,
    )
