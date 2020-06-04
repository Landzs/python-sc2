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

    async def SCVs_micro_control(self):
        enemies = self.bot.enemy_units | self.bot.enemy_structures
        if enemies:
            for s in self.bot.units(UnitTypeId.SCV).filter(
                lambda s: s in self.bot.macro_control_manager.SCVs
            ):
                # SCV is ready to attack, shoot nearest ground unit
                enemies_to_attack = enemies.filter(
                    lambda u: u.distance_to(s) <= 2 and not u.is_flying
                )
                if s.weapon_cooldown == 0 and enemies_to_attack:
                    focus_enemey = self.focus_enemy(s, enemies_to_attack)
                    if focus_enemey:
                        s.attack(focus_enemey)
                    continue

            for s in self.bot.units(UnitTypeId.SCV).filter(
                lambda s: s.is_collecting or s.is_idle
            ):
                enemy_to_attack = enemies.closest_to(s)
                if (
                    enemy_to_attack
                    and enemy_to_attack.distance_to(s) <= 3
                ):
                    enemy_to_attack
                    s.attack(enemy_to_attack)

    async def marines_micro_control(self):
        enemies = self.bot.enemy_units | self.bot.enemy_structures
        enemies_can_attack = enemies.filter(
            lambda u: u.can_attack_ground
        )

        for m in self.bot.units(UnitTypeId.MARINE):
            close_enemies = enemies_can_attack.filter(
                lambda u: u.distance_to(u) < 10
            )

            # marine is ready to attack, shoot nearest ground unit
            enemies_to_attack = enemies.filter(
                lambda u: u.distance_to(m) <= 6 and not u.is_flying
            )
            if m.weapon_cooldown == 0 and enemies_to_attack:
                focus_enemey = self.focus_enemy(m, enemies_to_attack)
                if focus_enemey:
                    m.attack(focus_enemey)
                continue

            # move to max unit range if enemy is closer than 4
            close_enemies = enemies.filter(
                lambda u:
                u.can_attack_ground and u.distance_to(m) <= 4.5
            )
            if m.weapon_cooldown != 0 and close_enemies:
                self.retreat(m, 1, close_enemies)
                continue

            # move to nearest enemy to keep in range of weapon
            enemies_to_attack = self.bot.enemy_units
            structures_to_attack = self.bot.enemy_structures
            if enemies_to_attack:
                closest_enemy = enemies_to_attack.closest_to(m)
                m.attack(closest_enemy.position)
                continue
            elif structures_to_attack:
                closest_enemy = structures_to_attack.closest_to(m)
                m.attack(closest_enemy.position)
                continue

    async def reapers_micro_control(self):
        enemies = self.bot.enemy_units | self.bot.enemy_structures
        enemies_can_attack = enemies.filter(
            lambda u: u.can_attack_ground
        )

        for r in self.bot.units(UnitTypeId.REAPER):
            close_enemies = enemies_can_attack.filter(
                lambda u: u.distance_to(u) < 10
            )

            # reaper's health is too low, retreat
            if r.health_percentage < 2 / 5:
                if close_enemies:
                    self.retreat(r, 4, close_enemies)
                continue
            if (
                r.health_percentage < 4 / 5
                and not close_enemies
            ):
                r.hold_position()

            # throw grenade to furthest enemy in range 5
            grenade_range = self.bot._game_data.abilities[
                AbilityId.KD8CHARGE_KD8CHARGE.value
            ]._proto.cast_range
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
            enemies_to_attack = enemies.filter(
                lambda u: u.distance_to(r) <= 5 and not u.is_flying
            )
            if r.weapon_cooldown == 0 and enemies_to_attack:
                focus_enemey = self.focus_enemy(r, enemies_to_attack)
                if focus_enemey:
                    r.attack(focus_enemey)
                continue

            # move to max unit range if enemy is closer than 4
            close_enemies = enemies.filter(
                lambda u:
                u.can_attack_ground and u.distance_to(r) <= 4.5
            )
            if r.weapon_cooldown != 0 and close_enemies:
                self.retreat(r, 1, close_enemies)
                continue

            # move to nearest enemy to keep in range of weapon
            enemies_to_attack = self.bot.enemy_units.not_flying
            structures_to_attack = self.bot.enemy_structures.not_flying
            if enemies_to_attack:
                closest_enemy = enemies_to_attack.closest_to(r)
                r.attack(closest_enemy.position)
                continue
            elif structures_to_attack:
                closest_enemy = structures_to_attack.closest_to(r)
                r.attack(closest_enemy.position)
                continue

    async def vikings_micro_control(self):
        enemies = self.bot.enemy_units | self.bot.enemy_structures
        enemies_can_attack = enemies.filter(
            lambda u: u.can_attack_air
        )

        for v in self.bot.units(UnitTypeId.VIKINGFIGHTER):
            close_enemies = enemies_can_attack.filter(
                lambda u: u.distance_to(u) < 15
            )

            # viking is ready to attack, shoot nearest ground unit
            enemies_to_attack = enemies.filter(
                lambda u: u.distance_to(v) <= 10 and u.is_flying
            )
            if v.weapon_cooldown == 0 and enemies_to_attack:
                focus_enemey = self.focus_enemy(v, enemies_to_attack)
                if focus_enemey:
                    v.attack(focus_enemey)
                continue

            # move to max unit range if enemy is closer than 4
            close_enemies = enemies.filter(
                lambda u:
                u.can_attack_ground and u.distance_to(v) <= 4.5
            )
            if v.weapon_cooldown != 0 and close_enemies:
                self.retreat(v, 2, close_enemies)
                continue

            # move to nearest enemy to keep in range of weapon
            enemies_to_attack = self.bot.enemy_units.flying
            structures_to_attack = self.bot.enemy_structures.flying
            if enemies_to_attack:
                closest_enemy = enemies_to_attack.closest_to(v)
                v.attack(closest_enemy.position)
                continue
            elif structures_to_attack:
                closest_enemy = structures_to_attack.closest_to(v)
                v.attack(closest_enemy.position)
                continue
