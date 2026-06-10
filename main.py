from __future__ import annotations

import copy
import random
import sys
from collections import deque
from dataclasses import dataclass
from pathlib import Path
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
DIRECTIONS = ((-1, 0), (1, 0), (0, -1), (0, 1))

ASSET_DIR = Path(__file__).with_name("assets")
ASSET_CANDIDATES = {
    "background": ("background.png", "background.jpg", "background.jpeg"),
    PLAYER: ("player.png", "player.jpg", "player.jpeg"),
    O: ("o.png", "o.jpg", "o.jpeg"),
    X: ("x.png", "x.jpg", "x.jpeg"),
    WALL: ("wall.png", "wall.jpg", "wall.jpeg"),
    ITEM: ("item.png", "item.jpg", "item.jpeg"),
}

DIFFICULTIES = {
    "쉬움": {
        "rows": 4,
        "cols": 5,
        "x_count": 2,
        "wall_count": 1,
        "item_count": 1,
        "move_limit": 16,
        "min_solution_moves": 3,
        "max_solution_moves": 12,
        "min_o_pushes": 1,
        "generation_attempts": 260,
        "solver_node_limit": 25_000,
    },
    "보통": {
        "rows": 5,
        "cols": 6,
        "x_count": 4,
        "wall_count": 2,
        "item_count": 1,
        "move_limit": 24,
        "min_solution_moves": 6,
        "max_solution_moves": 15,
        "min_o_pushes": 1,
        "generation_attempts": 340,
        "solver_node_limit": 60_000,
    },
    "어려움": {
        "rows": 6,
        "cols": 7,
        "x_count": 5,
        "wall_count": 3,
        "item_count": 1,
        "move_limit": 34,
        "min_solution_moves": 8,
        "max_solution_moves": 18,
        "min_o_pushes": 2,
        "generation_attempts": 450,
        "solver_node_limit": 140_000,
    },
    "매우 어려움": {
        "rows": 7,
        "cols": 8,
        "x_count": 6,
        "wall_count": 4,
        "item_count": 2,
        "move_limit": 44,
        "min_solution_moves": 10,
        "max_solution_moves": 22,
        "min_o_pushes": 2,
        "generation_attempts": 560,
        "solver_node_limit": 220_000,
    },
}

FONT_CANDIDATES = ("malgungothic", "nanumgothic", "applesdgothicneo", "arial")

COLOR_BG = (235, 237, 231)
COLOR_SURFACE = (253, 252, 246)
COLOR_SURFACE_DARK = (37, 43, 47)
COLOR_TEXT = (29, 34, 39)
COLOR_MUTED = (92, 103, 108)
COLOR_BOARD = (204, 211, 203)
COLOR_CELL = (250, 249, 242)
COLOR_CELL_ALT = (242, 244, 237)
COLOR_CELL_EDGE = (172, 181, 174)
COLOR_WALL = (47, 54, 59)
COLOR_X = (202, 60, 78)
COLOR_O = (38, 92, 174)
COLOR_PLAYER = (18, 126, 91)
COLOR_ITEM = (226, 171, 42)
COLOR_BUTTON = (43, 51, 57)
COLOR_BUTTON_HOVER = (28, 112, 85)
COLOR_BUTTON_DISABLED = (145, 153, 153)
COLOR_BUTTON_TEXT = (255, 255, 255)
COLOR_PANEL = (252, 250, 243)
COLOR_DANGER = (176, 43, 60)
COLOR_SUCCESS = (20, 125, 78)


@dataclass
class GameSnapshot:
    board: list[list[str]]
    player_pos: tuple[int, int]
    moves_left: int
    game_status: str
    lose_reason: str
    last_message: str
    message_until: int


@dataclass(frozen=True)
class SolutionStats:
    moves: int
    o_pushes: int
    total_pushes: int


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

        shadow = self.rect.move(0, 3)
        pygame.draw.rect(surface, (194, 199, 192), shadow, border_radius=7)
        pygame.draw.rect(surface, color, self.rect, border_radius=7)
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
        self.assets: dict[str, pygame.Surface] = {}
        self.scaled_assets: dict[tuple[str, int], pygame.Surface] = {}

        self.game_status = START
        self.current_difficulty = "쉬움"
        self.difficulty_display = "쉬움"
        self.current_config = copy.deepcopy(DIFFICULTIES["쉬움"])
        self.board: list[list[str]] = []
        self.rows = 0
        self.cols = 0
        self.player_pos = (0, 0)
        self.moves_left = 0
        self.solution_moves: int | None = None
        self.solution_o_pushes: int | None = None
        self.history_stack: list[GameSnapshot] = []
        self.initial_snapshot: GameSnapshot | None = None
        self.lose_reason = ""
        self.last_message = ""
        self.message_until = 0
        self.running = True
        self.load_assets()

    def load_assets(self) -> None:
        self.assets = {}
        self.scaled_assets = {}
        if not ASSET_DIR.exists():
            return

        for key, filenames in ASSET_CANDIDATES.items():
            for filename in filenames:
                path = ASSET_DIR / filename
                if not path.exists():
                    continue
                try:
                    image = pygame.image.load(str(path))
                    self.assets[key] = image.convert() if key == "background" else image.convert_alpha()
                except pygame.error:
                    pass
                break

        if PLAYER not in self.assets and O in self.assets:
            self.assets[PLAYER] = self.assets[O]

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
        self.solution_moves = None
        self.solution_o_pushes = None
        self.history_stack = []
        self.lose_reason = ""
        self.last_message = ""
        self.message_until = 0
        board, player_pos, solution_stats = self.generate_board(
            self.rows,
            self.cols,
            self.current_config["x_count"],
            self.current_config["wall_count"],
            self.current_config["item_count"],
            self.current_config["min_solution_moves"],
            self.current_config["max_solution_moves"],
            self.current_config["min_o_pushes"],
            self.current_config["generation_attempts"],
            self.current_config["solver_node_limit"],
        )
        self.board = board
        self.player_pos = player_pos
        self.solution_moves = solution_stats.moves
        self.solution_o_pushes = solution_stats.o_pushes
        self.game_status = PLAYING
        self.initial_snapshot = self.make_snapshot()

    def make_config(self, difficulty_name: str) -> dict[str, int]:
        if difficulty_name != RANDOM_MODE:
            self.difficulty_display = difficulty_name
            return copy.deepcopy(DIFFICULTIES[difficulty_name])

        profile_name = random.choice(("보통", "어려움", "매우 어려움"))
        self.difficulty_display = f"랜덤/{profile_name}"
        config = copy.deepcopy(DIFFICULTIES[profile_name])
        config["x_count"] = max(2, config["x_count"] + random.choice((-1, 0, 1)))
        config["wall_count"] = max(0, config["wall_count"] + random.choice((-1, 0, 1)))
        config["move_limit"] = max(
            config["max_solution_moves"] + 3,
            config["move_limit"] + random.choice((-2, 0, 2)),
        )
        return config

    def generate_board(
        self,
        rows: int,
        cols: int,
        x_count: int,
        wall_count: int,
        item_count: int,
        min_solution_moves: int,
        max_solution_moves: int,
        min_o_pushes: int,
        generation_attempts: int,
        solver_node_limit: int,
    ) -> tuple[list[list[str]], tuple[int, int], SolutionStats]:
        best_candidate: tuple[list[list[str]], tuple[int, int], SolutionStats] | None = None
        total_needed = 1 + 2 + x_count + wall_count + item_count
        if total_needed > rows * cols:
            raise ValueError("Too many objects for this board size.")

        for _ in range(generation_attempts):
            candidate = self.make_candidate_board(
                rows,
                cols,
                x_count,
                wall_count,
                item_count,
                min_solution_moves,
                max_solution_moves,
                min_o_pushes,
            )
            if candidate is None:
                continue

            board, player_pos = candidate
            solution_stats = self.find_solution_stats(
                board,
                player_pos,
                max_solution_moves,
                solver_node_limit,
            )
            if solution_stats is None:
                continue

            if (
                solution_stats.moves >= min_solution_moves
                and solution_stats.o_pushes >= min_o_pushes
            ):
                return board, player_pos, solution_stats

            if (
                solution_stats.o_pushes >= min_o_pushes
                and (best_candidate is None or solution_stats.moves > best_candidate[2].moves)
            ):
                best_candidate = (board, player_pos, solution_stats)

        if best_candidate is not None:
            return best_candidate

        relaxed_candidate = self.make_candidate_board(
            rows,
            cols,
            max(1, x_count // 2),
            max(0, wall_count // 2),
            item_count,
            max(2, min_solution_moves - 2),
            max_solution_moves + 3,
            max(1, min_o_pushes),
        )
        if relaxed_candidate is not None:
            board, player_pos = relaxed_candidate
            solution_stats = self.find_solution_stats(
                board,
                player_pos,
                max_solution_moves + 3,
                solver_node_limit,
            )
            if solution_stats is not None and solution_stats.o_pushes >= max(1, min_o_pushes):
                return board, player_pos, solution_stats

        board, player_pos = self.make_fallback_board(rows, cols)
        solution_stats = self.find_solution_stats(
            board,
            player_pos,
            max(rows + cols, max_solution_moves + 4),
            solver_node_limit,
        )
        return board, player_pos, solution_stats or SolutionStats(max(1, min_solution_moves), 1, 1)

    def make_candidate_board(
        self,
        rows: int,
        cols: int,
        x_count: int,
        wall_count: int,
        item_count: int,
        min_solution_moves: int,
        max_solution_moves: int,
        min_o_pushes: int,
    ) -> tuple[list[list[str]], tuple[int, int]] | None:
        lines = self.get_goal_lines(rows, cols)
        random.shuffle(lines)

        for line in lines:
            line_cells = list(line)
            endpoint_indexes = [0, 2]
            random.shuffle(endpoint_indexes)
            for player_index in endpoint_indexes:
                board = [[EMPTY for _ in range(cols)] for _ in range(rows)]
                for index, (r, c) in enumerate(line_cells):
                    board[r][c] = PLAYER if index == player_index else O

                player_pos = line_cells[player_index]
                protected = set(line_cells)
                target_steps = random.randint(min_solution_moves, max_solution_moves)
                scrambled = self.reverse_scramble_board(
                    board,
                    player_pos,
                    rows,
                    cols,
                    target_steps,
                    min_o_pushes,
                    protected,
                )
                if scrambled is None:
                    continue

                board, player_pos, protected = scrambled
                if self.has_three_in_row(O, board):
                    continue
                if self.has_adjacent_o_pair(board):
                    continue
                if not self.place_objects(board, protected, x_count, wall_count, item_count):
                    continue
                if self.has_three_in_row(X, board):
                    continue
                if not self.get_valid_moves(board, player_pos):
                    continue
                return board, player_pos

        return None

    def make_fallback_board(self, rows: int, cols: int) -> tuple[list[list[str]], tuple[int, int]]:
        board = [[EMPTY for _ in range(cols)] for _ in range(rows)]
        row = rows // 2
        start_col = max(0, min(cols - 4, cols // 2 - 2))
        board[row][start_col + 1] = O
        board[row][start_col + 3] = O
        player_pos = (0, 0) if (row, start_col) != (0, 0) else (rows - 1, cols - 1)
        board[player_pos[0]][player_pos[1]] = PLAYER
        return board, player_pos

    def reverse_scramble_board(
        self,
        board: list[list[str]],
        player_pos: tuple[int, int],
        rows: int,
        cols: int,
        target_steps: int,
        min_o_pushes: int,
        protected: set[tuple[int, int]],
    ) -> tuple[list[list[str]], tuple[int, int], set[tuple[int, int]]] | None:
        current_board = copy.deepcopy(board)
        current_pos = player_pos
        touched = set(protected)
        reverse_o_pushes = 0

        for step in range(target_steps):
            options = self.get_reverse_options(current_board, current_pos, rows, cols)
            if reverse_o_pushes < min_o_pushes:
                options = [option for option in options if option[0] == "push_o"]
            elif step < target_steps - 1:
                push_options = [option for option in options if option[0] == "push_o"]
                walk_options = [option for option in options if option[0] == "walk"]
                if push_options and random.random() < 0.35:
                    options = push_options
                elif walk_options:
                    options = walk_options + push_options

            random.shuffle(options)
            moved = False
            for option in options:
                next_board, next_pos, used_cells, pushed_o = self.apply_reverse_option(
                    current_board,
                    current_pos,
                    option,
                )
                if self.has_three_in_row(O, next_board):
                    continue
                current_board = next_board
                current_pos = next_pos
                touched.update(used_cells)
                reverse_o_pushes += 1 if pushed_o else 0
                moved = True
                break

            if not moved:
                return None

        if reverse_o_pushes < min_o_pushes:
            return None
        return current_board, current_pos, touched

    def get_reverse_options(
        self,
        board: list[list[str]],
        player_pos: tuple[int, int],
        rows: int,
        cols: int,
    ) -> list[tuple[str, int, int]]:
        options: list[tuple[str, int, int]] = []
        pr, pc = player_pos
        for dr, dc in DIRECTIONS:
            nr, nc = pr + dr, pc + dc
            if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] == EMPTY:
                options.append(("walk", dr, dc))

            piece_r, piece_c = pr + dr, pc + dc
            back_r, back_c = pr - dr, pc - dc
            if not (0 <= piece_r < rows and 0 <= piece_c < cols):
                continue
            if not (0 <= back_r < rows and 0 <= back_c < cols):
                continue
            if board[piece_r][piece_c] == O and board[back_r][back_c] == EMPTY:
                options.append(("push_o", dr, dc))

        return options

    def apply_reverse_option(
        self,
        board: list[list[str]],
        player_pos: tuple[int, int],
        option: tuple[str, int, int],
    ) -> tuple[list[list[str]], tuple[int, int], set[tuple[int, int]], bool]:
        kind, dr, dc = option
        pr, pc = player_pos
        next_board = copy.deepcopy(board)

        if kind == "walk":
            nr, nc = pr + dr, pc + dc
            next_board[pr][pc] = EMPTY
            next_board[nr][nc] = PLAYER
            return next_board, (nr, nc), {(pr, pc), (nr, nc)}, False

        piece_r, piece_c = pr + dr, pc + dc
        back_r, back_c = pr - dr, pc - dc
        next_board[back_r][back_c] = PLAYER
        next_board[pr][pc] = O
        next_board[piece_r][piece_c] = EMPTY
        return next_board, (back_r, back_c), {
            (back_r, back_c),
            (pr, pc),
            (piece_r, piece_c),
        }, True

    def has_adjacent_o_pair(self, board: list[list[str]]) -> bool:
        o_cells = [
            (r, c)
            for r, row in enumerate(board)
            for c, cell in enumerate(row)
            if cell == O
        ]
        if len(o_cells) < 2:
            return False
        return self.manhattan_distance(o_cells[0], o_cells[1]) == 1

    def get_goal_lines(self, rows: int, cols: int) -> list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]]:
        lines: list[tuple[tuple[int, int], tuple[int, int], tuple[int, int]]] = []
        for r in range(rows):
            for c in range(cols - 2):
                lines.append(((r, c), (r, c + 1), (r, c + 2)))
        for c in range(cols):
            for r in range(rows - 2):
                lines.append(((r, c), (r + 1, c), (r + 2, c)))
        return lines

    def place_objects(
        self,
        board: list[list[str]],
        protected: set[tuple[int, int]],
        x_count: int,
        wall_count: int,
        item_count: int,
    ) -> bool:
        rows = len(board)
        cols = len(board[0]) if rows else 0
        available = [
            (r, c)
            for r in range(rows)
            for c in range(cols)
            if board[r][c] == EMPTY and (r, c) not in protected
        ]
        random.shuffle(available)

        for _ in range(x_count):
            placed = False
            random.shuffle(available)
            for cell in list(available):
                r, c = cell
                board[r][c] = X
                if not self.has_three_in_row(X, board):
                    available.remove(cell)
                    placed = True
                    break
                board[r][c] = EMPTY
            if not placed:
                return False

        if len(available) < wall_count + item_count:
            return False

        for _ in range(wall_count):
            r, c = available.pop()
            board[r][c] = WALL

        for _ in range(item_count):
            r, c = available.pop()
            board[r][c] = ITEM

        return True

    def make_manhattan_path(
        self,
        start: tuple[int, int],
        goal: tuple[int, int],
    ) -> list[tuple[int, int]]:
        row, col = start
        goal_row, goal_col = goal
        path = [(row, col)]
        while (row, col) != (goal_row, goal_col):
            choices: list[tuple[int, int]] = []
            if row < goal_row:
                choices.append((row + 1, col))
            elif row > goal_row:
                choices.append((row - 1, col))
            if col < goal_col:
                choices.append((row, col + 1))
            elif col > goal_col:
                choices.append((row, col - 1))
            row, col = random.choice(choices)
            path.append((row, col))
        return path

    def manhattan_distance(self, first: tuple[int, int], second: tuple[int, int]) -> int:
        return abs(first[0] - second[0]) + abs(first[1] - second[1])

    def find_solution_stats(
        self,
        board: list[list[str]],
        player_pos: tuple[int, int],
        max_depth: int,
        max_nodes: int,
    ) -> SolutionStats | None:
        rows = len(board)
        cols = len(board[0]) if rows else 0
        flat = tuple(
            EMPTY if cell == ITEM else cell
            for row in board
            for cell in row
        )

        if self.flat_has_three(flat, X, rows, cols):
            return None
        if self.flat_has_three(flat, O, rows, cols):
            return SolutionStats(0, 0, 0)

        queue: deque[tuple[tuple[str, ...], tuple[int, int], int, int, int]] = deque()
        queue.append((flat, player_pos, 0, 0, 0))
        seen = {flat}
        checked_nodes = 0

        while queue and checked_nodes < max_nodes:
            current_flat, current_pos, depth, o_pushes, total_pushes = queue.popleft()
            checked_nodes += 1
            if depth >= max_depth:
                continue

            for dr, dc in DIRECTIONS:
                moved = self.simulate_flat_move(current_flat, current_pos, dr, dc, rows, cols)
                if moved is None:
                    continue

                next_flat, next_pos, pushed_symbol = moved
                if next_flat in seen:
                    continue
                seen.add(next_flat)

                if self.flat_has_three(next_flat, X, rows, cols):
                    continue

                next_depth = depth + 1
                next_o_pushes = o_pushes + (1 if pushed_symbol == O else 0)
                next_total_pushes = total_pushes + (1 if pushed_symbol in (O, X) else 0)
                if self.flat_has_three(next_flat, O, rows, cols):
                    return SolutionStats(next_depth, next_o_pushes, next_total_pushes)

                queue.append((next_flat, next_pos, next_depth, next_o_pushes, next_total_pushes))

        return None

    def find_solution_length(
        self,
        board: list[list[str]],
        player_pos: tuple[int, int],
        max_depth: int,
        max_nodes: int,
    ) -> int | None:
        solution_stats = self.find_solution_stats(board, player_pos, max_depth, max_nodes)
        return None if solution_stats is None else solution_stats.moves

    def simulate_flat_move(
        self,
        flat: tuple[str, ...],
        player_pos: tuple[int, int],
        dr: int,
        dc: int,
        rows: int,
        cols: int,
    ) -> tuple[tuple[str, ...], tuple[int, int], str | None] | None:
        pr, pc = player_pos
        nr, nc = pr + dr, pc + dc
        if not (0 <= nr < rows and 0 <= nc < cols):
            return None

        player_index = pr * cols + pc
        target_index = nr * cols + nc
        target = flat[target_index]

        if target == EMPTY:
            next_flat = list(flat)
            next_flat[player_index] = EMPTY
            next_flat[target_index] = PLAYER
            return tuple(next_flat), (nr, nc), None

        if target not in (O, X):
            return None

        br, bc = nr + dr, nc + dc
        if not (0 <= br < rows and 0 <= bc < cols):
            return None

        behind_index = br * cols + bc
        if flat[behind_index] != EMPTY:
            return None

        next_flat = list(flat)
        next_flat[behind_index] = target
        next_flat[target_index] = PLAYER
        next_flat[player_index] = EMPTY
        return tuple(next_flat), (nr, nc), target

    def flat_has_three(
        self,
        flat: tuple[str, ...],
        target: str,
        rows: int,
        cols: int,
    ) -> bool:
        for r in range(rows):
            for c in range(cols - 2):
                indexes = [r * cols + c + offset for offset in range(3)]
                if self.flat_cells_match([flat[index] for index in indexes], target):
                    return True

        for c in range(cols):
            for r in range(rows - 2):
                indexes = [(r + offset) * cols + c for offset in range(3)]
                if self.flat_cells_match([flat[index] for index in indexes], target):
                    return True

        return False

    def flat_cells_match(self, cells: list[str], target: str) -> bool:
        if target == O:
            return all(cell in (PLAYER, O) for cell in cells)
        return all(cell == target for cell in cells)

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

    def draw_background(self) -> None:
        background = self.assets.get("background")
        if background is None:
            self.screen.fill(COLOR_BG)
            pygame.draw.rect(self.screen, (221, 225, 216), pygame.Rect(0, 0, WINDOW_WIDTH, 150))
            pygame.draw.rect(self.screen, (226, 229, 222), pygame.Rect(0, WINDOW_HEIGHT - 118, WINDOW_WIDTH, 118))
            return

        source_width, source_height = background.get_size()
        scale = max(WINDOW_WIDTH / source_width, WINDOW_HEIGHT / source_height)
        scaled_size = (round(source_width * scale), round(source_height * scale))
        scaled = pygame.transform.smoothscale(background, scaled_size)
        x = (WINDOW_WIDTH - scaled_size[0]) // 2
        y = (WINDOW_HEIGHT - scaled_size[1]) // 2
        self.screen.blit(scaled, (x, y))
        tint = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        tint.fill((239, 240, 233, 210))
        self.screen.blit(tint, (0, 0))

    def draw_panel(
        self,
        rect: pygame.Rect,
        fill: tuple[int, int, int] = COLOR_PANEL,
        border: tuple[int, int, int] = COLOR_CELL_EDGE,
    ) -> None:
        shadow = rect.move(0, 5)
        pygame.draw.rect(self.screen, (202, 207, 199), shadow, border_radius=8)
        pygame.draw.rect(self.screen, fill, rect, border_radius=8)
        pygame.draw.rect(self.screen, border, rect, width=1, border_radius=8)

    def draw_chip(self, rect: pygame.Rect, text: str, font: pygame.font.Font) -> None:
        pygame.draw.rect(self.screen, (237, 241, 236), rect, border_radius=7)
        label = font.render(text, True, COLOR_TEXT)
        label_rect = label.get_rect(center=rect.center)
        self.screen.blit(label, label_rect)

    def draw_asset(self, key: str, rect: pygame.Rect) -> bool:
        image = self.assets.get(key)
        if image is None:
            return False

        width, height = image.get_size()
        if width <= 0 or height <= 0:
            return False

        max_width = max(1, rect.width)
        max_height = max(1, rect.height)
        scale = min(max_width / width, max_height / height)
        scaled_size = (max(1, round(width * scale)), max(1, round(height * scale)))
        cache_key = (key, scaled_size[0] * 10_000 + scaled_size[1])
        scaled = self.scaled_assets.get(cache_key)
        if scaled is None:
            scaled = pygame.transform.smoothscale(image, scaled_size)
            self.scaled_assets[cache_key] = scaled

        image_rect = scaled.get_rect(center=rect.center)
        self.screen.blit(scaled, image_rect)
        return True

    def draw_start_screen(self) -> None:
        self.draw_background()
        title_font = self.get_font(52, bold=True)
        body_font = self.get_font(20)
        small_font = self.get_font(17)
        button_font = self.get_font(21, bold=True)

        pygame.draw.rect(self.screen, COLOR_SURFACE_DARK, pygame.Rect(0, 0, WINDOW_WIDTH, 132))
        self.draw_centered_text("아이템 Tic-Tac-Go", title_font, COLOR_BUTTON_TEXT, 70)
        self.draw_centered_text(
            "검증된 랜덤 보드에서 O 3개를 한 줄로 연결하세요.",
            small_font,
            (215, 224, 220),
            116,
        )

        panel = pygame.Rect(130, 174, 640, 410)
        self.draw_panel(panel)

        description_lines = [
            "O 3개가 가로 또는 세로로 이어지면 승리",
            "X 3개가 이어지면 패배",
            "모든 새 보드는 자동 풀이 검사를 통과한 판만 사용",
        ]
        y = panel.y + 48
        for line in description_lines:
            self.draw_centered_text(line, body_font, COLOR_MUTED, y)
            y += 32

        button_data = [
            ("쉬움 4x5", "쉬움"),
            ("보통 5x6", "보통"),
            ("어려움 6x7", "어려움"),
            ("매우 어려움 7x8", "매우 어려움"),
            ("랜덤 시작", RANDOM_MODE),
        ]
        button_width = 250
        button_height = 52
        start_y = panel.y + 170
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

        self.draw_centered_text("숫자 1-5로도 시작할 수 있습니다.", small_font, COLOR_MUTED, 650)

    def draw_game_screen(self, show_controls: bool = True) -> None:
        self.draw_background()
        title_font = self.get_font(25, bold=True)
        small_font = self.get_font(18)
        button_font = self.get_font(18, bold=True)
        chip_font = self.get_font(16, bold=True)

        x_count = self.count_x()
        pygame.draw.rect(self.screen, COLOR_SURFACE_DARK, pygame.Rect(0, 0, WINDOW_WIDTH, 76))
        title = title_font.render("아이템 Tic-Tac-Go", True, COLOR_BUTTON_TEXT)
        self.screen.blit(title, (28, 23))

        chips = [
            f"이동 {self.moves_left}",
            f"보드 {self.rows}x{self.cols}",
            f"X {x_count}",
            self.difficulty_display,
        ]
        x = WINDOW_WIDTH - 28
        for text in reversed(chips):
            width = max(82, chip_font.size(text)[0] + 26)
            x -= width
            self.draw_chip(pygame.Rect(x, 22, width, 32), text, chip_font)
            x -= 10

        board_rect, cell_size = self.get_board_layout()
        frame = board_rect.inflate(24, 24)
        self.draw_panel(frame, fill=COLOR_BOARD, border=COLOR_CELL_EDGE)
        self.draw_board(board_rect, cell_size)

        if self.last_message and pygame.time.get_ticks() <= self.message_until:
            message_surface = small_font.render(self.last_message, True, COLOR_PLAYER)
            message_rect = message_surface.get_rect(center=(WINDOW_WIDTH // 2, board_rect.bottom + 30))
            bubble = message_rect.inflate(28, 12)
            pygame.draw.rect(self.screen, COLOR_PANEL, bubble, border_radius=7)
            pygame.draw.rect(self.screen, COLOR_CELL_EDGE, bubble, width=1, border_radius=7)
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

                fill = COLOR_CELL if (r + c) % 2 == 0 else COLOR_CELL_ALT
                if cell == WALL and WALL not in self.assets:
                    fill = COLOR_WALL
                pygame.draw.rect(self.screen, fill, rect, border_radius=8)
                pygame.draw.rect(self.screen, COLOR_CELL_EDGE, rect, width=1, border_radius=8)

                center = rect.center
                if cell == X:
                    if not self.draw_asset(X, rect.inflate(-6, -6)):
                        self.draw_x(center, cell_size)
                elif cell == O:
                    if not self.draw_asset(O, rect.inflate(-6, -6)):
                        self.draw_o(center, cell_size, COLOR_O, 7)
                elif cell == PLAYER:
                    if self.draw_asset(PLAYER, rect.inflate(-6, -6)):
                        self.draw_player_marker(rect, cell_size)
                    else:
                        self.draw_o(center, cell_size, COLOR_PLAYER, 9)
                        pygame.draw.circle(self.screen, COLOR_BUTTON_TEXT, center, max(5, cell_size // 13))
                elif cell == ITEM:
                    if not self.draw_asset(ITEM, rect.inflate(-6, -6)):
                        self.draw_item(center, cell_size)
                elif cell == WALL:
                    self.draw_asset(WALL, rect.inflate(-4, -4)) or self.draw_wall(rect)

    def draw_x(self, center: tuple[int, int], cell_size: int) -> None:
        radius = max(15, cell_size // 3)
        half = cell_size // 5
        width = max(5, cell_size // 13)
        x, y = center
        pygame.draw.circle(self.screen, COLOR_X, center, radius)
        pygame.draw.circle(self.screen, (132, 41, 54), center, radius, 2)
        pygame.draw.line(self.screen, COLOR_BUTTON_TEXT, (x - half, y - half), (x + half, y + half), width)
        pygame.draw.line(self.screen, COLOR_BUTTON_TEXT, (x + half, y - half), (x - half, y + half), width)

    def draw_o(self, center: tuple[int, int], cell_size: int, color: tuple[int, int, int], width: int) -> None:
        radius = max(15, cell_size // 3)
        pygame.draw.circle(self.screen, color, center, radius)
        pygame.draw.circle(self.screen, COLOR_BUTTON_TEXT, center, max(7, radius - width), width)

    def draw_item(self, center: tuple[int, int], cell_size: int) -> None:
        radius = max(14, cell_size // 3)
        x, y = center
        points = [(x, y - radius), (x + radius, y), (x, y + radius), (x - radius, y)]
        pygame.draw.polygon(self.screen, COLOR_ITEM, points)
        pygame.draw.polygon(self.screen, (151, 111, 25), points, width=2)
        font = self.get_font(max(24, cell_size // 2), bold=True)
        label = font.render("?", True, COLOR_TEXT)
        label_rect = label.get_rect(center=(center[0], center[1] - 1))
        self.screen.blit(label, label_rect)

    def draw_player_marker(self, rect: pygame.Rect, cell_size: int) -> None:
        width = max(4, cell_size // 16)
        pygame.draw.rect(self.screen, COLOR_PLAYER, rect.inflate(-3, -3), width=width, border_radius=8)
        dot_radius = max(5, cell_size // 12)
        dot_center = (rect.right - dot_radius - 8, rect.top + dot_radius + 8)
        pygame.draw.circle(self.screen, COLOR_PLAYER, dot_center, dot_radius)
        pygame.draw.circle(self.screen, COLOR_BUTTON_TEXT, dot_center, max(2, dot_radius // 2))

    def draw_wall(self, rect: pygame.Rect) -> None:
        wall_surface = pygame.Surface(rect.size, pygame.SRCALPHA)
        local_rect = wall_surface.get_rect()
        pygame.draw.rect(wall_surface, COLOR_WALL, local_rect, border_radius=8)
        for offset in range(-rect.height, rect.width, 18):
            start = (offset, rect.height)
            end = (offset + rect.height, 0)
            pygame.draw.line(wall_surface, (73, 82, 88), start, end, 3)
        pygame.draw.rect(wall_surface, (22, 27, 30), local_rect, width=2, border_radius=8)
        self.screen.blit(wall_surface, rect.topleft)

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
