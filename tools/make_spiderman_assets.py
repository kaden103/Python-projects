"""Draw the extra enemy sprites and synthesize the sound effects and music for SpiderMannn.

The sprites are drawn as pixel grids in the same chunky, black-outlined style as the
Spider-Man and Green Goblin art. The sounds are simple chiptune-style synthesis.

Run from the repo root (needs pygame, numpy and ffmpeg):
    python tools/make_spiderman_assets.py
"""

import subprocess
import tempfile
import wave
from pathlib import Path

import numpy as np
import pygame


GAME_DIR = Path(__file__).resolve().parent.parent / "SpiderMannn"
PIXEL = 4  # Screen pixels per art pixel, matching the existing sprites
RATE = 22050

PALETTE = {
    "B": (58, 58, 70),  # beanie
    "G": (128, 132, 140),  # metal gray
    "g": (90, 94, 102),  # dark metal
    "S": (226, 170, 110),  # skin
    "s": (186, 128, 78),  # skin shade
    "E": (20, 20, 20),  # eyes, mouth
    "P": (112, 54, 150),  # hoodie
    "p": (78, 34, 108),  # hoodie shade
    "J": (54, 86, 160),  # jeans
    "j": (36, 58, 112),  # jeans shade
    "W": (236, 236, 236),  # sneakers, flame core
    "R": (210, 40, 30),  # red
    "O": (250, 140, 20),  # orange
    "Y": (255, 220, 60),  # yellow
    "N": (40, 120, 40),  # Goblin green
    "V": (120, 60, 150),  # Goblin purple
}

THUG_HEAD = [
    "......BBBBBB..........",
    ".....BBBBBBBB.........",
    "....BBBBBBBBBB........",
    "....GGGGGGGGGG........",
    "....SSSSSSEESS........",
    "....SSSSSSSESS........",
    "....SSSSSSSESS........",
    "....sSSSSSSSSSS.......",
    "....sSSSSSEEESS.......",
    ".....sSSSSSSSS........",
]
THUG_BODY = [
    ".....pPPPPPPPp........",
    "....pPPPPPPPPPp.......",
    "...pPPPPPPPPPPPp......",
    "...PPpPPPPPPPpPP......",
    "...PPpPPPPPPPpPP......",
    "...SSpPPPPPPPpSS......",
    "...SS.PPPPPPP.SS......",
    "......JJJJJJJ.........",
    "......JJJjJJJ.........",
]
THUG_PUNCH_BODY = [
    ".....pPPPPPPPp........",
    "....pPPPPPPPPPp.......",
    "...pPPPPPPPPPPPPPPPSS.",
    "...PPpPPPPPPPPPPPPPSSS",
    "...PPpPPPPPPPPpPPPPSS.",
    "...SSpPPPPPPPp........",
    "...SS.PPPPPPP.........",
    "......JJJJJJJ.........",
    "......JjJJJjJ.........",
]
THUG_LEGS_A = [
    ".....JJJ...JJJ........",
    ".....JJJ...JJJ........",
    ".....jJ.....Jj........",
    "....WWW.....WWW.......",
]
THUG_LEGS_B = [
    "......JJJ.JJJ.........",
    ".......JJJJJ..........",
    ".......jJ.Jj..........",
    "......WWW.WWW.........",
]
THUG_LEGS_PUNCH = [
    "....JJJ.....JJJ.......",
    "...JJJ.......JJJ......",
    "...jJ.........Jj......",
    "..WWW.........WWW.....",
]

DRONE_UP = [
    "...........GG...........",
    "..........GNNG..........",
    "G........GNOONG........G",
    "GG......GGNNNNGG......GG",
    "GVVV..GGgggggggGG..VVVGG",
    ".GVVVVVVVVgGGgVVVVVVVVG.",
    "..GVVVVVVVVVVVVVVVVVVG..",
    "...GG..VVVVVVVVVV..GG...",
    ".........GgRRgG.........",
    "..........G..G..........",
]
DRONE_DOWN = [
    "...........GG...........",
    "..........GNNG..........",
    ".........GNOONG.........",
    "........GGNNNNGG........",
    "..VV..GGgggggggGG..VV...",
    ".GVVVVVVVVgGGgVVVVVVVVG.",
    "GVVVVVVVVVVVVVVVVVVVVVVG",
    "GG.GG..VVVVVVVVVV..GG.GG",
    "G........GgRRgG........G",
    "..........G..G..........",
]

FIRE = [
    "....R.....",
    "...RR..R..",
    "...ROR.RR.",
    "..ROOR.RR.",
    ".ROOORROR.",
    ".ROYOOOOR.",
    "RROYYOYORR",
    "ROYYYYYYOR",
    "ROYYWWYYOR",
    ".ROYYYYOR.",
]


def grid_to_surface(rows):
    """Turn a pixel grid into a sprite with a one-pixel black outline, scaled up."""
    width = max(len(row) for row in rows) + 2
    height = len(rows) + 2
    padded = ["." * width] + ["." + row.ljust(width - 2, ".") + "." for row in rows] + ["." * width]
    small = pygame.Surface((width, height), pygame.SRCALPHA)
    for y, row in enumerate(padded):
        for x, key in enumerate(row):
            if key != ".":
                small.set_at((x, y), PALETTE[key])
                continue
            neighbors = [
                padded[ny][nx]
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                if 0 <= nx < width and 0 <= ny < height
            ]
            if any(cell != "." for cell in neighbors):
                small.set_at((x, y), (0, 0, 0))
    return pygame.transform.scale(small, (width * PIXEL, height * PIXEL))


def wrap_in_web(sprite):
    """Cover a sprite in web strands, for a defeated thug."""
    webbed = sprite.copy()
    width, height = webbed.get_size()
    strand = (245, 245, 245)
    for offset in range(-height, width, 22):
        pygame.draw.line(webbed, strand, (offset, 0), (offset + height, height), 3)
        pygame.draw.line(webbed, strand, (offset + height, 0), (offset, height), 3)
    for y in range(18, height, 26):
        pygame.draw.line(webbed, strand, (8, y), (width - 8, y + 6), 4)
    mask = pygame.mask.from_surface(sprite)
    webbed_mask = mask.to_surface(setcolor=(255, 255, 255, 255), unsetcolor=(0, 0, 0, 0))
    webbed.blit(webbed_mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
    return webbed


def make_sprites():
    walk_a = grid_to_surface(THUG_HEAD + THUG_BODY + THUG_LEGS_A)
    sprites = {
        "Thug_Walk_1.png": walk_a,
        "Thug_Walk_2.png": grid_to_surface(THUG_HEAD + THUG_BODY + THUG_LEGS_B),
        "Thug_Punch.png": grid_to_surface(THUG_HEAD + THUG_PUNCH_BODY + THUG_LEGS_PUNCH),
        "Thug_Webbed.png": wrap_in_web(walk_a),
        "Drone_1.png": grid_to_surface(DRONE_UP),
        "Drone_2.png": grid_to_surface(DRONE_DOWN),
        "Fire.png": grid_to_surface(FIRE),
    }
    for name, surface in sprites.items():
        pygame.image.save(surface, GAME_DIR / name)
        print("wrote", name, surface.get_size())


# --- Sound -------------------------------------------------------------------------

def seconds(duration):
    return np.arange(int(RATE * duration)) / RATE


def envelope(length, attack=0.005, release=0.05):
    count = length
    env = np.ones(count)
    attack_n = max(1, int(RATE * attack))
    release_n = max(1, int(RATE * release))
    env[:attack_n] = np.linspace(0, 1, attack_n)[: count]
    env[-release_n:] *= np.linspace(1, 0, min(release_n, count))
    return env


def square(frequency, t, duty=0.5):
    phase = np.cumsum(np.broadcast_to(frequency, t.shape) / RATE)
    return np.where((phase % 1.0) < duty, 1.0, -1.0)


def triangle(frequency, t):
    phase = np.cumsum(np.broadcast_to(frequency, t.shape) / RATE)
    return 4 * np.abs((phase % 1.0) - 0.5) - 1


def noise(t, seed=0):
    return np.random.default_rng(seed).uniform(-1, 1, t.shape)


def lowpass(signal, amount):
    """One-pole low-pass; amount 0..1 (or an array), smaller is darker."""
    out = np.empty_like(signal)
    amount = np.broadcast_to(amount, signal.shape)
    value = 0.0
    for index, sample in enumerate(signal):
        value += amount[index] * (sample - value)
        out[index] = value
    return out


def decay(t, rate):
    return np.exp(-t * rate)


def sfx_thwip():
    t = seconds(0.22)
    swept = lowpass(noise(t, 1), np.linspace(0.9, 0.05, t.size))
    tone = square(np.linspace(1800, 500, t.size), t, 0.25) * 0.25
    return (swept * 0.9 + tone) * decay(t, 14)


def sfx_web_hit():
    t = seconds(0.25)
    splat = lowpass(noise(t, 2), 0.35) * decay(t, 18)
    thump = np.sin(2 * np.pi * np.linspace(220, 70, t.size) * t) * decay(t, 20)
    return splat * 0.8 + thump


def sfx_hit():
    t = seconds(0.3)
    body = np.sin(2 * np.pi * np.cumsum(np.linspace(160, 45, t.size)) / RATE) * decay(t, 12)
    crack = noise(t, 3) * decay(t, 40)
    return body + crack * 0.6


def sfx_explosion():
    t = seconds(0.7)
    rumble = lowpass(noise(t, 4), np.linspace(0.5, 0.02, t.size)) * decay(t, 5)
    boom = np.sin(2 * np.pi * np.cumsum(np.linspace(90, 30, t.size)) / RATE) * decay(t, 7)
    return rumble * 1.6 + boom * 0.8


def sfx_hurt():
    t = seconds(0.35)
    return square(np.linspace(520, 120, t.size), t, 0.5) * decay(t, 6) * 0.6


def sfx_jump():
    t = seconds(0.15)
    return square(np.linspace(300, 750, t.size), t, 0.25) * decay(t, 10) * 0.45


def sfx_swing():
    t = seconds(0.3)
    whoosh = lowpass(noise(t, 5), 0.15 + 0.25 * np.sin(np.pi * t / t[-1]))
    return whoosh * np.sin(np.pi * t / t[-1]) * 1.5


def sfx_stomp():
    t = seconds(0.18)
    return (square(np.linspace(180, 60, t.size), t, 0.5) * 0.5 + noise(t, 6) * 0.3) * decay(t, 18)


def sfx_defeat():
    notes = [523, 659, 784, 1047]
    parts = []
    for note in notes:
        t = seconds(0.06)
        parts.append(square(note, t, 0.25) * 0.4)
    return np.concatenate(parts) * envelope(len(parts) * int(RATE * 0.06), release=0.05)


def sfx_combo():
    t = seconds(0.09)
    return square(np.linspace(900, 1400, t.size), t, 0.125) * decay(t, 20) * 0.35


def sfx_heal():
    parts = [square(note, seconds(0.08), 0.5) * 0.3 for note in (660, 880, 1320)]
    return np.concatenate(parts)


def sfx_warning():
    parts = []
    for _ in range(3):
        t = seconds(0.09)
        parts.append(square(880, t, 0.5) * 0.35)
        parts.append(np.zeros(int(RATE * 0.04)))
    return np.concatenate(parts)


def sfx_laugh():
    """A cackle: wobbling, falling 'ha' syllables made from a buzzy square wave."""
    parts = []
    for index, pitch in enumerate((420, 400, 370, 340, 300)):
        t = seconds(0.11)
        wobble = pitch * (1 + 0.06 * np.sin(2 * np.pi * 28 * t))
        voice = lowpass(square(wobble, t, 0.3), 0.3) * np.sin(np.pi * t / t[-1])
        parts.append(voice * 0.9)
        parts.append(np.zeros(int(RATE * 0.04)))
    return np.concatenate(parts)


def sfx_fire():
    t = seconds(0.5)
    crackle = noise(t, 7) * (noise(t, 8) > 0.85)
    return (lowpass(noise(t, 9), 0.1) * 1.5 + crackle * 0.6) * decay(t, 5)


def jingle(notes, step, duty=0.5):
    parts = []
    for note, length in notes:
        t = seconds(step * length)
        if note:
            tone = square(note, t, duty) * 0.3 + triangle(note / 2, t) * 0.25
            parts.append(tone * envelope(t.size, release=0.03))
        else:
            parts.append(np.zeros(t.size))
    return np.concatenate(parts)


def sfx_win():
    return jingle([(523, 1), (659, 1), (784, 1), (1047, 2), (784, 1), (1047, 4)], 0.11)


def sfx_lose():
    return jingle([(392, 2), (370, 2), (349, 2), (330, 6)], 0.13, duty=0.25)


def sfx_phase():
    return jingle([(220, 1), (0, 1), (220, 1), (0, 1), (233, 1), (0, 1), (262, 3)], 0.09, duty=0.25)


def note_frequency(name):
    names = {"C": -9, "C#": -8, "D": -7, "D#": -6, "E": -5, "F": -4, "F#": -3, "G": -2, "G#": -1, "A": 0, "A#": 1, "B": 2}
    pitch, octave = name[:-1], int(name[-1])
    return 440.0 * 2 ** ((names[pitch] + (octave - 4) * 12) / 12)


def music():
    """A looping minor-key chase theme: bass, lead, arpeggio and drums."""
    bpm = 150
    eighth = 60 / bpm / 2
    chords = ["A", "A", "F", "G", "A", "A", "F", "E"] * 2
    roots = {"A": "A2", "F": "F2", "G": "G2", "E": "E2"}
    arps = {
        "A": ["A4", "C5", "E5", "C5"],
        "F": ["F4", "A4", "C5", "A4"],
        "G": ["G4", "B4", "D5", "B4"],
        "E": ["E4", "G#4", "B4", "G#4"],
    }
    # One note per eighth across 8 bars, repeated for the second half with a variation.
    melody_a = (
        "E5 . E5 D5 C5 . A4 . | C5 . D5 . E5 . . . | F5 . E5 . D5 . C5 . | D5 . . . B4 . G4 . |"
        " E5 . E5 D5 C5 . A4 . | C5 . E5 . A5 . . . | A5 . G5 . F5 . E5 . | E5 . . . G#4 . B4 . |"
    )
    melody_b = (
        "A5 . . . G5 . E5 . | C5 . E5 . A5 . G5 . | F5 . . . A5 . F5 . | G5 . . . D5 . B4 . |"
        " A5 . . . G5 . E5 . | C5 . E5 . A5 . . . | A5 . G5 . F5 . D5 . | E5 . . . . . . . |"
    )
    melody = [token for token in (melody_a + " " + melody_b).split() if token != "|"]
    step = int(RATE * eighth)
    total = step * len(melody)
    track = np.zeros(total)

    def add(sound, start):
        end = min(total, start + sound.size)
        track[start:end] += sound[: end - start]

    lead_note = None
    lead_start = 0
    for index, token in enumerate(melody + ["END"]):
        if token != "." and lead_note is not None:
            length = index * step - lead_start
            t = seconds(length / RATE)
            freq = note_frequency(lead_note)
            vibrato = freq * (1 + 0.006 * np.sin(2 * np.pi * 6 * t))
            add(square(vibrato, t, 0.25) * 0.16 * envelope(t.size, 0.004, 0.04), lead_start)
        if token not in (".", "END"):
            lead_note = token
            lead_start = index * step

    for bar, chord in enumerate(chords):
        bar_start = bar * step * 8
        root = note_frequency(roots[chord])
        for beat in range(8):
            start = bar_start + beat * step
            t = seconds(eighth * 0.9)
            octave = 2 if beat % 2 else 1
            add(triangle(root * octave, t) * 0.32 * envelope(t.size, 0.002, 0.02), start)
            arp = note_frequency(arps[chord][beat % 4])
            t16 = seconds(eighth / 2 * 0.9)
            add(square(arp, t16, 0.125) * 0.05 * envelope(t16.size, 0.002, 0.01), start)
            add(square(arp * 2, t16, 0.125) * 0.035 * envelope(t16.size, 0.002, 0.01), start + step // 2)

            kick = beat in (0, 3, 4)
            snare = beat in (2, 6)
            if kick:
                tk = seconds(0.12)
                add(np.sin(2 * np.pi * np.cumsum(np.linspace(150, 40, tk.size)) / RATE) * decay(tk, 25) * 0.55, start)
            if snare:
                ts = seconds(0.14)
                add(lowpass(noise(ts, bar * 8 + beat), 0.6) * decay(ts, 22) * 0.3, start)
            th = seconds(0.03)
            add(noise(th, 100 + beat) * decay(th, 120) * 0.08, start + step // 2)
    return track


def write_ogg(samples, name, volume=0.8):
    peak = max(1e-6, float(np.max(np.abs(samples))))
    data = (samples / peak * volume * 32767).astype(np.int16)
    with tempfile.TemporaryDirectory() as folder:
        wav_path = Path(folder) / "sound.wav"
        with wave.open(str(wav_path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(RATE)
            wav.writeframes(data.tobytes())
        subprocess.run(
            ["ffmpeg", "-loglevel", "error", "-y", "-i", str(wav_path), "-c:a", "libvorbis", "-q:a", "2", str(GAME_DIR / name)],
            check=True,
        )
    print("wrote", name)


def make_sounds():
    sounds = {
        "thwip": sfx_thwip,
        "web_hit": sfx_web_hit,
        "hit": sfx_hit,
        "explosion": sfx_explosion,
        "hurt": sfx_hurt,
        "jump": sfx_jump,
        "swing": sfx_swing,
        "stomp": sfx_stomp,
        "defeat": sfx_defeat,
        "combo": sfx_combo,
        "heal": sfx_heal,
        "warning": sfx_warning,
        "laugh": sfx_laugh,
        "fire": sfx_fire,
        "win": sfx_win,
        "lose": sfx_lose,
        "phase": sfx_phase,
    }
    sound_dir = GAME_DIR / "sounds"
    sound_dir.mkdir(exist_ok=True)
    for name, make in sounds.items():
        write_ogg(make(), f"sounds/{name}.ogg")
    write_ogg(music(), "sounds/music.ogg", volume=0.7)


if __name__ == "__main__":
    pygame.init()
    make_sprites()
    make_sounds()
