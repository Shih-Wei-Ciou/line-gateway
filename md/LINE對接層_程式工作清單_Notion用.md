# LINE對接層_程式工作清單_Notion用

# LINE 對接層 — 程式開發工作清單

> **負責範圍**：僅程式開發
**不負責**：內容撰寫、設計稿、廟方訪談、攝影、文案
**使用方式**：可直接複製到 Notion（支援表格、checkbox、code block）
> 

---

## 角色聲明

本文件僅列出**程式開發**相關工作。以下項目**不在本文件範圍**，需由其他團隊成員負責：

| 非程式工作 | 應由誰負責 |
| --- | --- |
| 參拜路線內容（站點順序、文案、照片） | 廟方訪談 + 內容組 |
| 神明介紹文案、祈禱用詞 | 內容組 + 廟方確認 |
| 設施資訊（停車、廁所位置） | 廟方提供 |
| 願望分類與對應神明 | 內容組 + 廟方諮詢 |
| LIFF 頁面視覺設計稿 | 設計組 |
| Rich Menu 圖檔 | 設計組 |
| Flex Message 視覺設計 | 設計組 |
| 操作說明文件給廟方 | 文件組 |

**程式設計者收到的應該是**：完整內容（文字、圖檔）+ 視覺設計稿。本工作清單假設這些素材會在對應階段前準備好。

---

## 功能總覽與優先順序

### 全部功能列表（最終藍圖）

| # | 功能 | 階段 | 程式複雜度 |
| --- | --- | --- | --- |
| F1 | 信眾加入 OA + 身分建立 | P0 | 低 |
| F2 | Rich Menu 主選單 | P0 | 低 |
| F3 | 廟宇訂閱機制（多對多） | P0 | 中 |
| F4 | 補充個資（姓名電話） | P0 | 低 |
| F5 | 活動推播（TEP 觸發） | P1 | 中 |
| F6 | Flex Message 報名互動 | P1 | 中 |
| F7 | 我的報名查詢 + 取消 | P1 | 中 |
| F8 | 行為追蹤基礎建設 | P1 | 中 |
| F9 | 參拜路線導覽 | P2 | 中 |
| F10 | 神明介紹與祈禱用詞 | P2 | 低 |
| F11 | 現場設施查詢 | P2 | 低 |
| F12 | 願望推薦廟宇 | P3 | 中 |
| F13 | 廟方數據後台（內容管理） | P3 | 中 |
| F14 | 廟方數據後台（統計圖表） | P3 | 中 |

### 優先順序定義

- **P0（基礎）**：所有後續功能的前提，不做就什麼都不能做
- **P1（核心）**：證明系統價值的關鍵閉環（與 TEP 整合）
- **P2（擴充）**：增加信眾黏著度的內容功能
- **P3（價值放大）**：給廟方真實業務價值的數據功能

---

## 階段對應時程（建議）

| 時程 | 階段 | 涵蓋功能 |
| --- | --- | --- |
| Week 0 | 準備 | 環境齊備 |
| Week 1-2 | P0 | F1-F4（基礎建設） |
| Week 3-4 | P1 | F5-F8（核心閉環） |
| Week 5-6 | P2 | F9-F11（內容功能） |
| Week 7-8 | P3 | F12-F14（數據價值） |

⚠️ **若時程壓縮為 4 週**：只做 P0 + P1，P2-P3 進入 V2。

---

## P0 基礎建設

### F1：信眾加入 OA + 身分建立

**需要的非程式素材**
- LINE Official Account 頭像、簡介
- 歡迎訊息文案

**程式工作細項**
- [ ] 建立 `line_users` model（id, line_uid, display_name, picture_url, follow_status, followed_at, last_seen_at）
- [ ] 撰寫 `/webhook/line` 端點骨架
- [ ] 實作 X-Line-Signature 簽章驗證
- [ ] 實作 follow event handler（寫入/更新 line_users）
- [ ] 實作 unfollow event handler（更新 follow_status）
- [ ] 實作 message event handler（先做 echo 測試）
- [ ] 實作歡迎訊息推播（follow 後推送）
- [ ] 寫 unit test：簽章驗證、follow/unfollow 邏輯

**驗收**
- 自己加 OA → DB 看到 line_users 新增一筆
- 取消加回 → followed_at 更新、status=active
- curl 假打 webhook 沒簽章 → 被擋

---

### F2：Rich Menu 主選單

**需要的非程式素材**
- Rich Menu 設計圖（六宮格圖檔，2500x1686 px）
- 每個格子的 icon 與功能名稱

**程式工作細項**
- [ ] 撰寫 Rich Menu 上傳腳本（`scripts/setup_rich_menu.py`）
- [ ] 定義六個格子的 action：訂閱廟宇、我的報名、參拜導覽、神明指南、設施資訊、廟宇資訊
- [ ] 設定為預設 Rich Menu（套用到所有使用者）
- [ ] 後續功能上線前先用「即將推出」訊息頂著

**驗收**
- LINE 內看到 Rich Menu 顯示
- 點任一格觸發對應 action

---

### F3：廟宇訂閱機制（多對多）

**需要的非程式素材**
- 訂閱頁 LIFF 視覺設計稿
- TEP 的廟宇列表 API 規格（向學長確認）

**程式工作細項**
- [ ] 建立 `subscriptions` model（id, line_user_id, tep_temple_id, is_active, subscribed_at）
- [ ] 加複合唯一索引 `(line_user_id, tep_temple_id)`
- [ ] 建立 LIFF 應用：訂閱頁
- [ ] 建立 `services/tep_client.py`，封裝 TEP API 呼叫
- [ ] 實作 `tep_client.list_temples()` 拉廟宇清單
- [ ] 開發 `/liff/subscribe` 頁面（HTML + Tailwind + Alpine.js）
- [ ] 開發 `GET /api/liff/me` 端點（回傳當前訂閱狀態）
- [ ] 開發 `POST /api/liff/subscriptions` 端點（新增訂閱）
- [ ] 開發 `DELETE /api/liff/subscriptions/:temple_id` 端點（取消訂閱）
- [ ] 實作 LIFF SDK 整合（`liff.init`、`liff.getProfile`）
- [ ] 處理重複訂閱（不報錯，更新 is_active）

**驗收**
- LIFF 頁顯示所有 TEP 廟宇
- 點選後資料庫看到訂閱記錄
- 重新整理頁面，已訂閱的顯示「已訂閱」狀態
- 取消訂閱後 is_active=false

---

### F4：補充個資（姓名電話）

**需要的非程式素材**
- 補資料頁 LIFF 設計稿
- 提示文案（為什麼需要這些資料）

**程式工作細項**
- [ ] `line_users` 加入 `phone`、`real_name` 欄位（migration）
- [ ] 建立 LIFF 應用：補資料頁
- [ ] 開發 `/liff/profile` 頁面
- [ ] 開發 `POST /api/liff/profile` 端點
- [ ] 表單驗證（姓名 1-20 字、電話格式）
- [ ] 寫入 line_users
- [ ] 提供「下次報名前先檢查資料是否完整」的 helper function

**驗收**
- 表單能填寫送出
- DB 看到 phone、real_name 欄位被填
- 沒填必填欄位無法送出

---

## P1 核心閉環

### F5：活動推播（TEP 觸發）

**需要的非程式素材**
- 與學長談妥 TEP 端的「LINE 推播」按鈕實作
- Flex Message 設計稿（活動邀請卡）

**程式工作細項**
- [ ] 建立 `push_logs` model（id, line_user_id, tep_event_id, flex_payload, status, sent_at, error_message）
- [ ] 開發 `POST /internal/push/event` 端點
- [ ] 實作 X-API-Key 驗證 middleware
- [ ] 實作 `tep_client.get_event(temple_id, event_id)` 拉活動詳情
- [ ] 實作 `services/push_service.py` 推播服務
- [ ] 撰寫 `services/flex_builder.py` 組 Flex Message
- [ ] 實作活動邀請卡 Flex 模板
- [ ] 查訂閱者邏輯（subscriptions WHERE tep_temple_id=? AND is_active）
- [ ] 批次推播實作（用 LINE multicast API，每批最多 500 人）
- [ ] 推播結果寫入 push_logs
- [ ] 失敗重試機制（最多 3 次）
- [ ] 推播 rate limit 處理

**驗收**
- curl 模擬 TEP 觸發推播 → 自己 LINE 收到 Flex Message
- push_logs 看到完整紀錄
- 故意關掉 LINE → 重試機制啟動

---

### F6：Flex Message 報名互動

**需要的非程式素材**
- Flex Message 按鈕視覺設計
- 確認訊息文案

**程式工作細項**
- [ ] 設計 Postback Data 規格：`action=register&event_id=X&response=yes/no`
- [ ] 實作 postback event handler
- [ ] 解析 postback data（urllib.parse）
- [ ] 建立 `action_logs` model
- [ ] 實作報名前置檢查（line_users.phone 存在嗎？沒有的話導去 F4）
- [ ] 實作 `tep_client.register_event(event_id, name, phone, line_user_id)`
- [ ] 失敗處理（TEP 回 400/500 怎麼辦）
- [ ] 推送確認訊息給使用者
- [ ] 推送錯誤訊息（友善文字，不暴露技術細節）

**驗收**
- 在 LINE 按「我要參加」→ TEP 資料庫看到報名
- action_logs 完整紀錄請求與回應
- 沒填過 profile 的使用者會被導去填表
- 故意關掉 TEP → 使用者看到「系統忙碌請稍後」

---

### F7：我的報名查詢 + 取消

**需要的非程式素材**
- 我的報名 LIFF 設計稿
- 與學長確認 TEP 取消報名的 API 規格

**程式工作細項**
- [ ] 建立 LIFF 應用：我的報名
- [ ] 開發 `/liff/my-registrations` 頁面
- [ ] 實作 `tep_client.get_user_registrations(line_uid)`
- [ ] 開發 `GET /api/liff/my-registrations` 端點（轉發給 TEP）
- [ ] 實作 `tep_client.cancel_registration(registration_id)`
- [ ] 開發 `POST /api/liff/registrations/:id/cancel` 端點
- [ ] 取消後寫 action_logs
- [ ] 推送取消確認訊息
- [ ] 列表頁面分類顯示（即將舉行 / 已取消 / 歷史）

**驗收**
- LIFF 看到自己所有報名
- 點取消後 TEP 狀態變更
- LINE 收到確認訊息

---

### F8：行為追蹤基礎建設

**這是 P2 P3 所有數據功能的前提**

**需要的非程式素材**
- 無

**程式工作細項**
- [ ] 建立 `view_logs` model（id, line_user_id, content_type, content_id, action, duration_seconds, metadata, created_at）
- [ ] `content_type` enum：route_stop / deity / facility / wish / event / temple
- [ ] `action` enum：view / click / scan / share
- [ ] 撰寫 `services/tracking_service.py`
- [ ] 提供統一 `track_event(user_id, type, id, action, metadata)` 介面
- [ ] 開發 `POST /api/liff/track` 端點供前端呼叫
- [ ] LIFF 端統一封裝 tracking JS function
- [ ] 加 index：`(content_type, content_id, created_at)` 給後續統計查詢用

**驗收**
- 任意 LIFF 頁面點擊後 view_logs 有記錄
- DB 查詢能聚合：「過去 7 天最多人查看的 deity」

---

## P2 擴充內容

### F9：參拜路線導覽

**需要的非程式素材**
- ⚠️ **大量內容**：每間廟的路線、每站文案、神明照片
- LIFF 路線頁設計稿（步驟卡介面）
- 廟內平面圖（如果要做地圖功能）

**程式工作細項**
- [ ] 建立 `temple_routes` model（id, tep_temple_id, name, description, sort_order）
- [ ] 建立 `route_stops` model（id, route_id, sort_order, name, description, photo_url, audio_url, location_hint）
- [ ] 建立 LIFF 應用：參拜導覽
- [ ] 開發 `/liff/route/:temple_id` 頁面
- [ ] 開發 `GET /api/liff/routes/:temple_id` 端點
- [ ] 實作步驟卡 UI（進度條、上下站切換）
- [ ] 整合 view_logs 追蹤每站的查看
- [ ] 用 localStorage 記住使用者進度（關掉再開能接續）
- [ ] 提供「我拜完了，下一站」按鈕（情感化動作）
- [ ] 完成後顯示「圓滿達成」畫面

**驗收**
- LIFF 開啟看到第一站
- 切換站別流暢
- 點擊資料寫進 view_logs
- 關掉再開能回到上次的站

---

### F10：神明介紹與祈禱用詞

**需要的非程式素材**
- ⚠️ **大量內容**：每尊神明的故事、祈禱用詞、準備物品
- 神明照片
- LIFF 設計稿

**程式工作細項**
- [ ] 建立 `deities` model（id, tep_temple_id, name, title, description, photo_url, prayer_text, offerings, sort_order）
- [ ] 建立 LIFF 應用：神明指南
- [ ] 開發 `/liff/deities/:temple_id` 頁面（列表）
- [ ] 開發 `/liff/deity/:id` 頁面（詳情）
- [ ] 開發 `GET /api/liff/deities/:temple_id` 端點
- [ ] 提供按願望類型篩選（求姻緣、求財、求學…）
- [ ] 整合 view_logs 追蹤
- [ ] 「複製祈禱用詞」按鈕（方便使用者照念）

**驗收**
- LIFF 列出所有神明
- 點擊看到詳情
- 篩選功能可用
- 點擊紀錄寫入

---

### F11：現場設施查詢

**需要的非程式素材**
- 每間廟的設施資訊（停車場位置、廁所、輪椅通道…）
- 設施照片
- LIFF 設計稿

**程式工作細項**
- [ ] 建立 `facilities` model（id, tep_temple_id, type, name, description, photo_url, location_hint, sort_order）
- [ ] facility type enum：parking / restroom / accessibility / food / souvenir / atm
- [ ] 建立 LIFF 應用：設施資訊
- [ ] 開發 `/liff/facilities/:temple_id` 頁面
- [ ] 按類型分類顯示
- [ ] 整合 view_logs 追蹤
- [ ] 每個設施可顯示「距離正殿多遠」（如果有資料）

**驗收**
- 設施按分類顯示
- 點擊有紀錄
- 大字顯示適合現場使用

---

## P3 價值放大

### F12：願望推薦廟宇

**需要的非程式素材**
- 願望分類體系（求姻緣 / 求財 / 求學 / 求平安 / 求子…）
- 每個願望對應的神明與廟宇
- 推薦邏輯規則（這要跟廟方諮詢）
- LIFF 設計稿

**程式工作細項**
- [ ] 建立 `wish_categories` model（id, name, description, icon）
- [ ] 建立 `wish_recommendations` model（id, wish_category_id, tep_temple_id, deity_id, reason, priority）
- [ ] 建立 LIFF 應用：願望推薦
- [ ] 開發 `/liff/wishes` 頁面
- [ ] 開發 `/liff/wishes/:id/recommend` 推薦結果頁
- [ ] 推薦邏輯實作（先用簡單規則匹配，未來可加機器學習）
- [ ] 在 line_users 紀錄使用者最常查的願望類型
- [ ] 整合 view_logs

**驗收**
- 選擇願望後看到推薦廟宇與神明
- 推薦結果可導去訂閱該廟（F3）
- 使用者偏好被記錄

---

### F13：廟方數據後台（內容管理）

**需要的非程式素材**
- 廟方後台 UI 設計稿（簡易即可）
- 後台帳號規格

**程式工作細項**
- [ ] 建立 `admin_users` model（id, username, password_hash, tep_temple_id, role, last_login_at）
- [ ] 開發 `/admin/login` 登入頁
- [ ] 實作 bcrypt 密碼驗證
- [ ] 實作 session 管理
- [ ] 開發 `/admin/dashboard` 首頁
- [ ] 開發 `/admin/routes` 路線管理（CRUD）
- [ ] 開發 `/admin/deities` 神明管理（CRUD）
- [ ] 開發 `/admin/facilities` 設施管理（CRUD）
- [ ] 開發 `/admin/wishes` 願望分類管理
- [ ] 圖片上傳功能（用 Zeabur 物件儲存或 S3）
- [ ] 資料按 temple_id 隔離（廟方只能看自己的廟）

**驗收**
- 廟方登入後只看到自己廟的資料
- CRUD 功能完整
- 圖片上傳成功
- LIFF 頁面立即反映後台變更

---

### F14：廟方數據後台（統計圖表）

**需要的非程式素材**
- 圖表設計稿（要顯示什麼指標、用什麼圖）
- 報表需求清單（廟方想看什麼）

**程式工作細項**
- [ ] 開發 `/admin/analytics/users` 訂閱者分析頁
- [ ] 開發 `/admin/analytics/heatmap` 動線熱區頁（基於 view_logs）
- [ ] 開發 `/admin/analytics/deities` 熱搜神明排行
- [ ] 開發 `/admin/analytics/wishes` 熱門願望分析
- [ ] 開發 `/admin/analytics/facilities` 設施關注度
- [ ] 開發 `/admin/analytics/events` 活動推播成效（基於 push_logs + 報名數）
- [ ] 圖表 library 選型（Chart.js 或 ECharts）
- [ ] 時間範圍篩選器（過去 7 天 / 30 天 / 90 天）
- [ ] CSV 匯出功能
- [ ] 寫聚合查詢的效能優化（加 index、必要時做 materialized view）

**驗收**
- 各圖表正確顯示
- 時間範圍切換能更新
- 大量資料時不會超時
- 廟方能匯出原始數據

---

## 跨階段共通工作

這些不屬於特定功能，但要在對應時點處理：

### 開發環境（Week 0）

- [ ]  申請 LINE Developers 帳號
- [ ]  建立 Provider + Channel（Messaging API + Login）
- [ ]  申請 LIFF（每個 LIFF 頁一個 ID，可先建幾個備用）
- [ ]  GitHub repo 建立 + .gitignore
- [ ]  本機 Docker PostgreSQL
- [ ]  本機 Docker TEP（從學長 repo clone）
- [ ]  ngrok 設定
- [ ]  VSCode 延伸模組
- [ ]  Zeabur 帳號 + 綁定 GitHub

### 部署相關（Week 4 + 8）

- [ ]  Zeabur 建立 PostgreSQL
- [ ]  環境變數設定
- [ ]  第一次部署
- [ ]  LINE Webhook URL 切換
- [ ]  LIFF Endpoint URL 設定
- [ ]  監控與日誌設定
- [ ]  備份策略

### 持續性工作

- [ ]  每完成一階段寫 README 對應段落
- [ ]  每完成一階段更新 API 文件
- [ ]  程式碼 review（自我或同儕）
- [ ]  重要決策記錄到 ADR（Architecture Decision Records）

---

## 給學長的整合需求清單

需要學長配合的事項，越早確認越好：

| # | 項目 | 哪個階段需要 | 阻塞等級 |
| --- | --- | --- | --- |
| 1 | TEP 後台加「LINE 推播」按鈕呼叫本系統 | F5 | 🔴 高 |
| 2 | 停用 TEP 既有 LINE 廣播功能 | F5 | 🔴 高 |
| 3 | 確認 TEP 取消報名 API 規格 | F7 | 🟡 中 |
| 4 | 確認 TEP 活動詳情公開 API | F5 | 🟡 中 |
| 5 | TEP 提供查詢個人報名的 API | F7 | 🟡 中 |

---

## 工作量估算（純程式工時）

| 階段 | 估算工時 | 說明 |
| --- | --- | --- |
| Week 0 準備 | 8 小時 | 環境申請與設定 |
| P0 (F1-F4) | 40 小時 | 基礎建設 |
| P1 (F5-F8) | 60 小時 | 核心閉環 + tracking 基建 |
| P2 (F9-F11) | 40 小時 | 內容功能（不含內容收集） |
| P3 (F12-F14) | 60 小時 | 推薦與後台與圖表 |
| 部署與測試 | 16 小時 | 雲端部署、bug 修復 |
| **合計** | **224 小時** | 約 28 個工作天（一天 8 小時） |

⚠️ 此估算僅含**程式工作**，不含內容收集、設計、訪談、會議。

---

## 進入 Notion 後建議的整理

複製此檔案到 Notion 後，建議這樣組織：

1. **Database 化**：把每個功能 F1-F14 變成一個 database row，欄位包含：優先級、狀態、估時、實際工時、Blocker
2. **Kanban view**：用 Status 欄位看板顯示（Not Started / In Progress / Blocked / Done）
3. **每個功能展開為子頁面**：把該功能的所有 checkbox 工作放進子頁面
4. **連結相關文件**：架構書、API 規格、設計稿都連到對應功能
5. **新增「進度看板」頁面**：用 percent 顯示整體完成度