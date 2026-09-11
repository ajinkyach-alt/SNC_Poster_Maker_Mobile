# poster_generator.py
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import datetime
import os

W, H = 1248, 1248
GREEN = (0, 91, 43)
DARK_GREEN = (0, 65, 32)
YELLOW = (255, 215, 0)
RED = (244, 25, 25)
WHITE = (255, 255, 255)
LIGHT = (247, 251, 242)

# The supplied reference poster is 1248x1248.
# Keep template.png in the same folder as this script.
TEMPLATE = Path(__file__).with_name("template.png")

def find_font(size, bold=False):
    """
    Robust Devanagari font loader.
    Priority:
      1) Noto Sans Devanagari
      2) Nirmala UI
      3) Mangal
      4) other common Devanagari fonts
    This prevents Marathi text from becoming square boxes.
    """
    if bold:
        names = [
            "NotoSansDevanagari-Bold.ttf",
            "NotoSansDevanagari-Bold.otf",
            "NirmalaUI-Bold.ttf",
            "Mangal.ttf",
        ]
    else:
        names = [
            "NotoSansDevanagari-Regular.ttf",
            "NotoSansDevanagari-Regular.otf",
            "NirmalaUI.ttf",
            "Mangal.ttf",
        ]

    roots = [
        Path(__file__).parent / "fonts",
        Path(r"C:\Windows\Fonts"),
        Path(r"C:\Windows\Fonts\Nirmala"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/opentype/noto"),
        Path("/usr/share/fonts/truetype/dejavu"),
    ]

    for root in roots:
        for name in names:
            p = root / name
            if p.exists():
                return ImageFont.truetype(str(p), size)

    # Search Windows Fonts recursively as a final attempt.
    win_fonts = Path(r"C:\Windows\Fonts")
    if win_fonts.exists():
        for p in win_fonts.glob("*.ttf"):
            if any(k.lower() in p.name.lower() for k in
                   ["nirmala", "mangal", "devanagari"]):
                return ImageFont.truetype(str(p), size)

    raise RuntimeError(
        "Marathi/Devanagari font सापडला नाही. "
        "Noto Sans Devanagari install करा किंवा project च्या fonts folder मध्ये "
        "NotoSansDevanagari-Regular.ttf आणि NotoSansDevanagari-Bold.ttf ठेवा."
    )

def fit_font(text, max_width, start_size, bold=True):
    size = start_size
    while size >= 12:
        f = find_font(size, bold)
        bbox = f.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return f
        size -= 1
    return find_font(12, bold)

def crop_fill(img, box_size):
    """Center-crop photo into the card photo area."""
    target_w, target_h = box_size
    img = img.convert("RGB")
    iw, ih = img.size
    scale = max(target_w / iw, target_h / ih)
    nw, nh = int(iw * scale), int(ih * scale)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left = (nw - target_w) // 2
    top = (nh - target_h) // 2
    return img.crop((left, top, left + target_w, top + target_h))

def rounded_rectangle(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)

def add_card(canvas, item, x, y, w, h):
    draw = ImageDraw.Draw(canvas)

    # Card
    rounded_rectangle(draw, (x, y, x+w, y+h), 12, WHITE, GREEN, 3)

    # Photo
    photo_x, photo_y = x+8, y+8
    photo_w, photo_h = w-16, int(h*0.67)
    if item["photo"] and Path(item["photo"]).exists():
        try:
            photo = crop_fill(Image.open(item["photo"]), (photo_w, photo_h))
            canvas.paste(photo, (photo_x, photo_y))
        except Exception:
            rounded_rectangle(draw, (photo_x, photo_y, photo_x+photo_w, photo_y+photo_h),
                              8, (220,235,220), GREEN, 2)
    else:
        rounded_rectangle(draw, (photo_x, photo_y, photo_x+photo_w, photo_y+photo_h),
                          8, (247,251,242), GREEN, 1)

    # Vegetable name
    name_y = y + photo_h + 15
    name_h = 48
    rounded_rectangle(draw, (x+12, name_y, x+w-12, name_y+name_h),
                      12, GREEN, GREEN, 1)
    name = str(item.get("name", "")).strip()
    if name:
        nf = fit_font(name, w-45, 30, True)
        bb = draw.textbbox((0,0), name, font=nf)
        draw.text((x+w/2-(bb[2]-bb[0])/2,
                   name_y+(name_h-(bb[3]-bb[1]))/2-3),
                  name, font=nf, fill=WHITE)

    # Price strip
    price_y = name_y + name_h + 8
    price_h = h - (price_y-y) - 10
    rounded_rectangle(draw, (x+25, price_y, x+w-25, price_y+price_h),
                      12, YELLOW, YELLOW, 1)

    price = str(item.get("price", "")).strip() or "0"
    price_text = f"₹ {price}"
    pf = fit_font(price_text, int(w*0.55), 34, True)
    bb = draw.textbbox((0,0), price_text, font=pf)
    draw.text((x+40, price_y+(price_h-(bb[3]-bb[1]))/2-4),
              price_text, font=pf, fill=RED)

    kf = fit_font("/ किलो", int(w*0.35), 23, True)
    kbb = draw.textbbox((0,0), "/ किलो", font=kf)
    draw.text((x+w-35-(kbb[2]-kbb[0]), price_y+(price_h-(kbb[3]-kbb[1]))/2-3),
              "/ किलो", font=kf, fill=(15,15,15))

def generate_poster(items, date_text, contact, address, output_path):
    if not TEMPLATE.exists():
        raise FileNotFoundError(
            "template.png सापडला नाही. Reference poster image चे नाव template.png ठेवा."
        )

    base = Image.open(TEMPLATE).convert("RGB").resize((W,H), Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(base)

    # Product area: cover the old product cards only.
    # Header and footer from the supplied SNC design remain untouched.
    draw.rectangle((8, 268, 1240, 995), fill=LIGHT)

    # 8 cards = 4 columns x 2 rows
    margin_x = 14
    gap = 10
    top = 278
    bottom = 985
    card_w = int((W - 2*margin_x - 3*gap) / 4)
    card_h = int((bottom - top - gap) / 2)

    positions = []
    for row in range(2):
        for col in range(4):
            x = margin_x + col*(card_w+gap)
            y = top + row*(card_h+gap)
            positions.append((x,y))

    for i in range(8):
        item = items[i] if i < len(items) else {"photo":"","name":"","price":""}
        add_card(base, item, positions[i][0], positions[i][1], card_w, card_h)

    # Date/contact/address are placed over the existing fields only when requested.
    # For the first version, keep the supplied SNC header/footer design intact.
    # The date box and footer can be enabled later as separate editable regions.

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, quality=95, subsampling=0)
    return output_path
