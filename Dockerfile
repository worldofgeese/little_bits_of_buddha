# syntax=docker/dockerfile:1

# Comments are provided throughout this file to help you get started.
# If you need more help, visit the Dockerfile reference guide at
# https://docs.docker.com/engine/reference/builder/

ARG PYTHON_VERSION=3.11.3
FROM cgr.dev/chainguard/python:${PYTHON_VERSION}-dev as telegram-bot-service-builder

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

USER root

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,mode=0777,target=/root/.cache/pip \
    --mount=type=bind,source=src/telegram_bot_service_worldofgeese/requirements.txt,target=requirements.txt \
    pip install -r requirements.txt --user

FROM cgr.dev/chainguard/python:${PYTHON_VERSION} as telegram-bot-service-production

USER root

# Change ownership of process files to non-privileged user that the app will run under.
# See https://developers.redhat.com/articles/2021/11/11/best-practices-building-images-pass-red-hat-container-certification#best_practice__3__set_group_ownership_and_file_permissions
# Copy package dependencies into container.
COPY --from=telegram-bot-service-builder --chown=65332:0 --chmod=775 /root/.local/lib/python3.11/site-packages /home/nonroot/.local/lib/python3.11/site-packages

# Switch the working directory to the non-privileged user.
WORKDIR /home/nonroot

# Switch to the non-privileged user to run the application.
USER nonroot

# Copy tests separately to allow testing inside remote cluster.
COPY --chown=65332:0 --chmod=775 tests tests

# Copy the source code into the container.
COPY --chown=65332:0 --chmod=775 src/telegram_bot_service_worldofgeese telegram_bot_service_worldofgeese/

# Expose the port that the application listens on.
EXPOSE 8090

# Run the application.
ENTRYPOINT ["python", "-m", "telegram_bot_service_worldofgeese"]

FROM cgr.dev/chainguard/python:${PYTHON_VERSION}-dev as openai-service-builder

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

USER root

# Download dependencies as a separate step to take advantage of Docker's caching.
# Leverage a cache mount to /root/.cache/pip to speed up subsequent builds.
# Leverage a bind mount to requirements.txt to avoid having to copy them into
# into this layer.
RUN --mount=type=cache,mode=0777,target=/root/.cache/pip \
    --mount=type=bind,source=src/openai_service_worldofgeese/requirements.txt,target=requirements.txt \
    pip install -r requirements.txt --user

FROM cgr.dev/chainguard/python:${PYTHON_VERSION} as openai-service-production

USER root

# Change ownership of process files to non-privileged user that the app will run under.
# See https://developers.redhat.com/articles/2021/11/11/best-practices-building-images-pass-red-hat-container-certification#best_practice__3__set_group_ownership_and_file_permissions
# Copy package dependencies into container.
COPY --from=openai-service-builder --chown=65332:0 --chmod=775 /root/.local/lib/python3.11/site-packages /home/nonroot/.local/lib/python3.11/site-packages

# Switch the working directory to the non-privileged user.
WORKDIR /home/nonroot

# Switch to the non-privileged user to run the application.
USER nonroot

# Copy tests separately to allow testing inside remote cluster.
COPY --chown=65332:0 --chmod=775 tests tests

# Copy the source code into the container.
COPY --chown=65332:0 --chmod=775 src/openai_service_worldofgeese openai_service_worldofgeese/

# Expose the port that the application listens on.
EXPOSE 8080

# Run the application.
ENTRYPOINT ["python", "-m", "openai_service_worldofgeese"]
