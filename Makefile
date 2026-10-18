# 引入环境变量
include .env
export $(shell sed 's/=.*//' .env)

# 定义变量 (如果 .env 中没有，则使用默认值)
DOMAIN ?= champock.cloud
PORT ?= 9082
LOG_FILE ?= logs/amigo.log
VENV_PYTHON = venv/bin/python
VENV_UVICORN = venv/bin/uvicorn

.PHONY: start stop restart status log help install test eval-help eval-list eval-preview eval eval-all eval-clean-output

# 帮助信息
help:
	@echo "🛠️  Amigo AI Server 管理面板:"
	@echo "  make install  - 创建虚拟环境并安装依赖"
	@echo "  make start    - 启动 FastAPI 服务 (后台运行)"
	@echo "  make stop     - 停止服务 (杀死占用端口 $(PORT) 的进程)"
	@echo "  make status   - 查看服务运行状态"
	@echo "  make log      - 实时查看 API 日志"
	@echo "  make restart  - 重启服务"
	@echo "  make eval-help - 评测命令帮助"

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
		nohup $(VENV_UVICORN) app.main:app --host 0.0.0.0 --port $(PORT) > $(LOG_FILE) 2>&1 & \
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

test:
	export PYTHONPATH=. && pytest tests/ -v -s

eval-help:
	@echo "📊 评测命令:"
	@echo "  make eval-list"
	@echo "  make eval-preview TASK=intent_query [LIMIT=5] [HF_DATASET=SetFit/amazon_massive_intent_zh-CN] [HF_CONFIG=] [HF_SPLIT=test]"
	@echo "  make eval TASK=intent_query [LIMIT=50] [TOP_K=0] [HF_DATASET=SetFit/amazon_massive_intent_zh-CN] [HF_CONFIG=] [HF_SPLIT=test] [OUTPUT_DIR=outputs/eval]"
	@echo "  make eval-all [LIMIT=0] [TOP_K=0] [OUTPUT_DIR=outputs/eval]"
	@echo "  make eval-clean-output [OUTPUT_DIR=outputs/eval]"

eval-list:
	@export PYTHONPATH=$${PYTHONPATH}:. ; \
	$(VENV_PYTHON) -m app.eval_jobs.runner list

eval-preview:
	@export PYTHONPATH=$${PYTHONPATH}:. ; \
	$(VENV_PYTHON) -m app.eval_jobs.runner preview \
		--task "$(TASK)" \
		--dataset "$(HF_DATASET)" \
		--config "$(HF_CONFIG)" \
		--split "$(HF_SPLIT)" \
		--limit $${LIMIT:-5}

eval:
	@export PYTHONPATH=$${PYTHONPATH}:. ; \
	$(VENV_PYTHON) -m app.eval_jobs.runner run \
		--task "$(TASK)" \
		--dataset "$(HF_DATASET)" \
		--config "$(HF_CONFIG)" \
		--split "$(HF_SPLIT)" \
		--limit $${LIMIT:-0} \
		--top-k $${TOP_K:-0} \
		--output-dir "$${OUTPUT_DIR:-outputs/eval}"

eval-all:
	@export PYTHONPATH=$${PYTHONPATH}:. ; \
	$(VENV_PYTHON) -m app.eval_jobs.runner run-all \
		--limit $${LIMIT:-0} \
		--top-k $${TOP_K:-0} \
		--output-dir "$${OUTPUT_DIR:-outputs/eval}"

eval-clean-output:
	@export PYTHONPATH=$${PYTHONPATH}:. ; \
	$(VENV_PYTHON) -m app.eval_jobs.runner clean-output \
		--output-dir "$${OUTPUT_DIR:-outputs/eval}"