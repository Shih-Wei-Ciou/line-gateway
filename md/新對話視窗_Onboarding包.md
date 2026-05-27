# 新對話視窗 Onboarding（一篇進入狀態）

> **使用方式**：開新 Claude 對話視窗時，整篇貼進去當第一則訊息。Claude 看完會說「我了解了，請繼續」，你就可以無縫接軌。
>
> **最後更新**：2026-05-07
> **接續位置**：Stage 4 TEP API 串接（80% 骨架完成，等學長配合）

---

## 一、我是誰、在做什麼

我叫 Max，碩一研究生，正在開發一個叫做「**LINE 對接層（LINE Gateway）**」的專案。這是一個宮廟數位轉型專案的子系統。

### 一句話定位

我做的是 **LINE 端的對接層**——把 LINE 使用者的互動轉接到我學長已經做好的 TEP（Temple Events Platform）廟宇後端。**我不重建廟宇後端**，TEP 是真實資料的擁有者，我只負責 LINE 端。

### 系統本質

這是**體驗型專案**不是功能型專案。差別：
- 功能型（報稅系統）：使用者完成任務就走、過程越短越好
- 體驗型（本案）：使用者產生情感連結、想再回來

核心信念：每個功能要讓使用者覺得**「儀式感、被理解感、內心平靜」**。**警惕遊戲化陷阱**——不做積分、徽章、稀有度。

---

## 二、技術棧（已決定，不要建議改）

| 類別 | 選擇 |
|---|---|
| 後端 | Python 3.11 + Flask 3.x |
| ORM | SQLAlchemy 2.x（用 `select()` 新語法）+ Flask-Migrate |
| 資料庫 | PostgreSQL 16（本機 Windows 安裝、雲端 Zeabur） |
| LINE SDK | line-bot-sdk-python |
| LIFF 前端 | Jinja2 + Tailwind CDN + Alpine.js（**不用 React/Vue/npm**） |
| 部署 | Zeabur Dev Plan $5/月 |
| 本地測試 | ngrok |

**LINE 兩個 Channel**：
- Messaging API Channel：訊息收發、Webhook、推播
- LINE Login Channel：LIFF（2023 年 LINE 規定 LIFF 必須建在 Login Channel 下）

---

## 三、V1 五個核心功能（依優先順序）

1. **參訪動線**
2. **祈求詞**
3. **報名活動**（跟 TEP 整合最深的）
4. **現場資訊**（停車、廁所、設施）
5. **準備用品**

**示範廟**：白河三官寶殿（V1 唯一一間）。V1 目標 3 間（1 確定 + 2 代找）。

**V2 候選**（不在當前範圍）：推薦廟宇、打卡、LINE Pay、廟方數據後台。

---

## 四、資料庫架構（四張表）

```
line_users          ─ LINE 使用者
  ├── line_uid (UK), display_name, picture_url
  ├── phone, real_name（透過 LIFF 補填）
  ├── follow_status (active / unfollowed)
  └── followed_at, last_seen_at

subscriptions       ─ 訂閱關係（多對多，V2 多廟必備）
  ├── line_user_id (FK), tep_temple_id
  ├── is_active（軟刪除）
  └── subscribed_at, unsubscribed_at
  複合唯一索引：(line_user_id, tep_temple_id)

action_logs         ─ 操作流水（稽核 + debug）
  ├── line_user_id (FK), action_type
  ├── request_payload (JSONB), tep_response (JSONB)
  └── status (pending / success / failed)

push_logs           ─ 推播紀錄
  ├── line_user_id (FK), tep_event_id
  ├── flex_payload (JSONB)
  └── status, sent_at, error_message
```

**不建的表**（在 TEP）：❌ temples / events / registrations / admins

---

## 五、目前進度（重要！）

### 已完成

| Stage | 內容 | 狀態 |
|---|---|---|
| Week 0 | 環境（GitHub repo、LINE Channel、Python、PostgreSQL、Flask、4 張表） | ✅ |
| Stage 1 | LINE Webhook 接通、簽章驗證、Echo Bot、follow event 處理 | ✅ |
| Stage 2 | line_users upsert、unfollow 軟更新、Profile API、last_seen_at | ✅ |
| Stage 3 | LIFF SDK 整合（Fake/Real Mode）+ 訂閱 API（POST/DELETE/GET 都通） | ✅ |
| Stage 4 | TEP Client 骨架（含 retry、singleton、6 endpoints） | 🟡 80% |

### 還沒做

| Stage | 內容 | 阻塞原因 |
|---|---|---|
| Stage 4 | 端對端測試 | 等學長給測試資料 |
| Stage 5 | 活動推播（Flex Message） | 設計稿 + 後端 Push Service |
| Stage 6 | 報名互動（postback） | 設計稿 |
| Stage 7 | 我的報名 + 取消 | 設計稿 |
| Stage 8 | 部署到 Zeabur | 等前面都完成 |

### Stage 4 重大發現（2026-05-03）

> 原本以為 Stage 6 報名會卡在「LINE UID ↔ TEP user_id 綁定」。實測 TEP 程式碼發現 `/api/public/*` 直接吃 lineUserId，**不需要綁定**。Stage 4-7 後端可以一路打到底。

---

## 六、重要決策歷史（避免重複討論）

| 決策 | 為什麼這樣選 |
|---|---|
| 用 LINE 不做獨立 App | 信眾年齡層偏大、覆蓋率高 |
| 對接 TEP 不重建後端 | 學長已做好、避免重工 |
| 用 PostgreSQL 不用 MySQL | Zeabur 支援好、JSONB 對 logs 有優勢 |
| 用 Zeabur 不用 GCP/AWS | 台灣節點、$5/月、GitHub 一鍵部署 |
| 用 Tailwind+Alpine.js 不用 React | 單人開發、CDN 引入、學習成本低 |
| LIFF 建在 LINE Login Channel | LINE 2023 政策變更 |
| 訂閱用軟刪除 (is_active) | 保留歷史、重訂閱可「復活」 |
| 開發階段用 X-Line-Uid header | Postman 好測，正式版改 access token |
| 不做 Flex Builder | 等設計稿來了再做 |
| 警惕遊戲化機制 | 不適合廟宇場景，會違反核心信念 |

---

## 七、不做的事（拒絕清單）

如果接下來討論中我或你提到這些，請拒絕：

**系統層級**：
- ❌ 重建 TEP 廟方後台
- ❌ 在本系統存活動、廟宇、報名等業務資料
- ❌ 信眾獨立 web App / 移動端 App

**技術層級**：
- ❌ LINE Pay 金流
- ❌ 多 OA
- ❌ Docker（本機裝不起來）
- ❌ npm / 前端構建工具
- ❌ React / Vue / Next.js

**設計層級**：
- ❌ 過度動畫、過度設計
- ❌ 遊戲化機制（積分、徽章、稀有度）
- ❌ 在 MVP 階段做精美 UI（等設計師交稿）

---

## 八、四大關鍵架構機制（顧問會問）

### 8.1 資安（三層驗證）

- **對外**：X-Line-Signature 驗證 webhook 真偽
- **內部**：X-Gateway-Key 驗證 TEP 觸發推播的合法性
- **前端**：開發階段用 X-Line-Uid header，正式版改 liff.getAccessToken() + LINE 官方驗證 API

### 8.2 容錯（Graceful Degradation）

- TEP Client 內建 retry：5xx 重試 3 次（指數退避）、4xx 不重試
- TEP 完全失敗 → catch 例外、寫 action_logs、推友善訊息「系統忙碌請稍後」
- API Client Singleton + Session 重用

### 8.3 推播策略

- 使用 LINE Multicast API（每批 500 人）不用迴圈 push
- 漸進式 Onboarding：歡迎 Flex + 點擊觸發、不連續 push
- LIFF 通道分離（Login Channel）

### 8.4 數據追蹤（V2 規劃）

- 預留 view_logs 表（schema 先設、V1 不寫入）
- 統一 trackEvent(type, id, action, metadata) 介面
- 為廟方未來「人流熱區、熱搜神明」報表預備

---

## 九、現在的下一步

### 立刻可以做（不阻塞）

- Push Service 後端框架（Stage 5 純技術部分）
- Internal API 入口（`/internal/push/event` + X-Gateway-Key 驗證）
- Postback router 骨架（Stage 6 解析層）
- Stage 6/7 後端邏輯

### 等學長

- TEP 是否能本機跑、有 deploy 網址嗎
- 確認 `/api/public/*` 直接吃 lineUserId 的方向對不對
- 提供測試廟宇 + 測試活動

### 等設計同學（5/8 討論）

- LIFF 訂閱頁完整 UI
- Flex 卡片視覺
- 訊息文案

---

## 十、檔案地圖

```
line-gateway/
├── app.py                          # Flask 主程式
├── .env / .env.example             # 環境變數
├── models/
│   ├── line_user.py
│   ├── subscription.py
│   ├── action_log.py
│   └── push_log.py
├── services/
│   └── tep_client.py               # TEP API client（已完成）
├── templates/
│   └── liff/
│       └── test.html               # LIFF 測試頁（已完成）
└── migrations/                     # Flask-Migrate
```

---

## 十一、我的協作方式

我用三窗口分工：

1. **主窗口**（戰略討論、規劃方向）— 你會是這個
2. **第二窗口**（實作翻譯官，把需求翻成 Claude Code 指令）
3. **Claude Code**（實際寫程式碼）

你的角色是**陪我思考方向、決定下一步要做什麼**。具體寫程式我會丟給 Claude Code。

我提一個需求 → 你跟我討論可行性、設計細節 → 我跟第二窗口確認指令格式 → Claude Code 執行 → 回來跟你 review。

---

## 十二、關鍵連結

我的 Notion 工作區結構：
- 數位平安符（總頁）
  - 工作清單與流程（hub）
    - 01 主規劃文件 v2（詳細版）
    - 系統架構與專案說明書 v2（資訊顧問版）
    - LINE 功能全規格快查表
    - 2026-05-03 進度快照

如果你能讀 Notion，這幾頁可以參考。如果不行，這份文件就是最完整的 onboarding。

---

## 看完後請回我

如果你看完這份文件、能清楚理解專案狀態，請回我**「我了解了，請告訴我下一步要討論什麼」**。

不用重述背景、不用問前面提過的問題。我會直接給你今天要討論的事項。

---

*這份 onboarding 包讓你跟新對話無縫接軌，避免重複解釋背景。*
