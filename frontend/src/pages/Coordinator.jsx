import React, {useMemo} from 'react';
import {CheckCircle2, AlertCircle, Clock3, MapPin, Send, RefreshCcw, ShieldCheck} from 'lucide-react';
import {fmt} from '../utils/formatters';

/** Translate coordinator audit records to useful messages, without exposing internal rules. */
function classify(event) {
  if (event.action === 'offer_created') return {label:'NGO match found',detail:'A suitable NGO has been sent a donation offer.',tone:'success',Icon:CheckCircle2};
  if (event.action === 'escalation') return {label:'Needs attention',detail:'We could not find a suitable NGO. Check the pickup location, quantity and collection deadline.',tone:'warning',Icon:AlertCircle};
  if (event.action === 'offer_timed_out') return {label:'Offer expired',detail:'An NGO did not respond before the offer expired. Another match can be attempted.',tone:'warning',Icon:Clock3};
  return null;
}

export default function Coordinator({busy,user,run,agentResult,audit=[],donations=[],offers=[],navigate}) {
  const relevantIds=useMemo(()=>new Set(donations.map(d=>d.id)),[donations]);
  const recent=useMemo(()=>audit.filter(a=>a.actor==='agent' && relevantIds.has(a.donation_id))
    .map(a=>({...a,view:classify(a)})).filter(a=>a.view).slice(0,8),[audit,relevantIds]);
  const awaiting=donations.filter(d=>d.status==='available').length;
  const sent=offers.filter(o=>['pending','accepted'].includes(o.status)).length;
  const needsAttention=donations.filter(d=>d.status==='available' && audit.some(a=>a.donation_id===d.id && a.action==='escalation')).length;
  const isAdmin=user.role==='admin';
  return <div className="smart-match">
    <div className="smart-match-hero">
      <div className="smart-match-head"><div><span className="smart-match-eyebrow"><MapPin size={14}/> FOOD RESCUE NETWORK</span><h2>Find the right NGO for every donation</h2><p>Donation requests are checked against available, verified organisations. Track matching results and requests that need attention here.</p></div><span className="smart-match-status"><ShieldCheck size={15}/> Verified partners only</span></div>
      <div className="smart-match-stats" aria-label="Matching overview">
        <div><span>Waiting for a match</span><strong>{awaiting}</strong></div>
        <div><span>Open or accepted offers</span><strong>{sent}</strong></div>
        <div><span>Needs review</span><strong>{needsAttention}</strong></div>
      </div>
    </div>
    <section className="panel smart-match-panel">
      <div className="panel-heading"><div><h3>Matching activity</h3><p>Recent updates for your donation requests</p></div><button type="button" className="btn btn-sm btn-outline" onClick={()=>navigate('offers')}>View offers <Send size={15}/></button></div>
      {recent.length ? <div className="smart-match-events">{recent.map(a=>{const {Icon,tone,label,detail}=a.view; return <div className="smart-match-event" key={a.id}><div className={'smart-match-event-icon '+tone}><Icon size={19}/></div><div className="smart-match-event-body"><b>{label}</b><p>{detail}</p><small>{a.donation_id ? `Donation #${a.donation_id} · ` : ''}{fmt(a.created_at)}</small></div><span className={'smart-match-event-tag '+tone}>{tone==='success'?'Offer sent':'Review'}</span></div>})}</div> : <div className="smart-match-empty"><CheckCircle2 size={28}/><b>No matching updates yet</b><p>Once a donation is checked, new offers and important updates will appear here.</p></div>}
    </section>
    <div className="smart-match-foot"><p><ShieldCheck size={16}/> Only verified organisations can receive real donation offers. NGOs decide whether to accept an offer.</p>{isAdmin&&<button type="button" className="btn btn-sm btn-outline" disabled={busy} onClick={run}><RefreshCcw size={15}/>{busy?'Checking...':'Run matching check (admin)'}</button>}</div>
    {isAdmin && agentResult && <p className="smart-match-admin-result" role="status">Last manual check: {agentResult.created?.length||0} offers sent, {agentResult.escalated?.length||0} donations needing review, {agentResult.skipped?.length||0} waiting.</p>}
  </div>;
}
