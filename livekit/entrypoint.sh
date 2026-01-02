#!/bin/sh
set -e

# Find livekit-server binary
BIN="$(command -v livekit-server || true)"
if [ -z "$BIN" ]; then
  # Fallback common locations
  for path in /livekit-server /bin/livekit-server /usr/bin/livekit-server /usr/local/bin/livekit-server; do
    if [ -x "$path" ]; then
      BIN="$path"
      break
    fi
  done
fi

if [ -z "$BIN" ]; then
  echo "livekit-server binary not found in PATH or common locations" >&2
  exit 1
fi

# Extract host from LIVEKIT_URL (e.g., wss://hostname/path -> hostname)
export LIVEKIT_HOST=$(echo $LIVEKIT_URL | cut -d'/' -f3 | cut -d':' -f1)
# Determine node IP for internal candidates (prefer host LAN IP when provided)
if [ -n "$CAAL_HOST_IP" ]; then
  export LIVEKIT_NODE_IP="$CAAL_HOST_IP"
else
  export LIVEKIT_NODE_IP=$(hostname -i | awk '{print $1}')
fi

# Allow toggling external IP discovery for ICE
USE_EXTERNAL_IP="${LIVEKIT_USE_EXTERNAL_IP:-true}"
case "$USE_EXTERNAL_IP" in
  true|false) ;;
  *) USE_EXTERNAL_IP="true" ;;
esac

# Substitute environment variables in the config file
sed -e "s/API_KEY_PLACEHOLDER/${LIVEKIT_API_KEY}/g" \
    -e "s/API_SECRET_PLACEHOLDER/${LIVEKIT_API_SECRET}/g" \
    -e "s/NODE_IP_PLACEHOLDER/${LIVEKIT_NODE_IP}/g" \
    -e "s/USE_EXTERNAL_IP_PLACEHOLDER/${USE_EXTERNAL_IP}/g" \
    /app/livekit.yaml > /app/livekit.conf

# Start the livekit-server with the generated config file
exec "$BIN" --config /app/livekit.conf
