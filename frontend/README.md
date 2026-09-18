# Agent QualityOps 前端

企业智能体评测与质量运营控制台，基于 React、TypeScript 与 Vite，无外部 UI 组件库。

## 本地运行

已验证运行环境：Node.js `24.18.0`、npm `11.16.0`。Vite 需要 Node.js `20.19+` 或 `22.12+`。

```powershell
npm install
npm run dev
```

开发服务器默认访问 `http://127.0.0.1:5173`，并将 `/api` 代理到 `http://127.0.0.1:8000`。

如前后端分开部署，可在 `.env.local` 中设置：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

## 验证

```powershell
npm run typecheck
npm run build
```

前端不会伪造后端成功状态。后端不可用时会显示明确的离线提示和重试入口。
