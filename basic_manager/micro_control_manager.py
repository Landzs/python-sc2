from sc2.units import Units
from sc2.position import Point2
from sc2.ids.buff_id import BuffId
from sc2.ids.ability_id import AbilityId
from sc2.ids.upgrade_id import UpgradeId
from sc2.ids.unit_typeid import UnitTypeId


class TerranMicroControlManager():
    """
    - Basic micro unit control management for Terran
    """

    def __init__(self, bot=None):
        self.__bot                    = bot
        self.__micro_cotrol_parameter = {
            # low_health_retreat: retreat_distance, enemy_units_distance, health_retreat, health_back
            # attack_enemy_units: enemy_units_distance, kill_workers_first
            # keep_distance:      enemy_units_distance, retreat_distance
            # keep_in_range:      ignore_structures, move_to_workers_first
            UnitTypeId.MARINE       : [0, 0, 0.0, 0.0, 7, False, 4.0, 1, False, False],
            UnitTypeId.REAPER       : [5, 8, 0.5, 0.8, 5, True, 4.5, 1, False, True],
            UnitTypeId.MARAUDER     : [0, 0, 0.0, 0.0, 8, False, 5.0, 1, False, False],
            UnitTypeId.VIKINGFIGHTER: [0, 0, 0.0, 0.0, 8, False, 8.0, 1, False, False],
        }

    async def manage_micro_control(self):
        """
        - Manage micro unit control management, call in on_step
        - Including micro control for different units
        """

        await self.units_micro_control()
        await self.SCVs_micro_control()
        await self.medivas_micro_control()

    def neighbors4(self, unit_position, search_distance=1):
        p = unit_position
        d = search_distance
        return {
            Point2((p.x - d, p.y)),
            Point2((p.x + d, p.y)),
            Point2((p.x, p.y - d)),
            Point2((p.x, p.y + d))
        }

    def neighbors8(self, unit_position, search_distance=1):
        p = unit_position
        d = search_distance
        return self.neighbors4(p, d) | {
            Point2((p.x - d, p.y - d)),
            Point2((p.x - d, p.y + d)),
            Point2((p.x + d, p.y - d)),
            Point2((p.x + d, p.y + d))
        }

    def retreat(self, unit, distance=1, close_enemy_unit=[]):
        if close_enemy_unit:
            points = self.neighbors8(unit.position, distance)
            points |= self.neighbors8(unit.position, distance * 2)
            points = {x for x in points if self.__bot.in_pathing_grid(x)}
            if points:
                closest_enemy_unit = close_enemy_unit.closest_to(unit)
                point = closest_enemy_unit.position.furthest(points)
                unit.move(point)

    def focus_enemy_units(self, unit, enemy_units_in_range):
        if enemy_units_in_range:
            return min(enemy_units_in_range, key=lambda e: (e.health + e.shield) / unit.calculate_dps_vs_target(e))
        else:
            return None

    def low_health_retreat(
        self,
        unit,
        retreat_distance: float = 1,
        enemy_units_distance: float = 10,
        health_retreat: float = 0.4,
        health_back: float = 0.8
    ):
        if retreat_distance == 0 or unit.health_percentage >= health_back:
            return False

        if unit.is_flying:
            enemy_units_can_attack = self.__bot.enemy_units_attack_air
            enemy_units_can_attack |= self.__bot.enemy_structures_attack_air
        else:
            enemy_units_can_attack = self.__bot.enemy_units_attack_ground
            enemy_units_can_attack |= self.__bot.enemy_structures_attack_ground

        close_enemy_unit = enemy_units_can_attack.filter(
            lambda u:
                u.distance_to(u) < enemy_units_distance
                and u.type_id not in self.__bot.worker_type_id
        )

        if unit.health_percentage < health_retreat:
            if close_enemy_unit:
                self.retreat(unit, retreat_distance, close_enemy_unit)
            else:
                unit.hold_position()
            return True
        else:
            return False

    def attack_enemy_units(self, unit, enemy_units_distance: float = 0, kill_workers_first: bool = False):
        enemy_units_to_attack         = self.__bot.enemy_units
        distance_to_mineral           = self.__bot.enemy_minerals.closest_distance_to(unit)
        distance_threshold_to_mineral = 5

        if not unit.can_attack_both:
            if unit.can_attack_air:
                enemy_units_to_attack = self.__bot.enemy_units_air
            elif unit.can_attack_ground:
                enemy_units_to_attack = self.__bot.enemy_units_ground
        enemy_units_to_attack = enemy_units_to_attack.filter(lambda u: u.type_id not in self.__bot.ignore_type_id)

        if distance_to_mineral < distance_threshold_to_mineral or not kill_workers_first:
            structures_to_attack = self.__bot.enemy_structures
            if not unit.can_attack_both:
                if unit.can_attack_air:
                    structures_to_attack = self.__bot.enemy_structures_air
                elif unit.can_attack_ground:
                    structures_to_attack = self.__bot.enemy_structures_ground
            enemy_units_to_attack |= structures_to_attack
        enemy_units_to_attack = enemy_units_to_attack.filter(lambda u: u.distance_to(unit) <= enemy_units_distance)

        if unit.weapon_cooldown == 0 and enemy_units_to_attack:
            focus_enemey = self.focus_enemy_units(unit, enemy_units_to_attack)
            if focus_enemey:
                unit.attack(focus_enemey)
                return True
        else:
            return False

    def keep_distance(self, unit, enemy_units_distance, retreat_distance):
        close_enemy_unit = self.__bot.all_enemy_units

        if unit.is_flying:
            close_enemy_unit = self.__bot.enemy_units_attack_air
        else:
            close_enemy_unit = self.__bot.enemy_units_attack_ground
        close_enemy_unit = close_enemy_unit.filter(
            lambda u:
                u.distance_to(unit) <= enemy_units_distance
                and u.type_id not in self.__bot.ignore_type_id
        )
        if unit.weapon_cooldown != 0 and close_enemy_unit:
            self.retreat(unit, retreat_distance, close_enemy_unit)
            return True
        else:
            return False

    def keep_in_range(self, unit, ignore_structures=False, move_to_workers_first=False):
        enemy_units_minerals          = self.__bot.enemy_minerals
        distance_to_mineral           = enemy_units_minerals.closest_distance_to(unit)
        closest_mineral               = enemy_units_minerals.closest_to(unit)
        enemy_units_to_attack: Units  = Units([], self)
        enemy_units_in_range: Units   = Units([], self)
        structures_in_range: Units    = Units([], self)
        attack_range                  = 0
        distance_threshold_to_mineral = 6

        if unit.can_attack_air:
            attack_range          = unit.air_range  + 1
            enemy_units_in_range  |= self.__bot.enemy_units_air.filter(lambda e: e.distance_to(unit) <= attack_range)

        if unit.can_attack_ground:
            attack_range          = unit.ground_range + 1
            enemy_units_in_range  |= self.__bot.enemy_units_ground.filter(lambda e: e.distance_to(unit) <= attack_range)

        structures_in_range   = self.__bot.enemy_structures.filter(lambda e: e.distance_to(unit) <= attack_range)
        enemy_units_in_range  = enemy_units_in_range.filter(lambda u: u.type_id not in self.__bot.ignore_type_id)
        enemy_units_to_attack = self.__bot.enemy_units.filter(lambda u: u.type_id not in self.__bot.ignore_type_id)

        if (
            structures_in_range
            and not move_to_workers_first
            or enemy_units_in_range
        ):
            return False

        if enemy_units_to_attack:
            closest_enemy_unit = enemy_units_to_attack.closest_to(unit)
            keep_range         = unit.air_range - 1 if closest_enemy_unit.is_flying else unit.ground_range - 1
            position           = closest_enemy_unit.position.towards(unit, keep_range)
            unit.move(position)
            return True
        elif (
            move_to_workers_first
            and not self.__bot.macro_control_manager.start_searching_phase
            and distance_to_mineral > distance_threshold_to_mineral
        ):
            position = closest_mineral.position.towards(unit, distance_threshold_to_mineral - 2)
            unit.move(position)
            return True
        elif self.__bot.enemy_structures and not ignore_structures:
            closest_enemy_unit = self.__bot.enemy_structures.closest_to(unit)
            position           = closest_enemy_unit.position.towards(unit, attack_range)
            unit.move(closest_enemy_unit.position)
            return True
        else:
            return False

    def stimpack(self, unit):
        attack_range          = unit.ground_range
        enemy_units_to_attack = Units([], self)
        health_threshold      = 20

        if unit.can_attack_air:
            enemy_units_to_attack |= self.__bot.enemy_units_air
        elif unit.can_attack_ground:
            enemy_units_to_attack |= self.__bot.enemy_units_ground

        if not enemy_units_to_attack:
            return False

        enemy_units_to_attack = enemy_units_to_attack.filter(lambda u: u.type_id not in self.__bot.ignore_type_id)
        enemy_units_in_range  = self.__bot.enemy_units.filter(lambda u: u.distance_to(unit) < attack_range + 2)
        if (
            enemy_units_in_range
            and self.__bot.already_pending_upgrade(UpgradeId.STIMPACK) == 1
            and not unit.has_buff(BuffId.STIMPACK)
            and not unit.has_buff(BuffId.STIMPACKMARAUDER)
            and unit.health >= health_threshold
        ):
            unit(AbilityId.EFFECT_STIM)
            return True

    async def grenade(self, unit):
        grenade_range         = 5
        enemy_units_to_attack = self.__bot.enemy_units_ground.filter(
            lambda u:
                u.type_id not in self.__bot.ignore_type_id
                and u.distance_to(unit) < grenade_range
        )
        if unit.is_attacking or unit.is_moving:
            abilities = await self.__bot.get_available_abilities(unit)
            enemy_units_to_attack = enemy_units_to_attack.sorted(lambda x: x.distance_to(unit), reverse=True)
            furthest_enemy_units = None
            for enemy_units in enemy_units_to_attack:
                if await self.__bot.can_cast(
                    unit,
                    AbilityId.KD8CHARGE_KD8CHARGE,
                    enemy_units,
                    cached_abilities_of_unit=abilities
                ):
                    furthest_enemy_units = enemy_units
                    break
            if furthest_enemy_units:
                unit(AbilityId.KD8CHARGE_KD8CHARGE, furthest_enemy_units)
                return True
            else:
                return False

    async def SCVs_micro_control(self):
        # defense worker rush
        attack_distance = 2
        for s in self.__bot.units(UnitTypeId.SCV).filter(lambda s: s in self.__bot.macro_control_manager.SCVs):
            self.attack_enemy_units(s, attack_distance)

        # move SCVs back when enemy workers leave
        max_chase_distance = 20
        for s in self.__bot.units(UnitTypeId.SCV).filter(
            lambda s:
                s.is_attacking
                and s.distance_to(self.__bot.start_location) >= max_chase_distance
                and s not in self.__bot.building_manager.proxy_workers
        ):
            s.move(self.__bot.start_location)

        attack_distance = 3
        for s in self.__bot.units(UnitTypeId.SCV).filter(lambda s: s.is_collecting or s.is_idle):
            self.attack_enemy_units(s, attack_distance)

    async def units_micro_control(self):
        combat_units = self.__bot.macro_control_manager.attack_units | self.__bot.macro_control_manager.defense_units
        for u in self.__bot.units.filter(lambda u: u in combat_units):
            # unit's health is too low, retreat
            retreat_distance     = self.__micro_cotrol_parameter[u.type_id][0]
            enemy_units_distance = self.__micro_cotrol_parameter[u.type_id][1]
            health_retreat       = self.__micro_cotrol_parameter[u.type_id][2]
            health_back          = self.__micro_cotrol_parameter[u.type_id][3]
            if self.low_health_retreat(u, retreat_distance, enemy_units_distance, health_retreat, health_back):
                continue

            # stimpack
            if (u.type_id == UnitTypeId.MARAUDER or UnitTypeId.MARINE) and self.stimpack(u):
                continue

            # throw grenade to furthest enemy_units in range 5
            if u.type_id == UnitTypeId.REAPER and await self.grenade(u):
                continue

            # unit is ready to attack, shoot nearest ground unit
            enemy_units_distance = self.__micro_cotrol_parameter[u.type_id][4]
            kill_workers_first   = self.__micro_cotrol_parameter[u.type_id][5]
            if self.attack_enemy_units(u, enemy_units_distance, kill_workers_first):
                continue

            # move to max unit range if enemy_units is closer than specific distance
            enemy_units_distance = self.__micro_cotrol_parameter[u.type_id][6]
            retreat_distance     = self.__micro_cotrol_parameter[u.type_id][7]
            if self.keep_distance(u, enemy_units_distance, retreat_distance):
                continue

            # move to nearest enemy_units to keep in range of weapon
            ignore_structures     = self.__micro_cotrol_parameter[u.type_id][8]
            move_to_workers_first = self.__micro_cotrol_parameter[u.type_id][9]
            if u in self.__bot.macro_control_manager.defense_units:
                self.keep_in_range(u, True, move_to_workers_first)
            else:
                self.keep_in_range(u, ignore_structures, move_to_workers_first)

    async def medivas_micro_control(self):
        for m in self.__bot.units(UnitTypeId.MEDIVAC):
            distance_threshold = 10
            unhealth_unit = self.__bot.units.filter(lambda u: u.health_percentage < 1 and u.is_biological)
            unit_in_range = unhealth_unit.filter(lambda u: u.distance_to(m) < distance_threshold)

            # heal unit has lowest health
            unit_in_range = sorted(unit_in_range, key=lambda u: u.health)
            if unit_in_range:
                m(AbilityId.MEDIVACHEAL_HEAL, unit_in_range[0])
                continue

            # move to nearest unit whose health is not full
            if unhealth_unit:
                m.move(unhealth_unit.closest_to(m).position)
            else:
                combat_unit = self.__bot.units.filter(
                    lambda u:
                        u not in self.__bot.workers
                        and u not in self.__bot.units(UnitTypeId.MULE)
                        and u.is_biological
                )
                if combat_unit:
                    m.move(combat_unit.closest_to(m).position)
