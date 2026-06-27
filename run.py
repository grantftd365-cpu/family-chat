#!/usr/bin/env python3
"""FamilyChat 启动入口"""
import os
import uvicorn

if __name__ == "__main__":
    # 生产环境自动关闭 reload
    is_production = os.getenv("ENV", "").lower() in ("production", "prod") or not os.getenv("DEBUG")

    uvicorn.run(
        "backend.app.main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=not is_production,
        log_level="info",
        workers=1,  # SQLite 单写者，只能单 worker
        timeout_keep_alive=65,
        limit_concurrency=200,
    )
