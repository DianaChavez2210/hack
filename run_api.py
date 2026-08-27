"""
Punto de Entrada CLI para Iniciar el Servidor API Backend FastAPI (Uvicorn).
Ejecución:
    python run_api.py
"""

import sys
import uvicorn
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))

if __name__ == "__main__":
    print("=" * 75)
    print("  HEALTHSIGNAL LATAM — INICIANDO SERVIDOR API BACKEND (FASTAPI)")
    print("  Documentación Swagger: http://localhost:8000/docs")
    print("===========================================================================")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
