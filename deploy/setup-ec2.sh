#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="/opt/totem"
APP_USER="totem"
ENV_FILE="/etc/totem/totem.env"

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run with sudo: sudo bash deploy/setup-ec2.sh" >&2
  exit 1
fi

if [[ ! -f "${APP_DIR}/backend/pyproject.toml" ]]; then
  echo "Deploy the repository to ${APP_DIR} before running this script." >&2
  exit 1
fi

apt-get update
apt-get install -y python3 python3-venv python3-pip nginx curl ca-certificates gnupg

if ! command -v node >/dev/null || [[ "$(node --version | tr -d v | cut -d. -f1)" -lt 20 ]]; then
  install -d -m 0755 /etc/apt/keyrings
  curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor --yes -o /etc/apt/keyrings/nodesource.gpg
  echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_22.x nodistro main" > /etc/apt/sources.list.d/nodesource.list
  apt-get update
  apt-get install -y nodejs
fi

id -u "${APP_USER}" >/dev/null 2>&1 || useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin "${APP_USER}"
chown -R "${APP_USER}:${APP_USER}" "${APP_DIR}"
install -d -m 0750 -o "${APP_USER}" -g "${APP_USER}" \
  /srv/totem-data \
  /srv/totem-data/images \
  /srv/totem-data/temp

sudo -u "${APP_USER}" python3 -m venv "${APP_DIR}/.venv"
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install --upgrade pip
sudo -u "${APP_USER}" "${APP_DIR}/.venv/bin/pip" install -e "${APP_DIR}/backend[postgres]" gunicorn
sudo -u "${APP_USER}" npm --prefix "${APP_DIR}/frontend" ci
sudo -u "${APP_USER}" npm --prefix "${APP_DIR}/frontend" run build

install -d -m 0750 -o root -g "${APP_USER}" /etc/totem
if [[ ! -f "${ENV_FILE}" ]]; then
  install -m 0640 -o root -g "${APP_USER}" "${APP_DIR}/.env.example" "${ENV_FILE}"
  echo "Created ${ENV_FILE}. Fill production secrets, then run this script again." >&2
  exit 2
fi

install -m 0644 "${APP_DIR}/deploy/systemd/totem-api.service" /etc/systemd/system/totem-api.service
install -m 0644 "${APP_DIR}/deploy/systemd/totem-cleanup.service" /etc/systemd/system/totem-cleanup.service
install -m 0644 "${APP_DIR}/deploy/systemd/totem-cleanup.timer" /etc/systemd/system/totem-cleanup.timer
install -m 0644 "${APP_DIR}/deploy/nginx/totem.conf" /etc/nginx/sites-available/totem
ln -sfn /etc/nginx/sites-available/totem /etc/nginx/sites-enabled/totem
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable --now totem-api
systemctl enable --now totem-cleanup.timer
nginx -t
systemctl enable --now nginx
systemctl reload nginx

echo "Deployment complete. Check: systemctl status totem-api"
