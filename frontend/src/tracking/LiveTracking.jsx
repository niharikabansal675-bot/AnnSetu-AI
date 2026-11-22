import React, {useState,useEffect,useRef} from 'react'
import {ArrowRight,ArrowUpRight,Leaf,LayoutDashboard,Package,Users,Activity,LogOut,Plus,Menu,X,ShieldCheck,Clock3,CheckCircle2,MapPin,UtensilsCrossed,HeartHandshake,ClipboardList,BrainCircuit,ScanLine,Camera,BarChart3,ChevronRight,Search,Mail,Lock,User,Building2,Truck,RefreshCcw,AlertCircle,Send,Check,Command,SlidersHorizontal} from 'lucide-react'
import {fmt} from '../utils/formatters'
function LiveTracking({donation,live,isNgo,sharingLocal,startSharing,stopSharing,gpsError,cardStyle}) {
  return (
        <div style={{...cardStyle,background:'#F3F8FD'}}>
          <h3 style={{margin:'0 0 8px'}}>Collector location updates</h3>
          <p style={{fontSize:13}}>Location is shared only after the NGO collector grants permission. Keep this tracking window open during delivery. GPS stops when you close it.</p>
          <p style={{fontSize:13}}>Sharing: <strong>{live?.sharing?'Enabled':'Off'}</strong> · Position: <strong>{live?.fresh?'Recently updated':live?.sharing?'Waiting for an update':'Not shared'}</strong></p>
          {live?.updated_at&&<p style={{fontSize:12}}>Last update: {fmt(live.updated_at)}</p>}
          {live?.position&&<p style={{fontSize:12}}>GPS accuracy: ±{Math.round(live.position.accuracy_m)} m</p>}
          {isNgo&&donation.status==='picked_up'&&<div className='row-actions'>
            {!sharingLocal?<button type='button' className='btn btn-dark' onClick={startSharing}><MapPin size={16}/> Start sharing my location</button>
              :<button type='button' className='btn btn-outline' onClick={stopSharing}>Stop sharing</button>}
          </div>}
          {gpsError&&<p role='alert' style={{color:'#B42318',fontSize:13}}>{gpsError}</p>}
        </div>
  )
}
export default LiveTracking
