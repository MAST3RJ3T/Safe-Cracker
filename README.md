# Safe Cracker

## Rotary-Encoder Safe Cracking Game (DE1-SoC / Nios V)

A bare-metal C game for the Intel DE1-SoC that turns the board into a physical safe. A real
rotary encoder — mounted in a custom 3D-printed enclosure and wired into the FPGA's JP1
expansion header — drives a live safe dial rendered on a 320x240 VGA display. The player
spins the dial to find a randomly generated combination, listening for audio cues and
alternating rotation direction like a real lock, all before a countdown timer runs out.

Everything runs on a Nios V soft processor with no operating system: interrupt-driven I/O,
a hand-written double-buffered graphics pipeline, fixed-point trigonometry, and a
FIFO-managed audio engine.

By: **Tej Patel** & **Leo Zou**
ECE243 — Computer Organization, University of Toronto

---

## Demo

**Demo video:** [Watch on Google Drive](https://drive.google.com/file/d/1jstQclyEpFpwkT6OPigZCI7hnV77oXO9/view?usp=drive_link)

**Project pictures (hardware, enclosure, board setup):** [Google Drive folder](https://drive.google.com/drive/folders/1qsyP7JgdmJ4kz1QdTN5XOlyEALHF50tc?usp=drive_link)

| Start screen | Help screen |
| --- | --- |
| ![Start screen](image-assets/start_screen.png) | ![Help screen](image-assets/help_screen.png) |

| Safe (gameplay) | Safe (unlocked) | Safe (failed) |
| --- | --- | --- |
| ![Safe](image-assets/safe_v1.png) | ![Safe unlocked](image-assets/safe_pass.png) | ![Safe failed](image-assets/safe_fail.png) |

---

## Repository Structure

* `docs/` — final report, project plan, block diagram, JP1 pinout, and the Tinkercad
  enclosure model (`243 SafeCracker.3mf`).
* `image-assets/` — source `.png` art, the exported RGB565 `.c` arrays, and the image
  conversion script.
* `audio-assets/` — source `.mp3` sound effects that were converted into PCM sample arrays.

> **Academic Integrity & Licensing**
> To comply with the University of Toronto's academic integrity policy, the C source code
> for this course project is **not** published in this repository. This README documents the
> design; the assets, documentation, and hardware work are included.

---

## Hardware

| Component | Detail |
| --- | --- |
| Board | Intel DE1-SoC (Cyclone V) |
| Processor | Nios V soft RISC-V core, bare-metal C |
| Input | Rotary encoder on JP1 (GPIO 0), KEY0–3, SW0–9 |
| Output | VGA 320x240 @ 16-bit RGB565, audio codec, HEX0–5, LEDR0–9 |
| Enclosure | Custom rotary-encoder and wiring housing, modelled in Tinkercad and 3D printed |
| Debounce | 10 µF ceramic capacitors on the encoder's CLK and DT lines |

### Rotary encoder wiring

The encoder's two quadrature phases are wired into the JP1 expansion header (D0 and D1)
alongside 3.3 V and ground. D0 is configured as an edge-triggered interrupt source; D1 is
sampled inside the ISR to recover direction.

![JP1 pinout](docs/JP1_pins.png)

### Enclosure

The bare encoder module is far too small to spin like a safe dial, and its jumper wires pull
loose under repeated rotation. A housing was modelled in Tinkercad and 3D printed to hold
the encoder body rigid, route and strain-relieve the wires out the back, and give the whole
assembly a stable base to sit on while being turned. The printable model is included at
[`docs/243 SafeCracker.3mf`](docs/243%20SafeCracker.3mf).

---

## Gameplay

The safe hides a randomly generated combination of numbers, each in the range 0–39. To open
it, the player must enter every number in order — and, like a real combination lock, must
**alternate rotation direction on every stage**: clockwise, counterclockwise, clockwise, and
so on. Landing on the right number while turning the wrong way still fails.

Two cues help. A distinct "correct" click plays the instant the dial lands on the right
number for the current stage, and the HEX displays and LEDs track progress live. The player
gets **3 wrong guesses** and a configurable countdown. Running out of either drops the game
into a fail state with a blaring alarm; entering the full sequence opens the safe.

### Controls

**Setup (intro / help screens)**

| Input | Action |
| --- | --- |
| `SW0–9` | Number of stages in the combination — 1 minimum, 10 maximum, each switch adds one |
| `KEY3` / `KEY2` | Decrease / increase the time limit in 10 s steps (7 s to 670 s) |
| `KEY1` | Toggle the help screen |
| `KEY0` | Confirm settings and start |
| `HEX0–1` | Selected number of stages |

**Gameplay**

| Input / Output | Action |
| --- | --- |
| Rotary encoder | Spin the dial — two full physical revolutions cover the on-screen 0–39 |
| `KEY0` | Confirm the current guess; also exits the pass and fail screens |
| `HEX0–1` | Current dial position (0–39) |
| `HEX2–3` | Current stage |
| `HEX4–5` | Guesses remaining |
| `LEDR0–9` | Stage progress |
| VGA | Live dial, safe art, and a 3-digit countdown |

---

## System Architecture

![Block diagram](docs/SafeCracker_Block-Diagram.png)

The program is a single `main()` render-and-audio loop fed by three independent interrupt
sources. Nothing polls for input: the main loop only draws frames, pushes audio samples, and
mirrors state onto the HEX displays and LEDs, while every state change happens inside an ISR.

### 1. Interrupt layer

A single RISC-V trap handler reads `mcause` and dispatches on the IRQ line. `mstatus`,
`mtvec`, and `mie` are configured directly with inline assembly (`csrw` / `csrs` / `csrc`).

| IRQ | Source | Responsibility |
| --- | --- | --- |
| 27 | JP1 parallel port | Rotary encoder edges — debounce, decode direction, update dial position |
| 18 | KEY0–3 | Screen transitions, guess confirmation, time-limit adjustment |
| 16 | FPGA interval timer | 1 Hz countdown tick; triggers the fail state at zero |

The interval timer is loaded with the full 100 MHz clock rate and configured with
`START | CONT | ITO` so it fires exactly once per second.

### 2. Rotary encoder decoding

Mechanical encoders are noisy, and a naive edge count produced dozens of phantom steps per
detent. The fix is layered:

* **Hardware.** 10 µF ceramic capacitors on the CLK and DT lines form an RC low-pass with
  the encoder's pull-up resistors, absorbing the worst of the contact chatter before it ever
  reaches the FPGA.
* **Software debounce.** Each accepted edge timestamps the RISC-V machine timer (`mtime`).
  Any edge arriving within 180,000 ticks of the last accepted one is discarded outright.
* **Edge division.** The encoder emits two clean transitions per physical detent, so the ISR
  counts edges and only advances the dial on every second one.

Direction comes from comparing the two phase levels at the moment of the interrupt: if CLK
and DT differ, the encoder is turning clockwise; if they match, counterclockwise. The dial
position wraps within 0–39, and the direction is latched so the game logic can check it
against the alternating-rotation rule when the player confirms a guess.

### 3. Game logic

Game state lives in a small set of `volatile` globals shared between the ISRs and the main
loop — dial position, combination array, current stage, latched spin direction, wrong-guess
count, and the active screen. The combination is regenerated on every game start with
`rand()`, seeded from the machine timer so each run differs.

On `KEY0` the game compares both the number **and** the direction against the expected
values for the current stage (`stage % 2` selects clockwise or counterclockwise). A correct
guess advances a stage or, on the last stage, unlocks the safe. A wrong guess resets stage
progress to zero, burns one of the three lives, and sends the player back to the first
number — the combination itself is not regenerated, so a careful player can still recover.

Screen state is a five-way enum (`INTRO`, `HELP`, `GAME`, `PASS`, `FAIL`) that both the
render path and the input handlers switch on, keeping drawing and logic decoupled.

### 4. Visual system

The graphics stack is written from scratch on top of a single `plot_pixel()` primitive.

* **Double buffering.** Two `240 x 512` 16-bit buffers are allocated statically. Each frame
  is drawn entirely into the back buffer and swapped on vertical sync, so the dial animation
  never tears. The 512-pixel stride lets pixel addressing collapse into shifts:
  `base + (y << 10) + (x << 1)`.
* **Rasterization.** Lines use Bresenham's algorithm with the steep-slope swap; circle
  outlines use the midpoint circle algorithm, drawing one 45° arc and mirroring it eight
  ways. Filled circles use a bounding-box scan with a squared-distance test — no square
  roots anywhere.
* **Fixed-point trigonometry.** With no FPU available, sine and cosine are 40-entry integer
  lookup tables scaled by 1024. Angles are tracked in tenths of a degree (0–3599), so each
  of the 40 dial positions sits exactly 90 units apart and every trig result is recovered
  with one integer divide.
* **The live dial.** All 40 tick marks are recomputed every frame against the current dial
  angle: long marks with engraved numbers every 5 positions, short marks in between, plus
  the outer face, the center knob, and a fixed red pointer drawn last.
* **Custom bitmap font.** Digits are stored as a 3x5 grid packed into nibbles (`0x7` renders
  as `[X][X][X]`) and scaled at draw time. The same routine renders the 1-digit dial labels
  at scale 1 and the 3-digit countdown at scale 5.
* **Overdraw avoidance.** The gameplay screen skips the usual clear-to-black entirely,
  because the full-screen brick wall image already covers every pixel — one fewer full-frame
  pass per frame.
* **Chroma keying.** The pass and fail emotes are stored on a magenta background (`0xF81F`),
  which the plot routine skips per pixel to composite them transparently over the wall.

### 5. Audio

Six sound effects are held in memory as PCM sample arrays and pushed into the audio codec's
output FIFO. Two playback modes coexist:

* **Non-blocking** (`audioService`) — called every iteration of the main loop, it tops up
  the FIFO only while there is space, so dial clicks play without ever stalling rendering.
* **Blocking** (`audioPlayback`) — used for the pass, fail, and wrong-guess cues where the
  clip must play to completion. It busy-waits on FIFO space, and the buffer state is
  explicitly reset afterwards so the non-blocking path resumes cleanly.

The FIFOs are cleared through the control register (`0x8` then `0x0`) before every new clip,
which is what makes rapid-fire ratchet clicks feel responsive instead of queued.

| Sound | Samples | Trigger |
| --- | --- | --- |
| `ratchet` | 160 | Every encoder detent |
| `correctRatchet` | 1,200 | Dial lands on the correct number for the current stage |
| `correctGuess` | 5,120 | Confirmed correct stage |
| `wrongGuess` | 8,880 | Confirmed wrong stage |
| `safeOpen` | 21,120 | Full combination entered |
| `alarm` | 39,282 | Fail state, looped until reset |

### 6. Asset pipeline

There is no filesystem on the board, so every image and sound is compiled directly into the
binary as a C array.

* **Images** — [`image-assets/convert_img.py`](image-assets/convert_img.py) loads a PNG with
  OpenCV, resizes it with nearest-neighbour interpolation, packs each pixel into RGB565
  (`R >> 3 << 11 | G >> 2 << 5 | B >> 3`), and emits both the `short unsigned int` array and
  matching `plot_image_*` / `erase_image_*` functions.
* **Screens** — the start and help screens are generated programmatically with a Pillow
  script that renders text, drop shadows, and layout at 3x resolution before downsampling to
  320x240, so the 240p output stays crisp. The help text is externalized to a plain text
  file, making a copy change a one-line edit rather than a re-render by hand.
* **Audio** — the source MP3s in `audio-assets/` were decoded to mono PCM and exported as
  32-bit signed sample arrays.

Together the compiled-in assets come to roughly **1.4 MB** of static data: about 674 KB of
images, 296 KB of audio, and 480 KB of frame buffers.

---

## Attribution

| Member | Contributions |
| --- | --- |
| **Tej Patel** | Rotary encoder (JP1 wiring, interrupt decoding, hardware and software debounce, direction tracking), 3D-printed enclosure design, KEY interrupt handling, HEX display and LED output, SW-based stage selection, the full audio subsystem (MP3 to C array conversion, blocking and non-blocking FIFO playback), core game logic (random code generation, stage tracking, guess validation), and integration of the game logic with the VGA system |
| **Leo Zou** | VGA graphics system (pixel plotting, double buffering, vsync, line and circle rasterization), live safe dial rendering (rotating numbered face, tick marks, pointer, knob), interval-timer countdown logic and time-limit controls, the digit rendering and 3-digit timer display, and the design and integration of the intro, help, gameplay, pass, fail, and wall background screens |

Full details are in the [final report](docs/SafeCracker_Final-Report.pdf) and the original
[project plan](docs/SafeCracker_Project-Plan.pdf).
