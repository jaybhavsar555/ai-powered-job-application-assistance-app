#!/usr/bin/env bash
# Build & push distributable images (maintainer only).
# Never bake secrets into the image — users supply .env.dist.
#
# Usage:
#   export DOCKERHUB_USER=youruser
#   export TAG=1.0.0
#   ./scripts/dist-publish.sh
#
# Then tell users to set in .env.dist:
#   API_IMAGE=youruser/career-os-api:1.0.0
#   WEB_IMAGE=youruser/career-os-web:1.0.0
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

USER_NS="${DOCKERHUB_USER:?Set DOCKERHUB_USER (Docker Hub or GHCR namespace)}"
TAG="${TAG:-latest}"
REGISTRY="${REGISTRY:-docker.io}"

API_IMAGE="${REGISTRY%/}/${USER_NS}/career-os-api:${TAG}"
WEB_IMAGE="${REGISTRY%/}/${USER_NS}/career-os-web:${TAG}"
# docker.io/user/img → user/img for Hub convenience
if [[ "$REGISTRY" == "docker.io" ]]; then
  API_IMAGE="${USER_NS}/career-os-api:${TAG}"
  WEB_IMAGE="${USER_NS}/career-os-web:${TAG}"
fi

API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8001/api/v1}"

echo "==> Building API → ${API_IMAGE}"
docker build -t "${API_IMAGE}" ./backend

echo "==> Building Web → ${WEB_IMAGE}"
docker build \
  --build-arg "NEXT_PUBLIC_API_URL=${API_URL}" \
  -t "${WEB_IMAGE}" \
  ./frontend

echo "==> Pushing…"
docker push "${API_IMAGE}"
docker push "${WEB_IMAGE}"

echo ""
echo "Published:"
echo "  ${API_IMAGE}"
echo "  ${WEB_IMAGE}"
echo ""
echo "Users set in .env.dist:"
echo "  API_IMAGE=${API_IMAGE}"
echo "  WEB_IMAGE=${WEB_IMAGE}"
echo "Then: ./scripts/dist-setup.sh"
echo ""
echo "Offline alternative (large files):"
echo "  docker save ${API_IMAGE} ${WEB_IMAGE} -o career-os-images.tar"
echo "  # receiver: docker load -i career-os-images.tar"
