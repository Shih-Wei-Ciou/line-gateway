# 宮廟 LINE 系統 — 開發規劃書（精簡版）

> 版本：v1.0 (Lite)
> 時程：4 週 MVP
> 目標：為示範宮廟建立 LINE 數位服務系統

---

## 一、MVP 範圍

本階段**不含**線上付款（LINE Pay）。金流採「線上預約 → 現場付款」模式：使用者於 LINE 預約 → 系統生成預約單 → 到廟後現場繳費 → 廟方於後台標記完成。

### 三大核心功能

1. **報名系統**：法會、志工活動線上報名，後台自動彙整名單
2. **預約系統**：光明燈預約、隨喜登記，產生預約單供現場核對
3. **廟方後台**：報名名單、預約紀錄、活動管理、基本數據

---

## 二、技術棧

| 項目 | 選擇 |
|------|------|
| IDE | VSCode（已設好 Claude Code） |
| 後端 | Flask + SQLAlchemy + Flask-Migrate |
| 資料庫 | PostgreSQL 16（本地 Docker / 雲端 Zeabur） |
| 前端 | Flask + Jinja2 + htmx |
| 認證 | LINE Login（信眾）/ bcrypt（Admin） |
| 部署 | Zeabur（台灣節點、中文介面、$5/月） |
| 本地測試 | ngrok |
| LINE SDK | line-bot-sdk-python |

### VSCode 必裝延伸模組

Python、Pylance、SQLTools + PostgreSQL Driver、Jinja、Thunder Client、GitLens

---

## 三、4 週時程

### Week 0（準備日，當天完成）

- [ ] 申請 LINE Developers 帳號、建立 Provider
- [ ] 開啟 Messaging API（取得 Channel Secret、Access Token）
- [ ] 開啟 LINE Login、建立 LIFF 應用
- [ ] GitHub 建 private repo
- [ ] 註冊 Zeabur、綁定 GitHub
- [ ] 跟宮廟索取：既有後台技術資料、活動資訊、管理員名單

### Week 1 — 架構與資料庫

- [ ] `python -m venv venv` 建虛擬環境
- [ ] 安裝套件：`flask line-bot-sdk Flask-SQLAlchemy Flask-Migrate psycopg2-binary python-dotenv Flask-WTF bcrypt gunicorn`
- [ ] Docker 跑本地 PostgreSQL：
  ```bash
  docker run --name temple-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:16
  ```
- [ ] 建立 Flask 專案骨架（見 §5）
- [ ] 依 §4 ERD 實作 models
- [ ] 初始化 migration：`flask db init && flask db migrate && flask db upgrade`
- [ ] `/` 路由回 Hello World 測試

### Week 2 — LINE 整合 + 使用者綁定

- [ ] 啟動 ngrok，將網址設到 LINE Developer Console
- [ ] 開發 `/webhook` endpoint（**必須驗證 X-Line-Signature**）
- [ ] 測試 Echo Bot，確認收發訊息正常
- [ ] LIFF 首頁：取得 LINE UID、自動建立/更新 User 記錄
- [ ] LINE 官方後台手動設定 Rich Menu（六宮格）
  - 建議：法會報名 / 光明燈預約 / 志工報名 / 我的紀錄 / 廟宇資訊 / 聯絡我們
- [ ] 與設計端確認 UI 規格：字級、對比、長輩友善模式

### Week 3 — 核心功能開發

**3.1 報名系統（最重要，先做）**
- [ ] 活動列表頁（顯示日期、名額、進度條）
- [ ] 活動詳情 + 報名表單（姓名、電話自動預填）
- [ ] 寫入 Registrations 表
- [ ] 推一則 Flex Message 確認通知

**3.2 光明燈預約**
- [ ] 燈種選擇 + 疏文填寫
- [ ] 產生預約單（含編號 + QR code）
- [ ] 預約紀錄寫入 Lamps 表（`status=pending_payment`）

**3.3 廟方後台（Admin）**
- [ ] 登入頁（bcrypt 雜湊密碼）
- [ ] Dashboard：本週統計（報名數、預約數）
- [ ] 活動管理 CRUD
- [ ] 報名名單檢視、CSV 匯出
- [ ] 預約單管理（查核付款、標記完成）

### Week 4 — 部署、測試、實地檢驗

- [ ] `.gitignore` 確認 `.env` 沒被 push
- [ ] 程式碼 push GitHub
- [ ] Zeabur 建立 PostgreSQL、取得連線字串
- [ ] 部署 Flask 專案到 Zeabur
- [ ] 設定環境變數（見 §6）
- [ ] 雲端執行 `flask db upgrade`
- [ ] LINE Webhook URL 切換到 Zeabur 正式網址
- [ ] 端對端測試：掃碼 → 報名 → 收通知 → 後台查看
- [ ] 實地到宮廟測試，記錄新手使用者痛點
- [ ] 依回饋做第一版修正

---

## 四、ERD 資料庫設計

```mermaid
erDiagram
    Users ||--o{ Registrations : "報名"
    Events ||--o{ Registrations : "被報名"
    Users ||--o{ Lamps : "預約"
    Users ||--o{ PushLogs : "收通知"

    Users {
        int id PK
        string line_user_id UK
        string display_name
        string phone
        int merit_points
        datetime created_at
    }

    Events {
        int id PK
        string title
        enum type "ceremony / volunteer"
        text description
        datetime start_time
        datetime end_time
        int capacity
        enum status "draft / open / closed"
        datetime created_at
    }

    Registrations {
        int id PK
        int user_id FK
        int event_id FK
        enum status "confirmed / cancelled / attended"
        text note
        datetime registered_at
    }

    Lamps {
        int id PK
        int user_id FK
        enum lamp_type "光明燈 / 文昌燈 / 財神燈"
        string blessing_for_name
        date birth_date
        string address
        int amount
        enum status "pending_payment / paid / active / expired"
        string reservation_code UK "預約單編號"
        datetime valid_from
        datetime valid_until
        datetime created_at
    }

    PushLogs {
        int id PK
        int user_id FK
        string type
        text content
        datetime sent_at
    }

    Admins {
        int id PK
        string username UK
        string password_hash
        enum role "admin / viewer"
        datetime created_at
    }
```

**關鍵設計決策：**
- `Users.line_user_id` 為登入識別，LIFF 直接取得，免密碼
- `Registrations` 獨立中介表，加複合唯一索引 `(user_id, event_id)` 防重複報名
- `Lamps.status` 流程：`pending_payment`（剛預約）→ `paid`（現場繳費後廟方標記）→ `active`（生效）→ `expired`
- `Lamps.reservation_code` 當作現場核對用的預約單編號（例：`L2026-0001`）

---

## 五、專案目錄結構

```
temple_line_system/
├── app.py                  # 啟動點
├── config.py               # 設定（讀 .env）
├── requirements.txt
├── .env.example
├── .gitignore
├── migrations/             # Flask-Migrate
│
├── blueprints/
│   ├── webhook.py          # LINE Webhook
│   ├── liff.py             # 信眾 LIFF 頁面
│   └── admin.py            # 廟方後台
│
├── models/                 # SQLAlchemy models
├── services/               # 業務邏輯
├── templates/
│   ├── liff/
│   └── admin/
└── static/
```

---

## 六、環境變數範本（.env.example）

```env
FLASK_ENV=development
SECRET_KEY=change-me

DATABASE_URL=postgresql://postgres:dev@localhost:5432/temple

LINE_CHANNEL_SECRET=xxx
LINE_CHANNEL_ACCESS_TOKEN=xxx
LIFF_ID=xxx

LINE_LOGIN_CHANNEL_ID=xxx
LINE_LOGIN_CHANNEL_SECRET=xxx

ADMIN_INITIAL_USERNAME=admin
ADMIN_INITIAL_PASSWORD=change-on-first-login
```

---

## 七、安全性必做清單

- [ ] `.env` 加入 `.gitignore`
- [ ] Webhook 驗證 `X-Line-Signature`（`line-bot-sdk` 的 `WebhookHandler` 會處理）
- [ ] LIFF 取得的資料到後端再次驗證
- [ ] Admin 密碼用 bcrypt 雜湊
- [ ] 表單 CSRF token（Flask-WTF）
- [ ] 正式環境 `DEBUG=False`
- [ ] 資料庫連線走 SSL（`sslmode=require`）

---

## 八、核心風險提醒

1. **宮廟既有後台是黑盒子**：在拿到技術資料前，系統設計成獨立、未來可 API 對接
2. **長輩友善介面**：開發前就與設計端確認字級、對比規格，不要後期才加
3. **一個月時程很緊**：不做 Docker 容器化、不寫過多測試、不引入新框架；有瓶頸就砍次要功能，不砍核心
4. **學業並行**：每週記錄投入時數，連兩週遲延就重排優先順序

---

## 九、立即行動（今天內完成）

1. 去 https://developers.line.biz 申請帳號、建 Provider
2. GitHub 建 private repo `temple-line-system`
3. 去 https://zeabur.com 註冊、綁定 GitHub
4. 問宮廟：既有後台技術棧、現有活動清單、管理員人數
5. VSCode 裝好上面列的七個延伸模組

加起來不超過 2 小時，做完就能開始 Week 1。
