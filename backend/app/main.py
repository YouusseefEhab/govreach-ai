
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.campaigns import router as campaigns_router
from app.api.v1.generation import router as generation_router
from app.api.v1.images import router as images_router


app = FastAPI(
    title="GovReach AI API",
    version="0.2.0",
    description=(
        "Generative AI platform for Egyptian government "
        "awareness campaigns."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(campaigns_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")
app.include_router(images_router, prefix="/api/v1")


@app.get("/")
def root():
    return {
        "message": "GovReach AI API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }
