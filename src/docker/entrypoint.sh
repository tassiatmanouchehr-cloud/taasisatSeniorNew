#!/bin/bash
set -e

# Wait for PostgreSQL to be ready
if [ -n "$DATABASE_HOST" ]; then
    echo "Waiting for PostgreSQL at $DATABASE_HOST:${DATABASE_PORT:-5432}..."
    while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('$DATABASE_HOST', ${DATABASE_PORT:-5432}))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
        echo "PostgreSQL not ready, retrying in 1s..."
        sleep 1
    done
    echo "PostgreSQL is ready."
fi

# Wait for Redis to be ready
if [ -n "$REDIS_HOST" ]; then
    echo "Waiting for Redis at $REDIS_HOST:${REDIS_PORT:-6379}..."
    while ! python -c "
import socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.connect(('$REDIS_HOST', ${REDIS_PORT:-6379}))
    s.close()
    exit(0)
except:
    exit(1)
" 2>/dev/null; do
        echo "Redis not ready, retrying in 1s..."
        sleep 1
    done
    echo "Redis is ready."
fi

exec "$@"
