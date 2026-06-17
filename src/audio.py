from __future__ import annotations

from pathlib import Path

import pygame

from src.settings import MUSIC_DIR


class AudioManager:
    def __init__(
        self,
        filenames: tuple[str, ...] = (
            "gameplay_retro_platformer.ogg",
            "gameplay_retro_platformer.mp3",
            "gameplay_retro_platformer.wav",
            "ttg_chiptune_loop.wav",
        ),
        volume: float = 0.32,
    ) -> None:
        MUSIC_DIR.mkdir(parents=True, exist_ok=True)
        self.candidates = tuple(MUSIC_DIR / filename for filename in filenames)
        self.path: Path | None = None
        self.volume = volume
        self.loaded = False
        self.playing = False
        self.paused = False
        self.warned = False

    def play_gameplay(self) -> None:
        if not self._ensure_loaded():
            return
        try:
            if self.playing and self.paused:
                pygame.mixer.music.unpause()
            elif not self.playing:
                pygame.mixer.music.play(-1)
            self.playing = True
            self.paused = False
        except Exception as exc:
            self._warn(f"music playback failed: {exc}")

    def pause(self) -> None:
        if not self.playing or self.paused or not self._mixer_ready():
            return
        try:
            pygame.mixer.music.pause()
            self.paused = True
        except Exception as exc:
            self._warn(f"music pause failed: {exc}")

    def unpause(self) -> None:
        if self.paused:
            self.play_gameplay()

    def stop(self) -> None:
        if not self.playing or not self._mixer_ready():
            return
        try:
            pygame.mixer.music.stop()
        except Exception as exc:
            self._warn(f"music stop failed: {exc}")
        self.playing = False
        self.paused = False

    def _ensure_loaded(self) -> bool:
        if self.loaded:
            return True
        if not self._mixer_ready():
            self._warn("pygame mixer is unavailable; background music disabled")
            return False
        self.path = next((path for path in self.candidates if path.exists()), None)
        if self.path is None:
            names = ", ".join(path.name for path in self.candidates)
            self._warn(f"no music file found; tried {names}")
            return False
        try:
            pygame.mixer.music.load(self.path)
            pygame.mixer.music.set_volume(self.volume)
            self.loaded = True
            return True
        except Exception as exc:
            self._warn(f"music load failed: {exc}")
            return False

    def _mixer_ready(self) -> bool:
        try:
            return pygame.mixer.get_init() is not None
        except Exception:
            return False

    def _warn(self, message: str) -> None:
        if not self.warned:
            print(f"Audio warning: {message}")
            self.warned = True
