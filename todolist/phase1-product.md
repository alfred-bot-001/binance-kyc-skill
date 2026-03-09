# 第一阶段：产品打磨（当前 → 可演示）

## ✅ 已完成
- [x] 完整对话式 KYC 流程设计（12 状态机）
- [x] SKILL.md 技能定义文件（符合 OpenClaw 规范）
- [x] Demo 前端 — user-demo.html（手机模型聊天界面）
- [x] Demo 前端 — index.html（带右侧面板的聊天演示）
- [x] Demo 前端 — business.html（商业分析页面）
- [x] Demo 后端 — FastAPI 模拟服务器（demo_server/app.py）
- [x] 多语言支持框架（en/zh JSON 模板）
- [x] GitHub Pages 线上演示部署
- [x] 76+ 单元测试
- [x] Docker 部署支持
- [x] CI/CD 自动部署 workflow

## 🟡 待完成
- [ ] 对接真实 Binance KYC API（当前所有调用为模拟）
  - 确认 API 端点：`/sapi/v1/kyc/*`
  - 获取 API Key / Secret 权限
  - 替换 demo mock 为真实请求
- [ ] Liveness 页面集成
  - 确认 Binance liveness 服务 URL 格式
  - 确认回调（callback）机制和参数
  - 测试 liveness URL 的有效期和重试逻辑
- [ ] Webhook 端点搭建
  - `/webhook/kyc/liveness` — 接收活体检测结果
  - `/webhook/kyc/result` — 接收审核结果（通过/拒绝）
- [ ] Demo 体验优化
  - 图片上传预览效果
  - 错误状态的 UI 反馈
  - 移动端适配测试
