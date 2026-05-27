# LINE Gateway

LINE Bot + LIFF 對接層，橋接 LINE 用戶與廟宇活動平台（TEP）。

## 技術棧

- Python 3.12 / Flask 3.0
- PostgreSQL 16
- SQLAlchemy + Flask-Migrate
- LINE Bot SDK v3 / LIFF SDK

## 本機快速啟動

### 前置需求

- Python 3.12+
- PostgreSQL 16（本機或 Docker）
- ngrok（LINE Webhook 需要 HTTPS）

### 步驟

```bash
# 1. clone 後進入專案根目錄
cd 奕守long

# 2. 建立虛擬環境並安裝依賴
python -m venv .venv
source .venv/Scripts/activate   # Windows Git Bash
# 或 .venv\Scripts\activate.bat  # Windows CMD

pip install -r requirements.txt

# 3. 設定環境變數
cp .env.example .env
# 用編輯器打開 .env，填入 LINE_CHANNEL_SECRET / LINE_CHANNEL_ACCESS_TOKEN
# 和 LIFF_ID_SUBSCRIBE（至少這三個才能完整跑通）

# 4. 建立資料庫並跑 migration
flask db upgrade

# 5. 啟動開發伺服器（port 5002）
python app.py

# 6. 另開一個終端，啟動 ngrok 把 5002 暴露出去
ngrok http 5002
```

ngrok 會印出一個 `https://xxxx.ngrok-free.app` 的 URL，
把這個 URL + `/webhook` 貼到 LINE Developers → Messaging API → Webhook URL。

### 確認服務正常

```bash
curl http://localhost:5002/
# → LINE Gateway is running!
```

## API 端點（Stage 3）

所有 `/api/liff/*` 端點都需要帶 `X-Line-Uid` header（開發用；Stage 8 換成 LIFF access token 驗證）。

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/liff/me` | 取得當前用戶資料 + 有效訂閱清單 |
| POST | `/api/liff/subscriptions` | 訂閱廟宇（body: `{"tep_temple_id": 1}`） |
| DELETE | `/api/liff/subscriptions/<id>` | 取消訂閱 |

### 快速 curl 測試

```bash
UID="U8a2e2fb7984278f5485a2b2aea1fd7a4"

# 查我的訂閱
curl http://localhost:5002/api/liff/me -H "X-Line-Uid: $UID"

# 訂閱 temple 1
curl -X POST http://localhost:5002/api/liff/subscriptions \
  -H "Content-Type: application/json" \
  -H "X-Line-Uid: $UID" \
  -d '{"tep_temple_id": 1}'

# 取消訂閱（把 1 換成實際 id）
curl -X DELETE http://localhost:5002/api/liff/subscriptions/1 \
  -H "X-Line-Uid: $UID"
```

## 專案結構

```
├── app.py                  # Flask app factory
├── extensions.py           # db / migrate 初始化
├── models/
│   ├── line_user.py        # LINE 使用者主表
│   ├── subscription.py     # 訂閱關係表
│   ├── action_log.py       # 操作稽核記錄
│   └── push_log.py         # 推播記錄
├── blueprints/
│   ├── webhook.py          # POST /webhook（LINE 事件）
│   └── liff_api.py         # GET|POST|DELETE /api/liff/*
├── services/
│   ├── line_user_service.py    # follow / unfollow 邏輯
│   └── subscription_service.py # 訂閱 CRUD 邏輯
├── templates/liff/         # LIFF 前端頁面
├── migrations/             # Flask-Migrate 版本
└── .env.example            # 環境變數範本
```

## 常見問題

**`flask db upgrade` 失敗**
確認 PostgreSQL 正在執行，且 `.env` 的 `DATABASE_URL` 指向正確的 host/port/dbname。

**LINE Webhook 驗證失敗（400）**
`LINE_CHANNEL_SECRET` 必須與 LINE Developers 上的 Messaging API channel secret 完全一致。

**ngrok session 過期**
免費版 ngrok 每次重啟 URL 會變，記得重新貼到 LINE Developers Webhook URL 設定。

## Rich Menu 管理

### 首次建立 / 更新 Rich Menu

```bash
# 1. 確認 .env 設定好 LINE_CHANNEL_ACCESS_TOKEN 和 WEBAPP_BASE_URL
# 2. 執行
python scripts/setup_rich_menu.py --confirm
```

腳本會做的事：
1. 用 PIL 生成 main_v1.png
2. 建立新的 Rich Menu
3. 上傳圖片
4. 設為預設
5. 刪除所有舊的 Rich Menu

### 使用者看不到新 menu 怎麼辦？

LINE app 會 cache rich menu。請使用者：
1. 封鎖官方帳號 → 解除封鎖
2. 或 LINE app 重啟

### 之後設計師交稿後

把設計師給的圖存到 `static/richmenu/main_v2.png`，修改 `setup_rich_menu.py` 中的 IMAGE_PATH 變數，重跑腳本。

## Stage 進度

| Stage | 內容 | 狀態 |
|-------|------|------|
| 0 | 環境建置 | ✅ |
| 1 | LINE Bot webhook 基本連線 | ✅ |
| 2 | 用戶識別 + DB（follow/unfollow） | ✅ |
| 3 | LIFF + 訂閱 API | ✅ |
| 4–8 | 報名流程、推播、個人頁、上線 hardening | 待開發 |
