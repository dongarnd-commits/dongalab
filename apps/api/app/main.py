from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router
from app.core.config import get_settings

app = FastAPI(title="DATCO Skeleton API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=[get_settings().web_origin], allow_credentials=False, allow_methods=["GET"], allow_headers=["Accept", "Content-Type"])
app.include_router(router)
