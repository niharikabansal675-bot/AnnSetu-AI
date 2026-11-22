import React from 'react'
import {ArrowUpRight,Package,Clock3,Truck,CheckCircle2,Leaf,MapPin,ScanLine,Send,BrainCircuit,RefreshCcw,Check,Users,ShieldCheck,Search,Activity,Plus,AlertCircle} from 'lucide-react'
import {fmt,cap} from '../utils/formatters'
import {Pill,Status} from '../components/StatusBadge'
import ActivityList from '../components/ActivityList'
import Empty from '../components/EmptyState'

export default function Coordinator({busy,user,run,agentResult,audit}) {
 return (
 <>{<><div className="agent-banner"><div><span className="agent-chip"><BrainCircuit size={15}/> COORDINATION ENGINE</span><h2>Observe. Evaluate.<br/>Act. Verify.</h2><p>A safeguarded coordination workflow that checks eligibility, ranks suitable NGOs, initiates offers and records every decision.</p><button className="btn btn-white" disabled={busy||user.role==='ngo'} onClick={run}><RefreshCcw size={17}/>{busy?'Running...':'Run coordination cycle'}</button></div><div className="agent-decoration"><span>01<span>OBSERVE</span></span><span>02<span>EVALUATE</span></span><span>03<span>ACT</span></span><span>04<span>VERIFY</span></span></div></div><div className="agent-note"><AlertCircle size={18}/><span>This starter runs a deterministic, rule-governed agent workflow. An LLM is <b>optional</b> and used only when configured on the backend. All real-world coordination requires verified participants and their consent.</span></div>{agentResult&&<div className="panel"><h3>Latest coordinator run</h3><div className="run-results"><div><strong>{agentResult.created.length}</strong><span>Offers created</span></div><div><strong>{agentResult.escalated.length}</strong><span>Escalations</span></div><div><strong>{agentResult.skipped.length}</strong><span>Skipped</span></div></div>{agentResult.created.map((x,i)=><p className="result-line" key={i}><Check size={16}/> Donation #{x.donation_id} → {x.ngo}</p>)}</div>}<div className="panel"><div className="panel-heading"><div><h3>Recent agent decisions</h3><p>Actions are explainable and available for review</p></div></div><ActivityList items={audit.filter(a=>a.actor==='agent').slice(0,12)}/></div></>}</>
 )
}
