# 霧峰南天宮 LINE 系統 — 開發規劃書

> 版本：v1.0
> 最後更新：2026-04-23
> 作者：Max
> 專案階段：MVP 規劃

---

## 目錄

1. [核心指導原則](#一核心指導原則)
2. [部署策略（修訂版）](#二部署策略修訂版)
3. [8 週 MVP 時程規劃](#三8-週-mvp-時程規劃)
4. [技術棧決策](#四技術棧決策)
5. [ERD 資料庫設計](#五erd-資料庫設計)
6. [專案目錄結構](#六專案目錄結構)
7. [安全性檢查清單](#七安全性檢查清單)
8. [核心風險與對策](#八核心風險與對策)
9. [學習資源](#九學習資源)

---

## 一、核心指導原則

1. **模組化 + 快速對接**：先解決廟方最痛的行政與金流問題，快速建立信任。
2. **LINE 為先**：不要求使用者下載新 App，把服務嵌進他們每天用的工具裡。
3. **Monolith First**：單一 Flask 應用搭配 blueprints 分層，不要過早拆微服務。
4. **不為未來寫程式**：單人開發，避免過度設計；真的需要擴展時再重構。
5. **既有後台當黑盒子**：在拿到廟方既有後台技術資料前，系統設計成獨立完整、未來可 API 對接。

---

## 二、部署策略（修訂版）

### 2.1 為什麼選 Zeabur 而非 Render

| 面向 | Zeabur | Render |
|------|--------|--------|
| 免費方案 | $5/月信用額度，但不支援持久化儲存 | 仍有免費層，但 PostgreSQL 90 天會被刪除 |
| 付費起步 | Dev Plan $5/月（含 $5 額度） | Starter $7/月（每服務獨立計費） |
| 語言與文件 | 中文介面、中文文件 | 英文為主 |
| 機房位置 | 台灣/亞太節點 | 美洲為主 |
| 台灣使用者延遲 | 低 | 需選日韓節點，稍高 |

### 2.2 對南天宮專案的決定性因素

- **使用者都在台灣**：廟方長輩滑手機時，延遲 50ms vs 300ms 會明顯影響體感。
- **資料庫永續性**：Render 免費 PostgreSQL 90 天會刪庫，對「真的要給人用」的系統是致命傷。Zeabur $5/月方案雖非免費，但資料不會突然消失。
- **中文支援**：遇到問題時能看中文文件、問中文社群，除錯效率加倍。

### 2.3 重新思考兩階段策略

**原規劃**：
```
Phase 1: Render/Zeabur → Phase 2: GCP/AWS
```

**修正後**：
```
Phase 1: Zeabur MVP ($5/月)
   ↓
Phase 2: 繼續 Zeabur，升級方案或多 region ($20-50/月)
   ↓
Phase 3 (可能永遠不會發生): 真有商業擴展需求時才考慮 GCP/AWS
```

**理由**：南天宮一天的交易量可能幾十筆、報名一個月幾百筆，這種流量在 Zeabur $5/月方案上可以跑好幾年。把「遲早要搬大雲」當成前提會讓你一開始就過度設計，反而拖慢 MVP 進度。

---

## 三、8 週 MVP 時程規劃

### Week 0 ── 準備週（現在就啟動，並行進行）

這些事情有外部等待時間，**不能等到前面做完才啟動**：

- [ ] 申請 LINE Pay 商家資格（最耗時，台灣審核約 2-4 週）
- [ ] 跟廟方索取既有後台技術文件（參考 §8.1 問題清單）
- [ ] 申請 LINE Developers 帳號
  - 建立 Provider
  - 開啟 Messaging API（取得 Channel Secret、Access Token）
  - 開啟 LINE Login（用來建置 LIFF）
- [ ] 建立 GitHub Repo（設 Private）
- [ ] 註冊 Zeabur 帳號（綁定 GitHub）

### Week 1-2 ── 架構奠基

**目標**：本地開發環境完整可跑、資料庫設計完成、第一個 Hello World 能通。

- [ ] 建立 Python 虛擬環境：`python -m venv venv`
- [ ] 安裝核心套件：
  ```bash
  pip install flask line-bot-sdk Flask-SQLAlchemy Flask-Migrate psycopg2-binary python-dotenv gunicorn
  ```
- [ ] Docker 跑本地 PostgreSQL（與雲端環境一致）：
  ```bash
  docker run --name temple-db -e POSTGRES_PASSWORD=dev -p 5432:5432 -d postgres:16
  ```
- [ ] 建立 Flask 專案骨架（見 §6 目錄結構）
- [ ] 設定 SQLAlchemy + Flask-Migrate
- [ ] 依 §5 ERD 實作 Models
- [ ] 執行首次 migration：`flask db init && flask db migrate && flask db upgrade`
- [ ] 基礎路由 `/` 回 Hello World，確認啟動正常

### Week 3-4 ── LINE 整合基礎

**目標**：LINE Bot 能收發訊息、LIFF 頁面能打開、使用者身分綁定完成。

- [ ] 設定 ngrok：`ngrok http 5000`
- [ ] 開發 Webhook endpoint（含 `X-Line-Signature` 簽章驗證）
- [ ] 測試 Echo Bot（收到什麼回什麼）
- [ ] 將 webhook URL 設定到 LINE Developer Console
- [ ] 設定 LIFF 應用（取得 LIFF ID）
- [ ] 開發第一個 LIFF 頁面：使用者首次訪問自動取得 LINE UID 並建立 User 記錄
- [ ] 設定 Rich Menu（先用 LINE 官方後台手動設，不寫程式）
  - 六宮格：點光明燈、添香油錢、法會報名 / 志工報名、我的福報、廟宇資訊
- [ ] 與設計師（子怡、子葳）確認長輩友善模式的字級/對比規格

### Week 5-6 ── 核心功能 MVP

**目標**：三大核心功能可操作（先做最簡單的香油錢，最後才做報名）。

#### 5.1 添香油錢（最簡單，先做）
- [ ] LIFF 頁面：金額按鈕（100/300/500/自訂）+ 匿名切換
- [ ] 後端：建立 Donation 記錄（`status=pending`）
- [ ] LINE Pay Request API 串接
- [ ] LINE Pay Confirm 回呼處理
- [ ] 成功後推一則 Flex Message 祝福給使用者

#### 5.2 點光明燈
- [ ] 燈種選擇頁（光明燈/文昌燈/財神燈）
- [ ] 疏文填寫頁（姓名、生辰、地址；自動預填 LINE 顯示名稱）
- [ ] 建立 Lamp 記錄 + 對應 Donation
- [ ] LINE Pay 流程同上
- [ ] 推播「電子疏文」Flex Message

#### 5.3 法會/志工報名
- [ ] 活動列表頁（顯示日期、名額、已報名進度條）
- [ ] 活動詳情與報名表單
- [ ] 建立 Registration 記錄
- [ ] 報名成功通知
- [ ] 活動前一天 / 前一小時的提醒推播（可用 cron job）

### Week 7 ── 廟方後台（Admin）

**目標**：廟方可以登入看到報名名單、交易紀錄、管理活動。

- [ ] Admin 登入頁（bcrypt 密碼雜湊）
- [ ] Dashboard：本週統計卡片（報名數、香油錢總額、點燈數）
- [ ] 活動管理 CRUD
- [ ] 報名名單檢視 + CSV 匯出
- [ ] 香油錢與點燈交易紀錄檢視
- [ ] 使用者列表（基本資訊、福報值）

### Week 8 ── 部署與實測

**目標**：系統上線，南天宮實地測試通過。

- [ ] 檢查 `.env` 已加入 `.gitignore`
- [ ] 程式碼推上 GitHub
- [ ] Zeabur 建立 PostgreSQL 資料庫，取得連線字串
- [ ] Zeabur 部署 Flask 專案
- [ ] 設定環境變數（LINE Token、Channel Secret、LINE Pay Key、Database URL 等）
- [ ] 執行雲端 migration：`flask db upgrade`
- [ ] LINE Webhook URL 從 ngrok 換成 Zeabur 正式網址
- [ ] 端對端測試：真實掃碼 → 點燈 → 付款 → 推播 → 後台查看
- [ ] 實地去南天宮測試，並做新手使用者觀察記錄

---

## 四、技術棧決策

| 層級 | 選擇 | 理由 |
|------|------|------|
| 後端框架 | Flask | 延續貓籠專案經驗，學習曲線低 |
| ORM | SQLAlchemy + Flask-Migrate | Alembic 底層，migration 成熟可靠 |
| 資料庫 | PostgreSQL 16 | 雲端支援好，免費額度大，語法與 MySQL 差異小 |
| 前端 | Flask + Jinja2 + htmx | 避免 SPA 複雜度，單人開發負擔輕 |
| 認證 | LINE Login（信眾）/ 自建（Admin） | LIFF 自動取得 LINE UID |
| 部署 | Zeabur | 台灣節點、中文支援、帳單簡單 |
| 本地測試 | ngrok | HTTPS tunnel，穩定好用 |
| 本地資料庫 | Docker PostgreSQL | 與雲端環境一致，避免遷移痛苦 |
| 環境管理 | python-dotenv | 標準做法 |
| LINE SDK | line-bot-sdk (官方 Python) | 官方維護 |
| LINE Pay | 官方 API 直接串 | 無好用 Python SDK，自己寫 |
| 密碼雜湊 | bcrypt | Werkzeug / Flask 內建 |
| 前端驗證 | Flask-WTF | CSRF 保護 |

---

## 五、ERD 資料庫設計

### 5.1 資料表清單

```
Users          — 信眾
Events         — 法會/志工活動
Registrations  — 報名紀錄（Users × Events 多對多中介表）
Donations      — 香油錢與點燈的金流紀錄
Lamps          — 光明燈實例（有效期間）
PushLogs       — 推播紀錄（供除錯與統計）
Admins         — 廟方管理員
```

### 5.2 關聯圖（Mermaid）

```mermaid
erDiagram
    Users ||--o{ Registrations : "報名"
    Events ||--o{ Registrations : "被報名"
    Users ||--o{ Donations : "捐獻"
    Users ||--o{ Lamps : "點燈"
    Donations ||--o| Lamps : "對應付款"
    Users ||--o{ PushLogs : "接收推播"

    Users {
        int id PK
        string line_user_id UK "LINE UID，唯一"
        string display_name
        string phone
        string email
        int merit_points "福報值"
        datetime created_at
        datetime updated_at
    }

    Events {
        int id PK
        string title
        enum type "ceremony / volunteer"
        text description
        datetime start_time
        datetime end_time
        string location
        int capacity "名額上限"
        enum status "draft / open / closed / cancelled"
        datetime created_at
    }

    Registrations {
        int id PK
        int user_id FK
        int event_id FK
        enum status "pending / confirmed / cancelled / attended"
        text note
        datetime registered_at
    }

    Donations {
        int id PK
        int user_id FK "nullable for 匿名"
        int amount
        enum payment_method "line_pay / cash / other"
        string transaction_id "LINE Pay 回傳"
        enum status "pending / success / failed / refunded"
        boolean is_anonymous
        datetime created_at
        datetime paid_at
    }

    Lamps {
        int id PK
        int user_id FK
        int donation_id FK
        enum lamp_type "光明燈 / 文昌燈 / 財神燈"
        string blessing_for_name "祈福對象姓名"
        date birth_date
        string address
        datetime valid_from
        datetime valid_until
        datetime created_at
    }

    PushLogs {
        int id PK
        int user_id FK
        enum type "registration_confirm / event_reminder / blessing"
        text content
        enum status "sent / failed"
        datetime sent_at
    }

    Admins {
        int id PK
        string username UK
        string password_hash
        enum role "admin / viewer"
        datetime last_login_at
        datetime created_at
    }
```

### 5.3 關鍵設計決策

- **Users.line_user_id 為唯一識別**：不用 email 或手機，因為 LIFF 能穩定提供 LINE UID，免密碼登入。
- **Registrations 是獨立中介表**：不用 Users/Events 直接多對多，因為需要 status、note、時間戳等額外欄位。
- **Donations 與 Lamps 分開**：Donation 是「一次付款」，Lamp 是「持續一年的燈」，生命週期不同。點燈會產生一筆 Donation + 一筆 Lamp。
- **Donations.user_id 可為 NULL**：支援匿名捐獻情境。
- **加複合唯一索引** `(user_id, event_id)` on Registrations：防止重複報名。
- **PushLogs 獨立表**：方便查詢「誰沒收到提醒」、統計推播成功率。

---

## 六、專案目錄結構

```
temple_line_system/
├── app.py                        # Flask entry point
├── config.py                     # 設定檔（讀 .env）
├── requirements.txt
├── .env.example                  # 環境變數範本（可上傳）
├── .env                          # 實際環境變數（不上傳）
├── .gitignore
├── README.md
├── migrations/                   # Flask-Migrate 產生
│
├── blueprints/
│   ├── __init__.py
│   ├── line_webhook.py           # /webhook （LINE Platform 打）
│   ├── liff_api.py               # /api/liff/* （信眾 LIFF 打）
│   └── admin.py                  # /admin/* （廟方後台）
│
├── models/
│   ├── __init__.py
│   ├── user.py
│   ├── event.py
│   ├── registration.py
│   ├── donation.py
│   ├── lamp.py
│   ├── push_log.py
│   └── admin.py
│
├── services/                     # 業務邏輯（共用）
│   ├── __init__.py
│   ├── user_service.py
│   ├── event_service.py
│   ├── donation_service.py
│   ├── linepay_service.py
│   └── notification_service.py
│
├── templates/
│   ├── liff/                     # 信眾看的頁面
│   │   ├── base.html
│   │   ├── home.html             # 福報卡首頁
│   │   ├── donate.html
│   │   ├── lamp.html
│   │   └── event_list.html
│   └── admin/                    # 廟方後台頁面
│       ├── base.html
│       ├── login.html
│       ├── dashboard.html
│       ├── events.html
│       └── registrations.html
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
└── tests/
    ├── test_webhook.py
    ├── test_donation.py
    └── test_registration.py
```

---

## 七、安全性檢查清單

### 7.1 基礎

- [ ] `.env` 加入 `.gitignore`，確認未被 push 到 GitHub
- [ ] 所有 secret 都從 `os.environ` 讀取，不寫死在程式碼
- [ ] `DEBUG=False` 在正式環境
- [ ] 資料庫連線字串走 SSL（`sslmode=require`）

### 7.2 LINE 相關

- [ ] Webhook 必須驗證 `X-Line-Signature`（`line-bot-sdk` 的 `WebhookHandler` 會幫你做）
- [ ] LINE Pay Confirm callback 要驗簽（防偽造付款通知）
- [ ] LIFF 端取得的使用者資料要在後端再次驗證（前端可被竄改）

### 7.3 Web 應用

- [ ] Admin 密碼用 bcrypt 雜湊（`werkzeug.security.generate_password_hash`）
- [ ] 表單加 CSRF token（Flask-WTF 處理）
- [ ] SQL 一律用 ORM，不拼字串（SQLAlchemy 已自動防注入）
- [ ] 使用者輸入顯示在頁面時用 Jinja2 的 autoescape（預設開啟）
- [ ] Admin session 設合理過期時間（例如 2 小時）
- [ ] Rate limiting（考慮用 Flask-Limiter）

### 7.4 資料保護

- [ ] 信眾個資（姓名、生辰、地址）僅在必要時顯示
- [ ] Admin 不同角色權限分離（admin / viewer）
- [ ] 資料庫定期備份（Zeabur 付費方案有自動備份）

---

## 八、核心風險與對策

### 8.1 風險 1：廟方既有後台是黑盒子

**對策**：系統設計成獨立完整，未來 API 對接。先寫一份問題清單，pinpoint 整合可行性：

1. 既有後台的技術棧是什麼？（PHP/Node/WordPress?）
2. 有沒有獨立資料庫？我們能存取嗎？
3. 有沒有開放 API？文件在哪？
4. 誰維護？未來還會繼續改嗎？

拿到答案前不要做任何整合假設。

### 8.2 風險 2：LINE Pay 商家審核耗時

**對策**：Week 0 就啟動申請，不等系統寫完。若 Week 5-6 還沒下來：
- 香油錢功能先用 **沙盒（sandbox）環境** 開發測試
- 退路方案：先做「顯示轉帳帳號 + 匯款後自行回報」的土砲版本

### 8.3 風險 3：長輩友善介面規格落差

**對策**：
- 開發前先跟設計師確認兩套 design tokens（一般 14px / 友善 18px 起跳）
- 主動告知設計師 LIFF 技術底線：CSS 動畫可以、3D 不建議、全螢幕轉場不穩
- 請設計師提供靜態 PNG/SVG 即可，不要複雜動畫

### 8.4 風險 4：單人開發容易過度設計

**對策**：
- 不做 Docker 容器化（Zeabur 自動處理）
- 不寫測試直到核心功能穩定（只對金流邏輯寫測試）
- 不用 React/Vue（Jinja2 + htmx 夠用）
- 不為「未來 10 間廟」設計多租戶（只服務南天宮）

### 8.5 風險 5：學業與專案並行

**對策**：
- 每週記錄實際投入時數，若連兩週遲延就重新排序優先項
- 週計劃不要塞滿，保留 30% 緩衝時間
- 貓籠與碩論的交付時程先畫出來，LINE 專案繞開關鍵期

---

## 九、學習資源

### 9.1 LINE 開發

- **LINE Developers 官方文件（繁中）**：https://developers.line.biz/zh-hant/
- **LINE Pay Developers（繁中）**：https://pay.line.me/tw/developers
- **line-bot-sdk-python GitHub Examples**：官方範例最值得看
- **iT 邦幫忙「LINE Bot Python」鐵人賽系列**：台灣工程師實戰記錄

### 9.2 Flask 深入

- Miguel Grinberg《Flask Web Development》（俗稱 Flask 聖經）
- Miguel Grinberg《Flask Mega-Tutorial》線上教學
- Flask-Migrate 官方文件：https://flask-migrate.readthedocs.io/

### 9.3 Zeabur

- 官方 Flask 部署指南：https://zeabur.com/docs/en-US/guides/python/flask
- 免費方案說明：https://zeabur.com/docs/en-US/pricing/free-plan

### 9.4 架構思考

- GitHub 專案 `System Design Primer`（有中文翻譯）
- iT 邦幫忙「後端架構」鐵人賽（特別是電商或訂閱系統）

---

## 附錄 A：環境變數範本（.env.example）

```env
# Flask
FLASK_ENV=development
SECRET_KEY=change-me-in-production

# Database
DATABASE_URL=postgresql://postgres:dev@localhost:5432/temple

# LINE Messaging API
LINE_CHANNEL_SECRET=xxx
LINE_CHANNEL_ACCESS_TOKEN=xxx

# LINE LIFF
LIFF_ID=xxx

# LINE Login
LINE_LOGIN_CHANNEL_ID=xxx
LINE_LOGIN_CHANNEL_SECRET=xxx

# LINE Pay
LINEPAY_CHANNEL_ID=xxx
LINEPAY_CHANNEL_SECRET=xxx
LINEPAY_API_URL=https://sandbox-api-pay.line.me  # 測試環境

# Admin
ADMIN_INITIAL_USERNAME=admin
ADMIN_INITIAL_PASSWORD=change-me-on-first-login
```

---

## 附錄 B：本週立即行動

照著上面 Week 0 並行做這五件事：

1. ⏰ 去南天宮問 LINE Pay 商家申請進度，若還沒辦就今天辦
2. 📄 寫信/訊息給廟方既有後台開發者（問四個問題，見 §8.1）
3. 🔑 去 https://developers.line.biz 申請帳號、建 Provider
4. 📦 GitHub 建 private repo `temple-line-system`
5. ☁️ https://zeabur.com 註冊帳號、綁定 GitHub

五件事全部加起來不超過 2 小時，做完這週就能開始 Week 1 的技術工作。

---

*本文件為活文件，會隨專案進展更新。建議放在 GitHub repo 的 `docs/` 資料夾內，與程式碼一起版控。*
