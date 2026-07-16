# syntax=docker/dockerfile:1.7
FROM certbot/certbot:v5.1.0

RUN addgroup -S -g 10001 certbot-group \
    && adduser -S -D -H -u 10001 -G certbot-group certbot-user \
    && mkdir -p /etc/letsencrypt /var/www/certbot /var/lib/letsencrypt /var/log/letsencrypt \
    && chown -R 10001:10001 \
        /etc/letsencrypt \
        /var/www/certbot \
        /var/lib/letsencrypt \
        /var/log/letsencrypt

USER 10001:10001
