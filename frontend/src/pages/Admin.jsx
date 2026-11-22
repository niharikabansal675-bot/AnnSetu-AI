import React from 'react'
import {ArrowUpRight,Package,Clock3,Truck,CheckCircle2,Leaf,MapPin,ScanLine,Send,BrainCircuit,RefreshCcw,Check,Users,ShieldCheck,Search,Activity,Plus,AlertCircle} from 'lucide-react'
import {fmt,cap} from '../utils/formatters'
import {Pill,Status} from '../components/StatusBadge'
import ActivityList from '../components/ActivityList'
import Empty from '../components/EmptyState'

export default function Admin({user,users,busy,action}) {
 return (
 <>{user.role==='admin'&&<div className="panel"><div className="panel-heading"><div><h3>Account verification</h3><p>Approve legitimate accounts only after checking their details.</p></div></div><div className="table-scroll"><table><thead><tr><th>ACCOUNT</th><th>ROLE</th><th>AREA</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>{users.filter(u=>u.role!=='admin').map(u=><tr key={u.id}><td><div className="table-title"><span className="table-icon"><Users size={17}/></span><span><b>{u.organisation}</b><small>{u.name} · {u.email}</small></span></div></td><td>{cap(u.role)}</td><td>{u.locality}</td><td><Pill tone={u.verified?'green':'orange'}>{u.verified?'Verified':'Pending'}</Pill></td><td><button disabled={busy} className="btn btn-sm btn-outline" onClick={()=>action(`/api/admin/users/${u.id}/verify`,'PATCH',{verified:!u.verified})}>{u.verified?'Revoke':'Verify'}</button></td></tr>)}</tbody></table></div></div>}</>
 )
}
