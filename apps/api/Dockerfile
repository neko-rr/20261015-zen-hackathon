FROM python:3.12-slim

WORKDIR /app

# MediaPipe は OpenCV 経由で libxcb / libGL を読む。slim には入っていない。
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
    curl \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libxcb1 \
    libsm6 \
    libxext6 \
    libxrender1 \
  && mkdir -p /app/app/models \
  && curl -fsSL -o /app/app/models/pose_landmarker_full.task \
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/latest/pose_landmarker_full.task" \
  && curl -fsSL -o /app/app/models/hand_landmarker.task \
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task" \
  && curl -fsSL -o /app/app/models/selfie_segmenter.tflite \
    "https://storage.googleapis.com/mediapipe-models/image_segmenter/selfie_segmenter/float16/latest/selfie_segmenter.tflite" \
  && apt-get purge -y curl \
  && apt-get autoremove -y \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

EXPOSE 8080
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
