# GitHub Pages 与后端部署说明

Hint 自动机的前后端可以分开部署：

1. `frontend/` 是纯静态站点，可部署到 GitHub Pages。
2. FastAPI 后端必须运行在有公网地址的服务上，因为浏览器无法在 GitHub Pages 上直接执行 Python。

## 部署前端到 GitHub Pages

1. 将仓库推送到 GitHub。
2. 进入仓库 **Settings → Pages**。
3. **Build and deployment → Source** 选择 `Deploy from a branch`。
4. **Branch** 选择 `main`，目录选择 `/frontend`。
5. 保存后等待几分钟，记下生成的站点地址。

## 让前端访问后端

前端默认请求同源接口。部署到 GitHub Pages 后，需要修改 `frontend/app.js` 中的接口地址：

```javascript
const API_BASE = "https://你的后端地址";
```

然后在所有 `fetch` 请求前加上这个前缀，例如：

```javascript
fetch(API_BASE + "/api/health")
```

如果使用 Render.com，可将后端服务地址配置到 Render 环境变量 `APP_URL`，这样接口返回的健康状态会包含部署地址。

## 推荐后端托管方案

- Render.com：使用仓库中的 `deploy/render.yaml`。
- Railway / Fly.io：适合 Docker 部署。
- 云服务器：使用 Dockerfile 自行部署，并配置 HTTPS 反向代理。

## 跨域说明

后端已允许所有来源。生产环境建议把 `app/main.py` 的 `allow_origins=["*"]` 改为前端实际域名。

## 模型配置

后端支持 OpenAI 兼容协议。若使用 Ollama，可设置为：

- `LLM_BASE_URL=http://localhost:11434/v1`
- `LLM_API_KEY=ollama`
- `LLM_MODEL=qwen2.5:14b`

部署到云端时，建议使用可访问的模型服务，不要暴露个人内网地址。
