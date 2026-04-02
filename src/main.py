import fastapi
import uvicorn
from api.routes import router as api_router

# 注册接口
app = fastapi.FastAPI(title="GeoTrave API")
app.include_router(api_router)
 
if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)