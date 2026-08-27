"""
Servidor Principal FastAPI — HealthSignal LATAM.
Configuración de CORS, ruteadores /api/v1 y documentación OpenAPI Swagger.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.patients import router as patients_router
from app.api.signals import router as signals_router
from app.api.evidence import router as evidence_router
from app.api.alerts import router as alerts_router

app = FastAPI(
    title="HealthSignal LATAM — RISA Data V1.0 API",
    description="API REST de Servicios Clínicos, Priorización Predictiva y Linaje de Evidencias Explicables",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS para integración con Frontend React SPA
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir ruteadores con prefijo de versión /api/v1
app.include_router(patients_router, prefix="/api/v1")
app.include_router(signals_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")


@app.get("/", tags=["Health Check"])
def root_health_check():
    return {
        "status": "ONLINE",
        "system": "HealthSignal LATAM",
        "version": "v1.0.0",
        "docs": "/docs"
    }
