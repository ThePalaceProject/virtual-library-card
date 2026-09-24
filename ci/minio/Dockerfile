# MinIO withdrew anonymous public access to its own image from both Docker Hub and quay.io, so
# this pulls from the Palace mirror of the upstream release instead. The mirror is an unmodified
# MinIO build, published from the ci-scripts repo:
# https://github.com/ThePalaceProject/ci-scripts/blob/main/images/minio/Dockerfile
# The tag is pinned deliberately; the mirror publishes no `latest`.
FROM ghcr.io/thepalaceproject/palace-ci-minio:RELEASE.2025-09-07T16-13-09Z

ENV MINIO_ROOT_USER=vlc-minio
ENV MINIO_ROOT_PASSWORD=123456789

EXPOSE 9000 9001

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Override the default entrypoint
ENTRYPOINT ["/bin/sh"]
CMD ["/usr/local/bin/entrypoint.sh"]
