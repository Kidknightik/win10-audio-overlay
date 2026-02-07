#!/usr/bin/env bash
set -euo pipefail

if ! command -v kwriteconfig6 >/dev/null 2>&1; then
  echo "kwriteconfig6 not found. Install plasma-workspace." >&2
  exit 1
fi

# Disable Plasma OSD
kwriteconfig6 --file plasmarc --group OSD --key Enabled false

# Ensure volume keys are bound (kmix defaults)
kwriteconfig6 --file kglobalshortcutsrc --group kmix --key increase_volume "Volume Up,Volume Up,Увеличить громкость"
kwriteconfig6 --file kglobalshortcutsrc --group kmix --key decrease_volume "Volume Down,Volume Down,Уменьшить громкость"
kwriteconfig6 --file kglobalshortcutsrc --group kmix --key mute "Volume Mute,Volume Mute,Выключить звук"

# Reload configs (best-effort)
if command -v qdbus6 >/dev/null 2>&1; then
  qdbus6 org.kde.KWin /KWin reconfigure >/dev/null 2>&1 || true
  qdbus6 org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.restart >/dev/null 2>&1 || true
  qdbus6 org.kde.kglobalaccel /kglobalaccel org.kde.KGlobalAccel.reconfigure >/dev/null 2>&1 || true
fi

echo "Plasma OSD disabled and volume keys ensured."
