import React, {useState,useEffect,useRef} from 'react'
import {Html5Qrcode} from 'html5-qrcode'
import {Camera} from 'lucide-react'
function QRScanner({token,setToken,loading,onVerify,flash}) {
  const [camera,setCamera]=useState(false)
  
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
      startPromise.then(async () => {
        try { await scanner.stop(); } catch (_) { /* Scanner may never have started. */ }
        try { scanner.clear(); } catch (_) { /* Ignore cleanup failures. */ }
      });
    };
  }, [camera]);

  return (
<div className="scan-form">
  <h3>Verify pickup</h3><p>Scan the provider's QR code with your camera, or paste the decoded code.</p>
  <div className="row-actions">
    <input value={token} onChange={e=>setToken(e.target.value)} placeholder="Scanned QR token" autoComplete="off"/>
    <button type="button" className="btn btn-outline" disabled={loading} onClick={()=>setCamera(value=>!value)}>
      <Camera size={17}/>{camera?'Stop camera':'Scan QR'}
    </button>
  </div>
  {camera&&<div id="food-rescue-qr-reader" style={{width:'100%',minHeight:280,marginTop:12,borderRadius:12,overflow:'visible'}}/>}
  <button type="button" className="btn btn-dark" disabled={!token.trim()||loading||camera} onClick={onVerify}>
    {loading?'Confirming...':'Confirm QR pickup'}
  </button>
</div>
  )
}
export default QRScanner
