#!/bin/sh
set -eu
echo "=== Building container ==="
podman build --storage-driver=vfs -t little-bits-of-buddha:ci -f Dockerfile .
