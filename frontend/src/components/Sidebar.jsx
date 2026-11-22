import React from 'react'
import {LayoutDashboard,Package,Send,BrainCircuit,Activity,BarChart3,ShieldCheck,X,HeartHandshake,LogOut} from 'lucide-react'
import Logo from './Navbar'
import {cap} from '../utils/formatters'

export default function Sidebar({mobile,setMobile,page,navigate,user,logout}) {
 return (<aside className={'sidebar '+(mobile?'open':'')}><div className="sidebar-top"><Logo/><button className="icon-btn mobile-only" onClick={()=>setMobile(false)}><X size={20}/></button></div><div className="workspace-label">WORKSPACE</div><nav className="side-nav">{[[LayoutDashboard,'dashboard','Overview'],[Package,'donations','Donations'],[Send,'offers','Offers & requests'],[BrainCircuit,'coordinator','AI coordinator'],[Activity,'activity','Activity log'],...(user?.role==='admin'?[[BarChart3,'reports','Reports']]:[]),...(user?.role==='admin'?[[ShieldCheck,'admin','Administration']]:[])].map(([Icon,key,label])=><button key={key} className={page===key?'active':''} onClick={()=>navigate(key)}><Icon size={18}/>{label}{page===key&&<span className="side-active-dot"/>}</button>)}</nav><div className="sidebar-bottom"><div className="help-panel"><HeartHandshake size={20}/><b>Small actions, big impact.</b><p>Making food donation simpler, one connection at a time.</p></div><button className="account" onClick={logout}><span className="avatar">{user?.name?.slice(0,1).toUpperCase()||'U'}</span><span className="account-text"><b>{user?.name||'Account'}</b><small>{cap(user?.role||'')}</small></span><LogOut size={17}/></button></div></aside>)
}
