"""Shared route dependencies; no FastAPI router imports here (avoids circular imports)."""
from __future__ import annotations
import os
import json
import secrets
import qrcode
from io import BytesIO
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from urllib import request as urlrequest
from fastapi import Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy import select, func, text
from sqlalchemy.orm import Session
from .database import db_session, engine, Base
from .config import GIS_RADIUS_KM
from .models import User, Donation, CollectorTracking, DeliveryReceipt, Offer, Audit
from .schemas import *
from .security import utcnow, aware, password_hash, check_password, token_for, current_user, require_role
from .services.helpers import serial_user, serial_donation, log, expire_if_needed
from .services.routing import driving_route
from .services.gis import ensure_postgis, set_user_point, set_pickup_point, point_coordinates
