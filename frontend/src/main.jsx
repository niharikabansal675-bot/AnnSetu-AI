import React,{useState,useEffect,useRef} from 'react'
import {createRoot} from 'react-dom/client'
import { Html5Qrcode } from 'html5-qrcode'
import { MapContainer, TileLayer, CircleMarker, Polyline, Popup, useMapEvents, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,Activity,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
import './style.css'
const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8000'
const fmt = d=>new Date(d).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'})
const cap = s=>s ? s.replaceAll('_',' ').replace(/\b\w/g,x=>x.toUpperCase()):''
async function request(path,method='GET',body){const token=localStorage.getItem('fr_token');let r;try{r=await fetch(`${API}${path}`,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})})}catch(e){throw new Error(`Cannot reach the Food Rescue API at ${API}. Check that FastAPI is running and CORS allows this frontend address. (${e.message})`)}const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:`Request failed (${r.status})`);return data}

// Map picker uses manually selected coordinates. The map's Ghaziabad centre
// is a default viewport, NOT a recorded restaurant or NGO location.
const GIS_MAP_CENTER = [28.6692, 77.4538]
function MapClickSelector({onSelect}) {
  useMapEvents({click: e => onSelect({latitude: e.latlng.lat, longitude: e.latlng.lng})})
  return null
}
function MapFitPoints({points}) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 1) map.setView(points[0], 14)
    else if (points.length > 1) map.fitBounds(points, {padding:[28,28]})
  }, [map, JSON.stringify(points)])
  return null
}
function GeoMap({pickup,destination,pickable=false,value,onSelect}) {
  const points = pickable ? (value ? [[value.latitude,value.longitude]] : []) :
    [pickup,destination].filter(Boolean).map(p=>[p.latitude,p.longitude])
  return <div style={{borderRadius:12,overflow:'hidden',border:'1px solid #D8E4F0',marginTop:12}}>
    <MapContainer center={points[0]||GIS_MAP_CENTER} zoom={12} scrollWheelZoom={false}
      style={{height:280,width:'100%',zIndex:0}}>
      <TileLayer attribution='&copy; OpenStreetMap contributors'
        url='https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'/>
      <MapFitPoints points={points}/>
      {pickable&&<MapClickSelector onSelect={onSelect}/>}
      {pickable&&value&&<CircleMarker center={[value.latitude,value.longitude]}
        radius={9} pathOptions={{color:'#17324F',fillColor:'#F4BF40',fillOpacity:1}}>
        <Popup>Selected location</Popup>
      </CircleMarker>}
      {!pickable&&pickup&&<CircleMarker center={[pickup.latitude,pickup.longitude]}
        radius={9} pathOptions={{color:'#17324F',fillColor:'#F4BF40',fillOpacity:1}}><Popup>Pickup location</Popup></CircleMarker>}
      {!pickable&&destination&&<CircleMarker center={[destination.latitude,destination.longitude]}
        radius={9} pathOptions={{color:'#17324F',fillColor:'#6FA6E8',fillOpacity:1}}><Popup>NGO receiving location</Popup></CircleMarker>}
      {!pickable&&pickup&&destination&&<Polyline positions={points} pathOptions={{color:'#17324F',dashArray:'7 8',weight:3}}/>}
    </MapContainer>
  </div>
}
function LocationModal({title,description,initial,onSave,close,busy}) {
  const [point,setPoint]=useState(initial||null)
  return <div className='modal-overlay' onMouseDown={close}>
    <div className='modal tracking-modal' onMouseDown={e=>e.stopPropagation()}>
      <div className='modal-head'><div><span className='section-kicker'>GIS LOCATION</span><h2>{title}</h2><p>{description}</p></div>
        <button className='icon-btn' onClick={close}><X size={21}/></button></div>
      <div className='tracking-body'>
        <p style={{marginTop:0}}>Click the map to select the actual location. The initial map centre is not saved automatically.</p>
        <GeoMap pickable value={point} onSelect={setPoint}/>
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

function Logo(){return <div className="brand"><span className="brand-icon"><Leaf size={20} strokeWidth={2.3}/></span><span>food<span className="brand-dot">.</span>rescue</span></div>}
function Pill({children,tone='muted'}){return <span className={'pill pill-'+tone}>{children}</span>}
function Status({value}){return <Pill tone={value==='completed'?'green':value==='available'?'lime':value==='accepted'?'blue':value==='picked_up'?'orange':value==='pending'?'orange':value==='declined'?'red':'muted'}><i className="status-dot"/>{cap(value)}</Pill>}
function App(){const [token,setToken]=useState(localStorage.getItem('fr_token'));const [user,setUser]=useState(null);const [page,setPage]=useState(token?'dashboard':'home');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [mobile,setMobile]=useState(false)
useEffect(()=>{if(token)request('/api/me').then(setUser).catch(()=>{localStorage.removeItem('fr_token');setToken(null);setPage('home')})},[token])
const flash=(msg,isError=false)=>{isError?setError(msg):setNotice(msg);setTimeout(()=>{setNotice('');setError('')},5000)}
const logout=()=>{localStorage.removeItem('fr_token');setToken(null);setUser(null);setPage('home')}
const auth=async(payload,isRegister)=>{setBusy(true);setError('');try{const data=await request(isRegister?'/api/auth/register':'/api/auth/login','POST',payload);localStorage.setItem('fr_token',data.token);setToken(data.token);setUser(data.user);setPage('dashboard');flash(isRegister?'Account created. Admin verification is required before posting or receiving real donations.':'Welcome back!')}catch(e){flash(e.message,true)}finally{setBusy(false)}}
const navigate=(p)=>{setPage(p);setMobile(false);setError('');window.scrollTo({top:0,behavior:'smooth'})}
// A saved token exists before /api/me has returned a user. Do not mount
// Workspace until the user is available; otherwise it crashes on user.id.
if (token && !user) {
  return <div className="site" style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'#F6F9FD',color:'#17324F'}} role="status" aria-live="polite">Loading your Food Rescue workspace...</div>
}
return <><div className="site">{!token? <><header className="public-nav wrap"><Logo/><nav className="desktop-nav"><a href="#how" onClick={()=>setPage('home')}>How it works</a><a href="#why" onClick={()=>setPage('home')}>Our mission</a><a href="#features" onClick={()=>setPage('home')}>Platform</a></nav><div className="nav-actions"><button className="btn btn-text" onClick={()=>navigate('login')}>Log in</button><button className="btn btn-dark" onClick={()=>navigate('register')}>Get started <ArrowUpRight size={16}/></button></div></header>{page==='home'?<Home navigate={navigate}/>:<Auth page={page} navigate={navigate} onSubmit={auth} busy={busy}/>}</>:<div className="app-shell"><aside className={'sidebar '+(mobile?'open':'')}><div className="sidebar-top"><Logo/><button className="icon-btn mobile-only" onClick={()=>setMobile(false)}><X size={20}/></button></div><div className="workspace-label">WORKSPACE</div><nav className="side-nav">{[[LayoutDashboard,'dashboard','Overview'],[Package,'donations','Donations'],[Send,'offers','Offers & requests'],[BrainCircuit,'coordinator','AI coordinator'],[Activity,'activity','Activity log'],...(user?.role==='admin'?[[BarChart3,'reports','Reports']]:[]),...(user?.role==='admin'?[[ShieldCheck,'admin','Administration']]:[])].map(([Icon,key,label])=><button key={key} className={page===key?'active':''} onClick={()=>navigate(key)}><Icon size={18}/>{label}{page===key&&<span className="side-active-dot"/>}</button>)}</nav><div className="sidebar-bottom"><div className="help-panel"><HeartHandshake size={20}/><b>Small actions, big impact.</b><p>Making food donation simpler, one connection at a time.</p></div><button className="account" onClick={logout}><span className="avatar">{user?.name?.slice(0,1).toUpperCase()||'U'}</span><span className="account-text"><b>{user?.name||'Account'}</b><small>{cap(user?.role||'')}</small></span><LogOut size={17}/></button></div></aside><div className="main-area"><header className="app-topbar"><button className="icon-btn mobile-only" onClick={()=>setMobile(true)}><Menu size={22}/></button><span className="breadcrumb">Workspace <ChevronRight size={14}/> <b>{cap(page)}</b></span><div className="topbar-right"><Pill tone={user?.verified?'green':'orange'}>{user?.verified?'Verified account':'Verification pending'}</Pill><span className="avatar small">{user?.name?.slice(0,1).toUpperCase()}</span></div></header><div className="content"><Workspace page={page} user={user} navigate={navigate} flash={flash}/></div></div></div>}{(notice||error)&&<div className={'toast '+(error?'error':'')}><span>{error||notice}</span><button onClick={()=>{setError('');setNotice('')}}><X size={15}/></button></div>}</div></>}
function Home({navigate}){return <><main><section className="hero wrap"><div className="hero-copy"><div className="eyebrow"><span className="eyebrow-line"/> A BETTER WAY TO GIVE</div><h1>Good food.<br/><span>Shared forward.</span></h1><p>Connecting surplus food from local events with the communities who need it. Less waste, more care — starting in Ghaziabad.</p><div className="hero-actions"><button className="btn btn-dark btn-lg" onClick={()=>navigate('register')}>Join the movement <ArrowUpRight size={18}/></button><a className="text-link" href="#how">See how it works <ArrowRight size={16}/></a></div><div className="hero-proof"><div className="proof-symbols"><span>♥</span><span>✳</span><span>●</span></div><span>Built for food providers & local NGOs</span></div></div><div className="hero-visual"><div className="hero-art"><div className="blob-plate"><div className="plate"><span>🥬</span><span>🥕</span><span>🍚</span><span>🍅</span></div></div><div className="art-sticker sticker-top"><span className="sticker-icon"><Leaf size={18}/></span><span><b>More shared.</b><small>Less wasted.</small></span></div><div className="art-sticker sticker-bottom"><span className="dot-live"/><span>Serving Ghaziabad, India</span></div><span className="art-cross cross-one">✳</span><span className="art-cross cross-two">✳</span></div><div className="hero-caption">A GOOD IDEA, MADE PRACTICAL. <span>↗</span></div></div></section><section className="feature-strip" id="features"><div className="wrap strip-inner"><span><ShieldCheck size={19}/> Verified participants</span><span><BrainCircuit size={19}/> AI-assisted coordination</span><span><ScanLine size={19}/> QR pickup verification</span><span><Activity size={19}/> Transparent tracking</span></div></section><section className="how-section wrap" id="how"><div className="section-heading"><div><span className="section-kicker">THE PROCESS</span><h2>Simple by design.<br/>Meaningful by nature.</h2></div><p>From a surplus meal to a confirmed handover — every step has a place.</p></div><div className="steps-grid">{[[UtensilsCrossed,'01','List available food','Food providers share confirmed surplus with clear pickup details.'],[BrainCircuit,'02','Find the right match','Eligibility rules and an AI coordinator help suitable NGOs connect.'],[Truck,'03','Collect & confirm','NGOs accept, verify pickup and confirm safe receipt.']].map(([Icon,n,title,desc])=><div className="step-card" key={n}><span className="step-num">{n}</span><div className="step-icon"><Icon size={26}/></div><h3>{title}</h3><p>{desc}</p><ArrowUpRight size={21} className="step-arrow"/></div>)}</div></section><section className="mission" id="why"><div className="wrap mission-inner"><div><span className="section-kicker">OUR WHY</span><h2>Food belongs<br/>on plates,<br/><em>not in bins.</em></h2></div><div className="mission-text"><p>We believe local coordination can make a real difference. Our platform brings food providers and verified NGOs into one transparent process.</p><button className="btn btn-white" onClick={()=>navigate('register')}>Be part of it <ArrowUpRight size={16}/></button></div></div></section></main><footer className="footer wrap"><Logo/><span>Made for a better tomorrow. © {new Date().getFullYear()} Food Rescue</span><span>Ghaziabad, India</span></footer></>}
function Auth({page,navigate,onSubmit,busy}){const isRegister=page==='register';const [role,setRole]=useState('provider');const [fields,setFields]=useState({name:'',email:'',password:'',organisation:'',locality:'Indirapuram',capacity:100});const update=(key,value)=>setFields(p=>({...p,[key]:value}));const submit=e=>{e.preventDefault();onSubmit(isRegister?{...fields,role,capacity:role==='ngo'?Number(fields.capacity):0}:{email:fields.email,password:fields.password},isRegister)};return <div className="auth-layout"><div className="auth-left"><div className="auth-content"><div className="section-kicker">FOOD RESCUE PLATFORM</div><h2>Better together.<br/><em>One meal at a time.</em></h2><p>Join a growing idea that makes local food redistribution simpler, safer and more transparent.</p><div className="auth-art">✳ <span>♥</span> ✳</div></div></div><div className="auth-right"><div className="auth-box"><span className="section-kicker">WELCOME {isRegister?'TO FOOD RESCUE':'BACK'}</span><h2>{isRegister?'Create your account':'Sign in to your account'}</h2><p>{isRegister?'Start connecting good food with good people.':'Continue making a difference in your community.'}</p>{isRegister&&<div className="role-picker"><button className={role==='provider'?'selected':''} onClick={()=>setRole('provider')}><UtensilsCrossed size={19}/><b>Food provider</b><small>I have food to share</small></button><button className={role==='ngo'?'selected':''} onClick={()=>setRole('ngo')}><HeartHandshake size={19}/><b>NGO / receiver</b><small>I collect donations</small></button></div>}<form onSubmit={submit} className="form-grid">{isRegister&&<><label>Full name<input required minLength={2} placeholder="Your name" value={fields.name} onChange={e=>update('name',e.target.value)}/></label><label>Organisation<input required minLength={2} placeholder="Organisation name" value={fields.organisation} onChange={e=>update('organisation',e.target.value)}/></label><label>Locality<input required placeholder="e.g. Indirapuram" value={fields.locality} onChange={e=>update('locality',e.target.value)}/></label>{role==='ngo'&&<label>Pickup capacity (meals)<input required type="number" min="1" value={fields.capacity} onChange={e=>update('capacity',e.target.value)}/></label>}</>}<label>Email address<input type="email" required placeholder="you@example.com" value={fields.email} onChange={e=>update('email',e.target.value)}/></label><label>Password<input type="password" minLength={isRegister?8:1} required placeholder={isRegister?'Minimum 8 characters':'Your password'} value={fields.password} onChange={e=>update('password',e.target.value)}/></label><button disabled={busy} className="btn btn-dark full btn-lg">{busy?'Please wait...':isRegister?'Create account':'Sign in'}<ArrowRight size={17}/></button></form><p className="auth-switch">{isRegister?'Already have an account?':'New to Food Rescue?'} <button onClick={()=>navigate(isRegister?'login':'register')}>{isRegister?'Sign in':'Create an account'}</button></p>{isRegister&&<div className="auth-disclaimer"><ShieldCheck size={17}/> Account verification is required before live participation.</div>}</div></div></div>}
function Workspace({page,user,navigate,flash}){const [donations,setDonations]=useState([]);const [offers,setOffers]=useState([]);const [stats,setStats]=useState({total:0,available:0,active:0,completed:0,meals:0});const [audit,setAudit]=useState([]);const [users,setUsers]=useState([]);const [busy,setBusy]=useState(false);const [modal,setModal]=useState(false);const [search,setSearch]=useState('');const [agentResult,setAgentResult]=useState(null);const [tracking,setTracking]=useState(null);const [editDonation,setEditDonation]=useState(null);const [report,setReport]=useState(null);const [locationEdit,setLocationEdit]=useState(null);const [locationBusy,setLocationBusy]=useState(false);const [ngoLocation,setNgoLocation]=useState(null)
async function reload(){try{const [d,o,s,a]=await Promise.all([request('/api/donations'),request('/api/offers'),request('/api/stats'),request('/api/audit')]);setDonations(d);setOffers(o);setStats(s);setAudit(a);if(user.role==='admin'){setUsers(await request('/api/admin/users'));setReport(await request('/api/reports'))}}catch(e){flash(e.message,true)}}
useEffect(()=>{reload()},[page,user.id]);
useEffect(()=>{if(user.role!=='ngo')return;let active=true;request('/api/me/location').then(data=>{if(active)setNgoLocation(data.location)}).catch(()=>{});return()=>{active=false}},[user.id,user.role]);
async function saveLocation(point){setLocationBusy(true);try{const path=locationEdit?.kind==='ngo'?'/api/me/location':`/api/donations/${locationEdit.id}/location`;const result=await request(path,'PUT',point);if(locationEdit?.kind==='ngo')setNgoLocation(point);flash(result.message||'Location saved');setLocationEdit(null);await reload()}catch(error){flash(error.message,true)}finally{setLocationBusy(false)}}
const action=async(path,method='POST',body)=>{setBusy(true);try{const r=await request(path,method,body);await reload();flash(r.message||'Updated successfully');return r}catch(e){flash(e.message,true)}finally{setBusy(false)}}
const create=async(body)=>{const result=await action(editDonation?`/api/donations/${editDonation.id}`:'/api/donations',editDonation?'PATCH':'POST',body);if(result){setModal(false);setEditDonation(null);navigate('donations')}}
const run=async()=>{const r=await action('/api/agent/run');if(r)setAgentResult(r)}
const filtered=donations.filter(d=>[d.title,d.locality,d.food_type,d.provider_name].join(' ').toLowerCase().includes(search.toLowerCase()))
const title=({dashboard:'Overview',donations:'Food donations',offers:'Offers & requests',coordinator:'AI coordinator',activity:'Activity history',admin:'Administration',reports:'Reports & results'})[page]||'Workspace'
return <><div className="page-header"><div><div className="section-kicker">{user.role.toUpperCase()} WORKSPACE <span className="header-slash">/</span> GHAZIABAD</div><h1>{page==='dashboard'?`Hello, ${user.name.split(' ')[0]}.`:title}</h1><p>{page==='dashboard'?'Here’s what’s happening in your food rescue network.':({donations:'A clear view of surplus food and its journey.',offers:'Keep track of requests, responses and handovers.',coordinator:'A controlled, auditable food donation coordination workflow.',activity:'Every important action, recorded for transparency.',admin:'Review participants and manage platform access.',reports:'Reproducible counts from real application records.'})[page]}</p></div><div className="header-actions">{user.role==='ngo'&&<button className="btn btn-outline" onClick={()=>setLocationEdit({kind:'ngo'})}><MapPin size={17}/> {ngoLocation?'Update NGO location':'Set NGO location'}</button>}{user.role==='provider'&&<button className="btn btn-dark" onClick={()=>setModal(true)}><Plus size={17}/> New donation</button>}{user.role==='admin'&&<button className="btn btn-outline" disabled={busy} onClick={()=>action('/api/demo/seed')}><Plus size={17}/> Seed demo data</button>}</div></div>
{!user.verified&&<div className="notice-banner"><AlertCircle size={19}/><span>Your account is awaiting administrator verification. You can explore your workspace, but live actions may be restricted.</span></div>}
{page==='dashboard'&&<><div className="stats-grid">{[[Package,'Total donations',stats.total,'All records'],[Clock3,'Available now',stats.available,'Awaiting response'],[Truck,'In progress',stats.active,'Under coordination'],[CheckCircle2,'Completed',stats.completed,'Confirmed handovers']].map(([Icon,label,value,sub])=><div className="stat-card" key={label}><div className="stat-header"><span>{label}</span><span className="stat-icon"><Icon size={18}/></span></div><strong>{value.toLocaleString()}</strong><small>{sub}</small></div>)}</div><div className="two-col"><div className="panel"><div className="panel-heading"><div><h3>Recent donations</h3><p>Latest activity in your workspace</p></div><button className="link-button" onClick={()=>navigate('donations')}>View all <ArrowUpRight size={15}/></button></div>{donations.length?<div className="compact-list">{donations.slice(0,5).map(d=><div className="compact-row" key={d.id}><span className="list-icon"><Package size={17}/></span><span className="item-main"><b>{d.title}</b><small><MapPin size={12}/>{d.locality} · {d.quantity} meals</small></span><Status value={d.status}/></div>)}</div>:<Empty title="No donations yet" description="Create your first food listing, or ask an admin to seed clearly labelled demo data."/>}</div><div className="panel panel-dark"><span className="mini-eyebrow">THE MISSION</span><div className="panel-dark-symbol"><Leaf size={38}/></div><h2>Every meal<br/>matters.</h2><p>Make a positive difference by connecting good food with people who can share it.</p><button onClick={()=>navigate('coordinator')}>Explore coordination <ArrowUpRight size={16}/></button></div></div><div className="panel"><div className="panel-heading"><div><h3>Latest platform activity</h3><p>Transparent records from every interaction</p></div><button className="link-button" onClick={()=>navigate('activity')}>Activity log <ArrowUpRight size={15}/></button></div><ActivityList items={audit.slice(0,4)}/></div></>}
{page==='donations'&&<div className="panel"><div className="panel-heading"><div><h3>All donations</h3><p>{filtered.length} record{filtered.length===1?'':'s'} in this view</p></div><div className="search"><Search size={17}/><input placeholder="Search donations..." value={search} onChange={e=>setSearch(e.target.value)}/></div></div>{filtered.length?<div className="table-scroll"><table><thead><tr><th>DONATION</th><th>LOCATION</th><th>QUANTITY</th><th>DEADLINE</th><th>STATUS</th><th>ACTIONS</th></tr></thead><tbody>{filtered.map(d=><tr key={d.id}><td><div className="table-title"><span className="table-icon"><Package size={17}/></span><span><b>{d.title}</b><small>{d.provider_name}{d.is_demo?' · SIMULATION':''}</small></span></div></td><td>{d.locality}</td><td>{d.quantity} meals</td><td>{fmt(d.deadline)}</td><td><Status value={d.status}/></td><td><div className="row-actions"><button className="btn btn-sm btn-outline" onClick={()=>setTracking(d)}><ScanLine size={14}/> Track</button>{user.role==='provider'&&d.provider_id===user.id&&d.status==='available'&&<><button className="btn btn-sm btn-outline" disabled={busy} onClick={()=>{setEditDonation(d);setModal(true)}}>Edit</button><button className="btn btn-sm btn-outline" disabled={busy} onClick={()=>setLocationEdit({kind:'donation',id:d.id})}><MapPin size={14}/> Pickup map</button><button className="btn btn-sm btn-outline" disabled={busy} onClick={()=>{const reason=window.prompt('Reason for cancellation (at least 5 characters):');if(reason&&reason.trim().length>=5)action(`/api/donations/${d.id}/cancel`,'POST',{reason})}}>Cancel</button></>}</div></td></tr>)}</tbody></table></div>:<Empty title="No matching donations" description="Try a different search term or create a listing."/>}</div>}
{page==='offers'&&<div className="panel"><div className="panel-heading"><div><h3>Donation offers</h3><p>NGOs make the final decision to accept or decline.</p></div></div>{offers.length?<div className="offer-list">{offers.map(o=><div className="offer-row" key={o.id}><div className="offer-icon"><Send size={19}/></div><div className="offer-detail"><b>{o.donation_title}</b><p>Offered to {o.ngo_name} · Expires {fmt(o.expires_at)}</p><small>{o.reason}</small></div><div className="offer-controls"><Status value={o.status}/>{o.status==='pending'&&user.role==='ngo'&&<><button disabled={busy} className="btn btn-sm btn-dark" onClick={()=>action(`/api/offers/${o.id}/respond`,'POST',{decision:'accept'})}>Accept</button><button disabled={busy} className="btn btn-sm btn-outline" onClick={()=>action(`/api/offers/${o.id}/respond`,'POST',{decision:'decline'})}>Decline</button></>}</div></div>)}</div>:<Empty title="No offers yet" description="When the coordinator matches an eligible NGO, you'll see offers here."/>}</div>}
{page==='coordinator'&&<><div className="agent-banner"><div><span className="agent-chip"><BrainCircuit size={15}/> COORDINATION ENGINE</span><h2>Observe. Evaluate.<br/>Act. Verify.</h2><p>A safeguarded coordination workflow that checks eligibility, ranks suitable NGOs, initiates offers and records every decision.</p><button className="btn btn-white" disabled={busy||user.role==='ngo'} onClick={run}><RefreshCcw size={17}/>{busy?'Running...':'Run coordination cycle'}</button></div><div className="agent-decoration"><span>01<span>OBSERVE</span></span><span>02<span>EVALUATE</span></span><span>03<span>ACT</span></span><span>04<span>VERIFY</span></span></div></div><div className="agent-note"><AlertCircle size={18}/><span>This starter runs a deterministic, rule-governed agent workflow. An LLM is <b>optional</b> and used only when configured on the backend. All real-world coordination requires verified participants and their consent.</span></div>{agentResult&&<div className="panel"><h3>Latest coordinator run</h3><div className="run-results"><div><strong>{agentResult.created.length}</strong><span>Offers created</span></div><div><strong>{agentResult.escalated.length}</strong><span>Escalations</span></div><div><strong>{agentResult.skipped.length}</strong><span>Skipped</span></div></div>{agentResult.created.map((x,i)=><p className="result-line" key={i}><Check size={16}/> Donation #{x.donation_id} → {x.ngo}</p>)}</div>}<div className="panel"><div className="panel-heading"><div><h3>Recent agent decisions</h3><p>Actions are explainable and available for review</p></div></div><ActivityList items={audit.filter(a=>a.actor==='agent').slice(0,12)}/></div></>}
{page==='reports'&&user.role==='admin'&&<div className="panel"><div className="panel-heading"><div><h3>Milestone 2 — measurable results</h3><p>Calculated from stored records; simulation data is not evidence of real-world impact.</p></div><button className="btn btn-sm btn-outline" onClick={()=>{const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='food-rescue-results.json';a.click();URL.revokeObjectURL(url)}}>Export JSON</button></div>{report?<><div className="report-grid">{[['Total listings',report.total_donations],['Completed meals',report.completed_quantity],['Agent actions',report.agent_actions],['Human escalations',report.escalations]].map(([k,v])=><div className="stat-card" key={k}><span>{k}</span><strong>{v}</strong></div>)}</div><h3>Donation status counts</h3><div className="report-grid">{Object.entries(report.donations_by_status).map(([k,v])=><div className="mini-metric" key={k}><span>{cap(k)}</span><b>{v}</b></div>)}</div><h3>Offer response outcomes</h3><p>Accepted: {report.offer_responses.accepted} · Declined: {report.offer_responses.declined} · Timed out: {report.offer_responses.timed_out}</p><p className="muted-text">{report.disclaimer}</p></>:<Empty title="No report available" description="Verify the backend connection first."/>}</div>}
{page==='activity'&&<div className="panel"><div className="panel-heading"><div><h3>Audit trail</h3><p>Actor, action, detail and timestamp</p></div></div><ActivityList items={audit}/></div>}
{page==='admin'&&user.role==='admin'&&<div className="panel"><div className="panel-heading"><div><h3>Account verification</h3><p>Approve legitimate accounts only after checking their details.</p></div></div><div className="table-scroll"><table><thead><tr><th>ACCOUNT</th><th>ROLE</th><th>AREA</th><th>STATUS</th><th>ACTION</th></tr></thead><tbody>{users.filter(u=>u.role!=='admin').map(u=><tr key={u.id}><td><div className="table-title"><span className="table-icon"><Users size={17}/></span><span><b>{u.organisation}</b><small>{u.name} · {u.email}</small></span></div></td><td>{cap(u.role)}</td><td>{u.locality}</td><td><Pill tone={u.verified?'green':'orange'}>{u.verified?'Verified':'Pending'}</Pill></td><td><button disabled={busy} className="btn btn-sm btn-outline" onClick={()=>action(`/api/admin/users/${u.id}/verify`,'PATCH',{verified:!u.verified})}>{u.verified?'Revoke':'Verify'}</button></td></tr>)}</tbody></table></div></div>}
{locationEdit&&<LocationModal title={locationEdit.kind==='ngo'?'NGO receiving location':'Donation pickup location'} description={locationEdit.kind==='ngo'?'Select your NGO receiving premises. This will be used for GIS matching.':'Select the actual pickup point for this available donation.'} initial={locationEdit.kind==='ngo'?ngoLocation:null} onSave={saveLocation} close={()=>setLocationEdit(null)} busy={locationBusy}/>}
 {tracking&&<TrackingModal donation={tracking} user={user} close={()=>setTracking(null)} action={action} refresh={reload} flash={flash}/>}
{modal&&<DonationModal initial={editDonation} close={()=>{setModal(false);setEditDonation(null)}} submit={create} busy={busy}/>}
</>}
function ActivityList({items}){return items.length?<div className="activity-list">{items.map(a=><div className="activity-row" key={a.id}><span className="activity-symbol"><Activity size={16}/></span><div><b>{cap(a.action)}</b><p>{a.detail}</p></div><span className="activity-time">{fmt(a.created_at)}</span></div>)}</div>:<Empty title="Nothing here yet" description="Events and decisions will appear here as the platform is used."/>}
function Empty({title,description}){return <div className="empty"><span className="empty-icon"><ClipboardList size={26}/></span><b>{title}</b><p>{description}</p></div>}
// Format a Date as local wall-clock time for a datetime-local input.
// toISOString() by itself uses UTC and shifts the displayed time in India.
function toLocalDateTime(date) {
  const d = new Date(date)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16)
}

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
        {!initial&&<div className="span-two"><label>Pickup location on map (required for GIS matching)</label><p style={{fontSize:13}}>Click your actual pickup position. The map does not guess it from the locality.</p><GeoMap pickable value={pickupPoint} onSelect={setPickupPoint}/>{pickupPoint&&<small>Selected: {pickupPoint.latitude.toFixed(6)}, {pickupPoint.longitude.toFixed(6)}</small>}</div>}
        {dateError && <p className="span-two" role="alert" style={{color:'#B42318',margin:0}}>{dateError}</p>}
        <div className="span-two modal-actions"><button type="button" className="btn btn-outline" onClick={close}>Cancel</button><button disabled={busy} className="btn btn-dark">{busy?'Saving...':initial?'Save changes':'Publish donation'} <ArrowRight size={16}/></button></div>
      </form>
    </div>
  </div>
}

function TrackingModal({donation,user,close,action,refresh,flash}){
  const [events,setEvents]=useState([])
  const [geo,setGeo]=useState(null)
  const [geoError,setGeoError]=useState('')
  const [qr,setQr]=useState('')
  const [token,setToken]=useState('')
  const [camera,setCamera]=useState(false)
  const [loading,setLoading]=useState(false)
  const isNgo=user.role==='ngo'&&donation.accepted_ngo_id===user.id
  
  const canQR =
  donation.status === 'accepted' &&
  user.role === 'provider' &&
  donation.provider_id === user.id

  useEffect(()=>{
    let active=true
    request(`/api/donations/${donation.id}/tracking`)
      .then(data=>{if(active)setEvents(data.events)})
      .catch(error=>{if(active)flash(error.message,true)})
    return()=>{active=false}
  },[donation.id])

  useEffect(()=>{
    let active=true
    setGeo(null);setGeoError('')
    request(`/api/donations/${donation.id}/geo`)
      .then(data=>{if(active)setGeo(data)})
      .catch(error=>{if(active)setGeoError(error.message)})
    return()=>{active=false}
  },[donation.id])

  useEffect(()=>{
    if(!canQR)return
    let active=true
    let objectUrl=null
    const auth=localStorage.getItem('fr_token')
    fetch(`${API}/api/donations/${donation.id}/qr`,{headers:{Authorization:`Bearer ${auth}`}})
      .then(response=>{if(!response.ok)throw new Error('QR unavailable');return response.blob()})
      .then(blob=>{
        if(!active)return
        objectUrl=URL.createObjectURL(blob)
        setQr(objectUrl)
      })
      .catch(error=>{if(active)flash(error.message,true)})
    return()=>{active=false;if(objectUrl)URL.revokeObjectURL(objectUrl)}
  },[donation.id,canQR])

  // html5-qrcode owns the camera and video element. Start only after
  // the scanner container has been rendered; stop and release it on exit.
  
  useEffect(() => {
    if (!camera) return;

    let disposed = false;
    const scanner = new Html5Qrcode('food-rescue-qr-reader', false);

    // Without qrbox, the entire camera frame is scanned. This is more
    // forgiving on small laptop webcams and narrow/mobile previews.
    const startPromise = scanner.start(
      { facingMode: 'environment' },
      { fps: 10, disableFlip: false },
      (decodedText) => {
        if (disposed) return;
        setToken(decodedText.trim());
        setCamera(false);
        flash('QR scanned successfully. Confirm pickup to continue.');
      },
      () => { /* Normal frames without a QR are not errors. */ }
    ).catch((error) => {
      if (!disposed) {
        flash(`Could not start camera: ${error?.message || String(error)}. You can paste the decoded token instead.`, true);
        setCamera(false);
      }
    });

    return () => {
      disposed = true;
      // Stopping only after start settles avoids camera startup/cleanup races.
      startPromise.then(async () => {
        try { await scanner.stop(); } catch (_) { /* Scanner may never have started. */ }
        try { scanner.clear(); } catch (_) { /* Ignore cleanup failures. */ }
      });
    };
  }, [camera]);

  async function verifyPickup(){
    setLoading(true)
    try{
      const result=await action(`/api/donations/${donation.id}/pickup`,'POST',{token:token.trim()})
      if(result){await refresh();close()}
    }finally{setLoading(false)}
  }
  async function receive(){
    setLoading(true)
    try{
      const result=await action(`/api/donations/${donation.id}/complete`)
      if(result){await refresh();close()}
    }finally{setLoading(false)}
  }

  return <div className="modal-overlay" onMouseDown={close}>
    <div className="modal tracking-modal" onMouseDown={e=>e.stopPropagation()}>
      <div className="modal-head">
        <div><span className="section-kicker">DONATION #{donation.id}</span><h2>Donation journey</h2><p>{donation.title} · {donation.locality}</p></div>
        <button className="icon-btn" onClick={close}><X size={21}/></button>
      </div>
      <div className="tracking-body">
        <Status value={donation.status}/>
        <div className='scan-form' style={{marginTop:16}}><h3>GIS donation map</h3>
          {geo?.pickup||geo?.destination ? <><GeoMap pickup={geo.pickup} destination={geo.destination}/>
            <p style={{fontSize:13,marginTop:10}}>Yellow: pickup · Blue: NGO destination. Dashed line is direct distance, not a road route.</p>
            {geo.straight_line_distance_km!=null&&<p style={{fontSize:13}}>Straight-line distance: {geo.straight_line_distance_km} km</p>}</>
          : <p>{geoError?`Map unavailable: ${geoError}`:'No saved coordinates yet. The provider must set the pickup location and the NGO must set its receiving location.'}</p>}
          <p style={{fontSize:12}}>This map is not live GPS tracking. Collector location sharing and road routing are future steps.</p>
        </div>
        {canQR&&<div className="qr-card">
          <h3>Pickup verification QR</h3>
          {qr&&<img alt="Unique donation pickup verification QR" className="qr-image" src={qr}/>}
          <p>Show this code to the assigned NGO collector at pickup. The QR token is a private verification credential.</p>
        </div>}
        {isNgo&&donation.status==='accepted'&&<div className="scan-form">
          <h3>Verify pickup</h3>
          <p>Scan the provider's QR code with your camera, or paste the decoded code.</p>
          <div className="row-actions">
            <input value={token} onChange={e=>setToken(e.target.value)} placeholder="Scanned QR token" autoComplete="off"/>
            <button className="btn btn-outline" disabled={loading} onClick={()=>setCamera(value=>!value)}>
              <Camera size={17}/>{camera?'Stop camera':'Scan QR'}
            </button>
          </div>
          {camera&&<div id="food-rescue-qr-reader" style={{width:'100%',minHeight:280,marginTop:12,borderRadius:12,overflow:'visible'}}/>}
          <button className="btn btn-dark" disabled={!token.trim()||loading||camera} onClick={verifyPickup}>
            {loading?'Confirming...':'Confirm QR pickup'}
          </button>
        </div>}
        {isNgo&&donation.status==='picked_up'&&<div className="scan-form">
          <h3>Confirm receipt at NGO</h3>
          <p>Only confirm after your organisation has actually received the food.</p>
          <button className="btn btn-dark" disabled={loading} onClick={receive}>Confirm handover</button>
        </div>}
        <h3>Timestamped history</h3>
        <div className="timeline">{events.map((event,i)=><div className="timeline-event" key={i}>
          <span className="timeline-dot"/><div><b>{cap(event.action)}</b><small>{fmt(event.created_at)} · {cap(event.actor)}</small><p>{event.detail}</p></div>
        </div>)}</div>
      </div>
    </div>
  </div>
}

createRoot(document.getElementById('root')).render(<App/>)