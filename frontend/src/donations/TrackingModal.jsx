import React, {useState,useEffect,useRef} from 'react'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,Activity,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
import {API,request} from '../services/api'
import {fmt,cap} from '../utils/formatters'
import {Status} from '../components/StatusBadge'
import GeoMap from '../maps/GeoMap'
import QRScanner from '../tracking/QRScanner'
import LiveTracking from '../tracking/LiveTracking'
import DeliveryReceipt from '../tracking/DeliveryReceipt'
function TrackingModal({donation,user,close,action,refresh,flash}){
  const [events,setEvents]=useState([])
  const [geo,setGeo]=useState(null)
  const [geoError,setGeoError]=useState('')
  const [qr,setQr]=useState('')
  const [token,setToken]=useState('')
  const [loading,setLoading]=useState(false)
  const [live,setLive]=useState(null)
  const [sharingLocal,setSharingLocal]=useState(false)
  const [gpsError,setGpsError]=useState('')
  const watchRef=useRef(null)
  const sharingRef=useRef(false)
  const sharingRefWasStarted=useRef(false)
  const sendingRef=useRef(false)
  const lastSentAtRef=useRef(0)
  const [receiverName,setReceiverName]=useState('')
  const [receivedQuantity,setReceivedQuantity]=useState(String(donation.quantity))
  const [foodCondition,setFoodCondition]=useState('good')
  const [receiptNotes,setReceiptNotes]=useState('')
  const [receiptConfirmed,setReceiptConfirmed]=useState(false)
  const [receipt,setReceipt]=useState(null)
  const isNgo=user.role==='ngo'&&donation.accepted_ngo_id===user.id
  
  const canQR =
  donation.status === 'accepted' &&
  user.role === 'provider' &&
  donation.provider_id === user.id

  useEffect(()=>{
    let active=true
    request(`/api/donations/${donation.id}/tracking`)
      .then(data=>{if(active)setEvents(data.events)})
      .catch(error=>{if(active)flash(error.message,true)})
    return()=>{active=false}
  },[donation.id])

  useEffect(()=>{
    let active=true
    setGeo(null);setGeoError('')
    request(`/api/donations/${donation.id}/geo`)
      .then(data=>{if(active)setGeo(data)})
      .catch(error=>{if(active)setGeoError(error.message)})
    return()=>{active=false}
  },[donation.id])

  useEffect(()=>{
    let active=true
    const refreshLive=()=>request(`/api/donations/${donation.id}/live`)
      .then(data=>{if(active)setLive(data)}).catch(()=>{})
    refreshLive()
    const timer=window.setInterval(refreshLive,10000)
    return()=>{active=false;window.clearInterval(timer)}
  },[donation.id])

  useEffect(()=>{
    if(donation.status!=='completed')return
    request(`/api/donations/${donation.id}/delivery-receipt`).then(data=>setReceipt(data.receipt)).catch(()=>{})
  },[donation.id,donation.status])

  // Camera/GPS is stopped on modal close or unmount; server-side position is cleared too.
  useEffect(()=>()=>{
    sharingRef.current=false
    if(watchRef.current!==null && navigator.geolocation){navigator.geolocation.clearWatch(watchRef.current);watchRef.current=null}
    // Avoid leaving a server-side tracking session active after the modal closes.
    // A best-effort stop uses the token captured by request(); failures remain visible as stale server updates.
    if(sharingRefWasStarted.current){request(`/api/donations/${donation.id}/live/stop`,'POST').catch(()=>{})}
  },[donation.id])

  useEffect(()=>{
    if(!canQR)return
    let active=true
    let objectUrl=null
    const auth=localStorage.getItem('fr_token')
    fetch(`${API}/api/donations/${donation.id}/qr`,{headers:{Authorization:`Bearer ${auth}`}})
      .then(response=>{if(!response.ok)throw new Error('QR unavailable');return response.blob()})
      .then(blob=>{
        if(!active)return
        objectUrl=URL.createObjectURL(blob)
        setQr(objectUrl)
      })
      .catch(error=>{if(active)flash(error.message,true)})
    return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl)}
  },[donation.id,canQR])

  async function startSharing(){
    if(!navigator.geolocation){setGpsError('This browser does not support GPS.');return}
    if(!window.isSecureContext){setGpsError('GPS requires HTTPS or localhost.');return}
    setGpsError('')
    try{
      // Obtain permission and a first position before enabling server sharing.
      const initial=await new Promise((resolve,reject)=>navigator.geolocation.getCurrentPosition(resolve,reject,{enableHighAccuracy:true,timeout:15000,maximumAge:0}))
      await request(`/api/donations/${donation.id}/live/start`,'POST')
      sharingRef.current=true;sharingRefWasStarted.current=true;setSharingLocal(true)
      async function sendPosition(pos){
        if(!sharingRef.current||sendingRef.current)return
        if(Date.now()-lastSentAtRef.current < 12000)return
        lastSentAtRef.current=Date.now()
        sendingRef.current=true
        try{
          await request(`/api/donations/${donation.id}/live/update`,'POST',{
            latitude:pos.coords.latitude,longitude:pos.coords.longitude,accuracy_m:pos.coords.accuracy
          })
          setLive(prev=>({...prev,sharing:true,fresh:true,position:{latitude:pos.coords.latitude,longitude:pos.coords.longitude,accuracy_m:pos.coords.accuracy},updated_at:new Date().toISOString()}))
        }catch(error){setGpsError(error.message)}finally{sendingRef.current=false}
      }
      await sendPosition(initial)
      watchRef.current=navigator.geolocation.watchPosition(sendPosition,error=>setGpsError(error.message),
        {enableHighAccuracy:true,maximumAge:15000,timeout:20000})
    }catch(error){setGpsError(error.message||String(error))}
  }

  async function stopSharing(){
    sharingRef.current=false;sharingRefWasStarted.current=false
    if(watchRef.current!==null){navigator.geolocation.clearWatch(watchRef.current);watchRef.current=null}
    setSharingLocal(false)
    try{await request(`/api/donations/${donation.id}/live/stop`,'POST');setLive({sharing:false,fresh:false,position:null,updated_at:null})}
    catch(error){setGpsError(error.message)}
  }

  async function confirmDelivery(){
    setLoading(true)
    try{
      const payload={receiver_name:receiverName.trim(),received_quantity:Number(receivedQuantity),
        condition:foodCondition,notes:receiptNotes,confirmed_received:receiptConfirmed}
      const result=await action(`/api/donations/${donation.id}/delivery-confirm`,'POST',payload)
      if(result){await stopSharing();await refresh();close()}
    }finally{setLoading(false)}
  }

  async function verifyPickup(){
    setLoading(true)
    try{
      const result=await action(`/api/donations/${donation.id}/pickup`,'POST',{token:token.trim()})
      if(result){await refresh();close()}
    }finally{setLoading(false)}
  }
  const hasPickup = Boolean(geo?.pickup)
  const hasDestination = Boolean(geo?.destination)
  const hasRoadRoute = Boolean(hasPickup && hasDestination && geo?.route_points?.length > 1)
  const hasRoadEstimate = Boolean(hasPickup && hasDestination && geo?.route_distance_km != null)
  const inTransit = ['picked_up', 'completed'].includes(donation.status)
  const stepNames = ['Listed', 'Accepted', 'Picked up', 'Completed']
  const stepIndex = donation.status === 'completed' ? 3 : donation.status === 'picked_up' ? 2 : donation.status === 'accepted' ? 1 : 0
  const locationText = (point, fallback) => point ? `${point.latitude.toFixed(5)}, ${point.longitude.toFixed(5)}` : fallback
  const cardStyle = {background:'#fff',border:'1px solid #D7E4F0',borderRadius:14,padding:'15px 17px'}
  const labelStyle = {fontSize:12,fontWeight:700,color:'#526982',marginBottom:5}
  const selectedNgoName = donation.accepted_ngo_name || 'Assigned NGO'
  const routingText = !hasPickup
    ? 'Pickup location is missing. The provider needs to set the pickup point.'
    : !hasDestination
      ? donation.status === 'available'
        ? 'A delivery destination is not selected yet. The agent may estimate routes to candidate NGOs when it creates offers, but a confirmed route appears only after an NGO accepts.'
        : 'No saved destination coordinates for the assigned NGO. Ask the NGO to set its receiving location.'
      : hasRoadRoute
        ? 'Showing the estimated driving route. This is not live traffic or live collector GPS.'
        : hasRoadEstimate
          ? 'Driving distance and time are available, but the route line could not be drawn.'
          : 'Road routing is temporarily unavailable. The dashed line is straight-line distance, not a driving route.'

  return <div className="modal-overlay" onMouseDown={close}>
    <div className="modal tracking-modal" onMouseDown={e=>e.stopPropagation()} style={{width:'min(1080px,96vw)',maxWidth:'1080px',maxHeight:'94vh',overflowY:'auto',padding:'24px'}}>
      <div className="modal-head" style={{marginBottom:18}}>
        <div>
          <span className="section-kicker">DONATION #{donation.id} · DELIVERY TRACKING</span>
          <h2 style={{margin:'7px 0'}}>Donation journey</h2>
          <p>{donation.title} · {donation.locality} · {donation.quantity} meals</p>
        </div>
        <button className="icon-btn" onClick={close} aria-label="Close tracking"><X size={21}/></button>
      </div>
      <div className="tracking-body" style={{display:'grid',gap:18}}>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',flexWrap:'wrap',gap:10}}>
          <Status value={donation.status}/>
          <span style={{fontSize:12,color:'#617790'}}>Location-based tracking · Not live GPS</span>
        </div>

        <div style={{...cardStyle,background:'#F3F8FD'}}>
          <h3 style={{fontSize:16,margin:'0 0 14px',color:'#17324F'}}>Delivery progress</h3>
          <div style={{display:'grid',gridTemplateColumns:'repeat(4,minmax(0,1fr))',gap:8}}>
            {stepNames.map((step,i)=><div key={step} style={{minWidth:0}}>
              <div style={{height:7,borderRadius:9,background:i<=stepIndex?'#17324F':'#D3E0EC',marginBottom:8}}/>
              <span style={{fontSize:12,fontWeight:i<=stepIndex?700:400,color:i<=stepIndex?'#17324F':'#60758A'}}>{step}</span>
            </div>)}
          </div>
        </div>

        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(215px,1fr))',gap:12}}>
          <div style={cardStyle}>
            <div style={{...labelStyle,display:'flex',alignItems:'center',gap:7}}><MapPin size={15} color="#DAA51B"/> PICKUP · PROVIDER</div>
            <strong style={{display:'block',fontSize:15,color:'#17324F'}}>{donation.address||donation.locality}</strong>
            <span style={{fontSize:12,color:'#617790'}}>{locationText(geo?.pickup,'Coordinates not saved')}</span>
          </div>
          <div style={cardStyle}>
            <div style={{...labelStyle,display:'flex',alignItems:'center',gap:7}}><MapPin size={15} color="#377EC5"/> DESTINATION · NGO</div>
            <strong style={{display:'block',fontSize:15,color:'#17324F'}}>{donation.accepted_ngo_id?selectedNgoName:'Awaiting NGO acceptance'}</strong>
            <span style={{fontSize:12,color:'#617790'}}>{locationText(geo?.destination,donation.accepted_ngo_id?'Receiving coordinates not saved':'Destination not assigned')}</span>
          </div>
        </div>

        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(160px,1fr))',gap:12}}>
          <div style={cardStyle}>
            <div style={labelStyle}>DRIVING DISTANCE</div>
            <div style={{fontSize:23,fontWeight:800,color:'#17324F'}}>{hasRoadEstimate?`${geo.route_distance_km} km`:'—'}</div>
            <div style={{fontSize:11,color:'#617790'}}>Road-network estimate</div>
          </div>
          <div style={cardStyle}>
            <div style={labelStyle}>ESTIMATED DRIVE</div>
            <div style={{fontSize:23,fontWeight:800,color:'#17324F'}}>{hasRoadEstimate?`${geo.route_duration_minutes} min`:'—'}</div>
            <div style={{fontSize:11,color:'#617790'}}>Excludes live traffic</div>
          </div>
          <div style={cardStyle}>
            <div style={labelStyle}>DIRECT DISTANCE</div>
            <div style={{fontSize:23,fontWeight:800,color:'#17324F'}}>{geo?.straight_line_distance_km!=null?`${geo.straight_line_distance_km} km`:'—'}</div>
            <div style={{fontSize:11,color:'#617790'}}>PostGIS straight-line</div>
          </div>
        </div>

        <div style={{...cardStyle,background:'#EDF5FD',padding:16}}>
          <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',flexWrap:'wrap',gap:8,marginBottom:10}}>
            <h3 style={{fontSize:17,margin:0,color:'#17324F'}}>Pickup and delivery map</h3>
            <span style={{fontSize:12,color:'#526982'}}>{hasRoadRoute?'Estimated road route':hasPickup?'Saved pickup point':'Awaiting location'}</span>
          </div>
          {hasPickup||hasDestination ? <GeoMap pickup={geo?.pickup} destination={geo?.destination} collector={live?.fresh?live.position:null} routePoints={geo?.route_points||[]} height={380}/>
            : <div style={{background:'#fff',border:'1px dashed #B9CBDD',padding:24,borderRadius:12,color:'#536981'}}>No saved map coordinates yet. A provider must set the pickup location.</div>}
          <div style={{display:'flex',flexWrap:'wrap',gap:18,marginTop:13,fontSize:12,color:'#334E68'}}>
            <span><b style={{color:'#C99817'}}>●</b> Pickup location</span>
            <span><b style={{color:'#377EC5'}}>●</b> NGO destination</span>
            <span>{hasRoadRoute?'━ Driving route':'┄ Direct connection (when both points are available)'}</span>
          </div>
          <p role="status" style={{background:'#fff',borderRadius:10,padding:'11px 13px',fontSize:13,color:'#35536D',margin:'12px 0 0'}}>{geoError?`Location service: ${geoError}`:routingText}</p>
        </div>

        {['picked_up','completed'].includes(donation.status)&&<LiveTracking donation={donation} live={live} isNgo={isNgo} sharingLocal={sharingLocal} startSharing={startSharing} stopSharing={stopSharing} gpsError={gpsError} cardStyle={cardStyle}/>}
        {canQR&&<div className="qr-card">
          <h3>Pickup verification QR</h3>
          {qr&&<img alt="Unique donation pickup verification QR" className="qr-image" src={qr}/>}
          <p>Show this code only to the assigned NGO collector. It is a private verification credential.</p>
        </div>}
        {isNgo&&donation.status==='accepted'&&<QRScanner token={token} setToken={setToken} loading={loading} onVerify={verifyPickup} flash={flash}/> }
        {isNgo&&donation.status==='picked_up'&&<DeliveryReceipt donation={donation} receiverName={receiverName} setReceiverName={setReceiverName} receivedQuantity={receivedQuantity} setReceivedQuantity={setReceivedQuantity} foodCondition={foodCondition} setFoodCondition={setFoodCondition} receiptNotes={receiptNotes} setReceiptNotes={setReceiptNotes} receiptConfirmed={receiptConfirmed} setReceiptConfirmed={setReceiptConfirmed} loading={loading} confirmDelivery={confirmDelivery}/>}
        {receipt&&<div style={cardStyle}><h3>Delivery receipt</h3><p>Received by: {receipt.receiver_name} · Meals: {receipt.received_quantity} · Condition: {cap(receipt.condition)}</p><small>Recorded: {fmt(receipt.confirmed_at)} · Recorded by NGO account, not independent verification</small></div>}
        <div style={cardStyle}>
          <h3 style={{margin:'0 0 12px',color:'#17324F'}}>Timestamped activity history</h3>
          <div className="timeline">{events.length?events.map((event,i)=><div className="timeline-event" key={i}>
            <span className="timeline-dot"/><div><b>{cap(event.action)}</b><small>{fmt(event.created_at)} · {cap(event.actor)}</small><p>{event.detail}</p></div>
          </div>):<p style={{color:'#617790'}}>No tracking events recorded.</p>}</div>
        </div>
      </div>
    </div>
  </div>
}
export default TrackingModal