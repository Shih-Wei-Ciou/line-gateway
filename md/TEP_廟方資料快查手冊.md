# TEP 廟方資料快查手冊

> 來源：`tep-master/backend` 原始碼直接萃取，供 Gateway 開發對照用。
> 實作時遇到問題先查這份，不用先問學長。

---

## 目錄

1. [資料庫 Schema](#1-資料庫-schema)
2. [API 端點速查](#2-api-端點速查)
3. [Gateway 最常用的 6 個端點](#3-gateway-最常用的-6-個端點)
4. [欄位對照：TEP camelCase ↔ Gateway snake_case](#4-欄位對照tep-camelcase--gateway-snake_case)
5. [活動狀態機](#5-活動狀態機)
6. [常見錯誤與對應 HTTP 狀態碼](#6-常見錯誤與對應-http-狀態碼)
7. [已知 Schema 不一致（地雷區）](#7-已知-schema-不一致地雷區)

---

## 1. 資料庫 Schema

### 1-1 temples（廟宇主表）

| 欄位 | 型別 | 必填 | 備註 |
|------|------|------|------|
| id | Integer | ✓ | PK |
| name | VARCHAR(100) | ✓ | 廟宇名稱，有索引 |
| address | VARCHAR(200) | | |
| latitude | NUMERIC(10,8) | | 緯度 |
| longitude | NUMERIC(11,8) | | 經度 |
| main_deity | VARCHAR(50) | | 主祀神明 |
| description | TEXT | | |
| images | JSON | | 照片陣列 |
| phone | VARCHAR(20) | | |
| email | VARCHAR(100) | | |
| website | VARCHAR(200) | | |
| opening_hours | JSON | | 開放時間 |
| checkin_radius | Integer | ✓ | 預設 100（公尺）|
| checkin_merit_points | Integer | ✓ | 預設 10（簽到得分）|
| nfc_uid | VARCHAR(50) | | Unique，NFC 標籤 |
| is_active | Boolean | ✓ | 預設 True |
| created_at | DateTime | ✓ | |
| updated_at | DateTime | | auto-update |

---

### 1-2 temple_admin_users（廟方後台帳號）

> 廟方登入 TEP 後台用的帳號，一間廟對應一個帳號。

| 欄位 | 型別 | 必填 | 備註 |
|------|------|------|------|
| id | Integer | ✓ | PK |
| name | VARCHAR(100) | ✓ | 管理員姓名 |
| email | VARCHAR(120) | ✓ | Unique，登入用 |
| password_hash | VARCHAR(255) | ✓ | Werkzeug 雜湊 |
| temple_id | Integer | ✓ | FK → temples.id |
| is_active | Boolean | ✓ | 預設 True |
| created_at | DateTime | ✓ | |
| last_login_at | DateTime | | |

登入方式：
```
POST /api/auth/login
{"email": "...", "password": "...", "login_type": "temple_admin"}
→ {"token": "eyJ...", "refresh_token": "...", "account_type": "temple_admin"}
```

---

### 1-3 temple_events（廟宇活動）

| 欄位 | 型別 | 必填 | 備註 |
|------|------|------|------|
| id | Integer | ✓ | PK |
| temple_id | Integer | ✓ | FK → temples.id |
| title | VARCHAR(200) | ✓ | 活動名稱 |
| description | TEXT | ✓ | |
| location | VARCHAR(200) | ✓ | 地點（非地址，填「大殿」等即可）|
| start_at | DateTime | ✓ | 活動開始時間 |
| end_at | DateTime | ✓ | 活動結束時間 |
| signup_end_at | DateTime | ✓ | 報名截止（必須 ≤ start_at）|
| capacity | Integer | ✓ | 名額（0 = 不限）|
| fee | DECIMAL(10,2) | ✓ | 預設 0.00 |
| cover_image_url | VARCHAR(500) | | |
| status | VARCHAR(20) | ✓ | draft / published / closed / canceled |
| created_by | Integer | ✓ | FK → users.id |
| created_at | DateTime | ✓ | |
| updated_at | DateTime | | |

**狀態機限制：**
- `signup_end_at ≤ start_at`（否則 POST 時 400）
- `start_at < end_at`
- `capacity ≥ 1`（0 表示不限，但建立時仍要傳正整數）
- `fee ≥ 0`

---

### 1-4 event_registrations（活動報名）

| 欄位 | 型別 | 必填 | 備註 |
|------|------|------|------|
| id | Integer | ✓ | PK |
| event_id | Integer | ✓ | FK → temple_events.id |
| user_id | Integer | | FK → users.id（允許訪客報名）|
| **line_user_id** | VARCHAR(50) | | **LINE UID，Gateway 報名時帶這個** |
| name | VARCHAR(100) | ✓ | 報名人姓名 |
| phone | VARCHAR(20) | ✓ | 聯絡電話 |
| email | VARCHAR(120) | ✓ | 聯絡 email（⚠️ 欄位必填但 API 允許空字串）|
| people_count | Integer | ✓ | 預設 1，最多 20 |
| notes | TEXT | | 備註 |
| status | VARCHAR(20) | ✓ | registered / canceled / waitlist |
| registered_at | DateTime | ✓ | |
| canceled_at | DateTime | | |

> ⚠️ `email` 在 migration 標記 NOT NULL，但 `public_event.py` 實作用 `.get('email', '').strip()`，空字串可以通過。

---

### 1-5 temple_admins（廟方角色表，gateway 不直接用）

| 欄位 | 備註 |
|------|------|
| role | owner / manager / staff |
| permissions | JSON，控制各功能存取 |

---

## 2. API 端點速查

### 公開端點（不需 JWT）

| Method | Path | 說明 |
|--------|------|------|
| GET | `/api/temples/` | 廟宇列表（?is_active=true&search=&limit=50）|
| GET | `/api/temples/<id>` | 廟宇詳情 |
| GET | `/api/temples/nearby` | 附近廟宇（?latitude=&longitude=&radius=10）|
| GET | `/api/public/temples/<temple_id>/events` | 該廟已公開且報名中的活動 |
| GET | `/api/public/events/<event_id>` | 單一活動詳情（含 canRegister）|
| POST | `/api/public/events/<event_id>/register` | 報名（帶 lineUserId）|
| GET | `/api/public/registrations` | 我的報名（?line_uid=Uxxxxx）|
| PUT | `/api/public/registrations/<id>/cancel` | 取消報名（body 帶 lineUserId 驗身）|

### 需要 JWT 的端點（廟方後台用，Gateway 目前不呼叫）

| Method | Path | 說明 |
|--------|------|------|
| POST | `/api/auth/login` | 廟方帳號登入 |
| POST | `/api/temple-admin/events/` | 建立活動 |
| POST | `/api/temple-admin/events/<id>/publish/` | 發布活動 |
| GET | `/api/temple-admin/events/<id>/registrations/` | 報名名單 |

---

## 3. Gateway 最常用的 6 個端點

### 3-1 取得廟宇資訊
```
GET /api/temples/<temple_id>
```
回傳（data 欄位）：
```json
{
  "id": 1,
  "name": "文武廟",
  "address": "台北市...",
  "main_deity": "文昌帝君",
  "phone": "02-1234-5678",
  "is_active": true
}
```

---

### 3-2 取得廟宇活動列表
```
GET /api/public/temples/<temple_id>/events
```
只回傳 `published` 且 `signup_end_at > now` 的活動。
回傳（data.events 陣列）：
```json
[{
  "id": 42,
  "title": "新春祈福法會",
  "location": "大殿",
  "startAt": "2026-02-01T09:00:00",
  "endAt": "2026-02-01T12:00:00",
  "signupEndAt": "2026-01-25T23:59:00",
  "capacity": 100,
  "fee": 0,
  "coverImageUrl": "https://...",
  "status": "published",
  "registeredCount": 23,
  "totalPeople": 30,
  "remainingCapacity": 70
}]
```

---

### 3-3 取得單一活動詳情
```
GET /api/public/events/<event_id>
```
比列表多一個欄位：
```json
{
  "canRegister": true   ← 是否還能報名（已綜合 status + 截止 + 容量）
}
```

---

### 3-4 活動報名
```
POST /api/public/events/<event_id>/register
Content-Type: application/json

{
  "name":        "邱識瑋",       ← 必填
  "phone":       "0912345678",  ← 必填
  "lineUserId":  "Uxxxxxxxx",   ← 選填（填了才能查重複報名）
  "email":       "",            ← 選填（空字串可以）
  "peopleCount": 1,             ← 選填，預設 1，最多 20
  "notes":       ""             ← 選填
}
```
成功回傳（201）：
```json
{
  "id": 7,
  "eventId": 42,
  "name": "邱識瑋",
  "phone": "0912345678",
  "lineUserId": "Uxxxxxxxx",
  "status": "registered",
  "registeredAt": "2026-05-03T10:00:00"
}
```
常見錯誤：
- 400 `此活動未開放報名`（status != published）
- 400 `報名已截止`
- 400 `名額不足，目前剩餘 X 名`
- 400 `您已報名此活動`（同一 lineUserId 重複）
- 400 `人數必須在 1-20 之間`

---

### 3-5 查詢個人報名
```
GET /api/public/registrations?line_uid=Uxxxxxxxx
```
回傳（data.registrations 陣列）：
```json
[{
  "id": 7,
  "event_id": 42,
  "name": "邱識瑋",
  "status": "registered",
  "event": {
    "id": 42,
    "title": "新春祈福法會",
    "startAt": "2026-02-01T09:00:00",
    ...
  }
}]
```

---

### 3-6 取消報名
```
PUT /api/public/registrations/<reg_id>/cancel
Content-Type: application/json

{
  "lineUserId": "Uxxxxxxxx"   ← 用來驗身，不符合 → 403
}
```
成功回傳（200）：
```json
{
  "id": 7,
  "status": "canceled",
  "canceledAt": "2026-05-03T11:00:00"
}
```
錯誤：
- 404 `報名紀錄不存在`
- 403 `無權取消此報名`
- 400 `此報名已取消`

---

## 4. 欄位對照：TEP camelCase ↔ Gateway snake_case

TEP API 回傳 camelCase，gateway 內部用 snake_case。`flex_builder.py` 的 `_ev()` 函式已處理這個轉換，但手動查的時候用這張表：

| TEP 回傳（camelCase） | Gateway 內部（snake_case） | 說明 |
|----------------------|--------------------------|------|
| `templeId` | `temple_id` | |
| `startAt` | `start_at` | ISO 8601 字串 |
| `endAt` | `end_at` | |
| `signupEndAt` | `signup_end_at` | |
| `coverImageUrl` | `cover_image_url` | |
| `registeredCount` | `registered_count` | |
| `remainingCapacity` | `remaining_capacity` | |
| `canRegister` | `can_register` | |
| `totalPeople` | `total_people` | |
| `lineUserId` | `line_user_id` | 報名時送出用 camelCase |
| `peopleCount` | `people_count` | |

---

## 5. 活動狀態機

```
建立 → draft
         ↓ publish
      published ──────────────────┐
         ↓ close (提前關閉報名)    │ cancel
       closed                    │
         ↓ (只能 cancel)          │
       canceled ←────────────────┘

注意：不能從任何狀態回到 draft
      不能跳過狀態（draft 不能直接 cancel，必須先 publish）
```

---

## 6. 常見錯誤與對應 HTTP 狀態碼

| 狀況 | HTTP | TEP 訊息（繁中）|
|------|------|---------------|
| 活動不存在 | 404 | 活動不存在 |
| 活動未公開 | 404 | 此活動尚未公開 |
| 未開放報名 | 400 | 此活動未開放報名 |
| 報名已截止 | 400 | 報名已截止 |
| 名額不足 | 400 | 名額不足，目前剩餘 X 名 |
| 重複報名 | 400 | 您已報名此活動 |
| 人數超限 | 400 | 人數必須在 1-20 之間 |
| 缺少姓名/電話 | 400 | 姓名和電話為必填 |
| 無權取消 | 403 | 無權取消此報名 |
| 已取消過 | 400 | 此報名已取消 |
| TEP 連線失敗 | 0（ConnectionError）| — |
| TEP 5xx | 500-504 | 依錯誤而定 |

---

## 7. 已知 Schema 不一致（地雷區）

| 問題 | 影響 | 處理方式 |
|------|------|---------|
| `event_registrations` migration 缺少 `people_count` 和 `line_user_id` 欄位，但 model 有 | 若用 `flask db upgrade` 建表，這兩欄不存在 | 學長那邊應已手動補過；若報名失敗先查這個 |
| `email` 欄位在 migration 是 NOT NULL，但 API 允許空字串 | POST 報名時空字串可通過 | Gateway 傳 `""` 即可，不要傳 `null` |
| 活動列表 API 路徑與 swagger 不同 | 實際路徑是 `/api/public/temples/<id>/events`，不是 `/api/public/events` | 以原始碼為準 |
| TEP `TempleAdmin`（角色表）與 `TempleAdminUser`（登入帳號）名稱相近 | 搞混會找不到資料 | 登入帳號查 `temple_admin_users`；角色權限查 `temple_admins` |
