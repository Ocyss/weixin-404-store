from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import asynccontextmanager
from fastapi.responses import FileResponse
from loguru import logger

import weixin
import weixin.mp
import weixin.work
from env import settings
from model import init_mongodb


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb = await init_mongodb(
        user=settings.mongo.user,
        password=settings.mongo.password,
        host=settings.mongo.host,
        port=settings.mongo.port,
        db_name=settings.mongo.db_name,
    )

    yield

    await mongodb.client.aclose()


app = FastAPI(
    title="WeChat Server",
    description="FastAPI版微信服务器",
    version="1.0.0",
    lifespan=lifespan,
)


def setup_static_routes():
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    ALLOWED_STATIC_EXTENSIONS = {".txt", ".html", ".xml", ".json"}

    if not static_dir.exists():
        return

    for file_path in static_dir.iterdir():
        if (
            file_path.is_file()
            and file_path.suffix.lower() in ALLOWED_STATIC_EXTENSIONS
        ):
            filename = file_path.name

            @app.get(f"/{filename}", include_in_schema=False, tags=["static"])
            async def serve_static_file(file_name: str = filename):
                """提供静态文件访问"""
                file_full_path = static_dir / file_name
                if not file_full_path.exists():
                    raise HTTPException(status_code=404, detail="File not found")

                logger.info(f"提供静态文件: {file_name}")
                return FileResponse(
                    file_full_path,
                    media_type="text/plain"
                    if file_full_path.suffix == ".txt"
                    else None,
                )


setup_static_routes()

app.include_router(weixin.mp.router)
app.include_router(weixin.work.router)


@app.get("/health")
async def health_check():
    """健康检查接口"""

    return {
        "status": "ok",
        "message": "WeChat server is running",
        "current_time": datetime.now().isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        # log_level=logging.root.level,
    )
