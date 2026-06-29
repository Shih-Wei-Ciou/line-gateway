"""
緣引拜拜通 · LINE 四分頁 Rich Menu 建置腳本
=================================================
用法：
  1. 把四張 2500x1686 的圖放到 IMAGES 指定路徑
  2. 設環境變數 LINE_CHANNEL_ACCESS_TOKEN（或直接填下面）
  3. python scripts/setup_rich_menu_4tabs.py

說明（給 Claude Code）：
  - 用原生 HTTP（requests），不依賴特定 line-bot-sdk 版本，最好整合。
  - 四張選單共用「上方分頁列」四個 richmenuswitch 切換區（LINE 原生切換，不需 webhook）。
  - 預設選單 = 找廟。
  - 座標來自實際 mockup 校正，仍建議上線前用 LINE 後台「測試點擊區」微調一次。
  - postback（合作洽詢 / 依願找廟）的回覆邏輯在檔案最下方「WEBHOOK 區」，請整合進
    blueprints/webhook.py。

依賴：requests
"""

import os
import json
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()  # 自動讀 .env（LINE_CHANNEL_ACCESS_TOKEN / WEBAPP_BASE_URL）
except ImportError:
    pass

# ============ 設定 ============
CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "<填入 Channel access token>")
BASE_URL = os.environ.get("WEBAPP_BASE_URL", "https://yuanyinbb.zeabur.app")  # ← 務必是正式站

# 緣引分頁右下「合作」→ Google 表單完整網址（務必換成真的表單；未填則為佔位）
GOOGLE_FORM_URL = os.environ.get("COOP_FORM_URL", "https://forms.gle/REPLACE_ME")

# 四張圖（已由 richman/*.png 放大到 2500x1686 + 壓到 <1MB，轉成 JPEG）
IMAGES = {
    "find":    "static/richmenu/find.jpg",      # 找廟
    "explore": "static/richmenu/explore.jpg",   # 尋緣
    "news":    "static/richmenu/news.jpg",        # 最新消息
    "coop":    "static/richmenu/coop.jpg",        # 合作
}

ALIAS = {"find": "rm-find", "explore": "rm-explore", "news": "rm-news", "coop": "rm-coop"}

API = "https://api.line.me/v2/bot"
API_DATA = "https://api-data.line.me/v2/bot"
AUTH = {"Authorization": f"Bearer {CHANNEL_ACCESS_TOKEN}"}
JSON_HEADERS = {**AUTH, "Content-Type": "application/json"}


# ============ 共用：上方四分頁切換區（每張圖都一樣，y 0~230）============
def tab_areas():
    return [
        {"bounds": {"x": 0,    "y": 0, "width": 625, "height": 230},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "rm-find",    "data": "tab=find"}},
        {"bounds": {"x": 625,  "y": 0, "width": 625, "height": 230},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "rm-explore", "data": "tab=explore"}},
        {"bounds": {"x": 1250, "y": 0, "width": 625, "height": 230},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "rm-news",    "data": "tab=news"}},
        {"bounds": {"x": 1875, "y": 0, "width": 625, "height": 230},
         "action": {"type": "richmenuswitch", "richMenuAliasId": "rm-coop",    "data": "tab=coop"}},
    ]


def uri(path):
    # 所有「站內」選單連結都帶 ?from=line → 落地時前端自動觸發 LINE 登入（已登入則無感）
    sep = "&" if "?" in path else "?"
    return {"type": "uri", "uri": f"{BASE_URL}{path}{sep}from=line"}


def uri_raw(full_url):
    """完整外部網址（例如 Google 表單），不接 BASE_URL、不加 from=line。"""
    return {"type": "uri", "uri": full_url}


def postback(data, display):
    return {"type": "postback", "data": data, "displayText": display}


# ============ 四張選單定義（座標已依實際圖校正）============
MENUS = {
    # ① 找廟（預設）：大主圖 + 下排四標籤（連成一條、無間隔）
    "find": {
        "size": {"width": 2500, "height": 1686},
        "selected": True,
        "name": "找廟",
        "chatBarText": "開啟選單",
        "areas": tab_areas() + [
            {"bounds": {"x": 0,    "y": 230,  "width": 2500, "height": 1096}, "action": uri("/temples")},
            {"bounds": {"x": 0,    "y": 1326, "width": 625,  "height": 360},  "action": uri("/temples?tag=姻緣")},
            {"bounds": {"x": 625,  "y": 1326, "width": 625,  "height": 360},  "action": uri("/temples?tag=事業")},
            {"bounds": {"x": 1250, "y": 1326, "width": 625,  "height": 360},  "action": uri("/temples?tag=健康")},
            {"bounds": {"x": 1875, "y": 1326, "width": 625,  "height": 360},  "action": uri("/temples?tag=學業")},
        ],
    },
    # ② 尋緣：大主圖 + 下方兩張卡
    "explore": {
        "size": {"width": 2500, "height": 1686},
        "selected": True,
        "name": "尋緣",
        "chatBarText": "開啟選單",
        "areas": tab_areas() + [
            # 依願找廟：建議走 B（postback 觸發 Flex 廟宇卡）。若要改直接跳轉，換成 uri("/search")
            {"bounds": {"x": 0,    "y": 230,  "width": 2500, "height": 1096},
             "action": postback("action=recommend_temples", "依願找廟")},
            {"bounds": {"x": 0,    "y": 1326, "width": 1250, "height": 360}, "action": uri("/guides")},
            {"bounds": {"x": 1250, "y": 1326, "width": 1250, "height": 360}, "action": uri("/guides?section=stories")},
        ],
    },
    # ③ 最新消息：中間大按鈕（置中、兩側留白）+ 下方左右兩小按鈕
    "news": {
        "size": {"width": 2500, "height": 1686},
        "selected": True,
        "name": "最新消息",
        "chatBarText": "開啟選單",
        "areas": tab_areas() + [
            # /news 頁 Web App 還沒做 → 先導主頁，避免 404（之後做好再改回 /news）
            {"bounds": {"x": 650,  "y": 600,  "width": 1200, "height": 360}, "action": uri("/")},
            {"bounds": {"x": 600,  "y": 1040, "width": 620,  "height": 360}, "action": uri("/")},
            {"bounds": {"x": 1280, "y": 1040, "width": 620,  "height": 360}, "action": uri("/calendar")},
        ],
    },
    # ④ 緣引（原合作）：中間品牌說明鈕(回介紹圖) + 下方左「緣引/about」右「合作/Google表單」
    "coop": {
        "size": {"width": 2500, "height": 1686},
        "selected": True,
        "name": "緣引",
        "chatBarText": "開啟選單",
        "areas": tab_areas() + [
            {"bounds": {"x": 350,  "y": 500,  "width": 1800, "height": 560},
             "action": postback("action=about_image", "關於緣引拜拜通")},
            {"bounds": {"x": 200,  "y": 1180, "width": 950,  "height": 420}, "action": uri("/")},
            {"bounds": {"x": 1350, "y": 1180, "width": 950,  "height": 420}, "action": uri_raw(GOOGLE_FORM_URL)},
        ],
    },
}


# ============ LINE API 呼叫 ============
def create_rich_menu(menu):
    r = requests.post(f"{API}/richmenu", headers=JSON_HEADERS, data=json.dumps(menu))
    r.raise_for_status()
    return r.json()["richMenuId"]


def upload_image(rich_menu_id, path):
    ctype = "image/png" if path.lower().endswith(".png") else "image/jpeg"
    with open(path, "rb") as f:
        r = requests.post(f"{API_DATA}/richmenu/{rich_menu_id}/content",
                          headers={**AUTH, "Content-Type": ctype}, data=f.read())
    r.raise_for_status()


def upsert_alias(alias_id, rich_menu_id):
    """先嘗試建立；若已存在(400)則改為更新。"""
    r = requests.post(f"{API}/richmenu/alias", headers=JSON_HEADERS,
                      data=json.dumps({"richMenuAliasId": alias_id, "richMenuId": rich_menu_id}))
    if r.status_code == 400:
        r2 = requests.post(f"{API}/richmenu/alias/{alias_id}", headers=JSON_HEADERS,
                           data=json.dumps({"richMenuId": rich_menu_id}))
        r2.raise_for_status()
    else:
        r.raise_for_status()


def set_default(rich_menu_id):
    r = requests.post(f"{API}/user/all/richmenu/{rich_menu_id}", headers=AUTH)
    r.raise_for_status()


def cleanup_existing():
    """先刪舊 alias 再刪舊 richmenu，避免重複堆積。"""
    for a in ALIAS.values():
        requests.delete(f"{API}/richmenu/alias/{a}", headers=AUTH)
    r = requests.get(f"{API}/richmenu/list", headers=AUTH)
    if r.ok:
        for m in r.json().get("richmenus", []):
            requests.delete(f"{API}/richmenu/{m['richMenuId']}", headers=AUTH)


def main():
    print("清除舊選單與 alias…")
    cleanup_existing()

    ids = {}
    for key, menu in MENUS.items():
        rid = create_rich_menu(menu)
        upload_image(rid, IMAGES[key])
        ids[key] = rid
        print(f"  建立 {menu['name']} ({key}) -> {rid}")

    for key, rid in ids.items():
        upsert_alias(ALIAS[key], rid)
        print(f"  alias {ALIAS[key]} -> {rid}")

    set_default(ids["find"])
    print("完成。預設選單 = 找廟")


if __name__ == "__main__":
    main()


# =========================================================================
# WEBHOOK 區：把以下邏輯整合進 blueprints/webhook.py 的 postback 處理
# =========================================================================
#
# 收到 PostbackEvent 時，依 event.postback.data 分流：
#   - "tab=..."                  → 分頁切換產生的，LINE 已自動換選單，直接忽略
#   - "action=coop_soon"         → 回覆「合作洽詢即將開放」
#   - "action=recommend_temples" → 回覆 Flex 廟宇 carousel
#
# 下面用原生 HTTP reply 示範（與 SDK 版本無關）；若專案已用 line-bot-sdk，
# 改用對應的 reply_message / FlexMessage 物件即可，邏輯一樣。

def reply_messages(reply_token, messages):
    requests.post("https://api.line.me/v2/bot/message/reply",
                  headers=JSON_HEADERS,
                  data=json.dumps({"replyToken": reply_token, "messages": messages}))


def handle_postback(data, reply_token):
    if data.startswith("tab="):
        return  # 分頁切換，LINE 已處理

    if data == "action=coop_soon":
        reply_messages(reply_token, [{
            "type": "text",
            "text": "合作洽詢即將開放，歡迎來信 ____@____ 或留下聯絡方式，我們會盡快與您聯繫 🙏"
        }])
        return

    if data == "action=recommend_temples":
        temples = get_recommended_temples()  # ← 接你們的 DB / API
        reply_messages(reply_token, [build_temple_carousel(temples)])
        return


def get_recommended_temples():
    """接你們實際的廟宇資料來源。回傳 list[dict]，每筆需有 id / name / intro / image。"""
    # 範例（請換成真實查詢；廟少沒關係，1~2 筆也好看）
    return [
        {"id": "1", "name": "範例宮", "intro": "求姻緣首選・香火鼎盛",
         "image": f"{BASE_URL}/static/temples/1.jpg"},
    ]


def build_temple_carousel(temples):
    """把廟宇清單組成 Flex carousel（最多 10 張），每張按鈕跳 Web App 詳情頁。"""
    bubbles = []
    for t in temples[:10]:
        bubbles.append({
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": t["image"],
                "size": "full",
                "aspectRatio": "20:13",
                "aspectMode": "cover",
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "contents": [
                    {"type": "text", "text": t["name"], "weight": "bold", "size": "lg", "wrap": True},
                    {"type": "text", "text": t.get("intro", ""), "size": "sm", "color": "#888888", "wrap": True},
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [{
                    "type": "button",
                    "style": "primary",
                    "color": "#b3552b",
                    "action": {"type": "uri", "label": "看詳情",
                               "uri": f"{BASE_URL}/temples/{t['id']}"},
                }],
            },
        })
    return {
        "type": "flex",
        "altText": "為你推薦的宮廟",
        "contents": {"type": "carousel", "contents": bubbles},
    }
