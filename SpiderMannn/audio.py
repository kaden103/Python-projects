import pygame

from settings import ASSET_DIR


SOUND_VOLUMES = {
    "thwip": 0.45,
    "web_hit": 0.7,
    "hit": 0.8,
    "explosion": 0.55,
    "hurt": 0.7,
    "jump": 0.35,
    "swing": 0.5,
    "stomp": 0.7,
    "defeat": 0.6,
    "combo": 0.4,
    "heal": 0.6,
    "warning": 0.5,
    "laugh": 0.8,
    "fire": 0.5,
    "win": 0.8,
    "lose": 0.8,
    "phase": 0.7,
}
MUSIC_VOLUME = 0.4


class Audio:
    """Sound effects and music. If there is no audio device the game carries on silently."""

    def __init__(self):
        self.sounds = {}
        self.muted = False
        self.music_playing = False
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.set_num_channels(16)
            for name, volume in SOUND_VOLUMES.items():
                sound = pygame.mixer.Sound(str(ASSET_DIR / "sounds" / f"{name}.ogg"))
                sound.set_volume(volume)
                self.sounds[name] = sound
        except (pygame.error, FileNotFoundError):
            self.sounds = {}

    @property
    def enabled(self):
        return bool(self.sounds)

    def play(self, name):
        if self.enabled and not self.muted and name in self.sounds:
            self.sounds[name].play()

    def start_music(self):
        if not self.enabled:
            return
        try:
            pygame.mixer.music.load(str(ASSET_DIR / "sounds" / "music.ogg"))
            pygame.mixer.music.set_volume(0 if self.muted else MUSIC_VOLUME)
            pygame.mixer.music.play(-1)
            self.music_playing = True
        except pygame.error:
            self.music_playing = False

    def stop_music(self):
        if self.music_playing:
            pygame.mixer.music.fadeout(400)
            self.music_playing = False

    def toggle_mute(self):
        self.muted = not self.muted
        if self.enabled:
            pygame.mixer.music.set_volume(0 if self.muted else MUSIC_VOLUME)
            if self.muted:
                pygame.mixer.stop()
