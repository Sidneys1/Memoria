# syntax=docker/dockerfile:experimental
FROM scratch AS source
COPY pyproject.toml README.md hatch_build.py /
COPY src/ /src/

FROM python:3.12-alpine
CMD ["uvicorn", "memoria.web:APP", "--host", "0.0.0.0", "--port", "80"]
EXPOSE 80
RUN --mount=type=bind,from=source,target=/memoria,source=/,rw --mount=type=cache,target=/cache --mount=type=tmpfs,target=/temp \
    TMPDIR=/temp python -m pip install --cache-dir=/cache /memoria[uvicorn] \
 && mkdir /data
