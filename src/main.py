import argparse
from contextlib import asynccontextmanager
import fastapi
import uvicorn
from api.routes import router as api_router
from utils.logger import logger, set_global_log_level

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
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="GeoTrave API Server")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode (set log level to DEBUG)")
    parser.add_argument("--host", default="localhost", help="Host to bind the server to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind the server to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    
    args = parser.parse_args()

    # 如果通过命令行参数指定了 --debug，则动态调整日志级别
    if args.debug:
        set_global_log_level("DEBUG")
        logger.info("[GeoTrave] Debug mode is enabled via command line.")

    # 启动 uvicorn
    if args.reload:
        uvicorn.run("main:app", host=args.host, port=args.port, reload=True, factory=False)
    else:
        uvicorn.run(app, host=args.host, port=args.port)
