from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

@router.get('/api/gis/health')
def gis_health(user:User=Depends(current_user), db:Session=Depends(db_session)):
    ensure_postgis(db)
    return {'status':'ok','postgis_version':db.scalar(text('SELECT PostGIS_Version()')),
            'match_radius_km':GIS_RADIUS_KM}

@router.put('/api/me/location')
def update_my_location(body:CoordinatesIn, user:User=Depends(current_user), db:Session=Depends(db_session)):
    require_role(user,'ngo','provider')
    ensure_postgis(db)
    set_user_point(db,user.id,body.latitude,body.longitude)
    log(db,None,user.role,'location_updated','Organisation location updated by account holder',user.id)
    db.commit()
    return {'message':'Organisation location saved','latitude':body.latitude,'longitude':body.longitude}

@router.get('/api/me/location')
def get_my_location(user:User=Depends(current_user),db:Session=Depends(db_session)):
    ensure_postgis(db)
    return {'location':point_coordinates(db,'users','location',user.id)}

@router.put('/api/donations/{donation_id}/location')
def update_pickup_location(donation_id:int,body:CoordinatesIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'provider')
    d=db.get(Donation,donation_id)
    if not d or d.provider_id!=user.id:raise HTTPException(404,'Donation not found')
    if d.status!='available':raise HTTPException(409,'Pickup location can only be edited while available')
    if db.scalar(select(Offer.id).where(Offer.donation_id==d.id,Offer.status=='pending')):
        raise HTTPException(409,'Wait until the active offer resolves before editing the pickup location')
    ensure_postgis(db)
    set_pickup_point(db,d.id,body.latitude,body.longitude)
    log(db,d.id,'provider','pickup_location_updated','Pickup coordinates updated by provider',user.id)
    db.commit()
    return {'message':'Pickup location saved','latitude':body.latitude,'longitude':body.longitude}

@router.get('/api/donations/{donation_id}/geo')
def donation_geo(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    d=db.get(Donation,donation_id)
    if not d:raise HTTPException(404,'Donation not found')
    offered_to_ngo=(user.role=='ngo' and db.scalar(select(Offer.id).where(
        Offer.donation_id==d.id,Offer.ngo_id==user.id)) is not None)
    authorised=(user.role=='admin' or (user.role=='provider' and d.provider_id==user.id)
        or (user.role=='ngo' and (d.accepted_ngo_id==user.id or offered_to_ngo)))
    if not authorised:raise HTTPException(403,'Not authorised to view this donation location')
    ensure_postgis(db)
    pickup=point_coordinates(db,'donations','pickup_location',d.id)
    # Receiving NGO coordinates are only exposed to the provider after acceptance.
    destination=None
    if d.accepted_ngo_id and (user.role=='admin' or
            (user.role=='provider' and d.provider_id==user.id) or
            (user.role=='ngo' and d.accepted_ngo_id==user.id)):
        destination=point_coordinates(db,'users','location',d.accepted_ngo_id)
    distance_km=None
    if pickup and destination:
        distance_m=db.scalar(text('''SELECT ST_Distance(d.pickup_location,u.location)
            FROM donations d JOIN users u ON u.id=d.accepted_ngo_id
            WHERE d.id=:id'''),{'id':d.id})
        if distance_m is not None:distance_km=round(float(distance_m)/1000,2)
    route = driving_route(pickup,destination,include_geometry=True) if pickup and destination else None
    return {'donation_id':d.id,'pickup':pickup,'destination':destination,
            'straight_line_distance_km':distance_km,
            'route_distance_km':route['route_distance_km'] if route else None,
            'route_duration_minutes':route['route_duration_minutes'] if route else None,
            'route_points':route.get('route_points',[]) if route else [],
            'route_source':route['route_source'] if route else None,
            'note':('Road routing is an estimated journey without traffic; not live GPS tracking.'
                    if route else 'Road route unavailable; straight-line GIS distance only.')}
