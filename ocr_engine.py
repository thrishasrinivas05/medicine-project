import cv2
import pytesseract
import re

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# ================= OCR EXTRACTION =================
def extract_text(image_path):

    img = cv2.imread(image_path)

    if img is None:
        return ""

    img = cv2.resize(img, None, fx=0.6, fy=0.6)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)[1]

    text = pytesseract.image_to_string(thresh, config="--psm 6")

    return text


# ================= CLEAN TEXT =================
def clean_text(text):
    text = text.upper()
    text = re.sub(r'[^A-Z0-9 ]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


# ================= MEDICINE NAME =================
def extract_medicine_name(text):

    text = clean_text(text)

    ignore = {"TABLET","CAPSULE","MG","ML","TAB","CAP"}

    words = []

    for w in text.split():
        if w in ignore or w.isdigit() or len(w) < 3:
            continue
        words.append(w)
        if len(words) == 3:
            break

    return " ".join(words) if words else "Unknown"


# ================= EXPIRY DETECTION =================
def extract_expiry(text):

    text = clean_text(text)

    months = {
        "JAN":"01","FEB":"02","MAR":"03","APR":"04",
        "MAY":"05","JUN":"06","JUL":"07","AUG":"08",
        "SEP":"09","OCT":"10","NOV":"11","DEC":"12"
    }

    match = re.search(r'([A-Z]{3})\s*([0-9]{4})', text)

    if match:
        m, y = match.groups()
        if m in months:
            return f"{y}-{months[m]}-01"

    return None