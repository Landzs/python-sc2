from sc2.unit import Unit
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId


class TerranResourcesManager:
    """
    - Basic resources management for Terran
    """

    def __init__(self, bot=None, priority_manager=None): 
        self.bot                  = bot
        self.priority_manager     = priority_manager
        self.workers_limitation   = 66
        self.townhalls_limitation = 3
        self.resource_ratio       = 100

    async def manage_resources(self, iteration):
        """
        - Manage resource, call in on_step
        - Including distribute workers, build resource unit and structure

        parm: iteration
        """

        if iteration % 10 == 0:
            await self.distribute_workers(self.resource_ratio)

        await self.build_workers()
        await self.build_refinery()
        await self.build_base()
        await self.build_orbital()
        await self.manage_orbital()

    async def build_workers(self):
        if (
            not self.bot.priority_manager.check_block(UnitTypeId.SCV)
            and self.bot.can_afford(UnitTypeId.SCV)
            and self.bot.supply_left > 0
            and self.bot.supply_workers <= self.workers_limitation
        ):
            for th in self.bot.townhalls.ready.idle:
                if self.bot.can_afford(UnitTypeId.SCV):
                    th.train(UnitTypeId.SCV)

    async def build_base(self):
        if (
            not self.bot.priority_manager.check_block(UnitTypeId.COMMANDCENTER)
            and self.townhalls_limitation > self.bot.townhalls.amount
            and self.bot.already_pending(UnitTypeId.COMMANDCENTER) == 0
            and self.bot.can_afford(UnitTypeId.COMMANDCENTER)
        ):
            await self.bot.expand_now()

    async def build_refinery(self):
        if not self.bot.priority_manager.check_block(UnitTypeId.REFINERY):
            for th in self.bot.townhalls.ready:
                vespene_geyser = self.bot.vespene_geyser.closer_than(10, th)
                for vg in vespene_geyser:
                    if (
                        (await self.bot.can_place(
                            UnitTypeId.REFINERY,
                            [vg.position]))[0]
                        and self.bot.can_afford(UnitTypeId.REFINERY)
                    ):
                        worker = self.bot.select_build_worker(vg)
                        if worker:
                            worker.build(UnitTypeId.REFINERY, vg)
                            self.bot.priority_manager.block(
                                UnitTypeId.REFINERY
                            )
                            break

    async def build_orbital(self):
        if (
            not self.bot.priority_manager.check_block(
                UnitTypeId.ORBITALCOMMAND
            )
            and self.bot.tech_requirement_progress(
                UnitTypeId.ORBITALCOMMAND
            ) == 1
        ):
            for cc in self.bot.townhalls(UnitTypeId.COMMANDCENTER).idle:
                if self.bot.can_afford(UnitTypeId.ORBITALCOMMAND):
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def manage_orbital(self):
        for oc in self.bot.townhalls(UnitTypeId.ORBITALCOMMAND).filter(
            lambda x: x.energy >= 50
        ):
            mfs = self.bot.mineral_field.closer_than(10, oc)
            if mfs:
                mf: Unit = max(mfs, key=lambda x: x.mineral_contents)
                oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mf)

    def harvesting_efficiency(self, resource_ratio: float = 3):
        """
        - Return mineral efficiency,gas efficiency and number of workers
        needed to be adjusted
        - Number of workers needed to be adjusted is the worker's number
        needed to be switch to gas or mineral to reach the resource_ratio
        - When workers_to_transfer is positive, it means we need send workers
        to gas. When negative, send workers to mineral

        param: resource_ratio
        """

        mineral_efficiency: float = 0
        gas_efficiency    : float = 0
        mineral_per_worker: float = 42
        gas_per_worker    : float = 40
        mineral_per_mule  : float = 170

        townhalls         = self.bot.townhalls.ready
        gas_buildings     = self.bot.gas_buildings.ready
        workers_to_transfer = 0

        mineral_efficiency = sum(
            min(
                mineral_place.assigned_harvesters,
                mineral_place.ideal_harvesters
            ) * mineral_per_worker
            for mineral_place in townhalls
        )

        gas_efficiency = 0.1 + sum(
            min(
                gas_place.assigned_harvesters,
                gas_place.ideal_harvesters
            ) * gas_per_worker
            for gas_place in gas_buildings
        )

        mule_amount = self.bot.units(UnitTypeId.MULE).amount
        mule_efficiency = mule_amount * mineral_per_mule

        mineral_efficiency += mule_efficiency

        workers_to_transfer = round(
            (mineral_efficiency - resource_ratio * gas_efficiency)
            / (mineral_per_worker + resource_ratio * gas_per_worker)
        )

        return [mineral_efficiency, gas_efficiency, workers_to_transfer]

    async def distribute_workers(self, resource_ratio: float = 3):
        """
        - Distributes workers across all the bases taken.
        - Keyword `resource_ratio` takes a float. If the current
        harvesting efficiency of minerals to gas ratio is bigger
        than `resource_ratio`, this function prefer filling
        gas_buildings first, if it is lower, it will prefer
        sending workers to minerals first.

        param: resource_ratio
        """

        if (
            not self.bot.mineral_field
            or not self.bot.workers
            or not self.bot.townhalls.ready
        ):
            return

        bases = self.bot.townhalls.ready
        gas_buildings = self.bot.gas_buildings.ready
        mining_places = bases | gas_buildings
        worker_pool = [
            worker
            for worker in self.bot.workers.idle
            if self.bot.workers_proxyrax.count(worker) == 0
        ]
        deficit_mining_places = []
        current_efficiency = self.harvesting_efficiency(resource_ratio)
        current_resource_ratio = (
            current_efficiency[0]
            / current_efficiency[1]
        )

        # distribute worker from surplus mining places to deficit place
        surplus_mining_places = [
            sp
            for sp in mining_places
            if sp.surplus_harvesters != 0
        ]
        for sp in surplus_mining_places:
            difference = sp.surplus_harvesters
            if sp.has_vespene:
                local_workers = self.bot.workers.filter(
                    lambda unit: unit.order_target == sp.tag
                    or (
                        unit.is_carrying_vespene
                        and unit.order_target == bases.closest_to(sp).tag
                    )
                )
            else:
                local_minerals_tags = {
                    mineral.tag
                    for mineral in self.bot.mineral_field
                    if mineral.distance_to(sp) <= 8
                }
                local_workers = self.bot.workers.filter(
                    lambda unit: unit.order_target in local_minerals_tags
                    or (
                        unit.is_carrying_minerals
                        and unit.order_target == sp.tag
                    )
                )
            if difference > 0:
                worker_pool += local_workers[:difference]
            else:
                deficit_mining_places += [sp for _ in range(-difference)]

        if len(worker_pool) > len(deficit_mining_places):
            all_minerals_near_base = [
                mineral
                for mineral in self.bot.mineral_field
                if any(
                    mineral.distance_to(base) <= 8
                    for base in self.bot.townhalls.ready
                )
            ]

        for worker in worker_pool:
            if deficit_mining_places:
                if current_resource_ratio < resource_ratio:
                    possible_mining_places = [
                        place
                        for place in deficit_mining_places
                        if not place.vespene_contents
                    ]
                else:
                    possible_mining_places = [
                        place
                        for place in deficit_mining_places
                        if place.vespene_contents
                    ]
                if not possible_mining_places:
                    possible_mining_places = deficit_mining_places
                current_place = min(
                    deficit_mining_places,
                    key=lambda place: place.distance_to(worker)
                )
                deficit_mining_places.remove(current_place)
                if current_place.vespene_contents:
                    worker.gather(current_place)
                else:
                    local_minerals = (
                        mineral
                        for mineral in self.bot.mineral_field
                        if mineral.distance_to(current_place) <= 8
                    )
                    target_mineral = max(
                        local_minerals,
                        key=lambda mineral: mineral.mineral_contents,
                        default=None,
                    )
                    if target_mineral:
                        worker.gather(target_mineral)
            elif worker.is_idle and all_minerals_near_base:
                target_mineral = min(
                    all_minerals_near_base,
                    key=lambda mineral: mineral.distance_to(worker),
                )
                worker.gather(target_mineral)
            else:
                pass

        # distribute worker based on resource ratio
        workers_to_transfer = self.harvesting_efficiency(resource_ratio)[2]
        if workers_to_transfer >= 0:
            potential_places = gas_buildings
        else:
            workers_to_transfer = -workers_to_transfer
            potential_places = bases
        deficit_mining_places = [
            dp
            for dp in potential_places
            if dp.surplus_harvesters < 0
        ]

        for dp in deficit_mining_places:
            if workers_to_transfer != 0:
                difference = dp.surplus_harvesters
                if not dp.has_vespene:
                    local_workers = self.bot.workers.filter(
                        lambda w: w.order_target == dp.tag
                        or (
                            w.is_carrying_vespene
                            and w.order_target == bases.closest_to(dp).tag
                        )
                    )
                    workers_tansfer = min(
                        -difference,
                        workers_to_transfer,
                        local_workers.amount,
                    )
                    [w.gather(dp) for w in local_workers[:workers_tansfer]]
                    workers_to_transfer -= workers_tansfer
                else:
                    local_minerals_tags = {
                        mineral.tag
                        for mineral in self.bot.mineral_field
                        if mineral.distance_to(dp) <= 8
                    }
                    local_workers = self.bot.workers.filter(
                        lambda w: w.order_target in local_minerals_tags
                        or (
                            w.is_carrying_minerals
                            and w.order_target == dp.tag
                        )
                    )
                    workers_tansfer = min(
                        -difference,
                        workers_to_transfer,
                        local_workers.amount,
                    )
                    [w.gather(dp) for w in local_workers[:workers_tansfer]]
                    workers_to_transfer -= workers_tansfer

        pending_refinery = self.bot.already_pending(UnitTypeId.REFINERY)
        already_transfered = 3 * pending_refinery
        if (workers_to_transfer - already_transfered) > 0:
            self.bot.priority_manager.allow(UnitTypeId.REFINERY)
        else:
            self.bot.priority_manager.block(UnitTypeId.REFINERY)
