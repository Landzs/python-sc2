from sc2.unit import Unit
from sc2.position import Point2
from sc2.ids.ability_id import AbilityId
from sc2.ids.unit_typeid import UnitTypeId
from typing import Union


class TerranResourcesManager:
    """
    - Basic resources management for Terran
    """

    def __init__(self, bot=None):
        self.__bot                = bot
        self.__SCVs_amount_limit  = 60
        self.__bases_amount_limit = 3
        self.__resource_ratio     = 100

    async def manage_resources(self, iteration):
        """
        - Manage resource, call in on_step
        - Including distribute workers, build resource units and structures, and manage resource structures

        parm: iteration
        """

        await self.__distribute_workers()
        await self.__build_SCVs()
        await self.__build_refinery()
        await self.__build_commandcenter()
        await self.__build_orbital()
        await self.__manage_base_move()
        await self.__manage_orbital()

    async def __build_SCVs(self):
        if (
            not self.__bot.strategy_manager.check_block(UnitTypeId.SCV)
            and self.__bot.can_afford(UnitTypeId.SCV)
            and self.__bot.supply_left > 0
            and self.__bot.supply_workers <= self.__SCVs_amount_limit
        ):
            for th in self.__bot.townhalls.ready.idle:
                if self.__bot.can_afford(UnitTypeId.SCV):
                    th.train(UnitTypeId.SCV)

    async def __build_commandcenter(self):
        if (
            self.__bot.can_afford(UnitTypeId.COMMANDCENTER)
            and self.__bot.townhalls.amount < self.__bases_amount_limit
            and not self.__bot.strategy_manager.check_block(UnitTypeId.COMMANDCENTER)
            and self.__bot.already_pending(UnitTypeId.COMMANDCENTER) == 0
        ):
            position = await self.__bot.get_next_expansion()
            if position:
                self.__bot.macro_control_manager.expanded_position = position
            await self.__bot.expand_now()

    async def __build_refinery(self):
        if not self.__bot.strategy_manager.check_block(UnitTypeId.REFINERY):
            for th in self.__bot.townhalls.ready:
                vespene_geyser = self.__bot.vespene_geyser.closer_than(10, th)
                for vg in vespene_geyser:
                    if (
                        (await self.__bot.can_place(UnitTypeId.REFINERY, [vg.position]))[0]
                        and self.__bot.can_afford(UnitTypeId.REFINERY)
                    ):
                        worker = self.__bot.select_build_worker(vg)
                        if worker:
                            worker.build(UnitTypeId.REFINERY, vg)
                            self.__bot.strategy_manager.block(UnitTypeId.REFINERY)
                            break

    async def __build_orbital(self):
        if (
            self.__bot.tech_requirement_progress(UnitTypeId.ORBITALCOMMAND) == 1
            and not self.__bot.strategy_manager.check_block(UnitTypeId.ORBITALCOMMAND)
        ):
            for cc in self.__bot.townhalls(UnitTypeId.COMMANDCENTER).idle:
                if self.__bot.can_afford(UnitTypeId.ORBITALCOMMAND):
                    cc(AbilityId.UPGRADETOORBITAL_ORBITALCOMMAND)

    async def __manage_orbital(self):
        if not self.__bot.macro_control_manager.need_scan:
            for oc in self.__bot.townhalls(UnitTypeId.ORBITALCOMMAND).filter(lambda x: x.energy >= 50):
                mineral_fields = self.__bot.mineral_field.closer_than(10, oc)
                if mineral_fields:
                    mineral_field: Unit = max(mineral_fields, key=lambda x: x.mineral_contents)
                    oc(AbilityId.CALLDOWNMULE_CALLDOWNMULE, mineral_field)

    def local_workers(self, mining_place: Unit):
        if mining_place not in self.__bot.townhalls.ready | self.__bot.gas_buildings.ready:
            return

        if mining_place.has_vespene and mining_place in self.__bot.gas_buildings.ready:
            local_workers = self.__bot.workers.filter(
                lambda unit:
                    unit.order_target == mining_place.tag
                    or (
                        unit.is_carrying_vespene
                        and unit.order_target == self.__bot.townhalls.ready.closest_to(mining_place).tag
                    )
            )
            return local_workers
        elif mining_place in self.__bot.townhalls.ready:
            local_minerals = self.minerals_near(mining_place, 12)
            local_minerals_tags = [m.tag for m in local_minerals]
            local_workers = self.__bot.workers.filter(
                lambda unit:
                    unit.order_target in local_minerals_tags
                    or (
                        unit.is_carrying_minerals
                        and unit.order_target == mining_place.tag
                    )
            )
            return local_workers

    def minerals_near(self, near : Union[Unit, Point2], distance: float):
        if isinstance(near, Unit):
            near = near.position
        return {m for m in self.__bot.mineral_field if m.distance_to(near) <= distance}

    def gas_buildings_near(self, near : Union[Unit, Point2], distance: float):
        if isinstance(near, Unit):
            near = near.position
        return {g for g in self.__bot.gas_buildings.ready if g.distance_to(near) <= distance and g.has_vespene}

    def harvesting_efficiency(self):
        """
        - Return mineral efficiency,gas efficiency and number of workers needed to be adjusted
        - Number of workers needed to be adjusted is the worker's numberneeded to be switch to gas or mineral to reach
        the resource_ratio
        - When workers_to_transfer is positive, it means we need send workers to gas. When negative, send workers to
        mineral

        param: resource_ratio
        """

        mineral_efficiency: float = 0
        gas_efficiency    : float = 0
        mineral_per_worker: float = 42
        gas_per_worker    : float = 40
        mineral_per_mule  : float = 170

        townhalls           = self.__bot.townhalls.ready
        gas_buildings       = self.__bot.gas_buildings.ready
        workers_to_transfer = 0

        mineral_efficiency  = sum(
            min(mineral_place.assigned_harvesters, mineral_place.ideal_harvesters) * mineral_per_worker
            for mineral_place in townhalls
        )

        gas_efficiency      = 0.1 + sum(
            min(gas_place.assigned_harvesters, gas_place.ideal_harvesters) * gas_per_worker
            for gas_place in gas_buildings
        )

        mule_amount         = self.__bot.units(UnitTypeId.MULE).amount
        mule_efficiency     = mule_amount * mineral_per_mule

        mineral_efficiency  += mule_efficiency

        workers_to_transfer = round(
            (mineral_efficiency - self.__resource_ratio * gas_efficiency)
            / (mineral_per_worker + self.__resource_ratio * gas_per_worker)
        )

        return [mineral_efficiency, gas_efficiency, workers_to_transfer]

    async def __distribute_workers(self):
        """
        - Distributes workers across all the bases taken.
        - Keyword `resource_ratio` takes a float. If the current harvesting efficiency of minerals to gas ratio is
        bigger than `resource_ratio`, this function prefer filling gas_buildings first, if it is lower, it will prefer
        sending workers to minerals first.

        param: resource_ratio
        """

        if (
            not self.__bot.mineral_field
            or not self.__bot.workers
            or not self.__bot.townhalls.ready
        ):
            return

        bases = self.__bot.townhalls.ready
        gas_buildings = self.__bot.gas_buildings.ready
        mining_places = bases | gas_buildings

        if self.__bot.iteration % 7 == 0:
            worker_pool = [
                w
                for w in self.__bot.workers.idle
                if (
                    w not in self.__bot.building_manager.proxy_workers
                    and w != self.__bot.building_manager.first_SCV_to_build
                )
            ]
            deficit_mining_places = []
            current_efficiency = self.harvesting_efficiency()
            current_resource_ratio = (current_efficiency[0] / current_efficiency[1])

            # distribute worker from surplus mining places to deficit place
            surplus_mining_places = [s for s in mining_places if s.surplus_harvesters != 0]
            for s in surplus_mining_places:
                difference = s.surplus_harvesters
                local_workers = self.local_workers(s)

                if difference > 0:
                    worker_pool += local_workers[:difference]
                else:
                    deficit_mining_places += [s for _ in range(-difference)]

            all_minerals_near_base = None
            if len(worker_pool) > len(deficit_mining_places):
                all_minerals_near_base = [
                    mineral
                    for mineral in self.__bot.mineral_field
                    if any(mineral.distance_to(base) <= 8 for base in self.__bot.townhalls.ready)
                ]

            for w in worker_pool:
                if deficit_mining_places:
                    possible_mining_places = None
                    if current_resource_ratio < self.__resource_ratio:
                        possible_mining_places = [p for p in deficit_mining_places if not p.vespene_contents]
                    else:
                        possible_mining_places = [p for p in deficit_mining_places if p.vespene_contents]
                    if not possible_mining_places:
                        possible_mining_places = deficit_mining_places
                    current_place = min(deficit_mining_places, key=lambda place: place.distance_to(w))
                    deficit_mining_places.remove(current_place)
                    if current_place.vespene_contents:
                        w.gather(current_place)
                    else:
                        local_minerals = self.minerals_near(current_place, 12)
                        target_mineral = max(local_minerals, key=lambda mineral: mineral.mineral_contents)
                        if target_mineral:
                            w.gather(target_mineral)
                elif w.is_idle and all_minerals_near_base:
                    target_mineral = min(all_minerals_near_base, key=lambda mineral: mineral.distance_to(w))
                    w.gather(target_mineral)

        # distribute worker based on resource ratio
        if self.__bot.iteration % 5 == 0:
            workers_to_transfer = self.harvesting_efficiency()[2]
            if workers_to_transfer >= 0:
                potential_places = gas_buildings
            else:
                workers_to_transfer = -workers_to_transfer
                potential_places = bases
            deficit_mining_places = [d for d in potential_places if d.surplus_harvesters < 0]

            for d in deficit_mining_places:
                if workers_to_transfer != 0:
                    difference = d.surplus_harvesters
                    if d.has_vespene:
                        closest_mining_place = bases.closest_to(d)
                    else:
                        closest_mining_place = gas_buildings.closest_to(d)
                    local_workers = self.local_workers(closest_mining_place)
                    workers_tansfer = min(-difference, workers_to_transfer, local_workers.amount)
                    [w.gather(d) for w in local_workers[:workers_tansfer]]
                    workers_to_transfer -= workers_tansfer

            pending_refinery = self.__bot.already_pending(UnitTypeId.REFINERY)
            already_transfered = 3 * pending_refinery
            if (workers_to_transfer - already_transfered) > 0:
                self.__bot.strategy_manager.allow(UnitTypeId.REFINERY)
            else:
                self.__bot.strategy_manager.block(UnitTypeId.REFINERY)

    async def __manage_base_move(self):
        if (
            self.__bot.iteration % 30 == 0
            and self.__bot.mineral_field
            and self.__bot.workers
            and self.__bot.townhalls.ready
        ):
            for th in self.__bot.townhalls.ready:
                local_minerals_tags = self.minerals_near(th, 8)
                local_gas_buildings = self.gas_buildings_near(th, 10)
                if not local_minerals_tags and not local_gas_buildings:
                    th(AbilityId.LIFT)
        elif self.__bot.iteration % 10 == 0:
            bases = self.__bot.structures(UnitTypeId.COMMANDCENTERFLYING)
            bases |= self.__bot.structures(UnitTypeId.ORBITALCOMMANDFLYING)
            for b in bases.filter(lambda b: b.is_idle):
                location = await self.__bot.get_next_expansion()
                b(AbilityId.LAND, location)

    @property
    def SCVs_amount_limit(self):
        return self.__SCVs_amount_limit

    @property
    def bases_amount_limit(self):
        return self.__bases_amount_limit

    @property
    def resource_ratio(self):
        return self.__resource_ratio

    @SCVs_amount_limit.setter
    def SCVs_amount_limit(self, value: int):
        self.__SCVs_amount_limit = value if value > 0 else 1

    @bases_amount_limit.setter
    def bases_amount_limit(self, value: int):
        self.__bases_amount_limit = value if value > 0 else 1

    @resource_ratio.setter
    def resource_ratio(self, value):
        self.__resource_ratio = value if value >= 2.5 else 2.5
