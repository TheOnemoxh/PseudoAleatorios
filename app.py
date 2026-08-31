"""
FastAPI Application for Pseudo-Random Number Generator (PRNG) Suite
Clean, direct REST API serving frontend UI with dynamic charts and Excel exports.
"""

import io
import os
import tempfile
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response, FileResponse
from starlette.background import BackgroundTask
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from core.generators import (
    generate_gclm,
    generate_gcm,
    generate_cuadrados_medios,
    generate_productos_medios,
    generate_bbs,
)
from core.validators import (
    validate_gclm,
    validate_gcm,
    validate_cuadrados_medios,
    validate_productos_medios,
    validate_bbs,
)
from core.recommenders import (
    generate_gclm_optimal,
    generate_gcm_optimal,
    generate_cuadrados_medios_optimal,
    generate_productos_medios_optimal,
    generate_bbs_optimal,
)
from core.excel_exporter import export_prng_to_excel
from core.random_tests import run_all_tests


from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Generador de Numeros Pseudoaleatorios",
    description="Suite interactiva para generacion y analisis de numeros pseudoaleatorios.",
    version="2.0.0"
)

# Mount static and templates using absolute paths
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# Request Models
class GenerateRequest(BaseModel):
    method: str
    params: Dict[str, Any]


class ValidateRequest(BaseModel):
    method: str
    params: Dict[str, Any]


class RecommendRequest(BaseModel):
    method: str
    sub_type: Optional[str] = "default"


class TestsRequest(BaseModel):
    numbers: list
    alpha: float = 0.05


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renders the main single-page application interface."""
    return templates.TemplateResponse(request=request, name="index.html")


@app.post("/api/generate")
async def api_generate(payload: GenerateRequest):
    """Executes the selected PRNG algorithm, returns sequence trace, statistics, and cycle detection."""
    method = payload.method.lower().strip()
    p = payload.params

    try:
        if method in ["congruencial_mixto", "gclm"]:
            X0 = int(p.get("X0", 0))
            a = int(p.get("a", 1))
            c = int(p.get("c", 1))
            m = int(p.get("m", 1))
            n = int(p.get("n", 50))
            result = generate_gclm(X0, a, c, m, n)

        elif method in ["congruencial_multiplicativo", "gcm"]:
            X0 = int(p.get("X0", 1))
            a = int(p.get("a", 1))
            m = int(p.get("m", 1))
            n = int(p.get("n", 50))
            result = generate_gcm(X0, a, m, n)

        elif method in ["cuadrados_medios", "cm"]:
            X0 = int(p.get("X0", 1000))
            D = int(p.get("D", 4))
            n = int(p.get("n", 30))
            result = generate_cuadrados_medios(X0, D, n)

        elif method in ["productos_medios", "pm"]:
            X0 = int(p.get("X0", 1000))
            X1 = int(p.get("X1", 1001))
            D = int(p.get("D", 4))
            n = int(p.get("n", 30))
            result = generate_productos_medios(X0, X1, D, n)

        elif method in ["blum_blum_shub", "bbs"]:
            p_val = int(p.get("p", 499))
            q_val = int(p.get("q", 503))
            s_val = int(p.get("s", 8923))
            n = int(p.get("n", 50))
            result = generate_bbs(p_val, q_val, s_val, n)

        else:
            raise HTTPException(status_code=400, detail=f"Metodo desconocido: {method}")

        return JSONResponse(content=result)

    except ValueError as ve:
        return JSONResponse(
            status_code=400,
            content={"success": False, "errors": [f"Error de formato numerico: {str(ve)}"]}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "errors": [f"Error interno del generador: {str(e)}"]}
        )


@app.post("/api/validate")
async def api_validate(payload: ValidateRequest):
    """Validates parameters in real-time according to algebraic theorems."""
    method = payload.method.lower().strip()
    p = payload.params

    try:
        if method in ["congruencial_mixto", "gclm"]:
            X0 = int(p.get("X0", 0))
            a = int(p.get("a", 1))
            c = int(p.get("c", 1))
            m = int(p.get("m", 1))
            res = validate_gclm(X0, a, c, m)

        elif method in ["congruencial_multiplicativo", "gcm"]:
            X0 = int(p.get("X0", 1))
            a = int(p.get("a", 1))
            m = int(p.get("m", 1))
            res = validate_gcm(X0, a, m)

        elif method in ["cuadrados_medios", "cm"]:
            X0 = int(p.get("X0", 1000))
            D = int(p.get("D", 4))
            res = validate_cuadrados_medios(X0, D)

        elif method in ["productos_medios", "pm"]:
            X0 = int(p.get("X0", 1000))
            X1 = int(p.get("X1", 1001))
            D = int(p.get("D", 4))
            res = validate_productos_medios(X0, X1, D)

        elif method in ["blum_blum_shub", "bbs"]:
            p_val = int(p.get("p", 499))
            q_val = int(p.get("q", 503))
            s_val = int(p.get("s", 8923))
            res = validate_bbs(p_val, q_val, s_val)
        else:
            return {"valid": False, "errors": ["Metodo desconocido"]}

        return JSONResponse(content=res)
    except Exception as e:
        return JSONResponse(content={"valid": False, "errors": [f"Valores incompletos o invalidos: {str(e)}"]})


@app.post("/api/recommend")
async def api_recommend(payload: RecommendRequest):
    """Generates optimal random parameters based on algebraic rules."""
    method = payload.method.lower().strip()
    sub_type = payload.sub_type or "default"

    if method in ["congruencial_mixto", "gclm"]:
        res = generate_gclm_optimal(scale=sub_type)
    elif method in ["congruencial_multiplicativo", "gcm"]:
        res = generate_gcm_optimal(case_type=sub_type if sub_type in ["pow2", "prime"] else "pow2")
    elif method in ["cuadrados_medios", "cm"]:
        D = 4 if sub_type != "6" else 6
        res = generate_cuadrados_medios_optimal(D=D)
    elif method in ["productos_medios", "pm"]:
        D = 4 if sub_type != "6" else 6
        res = generate_productos_medios_optimal(D=D)
    elif method in ["blum_blum_shub", "bbs"]:
        res = generate_bbs_optimal()
    else:
        raise HTTPException(status_code=400, detail="Metodo desconocido")

    return JSONResponse(content=res)


@app.post("/api/tests")
async def api_tests(payload: TestsRequest):
    """Ejecuta las 7 pruebas estadisticas de aleatoriedad (Promedio, Frecuencia, Distancia,
    Series, Kolmogorov-Smirnov, Poker y Corridas Arriba/Abajo del Promedio) sobre una
    secuencia de numeros ya generada, con el nivel de significancia (alpha) indicado
    por el usuario."""
    try:
        numbers = [float(x) for x in (payload.numbers or [])]
        result = run_all_tests(numbers, payload.alpha)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"success": False, "errors": [f"Error al ejecutar las pruebas estadisticas: {str(e)}"]}
        )


def _generate_excel_response(method: str, p: dict, custom_filename: Optional[str] = None):
    if method in ["congruencial_mixto", "gclm"]:
        gen_res = generate_gclm(int(p.get("X0", 0)), int(p.get("a", 1)), int(p.get("c", 1)), int(p.get("m", 1)), int(p.get("n", 50)))
    elif method in ["congruencial_multiplicativo", "gcm"]:
        gen_res = generate_gcm(int(p.get("X0", 1)), int(p.get("a", 1)), int(p.get("m", 1)), int(p.get("n", 50)))
    elif method in ["cuadrados_medios", "cm"]:
        gen_res = generate_cuadrados_medios(int(p.get("X0", 1000)), int(p.get("D", 4)), int(p.get("n", 30)))
    elif method in ["productos_medios", "pm"]:
        gen_res = generate_productos_medios(int(p.get("X0", 1000)), int(p.get("X1", 1001)), int(p.get("D", 4)), int(p.get("n", 30)))
    elif method in ["blum_blum_shub", "bbs"]:
        gen_res = generate_bbs(int(p.get("p", 499)), int(p.get("q", 503)), int(p.get("s", 8923)), int(p.get("n", 50)))
    else:
        raise HTTPException(status_code=400, detail="Metodo no soportado")

    if not gen_res.get("success"):
        raise HTTPException(status_code=400, detail="Parametros invalidos para generar el reporte Excel")

    try:
        alpha = float(p.get("alpha", 0.05))
        if not (0 < alpha < 1):
            alpha = 0.05
    except (TypeError, ValueError):
        alpha = 0.05

    excel_buf = export_prng_to_excel(gen_res, alpha=alpha)
    excel_bytes = excel_buf.getvalue()
    
    filename = custom_filename or f"PRNG_{method}.xlsx"
    if not filename.endswith(".xlsx"):
        filename += ".xlsx"

    # Create temporary file for Starlette FileResponse with automatic background cleanup
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.write(excel_bytes)
    tmp.close()

    return FileResponse(
        path=tmp.name,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        background=BackgroundTask(lambda: os.unlink(tmp.name) if os.path.exists(tmp.name) else None)
    )


@app.get("/api/download/{filename}")
@app.get("/api/export-excel/{filename}")
@app.get("/api/export-excel")
async def api_export_excel_get(request: Request, filename: Optional[str] = None):
    """Direct browser GET download for Excel file with 100% native .xlsx filename."""
    params = dict(request.query_params)
    method = params.pop("method", "congruencial_mixto").lower().strip()
    try:
        return _generate_excel_response(method, params, custom_filename=filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar archivo Excel: {str(e)}")


@app.post("/api/export-excel")
async def api_export_excel(payload: GenerateRequest):
    """JSON POST endpoint for Excel generation."""
    method = payload.method.lower().strip()
    p = payload.params
    try:
        return _generate_excel_response(method, p)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al generar archivo Excel: {str(e)}")


