# Hint 自动机 v2

面向洛谷题目的渐进式提示生成器。输入题号后，先抓取题面与公开题解，再由大模型按四个档位生成提示，避免一上来就暴露完整题解。

## 主要升级

- **四档渐进提示**：关键词 → 概念铺垫 → 思路方向 → 关键步骤
- **防剧透确认**：查看更高档位前二次确认
- **内容护栏**：限制完整代码、题解全文和答案泄露
- **题解排序**：结合点赞、作者、摘要完整度等信号筛选
- **缓存与限流**：同一请求优先命中缓存，避免重复抓取
- **模型可替换**：兼容 OpenAI 协议的云端或本地模型

## 目录结构

```
backend/
  app.py                # 开发启动入口
  requirements.txt
  .env.example
  app/
    main.py             # FastAPI 路由
    config.py           # 配置
    cache.py            # 本地缓存
    luogu.py            # 洛谷题面/题解抓取
    analysis.py         # 题解筛选与知识点提取
    prompts.py          # 分级提示词与内容审查
    llm.py              # OpenAI 兼容模型客户端
    demo.py             # 演示降级内容
    models.py           # 请求/响应模型
frontend/
  index.html
  styles.css
  app.js
deploy/
  Dockerfile
  render.yaml           # Render.com 部署配置
  github-pages.md        # GitHub Pages 静态部署说明
```

## 快速开始

```bash
cp backend/.env.example backend/.env
pip install -r backend/requirements.txt
python backend/app.py
```

打开 http://127.0.0.1:8000 。前端由 FastAPI 托管；也可单独部署静态前端，并把接口指向后端地址。

## 配置说明

复制 `backend/.env.example` 为 `backend/.env`：

| 变量 | 说明 |
| --- | --- |
| `LLM_BASE_URL` | OpenAI 兼容接口地址 |
| `LLM_API_KEY` | 模型 API 密钥；本地 Ollama 可填任意非空值 |
| `LLM_MODEL` | 模型名称，例如 `qwen2.5:14b` |
| `LUOGU_ENABLED` | 是否抓取真实洛谷内容 |
| `CACHE_HOURS` | 缓存有效期 |
| `RATE_LIMIT_PER_MINUTE` | 单进程每分钟请求上限 |
| `DEMO_API_KEY` | 生产环境建议设置接口密钥 |

模型未连接时，接口不会崩溃，而是返回演示提示。

## API

| 路径 | 方法 | 说明 |
| --- | --- | --- |
| `/api/health` | GET | 服务状态、模型、版本 |
| `/api/levels` | GET | 提示档位定义 |
| `/api/problem/{problem_id}` | GET | 题目元数据 |
| `/api/hint` | POST | 生成提示 |

示例：

```bash
curl -X POST http://127.0.0.1:8000/api/hint \
  -H "Content-Type: application/json" \
  -d '{"problem_id":"P1001","level":"approach","student_note":"只会枚举"}'
```

## 部署

### GitHub Pages

`frontend/` 可以直接作为 GitHub Pages 站点。后端需要部署到有公网地址的服务，例如 Render、Railway、Fly.io 或自己的服务器。详情见 `deploy/github-pages.md`。

### Docker

```bash
docker build -t hint-automata -f deploy/Dockerfile .
docker run -p 8000:8000 --env-file backend/.env hint-automata
```

### Render.com

使用 `deploy/render.yaml`。创建 Blueprint 实例后，将 `LLM_*` 等变量填写到控制台。

## 尊重版权与使用边界

- 题面、题解及内容的著作权归原作者和洛谷所有。
- 本工具仅作学习提示，不应批量转载、镜像或商业化使用题解内容。
- 生成内容可能存在事实错误，正式学习和竞赛请以原始题面、官方题解为准。
- 若权利人有异议，请联系删除。

## 免责声明

本仓库的抓取方式、公开接口依赖第三方网站结构，可能随时失效。使用时应遵守目标网站的服务条款、robots 协议和访问频率限制。
