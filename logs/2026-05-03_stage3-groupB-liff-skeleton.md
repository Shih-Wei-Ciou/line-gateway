# 2026-05-03 | Stage 3 Group B — LIFF SDK 最小骨架

## 任務目標

驗證 LIFF SDK 整合通了。不做完整 UI，只建一個最小測試頁，
確認 Real Mode（LINE 內開）與 Fake Mode（電腦瀏覽器開）都能正確顯示。

---

## 修改檔案

### `app.py`
- 新增 `/liff/test` route
- 從 `.env` 讀取 `LIFF_ID_SUBSCRIBE`
- 若變數未設定（空字串），abort 500 並提示去設 .env
- 通過則 render `liff/test.html`，傳入 `liff_id`

### `templates/liff/test.html`（新建）
- HTML5 + Tailwind CDN（無 npm/build）
- LIFF SDK v2 CDN：`https://static.line-scdn.net/liff/edge/2/sdk.js`
- LIFF ID 用 Jinja2 插值：`liffId: '{{ liff_id }}'`
- 畫面正中央顯示「歡迎 [name]，UID: [uid]」
- 右上角 fixed 徽章：
  - `liff.isInClient() === true` → 綠點 + 「Real」
  - `liff.isInClient() === false` → 橙點 + 「Fake」（顯示 Fake User / U_FAKE_LOCAL_TEST_001）
  - init 失敗 → 橙點 + 「Fake」（顯示 Init Failed / N/A）
- 純原生 JS，無 Alpine.js、無 jQuery

---

## .env 設定

已存在，無需新增：
```
LIFF_ID_SUBSCRIBE=2009636830-jfBdo0LQ
```

---

## 驗收標準

| 測試情境 | 預期結果 |
|----------|----------|
| 電腦瀏覽器開 `/liff/test` | 「歡迎 Fake User，UID: U_FAKE_LOCAL_TEST_001」＋ 橙點「Fake」 |
| LINE App 開 `liff.line.me/{LIFF_ID}` | 「歡迎 [真實名字]，UID: [真實 UID]」＋ 綠點「Real」 |
| .env 將 LIFF_ID_SUBSCRIBE 註解掉重啟 | 訪問 `/liff/test` 回 500 並提示設 .env |

---

## Real Mode 測試步驟

1. 啟動 ngrok，取得 https URL
2. LINE Developers Console → LIFF App → Endpoint URL 改為 `https://<ngrok-url>/liff/test`
3. LINE 手機開 `https://liff.line.me/2009636830-jfBdo0LQ`
4. 確認顯示真實名字 + UID + 綠點「Real」

> 注意：ngrok 免費版每次重啟 URL 會變，須重新同步到 LINE Console。

---

## 明確排除（本次不做）

- 訂閱卡片、廟宇列表
- 任何按鈕、表單
- POST/DELETE 訂閱 API
- Alpine.js
- Stage 1/2 既有程式碼未動

---

## 下一步（待議）

- 等設計討論完後再做完整訂閱 UI（Stage 3 正式版）
- 確認 LINE UID ↔ public_user_id 綁定流程（目前尚未實作）
