import sc2
from sc2.ids.unit_typeid import UnitTypeId
from sc2.units import Units
from sc2.position import Point2
from sc2.ids.ability_id import AbilityId


class ExpandBot(sc2.BotAI):
    """
    - Expand bot
    - Build bases everywhere
    - For testing if search remain enemies works
    """

    def __init__(self):
        super()._initialize_variables()
        self.locations = []

    async def on_start(self):
        self.locations = sorted(
            self.expansion_locations_list,
            key = lambda l: l.distance_to(self.start_location),
        )

    async def on_step(self, iteration):
        if (
            self.can_afford(UnitTypeId.COMMANDCENTER)
            and self.locations
        ):
            position = self.locations.pop()
            while(
                position.distance_to(self.enemy_start_locations[0]) < 40
                and self.locations
            ):
                position = self.locations.pop()
                
            if position:
                worker = self.select_build_worker(position)
            if (
                worker
                and position
            ):
                worker.build(UnitTypeId.COMMANDCENTER, position)
        for th in self.townhalls.ready.idle:
            if th.health_percentage < 0.9:
                th(AbilityId.LIFT)
