from flask import Blueprint, current_app, jsonify, request
from datetime import datetime
import pytz
import numpy as np
import cv2
import logging
import hashlib

from ..db import get_scoped_session
from ..utils.time import now_wib
from ..models import Kendaraan, ScanLog
from ..services.ocr import preprocess, ocr_plate
from ..services.redis_service import get_cache, set_cache


bp = Blueprint("detect", __name__)

WIB = pytz.timezone("Asia/Jakarta")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

@bp.route("/detect", methods=["POST"])
def api_ocr_plate():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    try:
        file_bytes = np.frombuffer(file.read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        if img is None:
            return jsonify({"error": "Invalid image"}), 400

        image_hash = hashlib.md5(file_bytes).hexdigest()
        cached_result = get_cache(image_hash)
        if cached_result:
            logging.info("Mengambil hasil OCR dari Redis cache")
            return jsonify(cached_result), 200

        pre_img = preprocess(img)
        plate, raw_result = ocr_plate(pre_img)

        Session = get_scoped_session(current_app)
        db = Session()

        kendaraan = db.query(Kendaraan).filter(Kendaraan.no_plat == plate).first() if plate else None
        is_match = "Terdaftar" if kendaraan else "Tidak Terdaftar"
        kendaraan_data = {
            "nama_pemilik": kendaraan.nama_pemilik,
            "no_mesin": kendaraan.no_mesin,
            "no_rangka": kendaraan.no_rangka,
            "no_plat": kendaraan.no_plat,
            "jenis_kendaraan": kendaraan.jenis_kendaraan,
            "status": kendaraan.status
        } if kendaraan else {"message": "Kendaraan Tidak Terdaftar"}

        log = ScanLog(plate_text=plate or "PLAT TIDAK TERBACA", is_match=is_match, created_at=now_wib())
        db.add(log)
        db.commit()
        db.close()

        response = {
            "plate": plate,
            "raw": [{"text": t, "prob": float(p)} for (_, t, p) in raw_result],
            "match": kendaraan_data
        }

        set_cache(image_hash, response, expire=300)

        return jsonify(response), 200

    except Exception as e:
        logging.error(f"Unexpected error in OCR detect: {e}")
        return jsonify({"error": "Terjadi kesalahan pada server"}), 500