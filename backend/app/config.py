from __future__ import annotations
import os
from pathlib import Path
from dotenv import load_dotenv

# The user's existing backend/.env remains the source of configuration.
load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / '.env')
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./foodrescue.db')
JWT_SECRET = os.getenv('JWT_SECRET', 'dev-secret-change-me')
GIS_RADIUS_KM = float(os.getenv('GIS_MATCH_RADIUS_KM', '20'))
if not 0 < GIS_RADIUS_KM <= 100:
    raise ValueError('GIS_MATCH_RADIUS_KM must be between 0 and 100')
OSRM_BASE_URL = os.getenv('OSRM_BASE_URL', 'https://router.project-osrm.org').rstrip('/')
OSRM_TIMEOUT_SECONDS = 3
DEFAULT_CORS_ORIGINS = 'http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173'
CORS_ORIGINS = [origin.strip().rstrip('/') for origin in os.getenv('CORS_ORIGINS', DEFAULT_CORS_ORIGINS).split(',') if origin.strip()]
for local_origin in ('http://localhost:3000', 'http://127.0.0.1:3000'):
    if local_origin not in CORS_ORIGINS:
        CORS_ORIGINS.append(local_origin)
