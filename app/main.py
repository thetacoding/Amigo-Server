# app/main.py
from fastapi import FastAPI
from app.api.v1 import assets, chat
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Amigo AI Server")

# 注册路由
app.include_router(assets.router, prefix="/api/v1/assets", tags=["Assets"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["AI Chat"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9082)