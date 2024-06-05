# syntax=docker/dockerfile:experimental
FROM scratch AS source
COPY pyproject.toml README.md hatch_build.py /
COPY src/ /src/

FROM alpine:latest AS sass
ARG DART_SASS_VERSION=1.77.4
ARG DART_SASS_TAR=dart-sass-${DART_SASS_VERSION}-linux-x64-musl.tar.gz
ARG DART_SASS_URL=https://github.com/sass/dart-sass/releases/download/${DART_SASS_VERSION}/${DART_SASS_TAR}
ADD ${DART_SASS_URL} /opt/
RUN cd /opt/ && tar -xzf ${DART_SASS_TAR} && rm ${DART_SASS_TAR}
RUN --mount=type=bind,from=source,target=/memoria,source=/,rw \
    mkdir -p /tmp/static && mkdir /tmp/templates \
 && cd /memoria/src/memoria/web/www && /opt/dart-sass/sass static/:/tmp/static/ templates/:/tmp/templates/

FROM python:3.12-alpine
CMD ["uvicorn", "memoria.web:APP", "--host", "0.0.0.0", "--port", "80"]
EXPOSE 80
RUN --mount=type=bind,from=source,target=/memoria,source=/,rw --mount=type=bind,from=sass,target=/sass,source=/tmp,ro --mount=type=cache,target=/cache --mount=type=tmpfs,target=/temp \
    find /memoria -iname '*.scss' -delete \
 && cp -rt /memoria/src/memoria/web/www /sass/* \
 && TMPDIR=/temp python -m pip install --cache-dir=/cache /memoria[uvicorn] \
 && mkdir /data
