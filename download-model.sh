#!/usr/bin/env bash
# ดาวน์โหลด OpenThai2.1-OCR-Text (iApp, Apache-2.0) จาก Hugging Face แบบตรึงเวอร์ชัน
set -euo pipefail
REPO="iapp/OpenThai2.1-OCR-Text-20261118"
REV="${REV:-v2.1.4}"
FILES="NOTICE README.md SHA256SUMS config.json det.onnx det.yml rec.onnx rec2.onnx rec_dict.txt requirements.txt runtime/__init__.py runtime/line_engine.py runtime/thai_norm.py"
mkdir -p model/runtime
for f in $FILES; do
  echo "↓ $f"
  curl -fsSL "https://huggingface.co/$REPO/resolve/$REV/$f" -o "model/$f"
done
cd model && sha256sum -c SHA256SUMS --ignore-missing
echo "✔ ดาวน์โหลดโมเดล $REPO@$REV เรียบร้อย"
