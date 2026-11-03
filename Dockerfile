FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Railway runs this app on CPU. Install the CPU wheel before sentence-transformers
# so pip does not add CUDA packages to the image.
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir 'torch==2.7.0+cpu' \
        --index-url https://download.pytorch.org/whl/cpu \
    && python -m pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "app.py"]
