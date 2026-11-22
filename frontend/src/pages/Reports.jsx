import React from 'react'
import {ArrowUpRight,Package,Clock3,Truck,CheckCircle2,Leaf,MapPin,ScanLine,Send,BrainCircuit,RefreshCcw,Check,Users,ShieldCheck,Search,Activity,Plus,AlertCircle} from 'lucide-react'
import {fmt,cap} from '../utils/formatters'
import {Pill,Status} from '../components/StatusBadge'
import ActivityList from '../components/ActivityList'
import Empty from '../components/EmptyState'

export default function Reports({user,report}) {
 return (
 <>{user.role==='admin'&&<div className="panel"><div className="panel-heading"><div><h3>Milestone 2 — measurable results</h3><p>Calculated from stored records; simulation data is not evidence of real-world impact.</p></div><button className="btn btn-sm btn-outline" onClick={()=>{const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='food-rescue-results.json';a.click();URL.revokeObjectURL(url)}}>Export JSON</button></div>{report?<><div className="report-grid">{[['Total listings',report.total_donations],['Completed meals',report.completed_quantity],['Agent actions',report.agent_actions],['Human escalations',report.escalations]].map(([k,v])=><div className="stat-card" key={k}><span>{k}</span><strong>{v}</strong></div>)}</div><h3>Donation status counts</h3><div className="report-grid">{Object.entries(report.donations_by_status).map(([k,v])=><div className="mini-metric" key={k}><span>{cap(k)}</span><b>{v}</b></div>)}</div><h3>Offer response outcomes</h3><p>Accepted: {report.offer_responses.accepted} · Declined: {report.offer_responses.declined} · Timed out: {report.offer_responses.timed_out}</p><p className="muted-text">{report.disclaimer}</p></>:<Empty title="No report available" description="Verify the backend connection first."/>}</div>}</>
 )
}
