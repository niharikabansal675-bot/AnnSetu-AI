import React, {useState,useEffect,useRef} from 'react'
function DeliveryReceipt({donation,receiverName,setReceiverName,receivedQuantity,setReceivedQuantity,foodCondition,setFoodCondition,receiptNotes,setReceiptNotes,receiptConfirmed,setReceiptConfirmed,loading,confirmDelivery}) {
return (
        <div className='scan-form'>
          <h3>Confirm delivery receipt</h3>
          <p>Only submit when food has physically reached the NGO. This is an account-holder attestation, not independently verified.</p>
          <label>Receiving person's name<input required minLength={2} maxLength={130} value={receiverName} onChange={e=>setReceiverName(e.target.value)} placeholder='Name of person receiving food'/></label>
          <label>Meals actually received<input type='number' min={1} max={donation.quantity} value={receivedQuantity} onChange={e=>setReceivedQuantity(e.target.value)}/></label>
          <label>Food condition<select value={foodCondition} onChange={e=>setFoodCondition(e.target.value)}><option value='good'>Good</option><option value='partially_damaged'>Partially damaged</option><option value='rejected'>Rejected — escalate to admin</option></select></label>
          <label>Notes (optional)<textarea rows={3} maxLength={500} value={receiptNotes} onChange={e=>setReceiptNotes(e.target.value)}/></label>
          <label style={{display:'flex',gap:9,alignItems:'start'}}><input type='checkbox' checked={receiptConfirmed} onChange={e=>setReceiptConfirmed(e.target.checked)}/> I confirm that the food was received at the NGO destination.</label>
          {foodCondition==='rejected'&&<p style={{color:'#B42318'}}>Rejected food cannot be marked completed. Contact an administrator.</p>}
          <button className='btn btn-dark' disabled={loading||!receiptConfirmed||receiverName.trim().length<2||Number(receivedQuantity)<1||Number(receivedQuantity)>donation.quantity||foodCondition==='rejected'} onClick={confirmDelivery}>{loading?'Saving...':'Record delivery receipt'}</button>
        </div>
)
}
export default DeliveryReceipt
