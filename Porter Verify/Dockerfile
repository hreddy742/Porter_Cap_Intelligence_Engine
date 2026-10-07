# Multi-stage image for the Porter Verify API.
# Stage 1 builds a wheel + installs deps; stage 2 is a slim runtime.
# Pinned base image; runs as a non-root user.

FROM python:3.12-slim AS build
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --upgrade pip && pip wheel --wheel-dir /wheels .

FROM python:3.12-slim AS runtime
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
# Non-root runtime user.
RUN useradd --create-home --uid 10001 porter
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*.whl && rm -rf /wheels
COPY src ./src
USER porter
EXPOSE 8000
CMD ["uvicorn", "porter_verify.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
