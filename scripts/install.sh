#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_deps() {
  if need_cmd pacman; then
    local pkgs=(python pyside6 qt6-declarative qt6-tools playerctl)
    sudo pacman -S --needed "${pkgs[@]}" || true
    sudo pacman -S --needed plasma-browser-integration || true
    if ! need_cmd pactl; then
      if ! sudo pacman -S --needed pipewire pipewire-pulse; then
        sudo pacman -S --needed pulseaudio || true
      fi
    fi
    return
  fi

  if need_cmd apt-get; then
    sudo apt-get update -y
    sudo apt-get install -y \
      python3 \
      python3-pyside6 \
      qt6-declarative \
      qml6-module-qtquick \
      qml6-module-qtquick-window2 \
      qt6-tools-dev-tools \
      pulseaudio-utils \
      playerctl \
      plasma-browser-integration || true
    return
  fi

  if need_cmd dnf; then
    sudo dnf install -y \
      python3 \
      python3-pyside6 \
      qt6-qtdeclarative \
      qt6-qttools \
      pulseaudio-utils \
      playerctl \
      plasma-browser-integration || true
    return
  fi

  echo "No supported package manager found. Install dependencies manually." >&2
}

install_service() {
  mkdir -p "$HOME/.config/systemd/user"
  sed "s|@ROOT@|$ROOT|g" "$ROOT/systemd/win10-osd.service" > "$HOME/.config/systemd/user/win10-osd.service"
  systemctl --user daemon-reload
  systemctl --user enable --now win10-osd.service
}

case "${1:-}" in
  --no-deps)
    install_service
    "$ROOT/scripts/setup-kde.sh"
    ;;
  *)
    install_deps
    install_service
    "$ROOT/scripts/setup-kde.sh"
    ;;
esac

echo "Install complete."
