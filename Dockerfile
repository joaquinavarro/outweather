# ROOTSHIFT — single image, single port.
# Stage 1 builds the web app into static files; stage 2 serves them and the API.

FROM node:22-slim AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./
COPY --from=web /web/out /app/frontend/out

ENV DATA_MODE=demo \
    PYTHONUNBUFFERED=1
EXPOSE 8000

# One process serves the API and the built site at "/".
CMD ["python", "-m", "rootshift", "--host", "0.0.0.0"]
