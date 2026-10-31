#!/bin/sh
# Optional ngx_http_realip_module config so a trusted load balancer in front of
# this gateway can pass the real client IP. Default: unset (no realip).
set -eu

CONF=/etc/nginx/realip.conf
: >"$CONF"

cidrs=${TRUSTED_PROXY_CIDRS:-}
if [ -z "$cidrs" ]; then
    exit 0
fi

{
    echo "real_ip_header X-Forwarded-For;"
    echo "real_ip_recursive on;"
} >>"$CONF"

old_ifs=$IFS
IFS=,
# shellcheck disable=SC2086
set -- $cidrs
IFS=$old_ifs

for cidr in "$@"; do
    cidr=$(printf '%s' "$cidr" | tr -d '[:space:]')
    [ -z "$cidr" ] && continue
    case $cidr in
    *[!0-9a-fA-F.:/]*)
        echo "TRUSTED_PROXY_CIDRS contains an invalid CIDR: $cidr" >&2
        exit 1
        ;;
    esac
    echo "set_real_ip_from $cidr;" >>"$CONF"
done
