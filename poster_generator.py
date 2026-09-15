# poster_generator.py
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import datetime
import os
import sys

W, H = 1254, 1254
GREEN = (0, 91, 43)
DARK_GREEN = (0, 65, 32)
YELLOW = (255, 215, 0)
RED = (244, 25, 25)
WHITE = (254, 252, 227)
LIGHT = (247, 251, 242)

def resource_path(filename):
    """
    Resolve a file next to this script in normal use, or inside the
    PyInstaller onefile temp extraction folder (sys._MEIPASS) when running
    as a bundled .exe. Without this, a packaged exe can't find template.png.
    """
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return base / filename

# The supplied reference poster is 1248x1248.
# Keep template.png in the same folder as this script (or bundle it with
# --add-data when building the exe - see build notes at the bottom).
TEMPLATE = resource_path("template.png")

_FONT_CACHE = {}

def find_font(size, bold=False):
    key = ("AutoWindowsFont", size, bold)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]

    # Pillow ला Windows मध्ये font शोधण्यासाठी फक्त फाईलचे नाव द्यावे लागते.
    # हे fonts इंग्लिश (Latin) आणि मराठी (Devanagari) दोन्हीला उत्तम सपोर्ट करतात.
    fonts_to_try = [
        "nirmalab.ttf" if bold else "nirmala.ttf",  # पहिली पसंती: Nirmala UI
        "mangal.ttf",                               # दुसरी पसंती: Mangal (Windows Default)
        "arial.ttf"                                 # तिसरी पसंती: Arial 
    ]

    for font_name in fonts_to_try:
        try:
            # Pillow आपोआप सिस्टीममध्ये हे fonts शोधेल 
            f = ImageFont.truetype(font_name, size)
            _FONT_CACHE[key] = f
            return f
        except Exception:
            continue

    # सिस्टीममध्ये काहीच नाही मिळाले तर तुमच्या 'fonts' फोल्डरमधील जुना फॉन्ट वापरा
    fallback_name = "NotoSansDevanagari-Bold.ttf" if bold else "NotoSansDevanagari-Regular.ttf"
    roots = [resource_path("fonts"), Path(__file__).parent / "fonts"]
    for root in roots:
        p = root / fallback_name
        if p.exists():
            try:
                f = ImageFont.truetype(str(p), size)
                _FONT_CACHE[key] = f
                return f
            except Exception:
                pass

    # शेवटी काहीच नाही चालले तर PIL चा डिफॉल्ट फॉन्ट वापरा
    from PIL import ImageFont as PILFont
    return PILFont.load_default()

def fit_font(text, max_width, start_size, bold=True):
    size = start_size
    while size >= 12:
        f = find_font(size, bold)
        bbox = f.getbbox(text)
        if bbox[2] - bbox[0] <= max_width:
            return f
        size -= 1
    return find_font(12, bold)

def _raqm_available():
    try:
        from PIL import features
        return bool(features.check_feature("raqm"))
    except Exception:
        return False

RAQM_AVAILABLE = _raqm_available()

def draw_text(draw, xy, text, font, fill, anchor=None):
    """
    Wrapper around ImageDraw.text(). When the raqm layout engine is present
    we pass language="en" so digits render as plain 0-9 instead of the font
    substituting localized (Devanagari) numeral glyphs. Some Pillow builds -
    including PyInstaller-frozen exes where the libraqm DLL didn't get
    bundled - don't have raqm at all, and passing language= there raises
    "setting text direction, language or font features is not supported
    without libraqm". So we detect that once up front and just skip the
    hint on those builds rather than crashing (basic layout without raqm
    doesn't do that digit substitution anyway, so the output still looks
    right).
    """
    if RAQM_AVAILABLE:
        try:
            draw.text(xy, text, font=font, fill=fill, anchor=anchor, language="en")
            return
        except ValueError:
            pass
    draw.text(xy, text, font=font, fill=fill, anchor=anchor)

MAR_MONTHS = ["जानेवारी", "फेब्रुवारी", "मार्च", "एप्रिल", "मे", "जून",
              "जुलै", "ऑगस्ट", "सप्टेंबर", "ऑक्टोबर", "नोव्हेंबर", "डिसेंबर"]
MAR_WEEKDAYS = ["सोमवार", "मंगळवार", "बुधवार", "गुरुवार", "शुक्रवार", "शनिवार", "रविवार"]

def parse_date(date_text):
    """Best-effort parse of common date formats the UI/user might type."""
    date_text = (date_text or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d", "%d/%m/%y"):
        try:
            return datetime.datetime.strptime(date_text, fmt)
        except ValueError:
            continue
    return None

def wrap_text(draw, text, font, max_width):
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if draw.textlength(trial, font=font) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines

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
    """Draw one vegetable tile matching the NEW 1254x1254 SNC template."""
    draw = ImageDraw.Draw(canvas)

    # Outer card
    rounded_rectangle(draw, (x, y, x+w, y+h), 14, WHITE, GREEN, 3)

    # Photo area — matched to the new template
    photo_x, photo_y = x+8, y+8
    photo_w, photo_h = w-16, 170
    if item.get("photo") and Path(item["photo"]).exists():
        try:
            photo = crop_fill(Image.open(item["photo"]), (photo_w, photo_h))
            canvas.paste(photo, (photo_x, photo_y))
        except Exception:
            rounded_rectangle(
                draw, (photo_x, photo_y, photo_x+photo_w, photo_y+photo_h),
                8, (220,235,220), GREEN, 2
            )
    else:
        # Keep an empty photo tile genuinely empty.
        rounded_rectangle(
            draw, (photo_x, photo_y, photo_x+photo_w, photo_y+photo_h),
            8, WHITE, GREEN, 2
        )

    # Vegetable name strip
    name_y = y + 174
    name_h = 54
    rounded_rectangle(
        draw, (x+12, name_y, x+w-12, name_y+name_h),
        12, GREEN, GREEN, 1
    )
    name = str(item.get("name", "")).strip()
    if name:
        nf = fit_font(name, w-40, 31, True)
        draw_text(
            draw, (x+w/2, name_y+name_h/2),
            name, font=nf, fill=WHITE, anchor="mm"
        )

    # Price strip
    price_y = name_y + name_h + 8
    price_h = h - (price_y-y) - 8
    
    strip_left = x + 12
    strip_right = x + w - 12
    strip_width = strip_right - strip_left

    # १. बेस पिवळा Rounded Rectangle (बॅकग्राऊंड)
    rounded_rectangle(
        draw, (strip_left, price_y, strip_right, price_y+price_h),
        12, YELLOW, YELLOW, 1
    )

    # २. लाल रंगाचा तिरपा आकार (Polygon)
    top_right_x = strip_left + int(strip_width * 0.75)
    bottom_right_x = strip_left + int(strip_width * 0.65)

    # डावीकडचे कोपरे पिवळ्या बॉर्डरच्या आत राहावेत म्हणून +2 पिक्सल्स घेतले आहेत
    red_polygon = [
        (strip_left + 2, price_y + 1),               # टॉप-लेफ्ट
        (top_right_x, price_y + 1),                  # टॉप-राईट (तिरपा)
        (bottom_right_x, price_y + price_h - 1),     # बॉटम-राईट (तिरपा)
        (strip_left + 2, price_y + price_h - 1)      # बॉटम-लेफ्ट
    ]
    draw.polygon(red_polygon, fill=RED)

    price = str(item.get("price", "")).strip()
    if price:
        price_text = f"₹ {price}"
        unit_text = "/ किलो"

        center_y = price_y + price_h/2

        # =====================================================
        # PRICE / UNIT ZONES
        # =====================================================

        # Red price area
        price_zone_left = strip_left + 10
        price_zone_right = x + w * 0.66

        # Yellow unit area
        unit_zone_left = x + w * 0.70
        unit_zone_right = strip_right - 10


        # =====================================================
        # PRICE FONT
        # =====================================================

        pf = fit_font(
            price_text,
            int(price_zone_right - price_zone_left - 16),
            34,
            True
        )


        # =====================================================
        # UNIT FONT
        # =====================================================

        uf = fit_font(
            unit_text,
            int(unit_zone_right - unit_zone_left - 6),
            24,
            True
        )

        p_w = draw.textlength(price_text, font=pf)
        u_w = draw.textlength(unit_text, font=uf)

        p_x = price_zone_left + (price_zone_right-price_zone_left-p_w)/2
        u_x = unit_zone_left + (unit_zone_right-unit_zone_left-u_w)/2

        # ३. Text चा रंग बदला: किंमत पांढऱ्या (WHITE) रंगात आणि युनिट काळ्या (15,15,15) रंगात
        draw_text(
            draw, (p_x, center_y), price_text,
            font=pf, fill=WHITE, anchor="lm"  # इथे RED च्या जागी WHITE केले आहे
        )
        draw_text(
            draw, (u_x, center_y), unit_text,
            font=uf, fill=(15,15,15), anchor="lm"
        )

def draw_date_box(canvas, date_text):
    """Overwrite the enlarged DATE box in the new template."""
    draw = ImageDraw.Draw(canvas)

    # NEW template date box: much larger than the previous template.
    # Cover the old baked-in date text while preserving the border/header.
    fill_box = (954,105,1217,257)
    text_box = (983,116,1179,256)

    draw.rectangle(fill_box, fill=WHITE)

    cx = (text_box[0] + text_box[2]) / 2
    dt = parse_date(date_text)

    if dt:
        lines = [
            f"{dt.day:02d} {MAR_MONTHS[dt.month-1]}",
            f"{dt.year}",
            MAR_WEEKDAYS[dt.weekday()]
        ]
    else:
        lines = [date_text.strip()] if date_text and date_text.strip() else []

    if not lines:
        return

    box_w = text_box[2] - text_box[0]
    box_h = text_box[3] - text_box[1]

    size = 46
    while size >= 20:
        f = find_font(size, True)
        line_h = size * 1.08
        widths_ok = all(
            f.getbbox(t)[2] - f.getbbox(t)[0] <= box_w
            for t in lines
        )
        if line_h * len(lines) <= box_h and widths_ok:
            break
        size -= 1

    f = find_font(size, True)
    line_h = size * 1.08
    total_h = line_h * len(lines)
    start_y = text_box[1] + (box_h-total_h)/2 + line_h/2

    for i, line in enumerate(lines):
        draw_text(
            draw,
            (cx, start_y + i*line_h),
            line,
            font=f,
            fill=(20,20,20),
            anchor="mm"
        )

def draw_footer(canvas, contact, address):
    """Overwrite contact/address values in the NEW template footer."""
    draw = ImageDraw.Draw(canvas)
    bar_bg = (1, 64,25)

    # Contact number area — NEW template
    cbox = (132, 1038, 446, 1118)
    contact = str(contact or "").strip()
    if contact:
        draw.rectangle(cbox, fill=bar_bg)
        cf = fit_font(contact, cbox[2]-cbox[0]-8, 48, True)
        draw_text(
            draw,
            ((cbox[0]+cbox[2])/2, (cbox[1]+cbox[3])/2),
            contact,
            font=cf, fill=WHITE, anchor="mm"
        )

    # Address value area — NEW template
    fill_box = (593,1028,946,1116)
    text_box = (600, 1034, 943, 1119)

    address = str(address or "").strip()
    if address:
        draw.rectangle(fill_box, fill=bar_bg)

        max_w = text_box[2]-text_box[0]
        max_h = text_box[3]-text_box[1]

        size = 30
        while size >= 16:
            f = find_font(size, True)
            lines = wrap_text(draw, address, f, max_w)
            line_h = size * 1.18
            if line_h*len(lines) <= max_h:
                break
            size -= 1

        f = find_font(size, True)
        lines = wrap_text(draw, address, f, max_w)
        line_h = size * 1.18
        total_h = line_h*len(lines)
        start_y = text_box[1] + max(0, (max_h-total_h)/2) + line_h/2

        for i, line in enumerate(lines):
            draw_text(
                draw,
                (text_box[0], start_y+i*line_h),
                line,
                font=f, fill=WHITE, anchor="lm"
            )

def generate_poster(items, date_text, contact, address, output_path):
    if not TEMPLATE.exists():
        raise FileNotFoundError(
            "template.png सापडला नाही. Reference poster image चे नाव template.png ठेवा."
        )

    base = Image.open(TEMPLATE).convert("RGB").resize(
        (W, H), Image.Resampling.LANCZOS
    )

    # NEW TEMPLATE:
    # 8 cards occupy the center area, 4 columns x 2 rows.
    # Cover ONLY the old vegetable cards, keeping the new header/footer artwork.
    draw = ImageDraw.Draw(base)
    # draw.rectangle((8, 330, 1246, 968), fill=LIGHT)

    # Card positions matched to the uploaded 1254x1254 template.
    margin_x = 16
    gap_x = 10
    top = 338
    gap_y = 8
    bottom = 962

    card_w = int((W - 2*margin_x - 3*gap_x) / 4)
    card_h = int((bottom - top - gap_y) / 2)

    positions = []
    for row in range(2):
        for col in range(4):
            x = margin_x + col*(card_w+gap_x)
            y = top + row*(card_h+gap_y)
            positions.append((x, y))

    for i in range(8):
        item = items[i] if i < len(items) else {
            "photo": "", "name": "", "price": ""
        }
        
        # कार्ड ॲड करण्याआधी फक्त त्या कार्डची जागा (Bounding Box) पुसून घ्या
        cx = positions[i][0]
        cy = positions[i][1]
        draw.rectangle((cx, cy, cx + card_w, cy + card_h), fill=LIGHT)
        
        # आता कार्ड ॲड करा
        add_card(
            base, item,
            cx, cy,
            card_w, card_h
        )

    # Live date/contact/address
    draw_date_box(base, date_text)
    draw_footer(base, contact, address)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    base.save(output_path, quality=95, subsampling=0)
    return output_path
