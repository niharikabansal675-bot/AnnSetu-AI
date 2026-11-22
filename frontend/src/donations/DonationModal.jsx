import React, {useState,useEffect,useRef} from 'react'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,Activity,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
import {toLocalDateTime} from '../utils/formatters'
import LocationSearch from '../maps/LocationSearch'
import GeoMap from '../maps/GeoMap'
function DonationModal({close,submit,busy,initial}) {
  const [form,setForm] = useState(() => initial ? {
    ...initial,
    prepared_at: toLocalDateTime(initial.prepared_at),
    deadline: toLocalDateTime(initial.deadline)
  } : {
    title: '',
    food_type: 'Vegetarian meals',
    quantity: 50,
    locality: 'Indirapuram',
    address: '',
    storage: 'Covered and safely stored',
    prepared_at: toLocalDateTime(Date.now() - 15 * 60000),
    deadline: toLocalDateTime(Date.now() + 3 * 3600000)
  })
  const [dateError,setDateError] = useState('')
  const [pickupPoint,setPickupPoint]=useState(null)
  const set = (key,value) => {
    setForm(current => ({...current,[key]:value}))
    if (key === 'deadline' || key === 'prepared_at') setDateError('')
  }
  const handleSubmit = e => {
    e.preventDefault()
    const deadline = new Date(form.deadline)
    const preparedAt = new Date(form.prepared_at)
    if (!form.deadline || Number.isNaN(deadline.getTime()) || deadline.getTime() <= Date.now()) {
      setDateError('Choose a pickup deadline later than the current time.')
      return
    }
    if (!initial && (!form.prepared_at || Number.isNaN(preparedAt.getTime()) || preparedAt.getTime() > Date.now() + 5 * 60000)) {
      setDateError('Preparation time must not be in the future.')
      return
    }
    submit(initial ? {
      title: form.title,
      quantity: Number(form.quantity),
      storage: form.storage,
      deadline: deadline.toISOString()
    } : {
      ...form,
      ...(pickupPoint?pickupPoint:{}),
      quantity: Number(form.quantity),
      prepared_at: preparedAt.toISOString(),
      deadline: deadline.toISOString()
    })
  }
  return <div className="modal-overlay" onMouseDown={close}>
    <div className="modal" onMouseDown={e=>e.stopPropagation()}>
      <div className="modal-head">
        <div><span className="section-kicker">{initial?'EDIT FOOD LISTING':'NEW FOOD LISTING'}</span><h2>{initial?'Edit donation':'Share available food'}</h2><p>Only list food that is already prepared and confirmed available.</p></div>
        <button className="icon-btn" onClick={close}><X size={22}/></button>
      </div>
      <form onSubmit={handleSubmit} className="modal-form">
        <label className="span-two">Donation title<input required minLength="4" value={form.title} onChange={e=>set('title',e.target.value)} placeholder="e.g. Freshly packed vegetarian meals"/></label>
        <label>Food type<input disabled={!!initial} required value={form.food_type} onChange={e=>set('food_type',e.target.value)}/></label>
        <label>Quantity (meals)<input type="number" min="1" required value={form.quantity} onChange={e=>set('quantity',e.target.value)}/></label>
        <label>Locality<input disabled={!!initial} required value={form.locality} onChange={e=>set('locality',e.target.value)}/></label>
        <label>Storage conditions<input required value={form.storage} onChange={e=>set('storage',e.target.value)}/></label>
        <label className="span-two">Pickup address<input disabled={!!initial} required minLength="5" value={form.address} onChange={e=>set('address',e.target.value)} placeholder="Complete pickup address"/></label>
        <label>Food preparation time<input disabled={!!initial} required type="datetime-local" value={form.prepared_at} onChange={e=>set('prepared_at',e.target.value)}/></label>
        <label>Pickup deadline<input required type="datetime-local" min={toLocalDateTime(Date.now())} value={form.deadline} onChange={e=>set('deadline',e.target.value)}/></label>
        {!initial&&<div className="span-two"><label>Pickup location on map (required for GIS matching)</label><p style={{fontSize:13}}>Search for the pickup venue, select a suggestion, and verify the exact building or entrance pin.</p><LocationSearch onSelect={setPickupPoint} onAddressSelect={address=>set('address',address.slice(0,300))}/><GeoMap pickable value={pickupPoint} onSelect={setPickupPoint}/>{pickupPoint&&<small>Selected: {pickupPoint.latitude.toFixed(6)}, {pickupPoint.longitude.toFixed(6)}</small>}</div>}
        {dateError && <p className="span-two" role="alert" style={{color:'#B42318',margin:0}}>{dateError}</p>}
        <div className="span-two modal-actions"><button type="button" className="btn btn-outline" onClick={close}>Cancel</button><button disabled={busy} className="btn btn-dark">{busy?'Saving...':initial?'Save changes':'Publish donation'} <ArrowRight size={16}/></button></div>
      </form>
    </div>
  </div>
}
export default DonationModal
