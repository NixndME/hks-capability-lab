# HKS Capability Lab -- portal container.
#
# Single production image: FastAPI backend + built React frontend, served
# from one process on one port. Build/run with Podman:
#
#   podman build -t hks-capability-lab:dev -f Containerfile .
#   podman run --rm -p 8080:8080 hks-capability-lab:dev
#   podman run --rm -p 8080:8080 -v ~/.kube:/home/hkslab/.kube:ro hks-capability-lab:dev   # Kubernetes-connected
#     (runtime user is non-root "hkslab", home /home/hkslab -- not /root)

FROM node:22-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* /frontend/
RUN npm install
COPY frontend/ /frontend/
RUN npm run build

FROM python:3.12-slim AS runtime

WORKDIR /app

# kubectl/helm are deliberately NOT bundled into this image -- the backend
# talks to Kubernetes via the Python client, not by shelling out.

COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

COPY backend/app /app/backend/app
COPY tests/definitions /app/tests/definitions
COPY --from=frontend-build /frontend/dist /app/frontend/dist

RUN useradd --system --create-home --uid 10001 hkslab
USER hkslab

ENV PYTHONUNBUFFERED=1 \
    PORTAL_MODE=local \
    PORT=8080

WORKDIR /app/backend
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=2)" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
