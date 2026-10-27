import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException as FastAPIHTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.errors import validation_error_handler
from app.db.session import SessionLocal
from app.modules.audit.routes import router as audit_router
from app.modules.auth import models as auth_models  # noqa: F401 - registers ORM tables
from app.modules.auth.routes import identity_router, organizations_router
from app.modules.auth.routes import router as auth_router
from app.modules.marketplace.routes import router as marketplace_router
from app.modules.orders.routes import router as orders_router
from app.modules.pricing.routes import router as pricing_router
from app.modules.shipments.routes import router as shipments_router

settings = get_settings()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
app = FastAPI(title=settings.app_name, version="0.1.0", description="DOGO Web MVP backend API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"])
app.add_exception_handler(RequestValidationError, validation_error_handler)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))[:128]
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception):
    logging.getLogger("dogo.api").exception("Unhandled request error", extra={"request_id": getattr(request.state, "request_id", None)})
    return JSONResponse(status_code=500, content={"error": {"code": "INTERNAL_ERROR", "message": "The request could not be processed.", "details": [], "request_id": getattr(request.state, "request_id", None)}})


@app.exception_handler(FastAPIHTTPException)
async def http_error_handler(request: Request, exc: FastAPIHTTPException):
    code = {401: "UNAUTHORIZED", 403: "FORBIDDEN", 404: "NOT_FOUND", 409: "CONFLICT", 429: "RATE_LIMITED"}.get(exc.status_code, "REQUEST_ERROR")
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be processed."
    return JSONResponse(status_code=exc.status_code, headers=exc.headers, content={"error": {"code": code, "message": message, "details": [], "request_id": getattr(request.state, "request_id", None)}})


@app.get("/health/live", tags=["health"])
def live():
    return {"status": "live"}


@app.get("/health/ready", tags=["health"])
def ready():
    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


app.include_router(auth_router, prefix=f"{settings.api_v1_prefix}/auth", tags=["identity"])
app.include_router(identity_router, prefix=settings.api_v1_prefix, tags=["identity"])
app.include_router(organizations_router, prefix=settings.api_v1_prefix, tags=["organizations"])
app.include_router(pricing_router, prefix=f"{settings.api_v1_prefix}/pricing", tags=["pricing"])
app.include_router(marketplace_router, prefix=f"{settings.api_v1_prefix}", tags=["marketplace", "merchant"])
app.include_router(shipments_router, prefix=settings.api_v1_prefix, tags=["shipments", "tracking", "waybills"])
app.include_router(orders_router, prefix=settings.api_v1_prefix, tags=["orders", "cart"])
app.include_router(audit_router, prefix=settings.api_v1_prefix, tags=["administration"])
