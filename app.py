"""OpenThai OCR — API + หน้าเว็บอัปโหลดไฟล์ ในโปรแกรมเดียว

GET  /            หน้าเว็บสำหรับอัปโหลดรูป/PDF
GET  /api/health  เช็กว่าระบบพร้อม
POST /api/ocr     ส่งไฟล์ (multipart field "file") -> ข้อความที่ถอดได้
"""
import asyncio
import os
import sys
import time
from pathlib import Path

import pypdfium2 as pdfium
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

MODEL_DIR = os.environ.get("MODEL_DIR", "/model")
sys.path.insert(0, MODEL_DIR)
from runtime.line_engine import LineOCR  # noqa: E402  (มากับโมเดลที่ดาวน์โหลด)

MODEL_NAME = os.environ.get("MODEL_NAME", "OpenThai2.1-OCR-Text v2.1.4")
API_KEY = os.environ.get("API_KEY", "").strip()          # ว่าง = ไม่ต้องใส่รหัส
MAX_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))
MAX_PAGES = int(os.environ.get("MAX_PDF_PAGES", "20"))
PDF_DPI = int(os.environ.get("PDF_DPI", "200"))

ocr = LineOCR(MODEL_DIR, threads=int(os.environ.get("OCR_THREADS", "1")))
lock = asyncio.Lock()  # 1 worker อ่านทีละหน้า
app = FastAPI(title="OpenThai OCR", docs_url="/api/docs", openapi_url="/api/openapi.json")
STATIC = Path(__file__).parent / "static"


def pdf_to_images(data: bytes):
    pdf = pdfium.PdfDocument(data)
    try:
        if len(pdf) > MAX_PAGES:
            raise HTTPException(413, f"PDF มี {len(pdf)} หน้า เกินที่ตั้งไว้ {MAX_PAGES} หน้า")
        return [pdf[i].render(scale=PDF_DPI / 72).to_pil().convert("RGB") for i in range(len(pdf))]
    finally:
        pdf.close()


@app.get("/", include_in_schema=False)
async def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/health")
async def health():
    return {"ok": True, "model": MODEL_NAME, "auth": bool(API_KEY),
            "max_upload_mb": MAX_MB, "max_pdf_pages": MAX_PAGES}


@app.post("/api/ocr")
async def read_file(file: UploadFile = File(...), x_api_key: str = Header(default="")):
    if API_KEY and x_api_key != API_KEY:
        raise HTTPException(401, "รหัส API ไม่ถูกต้อง")
    data = await file.read()
    if not data:
        raise HTTPException(400, "ไฟล์ว่าง")
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"ไฟล์ใหญ่เกิน {MAX_MB} MB")

    t0 = time.time()
    try:
        images = await run_in_threadpool(pdf_to_images, data) if data[:5] == b"%PDF-" else [data]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, "เปิดไฟล์ PDF ไม่ได้")

    pages = []
    for no, image in enumerate(images, 1):
        try:
            async with lock:
                r = await run_in_threadpool(ocr.read, image)
        except Exception:
            raise HTTPException(400, "อ่านไฟล์ไม่ได้ รองรับ JPG, PNG, WEBP, TIFF และ PDF")
        pages.append({"page": no, "text": r["text"], "lines": len(r.get("lines", [])),
                      "rotation": r.get("rotation", 0)})

    return {"model": MODEL_NAME, "file": file.filename, "pages": pages,
            "text": "\n\n".join(p["text"] for p in pages),
            "seconds": round(time.time() - t0, 2)}
