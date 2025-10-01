import re
from typing import List, Optional, Tuple
import cv2
import numpy as np
import easyocr


_reader = easyocr.Reader(['en'], gpu=False)

_similar_map = {"0": "O", "1": "I", "4": "A", "8": "B", "5": "S"}


def _correct_similar(text: str, only_letters: bool = False) -> str:
    if only_letters:
        return "".join([_similar_map.get(ch, ch) if ch.isalpha() else ch for ch in text])
    return "".join([_similar_map.get(ch, ch) for ch in text])


def preprocess(img: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    resized = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(resized, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def _clean_and_order(result) -> List[str]:
    ordered = sorted(result, key=lambda r: r[0][0][0])
    texts = []
    for (_, text, prob) in ordered:
        text = text.strip().upper()
        texts.append(text)
    return texts


def _extract_plate_from_parts(parts: List[str]) -> Optional[str]:
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
            if huruf_awal:
                break
        if huruf_awal:
            break

    if huruf_awal and angka and huruf_akhir:
        huruf_awal = _correct_similar(huruf_awal, only_letters=True)
        huruf_akhir = _correct_similar(huruf_akhir, only_letters=True)
        return f"{huruf_awal} {angka} {huruf_akhir}"
    return None


def ocr_plate(img: np.ndarray) -> Tuple[Optional[str], list]:
    result = _reader.readtext(img, allowlist="ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")
    parts = _clean_and_order(result)
    plate = _extract_plate_from_parts(parts)
    return plate, result


def shutdown_reader():
    try:
        _reader.close()
    except Exception:
        pass


