from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import CORS_ORIGINS
from .database import Base, engine
from . import models  # register all ORM tables before create_all
from .routers import auth, locations, donations, offers, coordinator, audit, handover, delivery, admin

app = FastAPI(title='Food Rescue API', version='0.1.0', description='Ghaziabad food rescue coordination API')
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'],
    allow_headers=['Authorization', 'Content-Type', 'Accept'],
)

@app.on_event('startup')
def startup():
    Base.metadata.create_all(engine)

@app.get('/api/health')
def health():
    return {'status':'ok','service':'food-rescue-api'}

# Keep API paths and method signatures exactly as in the working monolith.
for router_module in (auth, locations, donations, offers, coordinator, audit, handover, delivery, admin):
    app.include_router(router_module.router)
