import React, {useState,useEffect,useRef} from 'react'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,Activity,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
// Photon is a public demo geocoder: debounced searches, not for production-scale traffic.
// A result is only saved when the user selects it and confirms the location.
const PHOTON_API = 'https://photon.komoot.io/api/'
function describePlace(feature) {
  const p = feature.properties || {}
  const segments = [p.name, p.housenumber && p.street ? `${p.housenumber} ${p.street}` : p.street,
    p.district, p.city, p.county, p.state, p.country].filter(Boolean)
  return [...new Set(segments)].join(', ')
}
function LocationSearch({onSelect, onAddressSelect}) {
  const [query,setQuery]=useState('')
  const [results,setResults]=useState([])
  const [searching,setSearching]=useState(false)
  const [error,setError]=useState('')
  const [locating,setLocating]=useState(false)
  const [chosen,setChosen]=useState('')
  useEffect(()=>{
    const q=query.trim()
    if(q.length<3 || chosen===q){setResults([]);setSearching(false);return}
    const controller=new AbortController()
    const timer=setTimeout(async()=>{
      setSearching(true);setError('')
      try{
        const params=new URLSearchParams({q,limit:'6',lat:'28.6692',lon:'77.4538',lang:'en'})
        const response=await fetch(`${PHOTON_API}?${params}`,{signal:controller.signal})
        if(!response.ok)throw new Error('Location search is temporarily unavailable')
        const data=await response.json()
        setResults((data.features||[]).filter(f=>Array.isArray(f.geometry?.coordinates)&&f.geometry.coordinates.length>=2))
      }catch(e){if(e.name!=='AbortError'){setResults([]);setError(e.message||'Location search failed')}}
      finally{if(!controller.signal.aborted)setSearching(false)}
    },750)
    return()=>{clearTimeout(timer);controller.abort()}
  },[query,chosen])
  function choose(feature){
    const [longitude,latitude]=feature.geometry.coordinates
    if(!Number.isFinite(latitude)||!Number.isFinite(longitude))return
    const label=describePlace(feature)
    onSelect({latitude,longitude})
    onAddressSelect?.(label)
    setChosen(label)
    setQuery(label)
    setResults([])
    setError('')
  }
  function currentLocation(){
    if(!navigator.geolocation){setError('Your browser does not support location access.');return}
    setLocating(true);setError('')
    navigator.geolocation.getCurrentPosition(
      pos=>{
        const point={latitude:pos.coords.latitude,longitude:pos.coords.longitude}
        onSelect(point)
        setQuery('Current device location — adjust pin if needed')
        setChosen('Current device location — adjust pin if needed')
        setResults([])
        setLocating(false)
      },
      err=>{setError(err.message||'Location permission denied');setLocating(false)},
      {enableHighAccuracy:true,timeout:12000,maximumAge:0}
    )
  }
  return <div style={{margin:'12px 0',position:'relative'}}>
    <label style={{display:'block',fontWeight:600,marginBottom:6}}>Find a place or address</label>
    <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
      <input aria-label='Search location' value={query}
        onChange={e=>{setQuery(e.target.value);setChosen('')}}
        placeholder='e.g. Gaur City 2, Greater Noida West'
        style={{flex:'1 1 210px',minWidth:0,padding:'11px 12px',border:'1px solid #C9D7E6',borderRadius:8}}/>
      <button type='button' className='btn btn-outline' disabled={locating} onClick={currentLocation}>
        <MapPin size={16}/>{locating?'Locating...':'Use my location'}
      </button>
    </div>
    {searching&&<p role='status' style={{fontSize:12,margin:'6px 0'}}>Searching places...</p>}
    {error&&<p role='alert' style={{color:'#B42318',fontSize:12,margin:'6px 0'}}>{error}</p>}
    {!searching&&query.trim().length>=3&&!chosen&&results.length===0&&!error&&
      <p style={{fontSize:12,margin:'6px 0'}}>No matching place yet. Try adding Ghaziabad or Greater Noida.</p>}
    {results.length>0&&<div role='listbox' aria-label='Location suggestions'
      style={{border:'1px solid #D8E4F0',borderRadius:8,marginTop:6,maxHeight:210,overflowY:'auto',background:'#fff'}}>
      {results.map((item,index)=><button type='button' role='option' aria-selected={false}
        key={`${item.properties?.osm_id||index}-${index}`} onClick={()=>choose(item)}
        style={{display:'block',width:'100%',textAlign:'left',padding:'10px 12px',background:'#fff',border:0,borderBottom:'1px solid #EDF2F7',cursor:'pointer',color:'#17324F'}}>
        <MapPin size={14} style={{verticalAlign:'middle',marginRight:7}}/>{describePlace(item)||'Unnamed place'}
      </button>)}
    </div>}
    <p style={{fontSize:12,color:'#63778C',margin:'7px 0 0'}}>Select a suggestion to move the pin, then check the exact entrance on the map. GPS requires browser permission and HTTPS or localhost.</p>
  </div>
}

export default LocationSearch
