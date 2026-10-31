FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY realip.conf /etc/nginx/realip.conf
COPY docker-entrypoint.d/40-trusted-proxy.sh /docker-entrypoint.d/40-trusted-proxy.sh
RUN sed -i 's/\r$//' /docker-entrypoint.d/40-trusted-proxy.sh \
    && chmod +x /docker-entrypoint.d/40-trusted-proxy.sh

EXPOSE 80

HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
    CMD wget -q -O- http://127.0.0.1:80/api/v1/health || exit 1
