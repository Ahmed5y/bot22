# Minimal drop-in replacement for the removed stdlib 'imghdr' (Python 3.13+)
# Provides imghdr.what(file, h=None) to detect basic image types used by PTB.
# Returns: 'jpeg'|'png'|'gif'|'webp'|'bmp'|'tiff' or None.

def _what_from_bytes(h: bytes):
    if not h or len(h) < 12:
        return None
    # JPEG
    if h.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    # PNG
    if h.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    # GIF
    if h.startswith(b"GIF87a") or h.startswith(b"GIF89a"):
        return "gif"
    # WebP (RIFF....WEBP)
    if h[:4] == b"RIFF" and h[8:12] == b"WEBP":
        return "webp"
    # BMP
    if h.startswith(b"BM"):
        return "bmp"
    # TIFF (little/big endian)
    if h.startswith(b"II*\x00") or h.startswith(b"MM\x00*"):
        return "tiff"
    return None

def what(file, h=None):
    """Mimic imghdr.what API."""
    if h is not None:
        return _what_from_bytes(h)
    try:
        with open(file, "rb") as f:
            head = f.read(32)
        return _what_from_bytes(head)
    except Exception:
        return None

# Optional compatibility attribute
tests = []
