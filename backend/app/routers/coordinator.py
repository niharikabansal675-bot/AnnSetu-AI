from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

LOCALITIES = {'indirapuram':(28.642,77.370),'vaishali':(28.649,77.340),'vasundhara':(28.660,77.370),'raj nagar':(28.688,77.448),'raj nagar extension':(28.706,77.435),'crossings republik':(28.630,77.435),'kaushambi':(28.646,77.324),'sahibabad':(28.676,77.357),'govindpuram':(28.680,77.478),'ghaziabad':(28.670,77.430)}

def locality_distance(a,b):
    # Approximate distances ONLY for simulated demo rankings; never a travel-time guarantee.
    from math import radians,sin,cos,asin,sqrt
    c1=LOCALITIES.get(a.lower().strip());c2=LOCALITIES.get(b.lower().strip())
    if not c1 or not c2: return None
    lat1,lon1=map(radians,c1);lat2,lon2=map(radians,c2)
    delta=2*6371*asin(sqrt(sin((lat2-lat1)/2)**2+cos(lat1)*cos(lat2)*sin((lon2-lon1)/2)**2))
    return round(delta,1)

@router.post('/api/agent/run')
def run_coordinator(user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'admin','provider')
    rows=db.scalars(select(Donation).where(Donation.status=='available').order_by(Donation.created_at.asc())).all()
    if user.role=='provider': rows=[d for d in rows if d.provider_id==user.id]
    created=[]; escalated=[]; skipped=[]
    for d in rows:
        expire_if_needed(db,d)
        if d.status!='available': continue
        # Observe: check outstanding offer; expire timeouts
        pending=db.scalars(select(Offer).where(Offer.donation_id==d.id,Offer.status=='pending')).all()
        for o in pending:
            if aware(o.expires_at)<=utcnow(): o.status='timed_out';log(db,d.id,'agent','offer_timed_out',f'Offer {o.id} expired')
        db.flush()
        still_pending=[o for o in pending if o.status=='pending']
        if still_pending: skipped.append({'donation_id':d.id,'reason':'Pending offer is still active'});continue
        already_offered=set(db.scalars(select(Offer.ngo_id).where(Offer.donation_id==d.id)).all())
        ngo_rows=db.scalars(select(User).where(User.role=='ngo',User.verified.is_(True),User.capacity>=d.quantity)).all()
        eligible=[]
        # Real donations: accurate PostGIS coordinate matching ONLY.
        # Demo donations without coordinates retain their clearly labelled approximate fallback.
        ensure_postgis(db)
        pickup_exists=db.scalar(text('SELECT pickup_location IS NOT NULL FROM donations WHERE id=:id'),{'id':d.id})
        gis_distances={}
        if pickup_exists:
            locations=db.execute(text('''SELECT u.id AS ngo_id,
                    ST_Distance(u.location,d.pickup_location)/1000.0 AS km
                FROM users u CROSS JOIN donations d
                WHERE d.id=:donation_id AND u.role='ngo' AND u.verified = TRUE
                    AND u.capacity >= d.quantity AND u.is_demo = d.is_demo
                    AND u.location IS NOT NULL
                    AND ST_DWithin(u.location,d.pickup_location,:radius_m)'''),
                {'donation_id':d.id,'radius_m':GIS_RADIUS_KM*1000}).mappings().all()
            gis_distances={row['ngo_id']:round(float(row['km']),2) for row in locations}
        for ngo in ngo_rows:
            if ngo.id in already_offered or ngo.is_demo!=d.is_demo: continue
            if aware(d.deadline) <= utcnow()+timedelta(minutes=30):continue
            # Never infer a real NGO's position from its locality name.
            if pickup_exists:
                dist=gis_distances.get(ngo.id)
                method='PostGIS straight-line'
            elif d.is_demo:
                dist=locality_distance(d.locality,ngo.locality)
                method='SIMULATION locality approximation'
            else:
                dist=None
                method='not available'
            if dist is None: continue
            eligible.append((dist,-ngo.capacity,ngo,method))
        # Prefer real road-routing estimates when available. If OSRM is unavailable,
        # the GIS straight-line shortlist still works, but ETA is NOT verified.
        road_estimates={}
        if pickup_exists and eligible and not d.is_demo:
            pickup_point=point_coordinates(db,'donations','pickup_location',d.id)
            # Bound external requests and rate impact to the five closest GIS candidates.
            for straight_km,_,candidate,_ in sorted(eligible,key=lambda x:x[0])[:5]:
                ngo_point=point_coordinates(db,'users','location',candidate.id)
                if not pickup_point or not ngo_point:continue
                estimate=driving_route(pickup_point,ngo_point)
                if estimate:
                    road_estimates[candidate.id]=estimate
            # A route duration is only a rough transport estimate. Require an additional
            # 15-minute operational buffer and preserve the original 30-minute minimum.
            eligible=[item for item in eligible if (
                item[2].id not in road_estimates or
                aware(d.deadline)>utcnow()+timedelta(minutes=max(30,
                    road_estimates[item[2].id]['route_duration_minutes']+15)))]
        eligible.sort(key=lambda x:(
            0 if x[2].id in road_estimates else 1,
            road_estimates[x[2].id]['route_duration_minutes'] if x[2].id in road_estimates else x[0],
            x[0],x[1],x[2].id))
        if not eligible:
            log(db,d.id,'agent','escalation','No eligible NGO with confirmed location (real donations), matching capacity, verification and deadline; check GIS coordinates or radius')
            escalated.append(d.id); continue
        distance,_,ngo,distance_method=eligible[0]
        # Optional LLM assists selection only within the backend-approved shortlist.
        # It never receives identities, addresses, credentials or unrestricted tools.
        ai_note='Deterministic coordination policy'
        if not road_estimates and os.getenv('OPENAI_API_KEY') and os.getenv('ENABLE_LLM_RANKING','false').lower()=='true':
            try:
                candidates=[{'candidate':str(n.id),'distance_km':distance_km,'capacity':n.capacity} for distance_km,_,n,_ in eligible[:5]]
                req_data={'model':os.getenv('OPENAI_MODEL','gpt-4.1-mini'), 'temperature':0,
                          'messages':[{'role':'system','content':'Select a candidate from the provided eligible list ONLY. Return JSON object with keys candidate and rationale. Minimise distance; use capacity as a tiebreaker. Never invent a candidate or loosen constraints.'},
                                      {'role':'user','content':json.dumps({'quantity':d.quantity,'candidates':candidates})}],
                          'response_format':{'type':'json_object'}}
                req=urlrequest.Request('https://api.openai.com/v1/chat/completions',data=json.dumps(req_data).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},method='POST')
                with urlrequest.urlopen(req,timeout=8) as reply: response_data=json.load(reply)
                answer=json.loads(response_data['choices'][0]['message']['content'])
                chosen=next((e for e in eligible if str(e[2].id)==str(answer.get('candidate'))),None)
                if chosen:
                    distance,_,ngo,distance_method=chosen
                    ai_note='LLM-selected from verified shortlist; '+str(answer.get('rationale',''))[:180]
                else: ai_note='LLM returned non-eligible candidate; deterministic fallback'
            except Exception as exc:
                ai_note='LLM unavailable; deterministic fallback: '+type(exc).__name__
        road=road_estimates.get(ngo.id)
        route_note=(f'OSRM estimated road distance {road["route_distance_km"]} km and driving time '
                    f'{road["route_duration_minutes"]} minutes (no live traffic); '
                    f'pickup deadline assessed with 15-minute buffer.' if road else
                    'Road estimate unavailable; ETA has NOT been verified; 30-minute minimum deadline policy only.')
        reason=f'Verified; capacity {ngo.capacity} ≥ quantity {d.quantity}; {distance_method} distance {distance} km; {route_note} NGO makes final choice. {ai_note}.'
        offer=Offer(donation_id=d.id,ngo_id=ngo.id,status='pending',reason=reason,expires_at=min(utcnow()+timedelta(minutes=15),aware(d.deadline)))
        db.add(offer);db.flush()
        log(db,d.id,'agent','offer_created',f'Offer {offer.id} to {ngo.organisation}. {reason}')
        created.append({'donation_id':d.id,'ngo':ngo.organisation,'offer_id':offer.id,'reason':reason})
    db.commit()
    return {'created':created,'escalated':escalated,'skipped':skipped,'note':'Rule-governed coordination. Optional bounded LLM ranking only when explicitly enabled; deterministic fallback otherwise.'}
