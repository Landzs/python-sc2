import sc2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2.position import Point2


class WorkerRushBot(sc2.BotAI):
    """
    - Worker Rush
    """

    def __init__(self):
        super()._initialize_variables()
        self.close_to_enemies_base = False
        self.all_retreat = False
        self.last_probe_moved = False
        self.low_health_amount  = 0
        self.low_health_probe: Units = []
        self.base_mineral = []

    async def on_step(self, iteration):
        if iteration == 0:
            for w in self.workers:
                w.move(self.enemy_start_locations[0])
            self.townhalls.ready[0].train(UnitTypeId.PROBE)
            self.base_mineral = self.mineral_field.closest_to(
                self.townhalls.ready[0]
            )
        if self.units:
            distance_to_enemies_base = self.units.closest_distance_to(
                self.enemy_start_locations[0]
            )
        else:
            distance_to_enemies_base = 1000

        if (
            distance_to_enemies_base < 20
            and not self.close_to_enemies_base
        ):
            self.close_to_enemies_base = True
        if iteration > 10:
            probes = self.units(UnitTypeId.PROBE).collecting
            # probes = self.units(UnitTypeId.PROBE).closest_to(self.base_mineral)
            [p.move(self.enemy_start_locations[0])  for p in probes]
        if not self.units:
            await self.client.leave()
        await self.probes_micro_control()
    
    async def on_end(self, game_result):
        print(f"on_end() was called with result: {game_result}")
    
    async def probes_micro_control(self):
        enemies = self.enemy_units
        enemies_can_attack = enemies.filter(
            lambda u: u.can_attack_ground
        )
        if (
            enemies
            and self.close_to_enemies_base
        ):
            for p in self.units(UnitTypeId.PROBE).filter(
                lambda p: p not in self.low_health_probe
            ):
                close_enemies = enemies_can_attack.filter(
                    lambda u: u.distance_to(u) < 5
                )

                # probe's health is too low, retreat
                # if p.shield_percentage < 1 / 10:
                #     if close_enemies:
                #         p.gather(self.base_mineral)
                #         self.low_health_amount += 1
                #         self.low_health_probe.append(p)
                    # continue

                # probe is ready to attack, shoot nearest ground unit
                enemies_to_attack = enemies.filter(
                    lambda u: u.distance_to(p) <= 2 and not u.is_flying
                )
                if p.weapon_cooldown == 0 and enemies_to_attack:
                    focus_enemey = self.focus_enemy(p, enemies_to_attack)
                    if focus_enemey:
                        p.attack(focus_enemey)
                    continue

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
