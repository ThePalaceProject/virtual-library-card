#!/bin/sh
set -e

# Start MinIO server in the background
minio server /data --address "0.0.0.0:9000" --console-address "0.0.0.0:9001" &

# Store the PID
MINIO_PID=$!

# Wait for MinIO to be ready
echo "Waiting for MinIO to start..."
until curl -sf http://localhost:9000/minio/health/live > /dev/null 2>&1; do
    sleep 1
done
echo "MinIO is ready"

# Configure MinIO client
mc alias set myminio http://localhost:9000 ${MINIO_ROOT_USER} ${MINIO_ROOT_PASSWORD}

# Create the bucket
echo "Creating bucket: vlc-test"
mc mb myminio/vlc-test --ignore-existing

# Set the bucket policy to public (download policy)
echo "Setting bucket policy to download (public read)"
mc anonymous set download myminio/vlc-test

echo "MinIO setup complete"

# Wait for MinIO process
wait $MINIO_PID
