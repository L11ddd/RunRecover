# RunRecover 产品使用手册

本手册基于当前仓库代码编写，适用于在本地演示 RunRecover MVP。RunRecover 是一个面向日常跑者的跑后恢复分析工具：用户输入本次跑步数据、主观用力 RPE、睡眠、疲劳、酸痛和明日计划后，系统返回 0-100 的恢复压力分、主要原因、饮食/补水/睡眠/放松/明日安排建议，以及 24 小时恢复时间轴。

## 1. 产品范围

### 1.1 当前能力

- 前端：React + Vite 单页应用，提供表单输入、三个一键演示案例、恢复结果展示。
- 后端：FastAPI 服务，提供健康检查和恢复分析接口。
- 评分：使用规则引擎计算恢复压力，不依赖外部 LLM。
- 建议：使用模板生成饮食、补水、睡眠、放松、明日安排和时间轴。
- 数据：每次分析会保存到本地 SQLite 数据库。

### 1.2 当前不包含

- 用户账号、登录、云端同步。
- 运动设备同步、GPX/CSV 上传。
- 历史趋势图和长期训练计划。
- 真实 LLM API 调用。当前 `RUNRECOVER_LLM_PROVIDER` 默认是 `template`。
- 医疗诊断。所有建议仅作为一般运动恢复参考。

## 2. 项目结构

```text
RunRecover/
  README.md
  docs/
    api.md
    demo-cases.md
    mvp-summary.md
    user-manual.md
  apps/
    api/
      app/
        main.py
        schemas.py
        config.py
        services/
        repositories/
      tests/
      requirements.txt
      pyproject.toml
    web/
      src/
        App.tsx
        lib/
          api.ts
          demoCases.ts
          types.ts
      package.json
      vite.config.ts
```

关键目录说明：

| 路径 | 作用 |
| --- | --- |
| `apps/api` | 后端 API、评分规则、建议模板、SQLite 持久化、后端测试 |
| `apps/web` | 前端页面、表单、演示案例、API 调用封装 |
| `docs` | 产品说明、API 文档、演示案例说明和本手册 |
| `.env.example` | 环境变量示例，说明后端数据库地址和前端 API 地址 |

## 3. 本地环境要求

建议环境：

- Python 3.9 或更高版本。
- Node.js `^20.19.0`、`>=22.12.0`，或当前兼容的新版本。
- npm。
- macOS、Linux 或 Windows 均可；本手册命令按 macOS/Linux shell 写法展示。

检查环境：

```bash
python3 --version
node --version
npm --version
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `python3 --version` | 查看本机 Python 版本，确认能创建后端虚拟环境。 |
| `node --version` | 查看 Node.js 版本，确认满足 Vite 依赖要求。 |
| `npm --version` | 查看 npm 版本，确认能安装和运行前端依赖。 |

## 4. 首次安装

以下命令从仓库根目录 `/Users/liuyidi/Project/RunRecover` 开始执行。

### 4.1 安装后端依赖

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `cd /Users/liuyidi/Project/RunRecover/apps/api` | 进入后端目录。后端默认 SQLite 路径是相对当前目录的 `./data/runrecover.db`，因此建议从 `apps/api` 启动。 |
| `python3 -m venv .venv` | 在 `apps/api` 下创建 Python 虚拟环境，避免依赖安装到系统 Python。 |
| `./.venv/bin/pip install -r requirements.txt` | 使用虚拟环境里的 pip 安装 FastAPI、Uvicorn、Pydantic、pytest、httpx 等后端依赖。 |

如果已经在仓库根目录创建了 `.venv`，也可以从 `apps/api` 使用 `../../.venv/bin/uvicorn` 和 `../../.venv/bin/pytest`。为了演示流程清晰，推荐后端目录内单独使用 `apps/api/.venv`。

### 4.2 安装前端依赖

```bash
cd /Users/liuyidi/Project/RunRecover/apps/web
npm install
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `cd /Users/liuyidi/Project/RunRecover/apps/web` | 进入前端目录。 |
| `npm install` | 按 `package-lock.json` 安装 React、Vite、TypeScript、lucide-react 等前端依赖。 |

## 5. 本地演示启动

本地完整演示需要同时启动后端和前端。建议打开两个终端窗口。

### 5.1 终端 A：启动后端 API

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
./.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

命令解释：

| 命令或参数 | 解释 |
| --- | --- |
| `cd /Users/liuyidi/Project/RunRecover/apps/api` | 进入后端目录，确保默认数据库会创建在 `apps/api/data/runrecover.db`。 |
| `./.venv/bin/uvicorn` | 使用后端虚拟环境里的 Uvicorn 启动 ASGI 服务。 |
| `app.main:app` | 指向 FastAPI 应用对象：`app/main.py` 文件中的 `app` 变量。 |
| `--reload` | 开发模式热重载；代码变更后服务自动重启。 |
| `--host 127.0.0.1` | 只监听本机地址，适合本地演示。 |
| `--port 8000` | 后端 API 端口。前端默认请求 `http://127.0.0.1:8000`。 |

启动成功后，后端会持续运行。不要关闭这个终端。

### 5.2 检查后端健康状态

另开一个终端执行：

```bash
curl http://127.0.0.1:8000/api/health
```

预期返回：

```json
{
  "status": "ok",
  "service": "runrecover-api"
}
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `curl http://127.0.0.1:8000/api/health` | 向后端健康检查接口发送 GET 请求，用于确认 API 已启动并能响应。 |

### 5.3 终端 B：启动前端页面

```bash
cd /Users/liuyidi/Project/RunRecover/apps/web
npm run dev -- --host 127.0.0.1 --port 5173
```

命令解释：

| 命令或参数 | 解释 |
| --- | --- |
| `cd /Users/liuyidi/Project/RunRecover/apps/web` | 进入前端目录。 |
| `npm run dev` | 执行 `package.json` 中的 `dev` 脚本，启动 Vite 开发服务器。 |
| `--` | npm 参数分隔符，表示后面的参数传给 Vite，而不是传给 npm。 |
| `--host 127.0.0.1` | 让前端服务监听本机地址。 |
| `--port 5173` | 指定前端端口。后端 CORS 已允许 `http://127.0.0.1:5173`。 |

启动成功后，在浏览器访问：

```text
http://127.0.0.1:5173
```

## 6. 前端操作指南

### 6.1 页面区域

页面分为两栏：

| 区域 | 作用 |
| --- | --- |
| 左侧 `本次跑步` | 输入跑步、身体状态、饮食场景、明日计划和异常信号。 |
| 右侧 `恢复结果` | 展示恢复压力分、等级、原因、分项贡献、建议卡片、安全提示和 24 小时时间轴。 |

### 6.2 一键演示案例

页面顶部有三个演示按钮。点击后会自动填入表单并立即分析。

| 案例 | 输入特点 | 预期结果 |
| --- | --- | --- |
| `轻松恢复` | 5 km 轻松跑，RPE 3，睡眠 8 小时，疲劳 2，酸痛 2 | 约 19 分，等级为 `轻度恢复`。 |
| `高强度夜跑` | 8 km 节奏跑，夜跑，RPE 8，睡眠 5.8 小时，明日强度课 | 约 75 分，等级为 `重点恢复`，原因包含 RPE、睡眠、明日计划。 |
| `长距离高 RPE` | 16 km 长距离跑，RPE 9，疲劳 8，酸痛 7，明日长距离 | 约 84 分，等级为 `高负荷提醒`。 |

推荐 5 分钟演示流程：

1. 打开 `http://127.0.0.1:5173`。
2. 点击 `轻松恢复`，说明低负荷场景下系统给出轻度恢复建议。
3. 点击 `高强度夜跑`，说明 RPE、睡眠不足和明日强度冲突如何抬高恢复压力。
4. 点击 `长距离高 RPE`，说明高负荷场景下系统会建议更保守的明日安排。
5. 手动勾选 `关节疼痛` 或 `疼痛影响走路`，点击 `开始分析`，展示安全提示如何出现。

### 6.3 手动输入字段

| 字段 | 可选值或范围 | 说明 |
| --- | --- | --- |
| `距离 km` | `0.5` 到 `60` | 本次跑步距离。影响基础跑量负荷。 |
| `时长 min` | `5` 到 `360` | 本次跑步用时。前端用它计算配速展示。 |
| `跑步类型` | 轻松跑、节奏跑、间歇跑、长距离跑、比赛 | 不同类型对应不同训练负荷。 |
| `跑步时间` | 早晨、中午、傍晚、夜跑 | 夜跑会增加睡前恢复关注，RPE 高时影响更明显。 |
| `RPE 主观用力` | `1` 到 `10` | 用户对本次训练吃力程度的主观评分。 |
| `睡眠 h` | `0` 到 `14` | 昨晚睡眠时长。低睡眠会增加恢复压力。 |
| `疲劳` | `1` 到 `10` | 当前疲劳程度。 |
| `酸痛` | `1` 到 `10` | 腿部或身体酸痛程度。 |
| `平均心率` | 可为空，或 `40` 到 `230` | 可选字段；为空时结果不会提到心率原因。 |
| `最大心率` | 可为空，或 `40` 到 `230` | 可选字段；用于辅助判断训练强度。 |
| `饮食场景` | 正常饮食、减脂、素食、食堂、外卖、夜间轻食 | 影响饮食建议模板。 |
| `明日计划` | 未确定、休息、轻松跑、强度课、长距离 | 高恢复压力下，强度课或长距离会触发冲突提示。 |
| `异常信号` | 胸闷/胸痛、头晕、呼吸困难、关节疼痛、疼痛影响走路 | 触发安全提示和更保守的明日建议。 |

### 6.4 结果解读

| 结果模块 | 说明 |
| --- | --- |
| 恢复压力分 | 0-100 分，越高表示越需要保守恢复。 |
| 等级 | `轻度恢复`、`中度恢复`、`重点恢复`、`高负荷提醒`。 |
| 主要原因 | 按影响分排序，最多展示 5 个原因。 |
| 分项贡献 | 展示跑量、类型、RPE、睡眠、疲劳、酸痛、心率、时间、明日冲突等贡献。 |
| 建议卡片 | 包含饮食、补水、睡眠、放松、明日安排。 |
| 24 小时时间轴 | 给出跑后 0-15 分钟、15-45 分钟、1-2 小时、睡前、明早、明日训练等阶段动作。 |
| 安全提示 | 当异常信号或高风险组合出现时展示。 |

分数等级规则：

| 分数 | 等级 | 说明 |
| --- | --- | --- |
| `0-30` | `轻度恢复` | 负荷较低，保持正常恢复即可。 |
| `31-60` | `中度恢复` | 有一定恢复压力，避免连续高强度。 |
| `61-80` | `重点恢复` | 恢复压力较高，建议主动调整饮食、睡眠和明日训练。 |
| `81-100` | `高负荷提醒` | 高负荷或风险组合，建议明日休息或非常轻松活动。 |

## 7. API 使用示例

本地 API 基础地址：

```text
http://127.0.0.1:8000
```

### 7.1 健康检查

```bash
curl http://127.0.0.1:8000/api/health
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `curl` | 命令行 HTTP 客户端。 |
| `http://127.0.0.1:8000/api/health` | 后端健康检查接口地址。 |

### 7.2 提交一次恢复分析

```bash
curl -X POST http://127.0.0.1:8000/api/recovery/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "distance_km": 8,
    "duration_min": 48,
    "run_type": "tempo",
    "run_time_period": "night",
    "rpe": 8,
    "sleep_hours": 5.8,
    "fatigue_level": 7,
    "soreness_level": 5,
    "avg_hr": 156,
    "max_hr": null,
    "diet_preference": "canteen",
    "tomorrow_plan": "intensity",
    "symptoms": []
  }'
```

命令解释：

| 命令或参数 | 解释 |
| --- | --- |
| `curl -X POST` | 使用 POST 方法提交数据。 |
| `http://127.0.0.1:8000/api/recovery/analyze` | 恢复分析接口地址。 |
| `-H "Content-Type: application/json"` | 告诉后端请求体是 JSON。 |
| `-d '...'` | 提交 JSON 请求体。里面的字段必须符合后端校验范围。 |
| `distance_km` | 跑步距离，单位 km。 |
| `duration_min` | 跑步时长，单位分钟。 |
| `run_type` | 跑步类型，示例 `tempo` 表示节奏跑。 |
| `run_time_period` | 跑步时间段，示例 `night` 表示夜跑。 |
| `rpe` | 主观用力评分。 |
| `sleep_hours` | 昨晚睡眠小时数。 |
| `fatigue_level` | 疲劳程度。 |
| `soreness_level` | 酸痛程度。 |
| `avg_hr` / `max_hr` | 平均心率和最大心率，可为 `null`。 |
| `diet_preference` | 饮食场景。 |
| `tomorrow_plan` | 明日计划。 |
| `symptoms` | 异常信号数组，无异常时传空数组。 |

关键返回示例：

```json
{
  "score": 75,
  "level": "重点恢复",
  "component_scores": {
    "base_load": 10,
    "run_type": 12,
    "rpe": 15,
    "heart_rate": 4,
    "sleep": 10,
    "fatigue": 8,
    "soreness": 5,
    "time": 6,
    "tomorrow_conflict": 5
  },
  "safety_flags": []
}
```

返回字段说明：

| 字段 | 说明 |
| --- | --- |
| `recovery_id` | 本次分析结果在 SQLite 中的记录 ID。 |
| `score` | 0-100 的恢复压力分。 |
| `level` | 分数对应等级。 |
| `component_scores` | 每个评分因素的贡献分。 |
| `reasons` | 主要原因列表，包含因素、影响分和解释文案。 |
| `advice` | 建议内容，包含摘要和五类建议。 |
| `timeline` | 24 小时恢复时间轴。 |
| `safety_flags` | 安全提示数组。 |

### 7.3 安全提示示例

```bash
curl -X POST http://127.0.0.1:8000/api/recovery/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "distance_km": 6,
    "duration_min": 38,
    "run_type": "easy",
    "run_time_period": "evening",
    "rpe": 7,
    "sleep_hours": 6.5,
    "fatigue_level": 6,
    "soreness_level": 6,
    "avg_hr": null,
    "max_hr": null,
    "diet_preference": "normal",
    "tomorrow_plan": "easy",
    "symptoms": ["joint_pain", "pain_affects_walking"]
  }'
```

预期效果：

- `safety_flags` 不为空。
- 建议会更保守。
- `advice.safety_note` 会提示本产品不构成医疗诊断或治疗建议。

## 8. 环境变量

后端配置位于 `apps/api/app/config.py`，前端 API 地址位于 `apps/web/src/lib/api.ts`。

| 环境变量 | 默认值 | 作用 |
| --- | --- | --- |
| `RUNRECOVER_DATABASE_URL` | `sqlite:///./data/runrecover.db` | 后端 SQLite 数据库地址。只支持 `sqlite:///`。 |
| `RUNRECOVER_LLM_PROVIDER` | `template` | 推荐生成服务提供方。当前 MVP 使用模板。 |
| `VITE_API_BASE_URL` | `http://127.0.0.1:8000` | 前端请求后端 API 的基础地址。 |

### 8.1 临时指定后端数据库

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
RUNRECOVER_DATABASE_URL=sqlite:///./data/demo.db ./.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

命令解释：

| 命令或参数 | 解释 |
| --- | --- |
| `RUNRECOVER_DATABASE_URL=sqlite:///./data/demo.db` | 只对本次命令生效，把数据库改为 `apps/api/data/demo.db`。 |
| `./.venv/bin/uvicorn app.main:app ...` | 使用同样方式启动后端。 |

### 8.2 临时指定前端 API 地址

```bash
cd /Users/liuyidi/Project/RunRecover/apps/web
VITE_API_BASE_URL=http://127.0.0.1:8000 npm run dev -- --host 127.0.0.1 --port 5173
```

命令解释：

| 命令或参数 | 解释 |
| --- | --- |
| `VITE_API_BASE_URL=http://127.0.0.1:8000` | 只对本次前端启动命令生效，指定前端请求的 API 地址。 |
| `npm run dev -- --host 127.0.0.1 --port 5173` | 启动 Vite 开发服务器。 |

如果需要长期配置前端 API 地址，可以在 `apps/web/.env.local` 中写入：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 9. 数据保存

只要调用 `POST /api/recovery/analyze`，后端就会写入 SQLite：

- `run_records`：保存用户输入。
- `recovery_results`：保存分数、等级、原因和分项贡献。
- `recommendations`：保存建议、时间轴和安全提示。

如果按本手册从 `apps/api` 启动后端，默认数据库文件是：

```text
/Users/liuyidi/Project/RunRecover/apps/api/data/runrecover.db
```

`apps/api/data/` 已被 `.gitignore` 忽略，不会提交到 Git。

## 10. 测试和构建

### 10.1 运行后端测试

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
./.venv/bin/pytest
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `cd /Users/liuyidi/Project/RunRecover/apps/api` | 进入后端目录，使 `pyproject.toml` 中的 pytest 配置生效。 |
| `./.venv/bin/pytest` | 运行 `apps/api/tests` 下的后端单元测试和 API 测试。 |

### 10.2 构建前端

```bash
cd /Users/liuyidi/Project/RunRecover/apps/web
npm run build
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `cd /Users/liuyidi/Project/RunRecover/apps/web` | 进入前端目录。 |
| `npm run build` | 执行 `tsc -b && vite build`，先进行 TypeScript 构建检查，再生成生产构建产物。 |

### 10.3 预览前端生产构建

```bash
cd /Users/liuyidi/Project/RunRecover/apps/web
npm run preview -- --host 127.0.0.1 --port 4173
```

命令解释：

| 命令或参数 | 解释 |
| --- | --- |
| `npm run preview` | 用 Vite 预览 `npm run build` 生成的生产构建。 |
| `--host 127.0.0.1` | 只监听本机地址。 |
| `--port 4173` | 指定预览服务端口。 |

## 11. 常见问题

### 11.1 前端显示后端请求失败

检查后端是否正在运行：

```bash
curl http://127.0.0.1:8000/api/health
```

如果没有返回 `{"status":"ok","service":"runrecover-api"}`，先回到终端 A 启动后端。

### 11.2 端口被占用

如果 `8000` 被占用，可以换后端端口：

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
./.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8001
```

同时启动前端时指定新的 API 地址：

```bash
cd /Users/liuyidi/Project/RunRecover/apps/web
VITE_API_BASE_URL=http://127.0.0.1:8001 npm run dev -- --host 127.0.0.1 --port 5173
```

说明：后端 CORS 当前只允许 `http://127.0.0.1:5173` 和 `http://localhost:5173` 访问，因此前端建议仍使用 `5173` 端口。

### 11.3 API 返回 422

422 表示请求 JSON 没有通过校验。常见原因：

- `rpe` 不在 `1-10`。
- `distance_km` 小于 `0.5` 或大于 `60`。
- `duration_min` 小于 `5` 或大于 `360`。
- `avg_hr` 或 `max_hr` 不为空时不在 `40-230`。
- 枚举值拼写错误，例如 `run_type` 只能是 `easy`、`tempo`、`interval`、`long`、`race`。

### 11.4 没有心率时结果是否可靠

可以不填心率。后端规则是：`avg_hr` 和 `max_hr` 都为空时，心率贡献分为 `0`，原因列表也不会输出心率相关解释。

### 11.5 如何重置本地演示数据

停止后端后删除 SQLite 数据库文件即可：

```bash
rm -f /Users/liuyidi/Project/RunRecover/apps/api/data/runrecover.db
```

命令解释：

| 命令 | 解释 |
| --- | --- |
| `rm -f /Users/liuyidi/Project/RunRecover/apps/api/data/runrecover.db` | 删除本地 SQLite 数据库。下次启动后端并提交分析时会自动重新创建。 |

删除数据库会清空本地演示记录，但不会影响代码。

## 12. 演示讲解词示例

可以按以下话术进行产品演示：

1. “RunRecover 解决的是跑后 24 小时该如何恢复的问题，不替代运动手表，也不做医疗诊断。”
2. “左侧输入本次训练和身体状态，RPE 是主观用力评分，是恢复压力的重要因素之一。”
3. “先看轻松恢复案例，系统给出低分，说明正常补水、吃饭和睡眠即可。”
4. “再看高强度夜跑案例，分数上升到重点恢复，主要原因包括 RPE 高、睡眠不足和明日强度冲突。”
5. “长距离高 RPE 案例进入高负荷提醒，系统建议明日休息或非常轻松活动。”
6. “如果勾选关节疼痛或疼痛影响走路，系统会出现安全提示，并建议优先保守处理。”

## 13. 一次完整本地演示命令清单

首次安装：

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt

cd /Users/liuyidi/Project/RunRecover/apps/web
npm install
```

每次演示启动：

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
./.venv/bin/uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

另开终端：

```bash
cd /Users/liuyidi/Project/RunRecover/apps/web
npm run dev -- --host 127.0.0.1 --port 5173
```

浏览器访问：

```text
http://127.0.0.1:5173
```

演示前自检：

```bash
curl http://127.0.0.1:8000/api/health
```

验证质量：

```bash
cd /Users/liuyidi/Project/RunRecover/apps/api
./.venv/bin/pytest

cd /Users/liuyidi/Project/RunRecover/apps/web
npm run build
```
