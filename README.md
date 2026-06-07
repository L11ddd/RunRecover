# RunRecover MVP

RunRecover is an AI-assisted post-run recovery MVP for everyday runners. The first version focuses on one complete demo loop:

1. User enters run data, RPE, sleep, fatigue, soreness, and tomorrow's plan.
2. The API computes a transparent recovery pressure score using distance, duration, run type modifiers, recent 48-hour load, and tomorrow-plan conflict.
3. The result explains the main factors, including RPE, duration, recent load, and safety conflicts when they materially affect the score.
4. Template-backed or LLM-backed advice returns diet, hydration, sleep, relaxation, tomorrow guidance, and a 24-hour timeline, with content-level safety validation.

The repository uses a React + FastAPI + SQLite split:

- `apps/api`: FastAPI backend, scoring rules, safety guard, template recommendations, SQLite persistence, pytest tests.
- `apps/web`: Vite React TypeScript frontend with demo cases and a single-page MVP flow.
- `docs`: MVP, API, demo-case notes, and the full product user manual.

## Quick Start

### One-command local demo

Install backend and frontend dependencies once:

```bash
cd apps/api
python3 -m venv .venv
./.venv/bin/python3 -m pip install -r requirements.txt

cd ../web
npm install
```

Then start both services from the repository root:

```bash
npm run dev
```

This runs:

- FastAPI API: `http://127.0.0.1:8000`
- Vite Web: `http://127.0.0.1:5173`

You can also run the script directly:

```bash
./scripts/dev.sh
```

The script respects these optional environment variables:

- `RUNRECOVER_API_HOST`, `RUNRECOVER_API_PORT`
- `RUNRECOVER_WEB_HOST`, `RUNRECOVER_WEB_PORT`
- `VITE_API_BASE_URL`

### 手机局域网体验 RunRecover

如果不想打包 App、也不想部署线上环境，可以让手机和 Mac 连接同一个 Wi-Fi，
然后通过 Mac 的局域网 IP 在手机浏览器访问 RunRecover。

从仓库根目录运行：

```bash
chmod +x scripts/dev-mobile.sh
npm run dev:mobile
```

脚本会自动尝试读取 Mac 当前局域网 IP：

1. `ipconfig getifaddr en0`
2. 如果为空，再尝试 `ipconfig getifaddr en1`

启动后终端会输出两类地址：

- Mac 本机访问地址：`http://127.0.0.1:5173`
- 手机访问地址：`http://<LAN_IP>:5173`

在手机浏览器打开终端里显示的手机访问地址，例如：

```text
http://192.168.1.23:5173
```

注意：手机不能访问 `127.0.0.1:5173`，因为 `127.0.0.1` 在手机上代表手机自己，
不是你的 Mac。

`npm run dev:mobile` 会自动设置：

- `RUNRECOVER_API_HOST=0.0.0.0`
- `RUNRECOVER_API_PORT=8000`
- `RUNRECOVER_WEB_HOST=0.0.0.0`
- `RUNRECOVER_WEB_PORT=5173`
- `VITE_API_BASE_URL=http://<LAN_IP>:8000`
- `RUNRECOVER_CORS_ORIGINS=http://<LAN_IP>:5173,http://127.0.0.1:5173,http://localhost:5173`

常见问题：

- 手机打不开页面：确认手机和 Mac 在同一个 Wi-Fi；检查 Mac 防火墙是否阻止入站连接；
  确认 `5173` 和 `8000` 端口没有被其他进程占用；确认手机打开的是脚本输出的 `<LAN_IP>`。
- 页面能打开但 API 请求失败：检查终端输出的 `VITE_API_BASE_URL` 是否是
  `http://<LAN_IP>:8000`；检查 `RUNRECOVER_CORS_ORIGINS` 是否包含
  `http://<LAN_IP>:5173`。
- PWA 添加到主屏幕：本地 HTTP 局域网访问下能力有限，完整安装体验通常需要 HTTPS 部署。

### 公网临时链接

如果需要临时发给别人访问，可以从仓库根目录运行：

```bash
npm run dev:tunnel
```

这个命令会启动 RunRecover，并通过 `cloudflared` 创建一个临时公网链接。终端会输出：

```text
Public URL: https://<random>.trycloudflare.com
```

保持终端打开，其他设备就可以通过这个临时链接访问。

### 自有域名启动

如果你已经有自己的域名，并且不用临时公网链接，可以使用：

```bash
npm run dev:domain
```

这个命令不会创建公网隧道；它只会按自有域名访问方式启动 RunRecover：

- Web 监听 `0.0.0.0:5173`
- API 监听 `127.0.0.1:8000`
- 浏览器请求同域 `/api`，由 Vite 代理到本地 API
- 如果配置了 `RUNRECOVER_PUBLIC_URL`，脚本会把该域名加入后端 CORS

在仓库根目录创建 `.env.local`：

```bash
RUNRECOVER_PUBLIC_URL=https://your-domain.example
```

如果你的域名是 `runrecover.cn`，就写：

```bash
RUNRECOVER_PUBLIC_URL=https://runrecover.cn
```

然后需要在你的域名服务商、服务器或路由器上完成外部访问配置。常见做法：

- 域名 DNS 的 `A` 记录指向你的公网 IP 或服务器 IP。
- 如果服务跑在家里或办公室的 Mac 上，路由器需要把公网 `80/443` 转发到这台 Mac，或转发到一台反向代理服务器。
- 推荐用 Nginx/Caddy 之类反向代理接 HTTPS，然后把请求代理到 `http://127.0.0.1:5173`。
- 不要直接把后端 `8000` 暴露到公网；前端同域 `/api` 会通过 Vite 代理访问后端。

### API

```bash
cd apps/api
python3 -m venv .venv
./.venv/bin/python3 -m pip install -r requirements.txt
./.venv/bin/python3 -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/api/health
```

### Web

```bash
cd apps/web
npm install
cp .env.example .env
npm run dev -- --host 127.0.0.1 --port 5173
```

Open `http://127.0.0.1:5173`.

For a complete local demo guide with command explanations, API examples, and presenter notes, see `docs/user-manual.md`.

## Productization Path

RunRecover should stay lightweight while the MVP is being validated.

Recommended phases:

1. Local one-command startup for development and demos.
2. Web App / PWA deployment: host the React app behind HTTPS and deploy the FastAPI API with SQLite or a managed database.
3. Consider a WeChat Mini Program or native iOS/Android app only after user validation shows that distribution channel is worth the extra maintenance.

The current frontend already includes basic PWA metadata:

- `apps/web/public/manifest.webmanifest`
- app icons under `apps/web/public/icons`
- mobile `theme-color` and Apple web app metadata
- production-only service worker registration for install/add-to-home-screen support

For production API access, configure backend CORS with:

```bash
RUNRECOVER_ENV=production
RUNRECOVER_CORS_ORIGINS=https://your-web-domain.example
```

For production frontend builds, configure:

```bash
VITE_API_BASE_URL=https://your-api-domain.example
```

This keeps the current React + FastAPI + SQLite architecture intact while making the app easier to demo and deploy as a Web/PWA product.

## Tests

```bash
cd apps/api
./.venv/bin/python3 -m pytest

cd apps/web
npm run build
```

## MVP Scope

Included in v1:

- Recovery score from distance, duration, run type, RPE, sleep, fatigue, soreness, run time, heart rate if present, and tomorrow-plan conflict.
- Main run type plus optional modifiers such as progressive, hills, target-pace block, and interval subtypes.
- Lightweight user level calibration for beginner, regular, and advanced runners.
- Recent 48-hour training context, lightweight feedback, and the latest 7 recovery records.
- Safety override flags for concerning symptoms and high-load combinations.
- Template recommendations that keep the demo stable without external API dependencies.
- Three frontend demo cases: easy recovery run, sleep-debt steady run, long muscle-load run.
- Optional LLM-backed recommendation providers with template fallback.

Not included in v1:

- Accounts, historical trends, device sync, GPX/CSV upload, calendar reminders, commercial admin tools.
- Native iOS/Android app or WeChat Mini Program implementation.
