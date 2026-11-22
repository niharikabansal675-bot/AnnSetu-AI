const API=import.meta.env.VITE_API_URL||'http://127.0.0.1:8000'
async function request(path,method='GET',body){const token=localStorage.getItem('fr_token');let r;try{r=await fetch(`${API}${path}`,{method,headers:{'Content-Type':'application/json',...(token?{Authorization:`Bearer ${token}`}:{})},...(body!==undefined?{body:JSON.stringify(body)}:{})})}catch(e){throw new Error(`Cannot reach the Food Rescue API at ${API}. Check that FastAPI is running and CORS allows this frontend address. (${e.message})`)}const data=await r.json().catch(()=>({}));if(!r.ok)throw new Error(typeof data.detail==='string'?data.detail:`Request failed (${r.status})`);return data}

export {API,request}
