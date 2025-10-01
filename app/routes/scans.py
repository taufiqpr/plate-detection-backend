from flask import Blueprint, jsonify, request, current_app

from ..db import get_scoped_session
from ..models import ScanLog


bp = Blueprint("scans", __name__)


@bp.route("/scans", methods=["GET"])
def get_scans():
    Session = get_scoped_session(current_app)
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


@bp.route("/scans/<int:scan_id>/verify", methods=["POST"])
def verify_scan(scan_id: int):
    data = request.get_json()
    status = data.get("status")

    Session = get_scoped_session(current_app)
    db = Session()
    scan = db.query(ScanLog).filter(ScanLog.id == scan_id).first()
    if not scan:
        db.close()
        return jsonify({"error": "Scan not Found"}), 404

    scan.is_match = status
    db.commit()
    db.close()
    return jsonify({"message": "Scan updated", "id": scan_id, "status": status})


