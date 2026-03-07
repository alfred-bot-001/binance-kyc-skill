# Binance 工程师对接指南

> 面向 Binance 内部工程师：将 Chat KYC Skill 从 Demo 推向生产，Binance 侧需要提供什么。

---

## 一句话总结

**Binance 只需要提供 4 样东西：KYC API 接口、Liveness 页面 URL、Webhook 回调、API 密钥。**
其他全部由 Skill 侧（AI 助手）完成。

---

## 架构总览

```
用户的 AI 助手 (Telegram / WhatsApp / Web / 任何平台)
  │
  ├── binance-kyc skill (安装在助手里)
  │     │
  │     ├── 聊天收集信息 (姓名/生日/国籍/地址/证件)
  │     ├── 调 Binance API 提交数据
  │     ├── 发 Liveness 链接给用户
  │     └── 等 Webhook 回调 → 通知用户结果
  │
  ↕ HTTPS
  │
  Binance KYC Backend (你们提供)
    ├── KYC REST API
    ├── Liveness 页面 (现有能力)
    └── Webhook 通知
```

---

## Binance 需要提供的 4 样东西

### 1. KYC REST API 接口

| 接口 | 方法 | 用途 |
|------|------|------|
| `/sapi/v1/kyc/session` | POST | 创建 KYC 会话，返回 session_id |
| `/sapi/v1/kyc/personal-info` | POST | 提交个人信息 |
| `/sapi/v1/kyc/document/upload` | POST | 上传证件照片 (multipart) |
| `/sapi/v1/kyc/liveness/create` | POST | 获取活体检测页面 URL |
| `/sapi/v1/kyc/submit` | POST | 最终提交审核 |
| `/sapi/v1/kyc/status/{id}` | GET | 查询审核结果 |

如果 Binance 已有类似接口，只需告诉我 endpoint + 认证方式 + 字段命名，Skill 侧适配。

### 2. Liveness 活体检测页面

这是 Binance 已有的能力。Skill 的做法：
1. 调 API 获取带 token 的 liveness URL
2. 把链接发给用户
3. 用户在手机浏览器打开 → 完成人脸验证
4. Binance 通过 webhook 通知结果

要求：URL 可在移动端浏览器打开（不依赖 Binance App），有效期 10 分钟，支持 3 次重试。

### 3. Webhook 回调

活体完成时：
```json
POST {webhook_url}/kyc/liveness
{ "session_id": "xxx", "result": "passed" }
```

审核完成时：
```json
POST {webhook_url}/kyc/result
{ "session_id": "xxx", "result": "approved", "reason": null }
```

### 4. API 密钥

API Key + Secret（HMAC 签名），或 OAuth2，或 Binance 内部认证。

---

## Binance 不需要做的事

| 事项 | 谁负责 |
|------|--------|
| 聊天界面 / 前端 UI | Skill（在聊天中完成） |
| 多语言翻译 | Skill（自带 7+ 语言） |
| 信息收集对话流 | Skill 状态机 |
| 输入验证 | Skill 侧验证后提交 |
| 重试/异常引导 | Skill 处理 |
| 多平台适配 | Skill（Telegram/WhatsApp/Web） |
| SDK / WebView | 完全不需要 |

---

## 对接工期

| 阶段 | 时间 |
|------|------|
| Binance 提供 API 文档 | 1-2 天 |
| Skill 适配 + staging 联调 | 3-5 天 |
| 集成测试 | 2-3 天 |
| 灰度测试 | 1 周 |
| 正式发布 | - |
| **总计** | **2-3 周** |

---

## FAQ

**安全性？** 敏感操作（活体/审核）在 Binance 侧。Skill 只是信息管道，照片加密直传 API。

**跟现有系统冲突？** 不冲突。只是新的前端入口（聊天），后端走现有 KYC 系统。

**需要改 Binance App？** 不需要。完全独立。

---

Demo: https://alfred-bot-001.github.io/binance-kyc-skill/user-demo.html
GitHub: https://github.com/alfred-bot-001/binance-kyc-skill
