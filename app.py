import signal
import sys
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import cv2
import numpy as np
import re
import easyocr
import threading
from dotenv import load_dotenv
from datetime import datetime
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from sqlalchemy.orm import scoped_session, sessionmaker

load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

FLASK_HOST = os.getenv("FLASK_HOST", "0,0,0,0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5000))
FLASK_DEBUG =os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1")

engine = create_engine(DATABASE_URL)
session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Session = scoped_session(session_factory)
Base = declarative_base()

class Kendaraan(Base):
    __tablename__ = "kendaraan"
    id = Column(Integer, primary_key=True, index=True)
    nama_pemilik = Column(String(15), nullable=False)
    no_mesin = Column(String(10), nullable=False)
    no_rangka = Column(String(15), nullable=False)
    no_plat = Column(String(10), unique=True, nullable=False)
    jenis_kendaraan = Column(String(20), nullable=False)
    status = Column(String(20), nullable=False)

class ScanLog(Base):
    __tablename__ = "scan_log"
    id = Column(Integer, primary_key=True, index=True)
    plate_text = Column(String(15), nullable=False)
    is_match = Column(String(20), nullable=False)
    created_at = Column(String(50), nullable=False)

Base.metadata.create_all(bind=engine)

similar_map = {"0": "O", "1": "I", "4": "A", "8": "B", "5": "S"}

def correct_similar(text, only_letters=False):
    if only_letters:
        return "".join([similar_map.get(ch, ch) if ch.isalpha() else ch for ch in text])
    else:
        return "".join([similar_map.get(ch, ch) for ch in text])

def preprocess(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh

def clean_and_order(result):
    ordered = sorted(result, key=lambda r: r[0][0][0])
    texts = []
    for (_, text, prob) in ordered:
        text = text.strip().upper()
        texts.append(text)
    return texts

def extract_plate_from_parts(parts):
    huruf_awal, angka, huruf_akhir = None, None, None
    for i in range(len(parts)):
        for j in range(len(parts)):
            for k in range(len(parts)):
                if len({i, j, k}) < 3:
                    continue
                pa, pb, pc = parts[i], parts[j], parts[k]
                if re.fullmatch(r"[A-Z]{1,2}", pa) and re.fullmatch(r"\d{3,4}", pb) and re.fullmatch(r"[A-Z]{1,3}", pc):
                    huruf_awal, angka, huruf_akhir = pa, pb, pc
                    break
            if huruf_awal: break
        if huruf_awal: break

    if huruf_awal and angka and huruf_akhir:
        huruf_awal = correct_similar(huruf_awal, only_letters=True)
        huruf_akhir = correct_similar(huruf_akhir, only_letters=True)
        return f"{huruf_awal} {angka} {huruf_akhir}"
    return None

reader = easyocr.Reader(['en'], gpu=False)

def ocr_plate(img):
    result = reader.readtext(img, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")
    parts = clean_and_order(result)
    plate = extract_plate_from_parts(parts)
    return plate, result

def graceful_exit(signum, frame):
    print("\n[INFO] Received shutdown signal. Cleaning up...")
    try:
        reader.close()  
    except Exception:
        pass
    try:
        engine.dispose()  
    except Exception:
        pass
    print("[INFO] Shutdown complete.")
    sys.exit(0)

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv('SECRET_KEY')
CORS(app)

admin = Admin(app, name="Admin", template_mode="bootstrap4")

admin.add_view(ModelView(Kendaraan, Session()))
admin.add_view(ModelView(ScanLog, Session()))

@app.route("/detect", methods=["POST"])
def api_ocr_plate():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    file_bytes = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return jsonify({"error": "Invalid image"}), 400

    pre_img = preprocess(img)
    plate, raw_result = ocr_plate(pre_img)

    if not plate:
        db = Session()
        log = ScanLog(
            plate_text=None,
            is_match="Tidak Terdaftar",
            created_at=str(np.datetime64('now'))
        )
        db.add(log)
        db.commit()
        db.close()

        return jsonify({"error": "Plat tidak terbaca", "raw": [
            {"text": t, "prob": float(p)} for (_, t, p) in raw_result
        ]})

    db = Session()
    kendaraan = db.query(Kendaraan).filter(Kendaraan.no_plat == plate).first()

    if kendaraan:
        data_kendaraan = {
            "nama_pemilik": kendaraan.nama_pemilik,
            "no_mesin": kendaraan.no_mesin,
            "no_rangka": kendaraan.no_rangka,
            "no_plat": kendaraan.no_plat,
            "jenis_kendaraan": kendaraan.jenis_kendaraan,
            "status": kendaraan.status
        }
        is_match = "Terdaftar"
    else:
        data_kendaraan = {"message": "Kendaraan Tidak Terdaftar"}
        is_match = "Tidak Terdaftar"
    
    log = ScanLog(
        plate_text=plate,
        is_match=is_match,
        created_at=str(np.datetime64('now'))
    )
    db.add(log)
    db.commit()
    db.close()

    return jsonify({
        "plate": plate,
        "raw": [{"text": t, "prob": float(p)} for (_, t, p) in raw_result],
        "match": data_kendaraan
    })
@app.route("/scans", methods=["GET"])
def get_scans():
    db = Session()
    scans = db.query(ScanLog).all()
    db.close()
    return jsonify([
        {
            "id": s.id,
            "plate_text": s.plate_text,
            "is_match": s.is_match,
            "created_at": s.created_at
        }
        for s in scans
    ])

@app.route("/scans/<int:scan_id>/verify", methods=["POST"])
def verify_scan(scan_id):
    data = request.get_json()
    status = data.get("status")

    db = Session()
    scan = db.query(ScanLog).filter(ScanLog.id == scan_id).first()
    if not scan:
        db.close()
        return jsonify({"error": "Scan not Found"}), 404

    scan.is_match = status
    db.commit()
    db.close()
    return jsonify({"message": "Scan updated", "id": scan_id, "status": status})

if __name__ == "__main__":
    print("[INFO] Starting server...")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG, threaded=True)