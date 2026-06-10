# 아이템 Tic-Tac-Go

Pygame으로 구현한 퍼즐 / 이동형 틱택고 게임입니다.

## 실행 방법

Python 3.10-3.12 사용을 권장합니다. VS Code에서는 이 폴더를 열고 아래 명령을 터미널에서 실행하면 됩니다.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

현재 프로젝트에는 Python 3.12 기반 `.venv`가 준비되어 있습니다. VS Code에서 실행할 때는 Run and Debug 패널의 `Run TTG (pygame)` 구성을 선택하면 이 가상환경으로 실행됩니다.

기존 실행 파일 이름을 쓰고 싶다면 아래 명령도 가능합니다.

```bash
python game.py
```

## 사진 바꾸기

사진은 `assets` 폴더에 넣으면 됩니다.

지원하는 파일 이름:

- `assets/background.png` 또는 `.jpg`: 전체 배경
- `assets/player.png` 또는 `.jpg`: 직접 움직이는 O
- `assets/o.png` 또는 `.jpg`: 일반 O
- `assets/x.png` 또는 `.jpg`: X
- `assets/wall.png` 또는 `.jpg`: 벽
- `assets/item.png` 또는 `.jpg`: 아이템

파일을 넣은 뒤 게임을 다시 실행하면 자동 적용됩니다. `player.png`가 없으면 `o.png`를 직접 움직이는 O에도 같이 쓰고, 초록색 표시를 덧그려 구분합니다. 파일이 없으면 기본 도형으로 표시됩니다.

## 조작

- 방향키 또는 WASD: 이동
- Z: 실행취소
- R: 현재 판 재설정
- N: 새 랜덤 보드
- ESC: 종료

## 규칙

- 주인공 O와 일반 O 2개를 포함해 O는 항상 총 3개입니다.
- O 3개가 가로 또는 세로로 연속되면 승리합니다.
- X 3개가 가로 또는 세로로 연속되면 패배합니다.
- 한 번에 X 또는 O 블록 하나만 밀 수 있습니다.
- 벽은 움직일 수 없고, 아이템은 플레이어가 직접 밟아야 먹을 수 있습니다.
- ? 아이템은 X 하나 삭제 또는 이동 횟수 추가 효과를 줍니다.
