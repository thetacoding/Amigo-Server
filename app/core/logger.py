import sys
import logging
from loguru import logger
from pathlib import Path

# 定义日志路径
LOG_PATH = Path("logs")
LOG_PATH.mkdir(exist_ok=True)

def setup_logging():
    """
    配置 Loguru 全局日志
    """
    # 1. 移除默认的控制台输出（为了自定义格式）
    logger.remove()

    # 2. 添加控制台输出 (带颜色，格式清晰)
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:7}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True
    )

    # 3. 添加文件输出 (按天滚动，自动压缩旧日志)
    logger.add(
        LOG_PATH / "amigo_{time:YYYY-MM-DD}.log",
        rotation="00:00",     # 每天午夜轮转
        retention="30 days",   # 保留30天
        compression="zip",     # 旧日志压缩
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}",
        level="INFO",
        encoding="utf-8"
    )

    # 4. 拦截原生 logging (让 FastAPI/uvicorn 的日志也通过 loguru 打印)
    class InterceptHandler(logging.Handler):
        def emit(self, record):
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno
            frame, depth = logging.currentframe(), 2
            while frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1
            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)