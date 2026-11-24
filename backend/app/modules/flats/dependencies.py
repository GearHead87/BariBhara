from typing import Annotated

from fastapi import Depends

from app.modules.buildings.dependencies import get_building_repository
from app.modules.buildings.repositories import BuildingRepository
from app.modules.flats.repositories import FlatRepository
from app.modules.flats.services import FlatService
from app.modules.users.dependencies import DbSession


def get_flat_repository(db: DbSession) -> FlatRepository:
    return FlatRepository(db)


def get_flat_service(
    flats: Annotated[FlatRepository, Depends(get_flat_repository)],
    buildings: Annotated[BuildingRepository, Depends(get_building_repository)],
) -> FlatService:
    return FlatService(flats, buildings)
