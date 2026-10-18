# Amigo Server

> 个人 AI App 的云侧后端服务（FastAPI + 多模型 Provider + 配置驱动）

Amigo Server 是一个基于 FastAPI 的云测后端服务，面向个人开发的 AI 应用场景，提供对话补全、预置资产下发、应用配置管理等能力。项目以轻量、可快速迭代为目标，支持多模型供应商接入（阿里云百炼、DeepSeek、腾讯混元），并具备统一日志、配置文件驱动和基础测试能力。

## 功能概览

- **AI 对话接口**：支持多轮消息输入，支持流式（SSE）与非流式返回。
- **多模型供应商适配**：通过工厂模式统一封装不同 LLM Provider。
- **资产与配置下发**：从 `data/presets.yaml` 提供角色、Agent、技能、会话及 App 配置。
- **静态资源托管**：通过 `/static` 对外提供头像、收款码等资源访问。
- **可观测日志**：使用 Loguru 统一接管 FastAPI/Uvicorn 日志并按天滚动。

## Why Amigo Server

- **配置驱动**：角色/会话/模型映射放在 `data/presets.yaml`，无需频繁改代码。
- **可扩展模型层**：通过 `LLMFactory + Provider` 解耦具体模型 SDK，便于新增厂商。
- **面向 App 场景**：接口结构贴近移动端/客户端实际交互，方便快速联调。
- **开箱即用**：内置 Makefile，支持一键安装、启动、测试与日志观察。

## 技术栈

- Python 3.11+
- FastAPI + Uvicorn
- Pydantic / pydantic-settings
- LangChain 生态（`langchain-core`、`langchain-openai`、`langchain-community`）
- DashScope（阿里云百炼）
- PyYAML
- Loguru

## 项目结构

```text
amigo-server/
├── app/
│   ├── api/v1_app/           # App 端接口（chat / assets）
│   ├── core/                 # 配置与日志
│   ├── schemas/              # 请求/响应模型
│   └── services/             # 业务服务（含 LLM 工厂与 Provider）
├── data/
│   └── presets.yaml          # App 配置、资产、会话预置
├── logs/                     # 运行日志目录
├── static/                   # 静态资源目录
├── tests/                    # 基础测试
├── .env.example              # 环境变量示例
├── Makefile                  # 启停与测试命令
└── requirements.txt
```

## 架构概览

```text
Client(App/Web)
    |
    v
FastAPI Router Layer
  - /api/v1_app/chat/*
  - /api/v1_app/assets/*
    |
    +--> Chat Service Path
    |      -> LLMFactory
    |      -> LLMProvider (aliyun/deepseek/tencent)
    |      -> LangChain ChatModel
    |
    +--> Config Service Path
           -> data/presets.yaml

Cross-cutting:
  - Loguru logging
  - Pydantic schema validation
  - Static files under /static
```

## 快速开始

### 1) 安装依赖

```bash
make install
```

### 2) 配置环境变量

复制 `.env.example` 为 `.env`，按你选择的模型供应商填写密钥。

常用变量示例：

```env
LLM_PROVIDER=aliyun
DASHSCOPE_API_KEY=your_dashscope_key
DEEPSEEK_API_KEY=your_deepseek_key
DEEPSEEK_BASE_URL=https://api.deepseek.com
TENCENT_HUNYUAN_API_KEY=your_tencent_key
```

### 3) 启动服务

```bash
make start
```

默认通过 `PORT`（Makefile 默认 `9082`）监听。  
本地调试文档地址通常为：`http://127.0.0.1:9082/docs`

### 4) 常用运维命令

```bash
make status   # 查看服务状态
make log      # 实时日志
make stop     # 停止服务
make restart  # 重启服务
make test     # 运行测试
```

## API 说明

### 基础信息

- 根路径：`/`
- OpenAPI 文档：`/docs`
- 全部响应统一格式：`{ code, msg, data }`

### 1) 对话补全

- `POST /api/v1_app/chat/completions`

请求体核心字段：

- `messages`: 多轮消息数组（`user` / `assistant` / `system`）
- `provider`: `aliyun` / `deepseek` / `tencent`（可选）
- `model`: 指定模型名（可选）
- `streaming`: 是否流式返回（默认 `true`）
- `reasoning`: 是否推理模式（默认 `false`）
- `options`: 推理参数，如 `temperature`

当 `streaming=true` 时，接口返回 `text/event-stream`，按 SSE 格式输出增量内容。

#### 请求示例（非流式）

```bash
curl -X POST "http://127.0.0.1:9082/api/v1_app/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "sessionInfo": {
      "session_id": "demo_session",
      "interaction_id": "round_1"
    },
    "userInfo": {
      "user_id": "u_1001"
    },
    "DeviceInfo": {
      "device_id": "device_abc"
    },
    "AppBaseInfo": {
      "package_name": "com.amigo.app"
    },
    "SystemSetting": {
      "gps": "0,0"
    },
    "messages": [
      {"role": "system", "content": "你是一个简洁的助手"},
      {"role": "user", "content": "你好，介绍一下你自己"}
    ],
    "provider": "tencent",
    "model": "hunyuan-standard",
    "streaming": false,
    "reasoning": false,
    "options": {
      "temperature": 0.7
    }
  }'
```

#### 响应示例（非流式）

```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "reply": "你好，我是你的 AI 助手..."
  }
}
```

#### 流式调用提示

- 设置 `streaming=true` 后，返回类型为 `text/event-stream`。
- 服务端按 SSE 格式逐块输出：`data: <chunk>\n\n`。
- 客户端建议使用 EventSource 或支持 SSE 的 HTTP 客户端解析。

### 2) 资产与配置接口

- `GET /api/v1_app/assets/all`：获取全部预置数据
- `GET /api/v1_app/assets/config`：获取 App 全局配置
- `GET /api/v1_app/assets/presets?type=<type>`：按类型获取资产（如 `characters`/`agents`/`skills`）
- `GET /api/v1_app/assets/chatSessions`：获取预置会话列表

## 配置数据说明

`data/presets.yaml` 当前用于承载：

- `app_config`：支持的 Provider、默认标题、模型映射、支付二维码地址等
- `assets`：角色、Agent、技能等预设入口
- `chatSessions`：预置会话模板

建议将此文件作为“产品运营配置层”，通过发布流程变更，而不是在代码中硬编码。

## 日志与排障

- 日志目录：`logs/`
- 日志文件：`amigo_YYYY-MM-DD.log`（按天切分，保留 30 天并压缩历史）
- 控制台与文件日志由 Loguru 统一接管，便于排查请求链路问题

## 测试建议

项目提供了基础接口与 LLM 连通性测试：

```bash
make test
```

注意：涉及真实模型调用的测试依赖有效密钥与网络环境，建议在 CI 中将外部模型调用用 mock/桩替代，避免不稳定因素。

## 本地开发建议

- 新增 Provider 时，优先在 `app/services/ai/llm/providers.py` 增加静态方法，再在 `factory.py` 注册策略映射。
- 若要扩展 App 配置项，优先更新 `data/presets.yaml` 与 `ConfigService`，保持前后端协议稳定。
- 建议逐步补充测试分层：
  - 单元测试：配置解析、参数校验、工厂策略选择
  - 接口测试：chat/assets 路由行为
  - 集成测试：真实模型连通性（可单独标记）

## 部署建议

- 生产环境建议通过 Nginx/Caddy 反向代理 Uvicorn，并启用 HTTPS。
- 使用环境变量管理密钥，不要将真实密钥提交到仓库。
- 建议补充进程守护（systemd / supervisor / 容器编排）与健康检查。
- 若访问量提升，建议增加限流、鉴权和请求追踪（trace id）机制。

## Roadmap

- [ ] 增加鉴权体系（API Key/JWT）
- [ ] 增加限流与熔断策略
- [ ] 增加请求 trace id 与链路追踪
- [ ] 完善 CI（lint + test + package）
- [ ] 对外发布 Docker 部署方案
- [ ] 增加管理端接口（`/api/v1_web`）

## 贡献指南

欢迎提交 Issue 和 PR。建议流程：

1. Fork 并创建功能分支（如 `feature/add-gemini-provider`）
2. 保持变更最小闭环并补充必要测试
3. 确保本地通过 `make test`
4. 提交 PR，描述变更动机、实现方式和验证结果

建议提交信息风格：

- `feat: ...` 新功能
- `fix: ...` 缺陷修复
- `refactor: ...` 重构
- `test: ...` 测试补充
- `docs: ...` 文档更新

## FAQ

**Q: 为什么 `tests/test_llm.py` 可能在 CI 不稳定？**  
A: 该测试依赖真实模型网络与密钥，建议将其标记为 integration，CI 默认跑 mock 测试。

**Q: 如何新增一个模型供应商？**  
A: 在 `providers.py` 增加实例化方法，在 `factory.py` 注册映射，并更新 `.env.example` 与 README。

**Q: 配置数据应该放哪里？**  
A: 当前推荐维护在 `data/presets.yaml`，适合单体服务快速迭代；后续可迁移数据库或配置中心。

## License

当前仓库尚未声明许可证。建议补充 `LICENSE`（如 MIT）后再对外公开分发。

## 版本信息

当前服务版本标识可通过根接口返回查看：`v1.0.0`。
