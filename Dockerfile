FROM python:3.12-alpine

LABEL org.opencontainers.image.title="claims-reporting-service" \
      org.opencontainers.image.description="Claims Reporting Service (DEMO-CRS), fictional demo application"

RUN adduser -D -H -u 10001 crs
WORKDIR /srv/crs
COPY app/ ./app/
COPY config/ ./config/

ENV PYTHONPATH=/srv/crs/app \
    PYTHONUNBUFFERED=1 \
    CRS_CONFIG=/srv/crs/config/application.yaml

USER crs
EXPOSE 8080
CMD ["python3", "-m", "crs_service"]
