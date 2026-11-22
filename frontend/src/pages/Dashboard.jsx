import Overview from './Overview'
import Donations from './Donations'
import Offers from './Offers'
import Coordinator from './Coordinator'
import Reports from './Reports'
import Activity from './Activity'
import Admin from './Admin'
import React, {useState,useEffect,useRef} from 'react'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
import {request} from '../services/api'
import {fmt,cap} from '../utils/formatters'
import {Pill,Status} from '../components/StatusBadge'
import ActivityList from '../components/ActivityList'
import Empty from '../components/EmptyState'
import DonationModal from '../donations/DonationModal'
import TrackingModal from '../donations/TrackingModal'
import LocationModal from '../maps/LocationModal'
function Workspace({page,user,navigate,flash}){const [donations,setDonations]=useState([]);const [offers,setOffers]=useState([]);const [stats,setStats]=useState({total:0,available:0,active:0,completed:0,meals:0});const [audit,setAudit]=useState([]);const [users,setUsers]=useState([]);const [busy,setBusy]=useState(false);const [modal,setModal]=useState(false);const [search,setSearch]=useState('');const [agentResult,setAgentResult]=useState(null);const [tracking,setTracking]=useState(null);const [editDonation,setEditDonation]=useState(null);const [report,setReport]=useState(null);const [locationEdit,setLocationEdit]=useState(null);const [locationBusy,setLocationBusy]=useState(false);const [ngoLocation,setNgoLocation]=useState(null)
async function reload(){try{const [d,o,s,a]=await Promise.all([request('/api/donations'),request('/api/offers'),request('/api/stats'),request('/api/audit')]);setDonations(d);setOffers(o);setStats(s);setAudit(a);if(user.role==='admin'){setUsers(await request('/api/admin/users'));setReport(await request('/api/reports'))}}catch(e){flash(e.message,true)}}
useEffect(()=>{reload()},[page,user.id]);
useEffect(()=>{if(user.role!=='ngo')return;let active=true;request('/api/me/location').then(data=>{if(active)setNgoLocation(data.location)}).catch(()=>{});return()=>{active=false}},[user.id,user.role]);
async function saveLocation(point){setLocationBusy(true);try{const path=locationEdit?.kind==='ngo'?'/api/me/location':`/api/donations/${locationEdit.id}/location`;const result=await request(path,'PUT',point);if(locationEdit?.kind==='ngo')setNgoLocation(point);flash(result.message||'Location saved');setLocationEdit(null);await reload()}catch(error){flash(error.message,true)}finally{setLocationBusy(false)}}
const action=async(path,method='POST',body)=>{setBusy(true);try{const r=await request(path,method,body);await reload();flash(r.message||'Updated successfully');return r}catch(e){flash(e.message,true)}finally{setBusy(false)}}
const create=async(body)=>{const result=await action(editDonation?`/api/donations/${editDonation.id}`:'/api/donations',editDonation?'PATCH':'POST',body);if(result){setModal(false);setEditDonation(null);navigate('donations')}}
const run=async()=>{const r=await action('/api/agent/run');if(r)setAgentResult(r)}
const filtered=donations.filter(d=>[d.title,d.locality,d.food_type,d.provider_name].join(' ').toLowerCase().includes(search.toLowerCase()))
const title=({dashboard:'Overview',donations:'Food donations',offers:'Offers & requests',coordinator:'Smart matching',activity:'Activity history',admin:'Administration',reports:'Reports & results'})[page]||'Workspace'
return <><div className="page-header"><div><div className="section-kicker">{user.role.toUpperCase()} WORKSPACE <span className="header-slash">/</span> GHAZIABAD</div><h1>{page==='dashboard'?`Hello, ${user.name.split(' ')[0]}.`:title}</h1><p>{page==='dashboard'?'Here’s what’s happening in your food rescue network.':({donations:'A clear view of surplus food and its journey.',offers:'Keep track of requests, responses and handovers.',coordinator:'Track NGO matching and donation requests.',activity:'Every important action, recorded for transparency.',admin:'Review participants and manage platform access.',reports:'Reproducible counts from real application records.'})[page]}</p></div><div className="header-actions">{user.role==='ngo'&&<button className="btn btn-outline" onClick={()=>setLocationEdit({kind:'ngo'})}><MapPin size={17}/> {ngoLocation?'Update NGO location':'Set NGO location'}</button>}{user.role==='provider'&&<button className="btn btn-dark" onClick={()=>setModal(true)}><Plus size={17}/> New donation</button>}{user.role==='admin'&&<button className="btn btn-outline" disabled={busy} onClick={()=>action('/api/demo/seed')}><Plus size={17}/> Seed demo data</button>}</div></div>
{!user.verified&&<div className="notice-banner"><AlertCircle size={19}/><span>Your account is awaiting administrator verification. You can explore your workspace, but live actions may be restricted.</span></div>}
{page==='dashboard'&&<Overview donations={donations} stats={stats} navigate={navigate} audit={audit}/>}
{page==='donations'&&<Donations filtered={filtered} search={search} setSearch={setSearch} user={user} setTracking={setTracking} busy={busy} setEditDonation={setEditDonation} setModal={setModal} setLocationEdit={setLocationEdit} action={action}/>}
{page==='offers'&&<Offers offers={offers} user={user} busy={busy} action={action}/>}
{page==='coordinator'&&<Coordinator busy={busy} user={user} run={run} agentResult={agentResult} audit={audit} donations={donations} offers={offers} navigate={navigate}/>}
{page==='reports'&&<Reports user={user} report={report}/>}
{page==='activity'&&<Activity audit={audit} isAdmin={user.role==='admin'}/>}
{page==='admin'&&<Admin user={user} users={users} busy={busy} action={action}/>}
{locationEdit&&<LocationModal title={locationEdit.kind==='ngo'?'NGO receiving location':'Donation pickup location'} description={locationEdit.kind==='ngo'?'Select your NGO receiving premises. This will be used for GIS matching.':'Select the actual pickup point for this available donation.'} initial={locationEdit.kind==='ngo'?ngoLocation:null} onSave={saveLocation} close={()=>setLocationEdit(null)} busy={locationBusy}/>}
 {tracking&&<TrackingModal donation={tracking} user={user} close={()=>setTracking(null)} action={action} refresh={reload} flash={flash}/>}
{modal&&<DonationModal initial={editDonation} close={()=>{setModal(false);setEditDonation(null)}} submit={create} busy={busy}/>}
</>}
export default Workspace
