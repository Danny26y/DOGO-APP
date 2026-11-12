from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.api.dependencies import get_current_user
from app.integrations.osrm import RoutingError, route
from app.modules.auth.models import User

router = APIRouter()


class RouteResponse(BaseModel):
    distance_meters: float
    duration_seconds: float


@router.get("/routing/route", response_model=RouteResponse)
def get_route(
    origin_lat: float = Query(ge=-90, le=90),
    origin_lon: float = Query(ge=-180, le=180),
    destination_lat: float = Query(ge=-90, le=90),
    destination_lon: float = Query(ge=-180, le=180),
    _user: User = Depends(get_current_user),
):
    try:
        return route(origin_lon, origin_lat, destination_lon, destination_lat)
    except RoutingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
