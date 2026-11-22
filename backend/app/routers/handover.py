from __future__ import annotations
from fastapi import APIRouter
from ..dependencies import *

router = APIRouter()

@router.get('/api/donations/{donation_id}/qr')
def donation_qr(
    donation_id: int,
    user: User = Depends(current_user),
    db: Session = Depends(db_session)
):
    d = db.get(Donation, donation_id)

    # Check whether donation exists
    if not d:
        raise HTTPException(
            status_code=404,
            detail="Donation not found"
        )

    # Only the provider who created the donation
    # can view its pickup QR code
    if user.role != "provider" or d.provider_id != user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the donation provider can view this QR code"
        )

    # QR is available only after NGO acceptance
    if d.status != "accepted":
        raise HTTPException(
            status_code=409,
            detail="QR available only for accepted donations"
        )

    # Generate the unique pickup QR code
    img = qrcode.make(d.qr_token)

    buffer = BytesIO()
    img.save(buffer, format="PNG")

    return Response(
        content=buffer.getvalue(),
        media_type="image/png",
        headers={"Cache-Control": "no-store"}
    )

@router.post('/api/donations/{donation_id}/pickup')
def pickup(donation_id:int,body:ScanIn,user:User=Depends(current_user),db:Session=Depends(db_session)):
    require_role(user,'ngo')
    d=db.get(Donation,donation_id)
    if not d or d.accepted_ngo_id!=user.id:raise HTTPException(404,'Donation not assigned to this NGO')
    if d.status!='accepted':raise HTTPException(409,'Donation not in accepted state')
    if not secrets.compare_digest(body.token,d.qr_token):raise HTTPException(403,'Invalid QR verification token')
    d.status='picked_up';log(db,d.id,'ngo','picked_up','Verified QR pickup recorded',user.id);db.commit()
    return {'status':'picked_up'}

@router.post('/api/donations/{donation_id}/complete')
def complete(donation_id:int,user:User=Depends(current_user),db:Session=Depends(db_session)):
    raise HTTPException(409,'Use /api/donations/{donation_id}/delivery-confirm to record receipt details')
