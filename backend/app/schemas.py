from __future__ import annotations
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, EmailStr, Field

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=130)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal['provider','ngo']
    organisation: str = Field(min_length=2, max_length=180)
    locality: str = Field(min_length=2, max_length=100)
    capacity: int = Field(default=0, ge=0, le=100000)

class CoordinatesIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class DonationIn(BaseModel):
    title: str = Field(min_length=4, max_length=150)
    food_type: str = Field(min_length=2, max_length=80)
    quantity: int = Field(gt=0, le=100000)
    locality: str = Field(min_length=2, max_length=90)
    address: str = Field(min_length=5, max_length=300)
    prepared_at: datetime
    storage: str = Field(min_length=4, max_length=160)
    deadline: datetime
    # Optional until the map picker is added to the React donation form.
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

class LivePointIn(CoordinatesIn):
    accuracy_m: float = Field(ge=0, le=10000)

class DeliveryConfirmIn(BaseModel):
    receiver_name: str = Field(min_length=2, max_length=130)
    received_quantity: int = Field(gt=0, le=100000)
    condition: Literal['good', 'partially_damaged', 'rejected']
    notes: str = Field(default='', max_length=500)
    confirmed_received: bool

class ScanIn(BaseModel):
    token: str

class VerifyIn(BaseModel):
    verified: bool

class CancelIn(BaseModel):
    reason: str = Field(min_length=5, max_length=300)

class DonationUpdateIn(BaseModel):
    title: str = Field(min_length=4, max_length=150)
    quantity: int = Field(gt=0, le=100000)
    storage: str = Field(min_length=4, max_length=160)
    deadline: datetime

class OfferAction(BaseModel):
    decision: Literal['accept','decline']
