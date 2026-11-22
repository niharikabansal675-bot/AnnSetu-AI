import React from 'react';
import {fmt,cap} from '../utils/formatters';
import {CheckCircle2, Clock3, MapPin} from 'lucide-react';

function friendly(a) {
  const labels={listing_created:'Donation created',listing_edited:'Donation updated',listing_cancelled:'Donation cancelled',offer_created:'NGO offer sent',offer_accepted:'NGO accepted the offer',offer_declined:'NGO declined the offer',offer_timed_out:'Offer expired',picked_up:'Food picked up',delivery_confirmed:'Delivery receipt recorded',location_sharing_started:'Delivery location sharing started',location_sharing_stopped:'Location sharing stopped',escalation:'No suitable NGO found',pickup_location_updated:'Pickup location updated'};
  return labels[a.action]||cap(a.action);
}
export default function Activity({audit=[],isAdmin=false}) {
  return <section className="panel"><div className="panel-heading"><div><h3>{isAdmin?'Audit history':'Donation activity'}</h3><p>{isAdmin?'Detailed records for platform review':'Updates about your donation journey'}</p></div></div>
    {audit.length?<div className="smart-match-events">{audit.slice(0,70).map((a,i)=><div className="smart-match-event" key={a.id||i}><div className="smart-match-event-icon"><Clock3 size={18}/></div><div className="smart-match-event-body"><b>{friendly(a)}</b>{isAdmin && a.detail && <p>{a.detail}</p>}<small>{a.donation_id?`Donation #${a.donation_id} · `:''}{fmt(a.created_at)}</small></div></div>)}</div>:<div className="smart-match-empty"><MapPin size={24}/><b>No activity yet</b><p>Your donation updates will appear here.</p></div>}
  </section>
}
