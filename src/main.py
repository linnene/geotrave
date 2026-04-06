from contextlib import asynccontextmanager
import fastapi
import uvicorn
from api.routes import router as api_router
from utils.logger import logger

@asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    # Startup logic
    logger.info("[GeoTrave] FastAPI Server loading...")
    yield
    # Shutdown logic (if any)
    logger.info("[GeoTrave] FastAPI Server shutting down...")

# 注册接口
app = fastapi.FastAPI(title="GeoTrave API", lifespan=lifespan)
app.include_router(api_router)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)