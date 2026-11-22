import React from 'react'
import {ArrowUpRight,Package,Clock3,Truck,CheckCircle2,Leaf,MapPin,ScanLine,Send,BrainCircuit,RefreshCcw,Check,Users,ShieldCheck,Search,Activity,Plus,AlertCircle} from 'lucide-react'
import {fmt,cap} from '../utils/formatters'
import {Pill,Status} from '../components/StatusBadge'
import ActivityList from '../components/ActivityList'
import Empty from '../components/EmptyState'

export default function Offers({offers,user,busy,action}) {
 return (
 <>{<div className="panel"><div className="panel-heading"><div><h3>Donation offers</h3><p>NGOs make the final decision to accept or decline.</p></div></div>{offers.length?<div className="offer-list">{offers.map(o=><div className="offer-row" key={o.id}><div className="offer-icon"><Send size={19}/></div><div className="offer-detail"><b>{o.donation_title}</b><p>Offered to {o.ngo_name} · Expires {fmt(o.expires_at)}</p></div><div className="offer-controls"><Status value={o.status}/>{o.status==='pending'&&user.role==='ngo'&&<><button disabled={busy} className="btn btn-sm btn-dark" onClick={()=>action(`/api/offers/${o.id}/respond`,'POST',{decision:'accept'})}>Accept</button><button disabled={busy} className="btn btn-sm btn-outline" onClick={()=>action(`/api/offers/${o.id}/respond`,'POST',{decision:'decline'})}>Decline</button></>}</div></div>)}</div>:<Empty title="No offers yet" description="When the coordinator matches an eligible NGO, you'll see offers here."/>}</div>}</>
 )
}
