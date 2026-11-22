from __future__ import annotations
import json
from urllib import request as urlrequest
from ..config import OSRM_BASE_URL, OSRM_TIMEOUT_SECONDS

def driving_route(pickup: dict, destination: dict, include_geometry: bool = False):
    """Road-network estimate; None means unavailable, never zero or a guessed ETA.

    Coordinates are passed to OSRM as longitude,latitude (GeoJSON order).
    Call only for authorised donation locations or eligible NGO candidates.
    """
    from urllib.error import HTTPError, URLError
    from math import isfinite
    a, b = pickup, destination
    try:
        for point in (a, b):
            if not (-90 <= point['latitude'] <= 90 and -180 <= point['longitude'] <= 180):
                return None
        coords = (f"{a['longitude']:.6f},{a['latitude']:.6f};"
                  f"{b['longitude']:.6f},{b['latitude']:.6f}")
        route_url = (f'{OSRM_BASE_URL}/route/v1/driving/{coords}'
                     f'?overview={"simplified" if include_geometry else "false"}'
                     f'&geometries=geojson&steps=false')
        req = urlrequest.Request(route_url, headers={'User-Agent':'AnnSetu-AI/0.2 (educational routing prototype)'})
        with urlrequest.urlopen(req, timeout=OSRM_TIMEOUT_SECONDS) as response:
            payload = json.load(response)
        if payload.get('code') != 'Ok' or not payload.get('routes'):
            return None
        route = payload['routes'][0]
        meters, seconds = float(route['distance']), float(route['duration'])
        if not all(map(isfinite, (meters, seconds))) or meters < 0 or seconds < 0:
            return None
        result = {'route_distance_km':round(meters/1000,2),
                  'route_duration_minutes':round(seconds/60,1),
                  'route_source':'OSRM road-network estimate (not live traffic)'}
        if include_geometry:
            raw = route.get('geometry',{}).get('coordinates', [])
            # Leaflet uses [latitude, longitude]; GeoJSON uses [longitude, latitude].
            if len(raw) <= 3000:
                result['route_points'] = [[float(y),float(x)] for x,y in raw]
        return result
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError, IndexError,
            TypeError, OSError, json.JSONDecodeError):
        return None
