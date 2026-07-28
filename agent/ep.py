import base64
import io
import re
import win32print
from PIL import Image, ImageOps, ImageEnhance, ImageFilter

_encoding = "cp1252"
e = None
PRINTER_NAME = "TM-T88IV"

# --- Commands ---

def open(printer_name=None):
    global e, PRINTER_NAME
    if printer_name:
        PRINTER_NAME = printer_name
    e = win32print.OpenPrinter(PRINTER_NAME)
    win32print.StartDocPrinter(e, 1, ("print", None, "RAW"))
    win32print.StartPagePrinter(e)


def close():
    global e
    if e is not None:
        win32print.EndPagePrinter(e)
        win32print.EndDocPrinter(e)
        win32print.ClosePrinter(e)
        e = None


def raw(data):
    if e is None:
        raise RuntimeError("Drucker ist nicht offen. Erst ep.open() aufrufen.")
    win32print.WritePrinter(e, data)


def reset():
    raw(b"\x1b\x40")


def feed(n=1):
    raw(b"\x1b\x64" + bytes([n]))


def cut():
    raw(b"\x1d\x56\x00")


def setEncoding(cp):
    global _encoding
    _encoding = cp


def setEndcoding(cp):  # alter Schreibfehler bleibt kompatibel
    setEncoding(cp)

# --- Text Commands ---

def cp1252():
    setEncoding("cp1252")
    raw(b"\x1b\x74\x10")


def cp437():
    setEncoding("cp437")
    raw(b"\x1b\x74\x00")


def write(text):
    raw(str(text).encode(_encoding, errors="replace"))


def line(txt=""):
    cp1252()
    write(str(txt) + "\n")


def heart():
    raw(b"\x1b\x74\x01")
    raw(b"\xe9")
    raw(b"\x1b\x74\x10")

# --- Style Commands ---

def bold(state):
    raw(b"\x1b\x45\x01" if state else b"\x1b\x45\x00")


def ori(state):
    if state == 0:
        raw(b"\x1b\x61\x00")
    elif state == 1:
        raw(b"\x1b\x61\x01")
    elif state == 2:
        raw(b"\x1b\x61\x02")


def box(text):
    width = 38
    text = str(text)
    if len(text) > width:
        text = text[:width]
    left = (width - len(text)) // 2
    right = width - len(text) - left
    cp437()
    write("╔" + "═" * width + "╗\n")
    write("║")
    cp1252()
    write(" " * left + text + " " * right)
    cp437()
    write("║\n")
    write("╚" + "═" * width + "╝\n")

def lineline():
    width = 40
    cp437()
    write("═" * width + "\n")

# --- Image Commands ---

def _prepare_image(img, width=384, photo=True):
    img = ImageOps.exif_transpose(img)
    img = img.convert("L")

    if width:
        ratio = width / img.width
        height = int(img.height * ratio)
        img = img.resize((width, height), Image.LANCZOS)

    img = ImageOps.autocontrast(img)

    if photo:
        img = ImageEnhance.Contrast(img).enhance(1.35)
        img = ImageEnhance.Sharpness(img).enhance(1.4)
        img = img.filter(ImageFilter.SMOOTH)
        img = img.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    else:
        img = ImageEnhance.Contrast(img).enhance(1.8)
        img = img.point(lambda p: 0 if p < 160 else 255)
        img = img.convert("1")

    new_width = (img.width + 7) // 8 * 8
    if new_width != img.width:
        new_img = Image.new("1", (new_width, img.height), 1)
        new_img.paste(img, (0, 0))
        img = new_img

    return img


def image(path, width=384, photo=True, center=True):
    """Druckt ein Bild von Datei, z.B. ep.image('test.jpg', width=384)."""
    img = Image.open(path)
    image_pil(img, width=width, photo=photo, center=center)


def image_base64(data, width=384, photo=True, center=True):
    """Druckt Base64/Data-URL aus Supabase, z.B. data:image/png;base64,..."""
    if not data:
        raise ValueError("Kein Bild/Base64 erhalten")

    data = str(data).strip()

    # data:image/png;base64,AAAA... entfernen
    if "," in data and data.lower().startswith("data:image"):
        data = data.split(",", 1)[1]

    # Leerzeichen/Zeilenumbrüche entfernen
    data = re.sub(r"\s+", "", data)

    img_bytes = base64.b64decode(data)
    img = Image.open(io.BytesIO(img_bytes))
    image_pil(img, width=width, photo=photo, center=center)


def image_pil(img, width=384, photo=True, center=True):
    """Druckt ein PIL Image per ESC/POS Raster."""
    if center:
        ori(1)

    img = _prepare_image(img, width=width, photo=photo)
    width_bytes = img.width // 8
    height = img.height

    # GS v 0 Raster Bit Image
    raw(b"\x1d\x76\x30\x00")
    raw(bytes([
        width_bytes % 256,
        width_bytes // 256,
        height % 256,
        height // 256,
    ]))

    pixels = img.load()
    for y in range(height):
        row = bytearray()
        for x_byte in range(width_bytes):
            b = 0
            for bit in range(8):
                x = x_byte * 8 + bit
                if pixels[x, y] == 0:
                    b |= 128 >> bit
            row.append(b)
        raw(bytes(row))

    feed(1)
