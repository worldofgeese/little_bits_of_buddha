# Task: Redeploy LBOB with Accept Header Fix

## Context
LBOB is deployed via podman-in-podman from this container. The 406 bug fix (Accept: application/json header) is on main but the running containers haven't been rebuilt.

## What to do

1. Check if compose.production.yaml exists in the project or lbob-deploy directory
2. Find where the LBOB containers are running (check `DOCKER_HOST=tcp://podman-in-podman:2375 docker ps`)
3. Rebuild the lbob-openai image from the latest main code
4. Restart only the openai service container (the telegram service doesn't need rebuilding)
5. Verify the Accept header is in the rebuilt image: `docker exec <container> grep -r "Accept" /app/`
6. Watch logs for 30 seconds to confirm no more 406 errors

## Key details
- DOCKER_HOST=tcp://podman-in-podman:2375 (podman sidecar)
- DOCKER_BUILDKIT=0 (required for rootless podman)
- Project: /home/node/.openclaw/workspace/projects/little_bits_of_buddha
- Previous deploy used compose.production.yaml with Dapr sidecars
- lbob-deploy/ directory may contain the production compose

## Report
Return: what you did, container status after, whether 406 is gone from logs.
Do NOT use message(action: "send"). Return plain text.
