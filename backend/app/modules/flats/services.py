from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.core.pagination import Page
from app.modules.buildings.models import Building
from app.modules.buildings.repositories import BuildingRepository
from app.modules.flats.models import Flat
from app.modules.flats.repositories import FlatFilters, FlatRepository
from app.modules.flats.schemas import FlatCreate, FlatUpdate


class FlatService:
    def __init__(self, flats: FlatRepository, buildings: BuildingRepository) -> None:
        self.flats = flats
        self.buildings = buildings

    async def list(self, filters: FlatFilters, page: Page) -> list[Flat]:
        return await self.flats.list(filters, page)

    async def get(self, flat_id: int) -> Flat:
        flat = await self.flats.get(flat_id)
        if flat is None:
            raise NotFoundError("Flat not found")
        return flat

    async def _get_building(self, building_id: int) -> Building:
        building = await self.buildings.get(building_id)
        if building is None:
            raise NotFoundError("Building not found")
        return building

    @staticmethod
    def _check_floor(floor: int, building: Building) -> None:
        if floor > building.total_floors:
            raise UnprocessableError(
                "floor", f"{building.name} only has {building.total_floors} floors"
            )

    async def _check_unique(
        self, building: Building, flat_no: str, exclude_id: int | None = None
    ) -> None:
        if await self.flats.flat_no_taken(building.id, flat_no, exclude_id=exclude_id):
            raise ConflictError(f"Flat {flat_no} already exists in {building.name}")

    async def create(self, data: FlatCreate) -> Flat:
        building = await self._get_building(data.building_id)
        self._check_floor(data.floor, building)
        await self._check_unique(building, data.flat_no)

        flat = Flat(**data.model_dump())
        await self.flats.add(flat)
        await self.flats.commit()
        return await self.get_fresh(flat.id)

    async def update(self, flat_id: int, data: FlatUpdate) -> Flat:
        flat = await self.get(flat_id)
        changes = data.changes()

        building = flat.building
        if "building_id" in changes and changes["building_id"] != flat.building_id:
            building = await self._get_building(changes["building_id"])
        self._check_floor(changes.get("floor", flat.floor), building)
        if "building_id" in changes or "flat_no" in changes:
            await self._check_unique(
                building, changes.get("flat_no", flat.flat_no), exclude_id=flat.id
            )

        await self.flats.update(flat, changes)
        await self.flats.commit()
        return await self.get_fresh(flat.id)

    async def delete(self, flat_id: int) -> None:
        flat = await self.get(flat_id)
        await self.flats.delete(flat)
        await self.flats.commit()

    async def get_fresh(self, flat_id: int) -> Flat:
        """Re-read a flat together with its (possibly changed) building."""
        flat = await self.flats.get(flat_id, refresh=True)
        if flat is None:
            raise NotFoundError("Flat not found")
        return flat
