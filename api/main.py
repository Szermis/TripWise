# app/main.py

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core import chat
from core.config import settings
from core import database


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="TripWise API",
        description="AI-powered travel planner backend",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )

    # ---- CORS ----
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ---- Routers ----
    # app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
    # app.include_router(trips.router, prefix="/api/v1/trips", tags=["Trips"])
    app.include_router(chat.router, prefix=f"{settings.API_V1_STR}/chat", tags=["AI Assistant"])

    # ---- Startup & Shutdown Events ----
    @app.on_event("startup")
    async def startup_event():
        print("🚀 Starting TripWise backend...")
        # (Optional) test DB connection
        async with database.engine.begin() as conn:
            await conn.run_sync(database.Base.metadata.create_all)
        print("✅ Database ready")

    @app.on_event("shutdown")
    async def shutdown_event():
        print("🛑 Shutting down TripWise backend...")

    return app


# Instantiate the app
app = create_app()


# Run directly with: python -m app.main
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
