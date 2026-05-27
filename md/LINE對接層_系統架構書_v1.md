# LINE 對接層 — 系統架構書 v2

| | |
|---|---|
| 版本 | v2.0（修正版） |
| 日期 | 2026-04-26 |
| 階段 | MVP 設計（施工前對齊用） |
| 目標時程 | 4 週 |
| 修訂重點 | **明確 TEP 為既有後端，本系統僅負責 LINE 對接，不重建活動/報名邏輯** |

---

## 目錄

1. [專案定位](#1-專案定位)
2. [系統邊界](#2-系統邊界)
3. [架構總覽](#3-架構總覽)
4. [資料模型](#4-資料模型)
5. [互動流程](#5-互動流程)
6. [API 設計](#6-api-設計)
7. [TEP 對接策略](#7-tep-對接策略)
8. [技術棧](#8-技術棧)
9. [開發環境](#9-開發環境)
10. [開放議題與風險](#10-開放議題與風險)
11. [分階段測試順序表](#11-分階段測試順序表)
12. [附錄](#12-附錄)

---

## 1. 專案定位

### 1.1 一句話定位

> **本系統是 LINE 端的對接層（LINE Gateway），把 LINE 使用者的互動轉接到既有的 TEP 廟宇後端。本系統不重建廟宇管理功能，TEP 仍是廟方管理後台與真實資料的擁有者。**

### 1.2 三個關鍵宣告

**宣告一：本系統不是廟宇系統。** 廟宇、活動、報名等業務資料的真正擁有者是 TEP（學長已實作的 Temple Events Platform）。本系統只負責 LINE 端的事情。

**宣告二：本系統不取代 TEP 後台。** 廟方管理員仍然在 TEP 後台建活動、管理報名。本系統不做廟方後台介面。

**宣告三：本系統的資料庫只記錄 LINE 端獨有的資訊。** 任何 TEP 已有的資料（活動、廟宇基本資料、報名紀錄）都不在本系統重建一份。

### 1.3 三方角色

| 角色 | 介面 | 屬於誰 |
|------|------|------|
| 信眾 | LINE App + LIFF 頁面 | 你做 |
| 廟方管理員 | TEP 管理後台網頁 | 學長已做 |
| 中間層 | LINE Webhook + LINE 推播服務 | **你做** |

### 1.4 為什麼需要這個對接層？

TEP 雖然已經有 LINE 整合（§11），但有以下結構性問題：

- TEP 的 LIFF 寫死 `VITE_TEMPLE_ID=1`，無法支援多廟
- TEP 的 `line_users` 與 `public_users` 完全脫鉤
- TEP 的 LINE 廣播是直接呼叫 LINE API，沒有訂閱機制（推給誰沒有清楚邊界）
- TEP 沒有 postback 互動處理（信眾無法在 LINE 內回應）

本系統存在的目的就是補上這些缺口，讓 LINE 互動體驗變完整。

---

## 2. 系統邊界

### 2.1 你做什麼（明確列出）

✅ LINE Official Account 申請與管理
✅ Rich Menu 設定
✅ Webhook endpoint（接收 follow / unfollow / message / postback）
✅ LIFF 頁面（訂閱廟宇、我的報名）
✅ Flex Message 模板（活動邀請卡）
✅ 訂閱關係資料庫（LINE UID ↔ 廟）
✅ 推播路由邏輯（廟方建活動 → 推給訂閱者）
✅ Postback 事件處理（按鈕 → 寫入 TEP）
✅ 操作流水紀錄（debug 與可觀測性）

### 2.2 你不做什麼（明確排除）

❌ 廟方管理後台（TEP 已有）
❌ 活動 CRUD 介面（TEP 已有）
❌ 報名名單管理介面（TEP 已有）
❌ 廟宇資料管理（TEP 已有）
❌ 信眾 web 端 App（不在本階段範圍）
❌ 金流 / LINE Pay
❌ 打卡、平安符、商品兌換等 TEP 既有功能的 LINE 版本

### 2.3 邊界爭議區（需協商）

⚠️ **TEP 既有的 LINE 廣播功能**：TEP §11.4 已有「廣播推播」並直接呼叫 LINE API。**這會與本系統衝突**——同一活動，TEP 會發一則陽春廣播，本系統會發一則 Flex Message，使用者收到兩則訊息。

**對策**：在 MVP 期間，協商請學長**暫停**或**禁用**TEP 的 LINE 廣播功能；改由本系統統一處理 LINE 通訊。長期方案見 §7。

---

## 3. 架構總覽

### 3.1 系統間關係

```
┌─────────────────┐         ┌──────────────────────┐
│   信眾 LINE     │         │   廟方管理員          │
│   (你的責任)     │         │   (TEP 既有後台)      │
└────────┬────────┘         └──────────┬───────────┘
         │                             │
         ▼                             ▼
┌─────────────────┐         ┌──────────────────────┐
│  LINE Platform  │         │  TEP Frontend       │
│  (Webhook/Push) │         │  (React SPA)        │
└────────┬────────┘         └──────────┬───────────┘
         │                             │
         ▼                             ▼
┌─────────────────────────┐  ┌──────────────────────┐
│   你的系統               │  │   TEP Backend       │
│   (LINE Gateway)         │  │   (Flask + MySQL)   │
│                          │  │                     │
│  ┌────────────────┐     │  │  - 活動 CRUD        │
│  │ Webhook Handler│     │  │  - 廟宇管理         │
│  │ LIFF Pages     │     │  │  - 報名管理         │
│  │ Subscription   │     │  │  - 廟方後台         │
│  │ Push Service   │     │◄──┤  - REST API        │
│  └────────────────┘     │HTTP│  (105 endpoints)   │
│                          │  │                     │
│  ┌────────────────┐     │  └──────────────────────┘
│  │ 輕量 DB         │     │           ▲
│  │ - line_users    │     │           │
│  │ - subscriptions │     │           │ HTTP API
│  │ - action_logs   │     │           │ (你呼叫 TEP)
│  └────────────────┘     │           │
│                          │───────────┘
└─────────────────────────┘
```

### 3.2 兩個關鍵呼叫方向

**方向 A：TEP → 你的系統**（推播觸發）

廟方在 TEP 後台按「發送通知」 → TEP 呼叫你的內部 API `POST /internal/push/event` → 你查訂閱關係 → 你推 Flex Message。

**方向 B：你的系統 → TEP**（使用者回應寫回）

信眾按 Flex Message 按鈕 → LINE 把 postback 給你 → 你呼叫 TEP `POST /api/public/events/:id/register` → 把報名寫進 TEP MySQL。

這兩個方向是整個系統的脈動，所有功能都建立在這之上。

### 3.3 你的系統內部三個入口

| 入口 | 對象 | 路徑 |
|------|------|------|
| Webhook | LINE Platform | `/webhook/line` |
| LIFF 頁面 | 信眾 | `/liff/*` |
| 內部 API | TEP（推播觸發） | `/internal/*` |

注意**沒有「廟方後台」入口**，因為那不是你的範圍。

---

## 4. 資料模型

### 4.1 設計原則

**只記錄 LINE 端獨有的資訊**。任何 TEP 已有的東西（廟宇詳細資料、活動內容、報名名單）都不在這裡重建——需要時透過 API 從 TEP 拉。

### 4.2 資料表

```mermaid
erDiagram
    LineUsers ||--o{ Subscriptions : "訂閱"
    LineUsers ||--o{ ActionLogs : "操作"
    LineUsers ||--o{ PushLogs : "收推播"

    LineUsers {
        int id PK
        string line_uid UK
        string display_name
        string picture_url
        enum follow_status "active / unfollowed"
        datetime followed_at
        datetime last_seen_at
    }

    Subscriptions {
        int id PK
        int line_user_id FK
        int tep_temple_id "對應 TEP 的 temples.id"
        boolean is_active
        datetime subscribed_at
    }

    ActionLogs {
        int id PK
        int line_user_id FK
        string action_type "register / cancel / view ..."
        json request_payload
        json tep_response
        enum status "pending / success / failed"
        datetime created_at
    }

    PushLogs {
        int id PK
        int line_user_id FK
        int tep_event_id "對應 TEP 的 temple_events.id"
        json flex_payload
        enum status "queued / sent / failed"
        datetime sent_at
    }
```

### 4.3 重要欄位說明

**`tep_temple_id`** 和 **`tep_event_id`**：這些是「外鍵」但不是真正的資料庫外鍵——它們指向 TEP MySQL 裡的 ID，但本系統不直接連 TEP 資料庫，只是用這些 ID 透過 API 查詢。

**為什麼不存 temples 表？** 因為廟宇資料在 TEP，本系統需要顯示廟宇名稱時透過 TEP API 查（並可選擇短暫快取）。把資料留在 TEP 才能保證一致性。

**`ActionLogs`** 是除錯救星。每次你呼叫 TEP API，都記下 request 和 response。當使用者抱怨「我明明按了參加但沒看到」時，你能立刻翻查為什麼。

### 4.4 不會建立的表（特別說明）

- ❌ `temples` — TEP 已有
- ❌ `events` — TEP 已有
- ❌ `registrations` — TEP 已有（叫 `event_registrations`）
- ❌ `admins` — TEP 已有

---

## 5. 互動流程

### 5.1 信眾首次加入

```
信眾掃 QR Code 加 OA
   ↓
LINE 觸發 follow 事件 → 你的 Webhook
   ↓
寫入 line_users
   ↓
推送歡迎訊息 + LIFF 連結（訂閱廟宇）
   ↓
信眾打開 LIFF → 從 TEP API 載入廟宇列表
   ↓
信眾選擇訂閱 → 寫入 subscriptions
```

**關鍵點**：訂閱列表由 TEP `GET /api/temples` 取得，本系統只負責顯示和記錄選擇結果。

### 5.2 廟方發布活動推播

```
廟方在 TEP 後台建活動（status=published）
   ↓
廟方點「LINE 推播」按鈕（TEP 上）
   ↓
TEP 呼叫你的 POST /internal/push/event
   payload: { event_id, temple_id }
   ↓
你的系統：
  1. 查 GET /api/temples/:id/events/:id 拿活動詳情
  2. 查 subscriptions WHERE tep_temple_id = ? AND is_active
  3. 對每位訂閱者：
     - 生成 Flex Message
     - 寫 push_logs
     - 呼叫 LINE Push API
```

**關鍵協商點**：TEP 那邊要新增「LINE 推播」按鈕呼叫你的 API，這需要學長配合改一行程式（見 §7.4）。

### 5.3 信眾回應流程

```
信眾收到 Flex，按「我要參加」
   ↓
LINE 觸發 postback → 你的 Webhook
   payload: { action: register, event_id, response: yes }
   ↓
你的系統：
  1. 寫 action_logs（status=pending）
  2. 呼叫 TEP POST /api/public/events/:event_id/register
     body: { name, phone, lineUserId }
  3. 寫 action_logs（status=success/failed）
  4. 推確認訊息給使用者
```

**關鍵問題**：呼叫 TEP 報名 API 需要 `name` 和 `phone`，但 LINE 只給你 `display_name` 和 `line_uid`。**怎麼辦？**

**對策三選一**（需團隊決定）：
- **(a) 首次報名時跳 LIFF 表單**讓使用者填姓名電話，存到 line_users
- **(b) 用 display_name 當 name**、phone 留空（TEP 有要求 phone 必填，可能不允許）
- **(c) 跟學長協商**讓 TEP 接受純 LINE UID 報名（修改 register API）

**MVP 建議走 (a)**——首次報名前先彈一個 LIFF 收集資料，後續報名直接用。

### 5.4 取消流程

```
信眾在「我的報名」LIFF 頁面或原 Flex 上按取消
   ↓
你的系統呼叫 TEP DELETE /api/registrations/:id
   或 PATCH /api/registrations/:id { status: cancelled }
   ↓
推確認訊息
```

**關鍵問題**：TEP 是否有公開的取消 API？需向學長確認。

---

## 6. API 設計

### 6.1 你提供的 API

**Webhook（給 LINE Platform 打）**
- `POST /webhook/line` — 接收所有 LINE 事件

**LIFF API（給信眾頁面打）**
- `GET /api/liff/me` — 取得自己的訂閱列表
- `POST /api/liff/subscriptions` — 新增訂閱
- `DELETE /api/liff/subscriptions/:temple_id` — 取消訂閱
- `POST /api/liff/profile` — 補充姓名電話
- `GET /api/liff/my-registrations` — 從 TEP 拉自己的報名（轉發）
- `POST /api/liff/registrations/:id/cancel` — 取消報名（轉發到 TEP）

**內部 API（給 TEP 打）**
- `POST /internal/push/event` — TEP 觸發推播
  - 需要簡單 API Key 驗證（HTTP Header）

### 6.2 你呼叫的 TEP API

| 用途 | 端點 | 認證 |
|------|------|------|
| 列廟宇 | `GET /api/temples` | 無（公開） |
| 廟宇詳情 | `GET /api/temples/:id` | 無 |
| 活動詳情 | `GET /api/temples/:id/events/:event_id` | 待確認 |
| 信眾報名 | `POST /api/public/events/:id/register` | 無（公開） |
| 查報名 | `GET /api/public/registrations?line_uid=` | 無（注意安全漏洞） |
| 取消報名 | 待確認 | 待確認 |

**注意**：`/api/public/registrations` 用 `line_uid` 當 query 沒有驗證——任何人知道某 LINE UID 就能查報名。本系統呼叫時要把這視為「弱身分」，只用於顯示自己的報名（從 webhook 取得的 line_uid 是可信的）。

### 6.3 需要跟學長確認的 API 缺口

清單給學長看：

1. 取消報名的端點是什麼？
2. 活動詳情有公開端點嗎？（給 LIFF 載入用）
3. TEP 的「LINE 推播」按鈕是否能改成呼叫本系統 API？
4. 有沒有 webhook 機制讓 TEP 主動通知本系統「活動建立/更新/刪除」？
5. 跨來源請求（CORS）設定是否允許 LIFF 頁面打 TEP？

---

## 7. TEP 對接策略

### 7.1 三個明確分工

| 工作 | 誰做 | 備註 |
|------|------|------|
| 活動 CRUD | 學長（TEP 已有） | 你不重做 |
| 廟方後台 UI | 學長（TEP 已有） | 你不重做 |
| LINE 推播觸發 UI | 學長（TEP 加一顆按鈕） | 改動很小 |
| 訂閱關係 | 你 | TEP 沒有這個 |
| Postback 處理 | 你 | TEP 沒有這個 |
| Flex Message 設計 | 你 | TEP 沒有這個 |

### 7.2 LINE 廣播衝突處理

**短期（MVP）**：
- 請學長禁用 TEP 既有的 LINE 廣播按鈕（或改成內部測試用）
- TEP 後台新增「LINE 推播」按鈕，呼叫本系統 API

**長期（V2 後）**：
- 完整移除 TEP 直接呼叫 LINE 的能力
- 所有 LINE 通訊統一經本系統

### 7.3 身分對應簡化方案

**MVP 階段不做 LINE UID ↔ TEP public_user 綁定**。

理由：
- 本階段沒有功德值、商品兌換等需要 TEP 帳號的功能
- 報名時直接傳 `lineUserId` 給 TEP，TEP 在 `event_registrations` 表會記，足夠 MVP 需求
- V2 才考慮綁定機制

### 7.4 學長那邊要做的最小變動

讓 MVP 跑起來，需要學長配合做的事：

1. **新增 TEP API**：`POST /internal/push/event` 的呼叫者（從廟方後台觸發）— 在 TEP 後台加一顆按鈕
2. **協商 API 細節**：取消報名、活動詳情公開端點
3. **暫停 TEP 既有 LINE 廣播功能**（避免衝突）

這三件事要在 Week 0-1 之間談妥。

---

## 8. 技術棧

### 8.1 你的系統

| 類別 | 技術 |
|------|------|
| 語言 | Python 3.11 |
| 框架 | Flask 3.x |
| ORM | SQLAlchemy + Flask-Migrate |
| 資料庫 | PostgreSQL 16 |
| LINE SDK | line-bot-sdk |
| HTTP Client | requests / httpx（呼叫 TEP） |
| 部署 | Zeabur |
| 本機 tunnel | ngrok |

### 8.2 你不需要做的決策

以下都已由 TEP 決定（你只要會打它的 API）：
- ❌ 不用選後台前端框架（學長用 React 19）
- ❌ 不用選 ORM 語意（你只用 HTTP 對接，不直接連 TEP MySQL）
- ❌ 不用設計廟方後台 UI

### 8.3 LIFF 前端決策

| 類別 | 技術 | 用途 |
|------|------|------|
| 樣板 | Jinja2 | Flask 直接吐 HTML |
| 樣式 | Tailwind CSS | 設計稿來時可還原 |
| 互動 | Alpine.js | 輕量，不用 React |
| LIFF SDK | @line/liff v2 | 必備 |

---

## 9. 開發環境

### 9.1 本機需要同時跑的東西

```
Terminal 1: TEP（學長系統）
  cd tep-master/
  docker-compose up
  → http://localhost:80（前端）
  → http://localhost:5000（後端 API）

Terminal 2: 你的系統
  cd line-gateway/
  flask run --port 5002
  → http://localhost:5002

Terminal 3: 你的 PostgreSQL
  docker run --name gw-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:16

Terminal 4: ngrok（暴露你的系統給 LINE）
  ngrok http 5002
  → 填到 LINE Webhook URL
```

### 9.2 環境變數

```env
# Flask
FLASK_ENV=development
SECRET_KEY=xxx

# Your DB
DATABASE_URL=postgresql://postgres:dev@localhost:5432/gateway

# LINE
LINE_CHANNEL_SECRET=xxx
LINE_CHANNEL_ACCESS_TOKEN=xxx
LIFF_ID_SUBSCRIBE=xxx
LIFF_ID_PROFILE=xxx
LIFF_ID_MY_REGISTRATIONS=xxx

# TEP
TEP_BASE_URL=http://localhost:5000/api
TEP_API_KEY=xxx              # 學長給的 internal call key

# 本系統的 internal API key（給 TEP 打你用）
GATEWAY_INTERNAL_KEY=xxx
```

---

## 10. 開放議題與風險

### 10.1 必須跟學長確認的事項

| # | 項目 | 阻塞等級 |
|---|------|---------|
| 1 | TEP 是否能新增「LINE 推播」按鈕呼叫本系統 | 🔴 高 |
| 2 | TEP 的取消報名 API 規格 | 🟡 中 |
| 3 | TEP 的活動詳情公開 API | 🟡 中 |
| 4 | TEP 既有 LINE 廣播是否能暫停 | 🟡 中 |
| 5 | TEP 是否能加 webhook 通知本系統 | 🟢 低（V2） |

### 10.2 風險

**風險 1：學長無法配合改 TEP**
對策：MVP 階段廟方在「**你的陽春管理頁**」按推播，繞過 TEP 改動。但這違反「不做後台」原則，是備案。

**風險 2：使用者報名需要姓名電話**
對策：見 §5.3，預設走方案 (a) — 首次報名前用 LIFF 收集。

**風險 3：TEP API 不穩定或變更**
對策：所有 TEP 呼叫包 try/except、設 timeout、寫 action_logs。失敗時使用者看到「系統忙碌請稍後再試」，不要爆炸。

**風險 4：設計稿零進度**
對策：先用 LINE 官方 Flex Message 預設樣式 + Tailwind 預設配色。功能完整 > 視覺完美。

**風險 5：時程壓力**
對策：嚴格遵守分階段測試表（§11），每個小功能做完就測，不要堆積。

---

## 11. 分階段測試順序表

**核心原則**：每個階段都是「能跑、能測、能 demo 一點點」。不要等全部做完才測試——那叫災難。

### 階段 0：環境齊備（不寫業務程式）

| # | 任務 | 驗收標準 | 預估 |
|---|------|---------|------|
| 0.1 | 本機跑起 TEP（docker-compose up） | 能用瀏覽器看到 TEP 前端 | 半天 |
| 0.2 | 本機建立你的 Flask 空專案 | `flask run` 能看到 hello world | 半天 |
| 0.3 | 本機 PostgreSQL 跑起來 | 能用 DBeaver 連上 | 1 小時 |
| 0.4 | ngrok 跑起來 | 能拿到公開 HTTPS URL | 30 分 |
| 0.5 | LINE Developer 申請完 OA + 1 個 LIFF | Channel Secret/Token 拿到 | 半天 |
| 0.6 | 加自己 LINE OA 為好友，測能不能加 | 加成功 | 5 分 |

**這階段不碰任何業務邏輯，只確保「工具齊備」。**

---

### 階段 1：LINE 連線打通（最簡單的回音）

| # | 任務 | 驗收標準（怎麼測） |
|---|------|------|
| 1.1 | 寫 `/webhook/line` 收 LINE 事件 | 用 ngrok URL 設到 LINE 後台，自己發訊息給 OA，能看到 Flask log 印出事件 |
| 1.2 | 加上簽章驗證 | 隨便用 curl 假打 webhook，要被擋掉 |
| 1.3 | 對 message 事件做 echo | 自己發「hello」給 OA，OA 回「你說：hello」 |
| 1.4 | 對 follow 事件記錄 | 自己取消追蹤再加回來，DB 看到 follow_status 變化 |

**這階段結束你已經有一個「會回話的 LINE Bot」。** Demo 給團隊看：「我發訊息它回我」就足夠。

---

### 階段 2：使用者資料庫（基礎建設）

| # | 任務 | 驗收標準 |
|---|------|------|
| 2.1 | 建 `line_users` 表 + Migration | flask db upgrade 跑成功 |
| 2.2 | follow 事件寫入 `line_users` | 加好友後查 DB，看到自己的 line_uid + display_name |
| 2.3 | unfollow 事件更新 status | 取消追蹤後 follow_status=unfollowed |
| 2.4 | 重複 follow 處理 | 取消再加，不重複建 row，updated_at 有變 |

**這階段結束你有「LINE 使用者」這個概念了。** 還測不到多人，但邏輯通了。

---

### 階段 3：LIFF 第一頁（顯示能讀到使用者）

| # | 任務 | 驗收標準 |
|---|------|------|
| 3.1 | 建一個最簡單的 LIFF 頁 `/liff/test` | 在 LINE 內打開 LIFF URL，看到 hello world |
| 3.2 | LIFF 取得 LINE UID 並顯示 | LIFF 頁面顯示「你的 LINE UID 是 Uxxx」 |
| 3.3 | LIFF 後端 API：`/api/liff/me` | LIFF 顯示「歡迎 [自己的名字]」（從 line_users 拉） |
| 3.4 | 加進 Rich Menu | 在 LINE 看到底下選單，點選會打開 LIFF |

**這階段結束你能在 LINE 內開頁面、認得使用者了。** 設計稿沒來也能做這些。

---

### 階段 4：訂閱關係（多對多核心）

| # | 任務 | 驗收標準 |
|---|------|------|
| 4.1 | 建 `subscriptions` 表 | Migration 跑成功 |
| 4.2 | LIFF 頁「訂閱廟宇」 | 從 TEP `GET /api/temples` 拉廟宇列表顯示 |
| 4.3 | 訂閱 API：`POST /api/liff/subscriptions` | 點選廟宇 → 寫入 subscriptions → 重新整理頁面看到「已訂閱」 |
| 4.4 | 取消訂閱 | 點「取消訂閱」→ is_active=false |
| 4.5 | 多廟測試 | 在 TEP 後台手動建第二間廟，LIFF 看得到，可以分別訂閱 |

**這階段結束多對多訂閱機制完成。Demo 重點：「我可以一次訂閱多間廟」。**

---

### 階段 5：推播觸發（單方向：廟方 → 信眾）

| # | 任務 | 驗收標準 |
|---|------|------|
| 5.1 | 寫 `/internal/push/event` 接 TEP 觸發 | 用 curl 假裝 TEP 打你，能成功收到 |
| 5.2 | 推播邏輯：查訂閱 → 推 LINE Push | curl 觸發後，自己 LINE 收到一則文字訊息 |
| 5.3 | 寫 push_logs 完整紀錄 | DB 能看到每筆推播紀錄 |
| 5.4 | 第一版 Flex Message（陽春） | 訊息變成卡片格式，有標題和內文 |
| 5.5 | Flex Message 加按鈕（不處理 callback） | 卡片下面有「我要參加」按鈕（按了沒反應沒關係） |

**這階段結束推播這條路通了。Demo：「廟方 trigger 推播，所有訂閱者收到漂亮卡片」。**

---

### 階段 6：基本資料收集（為了能呼叫 TEP）

| # | 任務 | 驗收標準 |
|---|------|------|
| 6.1 | LIFF 頁「補充資料」（姓名、電話） | LIFF 表單能填並送出 |
| 6.2 | 寫 `/api/liff/profile` 存進 line_users | DB 看到 phone 欄位被填 |
| 6.3 | 必填驗證 | 沒填姓名電話無法送出 |

**這階段是為下一階段準備——TEP 報名 API 需要這些資料。**

---

### 階段 7：呼叫 TEP 寫資料（最關鍵的整合）

| # | 任務 | 驗收標準 |
|---|------|------|
| 7.1 | 用 Postman 手動打 TEP `POST /api/public/events/:id/register` | 報名成功，TEP DB 看到 event_registrations 多一筆 |
| 7.2 | 寫 services/tep_client.py 封裝 TEP 呼叫 | 程式碼呼叫能成功 |
| 7.3 | Postback handler 處理「我要參加」 | 在 LINE 按按鈕，TEP DB 看到報名 |
| 7.4 | 寫 action_logs | 每次呼叫 TEP 都有紀錄 |
| 7.5 | 推確認訊息 | 報名成功後 LINE 收到「已為您報名！」 |
| 7.6 | 失敗處理 | 故意把 TEP 關掉，按按鈕後 LINE 收到「系統忙碌」 |

**這階段結束核心 demo 已成立：使用者按按鈕 → 真的報名到 TEP 了。** 這是整個 MVP 最關鍵的時刻。

---

### 階段 8：取消與查詢（雙向流的另一半）

| # | 任務 | 驗收標準 |
|---|------|------|
| 8.1 | LIFF 頁「我的報名」 | 從 TEP 拉自己的報名顯示 |
| 8.2 | 取消按鈕 + 呼叫 TEP 取消 API | TEP DB 看到狀態變 cancelled |
| 8.3 | 推確認訊息 | LINE 收到「已取消」 |
| 8.4 | 廟方後台驗證 | 在 TEP 後台看到報名清單即時反映 |

**這階段完成雙向流。Demo：「我能看自己報的名、能取消、廟方那邊立刻看到」。**

---

### 階段 9：Polishing 與部署

| # | 任務 | 驗收標準 |
|---|------|------|
| 9.1 | 部署到 Zeabur | 拿到正式 HTTPS URL |
| 9.2 | 設定環境變數 | 正式環境能跑 |
| 9.3 | LINE Webhook 換成正式 URL | 訊息能正常處理 |
| 9.4 | 找 3-5 個真人測試 | 全部跑通完整流程 |
| 9.5 | 修 bug | bug 列表清空 |
| 9.6 | 寫 README + 操作文件 | 別人能照做 |

---

### 11.1 階段判斷原則

每個階段做完先問自己三個問題：

1. **能不能 demo 給別人看？**（不能就還沒結束）
2. **這階段的 bug 修完了嗎？**（沒修完就不要進下階段）
3. **下一階段需要的東西這階段準備好了嗎？**（沒準備好會卡住）

三個都「是」才進下一階段。**寧可某階段做好一週，也不要每階段都做半套。**

### 11.2 時程對應

| 週 | 對應階段 | 主軸 |
|---|---------|------|
| Week 0 | 階段 0 | 工具齊備 |
| Week 1 | 階段 1-3 | LINE 連線通、使用者建立、LIFF 跑起 |
| Week 2 | 階段 4-5 | 訂閱機制、推播觸發 |
| Week 3 | 階段 6-7 | 整合 TEP、雙向流跑通 |
| Week 4 | 階段 8-9 | 取消功能、部署、測試 |

---

## 12. 附錄

### 12.1 專案目錄結構

```
line-gateway/
├── app.py
├── config.py
├── requirements.txt
├── .env.example
├── migrations/
│
├── blueprints/
│   ├── webhook.py        # /webhook/line
│   ├── liff.py           # /liff/* + /api/liff/*
│   └── internal.py       # /internal/* (給 TEP 打)
│
├── models/
│   ├── line_user.py
│   ├── subscription.py
│   ├── action_log.py
│   └── push_log.py
│
├── services/
│   ├── tep_client.py             # 呼叫 TEP API 的封裝
│   ├── flex_builder.py           # 組 Flex Message
│   ├── push_service.py           # 推播邏輯
│   └── subscription_service.py
│
├── templates/
│   └── liff/
│       ├── subscribe.html
│       ├── profile.html
│       └── my_registrations.html
│
└── static/
```

### 12.2 給學長的對接需求清單

請學長確認以下事項：

1. ✅ 我的系統 `POST /internal/push/event` 將接受以下參數：`{ event_id, temple_id }` ── 你能在 TEP 後台「活動編輯頁」加一顆「LINE 推播」按鈕，按下後呼叫這個 endpoint 嗎？
2. ❓ 取消報名的 API 規格是什麼？（端點、method、body、認證）
3. ❓ 活動詳情有公開（不需 JWT）的端點嗎？我需要在 LIFF 顯示活動內容
4. ⚠️ TEP §11.4 既有的 LINE 廣播功能，能在 MVP 期間暫停嗎？避免訊息重複
5. ❓ TEP 後台顯示「LINE 推播狀態」嗎？（成功幾人、失敗幾人）我可以提供 status callback API

### 12.3 術語對照

| 術語 | 中文 | 屬於 |
|------|------|------|
| TEP | Temple Events Platform | 學長的系統 |
| LINE Gateway | LINE 對接層 | 你的系統 |
| OA | LINE 官方帳號 | LINE 平台 |
| LIFF | 嵌在 LINE 的網頁 | LINE 平台 |
| Flex Message | 可互動卡片訊息 | LINE 平台 |
| Postback | 按鈕回呼事件 | LINE 平台 |
| Webhook | LINE 通知本系統的 endpoint | 你的系統 |

---

*本架構書建立在「TEP 已存在、本系統只做 LINE 對接」的明確前提上。任何重建廟方後台、活動管理、報名管理的提議都應拒絕。*
