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

기존 실행 파일 이름을 쓰고 싶다면 아래 명령도 가능합니다.

```bash
python game.py
```

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
