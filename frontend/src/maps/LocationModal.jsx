import React, {useState,useEffect,useRef} from 'react'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,Activity,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
import LocationSearch from './LocationSearch'
import GeoMap from './GeoMap'
function LocationModal({title,description,initial,onSave,close,busy}) {
  const [point,setPoint]=useState(initial||null)
  return <div className='modal-overlay' onMouseDown={close}>
    <div className='modal tracking-modal' onMouseDown={e=>e.stopPropagation()}>
      <div className='modal-head'><div><span className='section-kicker'>GIS LOCATION</span><h2>{title}</h2><p>{description}</p></div>
        <button className='icon-btn' onClick={close}><X size={21}/></button></div>
      <div className='tracking-body'>
        <p style={{marginTop:0}}>Search for a place, use your device location, or click the map. Confirm the exact receiving or pickup point before saving.</p>
        <LocationSearch onSelect={setPoint}/><GeoMap pickable value={point} onSelect={setPoint}/>
        {point ? <p style={{fontSize:13}}>Selected: {point.latitude.toFixed(6)}, {point.longitude.toFixed(6)}</p>
          : <p style={{fontSize:13}}>No coordinates selected yet.</p>}
        <div className='row-actions' style={{marginTop:12}}>
          <button className='btn btn-outline' onClick={close}>Cancel</button>
          <button className='btn btn-dark' disabled={!point||busy} onClick={()=>onSave(point)}>
            {busy?'Saving...':'Save selected location'}
          </button>
        </div>
      </div>
    </div>
  </div>
}

export default LocationModal
