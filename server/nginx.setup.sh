#!/bin/bash
# Update nginx config for demo-1 and reload nginx

set -e

cp "$(dirname "$0")/nginx.conf" /etc/nginx/conf.d/demo-1.conf
nginx -t
systemctl reload nginx

echo "nginx config updated and reloaded successfully." 