const fmt = d=>new Date(d).toLocaleString('en-IN',{day:'numeric',month:'short',hour:'numeric',minute:'2-digit'})
const cap = s=>s ? s.replaceAll('_',' ').replace(/\b\w/g,x=>x.toUpperCase()):''
export {fmt,cap}

export function toLocalDateTime(date) {
  const d = new Date(date)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16)
}
