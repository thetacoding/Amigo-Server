# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.core.logger import setup_logging
from app.api.v1_app import assets, chat, eval as eval_api, feedback, web_search
from dotenv import load_dotenv

load_dotenv()

# 整个项目启动前，先初始化日志引擎
setup_logging()

app = FastAPI(title="Amigo AI Server")

# 1. 静态文件挂载 (用于访问收款码、头像等)
# 这样你可以通过 http://server_ip:8000/static/pay.png 访问
app.mount("/static", StaticFiles(directory="static"), name="static")

# 2. 挂载 App 端对话接口
# 访问路径将变为: /api/v1_app/chat/completions
app.include_router(
    chat.router, 
    prefix="/api/v1_app/chat", 
    tags=["App-对话"]
)

# 3. 挂载 App 端资产/配置接口
# 访问路径将变为: /api/v1_app/assets/config 和 /api/v1_app/assets/presets
app.include_router(
    assets.router, 
    prefix="/api/v1_app/assets", 
    tags=["App-预置数据"]
)

# 4. 挂载 App 端用户反馈接口
# 访问路径: /api/v1_app/feedback/submit（点踩选项见 /api/v1_app/assets/all 或 /config 中 data.feedback）
app.include_router(
    feedback.router,
    prefix="/api/v1_app/feedback",
    tags=["App-反馈"],
)

# 5. 挂载 App 端 Web Search 接口
# 访问路径将变为: /api/v1_app/web_search/tavily/readable
app.include_router(
    web_search.router,
    prefix="/api/v1_app/web_search",
    tags=["App-搜索"]
)

# 6. 挂载 App 端统一评测接口
# 访问路径将变为: /api/v1_app/eval/run
app.include_router(
    eval_api.router,
    prefix="/api/v1_app/eval",
    tags=["App-评测"]
)

# 7. 预留 Web 端接口挂载点
# app.include_router(admin.router, prefix="/api/v1_web", tags=["Web-管理后台"])

@app.get("/")
async def root():
    return {"message": "Welcome to Amigo API Server", "version": "v1.0.0"}