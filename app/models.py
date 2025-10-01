from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import declarative_base


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


