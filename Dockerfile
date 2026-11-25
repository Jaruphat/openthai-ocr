# OpenThai OCR — API + หน้าเว็บอัปโหลดไฟล์ (CPU ล้วน ไม่ต้องมี GPU)
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app.py .
COPY static ./static
EXPOSE 8000
# WORKERS = จำนวนงานที่อ่านพร้อมกันได้ (แนะนำ = จำนวน vCPU, ใช้ RAM ราว 0.5 GB ต่อ worker)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port 8000 --workers ${WORKERS:-1}"]
