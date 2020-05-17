from sc2.units import Units
from sc2.position import Point2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.ids.ability_id import AbilityId


class TerranMicroControlManager():
    """
    - Basic micro unit control management for Terran
    """

    def __init__(self, bot=None):
        self.bot            = bot

    async def manage_micro_control(self):
        """
        - Manage micro unit control management, call in on_step
        - Including micro control for different units
        """

        await self.reapers_micro_control()

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
        target = max(
            enemies_in_range,
            key=lambda e: unit.calculate_dps_vs_target(e) / e.health
        )
        return target

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
            ground_enemies = enemies_can_attack.filter(
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
                ground_enemies = ground_enemies.sorted(
                    lambda x: x.distance_to(r), reverse=True
                )
                furthest_enemy = None
                for enemy in ground_enemies:
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
            ground_enemies = enemies.filter(
                lambda u: u.distance_to(r) <= 5 and not u.is_flying
            )
            if r.weapon_cooldown == 0 and ground_enemies:
                focus_enemey = self.focus_enemy(r, ground_enemies)
                r.attack(focus_enemey)
                continue

            # move to max unit range if enemy is closer than 4
            close_enemies = enemies.filter(
                lambda u:
                u.can_attack_ground and u.distance_to(r) <= 4.5
            )
            if r.weapon_cooldown != 0 and close_enemies:
                self.retreat(r, 0.5, close_enemies)
                continue

            # move to nearest enemy to keep in range of weapon
            ground_enemies = self.bot.enemy_units.not_flying
            if ground_enemies:
                closest_enemy = ground_enemies.closest_to(r)
                r.move(closest_enemy)
                continue
