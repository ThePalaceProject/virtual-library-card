FROM minio/minio:latest

ENV MINIO_ROOT_USER=vlc-minio
ENV MINIO_ROOT_PASSWORD=123456789

EXPOSE 9000 9001

# Copy the entrypoint script
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Override the default entrypoint
ENTRYPOINT ["/bin/sh"]
CMD ["/usr/local/bin/entrypoint.sh"]
