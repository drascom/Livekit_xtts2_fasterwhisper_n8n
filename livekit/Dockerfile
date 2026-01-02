# syntax=docker/dockerfile:1

FROM livekit/livekit-server:latest

WORKDIR /app

COPY entrypoint.sh /entrypoint.sh
COPY livekit.yaml /app/livekit.yaml
RUN apk add --no-cache gettext
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
