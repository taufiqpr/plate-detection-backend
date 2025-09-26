from flask import Flask, request, jsonify
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import cv2
import numpy as np
import re
import easyocr

DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/plat_detection_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Kendaraan(Base):
    __tablename__ = "kendaraan"

    id = Column(Integer, primary_key=True, index=True)
    nama_pemilik = Column(String, nullable=False)
    no_mesin = Column(String, nullable=False)
    no_rangka = Column(String, nullable=False)
    no_plat = Column(String, unique=True, nullable=False)
    jenis_kendaraan = Column(String, nullable=False)
    status = Column(String, nullable=False)

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

reader = easyocr.Reader(['en'])

def ocr_plate(img):
    result = reader.readtext(img, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")
    parts = clean_and_order(result)
    plate = extract_plate_from_parts(parts)
    return plate, result

app = Flask(__name__)
CORS(app)

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
        return jsonify({"error": "Plat tidak terbaca", "raw": [
            {"text": t, "prob": float(p)} for (_, t, p) in raw_result
        ]})

    db = SessionLocal()
    kendaraan = db.query(Kendaraan).filter(Kendaraan.no_plat == plate).first()
    db.close()

    if kendaraan:
        data_kendaraan = {
            "nama_pemilik": kendaraan.nama_pemilik,
            "no_mesin": kendaraan.no_mesin,
            "no_rangka": kendaraan.no_rangka,
            "no_plat": kendaraan.no_plat,
            "jenis_kendaraan": kendaraan.jenis_kendaraan,
            "status": kendaraan.status
        }
    else:
        data_kendaraan = {
            "message": "Kendaraan Tidak Terdaftar"
        }

    return jsonify({
        "plate": plate,
        "raw": [{"text": t, "prob": float(p)} for (_, t, p) in raw_result],
        "match": data_kendaraan
    })

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)