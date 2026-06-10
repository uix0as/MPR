from __future__ import annotations

import copy
import random
import sys
from dataclasses import dataclass
from typing import Callable

import pygame


WINDOW_WIDTH = 900
WINDOW_HEIGHT = 720
FPS = 60

EMPTY = "."
PLAYER = "P"
O = "O"
X = "X"
WALL = "#"
ITEM = "?"

START = "START"
PLAYING = "PLAYING"
WON = "WON"
LOST = "LOST"

RANDOM_MODE = "랜덤"

DIFFICULTIES = {
    "쉬움": {
        "rows": 4,
        "cols": 5,
        "x_count": 7,
        "wall_count": 2,
        "item_count": 1,
        "move_limit": 28,
    },
    "보통": {
        "rows": 5,
        "cols": 6,
        "x_count": 10,
        "wall_count": 3,
        "item_count": 1,
        "move_limit": 42,
    },
    "어려움": {
        "rows": 6,
        "cols": 7,
        "x_count": 15,
        "wall_count": 4,
        "item_count": 2,
        "move_limit": 58,
    },
    "매우 어려움": {
        "rows": 7,
        "cols": 8,
        "x_count": 20,
        "wall_count": 6,
        "item_count": 2,
        "move_limit": 77,
    },
}

RANDOM_SIZE_CANDIDATES = [(4, 5), (5, 6), (6, 7), (7, 8)]
FONT_CANDIDATES = ("malgungothic", "nanumgothic", "applesdgothicneo", "arial")

COLOR_BG = (244, 247, 244)
COLOR_TEXT = (35, 40, 48)
COLOR_MUTED = (98, 111, 122)
COLOR_BOARD = (211, 222, 218)
COLOR_CELL = (250, 252, 249)
COLOR_CELL_EDGE = (173, 188, 183)
COLOR_WALL = (54, 61, 67)
COLOR_X = (211, 65, 82)
COLOR_O = (47, 104, 210)
COLOR_PLAYER = (18, 137, 101)
COLOR_ITEM = (232, 181, 52)
COLOR_BUTTON = (42, 52, 62)
COLOR_BUTTON_HOVER = (24, 117, 91)
COLOR_BUTTON_DISABLED = (154, 164, 171)
COLOR_BUTTON_TEXT = (255, 255, 255)
COLOR_PANEL = (232, 238, 235)
COLOR_DANGER = (184, 45, 64)
COLOR_SUCCESS = (21, 137, 85)


@dataclass
class GameSnapshot:
    board: list[list[str]]
    player_pos: tuple[int, int]
    moves_left: int
    game_status: str
    lose_reason: str
    last_message: str
    message_until: int


class Button:
    def __init__(
        self,
        rect: pygame.Rect,
        text: str,
        action: Callable[[], None],
        enabled: bool = True,
    ) -> None:
        self.rect = rect
        self.text = text
        self.action = action
        self.enabled = enabled

    def draw(self, surface: pygame.Surface, font: pygame.font.Font) -> None:
        mouse_pos = pygame.mouse.get_pos()
        is_hover = self.enabled and self.rect.collidepoint(mouse_pos)
        color = COLOR_BUTTON_HOVER if is_hover else COLOR_BUTTON
        if not self.enabled:
            color = COLOR_BUTTON_DISABLED

        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        label = font.render(self.text, True, COLOR_BUTTON_TEXT)
        label_rect = label.get_rect(center=self.rect.center)
        surface.blit(label, label_rect)

    def handle_click(self, pos: tuple[int, int]) -> bool:
        if self.enabled and self.rect.collidepoint(pos):
            self.action()
            return True
        return False


class Game:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.font_cache: dict[tuple[int, bool], pygame.font.Font] = {}
        self.buttons: list[Button] = []

        self.game_status = START
        self.current_difficulty = "쉬움"
        self.current_config = copy.deepcopy(DIFFICULTIES["쉬움"])
        self.board: list[list[str]] = []
        self.rows = 0
        self.cols = 0
        self.player_pos = (0, 0)
        self.moves_left = 0
        self.history_stack: list[GameSnapshot] = []
        self.initial_snapshot: GameSnapshot | None = None
        self.lose_reason = ""
        self.last_message = ""
        self.message_until = 0
        self.running = True

    def get_font(self, size: int, bold: bool = False) -> pygame.font.Font:
        key = (size, bold)
        if key in self.font_cache:
            return self.font_cache[key]

        for name in FONT_CANDIDATES:
            path = pygame.font.match_font(name, bold=bold)
            if path:
                font = pygame.font.Font(path, size)
                self.font_cache[key] = font
                return font

        for name in FONT_CANDIDATES:
            try:
                font = pygame.font.SysFont(name, size, bold=bold)
                self.font_cache[key] = font
                return font
            except pygame.error:
                continue

        font = pygame.font.Font(None, size)
        self.font_cache[key] = font
        return font

    def start_game(self, difficulty_name: str) -> None:
        self.current_difficulty = difficulty_name
        self.current_config = self.make_config(difficulty_name)
        self.rows = self.current_config["rows"]
        self.cols = self.current_config["cols"]
        self.moves_left = self.current_config["move_limit"]
        self.history_stack = []
        self.lose_reason = ""
        self.last_message = ""
        self.message_until = 0
        self.board, self.player_pos = self.generate_board(
            self.rows,
            self.cols,
            self.current_config["x_count"],
            self.current_config["wall_count"],
            self.current_config["item_count"],
        )
        self.game_status = PLAYING
        self.initial_snapshot = self.make_snapshot()

    def make_config(self, difficulty_name: str) -> dict[str, int]:
        if difficulty_name != RANDOM_MODE:
            return copy.deepcopy(DIFFICULTIES[difficulty_name])

        rows, cols = random.choice(RANDOM_SIZE_CANDIDATES)
        cell_count = rows * cols
        x_count = round(cell_count * 0.35)
        if rows == 4 and cols == 5:
            x_count = 7

        return {
            "rows": rows,
            "cols": cols,
            "x_count": x_count,
            "wall_count": max(2, round(cell_count * 0.10)),
            "item_count": 1 if cell_count <= 30 else 2,
            "move_limit": int(cell_count * 1.2 + rows + cols - 5),
        }

    def generate_board(
        self,
        rows: int,
        cols: int,
        x_count: int,
        wall_count: int,
        item_count: int,
    ) -> tuple[list[list[str]], tuple[int, int]]:
        last_board: list[list[str]] | None = None
        last_player_pos = (0, 0)
        total_needed = 1 + 2 + x_count + wall_count + item_count
        if total_needed > rows * cols:
            raise ValueError("Too many objects for this board size.")

        for _ in range(500):
            board = [[EMPTY for _ in range(cols)] for _ in range(rows)]
            positions = [(r, c) for r in range(rows) for c in range(cols)]
            random.shuffle(positions)

            player_pos = positions.pop()
            board[player_pos[0]][player_pos[1]] = PLAYER

            for _ in range(2):
                r, c = positions.pop()
                board[r][c] = O

            for _ in range(x_count):
                r, c = positions.pop()
                board[r][c] = X

            for _ in range(wall_count):
                r, c = positions.pop()
                board[r][c] = WALL

            for _ in range(item_count):
                r, c = positions.pop()
                board[r][c] = ITEM

            last_board = board
            last_player_pos = player_pos

            if self.has_three_in_row(O, board):
                continue
            if self.has_three_in_row(X, board):
                continue
            if not self.get_valid_moves(board, player_pos):
                continue

            return board, player_pos

        if last_board is None:
            last_board = [[EMPTY for _ in range(cols)] for _ in range(rows)]
            last_board[0][0] = PLAYER
            last_player_pos = (0, 0)

        self.break_initial_lines(last_board)
        return last_board, last_player_pos

    def break_initial_lines(self, board: list[list[str]]) -> None:
        for symbol in (O, X):
            guard = 0
            while self.has_three_in_row(symbol, board) and guard < 100:
                guard += 1
                cells = [
                    (r, c)
                    for r, row in enumerate(board)
                    for c, cell in enumerate(row)
                    if (cell == O if symbol == O else cell == X)
                ]
                empties = [
                    (r, c)
                    for r, row in enumerate(board)
                    for c, cell in enumerate(row)
                    if cell == EMPTY
                ]
                if not cells or not empties:
                    return
                source = random.choice(cells)
                target = random.choice(empties)
                board[target[0]][target[1]] = board[source[0]][source[1]]
                board[source[0]][source[1]] = EMPTY

    def make_snapshot(self) -> GameSnapshot:
        return GameSnapshot(
            board=copy.deepcopy(self.board),
            player_pos=self.player_pos,
            moves_left=self.moves_left,
            game_status=self.game_status,
            lose_reason=self.lose_reason,
            last_message=self.last_message,
            message_until=self.message_until,
        )

    def restore_snapshot(self, snapshot: GameSnapshot) -> None:
        self.board = copy.deepcopy(snapshot.board)
        self.player_pos = snapshot.player_pos
        self.moves_left = snapshot.moves_left
        self.game_status = PLAYING if snapshot.game_status in (WON, LOST) else snapshot.game_status
        self.lose_reason = snapshot.lose_reason if self.game_status == LOST else ""
        self.last_message = snapshot.last_message
        self.message_until = snapshot.message_until

    def reset_level(self) -> None:
        if self.initial_snapshot is None:
            return
        self.restore_snapshot(self.initial_snapshot)
        self.game_status = PLAYING
        self.history_stack = []
        self.lose_reason = ""
        self.show_message("같은 판을 다시 시작합니다.", 1100)

    def new_board(self) -> None:
        self.start_game(self.current_difficulty)
        self.show_message("새 보드가 생성되었습니다.", 1100)

    def go_start(self) -> None:
        self.game_status = START
        self.buttons = []
        self.history_stack = []
        self.lose_reason = ""
        self.last_message = ""
        self.message_until = 0

    def undo(self) -> None:
        if not self.history_stack:
            self.show_message("되돌릴 이동이 없습니다.", 1000)
            return
        snapshot = self.history_stack.pop()
        self.restore_snapshot(snapshot)
        self.game_status = PLAYING
        self.lose_reason = ""
        self.show_message("실행취소", 800)

    def move_player(self, dr: int, dc: int) -> None:
        if self.game_status != PLAYING:
            return

        pr, pc = self.player_pos
        nr, nc = pr + dr, pc + dc
        if not self.in_bounds(nr, nc):
            self.show_message("보드 밖으로 이동할 수 없습니다.", 700)
            return

        target = self.board[nr][nc]
        if target in (EMPTY, ITEM):
            self.history_stack.append(self.make_snapshot())
            self.board[pr][pc] = EMPTY
            self.board[nr][nc] = PLAYER
            self.player_pos = (nr, nc)
            self.moves_left -= 1
            if target == ITEM:
                self.apply_item_effect()
            self.check_game_result()
            return

        if target in (O, X):
            br, bc = nr + dr, nc + dc
            if not self.in_bounds(br, bc) or self.board[br][bc] != EMPTY:
                self.show_message("블록 뒤가 비어 있어야 밀 수 있습니다.", 800)
                return

            self.history_stack.append(self.make_snapshot())
            self.board[br][bc] = target
            self.board[nr][nc] = PLAYER
            self.board[pr][pc] = EMPTY
            self.player_pos = (nr, nc)
            self.moves_left -= 1
            self.check_game_result()
            return

        if target == WALL:
            self.show_message("벽은 움직일 수 없습니다.", 700)

    def apply_item_effect(self) -> None:
        effect = random.choice(("delete_x", "add_moves"))
        x_cells = self.find_cells(X)
        if effect == "delete_x" and x_cells:
            r, c = random.choice(x_cells)
            self.board[r][c] = EMPTY
            self.show_message("X 하나 삭제!", 1000)
            return

        bonus = max(3, round((self.rows + self.cols) / 2))
        self.moves_left += bonus
        self.show_message(f"이동 횟수 +{bonus}", 1000)

    def check_game_result(self) -> None:
        if self.has_three_in_row(O, self.board):
            self.game_status = WON
            self.lose_reason = ""
            return

        if self.has_three_in_row(X, self.board):
            self.game_status = LOST
            self.lose_reason = "X 3개가 연결되었습니다."
            return

        if self.moves_left <= 0:
            self.moves_left = 0
            self.game_status = LOST
            self.lose_reason = "이동 횟수를 모두 사용했습니다."

    def has_three_in_row(self, target: str, board: list[list[str]] | None = None) -> bool:
        board_to_check = self.board if board is None else board
        if not board_to_check:
            return False

        rows = len(board_to_check)
        cols = len(board_to_check[0])

        for r in range(rows):
            for c in range(cols - 2):
                cells = [board_to_check[r][c + i] for i in range(3)]
                if self.cells_match(cells, target):
                    return True

        for c in range(cols):
            for r in range(rows - 2):
                cells = [board_to_check[r + i][c] for i in range(3)]
                if self.cells_match(cells, target):
                    return True

        return False

    def cells_match(self, cells: list[str], target: str) -> bool:
        if target == O:
            return all(self.is_o_cell(cell) for cell in cells)
        return all(cell == target for cell in cells)

    def get_valid_moves(
        self,
        board: list[list[str]] | None = None,
        player_pos: tuple[int, int] | None = None,
    ) -> list[tuple[int, int]]:
        board_to_check = self.board if board is None else board
        position = self.player_pos if player_pos is None else player_pos
        moves: list[tuple[int, int]] = []
        rows = len(board_to_check)
        cols = len(board_to_check[0]) if rows else 0

        for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nr, nc = position[0] + dr, position[1] + dc
            if not (0 <= nr < rows and 0 <= nc < cols):
                continue
            target = board_to_check[nr][nc]
            if target in (EMPTY, ITEM):
                moves.append((dr, dc))
            elif target in (O, X):
                br, bc = nr + dr, nc + dc
                if 0 <= br < rows and 0 <= bc < cols and board_to_check[br][bc] == EMPTY:
                    moves.append((dr, dc))

        return moves

    def find_cells(self, symbol: str) -> list[tuple[int, int]]:
        return [
            (r, c)
            for r, row in enumerate(self.board)
            for c, cell in enumerate(row)
            if cell == symbol
        ]

    def count_x(self) -> int:
        return len(self.find_cells(X))

    def in_bounds(self, row: int, col: int) -> bool:
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_o_cell(self, cell: str) -> bool:
        return cell in (PLAYER, O)

    def show_message(self, text: str, duration_ms: int) -> None:
        self.last_message = text
        self.message_until = pygame.time.get_ticks() + duration_ms

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.QUIT:
            self.running = False
            return

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for button in list(self.buttons):
                if button.handle_click(event.pos):
                    break
            return

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            self.running = False
            return

        if self.game_status == START:
            self.handle_start_key(event.key)
            return

        if event.key in (pygame.K_z,):
            self.undo()
            return
        if event.key == pygame.K_r:
            self.reset_level()
            return
        if event.key == pygame.K_n:
            self.new_board()
            return

        if self.game_status != PLAYING:
            return

        key_moves = {
            pygame.K_UP: (-1, 0),
            pygame.K_w: (-1, 0),
            pygame.K_DOWN: (1, 0),
            pygame.K_s: (1, 0),
            pygame.K_LEFT: (0, -1),
            pygame.K_a: (0, -1),
            pygame.K_RIGHT: (0, 1),
            pygame.K_d: (0, 1),
        }
        if event.key in key_moves:
            self.move_player(*key_moves[event.key])

    def handle_start_key(self, key: int) -> None:
        key_map = {
            pygame.K_1: "쉬움",
            pygame.K_2: "보통",
            pygame.K_3: "어려움",
            pygame.K_4: "매우 어려움",
            pygame.K_5: RANDOM_MODE,
        }
        if key in key_map:
            self.start_game(key_map[key])

    def draw(self) -> None:
        self.buttons = []
        if self.game_status == START:
            self.draw_start_screen()
        elif self.game_status == PLAYING:
            self.draw_game_screen()
        elif self.game_status == WON:
            self.draw_game_screen(show_controls=False)
            self.draw_end_overlay(True)
        elif self.game_status == LOST:
            self.draw_game_screen(show_controls=False)
            self.draw_end_overlay(False)

    def draw_start_screen(self) -> None:
        self.screen.fill(COLOR_BG)
        title_font = self.get_font(56, bold=True)
        body_font = self.get_font(22)
        button_font = self.get_font(22, bold=True)

        self.draw_centered_text("아이템 Tic-Tac-Go", title_font, COLOR_TEXT, 92)

        description_lines = [
            "O를 움직여 X와 O를 밀어보세요.",
            "O 3개를 가로/세로로 만들면 승리!",
            "X 3개가 가로/세로로 모이면 패배!",
            "? 아이템은 X 삭제 또는 이동 횟수 추가 효과를 줍니다.",
        ]
        y = 174
        for line in description_lines:
            self.draw_centered_text(line, body_font, COLOR_MUTED, y)
            y += 34

        button_data = [
            ("쉬움 4x5", "쉬움"),
            ("보통 5x6", "보통"),
            ("어려움 6x7", "어려움"),
            ("매우 어려움 7x8", "매우 어려움"),
            ("랜덤 시작", RANDOM_MODE),
        ]
        button_width = 245
        button_height = 54
        start_y = 356
        gap = 16

        for index, (label, difficulty) in enumerate(button_data):
            row = index // 2
            col = index % 2
            if index == len(button_data) - 1:
                x = (WINDOW_WIDTH - button_width) // 2
            else:
                total_width = button_width * 2 + gap
                x = (WINDOW_WIDTH - total_width) // 2 + col * (button_width + gap)
            rect = pygame.Rect(x, start_y + row * (button_height + gap), button_width, button_height)
            self.buttons.append(
                Button(rect, label, lambda name=difficulty: self.start_game(name))
            )

        for button in self.buttons:
            button.draw(self.screen, button_font)

        hint_font = self.get_font(18)
        self.draw_centered_text("숫자 1-5로도 시작할 수 있습니다.", hint_font, COLOR_MUTED, 660)

    def draw_game_screen(self, show_controls: bool = True) -> None:
        self.screen.fill(COLOR_BG)
        header_font = self.get_font(24, bold=True)
        small_font = self.get_font(18)
        button_font = self.get_font(18, bold=True)

        x_count = self.count_x()
        status_text = (
            f"남은 이동 {self.moves_left}    "
            f"보드 {self.rows}x{self.cols}    "
            f"X {x_count}개    "
            f"난이도 {self.current_difficulty}"
        )
        self.draw_centered_text(status_text, header_font, COLOR_TEXT, 35)

        board_rect, cell_size = self.get_board_layout()
        pygame.draw.rect(self.screen, COLOR_BOARD, board_rect.inflate(18, 18), border_radius=8)
        self.draw_board(board_rect, cell_size)

        if self.last_message and pygame.time.get_ticks() <= self.message_until:
            message_surface = small_font.render(self.last_message, True, COLOR_PLAYER)
            message_rect = message_surface.get_rect(center=(WINDOW_WIDTH // 2, board_rect.bottom + 28))
            self.screen.blit(message_surface, message_rect)

        guide = "방향키/WASD: 이동    Z: 실행취소    R: 재설정    N: 새 보드    ESC: 종료"
        self.draw_centered_text(guide, small_font, COLOR_MUTED, WINDOW_HEIGHT - 28)

        if show_controls:
            y = WINDOW_HEIGHT - 92
            labels = [
                ("실행취소", self.undo, bool(self.history_stack)),
                ("재설정", self.reset_level, self.initial_snapshot is not None),
                ("새 보드", self.new_board, True),
                ("시작 화면", self.go_start, True),
            ]
            button_width = 128
            button_height = 42
            gap = 12
            total_width = len(labels) * button_width + (len(labels) - 1) * gap
            start_x = (WINDOW_WIDTH - total_width) // 2
            for index, (label, action, enabled) in enumerate(labels):
                rect = pygame.Rect(
                    start_x + index * (button_width + gap),
                    y,
                    button_width,
                    button_height,
                )
                self.buttons.append(Button(rect, label, action, enabled))

            for button in self.buttons:
                button.draw(self.screen, button_font)

    def draw_board(self, board_rect: pygame.Rect, cell_size: int) -> None:
        for r in range(self.rows):
            for c in range(self.cols):
                x = board_rect.x + c * cell_size
                y = board_rect.y + r * cell_size
                rect = pygame.Rect(x + 4, y + 4, cell_size - 8, cell_size - 8)
                cell = self.board[r][c]

                fill = COLOR_CELL
                if cell == WALL:
                    fill = COLOR_WALL
                pygame.draw.rect(self.screen, fill, rect, border_radius=8)
                pygame.draw.rect(self.screen, COLOR_CELL_EDGE, rect, width=1, border_radius=8)

                center = rect.center
                if cell == X:
                    self.draw_x(center, cell_size)
                elif cell == O:
                    self.draw_o(center, cell_size, COLOR_O, 7)
                elif cell == PLAYER:
                    self.draw_o(center, cell_size, COLOR_PLAYER, 10)
                    pygame.draw.circle(self.screen, COLOR_PLAYER, center, max(4, cell_size // 12))
                elif cell == ITEM:
                    self.draw_item(center, cell_size)

    def draw_x(self, center: tuple[int, int], cell_size: int) -> None:
        half = cell_size // 4
        width = max(6, cell_size // 12)
        x, y = center
        pygame.draw.line(self.screen, COLOR_X, (x - half, y - half), (x + half, y + half), width)
        pygame.draw.line(self.screen, COLOR_X, (x + half, y - half), (x - half, y + half), width)

    def draw_o(self, center: tuple[int, int], cell_size: int, color: tuple[int, int, int], width: int) -> None:
        pygame.draw.circle(self.screen, color, center, max(12, cell_size // 3), width)

    def draw_item(self, center: tuple[int, int], cell_size: int) -> None:
        radius = max(14, cell_size // 3)
        pygame.draw.circle(self.screen, COLOR_ITEM, center, radius)
        font = self.get_font(max(24, cell_size // 2), bold=True)
        label = font.render("?", True, COLOR_TEXT)
        label_rect = label.get_rect(center=(center[0], center[1] - 1))
        self.screen.blit(label, label_rect)

    def draw_end_overlay(self, is_win: bool) -> None:
        overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 20, 26, 132))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(250, 190, 400, 340 if is_win else 390)
        pygame.draw.rect(self.screen, COLOR_PANEL, panel, border_radius=8)
        pygame.draw.rect(self.screen, COLOR_CELL_EDGE, panel, width=2, border_radius=8)

        title_font = self.get_font(44, bold=True)
        body_font = self.get_font(22)
        button_font = self.get_font(18, bold=True)
        title = "이겼습니다!" if is_win else "졌습니다!"
        color = COLOR_SUCCESS if is_win else COLOR_DANGER
        self.draw_centered_text(title, title_font, color, panel.y + 64)

        if is_win:
            self.draw_centered_text("O 3개를 연결했습니다.", body_font, COLOR_TEXT, panel.y + 113)
            button_specs = [
                ("같은 판 다시 시작", self.reset_level, True),
                ("새 보드", self.new_board, True),
                ("시작 화면으로", self.go_start, True),
            ]
        else:
            reason = self.lose_reason or "조건을 만족하지 못했습니다."
            self.draw_centered_text(reason, body_font, COLOR_TEXT, panel.y + 113)
            button_specs = [
                ("실행취소", self.undo, bool(self.history_stack)),
                ("재설정", self.reset_level, True),
                ("새 보드", self.new_board, True),
                ("시작 화면", self.go_start, True),
            ]

        button_width = 190
        button_height = 42
        gap = 12
        start_y = panel.y + 158
        for index, (label, action, enabled) in enumerate(button_specs):
            rect = pygame.Rect(
                panel.centerx - button_width // 2,
                start_y + index * (button_height + gap),
                button_width,
                button_height,
            )
            self.buttons.append(Button(rect, label, action, enabled))

        for button in self.buttons:
            button.draw(self.screen, button_font)

    def get_board_layout(self) -> tuple[pygame.Rect, int]:
        max_width = WINDOW_WIDTH - 130
        max_height = WINDOW_HEIGHT - 240
        cell_size = min(82, max_width // self.cols, max_height // self.rows)
        board_width = cell_size * self.cols
        board_height = cell_size * self.rows
        x = (WINDOW_WIDTH - board_width) // 2
        y = 96
        return pygame.Rect(x, y, board_width, board_height), cell_size

    def draw_centered_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: tuple[int, int, int],
        y: int,
    ) -> None:
        surface = font.render(text, True, color)
        rect = surface.get_rect(center=(WINDOW_WIDTH // 2, y))
        self.screen.blit(surface, rect)

    def run(self) -> None:
        while self.running:
            for event in pygame.event.get():
                self.handle_event(event)
            self.draw()
            pygame.display.flip()
            self.clock.tick(FPS)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("아이템 Tic-Tac-Go")
    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    game = Game(screen)
    game.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
