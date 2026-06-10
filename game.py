import pygame
import copy
import time
pygame.init()

SIZE = 600
ROWS = 6
CELL = SIZE // ROWS

screen = pygame.display.set_mode((SIZE, SIZE))
pygame.display.set_caption("Tic-Tac-Go Clone")

FONT = pygame.font.SysFont(None, 60)
BIG = pygame.font.SysFont(None, 100)

START_BOARD = [
[".",".","X",".",".","."],
[".","O",".",".",".","X"],
["X",".",".","X","X","."],
[".","X",".",".","X","O"],
[".",".","X","X",".","."],
["P",".","X",".",".","."]
]

board = copy.deepcopy(START_BOARD)
history = []

BEIGE = (232,188,104)
BROWN = (139,69,19)
WHITE = (255,255,255)
BLACK = (0,0,0)

def reset():
    global board, history
    board = copy.deepcopy(START_BOARD)
    history = []

def find_player():
    for y in range(ROWS):
        for x in range(ROWS):
            if board[y][x] == "P":
                return x,y

def push_move(dx,dy):
    global board

    px,py = find_player()

    nx = px + dx
    ny = py + dy

    if not (0 <= nx < ROWS and 0 <= ny < ROWS):
        return

    history.append(copy.deepcopy(board))

    target = board[ny][nx]

    if target == ".":
        board[py][px] = "."
        board[ny][nx] = "P"

    elif target in ["O","X"]:

        bx = nx + dx
        by = ny + dy

        if 0 <= bx < ROWS and 0 <= by < ROWS:
            if board[by][bx] == ".":

                board[by][bx] = target
                board[ny][nx] = "P"
                board[py][px] = "."
            else:
                history.pop()
        else:
            history.pop()
    else:
        history.pop()

def check_three(symbol):

    for y in range(ROWS):
        for x in range(ROWS-2):
            if all(board[y][x+i] == symbol for i in range(3)):
                return True

    for x in range(ROWS):
        for y in range(ROWS-2):
            if all(board[y+i][x] == symbol for i in range(3)):
                return True

    return False

def draw():

    screen.fill((170,100,40))

    for y in range(ROWS):
        for x in range(ROWS):

            rect = pygame.Rect(
                x*CELL+5,
                y*CELL+5,
                CELL-10,
                CELL-10
            )

            pygame.draw.rect(screen, BEIGE, rect, border_radius=8)

            cx = x*CELL + CELL//2
            cy = y*CELL + CELL//2

            value = board[y][x]

            if value == "O":
                pygame.draw.circle(
                    screen,
                    WHITE,
                    (cx,cy),
                    CELL//4,
                    6
                )

            elif value == "X":

                pygame.draw.line(
                    screen,
                    BROWN,
                    (cx-25,cy-25),
                    (cx+25,cy+25),
                    8
                )

                pygame.draw.line(
                    screen,
                    BROWN,
                    (cx+25,cy-25),
                    (cx-25,cy+25),
                    8
                )

            elif value == "P":

                pygame.draw.circle(
                    screen,
                    WHITE,
                    (cx,cy),
                    CELL//4
                )

                pygame.draw.circle(
                    screen,
                    BLACK,
                    (cx-10,cy-5),
                    4
                )

                pygame.draw.circle(
                    screen,
                    BLACK,
                    (cx+10,cy-5),
                    4
                )

    if check_three("O"):
        txt = BIG.render("WIN", True, WHITE)
        screen.blit(txt,(200,250))

    elif check_three("X"):
        # txt = BIG.render("LOSE", True, WHITE)
        # screen.blit(txt,(180,250))
        # time.sleep(300)
        pygame.exit() # x가 세개가 되면 게임을 종료함


running = True

while running:

    for event in pygame.event.get():

        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.KEYDOWN:

            if event.key == pygame.K_LEFT:
                push_move(-1,0)

            elif event.key == pygame.K_RIGHT:
                push_move(1,0)

            elif event.key == pygame.K_UP:
                push_move(0,-1)

            elif event.key == pygame.K_DOWN:
                push_move(0,1)

            elif event.key == pygame.K_r:
                reset()

            elif event.key == pygame.K_u:
                if history:
                    board = history.pop()

    draw()
    pygame.display.flip()

pygame.quit()