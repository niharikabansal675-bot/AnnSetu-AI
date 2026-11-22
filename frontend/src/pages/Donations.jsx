import React from 'react'
import {ArrowUpRight,Package,Clock3,Truck,CheckCircle2,Leaf,MapPin,ScanLine,Send,BrainCircuit,RefreshCcw,Check,Users,ShieldCheck,Search,Activity,Plus,AlertCircle} from 'lucide-react'
import {fmt,cap} from '../utils/formatters'
import {Pill,Status} from '../components/StatusBadge'
import ActivityList from '../components/ActivityList'
import Empty from '../components/EmptyState'

export default function Donations({filtered,search,setSearch,user,setTracking,busy,setEditDonation,setModal,setLocationEdit,action}) {
 return (
 <>{<div className="panel"><div className="panel-heading"><div><h3>All donations</h3><p>{filtered.length} record{filtered.length===1?'':'s'} in this view</p></div><div className="search"><Search size={17}/><input placeholder="Search donations..." value={search} onChange={e=>setSearch(e.target.value)}/></div></div>{filtered.length?<div className="table-scroll"><table><thead><tr><th>DONATION</th><th>LOCATION</th><th>QUANTITY</th><th>DEADLINE</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>{filtered.map(d=><tr key={d.id}><td><div className="table-title"><span className="table-icon"><Package size={17}/></span><span><b>{d.title}</b><small>{d.provider_name}{d.is_demo?' · SIMULATION':''}</small></span></div></td><td>{d.locality}</td><td>{d.quantity} meals</td><td>{fmt(d.deadline)}</td><td><Status value={d.status}/></td><td><div className="row-actions"><button className="btn btn-sm btn-outline" onClick={()=>setTracking(d)}><ScanLine size={14}/> Track</button>{user.role==='provider'&&d.provider_id===user.id&&d.status==='available'&&<><button className="btn btn-sm btn-outline" disabled={busy} onClick={()=>{setEditDonation(d);setModal(true)}}>Edit</button><button className="btn btn-sm btn-outline" disabled={busy} onClick={()=>setLocationEdit({kind:'donation',id:d.id})}><MapPin size={14}/> Pickup map</button><button className="btn btn-sm btn-outline" disabled={busy} onClick={()=>{const reason=window.prompt('Reason for cancellation (at least 5 characters):');if(reason&&reason.trim().length>=5)action(`/api/donations/${d.id}/cancel`,'POST',{reason})}}>Cancel</button></>}</div></td></tr>)}</tbody></table></div>:<Empty title="No matching donations" description="Try a different search term or create a listing."/>}</div>}</>
 )
}
