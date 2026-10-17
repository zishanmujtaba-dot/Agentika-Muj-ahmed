FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    HF_HOME=/opt/model-cache PORT=3000
WORKDIR /app
COPY requirements.txt ./
# CPU-only torch avoids installing the much larger CUDA runtime on cloud CPU workers.
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r requirements.txt
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2', device='cpu')"
COPY app ./app
COPY web ./web
COPY scripts ./scripts
COPY database ./database
COPY data ./data
RUN useradd --uid 10001 --create-home echo \
    && chmod +x scripts/start.sh \
    && chown -R echo:echo /app /opt/model-cache
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
USER echo
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','3000')+'/ready',timeout=8)"
CMD ["sh", "scripts/start.sh"]
