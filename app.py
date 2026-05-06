from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import os

from db import insert_user, get_user, insert_medicine, get_all_medicines, delete_medicine
from ocr_engine import extract_text, extract_medicine_name, extract_expiry
from ml_model import predict_stock_status, expiry_alert

app = Flask(__name__)

# ================= SECRET KEY =================
app.secret_key = os.getenv("SECRET_KEY", "medicine_project_key")

# ================= IMPORTANT FOR NGROK =================
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = False  # keep False for local + ngrok combo

UPLOAD_FOLDER = "static/images"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ================= LOGIN PAGE =================
@app.route('/')
def login():
    return render_template("login.html")


# ================= LOGIN CHECK =================
@app.route("/login", methods=["POST"])
def login_check():

    email = request.form.get("email")
    password = request.form.get("password")

    user = get_user(email)

    if user and user.get("password") == password:
        session["user"] = email
        return redirect(url_for("upload_page"))

    return render_template("login.html", error="Invalid login")


# ================= REGISTER =================
@app.route("/register", methods=["POST"])
def register():

    email = request.form.get("email")

    if get_user(email):
        return render_template("login.html", error="User already exists")

    insert_user({
        "name": request.form.get("name"),
        "email": email,
        "phone": request.form.get("phone"),
        "password": request.form.get("password")
    })

    # IMPORTANT FIX → proper redirect
    return redirect(url_for("login"))


# ================= UPLOAD PAGE =================
@app.route('/upload_page')
def upload_page():

    if "user" not in session:
        return redirect(url_for("login"))

    return render_template("index.html")


# ================= UPLOAD + OCR + ML =================
@app.route('/upload', methods=['POST'])
def upload():

    if "user" not in session:
        return redirect(url_for("login"))

    file = request.files.get("file")

    if not file or file.filename == "":
        return "No file selected"

    filename = file.filename.replace(" ", "_")
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    # ================= OCR =================
    text = extract_text(filepath)

    ocr_name = extract_medicine_name(text)
    ocr_expiry = extract_expiry(text)

    # ================= INPUTS =================
    name = request.form.get("manual_name") or ocr_name
    expiry = request.form.get("manual_expiry") or ocr_expiry
    stock = int(request.form.get("stock") or 0)

    # ================= ML =================
    stock_status = predict_stock_status(stock)
    expiry_status = expiry_alert(expiry) if expiry else "UNKNOWN"

    # ================= SAVE =================
    insert_medicine({
        "medicine_name": name,
        "stock": stock,
        "expiry_date": expiry,
        "order_date": datetime.now().strftime("%Y-%m-%d"),
        "image": filename,
        "stock_status": stock_status,
        "expiry_status": expiry_status
    })

    return redirect(url_for("dashboard"))


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():

    if "user" not in session:
        return redirect(url_for("login"))

    medicines = get_all_medicines()

    low_stock = []
    expiring = []

    today = datetime.now().date()

    for m in medicines:

        if m.get("stock", 0) <= 5:
            low_stock.append(m.get("medicine_name"))

        try:
            if m.get("expiry_date"):
                exp = datetime.strptime(m["expiry_date"], "%Y-%m-%d").date()
                days = (exp - today).days

                if 0 <= days <= 30:
                    expiring.append(f"{m['medicine_name']} → {days} days")

                m["expiry_date"] = exp.strftime("%d-%m-%Y")

        except:
            pass

    return render_template(
        "dashboard.html",
        medicines=medicines,
        popup_msg="\n".join(expiring) if expiring else None,
        low_stock_msg=", ".join(low_stock) if low_stock else None
    )


# ================= DELETE =================
@app.route('/delete/<id>')
def delete(id):
    delete_medicine(id)
    return redirect(url_for("dashboard"))


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for("login"))


# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)