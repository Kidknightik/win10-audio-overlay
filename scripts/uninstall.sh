#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

systemctl --user disable --now win10-osd.service >/dev/null 2>&1 || true
rm -f "$HOME/.config/systemd/user/win10-osd.service"
systemctl --user daemon-reload

echo "Uninstalled service. Config and project files kept at $ROOT."
