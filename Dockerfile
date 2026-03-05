FROM python:3.12-slim as base-builder

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install git for pip installing from git repos (triogram)
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# --- telegram-bot-service ---
FROM base-builder as telegram-bot-service-builder
COPY src/telegram_bot_service_worldofgeese/requirements.txt /tmp/requirements.txt
# Install triogram without its pinned deps (trio==0.22.* conflicts with anyio 4.x)
# Then install requirements which pull trio>=0.25.0 to fix the anyio/trio mismatch
RUN pip install --no-cache-dir --no-deps 'triogram @ git+https://github.com/worldofgeese/triogram@1b01daa' && \
    pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim as telegram-bot-service-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=telegram-bot-service-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=telegram-bot-service-builder /usr/local/bin /usr/local/bin
WORKDIR /app
RUN useradd --create-home nonroot
USER nonroot
COPY --chown=nonroot:nonroot src/telegram_bot_service_worldofgeese telegram_bot_service_worldofgeese/
EXPOSE 8090
ENTRYPOINT ["python", "-m", "telegram_bot_service_worldofgeese"]

# --- openai-service ---
FROM base-builder as openai-service-builder
COPY src/openai_service_worldofgeese/requirements.txt /tmp/requirements.txt
# Install CPU-only PyTorch first (avoids 2GB+ CUDA downloads)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim as openai-service-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=openai-service-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=openai-service-builder /usr/local/bin /usr/local/bin
WORKDIR /app
RUN useradd --create-home nonroot
USER nonroot
COPY --chown=nonroot:nonroot src/openai_service_worldofgeese openai_service_worldofgeese/
COPY --chown=nonroot:nonroot sutta_corpus/ sutta_corpus/
COPY --chown=nonroot:nonroot scripts/embed_suttas.py embed_suttas.py
COPY --chown=nonroot:nonroot scripts/entrypoint.sh entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["bash", "/app/entrypoint.sh"]

# --- seeker-actor-service ---
FROM base-builder as seeker-actor-service-builder
COPY src/seeker_actor_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim as seeker-actor-service-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=seeker-actor-service-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=seeker-actor-service-builder /usr/local/bin /usr/local/bin
WORKDIR /app
RUN useradd --create-home nonroot
USER nonroot
COPY --chown=nonroot:nonroot src/seeker_actor_service seeker_actor_service/
EXPOSE 8081
ENTRYPOINT ["python", "-m", "seeker_actor_service"]

# --- wisdom-service ---
FROM base-builder as wisdom-service-builder
COPY src/wisdom_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim as wisdom-service-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=wisdom-service-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=wisdom-service-builder /usr/local/bin /usr/local/bin
WORKDIR /app
RUN useradd --create-home nonroot
USER nonroot
COPY --chown=nonroot:nonroot src/wisdom_service wisdom_service/
COPY --chown=nonroot:nonroot sutta_corpus/ sutta_corpus/
COPY --chown=nonroot:nonroot scripts/embed_suttas.py embed_suttas.py
COPY --chown=nonroot:nonroot scripts/entrypoint.sh entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["bash", "/app/entrypoint.sh"]

# --- meditation-workflow-service ---
FROM base-builder as meditation-workflow-service-builder
COPY src/meditation_workflow_service/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

FROM python:3.12-slim as meditation-workflow-service-production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY --from=meditation-workflow-service-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=meditation-workflow-service-builder /usr/local/bin /usr/local/bin
WORKDIR /app
RUN useradd --create-home nonroot
USER nonroot
COPY --chown=nonroot:nonroot src/meditation_workflow_service meditation_workflow_service/
EXPOSE 8003
ENTRYPOINT ["python", "-m", "meditation_workflow_service"]
