"""Small HTTP client for a self-hosted OSRM instance."""

import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.config import get_settings


class RoutingError(RuntimeError):
    pass


def route(origin_lon: float, origin_lat: float, destination_lon: float, destination_lat: float) -> dict:
    base = get_settings().osrm_base_url.strip().rstrip("/")
    if not base:
        raise RoutingError("Routing service is not configured")
    coordinates = f"{origin_lon},{origin_lat};{destination_lon},{destination_lat}"
    url = f"{base}/route/v1/driving/{coordinates}?{urlencode({'overview':'false','steps':'false'})}"
    try:
        with urlopen(url, timeout=5) as response:
            payload = json.loads(response.read())
    except (URLError, TimeoutError, json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RoutingError("Routing service is unavailable") from exc
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError("No driving route was found")
    result = payload["routes"][0]
    return {"distance_meters": result["distance"], "duration_seconds": result["duration"]}
