from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_import_path() -> None:
    project_root = Path(__file__).resolve().parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))


def main() -> int:
    configure_import_path()

    try:
        import pygame

        from src.game import Game
    except Exception as exc:  # pragma: no cover - startup diagnostics
        print("Failed to import the game modules.")
        print(f"{type(exc).__name__}: {exc}")
        return 1

    try:
        pygame.init()
        try:
            pygame.mixer.init()
        except pygame.error as exc:
            print(f"Audio disabled: {exc}")

        smoke_test = "--smoke-test" in sys.argv or os.environ.get("TTG_SMOKE_TEST") == "1"
        game = Game(smoke_test=smoke_test)
        return game.run()
    except Exception as exc:  # pragma: no cover - user-facing crash report
        print("Mario Pipe Rush crashed with an unexpected error.")
        print(f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        try:
            pygame.quit()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
