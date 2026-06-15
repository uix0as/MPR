# Mario Pipe Rush: FIFO Delivery

A Python + Pygame 2D pixel platform puzzle action game. The player runs and jumps through a pipe kingdom, collects delivery items, and must satisfy orders using real Queue and Stack rules.

## Core Data Structure Idea

- `delivery_queue` is a `collections.deque`. Orders are processed FIFO, so `delivery_queue[0]` is always the current required delivery.
- `inventory_stack` is a Python `list`. Items are pushed with `append()` when collected and delivered only from `inventory_stack[-1]`.
- `spawn_queue` is a `collections.deque` of future item spawn events so the game can stay fair instead of relying only on randomness.

This means the player should read the queue and collect items in reverse order. If the queue is `[Mushroom, Coin, Flower]`, the useful collection order is `Flower -> Coin -> Mushroom`, so the stack top is Mushroom when delivery starts.

## Controls

- `A` / Left: move left
- `D` / Right: move right
- `Space`: jump
- `Shift`: run
- `E`: deliver the top bag item at the delivery pipe
- `Q`: return/discard the top bag item at the return pipe
- `P`: pause
- `R`: restart from the game-over screen
- `ESC`: quit

## Install and Run

```bash
pip install -r requirements.txt
python tools/download_assets.py
python main.py
```

If your system only exposes Python as `python3`, use `python3` for the same commands.

## Gameplay

You have 120 seconds to complete as many orders as possible. Correct deliveries increase score, combo, and time. Wrong deliveries keep the item in the bag, reset combo, reduce time, and shake the screen. The return pipe lets you recover from mistakes, but only by popping the stack top and paying a penalty.

Implemented item types:

- Mushroom: 100 points
- Coin: 80 points
- Fire Flower: 150 points
- Star: 250 points plus a short combo bonus
- Shell: 120 points

## Educational Design Note

This game turns a familiar platform-jump style into a delivery puzzle. The order list is a Queue, so older orders must be handled first. The player bag is a Stack, so the newest collected item must come out first. Queue FIFO and Stack LIFO are visible in the HUD and directly control scoring, success, failure, and recovery.

## Assets and Licensing

`tools/download_assets.py` optionally downloads CC0 Kenney Pixel Platformer sheets through raw GitHub URLs from [uheartbeast/Pixel-Platformer](https://github.com/uheartbeast/Pixel-Platformer). Kenney's official page lists Pixel Platformer as Creative Commons CC0: <https://kenney.nl/assets/pixel-platformer>.

No Nintendo sprites, logos, audio, ROM material, or other unlicensed IP are included. The Mario-like feeling is produced with original procedural placeholders: bright sky, green pipes, brick blocks, question blocks, coin particles, and a red-cap platformer character.

If downloads fail, the game still runs from generated placeholder PNGs and in-code fallback surfaces. See `assets/CREDITS.md` and `assets/manifest.json` for source, license, URL, and SHA256 details after running the downloader.
