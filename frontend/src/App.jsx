import React, {useState,useEffect,useRef} from 'react'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,Activity,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
import {request} from './services/api'
import {cap} from './utils/formatters'
import Logo from './components/Navbar'
import {Pill} from './components/StatusBadge'
import Home from './pages/Home'
import Auth from './pages/Auth'
import Workspace from './pages/Dashboard'
import Sidebar from './components/Sidebar'
function App(){const [token,setToken]=useState(localStorage.getItem('fr_token'));const [user,setUser]=useState(null);const [page,setPage]=useState(token?'dashboard':'home');const [busy,setBusy]=useState(false);const [error,setError]=useState('');const [notice,setNotice]=useState('');const [mobile,setMobile]=useState(false)
useEffect(()=>{if(token)request('/api/me').then(setUser).catch(()=>{localStorage.removeItem('fr_token');setToken(null);setPage('home')})},[token])
const flash=(msg,isError=false)=>{isError?setError(msg):setNotice(msg);setTimeout(()=>{setNotice('');setError('')},5000)}
const logout=()=>{localStorage.removeItem('fr_token');setToken(null);setUser(null);setPage('home')}
const auth=async(payload,isRegister)=>{setBusy(true);setError('');try{const data=await request(isRegister?'/api/auth/register':'/api/auth/login','POST',payload);localStorage.setItem('fr_token',data.token);setToken(data.token);setUser(data.user);setPage('dashboard');flash(isRegister?'Account created. Admin verification is required before posting or receiving real donations.':'Welcome back!')}catch(e){flash(e.message,true)}finally{setBusy(false)}}
const navigate=(p)=>{setPage(p);setMobile(false);setError('');window.scrollTo({top:0,behavior:'smooth'})}

if (token && !user) {
  return <div className="site" style={{minHeight:'100vh',display:'flex',alignItems:'center',justifyContent:'center',background:'#F6F9FD',color:'#17324F'}} role="status" aria-live="polite">Loading your Food Rescue workspace...</div>
}
return <><div className="site">{!token? <><header className="public-nav wrap"><Logo/><nav className="desktop-nav"><a href="#how" onClick={()=>setPage('home')}>How it works</a><a href="#why" onClick={()=>setPage('home')}>Our mission</a><a href="#features" onClick={()=>setPage('home')}>Platform</a></nav><div className="nav-actions"><button className="btn btn-text" onClick={()=>navigate('login')}>Log in</button><button className="btn btn-dark" onClick={()=>navigate('register')}>Get started <ArrowUpRight size={16}/></button></div></header>{page==='home'?<Home navigate={navigate}/>:<Auth page={page} navigate={navigate} onSubmit={auth} busy={busy}/>}</>:<div className="app-shell"><Sidebar mobile={mobile} setMobile={setMobile} page={page} navigate={navigate} user={user} logout={logout}/><div className="main-area"><header className="app-topbar"><button className="icon-btn mobile-only" onClick={()=>setMobile(true)}><Menu size={22}/></button><span className="breadcrumb">Workspace <ChevronRight size={14}/> <b>{cap(page)}</b></span><div className="topbar-right"><Pill tone={user?.verified?'green':'orange'}>{user?.verified?'Verified account':'Verification pending'}</Pill><span className="avatar small">{user?.name?.slice(0,1).toUpperCase()}</span></div></header><div className="content"><Workspace page={page} user={user} navigate={navigate} flash={flash}/></div></div></div>}{(notice||error)&&<div className={'toast '+(error?'error':'')}><span>{error||notice}</span><button onClick={()=>{setError('');setNotice('')}}><X size={15}/></button></div>}</div></>}
export default App