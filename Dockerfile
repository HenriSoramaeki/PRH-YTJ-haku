# Yksi kuva: React-build + FastAPI (Render, Fly jne.)
# EK_PROJECT_ROOT=/srv → frontend/dist ja backend rinnakkain

FROM node:25-alpine AS frontend-build
WORKDIR /src
COPY frontend/package.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
WORKDIR /srv/backend

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV EK_PROJECT_ROOT=/srv

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./
COPY --from=frontend-build /src/dist /srv/frontend/dist

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
