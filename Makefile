# 引入环境变量
include .env
export $(shell sed 's/=.*//' .env)

# 定义变量 (如果 .env 中没有，则使用默认值)
DOMAIN ?= champock.cloud
PORT ?= 9082
LOG_FILE ?= logs/amigo.log
VENV_PYTHON = venv/bin/python
VENV_UVICORN = venv/bin/uvicorn

.PHONY: start stop restart status log help install

# 帮助信息
help:
	@echo "🛠️  Amigo AI Server 管理面板:"
	@echo "  make install  - 创建虚拟环境并安装依赖"
	@echo "  make start    - 启动 FastAPI 服务 (后台运行)"
	@echo "  make stop     - 停止服务 (杀死占用端口 $(PORT) 的进程)"
	@echo "  make status   - 查看服务运行状态"
	@echo "  make log      - 实时查看 API 日志"
	@echo "  make restart  - 重启服务"

# 安装依赖
install:
	@python3 -m venv venv
	@venv/bin/pip install -r requirements.txt
	@mkdir -p logs
	@echo "✅ 环境安装完成。"

# 启动服务 (使用 uvicorn 运行 FastAPI)
start:
	@mkdir -p logs
	@CUR_PID=$$(lsof -t -i:$(PORT)); \
	if [ -n "$$CUR_PID" ]; then \
		echo "⚠️  端口 $(PORT) 已被占用 (PID: $$CUR_PID)，无需重复启动。"; \
	else \
		echo "🚀 正在启动 Amigo 服务..."; \
		export PYTHONPATH=$${PYTHONPATH}:. ; \
		nohup venv/bin/python app/main.py > $(LOG_FILE) 2>&1 & \
		echo "✅ 启动指令已发出。"; \
		echo "💡 执行 'make status' 确认。"; \
	fi

# 停止服务
stop:
	@CUR_PID=$$(lsof -t -i:$(PORT)); \
	if [ -n "$$CUR_PID" ]; then \
		echo "🛑 发现运行中的服务 (PID: $$CUR_PID)，正在停止..."; \
		kill $$CUR_PID; \
		sleep 1; \
		echo "✅ 服务已停止。"; \
	else \
		echo "❓ 端口 $(PORT) 未被占用。"; \
	fi

# 查看状态
status:
	@CUR_PID=$$(lsof -t -i:$(PORT)); \
	if [ -n "$$CUR_PID" ]; then \
		echo "🟢 服务状态: 运行中"; \
		echo "   - 进程 ID: $$CUR_PID"; \
		echo "   - 监听端口: $(PORT)"; \
		echo "   - 访问地址: https://$(DOMAIN)"; \
		echo "   - 交互文档: https://$(DOMAIN)/docs"; \
	else \
		echo "🔴 服务状态: 已停止"; \
	fi

# 重启
restart: stop start

# 日志
log:
	@tail -f $(LOG_FILE)