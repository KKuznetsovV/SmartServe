FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

HEALTHCHECK --interval=5s --timeout=3s --retries=10 \
    CMD wget -q -O- http://127.0.0.1:80/api/v1/health || exit 1
