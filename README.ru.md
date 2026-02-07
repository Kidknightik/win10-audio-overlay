# Win10 Audio OSD (KDE Plasma 6.5)

Пример (как выглядит):

![Пример внешнего вида](example.png)

Кастомный оверлей громкости в стиле Windows 10 для KDE Plasma. Показывает громкость и информацию о текущей музыке (MPRIS).

## Примечания

- Запускай демон от обычного пользователя (не `sudo`). Ему нужен твой пользовательский DBus/Wayland.
- Оверлей слушает `pactl subscribe` и появляется при изменении громкости.
- Информация о музыке работает для любых плееров с **MPRIS**. В приоритете используется `playerctl`.

## Установка

```
./scripts/install.sh
```

Если нужно пропустить установку зависимостей:

```
./scripts/install.sh --no-deps
```

Установщик поддерживает `pacman`, `apt-get`, `dnf`. Для других дистрибутивов ставь вручную:

- Python 3
- PySide6
- Qt6 Declarative (QML)
- `pactl` (pipewire-pulse или pulseaudio-utils)
- `playerctl`
- Опционально: `qdbus6` (qt6-tools). Иначе используется `busctl`.
- Опционально (веб-плееры): `plasma-browser-integration` и расширение браузера.

## Веб-плееры (YouTube, Spotify Web, SoundCloud, Яндекс Музыка Web)

Нужно установить:
- `plasma-browser-integration`
- расширение KDE Plasma Integration для браузера

Проверка MPRIS:

```
qdbus6 | rg mpris
```

Если видишь `org.mpris.MediaPlayer2.chromium` или `...firefox`, музыка из браузера должна отображаться.

## Запуск

Запуск демона (если не через systemd):

```
python3 ./src/win10_osd.py --daemon
```

Показать текущую громкость:

```
./scripts/win10-osd --show
```

Увеличить громкость на `step_percent`:

```
./scripts/win10-osd --up
```

## KDE

Установщик отключает штатный Plasma OSD и сохраняет стандартные кнопки громкости. Оверлей появляется при любом изменении громкости через `pactl subscribe`. Если нужны кастомные шорткаты, создавай их в System Settings -> Shortcuts.

## Конфиг

Файл `config/config.json`:

- `width`, `height`
- `timeout_ms`
- `anchor` (`bottom_right`, `bottom_left`, `top_right`, `top_left`)
- `margin_x`, `margin_y`
- `background_color`, `accent_color`, `text_color`
- `font_family`
- `show_player`
- `step_percent`
- `listen_pactl`
- `listen_media`
- `max_volume`

## Удаление

```
./scripts/uninstall.sh
```
