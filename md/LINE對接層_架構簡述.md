# LINE 對接層 — 系統架構簡述

| | |
|---|---|
| 版本 | v2.1（簡短版） |
| 用途 | 跨團隊對齊用 |
| 時程 | 4 週 MVP |

---

## 1. 一句話定位

> **本系統是 LINE 端的對接層，把 LINE 使用者的互動轉接到既有的 TEP 廟宇後端。本系統不重建任何 TEP 已有的功能。**

---

## 2. 職責分工

| | TEP（學長） | LINE 對接層（我） |
|---|---|---|
| 廟宇/活動/報名資料 | ✅ 真實資料擁有者 | ❌ 不重建 |
| 廟方管理後台 | ✅ 廟方使用 | ❌ 不做 |
| LINE 訊息收發 | ❌ 移交 | ✅ **完全接管** |
| LINE 推播觸發 | ❌ 移交 | ✅ **完全接管** |
| Rich Menu / LIFF | ❌ 不做 | ✅ |
| 訂閱關係（多對多） | ❌ 沒有 | ✅ |

**重點：TEP 既有的 LINE 整合（§11）完全由本系統取代。所有 LINE 通訊統一從這裡出去、進來。**

---

## 3. 角色與資料流

```
信眾 ──── LINE App ──── LINE 對接層 ──── HTTP API ──── TEP 後端
                          (我做)                       (學長做)
                              │                            ▲
                              │                            │
                              ▼                            │
                          輕量 DB                          │
                          (LINE 端資訊)                    │
                                                           │
廟方管理員 ──────── TEP 管理後台 ───────────────────────────┘
                    (學長做的網頁)
```

**雙向流**：
- 廟方在 TEP 後台建活動 → TEP 呼叫對接層 → 對接層推 Flex Message 給訂閱者
- 信眾在 LINE 按按鈕 → 對接層收到 → 對接層呼叫 TEP API 寫入報名

---

## 4. 核心設計決策

### 4.1 資料庫只記 LINE 端獨有的東西

本系統 4 張表：

| 表 | 用途 |
|---|---|
| `line_users` | LINE 使用者（含補填的姓名電話） |
| `subscriptions` | 多對多訂閱關係（LINE UID ↔ TEP temple_id） |
| `action_logs` | 操作流水紀錄（debug 用） |
| `push_logs` | 推播紀錄 |

**沒有** `events` `temples` `registrations` 表 — 這些都在 TEP。

### 4.2 多對多訂閱

一位信眾可訂閱多間廟，一間廟可有多位訂閱者。**訂閱關係只在本系統 DB**，TEP 不知道訂閱機制。

### 4.3 身分簡化

只用 LINE UID 當識別。不綁 TEP 的 `public_users` 帳號。

### 4.4 報名資料收集（A 案定案）

TEP 報名 API 需要姓名電話。**首次報名前**，本系統跳 LIFF 表單收集，存進 `line_users`。後續報名直接從 DB 取用。

### 4.5 單一 LINE OA

一個官方帳號服務全平台。信眾在 LIFF 內選訂閱哪些廟。

---

## 5. 系統間 API 對接

### 5.1 TEP → 本系統（推播觸發）

TEP 後台「發送 LINE 推播」按鈕呼叫：
```
POST /internal/push/event
Body: { event_id, temple_id }
Header: X-API-Key: <internal_key>
```

### 5.2 本系統 → TEP（寫入報名）

```
POST /api/public/events/:id/register
Body: { name, phone, lineUserId, peopleCount, notes }
```

### 5.3 本系統 → TEP（拉取資料）

```
GET /api/temples              # 給訂閱頁顯示
GET /api/temples/:id/events   # 給「我的關注」顯示活動
GET /api/public/registrations?line_uid=  # 我的報名
```

---

## 6. 學長要配合的事

**最小變動清單：**

1. TEP 後台「活動編輯頁」加一顆「發送 LINE 推播」按鈕，按下呼叫本系統 `/internal/push/event`
2. **停用** TEP 既有的 LINE 廣播功能（§11.4），所有 LINE 通訊由本系統取代
3. 提供（或新增）取消報名的公開 API
4. 確認活動詳情有公開讀取端點

---

## 7. 技術棧

| 類別 | 選擇 |
|---|---|
| 後端 | Python + Flask |
| 資料庫 | PostgreSQL |
| 部署 | Zeabur |
| LIFF 前端 | Jinja2 + Tailwind + Alpine.js |

---

## 8. 範圍限制

**本期不做：**
- 金流（LINE Pay）
- 打卡、平安符、商品兌換、功德值（這些 TEP 有，但本期不接 LINE）
- 多 OA
- 廟方後台 UI（TEP 已有）

---

## 9. 時程

| 週 | 主軸 |
|---|---|
| Week 0 | 環境齊備（LINE 申請、本機跑起 TEP） |
| Week 1 | LINE 連線通、使用者建立、LIFF 跑起 |
| Week 2 | 訂閱機制、推播觸發 |
| Week 3 | 整合 TEP、雙向流跑通 |
| Week 4 | 取消功能、部署、測試 |

---

*詳細施工計畫見《LINE 對接層 系統架構書 v2》分階段測試順序表。*
