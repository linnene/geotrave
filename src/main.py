import fastapi
import uvicorn
from api.routes import router as api_router
from utils.logger import logger

# 注册接口
app = fastapi.FastAPI(title="GeoTrave API")
app.include_router(api_router)
 
@app.on_event("startup")
async def startup_event():
    logger.info("[GeoTrave] FastAPI Server loading...")

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)