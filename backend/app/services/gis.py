from __future__ import annotations
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

def ensure_postgis(db: Session):
    if db.bind.dialect.name != 'postgresql':
        raise HTTPException(503, 'GIS requires the configured PostgreSQL/PostGIS database; check backend/.env')
    installed = db.scalar(text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')"))
    if not installed:
        raise HTTPException(503, 'PostGIS extension is not enabled in the application database')

def set_user_point(db: Session, user_id: int, latitude: float, longitude: float):
    db.execute(text('''UPDATE users
        SET location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        WHERE id = :id'''), {'id':user_id, 'lat':latitude, 'lon':longitude})

def set_pickup_point(db: Session, donation_id: int, latitude: float, longitude: float):
    db.execute(text('''UPDATE donations
        SET pickup_location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
        WHERE id = :id'''), {'id':donation_id, 'lat':latitude, 'lon':longitude})

def point_coordinates(db: Session, table: str, column: str, record_id: int):
    # table/column come exclusively from this source file, never from user input.
    result = db.execute(text(f'''SELECT ST_Y({column}::geometry) AS latitude,
        ST_X({column}::geometry) AS longitude FROM {table} WHERE id=:id'''),
        {'id':record_id}).mappings().first()
    if not result or result['latitude'] is None:
        return None
    return {'latitude':float(result['latitude']), 'longitude':float(result['longitude'])}