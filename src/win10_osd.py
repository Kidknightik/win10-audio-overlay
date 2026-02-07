#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
import threading
from typing import Any, Dict, Optional

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, Qt, QMetaObject
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtDBus import QDBusConnection, QDBusInterface, QDBusReply

SERVICE_NAME = "com.github.win10osd"
OBJECT_PATH = "/OSD"
INTERFACE_NAME = "com.github.win10osd"
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

DEFAULT_CONFIG = {
    "width": 430,
    "height": 150,
    "timeout_ms": 1800,
    "anchor": "top_left",
    "margin_x": 24,
    "margin_y": 24,
    "background_color": "#DD1C1C1C",
    "accent_color": "#00A4EF",
    "text_color": "#F2F2F2",
    "font_family": "Noto Sans",
    "show_player": True,
    "step_percent": 5,
    "listen_pactl": True,
    "listen_media": True,
    "max_volume": 150,
}


def load_config(config_path: str) -> Dict[str, Any]:
    if not os.path.exists(config_path):
        return DEFAULT_CONFIG.copy()
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    return merged


def _run(cmd: list[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="ignore")
    except Exception:
        return ""


def get_volume() -> int:
    out = _run(["pactl", "get-sink-volume", "@DEFAULT_SINK@"])
    for token in out.split():
        if token.endswith("%") and token[:-1].isdigit():
            return int(token[:-1])
    return 0


def get_mute() -> bool:
    out = _run(["pactl", "get-sink-mute", "@DEFAULT_SINK@"])
    return "yes" in out


class VolumeListener(threading.Thread):
    def __init__(self, backend: "Backend"):
        super().__init__(daemon=True)
        self._backend = backend
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        try:
            proc = subprocess.Popen(
                ["pactl", "subscribe"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except Exception:
            return

        if proc.stdout is None:
            return

        for line in proc.stdout:
            if self._stop.is_set():
                break
            if "sink" in line or "server" in line:
                self._backend.requestPoll.emit()

        try:
            proc.terminate()
        except Exception:
            pass


class MediaListener(threading.Thread):
    def __init__(self, backend: "Backend"):
        super().__init__(daemon=True)
        self._backend = backend
        self._stop = threading.Event()

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        if not _run(["which", "playerctl"]).strip():
            return
        try:
            proc = subprocess.Popen(
                [
                    "playerctl",
                    "-F",
                    "metadata",
                    "--format",
                    "{{status}}|{{xesam:title}}|{{xesam:artist}}|{{mpris:artUrl}}|{{playerName}}",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except Exception:
            return

        if proc.stdout is None:
            return

        for _line in proc.stdout:
            if self._stop.is_set():
                break
            # On any metadata change, show OSD with fresh data
            self._backend.requestShow.emit()

        try:
            proc.terminate()
        except Exception:
            pass


class Backend(QObject):
    volumeChanged = Signal()
    mutedChanged = Signal()
    trackChanged = Signal()
    uiChanged = Signal()
    showRequested = Signal()
    hideRequested = Signal()
    requestShow = Signal()
    requestPoll = Signal()

    def __init__(self, config: Dict[str, Any], app: QGuiApplication):
        super().__init__()
        self._config = config
        self._app = app
        self._window = None
        self._volume = 0
        self._muted = False
        self._track_title = ""
        self._track_artist = ""
        self._art_url = ""
        self._player_name = ""
        self._playing = False
        self._device_label = "Default Output"
        self._mpris_service = ""
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide)
        self._listener: Optional[VolumeListener] = None
        self._media_listener: Optional[MediaListener] = None
        self.requestShow.connect(self.show_current_volume, Qt.QueuedConnection)
        self.requestPoll.connect(self.debounce_poll, Qt.QueuedConnection)
        self._last_volume = None
        self._last_mute = None
        self._hovering = False
        self._poll_timer = QTimer()
        self._poll_timer.setSingleShot(True)
        self._poll_timer.timeout.connect(self.poll_volume_change)
        self._mpris_timer = QTimer()
        self._mpris_timer.setInterval(2000)
        self._mpris_timer.timeout.connect(self._update_mpris)
        self._pos_x = 0
        self._pos_y = 0

    # Volume
    @Property(int, notify=volumeChanged)
    def volume(self) -> int:
        return self._volume

    @Property(bool, notify=mutedChanged)
    def muted(self) -> bool:
        return self._muted

    # Media
    @Property(str, notify=trackChanged)
    def trackTitle(self) -> str:
        return self._track_title

    @Property(str, notify=trackChanged)
    def trackArtist(self) -> str:
        return self._track_artist

    @Property(str, notify=trackChanged)
    def artUrl(self) -> str:
        return self._art_url

    @Property(str, notify=trackChanged)
    def playerName(self) -> str:
        return self._player_name

    @Property(bool, notify=trackChanged)
    def playing(self) -> bool:
        return self._playing

    # UI config
    @Property(int, notify=uiChanged)
    def width(self) -> int:
        return int(self._config["width"])

    @Property(int, notify=uiChanged)
    def height(self) -> int:
        return int(self._config["height"])

    @Property(str, notify=uiChanged)
    def backgroundColor(self) -> str:
        return str(self._config["background_color"])

    @Property(str, notify=uiChanged)
    def accentColor(self) -> str:
        return str(self._config["accent_color"])

    @Property(str, notify=uiChanged)
    def textColor(self) -> str:
        return str(self._config["text_color"])

    @Property(str, notify=uiChanged)
    def fontFamily(self) -> str:
        return str(self._config["font_family"])

    @Property(bool, notify=uiChanged)
    def showPlayer(self) -> bool:
        return bool(self._config.get("show_player", True))

    @Property(str, notify=uiChanged)
    def deviceLabel(self) -> str:
        return self._device_label

    @Property(int, notify=uiChanged)
    def posX(self) -> int:
        return self._pos_x

    @Property(int, notify=uiChanged)
    def posY(self) -> int:
        return self._pos_y

    def set_window(self, window) -> None:
        self._window = window
        self._apply_position()

    def start_listening(self) -> None:
        if self._config.get("listen_pactl", True) and self._listener is None:
            self._listener = VolumeListener(self)
            self._listener.start()
        if self._config.get("listen_media", True) and self._media_listener is None:
            self._media_listener = MediaListener(self)
            self._media_listener.start()

    def _apply_position(self) -> None:
        if self._window is None:
            return
        screen = self._app.primaryScreen()
        if screen is None:
            return
        geo = screen.availableGeometry()
        width = self.width
        height = self.height
        margin_x = int(self._config.get("margin_x", 24))
        margin_y = int(self._config.get("margin_y", 48))
        anchor = self._config.get("anchor", "bottom_right")

        if anchor == "bottom_left":
            x = geo.left() + margin_x
            y = geo.bottom() - height - margin_y
        elif anchor == "top_right":
            x = geo.right() - width - margin_x
            y = geo.top() + margin_y
        elif anchor == "top_left":
            x = geo.left() + margin_x
            y = geo.top() + margin_y
        else:
            x = geo.right() - width - margin_x
            y = geo.bottom() - height - margin_y

        self._pos_x = int(x)
        self._pos_y = int(y)
        self.uiChanged.emit()
        try:
            self._window.setPosition(x, y)
        except Exception:
            self._window.setX(x)
            self._window.setY(y)

    def _hide(self) -> None:
        self.hideRequested.emit()
        if self._hovering:
            return
        if self._mpris_timer.isActive():
            self._mpris_timer.stop()
        if self._window is not None:
            QMetaObject.invokeMethod(self._window, "animateHide", Qt.QueuedConnection)
            QTimer.singleShot(180, self._window.hide)

    def _show(self) -> None:
        if self._window is None:
            return
        self._apply_position()
        self._update_mpris()
        self._window.show()
        self._window.raise_()
        # Do not steal focus (important for games)
        QMetaObject.invokeMethod(self._window, "animateShow", Qt.QueuedConnection)
        self.showRequested.emit()
        timeout = int(self._config.get("timeout_ms", 1800))
        if not self._hovering:
            self._hide_timer.start(timeout)
        if not self._mpris_timer.isActive() and self._config.get("show_player", True):
            self._mpris_timer.start()

    def _update_mpris(self) -> None:
        info = get_mpris_info()
        if info is None:
            self._track_title = ""
            self._track_artist = ""
            self._art_url = ""
            self._player_name = ""
            self._playing = False
            self._mpris_service = ""
        else:
            self._track_title = info.get("title", "")
            self._track_artist = info.get("artist", "")
            self._art_url = info.get("art_url", "")
            self._player_name = info.get("player", "")
            self._playing = info.get("playing", False)
            self._mpris_service = info.get("service", "")
        self.trackChanged.emit()

    @Slot(int, bool)
    def ShowVolume(self, volume: int, muted: bool) -> None:
        max_vol = int(self._config.get("max_volume", 150))
        self._volume = max(0, min(max_vol, int(volume)))
        self._muted = bool(muted)
        self.volumeChanged.emit()
        self.mutedChanged.emit()
        self._update_mpris()
        self._show()

    def show_current_volume(self) -> None:
        vol = get_volume()
        muted = get_mute()
        self.ShowVolume(vol, muted)

    def poll_volume_change(self) -> None:
        vol = get_volume()
        muted = get_mute()
        if self._last_volume is None or self._last_mute is None:
            self._last_volume = vol
            self._last_mute = muted
            return
        if vol != self._last_volume or muted != self._last_mute:
            self._last_volume = vol
            self._last_mute = muted
            self.ShowVolume(vol, muted)

    @Slot()
    def debounce_poll(self) -> None:
        self._poll_timer.start(80)

    @Slot(bool)
    def HoverChanged(self, hovering: bool) -> None:
        self._hovering = bool(hovering)
        if self._hovering:
            if self._hide_timer.isActive():
                self._hide_timer.stop()
        else:
            timeout = int(self._config.get("timeout_ms", 1800))
            self._hide_timer.start(timeout)

    @Slot()
    def PlayPause(self) -> None:
        if not self._mpris_service:
            return
        call_mpris(self._mpris_service, "PlayPause")

    @Slot()
    def Next(self) -> None:
        if not self._mpris_service:
            return
        call_mpris(self._mpris_service, "Next")

    @Slot()
    def Previous(self) -> None:
        if not self._mpris_service:
            return
        call_mpris(self._mpris_service, "Previous")


class DBusAdapter(QObject):
    def __init__(self, backend: Backend):
        super().__init__()
        self._backend = backend

    @Slot(int, bool)
    def ShowVolume(self, volume: int, muted: bool) -> None:
        self._backend.ShowVolume(volume, muted)


def get_mpris_info() -> Optional[Dict[str, Any]]:
    info = get_mpris_info_playerctl()
    if info is not None:
        return info

    bus = QDBusConnection.sessionBus()
    if not bus.isConnected():
        return None

    dbus_iface = QDBusInterface(
        "org.freedesktop.DBus",
        "/org/freedesktop/DBus",
        "org.freedesktop.DBus",
        bus,
    )
    reply = QDBusReply(dbus_iface.call("ListNames"))
    if not reply.isValid():
        return None

    names = reply.value()
    mpris_names = [n for n in names if n.startswith("org.mpris.MediaPlayer2.")]
    if not mpris_names:
        return None

    # Pick a playing player first, else first available
    selected = None
    selected_playing = False
    for name in mpris_names:
        status = get_mpris_property(name, "org.mpris.MediaPlayer2.Player", "PlaybackStatus")
        playing = isinstance(status, str) and status.lower() == "playing"
        if playing:
            selected = name
            selected_playing = True
            break
        if selected is None:
            selected = name

    if selected is None:
        return None

    metadata = get_mpris_property(selected, "org.mpris.MediaPlayer2.Player", "Metadata")
    identity = get_mpris_property(selected, "org.mpris.MediaPlayer2", "Identity")
    status = get_mpris_property(selected, "org.mpris.MediaPlayer2.Player", "PlaybackStatus")
    playing = isinstance(status, str) and status.lower() == "playing"

    title = ""
    artist = ""
    art_url = ""
    if isinstance(metadata, dict):
        title = metadata.get("xesam:title", "") or ""
        artists = metadata.get("xesam:artist", [])
        if isinstance(artists, list) and artists:
            artist = artists[0]
        art_url = metadata.get("mpris:artUrl", "") or ""

    # Normalize types to string for QML
    try:
        title = str(title) if title is not None else ""
    except Exception:
        title = ""
    try:
        artist = str(artist) if artist is not None else ""
    except Exception:
        artist = ""
    try:
        art_url = str(art_url) if art_url is not None else ""
    except Exception:
        art_url = ""

    return {
        "title": title,
        "artist": artist,
        "art_url": art_url,
        "player": identity or selected.split("org.mpris.MediaPlayer2.", 1)[-1],
        "playing": playing or selected_playing,
        "service": selected,
    }


def get_mpris_info_playerctl() -> Optional[Dict[str, Any]]:
    if not _run(["which", "playerctl"]).strip():
        return None

    players_out = _run(["playerctl", "-l"])
    players = [p.strip() for p in players_out.splitlines() if p.strip()]
    if not players:
        return None

    selected = None
    selected_playing = False
    for p in players:
        status = _run(["playerctl", "-p", p, "status"]).strip().lower()
        if status == "playing":
            selected = p
            selected_playing = True
            break
        if selected is None:
            selected = p

    if selected is None:
        return None

    title = _run(["playerctl", "-p", selected, "metadata", "xesam:title"]).strip()
    artist = _run(["playerctl", "-p", selected, "metadata", "xesam:artist"]).strip()
    art_url = _run(["playerctl", "-p", selected, "metadata", "mpris:artUrl"]).strip()
    player_name = _run(["playerctl", "-p", selected, "metadata", "--format", "{{playerName}}"]).strip()
    status = _run(["playerctl", "-p", selected, "status"]).strip().lower()
    playing = status == "playing"

    return {
        "title": title,
        "artist": artist,
        "art_url": art_url,
        "player": player_name or selected,
        "playing": playing or selected_playing,
        "service": f"org.mpris.MediaPlayer2.{selected}",
    }


def get_mpris_property(service: str, iface: str, prop: str) -> Any:
    bus = QDBusConnection.sessionBus()
    props_iface = QDBusInterface(
        service,
        "/org/mpris/MediaPlayer2",
        "org.freedesktop.DBus.Properties",
        bus,
    )
    reply = QDBusReply(props_iface.call("Get", iface, prop))
    if not reply.isValid():
        return None
    return _unwrap_variant(reply.value())


def _unwrap_variant(value: Any) -> Any:
    # QDBusVariant / QVariant wrapper
    try:
        if hasattr(value, "variant"):
            value = value.variant()
    except Exception:
        pass

    # Recursively unwrap dict/list values
    if isinstance(value, dict):
        return {k: _unwrap_variant(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_unwrap_variant(v) for v in value]
    return value


def call_mpris(service: str, method: str) -> None:
    bus = QDBusConnection.sessionBus()
    iface = QDBusInterface(
        service,
        "/org/mpris/MediaPlayer2",
        "org.mpris.MediaPlayer2.Player",
        bus,
    )
    iface.call(method)


def main() -> int:
    parser = argparse.ArgumentParser(description="Win10-style audio OSD overlay")
    parser.add_argument("--daemon", action="store_true", help="Run as OSD daemon")
    parser.add_argument("--config", default=os.path.join(ROOT_DIR, "config", "config.json"))
    args = parser.parse_args()

    if os.geteuid() == 0:
        print("Do not run as root. Use your user session (DBus/Wayland) instead.", file=sys.stderr)
        return 1

    config = load_config(args.config)

    app = QGuiApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    engine = QQmlApplicationEngine()
    backend = Backend(config, app)
    engine.rootContext().setContextProperty("backend", backend)

    qml_path = os.path.join(ROOT_DIR, "qml", "OSD.qml")
    engine.load(qml_path)

    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    backend.set_window(window)

    bus = QDBusConnection.sessionBus()
    if not bus.registerService(SERVICE_NAME):
        # Another instance already running
        return 0
    adapter = DBusAdapter(backend)
    bus.registerObject(OBJECT_PATH, adapter, QDBusConnection.ExportAllSlots)

    if args.daemon:
        backend.start_listening()
        return app.exec()

    backend.show_current_volume()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
