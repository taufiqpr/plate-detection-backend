from flask import Blueprint, current_app, jsonify, request
import numpy as np
import cv2

from ..db import get_scoped_session
from ..models import Kendaraan, ScanLog
from ..services.ocr import preprocess, ocr_plate


bp = Blueprint("detect", __name__)


@bp.route("/detect", methods=["POST"])
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

    Session = get_scoped_session(current_app)

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


