from fastapi import FastAPI
from .endpoints import router as api_router

app = FastAPI(title="Argumentation Analysis API")

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to the Argumentation Analysis API"}