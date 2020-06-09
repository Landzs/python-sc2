from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId


class TerranMicroControlManager():
    """
    - Basic micro unit control management for Terran
    """

    def __init__(self, bot=None):
        self.bot = bot

    async def manage_micro_control(self):
        """
        - Manage micro unit control management, call in on_step
        - Including micro control for different units
        """

        await self.SCVs_micro_control()
        await self.marines_micro_control()
        await self.reapers_micro_control()
        await self.marauders_micro_control()
        await self.medivas_micro_control()
        await self.vikings_micro_control()

    def neighbors4(self, unit_position, search_distance=1):
        p = unit_position
        d = search_distance
        return {
            Point2((p.x - d, p.y)),
            Point2((p.x + d, p.y)),
            Point2((p.x, p.y - d)),
            Point2((p.x, p.y + d)),
        }

    def neighbors8(self, unit_position, search_distance=1):
        p = unit_position
        d = search_distance
        return self.neighbors4(p, d) | {
            Point2((p.x - d, p.y - d)),
            Point2((p.x - d, p.y + d)),
            Point2((p.x + d, p.y - d)),
            Point2((p.x + d, p.y + d)),
        }

    def retreat(self, unit, distance=1, close_enemies: Units = []):
        if close_enemies:
            points = self.neighbors8(unit.position, distance)
            points |= self.neighbors8(unit.position, distance * 2)
            points = {
                x
                for x in points
                if self.bot.in_pathing_grid(x)
            }
            if points:
                closest_enemy = close_enemies.closest_to(unit)
                point = closest_enemy.position.furthest(points)
                unit.move(point)

    def focus_enemy(self, unit, enemies_in_range):
        if enemies_in_range:
            target = min(
                enemies_in_range,
                key=lambda e:
                    (e.health + e.shield) / unit.calculate_dps_vs_target(e)
            )
            return target
        else:
            return None

    def low_health_retreat(
        self,
        unit,
        distance=1,
        enemies_distance: float = 10,
        health_retreat: float = 2 / 5,
        health_back: float = 4 / 5
    ):
        enemies = self.bot.enemy_units | self.bot.enemy_structures
        if unit.is_flying:
            enemies_can_attack = enemies.filter(lambda u: u.can_attack_air)
        else:
            enemies_can_attack = enemies.filter(lambda u: u.can_attack_ground)

        close_enemies = enemies_can_attack.filter(
            lambda u: u.distance_to(u) < enemies_distance
        )
        if (
            unit.health_percentage < health_retreat
            and close_enemies
        ):
            self.retreat(unit, distance, close_enemies)
            return True
        elif (
            unit.health_percentage < health_back
            and not close_enemies
        ):
            unit.hold_position()
            return True
        else:
            return False

    def attack_enemy(
        self,
        unit,
        enemy_distance,
    ):
        enemies = self.bot.enemy_units | self.bot.enemy_structures
        enemies_to_attack = enemies.filter(
            lambda u: u.distance_to(unit) <= enemy_distance
        )
        if not unit.can_attack_both:
            if unit.can_attack_air:
                enemies_to_attack = enemies_to_attack.filter(
                    lambda u: u.is_flying
                )
            elif unit.can_attack_ground:
                enemies_to_attack = enemies_to_attack.filter(
                    lambda u: not u.is_flying
                )

        if (
            unit.weapon_cooldown == 0
            and enemies_to_attack
        ):
            focus_enemey = self.focus_enemy(unit, enemies_to_attack)
            if focus_enemey:
                unit.attack(focus_enemey)
                return True
        else:
            return False

    def keep_distance(self, unit, enemies_distance, retreat_distance):
        enemies = self.bot.enemy_units | self.bot.enemy_structures
        if unit.is_flying:
            close_enemies = enemies.filter(
                lambda u:
                    u.can_attack_air
                    and u.distance_to(u) <= enemies_distance
            )
        else:
            close_enemies = enemies.filter(
                lambda u:
                    u.can_attack_ground
                    and u.distance_to(u) <= enemies_distance
            )
        if unit.weapon_cooldown != 0 and close_enemies:
            self.retreat(unit, retreat_distance, close_enemies)
            return True
        else:
            return False

    def keep_in_range(self, unit):
        enemies_to_attack = self.bot.enemy_units
        structures_to_attack = self.bot.enemy_structures
        if not unit.can_attack_both:
            if unit.can_attack_air:
                enemies_to_attack = enemies_to_attack.filter(
                    lambda u: u.is_flying
                )
                structures_to_attack = structures_to_attack.filter(
                    lambda u: u.is_flying
                )
            elif unit.can_attack_ground:
                enemies_to_attack = enemies_to_attack.filter(
                    lambda u: not u.is_flying
                )
                structures_to_attack = structures_to_attack.filter(
                    lambda u: u.is_flying
                )
        if enemies_to_attack:
            closest_enemy = enemies_to_attack.closest_to(unit)
            unit.attack(closest_enemy.position)
            return True
        elif structures_to_attack:
            closest_enemy = structures_to_attack.closest_to(unit)
            unit.attack(closest_enemy.position)
            return True
        else:
            return False

    async def SCVs_micro_control(self):
        for s in self.bot.units(UnitTypeId.SCV).filter(
            lambda s: s in self.bot.macro_control_manager.SCVs
        ):
            # SCV is ready to attack, attack nearest ground unit
            self.attack_enemy(s, 2)

        for s in self.bot.units(UnitTypeId.SCV).filter(
            lambda s: s.is_collecting or s.is_idle
        ):
            self.attack_enemy(s, 1)

        for s in self.bot.units(UnitTypeId.SCV).filter(
            lambda s:
                s.is_attacking
                and s.distance_to(self.bot.start_location) >= 20
                and s not in self.bot.building_manager.proxy_workers
                and s not in self.bot.macro_control_manager.SCVs
        ):
            s.move(self.bot.start_location)

    async def marines_micro_control(self):
        for m in self.bot.units(UnitTypeId.MARINE).filter(
            lambda m:
                m in self.bot.macro_control_manager.marines
                or m in self.bot.macro_control_manager.defense_units
        ):
            # marine is ready to attack, shoot nearest ground unit
            if self.attack_enemy(m, 6):
                continue

            # move to max unit range if enemy is closer than 4
            if self.keep_distance(m, 4.5, 1):
                continue

            # move to nearest enemy to keep in range of weapon
            if self.keep_in_range(m):
                continue

    async def reapers_micro_control(self):
        for r in self.bot.units(UnitTypeId.REAPER).filter(
            lambda r:
                r in self.bot.macro_control_manager.reapers
                or r in self.bot.macro_control_manager.defense_units
        ):
            # reaper's health is too low, retreat
            if self.low_health_retreat(r, 4, 10, 2 / 5, 4 / 5):
                continue

            # throw grenade to furthest enemy in range 5
            grenade_range = self.bot._game_data.abilities[
                AbilityId.KD8CHARGE_KD8CHARGE.value
            ]._proto.cast_range

            enemies = self.bot.enemy_units | self.bot.enemy_structures
            enemies_can_attack = enemies.filter(lambda u: u.can_attack_ground)
            enemies_to_attack = enemies_can_attack.filter(
                lambda u:
                not u.is_structure
                and not u.is_flying
                and u.type_id not in {UnitTypeId.LARVA, UnitTypeId.EGG}
                and u.distance_to(r) < grenade_range
            )
            if (
                grenade_range
                and (
                    r.is_attacking
                    or r.is_moving
                )
            ):
                abilities = await self.bot.get_available_abilities(r)
                enemies_to_attack = enemies_to_attack.sorted(
                    lambda x: x.distance_to(r), reverse=True
                )
                furthest_enemy = None
                for enemy in enemies_to_attack:
                    if await self.bot.can_cast(
                        r,
                        AbilityId.KD8CHARGE_KD8CHARGE,
                        enemy,
                        cached_abilities_of_unit=abilities
                    ):
                        furthest_enemy = enemy
                        break
                if furthest_enemy:
                    r(AbilityId.KD8CHARGE_KD8CHARGE, furthest_enemy)
                    continue

            # reaper is ready to attack, shoot nearest ground unit
            if self.attack_enemy(r, 5):
                continue
            # move to max unit range if enemy is closer than 4
            if self.keep_distance(r, 4.5, 1):
                continue

            # move to nearest enemy to keep in range of weapon
            if self.keep_in_range(r):
                continue

    async def marauders_micro_control(self):
        for m in self.bot.units(UnitTypeId.MARAUDER).filter(
            lambda m:
                m in self.bot.macro_control_manager.marauders
                or m in self.bot.macro_control_manager.defense_units
        ):
            # marauder is ready to attack, shoot nearest ground unit
            if self.attack_enemy(m, 6):
                continue

            # move to max unit range if enemy is closer than 4
            if self.keep_distance(m, 4.5, 0.5):
                continue

            # move to nearest enemy to keep in range of weapon
            if self.keep_in_range(m):
                continue

    async def medivas_micro_control(self):
        for m in self.bot.units(UnitTypeId.MEDIVAC):
            unhealth_unit = self.bot.units.filter(
                lambda u:
                    u.health_percentage < 1
                    and u.is_biological
            )
            unit_in_range = unhealth_unit.filter(
                lambda u: u.distance_to(m) < 10
            )

            # heal unit has lowest health
            unit_in_range = sorted(
                unit_in_range,
                key=lambda u: u.health
            )
            if unit_in_range:
                m(AbilityId.MEDIVACHEAL_HEAL, unit_in_range[0])

            # move to nearest unit whose health is not full
            if unhealth_unit:
                m.move(unhealth_unit.closest_to(m).position)
            else:
                combat_unit = self.bot.units.filter(
                    lambda u:
                        u not in self.bot.workers
                        and u not in self.bot.units(UnitTypeId.MULE)
                        and u.is_biological
                )
                m.move(combat_unit.closest_to(m).position)

    async def vikings_micro_control(self):
        for v in self.bot.units(UnitTypeId.VIKINGFIGHTER).filter(
            lambda v:
                v in self.bot.macro_control_manager.vikings
                or v in self.bot.macro_control_manager.defense_units
        ):
            # viking is ready to attack, shoot nearest ground unit
            if self.attack_enemy(v, 10):
                continue

            # move to max unit range if enemy is closer than 4
            if self.keep_distance(v, 4.5, 2):
                continue

            # move to nearest enemy to keep in range of weapon
            if self.keep_in_range(v):
                continue
