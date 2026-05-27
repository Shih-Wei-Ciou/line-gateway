"""
Rich Menu 建立腳本 — 拜拜通 LINE Gateway
用法：python scripts/setup_rich_menu.py --confirm
"""

import argparse
import os
import sys

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont

# ── 常數 ──────────────────────────────────────────────────────
WIDTH, HEIGHT = 2500, 1686
CELL_W, CELL_H = WIDTH // 2, HEIGHT // 2  # 1250 × 843
IMAGE_PATH = os.path.join("static", "richmenu", "main_v1.png")

BG_COLOR = "#1A1A1A"
GOLD = "#C9A961"
WHITE = "#FFFFFF"
BORDER_COLOR = "#333333"

MENU_NAME = "main_menu_v1"
CHAT_BAR_TEXT = "緣引拜拜通"

# ── 四格定義 ──────────────────────────────────────────────────
CELLS = [
    {
        "label": "關於我們",
        "path": "/about?from=line",
        "bounds": {"x": 0, "y": 0, "width": CELL_W, "height": CELL_H},
        "text_color": WHITE,
    },
    {
        "label": "拜拜通",
        "path": "/?from=line",
        "bounds": {"x": CELL_W, "y": 0, "width": CELL_W, "height": CELL_H},
        "text_color": GOLD,  # highlight
    },
    {
        "label": "最新消息",
        "path": "/news?from=line",
        "bounds": {"x": 0, "y": CELL_H, "width": CELL_W, "height": CELL_H},
        "text_color": WHITE,
    },
    {
        "label": "合作管道",
        "path": "/partner?from=line",
        "bounds": {"x": CELL_W, "y": CELL_H, "width": CELL_W, "height": CELL_H},
        "text_color": WHITE,
    },
]

# ── 字型 fallback ────────────────────────────────────────────
FONT_CANDIDATES = [
    # Windows
    r"C:\Windows\Fonts\msjhbd.ttc",   # 微軟正黑體 Bold
    r"C:\Windows\Fonts\msjh.ttc",     # 微軟正黑體
    # Linux
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
    # macOS
    "/System/Library/Fonts/PingFang.ttc",
]


def load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    print("WARNING: No CJK font found, using default font. Chinese text may render as boxes.")
    return ImageFont.load_default()


# ── 圖片生成 ─────────────────────────────────────────────────
def generate_image() -> str:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 格線
    draw.line([(CELL_W, 0), (CELL_W, HEIGHT)], fill=BORDER_COLOR, width=3)
    draw.line([(0, CELL_H), (WIDTH, CELL_H)], fill=BORDER_COLOR, width=3)

    font = load_font(72)

    for cell in CELLS:
        b = cell["bounds"]
        cx = b["x"] + b["width"] // 2
        cy = b["y"] + b["height"] // 2
        draw.text(
            (cx, cy),
            cell["label"],
            fill=cell["text_color"],
            font=font,
            anchor="mm",
        )

    os.makedirs(os.path.dirname(IMAGE_PATH), exist_ok=True)
    img.save(IMAGE_PATH, "PNG")
    print(f"Image saved: {IMAGE_PATH}")
    return IMAGE_PATH


# ── LINE API ─────────────────────────────────────────────────
def get_clients():
    from linebot.v3.messaging import (
        ApiClient,
        Configuration,
        MessagingApi,
        MessagingApiBlob,
    )

    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "").strip()
    if not token:
        print("ERROR: LINE_CHANNEL_ACCESS_TOKEN is not set in .env")
        sys.exit(1)

    config = Configuration(access_token=token)
    api_client = ApiClient(config)
    return MessagingApi(api_client), MessagingApiBlob(api_client)


def build_rich_menu_request(webapp_base_url: str):
    from linebot.v3.messaging.models import (
        RichMenuArea,
        RichMenuBounds,
        RichMenuRequest,
        RichMenuSize,
        URIAction,
    )

    base = webapp_base_url.rstrip("/")
    areas = []
    for cell in CELLS:
        b = cell["bounds"]
        areas.append(
            RichMenuArea(
                bounds=RichMenuBounds(
                    x=b["x"], y=b["y"], width=b["width"], height=b["height"]
                ),
                action=URIAction(
                    label=cell["label"],
                    uri=f"{base}{cell['path']}",
                ),
            )
        )

    return RichMenuRequest(
        size=RichMenuSize(width=WIDTH, height=HEIGHT),
        selected=True,
        name=MENU_NAME,
        chat_bar_text=CHAT_BAR_TEXT,
        areas=areas,
    )


def create_rich_menu(api, blob_api, webapp_base_url: str) -> str:
    # 1. Create
    req = build_rich_menu_request(webapp_base_url)
    result = api.create_rich_menu(rich_menu_request=req)
    menu_id = result.rich_menu_id
    print(f"Rich Menu created: {menu_id}")

    # 2. Upload image
    with open(IMAGE_PATH, "rb") as f:
        blob_api.set_rich_menu_image(
            rich_menu_id=menu_id,
            body=f.read(),
            _headers={"Content-Type": "image/png"},
        )
    print(f"Image uploaded to {menu_id}")

    # 3. Set as default
    api.set_default_rich_menu(rich_menu_id=menu_id)
    print(f"Set as default: {menu_id}")

    return menu_id


def cleanup_old_menus(api, keep_id: str):
    resp = api.get_rich_menu_list()
    menus = resp.richmenus if resp.richmenus else []
    to_delete = [m.rich_menu_id for m in menus if m.rich_menu_id != keep_id]

    if not to_delete:
        print("Cleanup: no old menus to delete.")
        return

    print(f"Will delete the following {len(to_delete)} rich menu(s):")
    for mid in to_delete:
        print(f"  - {mid}")

    for mid in to_delete:
        print(f"Deleting: {mid}")
        api.delete_rich_menu(rich_menu_id=mid)

    print(f"Cleanup done. {len(to_delete)} menus deleted, 1 remaining (the new one).")


# ── main ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Setup Rich Menu for 拜拜通")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required flag to actually execute (create menu + cleanup old ones)",
    )
    args = parser.parse_args()

    if not args.confirm:
        print("Dry run mode. Pass --confirm to actually create and upload.")
        print("Will generate image only.\n")

    load_dotenv()

    webapp_base_url = os.getenv("WEBAPP_BASE_URL", "https://baibaitong-webapp.zeabur.app").rstrip("/")
    print(f"WEBAPP_BASE_URL = {webapp_base_url}")

    # Generate image
    generate_image()

    if not args.confirm:
        print("\nDone (dry run). Image generated. Re-run with --confirm to deploy to LINE.")
        return

    # Deploy to LINE
    api, blob_api = get_clients()
    new_id = create_rich_menu(api, blob_api, webapp_base_url)
    cleanup_old_menus(api, keep_id=new_id)
    print("\nAll done!")


if __name__ == "__main__":
    main()
