# Adım 1: Gerekli kütüphaneyi içe aktar
# Copilot'a: "# Pygame kütüphanesini içe aktar"
import pygame
import webbrowser
import sys # Programı düzgün kapatmak için
import random
import math
import json
import os
from deck import Deck, Card as DeckCard
from itertools import combinations
try:
    from globals import *
except Exception:
    # If globals.py is missing or fails to import, fall back to defaults
    pass

# Helper: resource path resolver for PyInstaller bundles
def resource_path(relative_path):
    """ Hem normal çalışmada hem de PyInstaller .exe'sinde asset'lerin yolunu doğru al. """
    try:
        # 1. Eğer yol zaten mutlaksa (örn: /Users/...), olduğu gibi döndür.
        if os.path.isabs(relative_path):
            return relative_path

        # 2. PyInstaller temp klasörü veya mevcut dizin
        try:
            base_path = sys._MEIPASS
        except Exception:
            base_path = os.path.abspath(".")

        return os.path.join(base_path, relative_path)
    except Exception:
        return relative_path

# When frozen by PyInstaller, ensure imageio/moviepy find the ffmpeg binary
try:
    if getattr(sys, 'frozen', False):
        # If we bundle ffmpeg at the root of the bundle, expose it via IMAGEIO_FFMPEG_EXE
        try:
            ff = resource_path('ffmpeg')
            os.environ.setdefault('IMAGEIO_FFMPEG_EXE', ff)
        except Exception:
            pass
except Exception:
    pass

# Monkey-patch common pygame/file loaders so relative asset paths like
# 'assets/...' automatically resolve inside bundled executables.
try:
    _orig_pygame_image_load = pygame.image.load
    def _patched_image_load(path, *args, **kwargs):
        try:
            if isinstance(path, str) and not os.path.isabs(path):
                path = resource_path(path)
        except Exception:
            pass
        return _orig_pygame_image_load(path, *args, **kwargs)
    pygame.image.load = _patched_image_load
except Exception:
    pass

try:
    if hasattr(pygame, 'mixer') and getattr(pygame, 'mixer') is not None:
        _orig_mixer_Sound = pygame.mixer.Sound
        def _patched_mixer_Sound(path, *args, **kwargs):
            try:
                if isinstance(path, str) and not os.path.isabs(path):
                    path = resource_path(path)
            except Exception:
                pass
            return _orig_mixer_Sound(path, *args, **kwargs)
        pygame.mixer.Sound = _patched_mixer_Sound

        _orig_music_load = pygame.mixer.music.load
        def _patched_music_load(path, *args, **kwargs):
            try:
                if isinstance(path, str) and not os.path.isabs(path):
                    path = resource_path(path)
            except Exception:
                pass
            return _orig_music_load(path, *args, **kwargs)
        pygame.mixer.music.load = _patched_music_load
except Exception:
    pass

# Optional video playback support via moviepy
MOVIEPY_AVAILABLE = False
try:
    from moviepy import VideoFileClip
    MOVIEPY_AVAILABLE = True
except Exception as e:
    MOVIEPY_AVAILABLE = False
    try:
        import traceback
        print('moviepy import failed in frozen app:')
        traceback.print_exc()
    except Exception:
        pass

# Optional numpy availability flag (used for efficient frame -> surface conversion)
NUMPY_AVAILABLE = False
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except Exception as e:
    np = None
    NUMPY_AVAILABLE = False
    try:
        import traceback
        print('numpy import failed in frozen app:')
        traceback.print_exc()
    except Exception:
        pass

# --- Adım 2: Oyun Ayarları ve Pencereyi Oluşturma ---
# Copilot'a: "# 800x600 boyutunda bir pencere oluştur"

pygame.init() # Pygame'i başlat
# Load persisted deck unlocks (if available)
try:
    load_deck_unlocks()
except Exception:
    pass
# Load all card images dictionary will be prepared after init
card_images = {}


def check_progression_unlocks(current_ante_level):
    """Unlock decks based on completed ante progression and save.

    Note: `current_ante_level` is the ante we have just entered; if it's 4,
    it means the player completed ante 3.
    """
    global DECK_UNLOCKS
    unlocked_new_deck = False

    # Ante 3 completed -> we've entered ante 4
    if current_ante_level == 4 and not DECK_UNLOCKS.get('GOLD', False):
        DECK_UNLOCKS['GOLD'] = True
        unlocked_new_deck = True

    # Ante 6 completed -> we've entered ante 7
    if current_ante_level == 7 and not DECK_UNLOCKS.get('GHOST', False):
        DECK_UNLOCKS['GHOST'] = True
        unlocked_new_deck = True

    # Ante 9 completed -> we've entered ante 10
    if current_ante_level == 10 and not DECK_UNLOCKS.get('CHAOS', False):
        DECK_UNLOCKS['CHAOS'] = True
        unlocked_new_deck = True

    if unlocked_new_deck:
        try:
            save_deck_unlocks()
        except Exception:
            pass


# Ekran boyutları (Proje Ayarları -> Pencere)
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
# Renkler
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
# Game state constants (use integers for centralized state handling)
STATE_MAIN_MENU = 0
STATE_PLAYING = 1
STATE_SHOP = 2
STATE_DECK_SELECTION = 3
# Alias for alternate naming in codepaths
STATE_DECK_SELECT = STATE_DECK_SELECTION
STATE_GAME_OVER = 4
STATE_SETTINGS = 5  # (Use appropriate next integer numbers)
STATE_CREDITS = 6
STATE_BOSS_DEFEATED_A = 7
STATE_BOSS_DEFEATED_B = 8
STATE_GAMBIT_CHOICE = 9
STATE_GAMBIT_RESULT = 10
STATE_TRUE_ENDING = 11
STATE_VIDEO_INTRO = 12
STATE_MERCY_PHASE = 13
# Kart Boyutu (Custom Minimum Size)
# Quick tuning: reduce default scale from 1.8 to 1.4 for better fit
CARD_SCALE = 1.4
# Base (design) card size is 100x150; apply `CARD_SCALE` to make them larger by default.
CARD_WIDTH = int(100 * CARD_SCALE)
CARD_HEIGHT = int(150 * CARD_SCALE)

# Kartların normal Y pozisyonu
NORMAL_Y = 200
# Selected Y when a card is lifted/selected (smaller lift to avoid excessive rise)
SELECTED_Y = NORMAL_Y - 15

# Small configurable vertical offset applied to all card Y calculations
# Use this to nudge the whole hand slightly lower on screen when desired.
CARD_Y_OFFSET = 30
# Hierarchical Y-position constants used by layout functions
# NORMAL = base, HOVER = slight lift, SELECTED = larger lift
NORMAL_Y_POS = 490
HOVER_Y_POS = 475
SELECTED_Y_POS = 460

# Ekranı oluştur (Ana Sahne)
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("VSCode + Copilot ile Balatro Prototipi")

# Frame timing
clock = pygame.time.Clock()
FPS = 60
# Particle manager startup globals (Adım 2)
particles = []
max_particles = 50  # Aynı anda ekranda olacak maksimum parçacık sayısı
particle_spawn_timer = 0
spawn_interval = 200  # Her 200ms'de bir yeni parçacık üretmeyi dene

# Detect desktop size for better fullscreen handling
DESKTOP_SIZE = pygame.display.get_desktop_sizes()[0]
print(f"Masaüstü boyutu algılandı: {DESKTOP_SIZE}")

# --- OYUN AYARLARI ---
settings_data = {
    'music_volume': 0.5,  # (0.0 ile 1.0 arası)
    'sfx_volume': 1.0,
    'music_on': True,
    'sfx_on': True,
    'display_mode': 'windowed', # 'windowed' veya 'fullscreen'
    'resolution': (1280, 720) # (Varsayılan çözünürlük)
}
available_resolutions = [(1280, 720), (1600, 900), (1920, 1080), (2560, 1440)]
current_resolution_index = 0 # (available_resolutions listesindeki indeks)

# MAPPING: Resmi poker el isimleri — evaluate_hand() çıktısını bu sözlükteki anahtarlara
# çevirirseniz ekranda gösterilecek insan-dostu isimleri merkezi olarak burada saklayabilirsiniz.
POKER_HAND_NAMES = {
    'HIGH_CARD': "High Card",
    'PAIR': "Pair",
    'TWO_PAIR': "Two Pair",
    'THREE_OF_A_KIND': "Three of a Kind",
    'STRAIGHT': "Straight",
    'FLUSH': "Flush",
    'FULL_HOUSE': "Full House",
    'FOUR_OF_A_KIND': "Four of a Kind",
    'STRAIGHT_FLUSH': "Straight Flush",
    'ROYAL_FLUSH': "Royal Flush",
    'FIVE_OF_A_KIND': "Five of a Kind",
    'FLUSH_FIVE': "Flush Five" # (Eğer 5 kartlık flush var ise)
}

# (Bu sözlük, evaluate_hand'in döndürdüğü anahtarları (key) alıp, ekranda gösterilecek metinlere (value) çevirmelidir.)

# --- Uygulanan Ayarlar (Hafıza) ---
current_applied_res = settings_data['resolution']
current_applied_fullscreen = (settings_data['display_mode'] == 'fullscreen')
# Dropdown state for resolution selection UI
dropdown_active = False
# Gameplay processing flags
# When a hand is being processed, set `is_hand_processing` to True to prevent
# concurrent selection/interaction. `cards_locked` can be used by UI code to
# disable selection while processing. They default to False.
is_hand_processing = False
cards_locked = False
# --- Hafıza Bitiş ---
# --- OYUN AYARLARI BİTİŞ ---


def play_sound(sound_effect):
    """ Sesi çalmadan önce SFX ayarını kontrol eden güvenli fonksiyon. """
    try:
        if settings_data.get('sfx_on', True):
            # Gelecekte SFX ses seviyesini de buradan ayarlayabiliriz
            # sound_effect.set_volume(settings_data['sfx_volume'])
            sound_effect.play()
    except pygame.error as e:
        try:
            print(f"Ses efekti hatası: {e}")
        except Exception:
            pass


# Small helper used by various UI locations when we want to show a
# non-fatal error to the player. Keep this minimal so missing GUI
# subsystems won't crash the game; it logs to stdout and can be
# expanded later to show an in-game popup.
def show_error_message(message, title='Hata'):
    try:
        print(f"[{title}] {message}")
    except Exception:
        pass


# Ensure splash/video-related globals exist with safe defaults so the
# video-intro fallback code doesn't trigger linter/runtime warnings.
try:
    if 'splash_screen_end_time' not in globals():
        splash_screen_end_time = 0
except Exception:
    splash_screen_end_time = 0

try:
    if 'splash_fallback_image' not in globals():
        splash_fallback_image = None
except Exception:
    splash_fallback_image = None

# Per-frame click lock (prevents double-handling multiple MOUSE events
# in the same frame). Added as a safe default; other code may overwrite
# this later but having a default reduces undefined-name warnings.
try:
    if 'CLICK_LOCKED' not in globals():
        CLICK_LOCKED = False
except Exception:
    CLICK_LOCKED = False


def handle_settings_click(mouse_pos):
    """ STATE_SETTINGS'deki tüm tıklama mantığını yönetir. """
    global game_state

    # --- Dropdown Kapanma Kontrolü ---
    global dropdown_active

    if dropdown_active:
        # Menü dışında bir yere tıklandıysa kapat
        is_click_on_dropdown_area = False
        for i, res in enumerate(available_resolutions):
            if menu_buttons_data.get(f'RES_{i}') and menu_buttons_data[f'RES_{i}'].collidepoint(mouse_pos):
                is_click_on_dropdown_area = True
                break
        
        # Eğer tıklama çözüm butonu (BTN_RES) üzerinde veya seçim listesi üzerinde değilse kapat
        if not is_click_on_dropdown_area and (not menu_buttons_data.get('BTN_RES') or not menu_buttons_data['BTN_RES'].collidepoint(mouse_pos)):
            dropdown_active = False
            return # Dışarıda tıklandıysa çık
    # --- Kapanma Kontrolü Bitişi ---

    # ÖNCE GERİ BUTONU KONTROLÜ
    if menu_buttons_data.get('GERİ_settings') and menu_buttons_data['GERİ_settings'].collidepoint(mouse_pos):
        game_state = STATE_MAIN_MENU
        return

    # (Display mode toggle was moved below the resolution block)

    # --- Ekran Boyutu Dropdown Mantığı (Aç/Kapa ve Seçim) ---
    if menu_buttons_data.get('BTN_RES') and menu_buttons_data['BTN_RES'].collidepoint(mouse_pos):
        dropdown_active = not dropdown_active # Dropdown'ı aç/kapa
        return

    # Dropdown Listesinden Seçim Yapma
    if dropdown_active:
        for i, res in enumerate(available_resolutions):
            btn_key = f'RES_{i}'
            if menu_buttons_data.get(btn_key) and menu_buttons_data[btn_key].collidepoint(mouse_pos):
                # Çözünürlüğü uygula
                global screen, current_applied_res, current_resolution_index
                settings_data['resolution'] = res
                current_resolution_index = i
                print(f"Çözünürlük ayarlandı: {res}")

                # Ayarı hemen uygulamak için memory değişkenini geçersiz kıl (Gözetmen'i tetikle)
                current_applied_res = (0, 0) # Sahte bir değer atar
                
                dropdown_active = False # Dropdown'ı kapat
                return

    

    # --- Müzik Sesi Ayarlama (Birleşik) ---
    if menu_buttons_data.get('BTN_VOL_DOWN') and menu_buttons_data['BTN_VOL_DOWN'].collidepoint(mouse_pos):
        # Sol tarafa tıklandı
        settings_data['music_volume'] = max(0.0, settings_data['music_volume'] - 0.1) # KISMA
        pygame.mixer.music.set_volume(settings_data['music_volume'] if settings_data['music_on'] else 0.0)
        print(f"Müzik Sesi: {settings_data['music_volume']}")
        return
    elif menu_buttons_data.get('BTN_VOL_UP') and menu_buttons_data['BTN_VOL_UP'].collidepoint(mouse_pos):
        # Sağ tarafa tıklandı
        settings_data['music_volume'] = min(1.0, settings_data['music_volume'] + 0.1) # ARTIRMA
        pygame.mixer.music.set_volume(settings_data['music_volume'] if settings_data['music_on'] else 0.0)
        print(f"Müzik Sesi: {settings_data['music_volume']}")
        return

    # --- Müzik Açık/Kapalı ---
    if menu_buttons_data.get('BTN_MUSIC_TOGGLE') and menu_buttons_data['BTN_MUSIC_TOGGLE'].collidepoint(mouse_pos):
        settings_data['music_on'] = not settings_data['music_on']
        if settings_data['music_on']:
            pygame.mixer.music.set_volume(settings_data['music_volume'])
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.set_volume(0.0)
            pygame.mixer.music.pause()
        return

    # --- Sesler (SFX) Açık/Kapalı ---
    if menu_buttons_data.get('BTN_SFX_TOGGLE') and menu_buttons_data['BTN_SFX_TOGGLE'].collidepoint(mouse_pos):
        settings_data['sfx_on'] = not settings_data['sfx_on']
        print(f"Ses Efektleri: {settings_data['sfx_on']}")
        return

# --- Adım 3: 'Card' Kalıbını Kod Olarak Oluşturma (Card.tscn + Card.cs) ---
# Copilot'a: "# Pygame'de tıklanabilir bir Kart sınıfı (class) oluştur"

class Card:
    # Bu, 'Card.cs' script'indeki değişkenler gibidir
    def __init__(self, image, x, y, rank, suit):
        # Card.tscn'deki TextureRect
        self.image = pygame.transform.scale(image, (CARD_WIDTH, CARD_HEIGHT))
        
        # Card.tscn'deki 'Layout' (Konum ve Boyut)
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
        # Card.cs'teki 'Rank' ve 'Suit' değişkenleri
        self.rank = rank
        self.suit = suit
        # Seçili mi değil mi bilgisini tutar (toggle ile değişecek)
        self.is_selected = False
        # hovered flag set each frame by MOUSEMOTION handling
        self.is_hovered = False
        # base positions for layout and animation
        self.base_x = x
        self.base_y = y
        # target positions for smooth animation
        # initialize targets to current rect position so update() lerps from here
        self.target_x = float(self.rect.x)
        self.target_y = float(self.rect.y)

        # temporary drag base positions used during group dragging
        self.drag_base_x = self.base_x
        self.drag_base_y = self.base_y

        # Edition and seal metadata (used for bonuses and shop effects)
        # edition: None | 'Foil' | 'Holo' (rare)
        # seal: None | 'Red' (applied by shop voucher)
        self.edition = None
        self.seal = None
        try:
            # ~1% chance to be special (Foil or Holo)
            if random.random() < 0.01:
                self.edition = random.choice(['Foil', 'Holo'])
        except Exception:
            # if random fails for any reason, leave edition as None
            pass

    def update(self):
        """Smoothly move rect toward target positions using easing.

        Y is updated with a small lerp step so selection movement feels smooth.
        """
        # Smoothly lerp rect.x/y toward target_x/target_y every frame
        try:
            self.rect.x += (self.target_x - self.rect.x) * 0.1
            self.rect.y += (self.target_y - self.rect.y) * 0.1
            # ensure rect stores int coordinates
            self.rect.x = int(self.rect.x)
            self.rect.y = int(self.rect.y)
        except Exception:
            pass

        # Settings screen "GERİ" button handling when on settings state
        try:
            if game_state == STATE_SETTINGS and event.type == pygame.MOUSEBUTTONUP and getattr(event, 'button', None) == 1:
                mouse_pos = event.pos
                try:
                    if menu_buttons_data.get('GERİ_settings') and menu_buttons_data['GERİ_settings'].collidepoint(mouse_pos):
                        game_state = STATE_MAIN_MENU
                except Exception:
                    pass
        except Exception:
            pass

    # Bu, 'SetTexture' ve 'Label'ı ayarlayan kod gibidir
    def draw(self, surface):
        # Eğer kart seçiliyse, etrafına vurgulu bir çerçeve çiz
        if self.is_selected:
            highlight_rect = self.rect.inflate(6, 6)
            pygame.draw.rect(surface, (255, 223, 0), highlight_rect, border_radius=5, width=3)

        # Kart görselini çiz
        surface.blit(self.image, self.rect)

        # Draw edition badge and seal indicator (non-intrusive overlays)
        try:
            # Edition badge (top-right)
            if getattr(self, 'edition', None):
                badge_text = str(self.edition)
                try:
                    badge_s = game_font_small.render(badge_text, True, (255, 255, 255))
                except Exception:
                    badge_s = pygame.font.SysFont(None, 16).render(badge_text, True, (255,255,255))
                bx = self.rect.right - badge_s.get_width() - 10
                by = self.rect.top + 6
                badge_rect = pygame.Rect(bx - 6, by - 4, badge_s.get_width() + 12, badge_s.get_height() + 8)
                pygame.draw.rect(surface, (24, 24, 48), badge_rect, border_radius=6)
                pygame.draw.rect(surface, (220, 180, 40), badge_rect, 2, border_radius=6)
                surface.blit(badge_s, (bx, by))

            # Red seal indicator (small circle top-left)
            if getattr(self, 'seal', None) == 'Red':
                cx = self.rect.left + 14
                cy = self.rect.top + 14
                pygame.draw.circle(surface, (200, 30, 30), (cx, cy), 10)
                try:
                    inner = game_font_small.render('R', True, (255, 255, 255))
                    ir = inner.get_rect(center=(cx, cy))
                    surface.blit(inner, ir)
                except Exception:
                    pass
        except Exception:
            pass

        # Holo visual: subtle rainbow overlay + small badge (if card has is_holo)
        try:
            pass
        except Exception:
            pass
class ScoreSplash(pygame.sprite.Sprite):
    """Small floating text sprite used to show score and multiplier splashes.

    Usage: `ScoreSplash(text, x, y, color, lifetime=1.0, vel_y=-60)` and add to
    `scores_splash_group`. `update(dt_seconds)` expects seconds.
    """
    def __init__(self, text, x, y, color=(255,255,255), lifetime=1.0, vel_y=-60, font=None):
        try:
            super().__init__()
        except Exception:
            pass
        self.text = str(text)
        self.font = font or globals().get('game_font_small')
        self.color = color or (255,255,255)
        try:
            self.image = self.font.render(self.text, True, self.color)
        except Exception:
            try:
                self.image = pygame.Surface((1,1), pygame.SRCALPHA)
            except Exception:
                self.image = None
        try:
            self.rect = self.image.get_rect(center=(int(x), int(y)))
        except Exception:
            try:
                self.rect = pygame.Rect(int(x), int(y), 1, 1)
            except Exception:
                self.rect = pygame.Rect(0, 0, 1, 1)
        try:
            self.initial_lifetime = float(lifetime)
        except Exception:
            self.initial_lifetime = 1.0
        self.lifetime = float(self.initial_lifetime)
        try:
            self.vel_y = float(vel_y)
        except Exception:
            self.vel_y = -60.0
        self.alpha = 255

    def update(self, dt: float = 0.0):
        try:
            self.lifetime -= float(dt)
        except Exception:
            self.lifetime -= 0.016
        if self.lifetime <= 0:
            try:
                self.kill()
            except Exception:
                pass
            return
        try:
            self.rect.y += int(self.vel_y * float(dt))
        except Exception:
            try:
                self.rect.y += int(self.vel_y * 0.016)
            except Exception:
                pass
        try:
            frac = max(0.0, min(1.0, self.lifetime / float(self.initial_lifetime))) if self.initial_lifetime else 0.0
            self.alpha = int(255 * frac)
        except Exception:
            try:
                self.alpha = max(0, self.alpha - int(80 * float(dt) if isinstance(dt, (int, float)) else 1))
            except Exception:
                pass
        try:
            if self.font is not None and self.image is not None:
                self.image = self.font.render(self.text, True, self.color)
                try:
                    self.image.set_alpha(self.alpha)
                except Exception:
                    pass
        except Exception:
            pass

    def draw(self, surface):
        try:
            if self.image is not None:
                surface.blit(self.image, self.rect)
        except Exception:
            pass

# Yeni bir Sprite Grubu oluşturulmalı (global alanda)
scores_splash_group = pygame.sprite.Group()

# Lightweight particle system: subtle background 'spirit sparks'
particle_last_update = pygame.time.get_ticks()
last_particle_spawn = particle_spawn_timer
PARTICLE_SPAWN_INTERVAL_MS = spawn_interval
PARTICLE_MAX_COUNT = max_particles


class Particle:
    """Very small, cheap particle used for subtle background ambience.

    Particles are intentionally simple: a position, velocity, lifetime and
    color. They update with elapsed milliseconds and render to a tiny
    SRCALPHA surface so they remain cheap and don't require extra textures.
    """
    def __init__(self, screen_width, screen_height, x: float = None):
        # store screen dimensions so particle can compute fade relative to height
        self.screen_width = int(screen_width)
        self.screen_height = int(screen_height)

        # horizontal position: use provided x (spawn area) or random across screen
        if x is None:
            self.x = float(random.randint(0, max(1, self.screen_width - 1)))
        else:
            try:
                self.x = float(x)
            except Exception:
                self.x = float(random.randint(0, max(1, self.screen_width - 1)))

        # start Y anywhere across the screen height for a distributed effect
        self.y = float(random.randint(0, max(1, self.screen_height - 1)))

        # Size in pixels
        self.size = random.uniform(2.0, 4.5)

        # speed in pixels per second (upwards)
        self.speed = random.uniform(10.0, 80.0)

        # gentle horizontal oscillation parameters
        self.x_offset = random.uniform(0.0, 2 * math.pi)
        self.amplitude = random.uniform(4.0, 18.0)
        self.frequency = random.uniform(0.005, 0.03)

        # starting alpha (0-255) and keep a copy for scaling
        self.initial_alpha = random.randint(30, 160)
        self.alpha = int(self.initial_alpha)

        # color: pale blue or warm gold with alpha stored in a pygame.Color
        if random.random() < 0.5:
            col = (200, 220, 255)
        else:
            col = (255, 230, 200)
        self.color = pygame.Color(col[0], col[1], col[2], self.alpha)

    def update(self, dt_ms: float) -> bool:
        """Advance particle by dt_ms milliseconds. Returns False when dead.

        Movement uses pixels-per-second speed; dt_ms is converted to seconds
        so motion is consistent across frame rates.
        """
        try:
            dt = float(dt_ms) / 1000.0
            # move upward
            self.y -= self.speed * dt

            # horizontal sinusoidal drift based on current Y
            self.x += self.amplitude * math.sin(self.x_offset + self.frequency * self.y) * dt * 30.0

            # clamp x to screen so we don't drift far off
            if self.x < -50:
                self.x = -50
            if self.x > self.screen_width + 50:
                self.x = self.screen_width + 50

            # alpha scales with vertical position: more opaque near bottom, fade near top
            try:
                decay_factor = max(0.0, min(1.0, (self.y + self.size) / float(max(1, self.screen_height))))
            except Exception:
                decay_factor = 0.0
            self.alpha = int(self.initial_alpha * decay_factor)
            self.color.a = max(0, min(255, int(self.alpha)))

            # dead when off the top or fully transparent
            if self.y < -self.size or self.alpha <= 1:
                return False
            return True
        except Exception:
            return False

    def draw(self, surface):
        try:
            s = int(max(2, self.size * 4))
            tmp = pygame.Surface((s, s), pygame.SRCALPHA)
            col = (self.color[0], self.color[1], self.color[2], max(0, min(255, int(self.alpha))))
            pygame.draw.circle(tmp, col, (s // 2, s // 2), max(1, int(self.size)))
            surface.blit(tmp, (int(self.x - s // 2), int(self.y - s // 2)))
        except Exception:
            pass


def spawn_particle_at(x=None, y=None):
    try:
        if len(particles) >= PARTICLE_MAX_COUNT:
            return
        # Particle will choose a random Y across the screen; X can be provided to bias spawn
        particles.append(Particle(SCREEN_WIDTH, SCREEN_HEIGHT, x))
    except Exception:
        pass


def update_particles(dt_ms: float):
    """Advance particle system by dt_ms milliseconds (frame-rate independent).

    This replaces the previous get_ticks()-based approach and accumulates
    a simple spawn timer so spawning remains consistent across variable FPS.
    """
    global particle_spawn_timer
    try:
        # spawn timer accumulates elapsed milliseconds
        particle_spawn_timer += dt_ms
        try:
            if particle_spawn_timer >= PARTICLE_SPAWN_INTERVAL_MS:
                # consume one interval (allow slight drift)
                particle_spawn_timer -= PARTICLE_SPAWN_INTERVAL_MS
                sx = random.randint(int(SCREEN_WIDTH * 0.15), int(SCREEN_WIDTH * 0.85))
                sy = random.randint(12, max(24, int(SCREEN_HEIGHT * 0.28)))
                for _ in range(random.randint(1, 2)):
                    spawn_particle_at(sx + random.uniform(-36, 36), sy + random.uniform(-12, 12))
        except Exception:
            pass

        # update particles and compact list
        newp = []
        for p in particles:
            try:
                if p.update(dt_ms):
                    newp.append(p)
            except Exception:
                pass
        particles[:] = newp
    except Exception:
        pass


def draw_particles(surface):
    try:
        for p in particles:
            try:
                p.draw(surface)
            except Exception:
                pass
    except Exception:
        pass


# Placeholder surfaces will be created by loader if specific card images are missing

def load_all_card_images():
    """Load card images from assets/{suit}_{rank}.png using Deck's suit/rank lists.

    Images are stored in the global card_images dict as card_images[suit][rank] = Surface
    If a file is missing, a simple placeholder Surface is created so the game keeps running.
    """
    global card_images
    card_images = {}
    d = Deck()
    suits = d._suits
    ranks = d._ranks
    for s in suits:
        card_images[s] = {}
        for r in ranks:
            path = f"assets/{s}_{r}.png"
            try:
                img = pygame.image.load(resource_path(path))
                img = pygame.transform.scale(img, (CARD_WIDTH, CARD_HEIGHT))
            except Exception:
                # create a simple placeholder surface (red for hearts/diamonds, dark for spades/clubs)
                placeholder = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
                if s in ("spades", "clubs"):
                    placeholder.fill((40, 40, 40))
                else:
                    placeholder.fill((200, 50, 50))
                # draw rank text on placeholder
                try:
                    # use game_font_small if available (loader is called after fonts are created)
                    font = game_font_small
                    txt = font.render(str(r), True, (255, 255, 255))
                    tr = txt.get_rect(center=(CARD_WIDTH//2, CARD_HEIGHT//2))
                    placeholder.blit(txt, tr)
                except Exception:
                    pass
                img = placeholder

            card_images[s][r] = img

# Load background image and game fonts, then load card images
try:
    background_image_original = pygame.image.load(resource_path("assets/background.png"))
    try:
        background_image = pygame.transform.scale(background_image_original, (SCREEN_WIDTH, SCREEN_HEIGHT))
    except Exception:
        # fallback if scaling fails
        background_image = background_image_original.copy()
except Exception:
    background_image_original = None
    background_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    background_image.fill(BLACK)

# Load TTF font (game font) - fall back to SysFont if missing
try:
    game_font = pygame.font.Font(resource_path('assets/my_font.ttf'), 32)
    game_font_small = pygame.font.Font(resource_path('assets/my_font.ttf'), 28)
except Exception:
    game_font = pygame.font.SysFont(None, 32)
    game_font_small = pygame.font.SysFont(None, 28)

# Now load all card images (placeholders will use game_font_small)
load_all_card_images()

# --- ANA MENÜ VARLIKLARI ---
try:
    logo_image = pygame.image.load(resource_path('assets/logo.png'))
    logo_image = pygame.transform.scale(logo_image, (600, 600))
    # İsteğe bağlı: Logoyu yeniden boyutlandırabilirsiniz, örn:
    # logo_image = pygame.transform.scale(logo_image, (400, 400))
    menu_font = pygame.font.Font(None, 74) # Buton yazı tipi boyutu
    # Smaller variants for main menu so items fit on smaller screens
    try:
        menu_font_medium = pygame.font.Font(None, 70)  # medium size for menus
    except Exception:
        try:
            menu_font_medium = pygame.font.SysFont(None, 70)
        except Exception:
            menu_font_medium = menu_font
    try:
        menu_font_small_menu = pygame.font.Font(None, 66)  # one size smaller for tight layouts
    except Exception:
        try:
            menu_font_small_menu = pygame.font.SysFont(None, 66)
        except Exception:
            menu_font_small_menu = menu_font_medium
    # Load optional HUD icon images (left-stat panel). Use simple dict keyed by
    # the same logical icon names used by the HUD's icon_map ('coin','target',...)
    ICONS = {}
    _icon_files = {
        'coin': 'assets/icons/icon_money.png',
        'target': 'assets/icons/icon_target.png',
        'hand': 'assets/icons/icon_hand.png',
        'refresh': 'assets/icons/icon_discard.png',
        'star': 'assets/icons/icon_score.png',
    }
    for k, p in _icon_files.items():
        try:
            img = pygame.image.load(resource_path(p)).convert_alpha()
            ICONS[k] = img
        except Exception:
            ICONS[k] = None
    # Load gameplay button images (play hand / discard)
    try:
        PLAY_BTN_IMG = pygame.image.load(resource_path('assets/buttons/button_play_hand.png')).convert_alpha()
    except Exception:
        PLAY_BTN_IMG = None
    try:
        DISCARD_BTN_IMG = pygame.image.load(resource_path('assets/buttons/button_discard_cards.png')).convert_alpha()
    except Exception:
        DISCARD_BTN_IMG = None

    # Optional decorative hand images for the main menu background
    try:
        _hb = pygame.image.load(resource_path('assets/hands/hand_bottom_left.png')).convert_alpha()
        try:
            hand_target_width = int(SCREEN_WIDTH * 0.55)
        except Exception:
            hand_target_width = 400
        try:
            hw = _hb.get_width()
            hh = _hb.get_height()
            new_h = max(1, int(hh * (hand_target_width / max(1, hw))))
            hand_bottom_left_img = pygame.transform.smoothscale(_hb, (hand_target_width, new_h))
        except Exception:
            hand_bottom_left_img = _hb
    except Exception:
        hand_bottom_left_img = None
    try:
        _ht = pygame.image.load(resource_path('assets/hands/hand_top_right.png')).convert_alpha()
        try:
            hand_target_width = int(SCREEN_WIDTH * 0.55)
        except Exception:
            hand_target_width = 400
        try:
            tw = _ht.get_width()
            th = _ht.get_height()
            new_h2 = max(1, int(th * (hand_target_width / max(1, tw))))
            hand_top_right_img = pygame.transform.smoothscale(_ht, (hand_target_width, new_h2))
        except Exception:
            hand_top_right_img = _ht
    except Exception:
        hand_top_right_img = None

    # Team Husk credit/logo for main menu (bottom-right) — load and scale to target width
    try:
        HUSK_LOGO_TARGET_WIDTH = 180
        team_husk_logo_img_original = pygame.image.load(resource_path('assets/logo_menu.png')).convert_alpha()
        try:
            ow = team_husk_logo_img_original.get_width()
            oh = team_husk_logo_img_original.get_height()
            aspect = (oh / max(1, ow))
            new_h = max(1, int(HUSK_LOGO_TARGET_WIDTH * aspect))
            team_husk_logo_img = pygame.transform.smoothscale(team_husk_logo_img_original, (HUSK_LOGO_TARGET_WIDTH, new_h))
        except Exception:
            team_husk_logo_img = team_husk_logo_img_original
    except Exception as e:
        try:
            print(f"HATA: Team Husk logosu ('logo_menu.png') yüklenemedi: {e}")
        except Exception:
            pass
        team_husk_logo_img = None

    # Per-button pressed timing for short press animation
    play_button_pressed = False
    play_button_pressed_time = 0
    discard_button_pressed = False
    discard_button_pressed_time = 0
    menu_buttons_data = {} # Butonların konumlarını (Rect) saklamak için
except pygame.error as e:
    print(f"FELAKET HATA: Ana Menü varlıkları yüklenemedi: {e}")
    logo_image = None # Çökmeyi önle
# --- ANA MENÜ VARLIKLARI BİTİŞ ---

# Legacy JOKER_ICON removed (old yellow 'J' HUD icon deleted)
# If code elsewhere still references JOKER_ICON, keep the name defined as None
JOKER_ICON = None

# Standard size for joker HUD slots/icons
JOKER_SLOT_SIZE = 60

# Initialize audio (mixer) and load sounds (with safe fallbacks)
try:
    pygame.mixer.init()
except Exception:
    # if mixer init fails, continue without sound
    pass

# Paths for music files used by the startup/video flow
MAIN_MUSIC_PATH = resource_path('assets/gamemusic.mp3')
ENTRANCE_MUSIC_PATH = resource_path('assets/sounds/enterence.mp3')

# Preload the main music if present (we will not start it until videos end)
try:
    pygame.mixer.music.load(MAIN_MUSIC_PATH)
    pygame.mixer.music.set_volume(0.5)
except Exception:
    try:
        # keep going if load fails
        print('Uyarı: Ana müzik yüklenemedi (başlangıçta).')
    except Exception:
        pass
# If starting in video intro state, stop background music immediately
try:
    if game_state == STATE_VIDEO_INTRO:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass
except Exception:
    pass

click_sound = None
buy_sound = None
score_sound = None
boss_sound = None
lose_sound = None
try:
    click_sound = pygame.mixer.Sound(resource_path('assets/sounds/click.wav'))
except Exception:
    click_sound = None
try:
    buy_sound = pygame.mixer.Sound(resource_path('assets/sounds/buy.wav'))
except Exception:
    buy_sound = None
try:
    score_sound = pygame.mixer.Sound(resource_path('assets/sounds/score.wav'))
except Exception:
    score_sound = None
try:
    boss_sound = pygame.mixer.Sound(resource_path('assets/sounds/boss.wav'))
except Exception:
    boss_sound = None
try:
    lose_sound = pygame.mixer.Sound(resource_path('assets/sounds/lose.wav'))
except Exception:
    lose_sound = None

# Fullscreen toggle / resize tracking
is_fullscreen = False

def recompute_ui_layout():
    """Recompute rects that depend on SCREEN_WIDTH/SCREEN_HEIGHT.

    This updates `button_rect`, `discard_button_rect` and `ante_button_rect`.
    Call this after changing SCREEN_WIDTH/SCREEN_HEIGHT or when toggling fullscreen.
    """
    global button_rect, discard_button_rect, ante_button_rect, EXTRA_SLOT_X
    global START_X, NORMAL_Y, HUD_Y
    global PLAY_BTN_IMG, DISCARD_BTN_IMG
    try:
        # Reserve the top HUD_Y area (default 300 or scaled down for small screens)
        if SCREEN_HEIGHT > 360:
            HUD_Y = 300
        else:
            HUD_Y = int(SCREEN_HEIGHT * 0.35)

        # Recompute card dimensions proportional to screen height (keep 2:3 ratio)
        # Card height ~18% of screen height, card width based on 2:3 ratio
        CARD_HEIGHT = int(max(64, SCREEN_HEIGHT * 0.18))
        CARD_WIDTH = int(max(40, CARD_HEIGHT * 2 // 3))
        # Apply global scaling factor so cards can be uniformly enlarged (1.8x by default)
        try:
            scale = float(globals().get('CARD_SCALE', 1.0))
        except Exception:
            scale = 1.0
        CARD_HEIGHT = int(CARD_HEIGHT * scale)
        CARD_WIDTH = int(CARD_WIDTH * scale)
        # update globals
        globals()['CARD_WIDTH'] = CARD_WIDTH
        globals()['CARD_HEIGHT'] = CARD_HEIGHT

        # spacing between cards based on card width
        CARD_SPACING = CARD_WIDTH + int(CARD_WIDTH * 0.12)
        globals()['CARD_SPACING'] = CARD_SPACING

        # Compute card Y so cards appear in the lower-middle (around 450 px on typical 800x600)
        desired_card_y = int(min(480, SCREEN_HEIGHT * 0.78))
        # apply a small configurable offset so the hand can be nudged downwards
        NORMAL_Y = max(HUD_Y + HUD_HEIGHT + 20, desired_card_y) + int(globals().get('CARD_Y_OFFSET', 0))
        globals()['NORMAL_Y'] = NORMAL_Y

        # Keep derived selection/hover constants consistent with the computed NORMAL_Y
        try:
            globals()['SELECTED_Y'] = int(NORMAL_Y - max(12, int(CARD_HEIGHT * 0.12)))
            globals()['NORMAL_Y_POS'] = int(NORMAL_Y)
            globals()['HOVER_Y_POS'] = int(NORMAL_Y - max(6, int(CARD_HEIGHT * 0.06)))
            globals()['SELECTED_Y_POS'] = int(NORMAL_Y - max(18, int(CARD_HEIGHT * 0.18)))
        except Exception:
            # keep legacy constants if something goes wrong
            pass

        # Compute START_X so the whole hand is horizontally centered
        try:
            current_slots = len(hand)
        except Exception:
            current_slots = MAX_HAND_SLOTS
        total_hand_width = int(current_slots * CARD_SPACING)
        START_X = int((SCREEN_WIDTH - total_hand_width) / 2)
        globals()['START_X'] = START_X

        # Extra slot sits right after the current hand area (use actual hand length)
        try:
            current_hand_width = int((len(hand) * globals().get('CARD_SPACING', CARD_SPACING)))
        except Exception:
            try:
                current_hand_width = int((len(hand) * CARD_SPACING))
            except Exception:
                current_hand_width = int(MAX_HAND_SLOTS * CARD_SPACING)
        EXTRA_SLOT_X = START_X + current_hand_width + 40
        globals()['EXTRA_SLOT_X'] = EXTRA_SLOT_X

        # Buttons: place them at percentages but use centerx so they are centered
        if SCREEN_HEIGHT > 700:
            button_y = 550
        else:
            button_y = min(int(SCREEN_HEIGHT * 0.9), SCREEN_HEIGHT - BUTTON_HEIGHT - 20)

        # Place the two primary action buttons in a vertical right-side column
        # so they no longer sit above the cards. This aligns them visually with
        # the HUD panels on the left and keeps them out of the play area.
        try:
            # Determine button diameter from loaded images when possible to avoid distortion
            try:
                if PLAY_BTN_IMG:
                    pw, ph = PLAY_BTN_IMG.get_size()
                    pref = min(pw, ph)
                elif DISCARD_BTN_IMG:
                    dw, dh = DISCARD_BTN_IMG.get_size()
                    pref = min(dw, dh)
                else:
                    pref = BUTTON_HEIGHT
            except Exception:
                pref = BUTTON_HEIGHT

            # Constrain diameter relative to screen so it never becomes huge
            BUTTON_DIAMETER = max(40, min(int(SCREEN_HEIGHT * 0.12), int(pref), 140))
            panel_padding = 12
            panel_margin = 12
            # panel width must fit the circular button plus padding
            panel_w = BUTTON_DIAMETER + (2 * panel_padding)
            panel_x = SCREEN_WIDTH - panel_w - panel_margin

            # center buttons inside the panel horizontally
            btn_x = panel_x + panel_padding
            top_y = HUD_Y + 20

            # ensure discard and primary buttons are square and use BUTTON_DIAMETER
            try:
                discard_button_rect.width = BUTTON_DIAMETER
                discard_button_rect.height = BUTTON_DIAMETER
                button_rect.width = BUTTON_DIAMETER
                button_rect.height = BUTTON_DIAMETER
            except Exception:
                discard_button_rect.w = BUTTON_DIAMETER
                discard_button_rect.h = BUTTON_DIAMETER
                button_rect.w = BUTTON_DIAMETER
                button_rect.h = BUTTON_DIAMETER

            # place 'Kart Değiştir' (discard) on top, 'Eli Oyna' below it with small gap
            discard_button_rect.x = btn_x
            discard_button_rect.y = top_y
            button_rect.x = btn_x
            button_rect.y = top_y + discard_button_rect.height + 10
        except Exception:
            try:
                button_rect.center = (int(SCREEN_WIDTH * 0.6), int(SCREEN_HEIGHT * 0.9))
            except Exception:
                button_rect.centerx = int(SCREEN_WIDTH * 0.6)
                button_rect.y = button_y

        # Ante button near right bottom (keep at 85% X but align by center)
        try:
            ante_button_rect.center = (int(SCREEN_WIDTH * 0.85), int(SCREEN_HEIGHT * 0.9))
        except Exception:
            ante_button_rect.centerx = int(SCREEN_WIDTH * 0.85)
            ante_button_rect.y = button_y

        # After changing CARD sizes, reload and rescale card images and hud icons
        try:
            load_all_card_images()
        except Exception:
            pass

        # Legacy JOKER_ICON rescale removed (no-op)
        try:
            pass
        except Exception:
            pass

        # Update all existing Card instances to use newly scaled images and to
        # recompute their base positions so hitboxes match the new sizes.
        try:
            for idx, c in enumerate(hand):
                if c is None:
                    continue
                # assign updated scaled image if available
                new_img = card_images.get(getattr(c, 'suit', ''), {}).get(getattr(c, 'rank', ''))
                if new_img is not None:
                    c.image = new_img
                # recompute base positions for the slot
                try:
                    c.base_x = START_X + (idx * CARD_SPACING)
                    c.base_y = NORMAL_Y
                    c.target_x = float(c.base_x)
                    # target_y depends on selection state
                    c.target_y = float(SELECTED_Y if getattr(c, 'is_selected', False) else NORMAL_Y)
                except Exception:
                    pass
                # recreate rect from the updated image
                try:
                    c.rect = c.image.get_rect()
                    c.rect.x = int(c.base_x)
                    c.rect.y = int(c.base_y)
                except Exception:
                    pass
        except Exception:
            pass

        # Update extra_card image if present; ensure extra_card.image is never None
        try:
            if extra_card is not None:
                new_img = card_images.get(getattr(extra_card, 'suit', ''), {}).get(getattr(extra_card, 'rank', ''))
                if new_img is not None:
                    extra_card.image = new_img
                else:
                    # fallback to generator which creates a placeholder if missing
                    try:
                        extra_card.image = get_card_image(getattr(extra_card, 'suit', 'spades'), getattr(extra_card, 'rank', 'ace'))
                    except Exception:
                        # last-resort: simple Surface
                        try:
                            surf = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
                            surf.fill((120, 120, 120))
                            extra_card.image = surf
                        except Exception:
                            pass
                try:
                    if getattr(extra_card, 'image', None) is not None:
                        extra_card.rect = extra_card.image.get_rect()
                        extra_card.rect.x = int(getattr(extra_card, 'base_x', globals().get('EXTRA_SLOT_X', 0)))
                        extra_card.rect.y = int(getattr(extra_card, 'base_y', globals().get('NORMAL_Y_POS', 490)))
                except Exception:
                    pass
        except Exception:
            pass

        # NOTE: Layout functions must not modify game entities like Enemy.
        # Enemy sprite/scale/state should be managed by Enemy methods (load_sprite(),
        # set_health(), update(), etc.) and called from game flow code (e.g. start of
        # an ante). We no longer perform any enemy reload/scale here to preserve
        # separation of concerns.
    except Exception:
        pass

def handle_resize_event(ev):
    """Update screen size, rescale background and recompute layout on resize events."""
    global SCREEN_WIDTH, SCREEN_HEIGHT, screen, background_image, background_image_original
    try:
        # Prefer w/h attributes (VIDEORESIZE), fallback to size tuple
        w = getattr(ev, 'w', None)
        h = getattr(ev, 'h', None)
        if w is None or h is None:
            sz = getattr(ev, 'size', None)
            if sz:
                w, h = sz[0], sz[1]
        if w and h:
            SCREEN_WIDTH = int(w)
            SCREEN_HEIGHT = int(h)
            # recreate the display surface in resizable mode (unless fullscreen)
            flags = pygame.FULLSCREEN if is_fullscreen else pygame.RESIZABLE
            try:
                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
            except Exception:
                # fallback: try without flags
                screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
            # rescale background if original available
            try:
                if background_image_original is not None:
                    background_image = pygame.transform.scale(background_image_original, (SCREEN_WIDTH, SCREEN_HEIGHT))
                else:
                    background_image = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
                    background_image.fill(BLACK)
            except Exception:
                try:
                    background_image = pygame.transform.scale(background_image, (SCREEN_WIDTH, SCREEN_HEIGHT))
                except Exception:
                    pass
            # recompute UI positions
            recompute_ui_layout()
    except Exception:
        pass

def toggle_fullscreen():
    """Toggle fullscreen on/off. Bound to F11 key by default."""
    global is_fullscreen, screen, background_image, background_image_original, SCREEN_WIDTH, SCREEN_HEIGHT
    try:
        is_fullscreen = not is_fullscreen
        flags = pygame.FULLSCREEN if is_fullscreen else pygame.RESIZABLE
        try:
            screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        except Exception:
            screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        # rescale background if possible
        try:
            if background_image_original is not None:
                background_image = pygame.transform.scale(background_image_original, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except Exception:
            pass
        recompute_ui_layout()
    except Exception:
        pass

# Load or create unlocks file
UNLOCKS_FILE = 'unlocks.json'
try:
    if not os.path.exists(UNLOCKS_FILE):
        # create default unlocks file
        with open(UNLOCKS_FILE, 'w') as f:
            json.dump({"Mavi Deste": False, "Joker_XYZ": False}, f)
    with open(UNLOCKS_FILE, 'r') as f:
        unlocks = json.load(f)
except Exception:
    unlocks = {"Mavi Deste": False, "Joker_XYZ": False}

HUD_HEIGHT = 80
# Base Y for HUD - will be recomputed by recompute_ui_layout()
HUD_Y = 300

def draw_hud(screen, mode='both'):
    """Draw a semi-transparent HUD bar at top and the joker area on the right."""
    # Only skip HUD for top-level non-gameplay menus. Allow HUD in
    # gameplay-adjacent states such as SHOP so MONEY and other stats
    # remain visible while the player shops or views results.
    try:
        gs = globals().get('game_state')
        # Hide HUD for main menu, settings, credits, and deck selection screens
        if gs in (STATE_MAIN_MENU, STATE_SETTINGS, STATE_CREDITS, STATE_DECK_SELECTION):
            return
    except Exception:
        pass
    # Semi-transparent HUD bar drawn at HUD_Y (reserved top region)
    try:
        top_y = HUD_Y
    except Exception:
        top_y = 300

    # Restrict HUD to only draw in explicit gameplay-related states.
    try:
        gs = globals().get('game_state')
        allowed_states = [STATE_PLAYING, STATE_SHOP]
        if gs not in allowed_states:
            return
    except Exception:
        pass

    # If we're in the shop, draw only the MONEY panel at the top-right.
    try:
        if globals().get('game_state') == STATE_SHOP:
            hud_pad = 12
            panel_h = 52
            panel_w = int(min(240, SCREEN_WIDTH * 0.22))
            # position top-right with a fixed margin so the money panel never overlaps shop/grid
            start_x = int(SCREEN_WIDTH - panel_w - 20)
            start_y = 20

            # fonts
            label_font = game_font_small
            try:
                value_font = pygame.font.Font(None, 26)
            except Exception:
                value_font = pygame.font.SysFont(None, 26)

            # build money panel background & icon (panels-only mode still draws this)
            try:
                panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
                try:
                    pygame.draw.rect(panel, (18, 18, 20, 200), (0, 0, panel_w, panel_h), border_radius=8)
                    pygame.draw.rect(panel, (50, 50, 50, 200), (0, 0, panel_w, panel_h), 1, border_radius=8)
                except Exception:
                    panel.fill((18, 18, 20, 200))
                    pygame.draw.rect(panel, (50, 50, 50, 200), (0, 0, panel_w, panel_h), 1)

                # icon
                try:
                    icon_size = min(28, panel_h - 12)
                    _draw_icon(panel, 'coin', 10, (panel_h - icon_size) // 2, icon_size)
                except Exception:
                    pass

                # blit panel background now (text/value may be drawn later in 'texts' mode)
                screen.blit(panel, (start_x, start_y))

                # draw label/value only in 'texts' or 'both' mode
                if mode in ('both', 'texts'):
                    try:
                        lbl_s = label_font.render('Para', True, (200, 200, 200))
                    except Exception:
                        lbl_s = pygame.font.SysFont(None, 18).render('Para', True, (200,200,200))
                    screen.blit(lbl_s, (start_x + 10 + icon_size + 8, start_y + (panel_h - lbl_s.get_height()) // 2))

                    try:
                        val_s = value_font.render(str(int(MONEY if MONEY is not None else 0)), True, WHITE)
                    except Exception:
                        val_s = pygame.font.SysFont(None, 22).render(str(int(MONEY if MONEY is not None else 0)), True, WHITE)
                    screen.blit(val_s, (start_x + panel_w - val_s.get_width() - 10, start_y + (panel_h - val_s.get_height()) // 2))
            except Exception:
                pass

            # only the money panel for shop (we drew either panels or both)
            return
    except Exception:
        pass

    # Draw a compact stacked panel group at top-left containing key stats
    try:
        hud_pad_x = 12
        hud_pad_y = 12
        panel_w = int(min(240, SCREEN_WIDTH * 0.28))
        panel_h = 52
        gap = 8
        start_x = hud_pad_x
        start_y = top_y + hud_pad_y

        stats = [
            ('Para', int(MONEY if MONEY is not None else 0)),
            ('HEDEF', int(TARGET_SCORE if TARGET_SCORE is not None else 0)),
            ('KALAN EL', int(HANDS_REMAINING if HANDS_REMAINING is not None else 0)),
            ('DEĞİŞTİRME', int(DISCARDS_REMAINING if DISCARDS_REMAINING is not None else 0)),
            ('PUAN', int(displayed_score if displayed_score is not None else 0)),
        ]

        # fonts: label smaller, value larger
        label_font = game_font_small
        try:
            value_font = pygame.font.Font(None, 26)
        except Exception:
            value_font = pygame.font.SysFont(None, 26)

        def _draw_icon(surface, key, x, y, size):
            """Draw a tiny procedural icon on `surface` at x,y with given size.

            Supported keys: 'coin','target','hand','refresh','star'
            """
            try:
                if key == 'coin':
                    # coin: outer gold circle + inner lighter circle
                    pygame.draw.circle(surface, (200, 150, 30), (x + size // 2, y + size // 2), size // 2)
                    pygame.draw.circle(surface, (255, 205, 60), (x + size // 2, y + size // 2), max(2, size // 3))
                elif key == 'target':
                    cx = x + size // 2
                    cy = y + size // 2
                    pygame.draw.circle(surface, (220, 60, 60), (cx, cy), size // 2, 2)
                    pygame.draw.circle(surface, (220, 60, 60), (cx, cy), max(2, size // 4), 2)
                    # small center dot
                    pygame.draw.circle(surface, (220, 60, 60), (cx, cy), max(2, size // 10))
                elif key == 'hand':
                    # draw a small card/hand icon: a rounded rect and a smaller inner rect
                    r = pygame.Rect(x + 2, y + 2, size - 4, size - 4)
                    try:
                        pygame.draw.rect(surface, (240, 240, 240), r, border_radius=4)
                        pygame.draw.rect(surface, (40, 40, 40), (r.x + 4, r.y + 6, max(6, r.width - 10), max(6, r.height - 14)))
                    except Exception:
                        pygame.draw.rect(surface, (240, 240, 240), r)
                elif key == 'refresh':
                    # circular arrow: arc + triangular arrow tip
                    cx = x + size // 2
                    cy = y + size // 2
                    rr = size // 2 - 2
                    try:
                        pygame.draw.arc(surface, (120, 200, 240), (cx - rr, cy - rr, rr * 2, rr * 2), math.radians(30), math.radians(300), 3)
                        # arrowhead triangle at ~-30 degrees
                        ang = math.radians(-30)
                        tip_x = int(cx + rr * math.cos(ang))
                        tip_y = int(cy + rr * math.sin(ang))
                        # small triangle
                        pts = [(tip_x, tip_y), (tip_x - 6, tip_y - 4), (tip_x - 2, tip_y + 6)]
                        pygame.draw.polygon(surface, (120, 200, 240), pts)
                    except Exception:
                        pygame.draw.circle(surface, (120, 200, 240), (cx, cy), max(2, rr), 1)
                elif key == 'star':
                    # simple 5-point star centered in box
                    cx = x + size / 2
                    cy = y + size / 2
                    outer = size // 2
                    inner = max(2, int(outer * 0.45))
                    pts = []
                    for i in range(5):
                        a = math.radians(i * 72 - 90)
                        pts.append((cx + outer * math.cos(a), cy + outer * math.sin(a)))
                        a2 = math.radians(i * 72 + 36 - 90)
                        pts.append((cx + inner * math.cos(a2), cy + inner * math.sin(a2)))
                    pygame.draw.polygon(surface, (255, 215, 50), pts)
            except Exception:
                pass

        icon_map = {
            'Para': 'coin',
            'HEDEF': 'target',
            'KALAN EL': 'hand',
            'DEĞİŞTİRME': 'refresh',
            'PUAN': 'star',
        }

        for i, (label, val) in enumerate(stats):
            y = start_y + i * (panel_h + gap)
            # Draw the panel background and icon regardless of mode; draw text/value only in 'texts' or 'both'
            panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            try:
                pygame.draw.rect(panel, (18, 18, 20, 200), (0, 0, panel_w, panel_h), border_radius=8)
                pygame.draw.rect(panel, (50, 50, 50, 200), (0, 0, panel_w, panel_h), 1, border_radius=8)
            except Exception:
                panel.fill((18, 18, 20, 200))
                pygame.draw.rect(panel, (50, 50, 50, 200), (0, 0, panel_w, panel_h), 1)

            # draw icon on the left side of the panel (prefer PNGs in assets/icons)
            try:
                icon_size = min(28, panel_h - 12)
                icon_x = 10
                icon_y = (panel_h - icon_size) // 2
                ik = icon_map.get(str(label), None)
                icon_img = ICONS.get(ik) if ik else None
                if icon_img:
                    try:
                        scaled = pygame.transform.smoothscale(icon_img, (icon_size, icon_size))
                    except Exception:
                        scaled = pygame.transform.scale(icon_img, (icon_size, icon_size))
                    panel.blit(scaled, (icon_x, icon_y))
                elif ik:
                    _draw_icon(panel, ik, icon_x, icon_y, icon_size)
            except Exception:
                pass

            # blit panel background
            screen.blit(panel, (start_x, y))

            # draw label/value only in text modes
            if mode in ('both', 'texts'):
                try:
                    lbl_s = label_font.render(str(label), True, (200, 200, 200))
                except Exception:
                    lbl_s = pygame.font.SysFont(None, 18).render(str(label), True, (200,200,200))
                try:
                    label_x = start_x + 10 + icon_size + 8
                except Exception:
                    label_x = start_x + 10
                screen.blit(lbl_s, (label_x, y + (panel_h - lbl_s.get_height()) // 2))

                try:
                    val_s = value_font.render(str(val), True, WHITE)
                except Exception:
                    val_s = pygame.font.SysFont(None, 22).render(str(val), True, WHITE)
                screen.blit(val_s, (start_x + panel_w - val_s.get_width() - 10, y + (panel_h - val_s.get_height()) // 2))
    except Exception:
        pass

    # If there's a boss effect active, show its description on the HUD (below the main HUD items)
    try:
        if current_boss_effect:
            desc = BOSS_EFFECT_DESC.get(current_boss_effect, str(current_boss_effect))
            boss_s = game_font_small.render(f"Boss: {desc}", True, (255, 180, 60))
            screen.blit(boss_s, (int(SCREEN_WIDTH * 0.1), int(SCREEN_HEIGHT * 0.1)))
    except Exception:
        pass

    # Legacy small joker icon area removed.

    # If there's a temporary invalid-play message, draw it at the top center
    try:
        if invalid_message and (pygame.time.get_ticks() - invalid_message_time) < INVALID_MESSAGE_DURATION_MS:
            im_s = game_font.render(str(invalid_message), True, (220, 80, 80))
            im_r = im_s.get_rect(center=(SCREEN_WIDTH // 2, HUD_HEIGHT // 2))
            screen.blit(im_s, im_r)
    except Exception:
        pass


def get_card_image(suit: str, rank: str):
    """Return card image Surface for suit/rank, fallback to a simple placeholder if missing."""
    if suit in card_images and rank in card_images[suit]:
        return card_images[suit][rank]
    # fallback placeholder
    placeholder = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
    if suit in ("spades", "clubs"):
        placeholder.fill((40, 40, 40))
    else:
        placeholder.fill((200, 50, 50))
    try:
        font = game_font_small
        txt = font.render(str(rank), True, (255, 255, 255))
        tr = txt.get_rect(center=(CARD_WIDTH//2, CARD_HEIGHT//2))
        placeholder.blit(txt, tr)
    except Exception:
        pass
    return placeholder


def maybe_apply_soul_holo(card_obj):
    """If the selected deck perk is SOUL, apply Holo pity logic to the new card.

    - If `SELECTED_DECK_PERK == 'SOUL'`:
        * If card_obj.is_holo is already True -> reset HOLOPITY_COUNTER to 0
        * Else increment HOLOPITY_COUNTER; if it reaches 10, set card_obj.is_holo = True and reset counter
    - Otherwise ensure card_obj.is_holo exists and is False.
    """
    try:
        perk = globals().get('SELECTED_DECK_PERK')
        if perk == 'SOUL':
            # If card already holographic, reset pity
            if getattr(card_obj, 'is_holo', False):
                globals()['HOLOPITY_COUNTER'] = 0
            else:
                # increment pity counter
                globals()['HOLOPITY_COUNTER'] = int(globals().get('HOLOPITY_COUNTER', 0)) + 1
                try:
                    if globals().get('HOLOPITY_COUNTER', 0) >= 10:
                        try:
                            card_obj.is_holo = True
                        except Exception:
                            setattr(card_obj, 'is_holo', True)
                        globals()['HOLOPITY_COUNTER'] = 0
                except Exception:
                    pass
        else:
            # non-soul decks: ensure flag exists and is False
            if not hasattr(card_obj, 'is_holo'):
                try:
                    card_obj.is_holo = False
                except Exception:
                    setattr(card_obj, 'is_holo', False)
    except Exception:
        pass


# --- El değerlendirme fonksiyonu ---
from typing import List

RANK_VALUE = {
    '02': 2, '03': 3, '04': 4, '05': 5, '06': 6, '07': 7, '08': 8, '09': 9, '10': 10,
    'jack': 11, 'queen': 12, 'king': 13, 'ace': 14,
    # common alternate representations
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'j': 11, 'q': 12, 'k': 13, 'a': 14
}


def get_rank_value(rank_str):
    """Normalize various rank string formats to integer values.

    Accepts forms like '02','2','10','jack','J','queen','Q','king','K','ace','A'.
    Returns integer 2..14 or None when unknown.
    """
    if rank_str is None:
        return None
    r = str(rank_str).strip()
    if not r:
        return None
    # direct case-insensitive lookup in RANK_VALUE
    try:
        v = RANK_VALUE.get(r.lower())
        if v is not None:
            return v
    except Exception:
        pass

    # single-letter forms
    up = r.upper()
    if up == 'A':
        return 14
    if up == 'K':
        return 13
    if up == 'Q':
        return 12
    if up == 'J':
        return 11

    # numeric parse (handles '2','02','10')
    try:
        n = int(r)
        if 2 <= n <= 10:
            return n
    except Exception:
        pass

    # fallback: leading-zero two-char like '02'
    try:
        if r.startswith('0') and len(r) == 2:
            n = int(r[1])
            if 2 <= n <= 9:
                return n
    except Exception:
        pass

    return None

def is_straight_from_values(values: List[int]) -> bool:
    if not values:
        return False
    # Work on a set of unique values to detect straights. Do NOT modify any
    # game state (no side-effects) — this function should be pure.
    vals = sorted(set(values))
    # If there are duplicate ranks, it cannot be a straight
    if len(vals) != len(values):
        return False

    # Simple consecutive check
    try:
        if max(vals) - min(vals) == len(vals) - 1:
            return True
    except Exception:
        pass

    # Handle Ace-low straight (A,2,3,4,5) where Ace is represented as 14
    try:
        if 14 in vals:
            alt = [1 if v == 14 else v for v in vals]
            alt = sorted(set(alt))
            if len(alt) == len(values) and max(alt) - min(alt) == len(alt) - 1:
                return True
    except Exception:
        pass

    return False

def evaluate_hand(cards: List[object], allow_combination: bool = True):
    """Evaluate a list of Card-like objects and return a standardized tuple:

    (KEY_STRING, BASE_CHIPS, BASE_MULTIPLIER)

    KEY_STRING is one of the keys in `POKER_HAND_NAMES` (e.g. 'PAIR', 'FULL_HOUSE').
    This function remains robust for varying card counts; if no valid hand is found
    it returns ('HIGH_CARD', base_chips, base_mult).
    """
    if not cards:
        return ('HIGH_CARD', 5, 1)
    if len(cards) < 2:
        return ('HIGH_CARD', 5, 1)

    # If more than 5 cards are provided and combinations are allowed,
    # evaluate all 5-card subsets and pick the best-scoring one.
    if allow_combination and len(cards) > 5:
        # Hand strength ordering: higher is better
        HAND_ORDER = {
            'ROYAL_FLUSH': 12,
            'STRAIGHT_FLUSH': 11,
            'FIVE_OF_A_KIND': 10,
            'FOUR_OF_A_KIND': 9,
            'FULL_HOUSE': 8,
            'FLUSH_FIVE': 7,
            'FLUSH': 6,
            'STRAIGHT': 5,
            'THREE_OF_A_KIND': 4,
            'TWO_PAIR': 3,
            'PAIR': 2,
            'HIGH_CARD': 1,
        }

        best_score = None
        best_subset = None
        try:
            for combo in combinations(cards, 5):
                # evaluate subset without allowing further combination branching
                res = evaluate_hand(list(combo), allow_combination=False)
                # res is (KEY, chips, mult)
                key = res[0]
                chips = res[1] if len(res) > 1 else 0
                mult = res[2] if len(res) > 2 else 0
                rank = HAND_ORDER.get(key, 0)
                score_tuple = (rank, chips, mult)
                if best_score is None or score_tuple > best_score:
                    best_score = score_tuple
                    best_subset = list(combo)
        except Exception:
            best_subset = None

        if best_subset:
            cards = best_subset

    # --- EN İYİ 5 KART SEÇİMİ (ZORUNLU) ---
    # If more than 5 cards are provided, ensure we evaluate only the best 5.
    # Note: this is a conservative default that simply picks the highest
    # rank cards (by numeric value) when more than 5 are given. For full
    # correctness (e.g. choosing best 5-card combination out of 6 or 7 cards)
    # a combinatorial search (choose 5 of N) is required; leave `pass` here
    # as a reminder to implement a full combination evaluator if needed.
    if len(cards) > 5:
        # Simple fallback: sort by rank value descending and keep top 5.
        try:
            # Use get_rank_value to map ranks, fall back to 0 for unknowns
            sorted_cards = sorted(cards, key=lambda cc: (get_rank_value(getattr(cc, 'rank', None)) or 0), reverse=True)
            cards = sorted_cards[:5]
        except Exception:
            # If any error occurs, just trim to first 5 to avoid crashing.
            cards = cards[:5]

    rank_counts = {}
    suits = []
    values = []
    for c in cards:
        r = c.rank
        s = c.suit
        rank_counts[r] = rank_counts.get(r, 0) + 1
        suits.append(s)
        # Normalize rank strings to numeric values (2..14). Use helper
        # so we accept multiple representations like 'A','ace','02','2', etc.
        rv = get_rank_value(r)
        if rv is not None:
            values.append(rv)
        else:
            try:
                # last-resort numeric parse
                values.append(int(r))
            except Exception:
                # unknown rank representation: skip adding to values
                pass

    counts = sorted(rank_counts.values(), reverse=True)

    # reward table maps standardized key -> (chips, multiplier)
    reward_table = {
        'HIGH_CARD': (5, 1),
        'PAIR': (10, 2),
        'TWO_PAIR': (20, 3),
        'THREE_OF_A_KIND': (30, 4),
        'STRAIGHT': (40, 5),
        'FLUSH': (50, 5),
        'FLUSH_FIVE': (70, 7),
        'FULL_HOUSE': (60, 6),
        'FOUR_OF_A_KIND': (80, 8),
        'STRAIGHT_FLUSH': (120, 10),
        'ROYAL_FLUSH': (200, 12),
        'FIVE_OF_A_KIND': (250, 15),
    }

    # detect five-of-a-kind (requires jokers, but support if rank_counts shows 5)
    if len(cards) >= 5 and 5 in counts:
        return ('FIVE_OF_A_KIND',) + reward_table.get('FIVE_OF_A_KIND', (0, 1))

    # Full House (requires 5 cards: 3 + 2)
    if len(cards) >= 5 and 3 in counts and 2 in counts:
        return ('FULL_HOUSE',) + reward_table.get('FULL_HOUSE')

    # Straight Flush / Royal Flush (require at least 5 cards)
    is_flush = len(set(suits)) == 1
    is_straight = is_straight_from_values(values)
    if len(cards) >= 5 and is_flush and is_straight:
        valset = set(values)
        if {10, 11, 12, 13, 14}.issubset(valset):
            return ('ROYAL_FLUSH',) + reward_table.get('ROYAL_FLUSH')
        return ('STRAIGHT_FLUSH',) + reward_table.get('STRAIGHT_FLUSH')

    # Flush (require at least 5 cards)
    if len(cards) >= 5 and is_flush:
        # Distinguish between a 5-card flush and larger flush
        if len(cards) == 5:
            return ('FLUSH_FIVE',) + reward_table.get('FLUSH_FIVE')
        return ('FLUSH',) + reward_table.get('FLUSH')

    # Straight (require at least 5 cards)
    if len(cards) >= 5 and is_straight:
        return ('STRAIGHT',) + reward_table.get('STRAIGHT')

    # Four of a kind
    if len(cards) >= 4 and 4 in counts:
        return ('FOUR_OF_A_KIND',) + reward_table.get('FOUR_OF_A_KIND')

    # Three of a kind
    if len(cards) >= 3 and 3 in counts:
        return ('THREE_OF_A_KIND',) + reward_table.get('THREE_OF_A_KIND')

    # Two pair
    if len(cards) >= 4 and counts.count(2) >= 2:
        return ('TWO_PAIR',) + reward_table.get('TWO_PAIR')

    # One pair
    if len(cards) >= 2 and 2 in counts:
        return ('PAIR',) + reward_table.get('PAIR')

    return ('HIGH_CARD',) + reward_table.get('HIGH_CARD')
# Helper: calculate money earned at the end of an ante based on score surplus
def calculate_round_money(total_score: int, target_score: int) -> int:
    """Compute the money reward for a completed ante.

    - If `total_score` <= `target_score`, return a small consolation amount.
    - Otherwise, convert the excess score to money via a rate and add a base
      guaranteed reward. Cap the result to avoid excessive payouts.
    """
    try:
        # Prefer configured globals, fall back to sensible literals
        rate = globals().get('SCORE_TO_MONEY_RATE', 10)
        base = globals().get('GUARANTEED_BASE_MONEY', 10)
        consolation = globals().get('CONSOLATION_MONEY', 5)
        cap = globals().get('MAX_ROUND_MONEY', 50)

        if total_score <= target_score:
            return min(consolation, cap)

        excess_score = int(total_score) - int(target_score)
        money_from_excess = max(0, excess_score // int(rate or 10))
        total = money_from_excess + int(base or 10)
        return min(total, int(cap or 50))
    except Exception:
        return 5


# 5 kartımızı tutacak slot listesi (HandContainer)
MAX_HAND_SLOTS = 5
hand = [None] * MAX_HAND_SLOTS
# Oyun başında bir deste oluşturup karıştıralım
deck = Deck()
deck.shuffle()
# Oyuncunun güncel puarı
current_score = 0
# Displayed score for HUD animation (counts up toward current_score)
displayed_score = 0

# Oyun hedefi ve haklar
TARGET_SCORE = 60  # Small Blind / hedef puan (başlangıç 60)
# Initial hands constant (used to detect the first ante)
# Lowered per user request: default starting hands for a run
INITIAL_HANDS = 3
# Default discard limit (can be changed by deck selection)
DEFAULT_DISCARDS = 3
HANDS_REMAINING = INITIAL_HANDS  # Oynanacak el hakkı
DISCARDS_REMAINING = DEFAULT_DISCARDS  # Kart değiştirme hakkı

# Player money for shop purchases (start at 0)
MONEY = 0
try:
    # initial money printed only in dev; removed verbose debug print in final build
    _ = globals().get('MONEY')
except Exception:
    pass

# Buton durumları / animasyon
button_pressed = False
button_pressed_time = 0
BUTTON_PRESS_DURATION_MS = 200

# One-frame lock to prevent multiple shop purchases in the same frame
CLICK_LOCKED = False

# Buton ayarları (ekran alt-orta)
BUTTON_WIDTH = 200
BUTTON_HEIGHT = 50
button_rect = pygame.Rect((SCREEN_WIDTH - BUTTON_WIDTH) // 2,
                          SCREEN_HEIGHT - BUTTON_HEIGHT - 20,
                          BUTTON_WIDTH,
                          BUTTON_HEIGHT)
# Discard (Kart Değiştir) butonu, ana butonun solunda
discard_button_rect = pygame.Rect(button_rect.left - BUTTON_WIDTH - 20,
                                  button_rect.y,
                                  BUTTON_WIDTH,
                                  BUTTON_HEIGHT)
# Shop button rects (used when game_state == 'SHOP')
joker_button_rect = pygame.Rect((SCREEN_WIDTH // 2) - 150, SCREEN_HEIGHT // 2, 140, 50)
# Move Ante button to bottom-right so it doesn't overlap shop items/grid
# Place it above the bottom edge and to the right so the grid (top-left) is unobstructed
ante_button_rect = pygame.Rect(SCREEN_WIDTH - 180, SCREEN_HEIGHT - BUTTON_HEIGHT - 20, 160, BUTTON_HEIGHT)

# Global game state
# Use the integer-based STATE_* constants; start at the video intro so videos play on launch
game_state = STATE_VIDEO_INTRO

# Video intro globals
VIDEO_PATHS = [
    resource_path('assets/videos/enterence_video.mp4'),
    resource_path('assets/videos/enterence_video_py.mp4')
]
current_video_index = 0
video_clip = None
video_start_ticks = 0
splash_screen_end_time = 0
splash_fallback_image = None
# If we're starting in video intro state, play the entrance track (once)
try:
    if game_state == STATE_VIDEO_INTRO:
        try:
            # Ensure any previously loaded music is stopped
            pygame.mixer.music.stop()
        except Exception:
            pass
        try:
            pygame.mixer.music.load(ENTRANCE_MUSIC_PATH)
            # Play entrance music once (no loop)
            pygame.mixer.music.play(0)
        except Exception as e:
            try:
                print(f"HATA: Giriş müziği (enterence.mp3) yüklenemedi: {e}")
            except Exception:
                pass
except Exception:
    pass
# The player's chosen deck for this session. Will be set on the selection screen.
# Possible values: 'Kırmızı Deste', 'Mavi Deste'
SELECTED_DECK = 'Kırmızı Deste'
# Currently selected cards for the preview/selection logic (global scope)
selected_cards = []

# Joker system

# YENİ JOKER HUD SINIFI
class JokerHUD:
    def __init__(self, x=None, y=None, card_width=150, card_height=140):
        # Fix base position to the right side of the screen so jokers
        # never draw over the boss in the center. Use SCREEN_WIDTH/HEIGHT
        # to compute a stable, right-aligned position.
        try:
            self.base_x = SCREEN_WIDTH - 150
        except Exception:
            # fallback if SCREEN_WIDTH isn't available for some reason
            self.base_x = x if x is not None else 50
        try:
            self.base_y = 100
        except Exception:
            self.base_y = y if y is not None else 50
        self.card_width = card_width
        self.card_height = card_height
        self.is_hovered = False
        # 'hover_rect'i dinamik olarak update'te hesaplayacağız
        # initialize hover_rect using the card dimensions
        self.hover_rect = pygame.Rect(self.base_x, self.base_y, self.card_width, max(200, int(self.card_height * 2))) # Başlangıç boyutu
        # hud_rect represents the visible HUD area and is used to position tooltips
        self.hud_rect = pygame.Rect(self.base_x, self.base_y, self.card_width + 20, self.hover_rect.height)
        # index of the joker currently hovered in the HUD (-1 = none)
        self.hovered_index = -1
        try:
            self.font = pygame.font.Font(None, 20) # Açıklama fontu
        except Exception:
            self.font = pygame.font.SysFont(None, 20)
        try:
            self.name_font = pygame.font.Font(None, 22) # İsim fontu
            self.name_font.set_bold(True)
        except Exception:
            self.name_font = pygame.font.SysFont(None, 22)

    def update(self, mouse_pos, active_jokers):
        # Force HUD position every frame to the right-side fixed location so
        # it cannot be moved/placed over the boss by other logic.
        try:
            # Move Joker HUD to bottom-right corner (leave a small margin)
            self.base_x = max(12, SCREEN_WIDTH - self.card_width - 20)
            self.base_y = max(12, SCREEN_HEIGHT - self.card_height - 20)
        except Exception:
            # if SCREEN_WIDTH isn't defined for some reason, keep existing values
            pass
        # Hover alanını, destedeki kart sayısına göre dinamik olarak ayarla
        if not active_jokers:
            self.hover_rect.height = 0
            self.is_hovered = False
            return
            
        # Kapalı deste yüksekliği: aralık kart genişliğinin ~30% si kadar olsun (scale with width)
        stack_increment = max(12, int(self.card_width * 0.3))
        stack_height = self.card_height + (len(active_jokers) - 1) * stack_increment
        # For bottom-up stacking, hover_rect's top is base_y - (stack_height - card_height)
        top_y = int(self.base_y - (stack_height - self.card_height))
        self.hover_rect.height = stack_height
        self.hover_rect.x = self.base_x
        self.hover_rect.y = top_y

        # Update hud_rect to match current hover_rect / base position
        try:
            self.hud_rect.x = self.base_x
            self.hud_rect.y = self.hover_rect.y
            self.hud_rect.width = self.card_width + 20
            self.hud_rect.height = self.hover_rect.height
        except Exception:
            pass

        if self.hover_rect.collidepoint(mouse_pos):
            self.is_hovered = True
            # determine which joker index is under the mouse vertically
            try:
                # use the stack_increment used above to map mouse Y to index
                if len(active_jokers) > 0:
                    # compute index from top of hover_rect, then convert to bottom-up index
                    rel_y = mouse_pos[1] - self.hover_rect.y
                    index_from_top = int(rel_y / max(1, stack_increment))
                    approx_idx = len(active_jokers) - 1 - index_from_top
                    # clamp
                    if approx_idx < 0:
                        approx_idx = 0
                    if approx_idx >= len(active_jokers):
                        approx_idx = len(active_jokers) - 1
                    self.hovered_index = approx_idx
                else:
                    self.hovered_index = -1
            except Exception:
                self.hovered_index = -1
        else:
            self.is_hovered = False
            self.hovered_index = -1

    def draw(self, surface, active_jokers):
        # If no jokers, nothing to draw
        jokers = list(active_jokers) if active_jokers else []
        if not jokers:
            return

        # Cache scaled images per draw call (could be cached longer-term)
        scaled_images = []
        for j in jokers:
            if getattr(j, 'image', None) is not None:
                try:
                    si = pygame.transform.scale(j.image, (self.card_width, self.card_height))
                except Exception:
                    si = pygame.Surface((self.card_width, self.card_height))
            else:
                si = pygame.Surface((self.card_width, self.card_height))
            scaled_images.append(si)

        # Which joker (by index) is currently marked by the kill-banner mechanic?
        try:
            kb_idx = int(globals().get('joker_kill_banner_index', -1))
        except Exception:
            kb_idx = -1
        try:
            disabled_idx = int(globals().get('disabled_joker_index', -1))
        except Exception:
            disabled_idx = -1

        n = len(jokers)
        # Determine available vertical space above the base_y (we stack upward)
        try:
            avail_h = max(80, int(self.base_y - 20))
        except Exception:
            avail_h = max(200, int(self.card_height * 3))

        # screen height from the surface passed in (use surface rather than global)
        try:
            screen_height = surface.get_height()
        except Exception:
            screen_height = SCREEN_HEIGHT

        # compute a base stack increment used in both modes
        # Enforce a minimum vertical separation so jokers never overlap.
        # Minimum is either 30px or 20% of card height, whichever is larger.
        min_spacing = max(30, int(self.card_height * 0.2))
        stack_increment_draw = max(min_spacing, int(self.card_width * 0.3), 50)

        if not self.is_hovered:
            # Stack mode: compute overlap step based on card width but ensure fit on screen
            # required height for current increment
            req_h = self.card_height + (n - 1) * stack_increment_draw
            if req_h > avail_h and n > 1:
                # reduce increment so whole stack fits inside avail_h
                # but do not reduce below the enforced minimum spacing
                stack_increment_draw = max(min_spacing, int((avail_h - self.card_height) / (n - 1)))
            for i, img in enumerate(scaled_images):
                # stack upward: index 0 is bottom card (base_y), subsequent indices go up
                card_y = int(self.base_y - i * stack_increment_draw)
                # clamp y to screen with a 10px buffer
                max_y = screen_height - self.card_height - 10
                if card_y > max_y:
                    card_y = max_y
                if card_y < 0:
                    card_y = 0
                surface.blit(img, (self.base_x, card_y))
                # expose a clickable rect on the Joker instance so shop sell-mode
                # can detect clicks directly on HUD items.
                try:
                    jk = jokers[i]
                    jk.rect = pygame.Rect(self.base_x, card_y, self.card_width, self.card_height)
                except Exception:
                    jk = None

                # If shop is in sell-mode, draw an overlay + sell price label
                try:
                    if globals().get('is_sell_mode'):
                        try:
                            overlay = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
                            overlay.fill((180, 30, 30, 80))
                            surface.blit(overlay, (self.base_x, card_y))
                            pygame.draw.rect(surface, (255, 200, 60), (self.base_x, card_y, self.card_width, self.card_height), 2)
                            if jk is not None:
                                try:
                                    _pp = int(getattr(jk, 'purchase_price', 10))
                                except Exception:
                                    _pp = 10
                                sell_price = int(_pp * 0.5)
                                price_s = self.font.render(f"Sat: {sell_price}$", True, (255,255,255))
                                surface.blit(price_s, (self.base_x + 6, card_y + 6))
                        except Exception:
                            pass
                except Exception:
                    pass
                # If this joker is marked, draw a small persistent red stamp/X
                try:
                    # kill-banner marker
                    if kb_idx == i:
                        marker_size = max(20, int(self.card_width * 0.18))
                        mx = self.base_x + self.card_width - marker_size - 6
                        my = card_y + 6
                        marker_surf = pygame.Surface((marker_size, marker_size), pygame.SRCALPHA)
                        # semi-transparent red circle
                        try:
                            pygame.draw.circle(marker_surf, (200, 40, 40, 180), (marker_size//2, marker_size//2), marker_size//2)
                            # white X over the circle
                            pygame.draw.line(marker_surf, (255,255,255,220), (4,4), (marker_size-4, marker_size-4), max(1, marker_size//8))
                            pygame.draw.line(marker_surf, (255,255,255,220), (marker_size-4,4), (4, marker_size-4), max(1, marker_size//8))
                        except Exception:
                            try:
                                marker_surf.fill((200, 40, 40, 160))
                            except Exception:
                                pass
                        try:
                            surface.blit(marker_surf, (mx, my))
                        except Exception:
                            pass

                    # disabled-by-boss marker (grayout + X)
                    if disabled_idx == i:
                        try:
                            ov = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
                            ov.fill((60, 60, 60, 160))
                            surface.blit(ov, (self.base_x, card_y))
                            # draw X across the card
                            try:
                                line_color = (255, 180, 180, 220)
                                pygame.draw.line(surface, line_color, (self.base_x + 6, card_y + 6), (self.base_x + self.card_width - 6, card_y + self.card_height - 6), 4)
                                pygame.draw.line(surface, line_color, (self.base_x + self.card_width - 6, card_y + 6), (self.base_x + 6, card_y + self.card_height - 6), 4)
                            except Exception:
                                pass
                        except Exception:
                            pass
                except Exception:
                    pass
        else:
            # Hover mode: expanded list. spacing proportional to card_height but ensure fit
            HOVER_CARD_Y_SPACING = max(10, int(self.card_height * 0.1))
            req_h = self.card_height + (n - 1) * HOVER_CARD_Y_SPACING
            if req_h > avail_h and n > 1:
                # reduce spacing so the list fits vertically
                HOVER_CARD_Y_SPACING = max(6, int((avail_h - self.card_height) / (n - 1)))

            for i, joker in enumerate(jokers):
                # base expanded position (stacking upwards)
                base_y_pos = int(self.base_y - i * HOVER_CARD_Y_SPACING)

                # If this is the hovered index, pop it out a bit further
                try:
                    if getattr(self, 'hovered_index', -1) == i:
                        card_y = int(self.base_y - (i * stack_increment_draw) - HOVER_CARD_Y_SPACING)
                    else:
                        card_y = base_y_pos
                except Exception:
                    card_y = base_y_pos

                # clamp so drawing stays on screen
                max_y = screen_height - self.card_height - 10
                if card_y < 0:
                    card_y = 0
                if card_y > max_y:
                    card_y = max_y
                surface.blit(scaled_images[i], (self.base_x, card_y))
                # expose rect for click detection and draw sell overlay if active
                try:
                    joker.rect = pygame.Rect(self.base_x, card_y, self.card_width, self.card_height)
                except Exception:
                    pass
                try:
                    if globals().get('is_sell_mode'):
                        try:
                            ov = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
                            ov.fill((180, 30, 30, 80))
                            surface.blit(ov, (self.base_x, card_y))
                            pygame.draw.rect(surface, (255, 200, 60), (self.base_x, card_y, self.card_width, self.card_height), 2)
                            try:
                                _pp = int(getattr(joker, 'purchase_price', 10))
                            except Exception:
                                _pp = 10
                            sell_price = int(_pp * 0.5)
                            price_s = self.font.render(f"Sat: {sell_price}$", True, (255,255,255))
                            surface.blit(price_s, (self.base_x + 6, card_y + 6))
                        except Exception:
                            pass
                except Exception:
                    pass
                # persistent marker in hover/expanded view as well
                try:
                    if kb_idx == i:
                        marker_size = max(20, int(self.card_width * 0.18))
                        mx = self.base_x + self.card_width - marker_size - 6
                        my = card_y + 6
                        marker_surf = pygame.Surface((marker_size, marker_size), pygame.SRCALPHA)
                        try:
                            pygame.draw.circle(marker_surf, (200, 40, 40, 180), (marker_size//2, marker_size//2), marker_size//2)
                            pygame.draw.line(marker_surf, (255,255,255,220), (4,4), (marker_size-4, marker_size-4), max(1, marker_size//8))
                            pygame.draw.line(marker_surf, (255,255,255,220), (marker_size-4,4), (4, marker_size-4), max(1, marker_size//8))
                        except Exception:
                            try:
                                marker_surf.fill((200, 40, 40, 160))
                            except Exception:
                                pass
                        try:
                            surface.blit(marker_surf, (mx, my))
                        except Exception:
                            pass
                    # disabled-by-boss marker in hover view
                    if disabled_idx == i:
                        try:
                            ov = pygame.Surface((self.card_width, self.card_height), pygame.SRCALPHA)
                            ov.fill((60, 60, 60, 160))
                            surface.blit(ov, (self.base_x, card_y))
                            try:
                                line_color = (255, 180, 180, 220)
                                pygame.draw.line(surface, line_color, (self.base_x + 6, card_y + 6), (self.base_x + self.card_width - 6, card_y + self.card_height - 6), 4)
                                pygame.draw.line(surface, line_color, (self.base_x + self.card_width - 6, card_y + 6), (self.base_x + 6, card_y + self.card_height - 6), 4)
                            except Exception:
                                pass
                        except Exception:
                            pass
                except Exception:
                    pass

                # Tooltip Çözümü: Açıklamayı joker ikonunun soluna güvenli şekilde yaz
                try:
                    name_surf = self.name_font.render(joker.name, True, (255, 255, 0))  # Sarı İsim
                    desc_surf = self.font.render(getattr(joker, 'description', getattr(joker, 'desc', '')), True, (255, 255, 255))  # Beyaz Açıklama

                    # Açıklamaları HUD'ın soluna hizala (Boss'un üzerine değil)
                    # place description to the left of the HUD rect
                    name_rect = name_surf.get_rect(right=self.hud_rect.x - 15, top=card_y + 10)
                    desc_rect = desc_surf.get_rect(right=self.hud_rect.x - 15, top=name_rect.bottom + 5)

                    # Draw a semi-transparent background panel behind the text for readability
                    try:
                        # Compute a background rect that covers both name and description
                        combined = name_rect.union(desc_rect)
                        # If this joker has the kill-banner index, prepare an extra banner line
                        try:
                            kb_idx = int(globals().get('joker_kill_banner_index', -1))
                        except Exception:
                            kb_idx = -1
                        banner_rect = None
                        if kb_idx == i:
                            try:
                                banner_text = "Ruhun Bedeli: Bu Joker Mühürlendi."
                                # use a dark red / orange color to emphasize penalty
                                banner_surf = self.font.render(banner_text, True, (200, 80, 20))
                                # place banner above the name_rect
                                banner_rect = banner_surf.get_rect(right=self.hud_rect.x - 15, bottom=name_rect.top - 6)
                                # include banner in combined area
                                combined = combined.union(banner_rect)
                            except Exception:
                                banner_rect = None
                        pad = 10
                        bg_w = combined.width + pad
                        bg_h = combined.height + pad
                        bg_surface = pygame.Surface((bg_w, bg_h))
                        # semi-transparent
                        bg_surface.set_alpha(150)
                        bg_surface.fill((0, 0, 0))
                        # position the background so its topright is slightly left of the HUD (with a small offset)
                        bg_pos = bg_surface.get_rect(topright=(combined.right + 5, combined.top - 5))
                        surface.blit(bg_surface, bg_pos)
                        # If there is a banner, blit it above the name/desc
                        try:
                            if kb_idx == i and banner_rect is not None:
                                # translate banner_rect relative to bg_pos
                                rel_x = banner_rect.x - bg_pos.x
                                rel_y = banner_rect.y - bg_pos.y
                                surface.blit(banner_surf, (bg_pos.x + rel_x, bg_pos.y + rel_y))
                        except Exception:
                            pass
                    except Exception:
                        pass

                    # Blit text on top of the background
                    surface.blit(name_surf, name_rect)
                    surface.blit(desc_surf, desc_rect)
                except Exception as e:
                    # Hata durumunda sadece logla; oyunun çökmesine izin verme
                    try:
                        print(f"JokerHUD çizerken hata: {e}")
                    except Exception:
                        pass

class Joker:
    def __init__(self, name: str, effect_id: str, desc: str = "", image_path: str = None):
        self.name = name
        self.effect_id = effect_id
        # human readable description for tooltips
        self.desc = desc
        self.description = desc
        # will be assigned a pygame.Rect when HUD is drawn
        self.rect = None
        # attempt to load an image if provided
        self.image = None
        if image_path:
            try:
                self.image = pygame.image.load(resource_path(image_path))
                try:
                    print(f"BAŞARILI: {image_path} yüklendi.")
                except Exception:
                    pass
            except Exception:
                # fallback to relative path then report error if still failing
                try:
                    self.image = pygame.image.load(resource_path(image_path))
                    try:
                        print(f"BAŞARILI: {image_path} yüklendi. (fallback kullanıldı)")
                    except Exception:
                        pass
                except Exception as e2:
                    self.image = None
                    try:
                        print(f"FELAKET HATA: {image_path} yüklenemedi! Hata: {e2}")
                    except Exception:
                        pass

# Active jokers the player has bought
active_jokers = []
# Joker HUD instance (positioned near right edge)
joker_hud = JokerHUD(SCREEN_WIDTH - 120, 50)

# Fate Orb HUD: displays up to 5 fate-orbs centered between the top HUD and player hand.
class FateOrbHUD:
    def __init__(self, y=None, radius=15, spacing=10, max_slots=5):
        try:
            self.radius = int(radius)
            self.spacing = int(spacing)
            self.max_slots = int(max_slots)
        except Exception:
            self.radius = 15
            self.spacing = 10
            self.max_slots = 5
        # slot_rects are computed each draw/update and used for click detection
        self.slot_rects = [pygame.Rect(0, 0, 0, 0) for _ in range(self.max_slots)]
        self.y = y
        try:
            self.font = game_font_small
        except Exception:
            try:
                self.font = pygame.font.SysFont(None, 18)
            except Exception:
                self.font = None

    def _compute_layout(self):
        # compute Y dynamically so HUD adapts to layout changes
        try:
            # Place the fate orbs centered between HUD_Y and the player's hand.
            # Use a stable central position so the HUD remains visible and centered.
            top = int(globals().get('HUD_Y', 300))
            bottom = int(globals().get('NORMAL_Y', 490))
            # default mid-point
            mid = int((top + bottom) / 2)
            # Place slightly above center so they don't overlap boss/hand
            self.y = int(globals().get('FATE_ORB_Y', mid - 0))
            # If not set, use an explicit centered Y roughly halfway on screen
            if self.y is None:
                self.y = SCREEN_HEIGHT // 2 - 20
        except Exception:
            if self.y is None:
                self.y = SCREEN_HEIGHT // 2 - 20
        # compute total width assuming each slot occupies (2*radius + spacing)
        slot_occupancy = (2 * self.radius) + self.spacing
        total_w = self.max_slots * slot_occupancy - self.spacing
        # Center explicitly: match requested centering calculation
        try:
            start_x = (SCREEN_WIDTH // 2) - (total_w // 2)
        except Exception:
            start_x = int((SCREEN_WIDTH - total_w) / 2)
        # populate slot rects
        for i in range(self.max_slots):
            cx = start_x + i * slot_occupancy + self.radius
            cy = self.y
            r = int(self.radius)
            self.slot_rects[i] = pygame.Rect(cx - r, cy - r, r * 2, r * 2)

    def draw(self, surface):
        try:
            # If a boss banner animation is active, avoid drawing so the banner
            # can remain visually on top without HUD overlap.
            if globals().get('boss_banner_active'):
                return
            self._compute_layout()
        except Exception:
            pass

        mouse_pos = pygame.mouse.get_pos()
        try:
            pf = globals().get('player_fate_orbs', [])
        except Exception:
            pf = []

        for i in range(self.max_slots):
            rect = self.slot_rects[i]
            # determine if this slot is filled
            filled = False
            orb = None
            try:
                if i < len(pf) and pf[i] is not None:
                    filled = True
                    orb = pf[i]
            except Exception:
                filled = False

            # Draw empty slot: white circle outline
            try:
                if not filled:
                    pygame.draw.circle(surface, WHITE, rect.center, self.radius, 2)
                else:
                    # filled: draw orb color (fallback to white) and a small white border
                    col = orb.get('color', (255, 255, 255)) if isinstance(orb, dict) else (255, 255, 255)
                    # filled circle
                    pygame.draw.circle(surface, col, rect.center, self.radius)
                    # white border
                    pygame.draw.circle(surface, WHITE, rect.center, self.radius, 2)
            except Exception:
                try:
                    pygame.draw.circle(surface, WHITE, rect.center, self.radius, 2)
                except Exception:
                    pass

            # Tooltip when hovered over a filled orb
            try:
                if filled and rect.collidepoint(mouse_pos):
                    # build tooltip lines
                    name = orb.get('name', '') if isinstance(orb, dict) else str(orb)
                    desc = orb.get('desc', '') if isinstance(orb, dict) else ''

                    # render texts
                    try:
                        name_s = self.font.render(name, True, WHITE)
                    except Exception:
                        try:
                            name_s = pygame.font.SysFont(None, 18).render(name, True, WHITE)
                        except Exception:
                            name_s = None
                    try:
                        desc_s = self.font.render(desc, True, (220, 220, 220))
                    except Exception:
                        try:
                            desc_s = pygame.font.SysFont(None, 16).render(desc, True, (220, 220, 220))
                        except Exception:
                            desc_s = None

                    # compute tooltip rect above the orb
                    tw = max(name_s.get_width() if name_s else 0, desc_s.get_width() if desc_s else 0) + 16
                    th = (name_s.get_height() if name_s else 0) + (desc_s.get_height() if desc_s else 0) + 12
                    tx = rect.centerx - tw // 2
                    ty = rect.top - th - 8
                    # clamp tooltip to screen
                    if tx < 6:
                        tx = 6
                    if tx + tw > SCREEN_WIDTH - 6:
                        tx = SCREEN_WIDTH - tw - 6

                    try:
                        tip_surf = pygame.Surface((tw, th), pygame.SRCALPHA)
                        tip_surf.fill((10, 10, 10, 220))
                        pygame.draw.rect(tip_surf, (180, 180, 180), (0, 0, tw, th), 1, border_radius=6)
                        surface.blit(tip_surf, (tx, ty))
                        # blit texts
                        if name_s:
                            surface.blit(name_s, (tx + 8, ty + 6))
                        if desc_s:
                            surface.blit(desc_s, (tx + 8, ty + 6 + (name_s.get_height() if name_s else 0)))
                    except Exception:
                        # fallback simple box
                        try:
                            pygame.draw.rect(surface, (0, 0, 0), (tx, ty, tw, th))
                        except Exception:
                            pass
            except Exception:
                pass

    def handle_click(self, mouse_pos):
        try:
            pf = globals().get('player_fate_orbs', [])
            afr = globals().get('active_fate_rules', [])
        except Exception:
            pf = []
            afr = []

        for i, rect in enumerate(self.slot_rects):
            try:
                if rect.collidepoint(mouse_pos):
                    # if filled, consume
                    if i < len(pf) and pf[i] is not None:
                        try:
                            orb = pf.pop(i)
                        except Exception:
                            orb = None
                        try:
                            if orb and isinstance(orb, dict) and orb.get('id'):
                                afr.append(orb.get('id'))
                        except Exception:
                            pass
                        # set globals back
                        try:
                            globals()['player_fate_orbs'] = pf
                            globals()['active_fate_rules'] = afr
                        except Exception:
                            pass
                        try:
                            globals()['CLICK_LOCKED'] = True
                        except Exception:
                            pass
                        try:
                            if globals().get('click_sound'):
                                click_sound.play()
                        except Exception:
                            pass
                        try:
                            print('Kader Küresi Aktif Edildi!')
                        except Exception:
                            pass
                        return True
            except Exception:
                pass
        return False

# Instantiate FateOrbHUD so game code can call draw/handle_click easily
fate_orb_hud = FateOrbHUD()
# Backwards-compatible alias expected by some code: `fate_hud`
try:
    fate_hud = fate_orb_hud
except Exception:
    fate_hud = FateOrbHUD()

# Shop state containers (ensure they exist before reset_game() can clear them)
shop_offers = []
shop_offer_rects = []
shop_items_generated = False
current_shop_items = []

# Rects for player-owned jokers (created during shop draw)
player_joker_rects = []
# Toggle used by the shop to enter/exit integrated "sell mode".
# When True, clicking a joker in the Joker HUD sells it for its computed price.
is_sell_mode = False

# Enemy instance (drawn in PLAYING state)
enemy = None

# Currently hovered joker (set by MOUSEMOTION handler)
hovered_joker = None

# Extra special card shown only during the first ante
extra_card = None

# Has the player completed the first successful ante and visited the shop?
# After this becomes True the extra card will no longer be provided.
first_ante_completed = False


# --- MERCY PHASE (SAVAŞ MODU) SINIFLARI ---

class MercySoul:
    """Undertale tarzı savaşta oyuncunun yönettiği kalp/ruh."""
    def __init__(self):
        # Fail-safe initialization: ensure a visible rect even if the image fails
        self.image = None
        self.rect = pygame.Rect(0, 0, 64, 64)  # Default fallback size

        try:
            img_path = resource_path('assets/character.png')
            loaded_img = pygame.image.load(img_path).convert_alpha()
            try:
                self.image = pygame.transform.smoothscale(loaded_img, (64, 64))
            except Exception:
                try:
                    self.image = pygame.transform.scale(loaded_img, (64, 64))
                except Exception:
                    self.image = None

            if self.image is not None:
                self.rect = self.image.get_rect()
        except Exception as e:
            try:
                print(f"UYARI: Karakter görseli yüklenemedi ({e}). Kırmızı kare kullanılacak.")
            except Exception:
                pass
            self.image = None

        # Movement speed and starting position (arena center by default)
        self.speed = 250
        try:
            self.rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
        except Exception:
            # Fallback: place at reasonable coordinates
            try:
                self.rect.x = SCREEN_WIDTH // 2
                self.rect.y = SCREEN_HEIGHT // 2
            except Exception:
                self.rect.x = 100
                self.rect.y = 100

    def update(self, dt: float):
        try:
            keys = pygame.key.get_pressed()
        except Exception:
            keys = []

        dx = 0
        dy = 0
        try:
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                dx = -1
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                dx = 1
            if keys[pygame.K_UP] or keys[pygame.K_w]:
                dy = -1
            if keys[pygame.K_DOWN] or keys[pygame.K_s]:
                dy = 1
        except Exception:
            pass

        try:
            if dx != 0 and dy != 0:
                dx *= 0.7071
                dy *= 0.7071
        except Exception:
            pass

        try:
            move_dt = float(dt) if dt else 0.016
            self.rect.x += int(dx * self.speed * move_dt)
            self.rect.y += int(dy * self.speed * move_dt)
        except Exception:
            pass

        # Clamp inside mercy arena rect if present
        try:
            arena = globals().get('mercy_arena_rect')
            if arena:
                try:
                    self.rect.clamp_ip(arena.inflate(-6, -6))
                except Exception:
                    # manual clamp fallback
                    try:
                        if self.rect.left < arena.left + 6:
                            self.rect.left = arena.left + 6
                        if self.rect.right > arena.right - 6:
                            self.rect.right = arena.right - 6
                        if self.rect.top < arena.top + 6:
                            self.rect.top = arena.top + 6
                        if self.rect.bottom > arena.bottom - 6:
                            self.rect.bottom = arena.bottom - 6
                    except Exception:
                        pass
        except Exception:
            pass

    def draw(self, surface):
        # Draw sprite if available; otherwise draw a visible red square fallback
        try:
            if self.image:
                surface.blit(self.image, self.rect)
            else:
                pygame.draw.rect(surface, (255, 0, 0), self.rect)
        except Exception:
            try:
                pygame.draw.rect(surface, (255, 0, 0), self.rect)
            except Exception:
                pass


class MercyProjectile:
    """Savaş modunda oyuncuya saldıran mermiler."""
    def __init__(self, x, y, vx, vy, ptype='default', size=10):
        # allow varying projectile sizes (e.g. large area bullets)
        self.size = int(size) if size is not None else 10
        try:
            self.rect = pygame.Rect(int(x), int(y), self.size, self.size)
        except Exception:
            self.rect = pygame.Rect(int(x), int(y), 10, 10)
        self.vx = float(vx)
        self.vy = float(vy)
        self.type = ptype
        self.alive = True

    def update(self, dt):
        try:
            self.rect.x += int(self.vx * dt)
            self.rect.y += int(self.vy * dt)
        except Exception:
            pass
        
        # Ekran dışına çıkarsa yok et (Performans)
        try:
            # expand check by size to avoid early disposal for large projectiles
            if not screen.get_rect().colliderect(self.rect.inflate(4, 4)):
                self.alive = False
        except Exception:
            pass
            
    def draw(self, surface):
        # Color and style mapping for different projectile types
        color = (255, 255, 255)  # default white
        try:
            if self.type == 'feed':
                color = (255, 255, 0)
            elif self.type == 'tears':
                color = (0, 100, 255)
            elif self.type == 'fire':
                # red/orange fire
                color = (255, 120, 20)
            elif self.type == 'coin':
                color = (212, 175, 55)
            elif self.type == 'fast':
                color = (220, 50, 200)
            elif self.type == 'spray':
                color = (200, 200, 200)
            elif self.type == 'big':
                color = (200, 60, 60)
            elif self.type == 'mixed':
                # pick a random color from a small palette
                color = random.choice([(255, 120, 20), (212,175,55), (0,100,255), (200,200,200)])
        except Exception:
            pass

        try:
            # coins and rounded things draw as circles for nicer visuals
            if self.type == 'coin':
                r = max(2, self.rect.width // 2)
                pygame.draw.circle(surface, color, self.rect.center, r)
            elif self.type in ('tears', 'fire'):
                # draw as rounded rect / ellipse
                try:
                    pygame.draw.ellipse(surface, color, self.rect)
                except Exception:
                    pygame.draw.rect(surface, color, self.rect)
            else:
                # default rectangular projectile (size-aware)
                pygame.draw.rect(surface, color, self.rect)
        except Exception:
            try:
                pygame.draw.rect(surface, color, self.rect)
            except Exception:
                pass


def update_mercy_logic(dt):
    """Boss'a göre mermi deseni (pattern) oluşturur."""
    try:
        global mercy_projectiles, current_boss_key, mercy_spawn_timer
        if 'mercy_projectiles' not in globals():
            globals()['mercy_projectiles'] = []
        if 'mercy_spawn_timer' not in globals():
            globals()['mercy_spawn_timer'] = 0.0
        globals()['mercy_spawn_timer'] += float(dt)
        # spawn delay
        spawn_delay = 0.2
        ck = globals().get('current_boss_key')
        if ck in ('boss1', 'Gallus'):
            spawn_delay = 0.15
        if globals()['mercy_spawn_timer'] >= spawn_delay:
            globals()['mercy_spawn_timer'] = 0.0
            arena = globals().get('mercy_arena_rect', pygame.Rect((SCREEN_WIDTH//2)-150, (SCREEN_HEIGHT//2)-150, 300, 300))
            if ck in ('boss1', 'Gallus'):
                x = random.randint(arena.left, max(arena.left+1, arena.right - 10))
                p = MercyProjectile(x, arena.top, 0, 200, 'feed')
                globals()['mercy_projectiles'].append(p)
            elif ck in ('mainboss1', 'Azazel'):
                # Azazel: rain of fireballs from top and sides
                # top fireballs
                for _ in range(random.randint(2, 4)):
                    sx = random.randint(arena.left, arena.right)
                    svx = random.uniform(-60, 60)
                    svy = random.uniform(220, 360)
                    p = MercyProjectile(sx, arena.top, svx, svy, 'fire', size=12)
                    globals()['mercy_projectiles'].append(p)
                # side fireballs aimed inward
                if random.random() < 0.5:
                    side = random.choice(['left','right'])
                    sy = random.randint(arena.top, arena.bottom)
                    svx = 200 if side == 'left' else -200
                    svy = random.uniform(-40, 40)
                    sx = arena.left if side == 'left' else arena.right
                    p = MercyProjectile(sx, sy, svx, svy, 'fire', size=14)
                    globals()['mercy_projectiles'].append(p)
            elif ck in ('smug',):
                # Smug: fling golden coins downwards with slight drift
                for _ in range(random.randint(1, 3)):
                    sx = random.randint(arena.left, arena.right)
                    svx = random.uniform(-80, 80)
                    svy = random.uniform(140, 240)
                    p = MercyProjectile(sx, arena.top, svx, svy, 'coin', size=12)
                    globals()['mercy_projectiles'].append(p)
            elif ck in ('shi-shu',):
                # Shi-shu: aim blue tears toward the player
                player = globals().get('mercy_player')
                if player is not None:
                    px, py = player.rect.centerx, player.rect.centery
                    # spawn 1-3 tears from top aiming at player
                    for _ in range(random.randint(1, 3)):
                        sx = random.randint(arena.left, arena.right)
                        sy = arena.top
                        dx = px - sx
                        dy = py - sy
                        dist = math.hypot(dx, dy) or 1.0
                        speed = random.uniform(220, 320)
                        vx = dx / dist * speed
                        vy = dy / dist * speed
                        p = MercyProjectile(sx, sy, vx, vy, 'tears', size=10)
                        globals()['mercy_projectiles'].append(p)
                else:
                    # fallback: simple tears from top
                    sx = random.randint(arena.left, arena.right)
                    p = MercyProjectile(sx, arena.top, 0, 180, 'tears')
                    globals()['mercy_projectiles'].append(p)
            elif ck in ('mainboss2', 'Al'):
                # Al: fast, targeted bullets from edges toward player
                player = globals().get('mercy_player')
                side = random.choice(['top','bottom','left','right'])
                if side == 'top':
                    sx = random.randint(arena.left, arena.right)
                    sy = arena.top
                elif side == 'bottom':
                    sx = random.randint(arena.left, arena.right)
                    sy = arena.bottom
                elif side == 'left':
                    sx = arena.left
                    sy = random.randint(arena.top, arena.bottom)
                else:
                    sx = arena.right
                    sy = random.randint(arena.top, arena.bottom)
                if player is not None:
                    dx = player.rect.centerx - sx
                    dy = player.rect.centery - sy
                    dist = math.hypot(dx, dy) or 1.0
                    speed = random.uniform(300, 460)
                    vx = dx / dist * speed
                    vy = dy / dist * speed
                else:
                    # aim roughly toward center
                    cx, cy = arena.centerx, arena.centery
                    dx = cx - sx
                    dy = cy - sy
                    dist = math.hypot(dx, dy) or 1.0
                    speed = 360.0
                    vx = dx / dist * speed
                    vy = dy / dist * speed
                p = MercyProjectile(sx, sy, vx, vy, 'fast', size=8)
                globals()['mercy_projectiles'].append(p)
            elif ck in ('pimp',):
                # Pimp: many small random bullets
                for _ in range(random.randint(5, 10)):
                    sx = random.randint(arena.left, arena.right)
                    sy = random.randint(arena.top, arena.bottom)
                    ang = random.uniform(0, math.tau if hasattr(math, 'tau') else 2*math.pi)
                    speed = random.uniform(120, 260)
                    vx = math.cos(ang) * speed
                    vy = math.sin(ang) * speed
                    p = MercyProjectile(sx, sy, vx, vy, 'spray', size=6)
                    globals()['mercy_projectiles'].append(p)
            elif ck in ('coby',):
                # Coby: slow but large area-covering projectiles
                for _ in range(random.randint(1, 3)):
                    sx = random.randint(arena.left, arena.right)
                    sy = random.randint(arena.top, arena.bottom)
                    ang = random.uniform(-0.5, 0.5)
                    vx = math.cos(ang) * random.uniform(-40, 40)
                    vy = math.sin(ang) * random.uniform(40, 100)
                    p = MercyProjectile(sx, sy, vx, vy, 'big', size=28)
                    globals()['mercy_projectiles'].append(p)
            elif ck in ('mainboss3',):
                # mainboss3: mixed attacks from various patterns
                choice = random.choice(['fire','coin','tears','fast','spray'])
                if choice == 'fire':
                    sx = random.randint(arena.left, arena.right)
                    p = MercyProjectile(sx, arena.top, random.uniform(-50,50), random.uniform(200,320), 'fire', size=12)
                    globals()['mercy_projectiles'].append(p)
                elif choice == 'coin':
                    sx = random.randint(arena.left, arena.right)
                    p = MercyProjectile(sx, arena.top, random.uniform(-60,60), random.uniform(140,220), 'coin', size=12)
                    globals()['mercy_projectiles'].append(p)
                elif choice == 'tears':
                    player = globals().get('mercy_player')
                    if player is not None:
                        px, py = player.rect.centerx, player.rect.centery
                        sx = random.randint(arena.left, arena.right)
                        dx = px - sx
                        dy = py - arena.top
                        dist = math.hypot(dx, dy) or 1.0
                        speed = random.uniform(220, 320)
                        vx = dx / dist * speed
                        vy = dy / dist * speed
                        p = MercyProjectile(sx, arena.top, vx, vy, 'tears', size=10)
                        globals()['mercy_projectiles'].append(p)
                elif choice == 'fast':
                    sx = random.choice([arena.left, arena.right])
                    sy = random.randint(arena.top, arena.bottom)
                    vx = -250 if sx == arena.right else 250
                    vy = random.uniform(-40,40)
                    p = MercyProjectile(sx, sy, vx, vy, 'fast', size=8)
                    globals()['mercy_projectiles'].append(p)
                else:
                    # spray
                    for _ in range(random.randint(3,6)):
                        sx = random.randint(arena.left, arena.right)
                        sy = random.randint(arena.top, arena.bottom)
                        ang = random.uniform(0, 2*math.pi)
                        sp = random.uniform(120, 260)
                        p = MercyProjectile(sx, sy, math.cos(ang)*sp, math.sin(ang)*sp, 'spray', size=6)
                        globals()['mercy_projectiles'].append(p)
            elif ck in ('boss2', 'Oculus'):
                # simple radial shot from random edge towards center
                side = random.choice(['top','bottom','left','right'])
                cx = arena.centerx
                cy = arena.centery
                if side == 'top':
                    sx = random.randint(arena.left, arena.right)
                    sy = arena.top
                elif side == 'bottom':
                    sx = random.randint(arena.left, arena.right)
                    sy = arena.bottom
                elif side == 'left':
                    sx = arena.left
                    sy = random.randint(arena.top, arena.bottom)
                else:
                    sx = arena.right
                    sy = random.randint(arena.top, arena.bottom)
                # velocity toward center
                dx = cx - sx
                dy = cy - sy
                dist = math.hypot(dx, dy) or 1.0
                speed = 160.0
                vx = dx / dist * speed
                vy = dy / dist * speed
                p = MercyProjectile(sx, sy, vx, vy, 'tears')
                globals()['mercy_projectiles'].append(p)
            else:
                x = random.randint(arena.left, arena.right)
                p = MercyProjectile(x, arena.top, 0, 150, 'default')
                globals()['mercy_projectiles'].append(p)
    except Exception:
        pass


# Visual feedback timer for mercy hits (ms)
mercy_hit_flash_time = 0


class Enemy:
    """Simple enemy with health and a drawable sprite."""
    def __init__(self):
        # Default health should reflect the current TARGET_SCORE when possible
        try:
            self.set_health(TARGET_SCORE)
        except Exception:
            # fallback to a sensible default if TARGET_SCORE not available yet
            try:
                # use set_health to keep assignments consistent
                self.set_health(100)
            except Exception:
                self.health = 100
                self.max_health = 100
        self.current_sprite = None
        self.state = 'idle'
        self.hit_timer = 0
        # dissolve alpha for DYING state (None until used)
        self.dissolve_alpha = None
        # attempt to load a sensible default sprite on init
        try:
            # If ante_level is set and we're in a normal (non-boss) section,
            # default to the plain boss1 image located at assets/bosses/boss1.png
            if 'ante_level' in globals() and (ante_level % 3) != 0:
                try:
                    # prefer boss images inside the `assets/bosses/` folder
                    self.load_sprite('assets/bosses/boss1.png')
                except Exception:
                    # fallback to generic load
                    self.load_sprite()
            else:
                # Use default loader (may be overridden later for boss encounters)
                self.load_sprite()
        except Exception:
            pass
    def load_sprite(self, target_path=None):
        import os
        # Prefer loading the exact path provided by the caller. Only if that
        # fails do we fall back to searching `assets/bosses/{name}.png` and
        # related case variants.
        base_name = 'boss1'
        found_image = None
        loaded_path = ""

        try:
            if target_path:
                # If caller provided a path (absolute or relative), try it first
                try:
                    full_try = resource_path(target_path)
                except Exception:
                    full_try = target_path

                try:
                    if os.path.exists(full_try):
                        try:
                            found_image = pygame.image.load(full_try).convert_alpha()
                            loaded_path = full_try
                        except Exception:
                            found_image = None
                    else:
                        # If target_path looks like a filename (no dir), record base
                        if not os.path.dirname(target_path):
                            base_name = os.path.splitext(os.path.basename(target_path))[0]
                        else:
                            base_name = os.path.splitext(os.path.basename(target_path))[0]
                except Exception:
                    # ignore and fall back to candidate search
                    base_name = os.path.splitext(os.path.basename(target_path))[0]
            else:
                # No explicit path: default to boss1 (we will search assets)
                base_name = 'boss1'
        except Exception:
            base_name = 'boss1'

        try:
            print(f"DEBUG: Boss '{base_name}' yüklenmeye çalışılıyor...")
        except Exception:
            pass

        # If direct load failed, try canonical candidate locations (case variants)
        if not found_image:
            candidates = [
                f"assets/bosses/{base_name}.png",
                f"assets/bosses/{base_name.lower()}.png",
                f"assets/bosses/{base_name.upper()}.png",
                f"assets/bosses/{base_name.capitalize()}.png",
                f"assets/{base_name}.png"
            ]

            for rel_path in candidates:
                try:
                    full_path = resource_path(rel_path)
                except Exception:
                    full_path = rel_path
                try:
                    if os.path.exists(full_path):
                        try:
                            found_image = pygame.image.load(full_path).convert_alpha()
                            loaded_path = full_path
                            try:
                                print(f"BAŞARILI: Görsel bulundu: {rel_path}")
                            except Exception:
                                pass
                            break
                        except Exception:
                            continue
                except Exception:
                    continue

        # 3. Apply image (scale to target height) or create magenta fallback
        if found_image:
            try:
                target_h = int(SCREEN_HEIGHT * 0.25)
                aspect = found_image.get_width() / found_image.get_height()
                target_w = int(target_h * aspect)
                self.current_sprite = pygame.transform.smoothscale(found_image, (target_w, target_h))
            except Exception:
                self.current_sprite = found_image

            # Look for a harmed variant next to the loaded path
            try:
                harmed_candidate = None
                if loaded_path and str(loaded_path).lower().endswith('.png'):
                    harmed_candidate = str(loaded_path).replace('.png', 'harmed.png')
                else:
                    harmed_candidate = resource_path(f"assets/bosses/{base_name}harmed.png")
                try:
                    if harmed_candidate and os.path.exists(harmed_candidate):
                        self.harmed_sprite = pygame.image.load(harmed_candidate).convert_alpha()
                    else:
                        self.harmed_sprite = None
                except Exception:
                    self.harmed_sprite = None
            except Exception:
                self.harmed_sprite = None

        else:
            try:
                print(f"KRİTİK HATA: '{base_name}' için hiçbir görsel bulunamadı! Pembe kutu oluşturuluyor.")
            except Exception:
                pass
            surf = pygame.Surface((200, 200))
            try:
                surf.fill((255, 0, 255))
            except Exception:
                pass
            try:
                font = pygame.font.SysFont(None, 30)
                text = font.render(base_name, True, (255, 255, 255))
                surf.blit(text, (10, 90))
            except Exception:
                pass
            self.current_sprite = surf
            self.harmed_sprite = None

    def set_health(self, amount):
        """Set both current and max health to `amount` (int).

        Use this instead of assigning .health/.max_health directly so we
        can enforce game rules (e.g., boss health == TARGET_SCORE).
        """
        try:
            a = int(amount)
        except Exception:
            a = 100
        try:
            self.max_health = a
            self.health = a
        except Exception:
            self.max_health = a
            self.health = a

    def draw(self, screen):
        # Canlı değilse çizme
        if not (getattr(self, 'health', 0) > 0 or getattr(self, 'state', None) == 'DYING'):
            return
        
        # Görsel yoksa yüklemeyi dene
        if self.current_sprite is None:
            try:
                self.load_sprite()
            except Exception:
                pass

        # 1. Görseli Seç (Normal veya Harmed)
        draw_img = self.current_sprite
        try:
            # Global değişkenleri güvenli çek
            is_harmed = globals().get('is_boss_harmed', False)
            harm_end = globals().get('boss_harm_end_time', 0)
            
            if is_harmed and pygame.time.get_ticks() < harm_end:
                if getattr(self, 'harmed_sprite', None) is not None:
                    draw_img = self.harmed_sprite
        except Exception:
            pass

        if draw_img is None:
            return

        # 2. Sabit Boyutlandırma (Ekranı kaplamayı önle)
        # Görseli her zaman ekran yüksekliğinin %25'ine sığdır
        try:
            screen_h = screen.get_height()
            screen_w = screen.get_width()
            target_h = int(screen_h * 0.25) # Örn: 180px
            
            orig_w = draw_img.get_width()
            orig_h = draw_img.get_height()
            aspect = orig_w / max(1, orig_h)
            
            target_w = int(target_h * aspect)
            
            # Görseli yeniden boyutlandır
            final_img = pygame.transform.smoothscale(draw_img, (target_w, target_h))
        except Exception:
            # Hata olursa orijinali kullan
            final_img = draw_img

        # 3. Konumlandırma
        try:
            # Ekranın tam ortasının biraz üstü
            cx = screen_w // 2
            cy = int(screen_h * 0.22) 
            rect = final_img.get_rect(center=(cx, cy))
            self.rect = rect # Hitbox'ı güncelle
        except Exception:
            return

        # 4. (Debug box removed) — draw only the boss image and UI elements
        
        # 5. Görseli Çiz
        try:
            screen.blit(final_img, rect)
        except Exception:
            try:
                screen.blit(draw_img, rect)
            except Exception:
                pass

        # --- 6. İSİM ETİKETİ (NAMETAG) ---
        try:
            # Global ismi al
            boss_name = globals().get('current_boss_display_name', '')
            
            if boss_name:
                # Fontu ayarla
                font = globals().get('game_font_medium') or pygame.font.SysFont(None, 36)
                
                # Metni oluştur (Beyaz)
                text_surf = font.render(boss_name, True, (255, 255, 255))
                
                # Konumu ayarla: Görselin (rect) tam ortasında ve 40px yukarısında
                # (self.rect, yukarıdaki çizim kodunda güncellenmiş olmalı)
                if hasattr(self, 'rect'):
                    text_rect = text_surf.get_rect(center=(self.rect.centerx, self.rect.top - 40))
                    
                    # Hafif gölge (okunabilirlik için)
                    shadow_surf = font.render(boss_name, True, (0, 0, 0))
                    screen.blit(shadow_surf, (text_rect.x + 2, text_rect.y + 2))
                    
                    # Metni çiz
                    screen.blit(text_surf, text_rect)
        except Exception:
            pass

        # Draw ability description frame to the right of the boss image
        try:
            ab_desc = globals().get('current_boss_ability_desc')
            if ab_desc:
                # compute box position: just to the right of the sprite, aligned vertically
                padding = 12
                box_x = rect.right + 12
                # limit width to about 25-30% of screen width but ensure it fits
                max_box_w = int(min(screen_w * 0.32, screen_w - box_x - 24))
                if max_box_w < 120:
                    max_box_w = 120
                # wrap text to estimate height
                lines = wrap_text(str(ab_desc), game_font_small, max_box_w - (padding * 2))
                line_h = game_font_small.get_height()
                box_h = max(48, (len(lines) * (line_h + 4)) + (padding * 2))
                box_y = rect.centery - (box_h // 2)

                # create semi-transparent rounded panel surface
                panel = pygame.Surface((max_box_w, box_h), pygame.SRCALPHA)
                # fill with semi-transparent dark color
                panel.fill((0,0,0,0))
                try:
                    pygame.draw.rect(panel, (18,18,20,200), (0,0,max_box_w,box_h), border_radius=8)
                    # subtle border
                    pygame.draw.rect(panel, (50,50,50,200), (0,0,max_box_w,box_h), 1, border_radius=8)
                except Exception:
                    # fallback if rounded rect not supported
                    panel.fill((18,18,20,200))
                    pygame.draw.rect(panel, (50,50,50,200), (0,0,max_box_w,box_h), 1)

                # render text lines in white inside panel
                ty = padding
                for ln in lines:
                    try:
                        s = game_font_small.render(ln, True, WHITE)
                        panel.blit(s, (padding, ty))
                        ty += s.get_height() + 4
                    except Exception:
                        pass

                # blit panel onto main surface
                screen.blit(panel, (box_x, box_y))
        except Exception:
            pass

        # Draw health bar below the sprite if max_health is present.
        try:
            mh = getattr(self, 'max_health', None)
            show_bar = False
            try:
                if mh is not None and (getattr(self, 'health', 0) > 0 or getattr(self, 'state', None) == 'DYING'):
                    show_bar = True
            except Exception:
                show_bar = False
            if show_bar:
                hw = rect.width
                hb_w = int(hw * 0.9)
                hb_h = 10
                hb_x = rect.centerx - hb_w // 2
                hb_y = rect.bottom + 8
                # determine alpha (255 normal, or dissolve_alpha when dying)
                alpha = None
                try:
                    if getattr(self, 'state', None) == 'DYING' and getattr(self, 'dissolve_alpha', None) is not None:
                        alpha = int(self.dissolve_alpha)
                except Exception:
                    alpha = None
                if alpha is None:
                    alpha = 255

                # render health bar onto a temporary surface so we can apply alpha
                try:
                    hb_surf = pygame.Surface((hb_w, hb_h), pygame.SRCALPHA)
                    # background (darker)
                    hb_surf.fill((60, 60, 60, int(200 * (alpha/255))))
                    # health proportion
                    cur = max(0, getattr(self, 'health', 0))
                    prop = min(1.0, float(cur) / float(max(1, mh)))
                    fg_w = int(hb_w * prop)
                    # full bar (red background)
                    pygame.draw.rect(hb_surf, (180, 40, 40, alpha), (0, 0, hb_w, hb_h))
                    # green foreground portion
                    pygame.draw.rect(hb_surf, (60, 200, 80, alpha), (0, 0, fg_w, hb_h))
                    # border (white) - draw onto surface and then blit
                    try:
                        pygame.draw.rect(hb_surf, (255,255,255, alpha), (0, 0, hb_w, hb_h), 1)
                    except Exception:
                        pass
                    screen.blit(hb_surf, (hb_x, hb_y))
                    # health text (apply alpha by modulating color with alpha)
                    try:
                        htxt = game_font_small.render(f"{int(cur)}/{int(mh)}", True, WHITE)
                        # draw text with slight transparency by creating a copy
                        if alpha < 255:
                            txt_s = pygame.Surface((htxt.get_width(), htxt.get_height()), pygame.SRCALPHA)
                            txt_s.blit(htxt, (0,0))
                            txt_s.set_alpha(alpha)
                            screen.blit(txt_s, (rect.centerx - htxt.get_width()//2, hb_y - htxt.get_height() - 2))
                        else:
                            screen.blit(htxt, (rect.centerx - htxt.get_width()//2, hb_y - htxt.get_height() - 2))
                    except Exception:
                        pass
                except Exception:
                    # fallback to non-alpha drawing
                    try:
                        pygame.draw.rect(screen, (60, 60, 60), (hb_x, hb_y, hb_w, hb_h))
                        cur = max(0, getattr(self, 'health', 0))
                        prop = min(1.0, float(cur) / float(max(1, mh)))
                        fg_w = int(hb_w * prop)
                        pygame.draw.rect(screen, (180, 40, 40), (hb_x, hb_y, hb_w, hb_h))
                        pygame.draw.rect(screen, (60, 200, 80), (hb_x, hb_y, fg_w, hb_h))
                    except Exception:
                        pass
        except Exception:
            pass

    def take_damage(self, amount):
        """Apply damage to the enemy and trigger hit animation state."""
        try:
            self.health -= int(amount)
        except Exception:
            try:
                self.health -= amount
            except Exception:
                pass
        try:
            # Trigger hit flash
            # enter 'hit' state and set a short timer (frames) during which we show a red tint
            self.state = 'hit'
            self.hit_timer = 15
            # Mark boss as harmed visually for a short duration (1.5s)
            try:
                global is_boss_harmed, boss_harm_end_time
                is_boss_harmed = True
                boss_harm_end_time = pygame.time.get_ticks() + 750
            except Exception:
                pass
            # If health dropped to zero or below, begin dying (dissolve) sequence
            if getattr(self, 'health', 1) <= 0:
                self.state = 'DYING'
                # reset dissolve alpha so update() will initialize it
                self.dissolve_alpha = None
                # stop any hit timer
                self.hit_timer = 0
                # try to play a death sound if provided
                try:
                    # play a small click/hit sound if available (don't assume a specific sound var)
                    if 'click_sound' in globals() and click_sound:
                        play_sound(click_sound)
                except Exception:
                    pass
                # Redirect flow to a boss-defeated narrative state so the game can present
                # an Undertale-like conversation sequence.
                try:
                    global game_state, current_boss_story, consecutive_kills, current_boss_key
                    # consecutive_kills will be handled by the gambit choice (do not increment here)
                    # Assign a temporary story text based on current_boss_key (fallback generic)
                    try:
                        # Do NOT set or overwrite `current_boss_story` here.
                        # Story content should come exclusively from `load_boss_for_ante`
                        # which sources `BOSS_METADATA` in `globals.py`.
                        pass
                    except Exception:
                        pass

                    # Award ante completion money immediately (before gambit decision)
                    try:
                        mg = calculate_round_money(int(globals().get('current_score', 0)), int(globals().get('TARGET_SCORE', 0)))
                    except Exception:
                        try:
                            mg = calculate_round_money(current_score, TARGET_SCORE)
                        except Exception:
                            mg = 0
                    try:
                        MONEY += int(mg)
                    except Exception:
                        try:
                            globals()['MONEY'] = int(globals().get('MONEY', 0)) + int(mg)
                        except Exception:
                            pass
                    try:
                        _ = globals().get('MONEY')
                    except Exception:
                        pass
                    try:
                        print(f"Boss defeated: Para ödülü verildi: {mg} -> Para={globals().get('MONEY')}")
                    except Exception:
                        pass

                    # Ensure there's a boss story loaded (load_boss_for_ante should have done this,
                    # but guard against missing metadata so the narrative screen has text).
                    try:
                        cur_story = globals().get('current_boss_story', '')
                        if not cur_story:
                            try:
                                md = globals().get('BOSS_METADATA', {}) or {}
                                ck = globals().get('current_boss_key') or None
                                entry = md.get(ck) if ck else None
                                if entry:
                                    cur_story = entry.get('story', "Bu boss için hikaye metni tanımlanmamış.")
                                else:
                                    cur_story = "Bu boss için hikaye metni tanımlanmamış."
                                globals()['current_boss_story'] = cur_story
                            except Exception:
                                try:
                                    globals()['current_boss_story'] = "Bu boss için hikaye metni tanımlanmamış."
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    # move game into the first boss-defeated narrative state
                    try:
                        # If we're in endless-mode (ante >= 10), skip the narrative
                        # and immediately advance to the next ante/shop so gameplay
                        # continues without forcing the story path.
                        try:
                            cur_ante = int(globals().get('ante_level', 1))
                        except Exception:
                            try:
                                cur_ante = int(ante_level)
                            except Exception:
                                cur_ante = 1

                        # Determine ante robustly
                        try:
                            cur_ante = int(globals().get('ante_level', cur_ante))
                        except Exception:
                            try:
                                cur_ante = int(cur_ante)
                            except Exception:
                                cur_ante = 1

                        # Endless mode: advance ante and go directly to shop flow
                        if cur_ante >= 10:
                            try:
                                next_ante = int(cur_ante) + 1
                                globals()['ante_level'] = next_ante
                            except Exception:
                                try:
                                    ante_level = int(cur_ante) + 1
                                except Exception:
                                    pass
                            try:
                                load_boss_for_ante(globals().get('ante_level', next_ante))
                            except Exception:
                                try:
                                    load_boss_for_ante(next_ante)
                                except Exception:
                                    pass
                            try:
                                reset_hand_state()
                            except Exception:
                                pass
                            try:
                                globals()['game_state'] = STATE_SHOP
                            except Exception:
                                try:
                                    game_state = STATE_SHOP
                                except Exception:
                                    pass
                        else:
                            # NORMAL MODE: Always go to the boss-defeated narrative state.
                            # Force the transition regardless of boss naming or other flags.
                            try:
                                globals()['game_state'] = STATE_BOSS_DEFEATED_A
                            except Exception:
                                try:
                                    game_state = STATE_BOSS_DEFEATED_A
                                except Exception:
                                    pass
                    except Exception:
                        pass
                except Exception:
                    pass
        except Exception:
            pass

    def update(self):
        """Per-frame update: manage hit timer and dying/dissolve progression."""
        try:
            # handle hit timer: simple flash duration
            if getattr(self, 'state', None) == 'hit':
                try:
                    if getattr(self, 'hit_timer', 0) > 0:
                        self.hit_timer -= 1
                    if getattr(self, 'hit_timer', 0) <= 0:
                        self.state = 'idle'
                        self.hit_timer = 0
                except Exception:
                    pass

            # handle dying dissolve: gradually reduce sprite alpha until gone
            if getattr(self, 'state', None) == 'DYING':
                try:
                    # initialize dissolve_alpha from current sprite alpha (or 255)
                    if self.dissolve_alpha is None:
                        try:
                            a = self.current_sprite.get_alpha()
                            if a is None:
                                a = 255
                        except Exception:
                            a = 255
                        self.dissolve_alpha = int(a)
                    # decrement alpha
                    self.dissolve_alpha = max(0, int(self.dissolve_alpha) - 10)
                    try:
                        self.current_sprite.set_alpha(self.dissolve_alpha)
                    except Exception:
                        pass
                    # when fully faded, mark as dead so draw() can stop showing it
                    if self.dissolve_alpha <= 0:
                        self.state = 'dead'
                except Exception:
                    pass
        except Exception:
            pass

# Boss arrival banner / overlay state
boss_banner_active = False
boss_banner_start = 0
BOSS_BANNER_DURATION_MS = 2000
boss_banner_text = ""
boss_banner_image = None

# Boss visual harm state: when True, draw the harmed sprite version for a short duration
is_boss_harmed = False
boss_harm_end_time = 0  # pygame.time.get_ticks() + ms

# Track ante/section level (starts at 1)
ante_level = 1
# Current boss effect (None when no boss effect active)
current_boss_effect = None
# Count how many boss encounters have occurred (used to pick boss assets)
boss_encounter_count = 0

# Persistent meta counters and story state
consecutive_kills = 0
total_spared_bosses = 0
current_boss_story = ""
current_boss_key = None
# Typewriter/story display globals for boss story screen (STATE_BOSS_DEFEATED_B)
visible_story_text = ""  # currently visible portion of the story
story_text_index = 0      # next character index to reveal
story_timer = 0           # accumulator in milliseconds
# Delay between characters in milliseconds
STORY_CHAR_DELAY = 30
# Index of a joker temporarily disabled by a boss (JOKER_ENVY). -1 = none
disabled_joker_index = -1
# Gambit result display state (message shown after making choice)
gambit_result_message = ""
pending_gambit_choice = None

# Screen shake globals
shake_timer_ms = 0
shake_last_tick = 0
SHAKE_DURATION_MS = 300
SHAKE_MAG = 8

def start_shake(duration_ms=300, magnitude=8):
    """Start a screen shake for duration_ms milliseconds at given magnitude."""
    global shake_timer_ms, shake_last_tick, SHAKE_DURATION_MS, SHAKE_MAG
    try:
        shake_timer_ms = int(duration_ms)
        SHAKE_DURATION_MS = int(duration_ms)
        SHAKE_MAG = int(magnitude)
        shake_last_tick = pygame.time.get_ticks()
    except Exception:
        pass

# Available boss effects and descriptions
BOSS_EFFECTS = [
    # (Boss effects list left empty of the old 'no-spades' debuff.)
    # Add new boss effects here as needed.
]
BOSS_EFFECT_DESC = {
    # Descriptions for boss effects are registered here.
}

# Temporary invalid-play message shown when a hand is blocked by boss effect
invalid_message = None
invalid_message_time = 0
INVALID_MESSAGE_DURATION_MS = 2000

# Hovered card (hand) for group animation
hovered_card = None

# Right-button drag group state
drag_active = False
drag_origin = (0, 0)

# Pool of possible jokers available in the shop (updated to use assets/jokers/*.png)
JOKER_POOL = [
    {'name': 'Maça Çarpanı', 
     'desc': 'Maça varsa +4 Çarpan.', 
     'effect_id': 'ADD_MULTIPLIER_SPADES', 
     'image_path': 'assets/jokers/joker_maca_carpani.png', 
     'price': 10},
    {'name': 'Per Güçlendirici', 
     'desc': 'Per eller +4 Çarpan.', 
     'effect_id': 'PLUS_4_MULT_IF_PER', 
     'image_path': 'assets/jokers/joker_per_guclendirici.png', 
     'price': 9},
    {'name': 'Kare Uzmanı', 
     'desc': 'Kare elde +6 Çarpan.', 
     'effect_id': 'PLUS_6_MULT_IF_FOUR_KIND', 
     'image_path': 'assets/jokers/joker_kare_uzmani.png', 
     'price': 25},
    {'name': 'Yedili Fişi', 
     'desc': 'Elde "7" varsa +20 Fiş.', 
     'effect_id': 'PLUS_20_CHIPS_FOR_SEVENS', 
     'image_path': 'assets/jokers/joker_yedili_fisi.png', 
     'price': 8},
    {'name': 'Rastgele Şans', 
     'desc': 'Rastgele küçük bonus verir.', 
     'effect_id': 'RANDOM_SMALL_BONUS', 
     'image_path': 'assets/jokers/joker_rastgele_sans.png', 
     'price': 5}
]

# Additional new jokers added per request
JOKER_POOL.extend([
    {
        'name': 'Koleksiyoncu',
        'desc': 'Elinizdeki her 10 Para için +1 Çarpan (Mult).',
        'effect_id': 'COLLECTOR_MONEY_MULT',
        'image_path': 'assets/jokers/joker_collector.png',
        'price': 12
    },
    {
        'name': 'Maça Ası',
        'desc': 'Oynanan her Maça (♠️) kartı, +3 Çip verir.',
        'effect_id': 'SPADE_ACE_CHIP',
        'image_path': 'assets/jokers/joker_spade_ace.png',
        'price': 9
    },
    {
        'name': 'Kızıl Kral',
        'desc': 'Oynanan her Kupa (♥️) veya Karo (♦️) kartı, +2 Çarpan verir.',
        'effect_id': 'RED_KING_MULT',
        'image_path': 'assets/jokers/joker_red_king.png',
        'price': 14
    },
    {
        'name': 'Minimalist',
        'desc': "Elinizde sadece 3 kart oynarsanız, o elin puanını x3 yapar.",
        'effect_id': 'MINIMALIST_HAND_X3',
        'image_path': 'assets/jokers/joker_minimalist.png',
        'price': 22
    },
    {
        'name': 'Zamanlayıcı',
        'desc': "Bu Joker +20 Çarpan verir, ancak her el oynadığınızda bonus 1 azalır (0'a kadar).",
        'effect_id': 'TIMER_DECAY_MULT',
        'image_path': 'assets/jokers/joker_timer.png',
        'price': 20
    },
])

# Voucher (kupon) pool: shop can offer one voucher
VOUCHER_POOL = [
    {'name': 'El Limiti Arttırıcı', 'desc': '+1 El Boyutu', 'price': 20, 'effect_id': 'INC_HAND_SIZE'},
    {'name': 'Değiştirme Arttırıcı', 'desc': '+1 Değiştirme Hakkı', 'price': 15, 'effect_id': 'INC_DISCARD_LIMIT'},
    # Kırmızı Mühür: bir kartınıza RED mühürü ekler (eldeyken oynandığında el puanını ikiye katlar)
    {'name': 'Kırmızı Mühür', 'desc': "Eldeki rastgele bir karta Kırmızı Mühür verir (oynanırsa el x2)", 'price': 18, 'effect_id': 'RED_SEAL'},
]

# Player-owned persistent items (vouchers and planet upgrades).
# These must persist across ante/round transitions and should not be
# cleared when entering the SHOP or starting a new ante.
player_vouchers = []
player_planets = []

# Discard pile (cards that have been played/discarded). If the game
# doesn't yet populate this list elsewhere, it's safe to keep it empty
# and the refill logic below will be a no-op.
discard_pile = []

# current shop voucher shown (single)
shop_voucher = None
shop_voucher_rect = None

# Planet/level system: each hand type has a level that multiplies base rewards
PLANET_LEVELS = {
    'High Card': 1,
    'Per': 1,
    'Döper': 1,
    'Üçlü': 1,
    'Kent': 1,
    'Flush': 1,
    'Full House': 1,
    'Kare': 1,
    'Straight Flush': 1,
    'Royal Flush': 1,
}

# Optional pool of planet items the shop may offer; empty by default
PLANET_POOL = []


def wrap_text(text, font, max_width):
    """Simple word-wrap: split text into lines that fit max_width using font.size()."""
    words = text.split()
    lines = []
    if not words:
        return lines
    cur = words[0]
    for w in words[1:]:
        test = cur + ' ' + w
        if font.size(test)[0] <= max_width:
            cur = test
        else:
            lines.append(cur)
            cur = w
    lines.append(cur)
    return lines


def handle_gambit_choice(choice):
    """Handle the player's gambit decision after a boss defeat.

    choice: 'KILL' or 'SPARE'
    This applies simple bookkeeping (incrementing spare counters) and
    prepares the next ante/round by resetting scores/hand and loading
    the boss for the next ante.
    """
    global total_spared_bosses, ante_level, HANDS_REMAINING, DISCARDS_REMAINING
    global current_score, displayed_score, shop_items_generated, current_shop_items
    global extra_card, first_ante_completed, enemy, current_boss_effect, current_boss_story
    global MONEY, consecutive_kills
    # Centralize globals we will modify/read
    global total_spared_bosses, ante_level, HANDS_REMAINING, DISCARDS_REMAINING
    global current_score, displayed_score, shop_items_generated, current_shop_items
    global extra_card, first_ante_completed, enemy, current_boss_effect, current_boss_story
    global MONEY, consecutive_kills, pending_gambit_choice, gambit_result_message

    # --- SEÇİMİ KAYDET ---
    try:
        globals()['pending_gambit_choice'] = choice
    except Exception:
        pass

    # Normalize incoming choice and support both legacy ('KILL'/'SPARE')
    # and new UI values ('AGGRESSIVE'/'EMPATHETIC'/'RATIONAL').
    try:
        norm = str(choice).upper() if choice is not None else ''
    except Exception:
        norm = choice

    # --- AGGRESSIVE / KILL: award money, increment kill streak ---
    if norm in ('AGGRESSIVE', 'KILL'):
        try:
            kb = int(globals().get('KILL_BONUS_BASE', 5))
            km = int(globals().get('KILL_BONUS_MULTIPLIER', 2))
            streak = int(consecutive_kills or 0)
            bonus = int(kb * (km ** streak))
        except Exception:
            try:
                bonus = 5 * (2 ** int(consecutive_kills or 0))
            except Exception:
                bonus = 5
        try:
            MONEY = int((MONEY if MONEY is not None else 0) + int(bonus))
        except Exception:
            try:
                globals()['MONEY'] = int(bonus)
            except Exception:
                pass
        try:
            consecutive_kills = int(consecutive_kills or 0) + 1
        except Exception:
            consecutive_kills = 1
        try:
            threshold = int(globals().get('KILL_BANNER_THRESHOLD', 2))
            if threshold > 0 and (int(consecutive_kills) % threshold) == 0:
                try:
                    if active_jokers:
                        idx = random.randrange(len(active_jokers))
                        globals()['joker_kill_banner_index'] = int(idx)
                    else:
                        globals()['joker_kill_banner_index'] = -1
                except Exception:
                    globals()['joker_kill_banner_index'] = -1
        except Exception:
            try:
                globals()['joker_kill_banner_index'] = -1
            except Exception:
                pass

        try:
            globals()['gambit_result_message'] = f"{int(bonus)} $ kazandın."
        except Exception:
            globals()['gambit_result_message'] = "Ödül kazandın."
        try:
            globals()['game_state'] = STATE_GAMBIT_RESULT
        except Exception:
            pass

    # --- EMPATHETIC / SPARE: start mercy phase ---
    elif norm in ('EMPATHETIC', 'SPARE'):
        try:
            globals()['total_spared_bosses'] = int(globals().get('total_spared_bosses', 0)) + 1
        except Exception:
            globals()['total_spared_bosses'] = 1
        try:
            globals()['consecutive_kills'] = 0
        except Exception:
            globals()['consecutive_kills'] = 0
        try:
            globals()['joker_kill_banner_index'] = -1
        except Exception:
            pass

        try:
            globals()['mercy_timer'] = 0
            globals()['mercy_hit_count'] = 0
            globals()['mercy_warmup_timer'] = 1.0
            globals()['mercy_projectiles'] = []
            lvl = int(globals().get('ante_level', 1))
            globals()['mercy_duration'] = int((5 + lvl * 1.5) * 1000)
            if 'MercySoul' in globals():
                try:
                    globals()['mercy_player'] = MercySoul()
                except Exception:
                    pass
        except Exception:
            pass

        try:
            globals()['game_state'] = STATE_MERCY_PHASE
        except Exception:
            pass

    # --- RATIONAL / BRIBE: negotiate, treat as a spared boss but skip mercy phase ---
    elif norm in ('RATIONAL', 'BRIBE'):
        try:
            globals()['total_spared_bosses'] = int(globals().get('total_spared_bosses', 0)) + 1
        except Exception:
            globals()['total_spared_bosses'] = 1
        try:
            globals()['consecutive_kills'] = 0
        except Exception:
            globals()['consecutive_kills'] = 0
        try:
            globals()['joker_kill_banner_index'] = -1
        except Exception:
            pass

        # KÜRE VER
        try:
            if 'player_fate_orbs' in globals() and len(player_fate_orbs) < 5:
                if 'FATE_ORBS_POOL' in globals() and FATE_ORBS_POOL:
                    import random
                    new_orb = random.choice(FATE_ORBS_POOL)
                    player_fate_orbs.append(new_orb)
                    print(f"DEBUG: Küre Verildi: {new_orb.get('name', new_orb.get('id'))}")
        except Exception:
            pass

        try:
            cur_ante = int(globals().get('ante_level', 1))
        except Exception:
            cur_ante = 1
        bribe = int(10 + max(0, (cur_ante - 1)) * 2)
        try:
            MONEY = int((MONEY if MONEY is not None else 0) + bribe)
        except Exception:
            try:
                globals()['MONEY'] = int(globals().get('MONEY', 0)) + bribe
            except Exception:
                pass

        try:
            globals()['gambit_result_message'] = "Anlaşma sağlandı. Yoluna devam ediyorsun."
        except Exception:
            globals()['gambit_result_message'] = "Anlaşma sağlandı. Yoluna devam ediyorsun."
        try:
            globals()['game_state'] = STATE_GAMBIT_RESULT
        except Exception:
            pass

    # finalize: reset hand state for next round
    try:
        reset_hand_state()
    except Exception:
        pass


def fill_hand_slots():
    """Fill empty slots in `hand` up to MAX_HAND_SLOTS by drawing from `deck`.

    This sets slot_index, base_x and target_x for newly created Card instances.
    """
    global hand, deck, MAX_HAND_SLOTS, current_boss_effect
    # ensure layout is up-to-date before filling slots
    try:
        recompute_ui_layout()
    except Exception:
        pass
    # Quick pre-check: only proceed if we actually need cards. Also ensure the
    # deck has enough cards; if not, try to recycle the discard pile into the deck.
    try:
        # Determine target slots: use MAX_HAND_SLOTS (cards per hand)
        try:
            if target_slots is None:
                target_slots = int(MAX_HAND_SLOTS)
        except Exception:
            target_slots = MAX_HAND_SLOTS

        # Keep drawing until we have the desired number of visible cards
        drawn_count = 0
        while len([c for c in hand if c is not None]) < target_slots:
            # If deck is empty, attempt to rebuild from discard_pile
            try:
                deck_cards = getattr(deck, 'cards', None) or []
            except Exception:
                deck_cards = []

            if len(deck_cards) == 0:
                try:
                    print("DEBUG: Deste bitti, atılanlar karıştırılıyor...")
                except Exception:
                    pass
                try:
                    if 'discard_pile' in globals() and discard_pile:
                        new_cards = []
                        for it in list(discard_pile):
                            try:
                                if isinstance(it, tuple) and len(it) == 2:
                                    new_cards.append(DeckCard(suit=it[0], rank=it[1]))
                                elif hasattr(it, 'suit') and hasattr(it, 'rank'):
                                    new_cards.append(it)
                            except Exception:
                                pass
                        if new_cards:
                            try:
                                deck.cards.extend(new_cards)
                            except Exception:
                                deck.cards = list(new_cards)
                            try:
                                discard_pile.clear()
                            except Exception:
                                pass
                            try:
                                deck.shuffle()
                            except Exception:
                                try:
                                    random.shuffle(deck.cards)
                                except Exception:
                                    pass
                    else:
                        try:
                            print("Oyun Bitti: Çekilecek kart kalmadı.")
                        except Exception:
                            pass
                        try:
                            globals()['game_state'] = STATE_GAME_OVER
                        except Exception:
                            try:
                                game_state = STATE_GAME_OVER
                            except Exception:
                                pass
                        break
                except Exception:
                    break

            # Draw a single card safely
            try:
                card_data = safe_draw()
            except Exception:
                card_data = None
            if card_data is None:
                # nothing to draw; exit loop
                break

            # Determine where to place the card: first free slot or append
            try:
                s = card_data.suit
                r = card_data.rank
                img = card_images.get(s, {}).get(r)
                if img is None:
                    img = get_card_image(s, r)
            except Exception:
                s = getattr(card_data, 'suit', None)
                r = getattr(card_data, 'rank', None)
                img = None
                try:
                    img = card_images.get(s, {}).get(r)
                except Exception:
                    try:
                        img = get_card_image(s, r)
                    except Exception:
                        img = None

            # find first free index up to target_slots
            placed = False
            for i in range(target_slots):
                if i >= len(hand):
                    hand.append(None)
                if hand[i] is None:
                    nc = Card(img or pygame.Surface((CARD_WIDTH, CARD_HEIGHT)), START_X + (i * CARD_SPACING), NORMAL_Y, r, s)
                    try:
                        maybe_apply_soul_holo(nc)
                    except Exception:
                        pass
                    nc.slot_index = i
                    nc.base_x = START_X + (i * CARD_SPACING)
                    nc.target_x = nc.base_x
                    hand[i] = nc
                    drawn_count += 1
                    placed = True
                    break
            if not placed:
                # append defensively
                nc = Card(img or pygame.Surface((CARD_WIDTH, CARD_HEIGHT)), START_X, NORMAL_Y, r, s)
                try:
                    maybe_apply_soul_holo(nc)
                except Exception:
                    pass
                hand.append(nc)
                drawn_count += 1

        # Update layout targets after dealing
        try:
            recalculate_hand_positions()
        except Exception:
            try:
                recompute_ui_layout()
            except Exception:
                pass
    except Exception:
        pass


def buy_item(item):
    """Attempt to buy `item` from the shop.

    Returns True if purchase succeeded (money deducted and effects applied), False otherwise.
    """
    global MONEY, active_jokers, PLANET_LEVELS, MAX_HAND_SLOTS, hand, EXTRA_SLOT_X, extra_card, DISCARDS_REMAINING
    price = item.get('price', 0)
    # Determine type/name early so we can validate purchase constraints
    otype = str(item.get('type', '')).lower()
    iname = str(item.get('name', '')).lower()

    # --- JOKER SLOT LIMIT CHECK ---
    try:
        if otype == 'joker' or 'joker' in iname:
            max_slots = int(globals().get('JOKER_SLOTS_MAX', 5))
            if len(active_jokers) >= int(max_slots):
                try:
                    print(f"HATA: Joker slotları dolu! (Maksimum {max_slots})")
                except Exception:
                    pass
                return False
    except Exception:
        pass

    if MONEY < price:
        print("Yetersiz para: Teklif satın alınamadı")
        return False

    MONEY -= price
    try:
        _ = globals().get('MONEY')
    except Exception:
        pass
    if otype == 'planet':
        hand_type = item.get('hand_type')
        if hand_type:
            PLANET_LEVELS[hand_type] = PLANET_LEVELS.get(hand_type, 1) + 1
            print(f"Gezegen satın alındı: {item.get('name')} -> {hand_type} seviyesi = {PLANET_LEVELS[hand_type]}")
    elif otype == 'voucher':
        eff = item.get('effect_id')
        if eff == 'INC_HAND_SIZE':
            # increase capacity then ensure layout and optionally grant extra card
            MAX_HAND_SLOTS += 1
            hand.append(None)
            try:
                recompute_ui_layout()
            except Exception:
                pass

            # If player does not currently have an extra card, create one now
            if extra_card is None:
                try:
                    new_extra = safe_draw()
                except Exception:
                    new_extra = None

                s = 'spades'
                r = 'ace'
                if new_extra is not None:
                    try:
                        s = getattr(new_extra, 'suit', s)
                        r = getattr(new_extra, 'rank', r)
                    except Exception:
                        pass

                # Try to fetch scaled image from cache, fallback to generator, then placeholder
                img = None
                try:
                    img = card_images.get(s, {}).get(r)
                except Exception:
                    img = None
                if img is None:
                    try:
                        img = get_card_image(s, r)
                    except Exception:
                        img = None
                if img is None:
                    try:
                        img = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
                        img.fill((255,255,255))
                    except Exception:
                        img = None

                try:
                    extra_card = Card(img, globals().get('EXTRA_SLOT_X', START_X), globals().get('NORMAL_Y_POS', NORMAL_Y), r, s)
                    try:
                        maybe_apply_soul_holo(extra_card)
                    except Exception:
                        pass
                except Exception:
                    try:
                        # fallback: create minimal Card-like object
                        extra_card = Card(img or pygame.Surface((CARD_WIDTH, CARD_HEIGHT)), globals().get('EXTRA_SLOT_X', START_X), globals().get('NORMAL_Y_POS', NORMAL_Y), r, s)
                    except Exception:
                        pass
        elif eff == 'INC_DISCARD_LIMIT':
            DISCARDS_REMAINING += 1
        elif eff == 'RED_SEAL':
            # Assign a Red seal to a random owned card (hand or extra_card)
            try:
                candidates = [c for c in hand if c is not None]
                if extra_card is not None:
                    candidates.append(extra_card)
                if candidates:
                    target = random.choice(candidates)
                    try:
                        target.seal = 'Red'
                        print(f"Kırmızı Mühür uygulandı: {getattr(target,'rank', '?')} of {getattr(target,'suit', '?')}")
                    except Exception:
                        pass
                else:
                    print('Kırmızı Mühür alınsa da uygulanacak kart yok.')
            except Exception:
                pass

        # Record purchased voucher in persistent player inventory so it
        # isn't lost when shop offers regenerate or rounds advance.
        try:
            if 'player_vouchers' in globals():
                player_vouchers.append(dict(item))
        except Exception:
            pass

        print(f"Kupon satın alındı: {item.get('name')} | Para={MONEY}")
    else:
        # regular joker purchase
        new_joker = Joker(name=item.get('name'), effect_id=item.get('effect_id'), desc=item.get('desc',''), image_path=item.get('image_path'))
        try:
            if len(active_jokers) < globals().get('JOKER_SLOTS_MAX', 5):
                active_jokers.append(new_joker)
                try:
                    print(f"Joker satın alındı: {new_joker.name} - Etki: {new_joker.effect_id} | Kalan para: {MONEY}")
                except Exception:
                    pass
            else:
                try:
                    print("UYARI: Joker limiti dolu! Ekleme engellendi.")
                except Exception:
                    pass
        except Exception:
            # Fallback: attempt append if something unexpected happens
            try:
                active_jokers.append(new_joker)
            except Exception:
                pass

    # play buy sound if available
    try:
        if buy_sound:
            play_sound(buy_sound)
    except Exception:
        pass

    return True

def reset_game():
    """Reset all game state to initial values and refill hand/deck."""
    global current_score, TARGET_SCORE, HANDS_REMAINING, DISCARDS_REMAINING, MONEY
    global active_jokers, deck, hand, game_state
    global shop_items_generated, current_shop_items, displayed_score
    global enemy, ante_level, boss_encounter_count, current_boss_effect, current_boss_ability, current_boss_ability_desc
    global INITIAL_HANDS, DEFAULT_DISCARDS
    global current_boss_key, extra_card, first_ante_completed
    global current_extra_card_slot_active
    global joker_kill_banner_index, boss_banner_active, boss_banner_image, boss_banner_start
    global is_boss_harmed, boss_harm_end_time, pending_gambit_choice, gambit_result_message

    # Reset core values
    current_score = 0
    displayed_score = 0
    # Use configured starting target if available
    try:
        TARGET_SCORE = globals().get('ANTE_1_TARGET', 60)
    except Exception:
        TARGET_SCORE = 60
    # Reset ante level to the initial starting ante for a fresh run
    try:
        ante_level = 1
    except Exception:
        pass
    # Use the session-selected deck defaults
    # Reset run defaults: ensure any per-run deck bonuses (e.g. +1 hand)
    # from a previous run are cleared here. `start_new_run()` will apply
    # deck-specific modifiers after this reset.
    try:
        # Prefer an explicit DEFAULT_HANDS if set (e.g. via globals.py),
        # otherwise fall back to INITIAL_HANDS so the starting hand count
        # remains consistent with the in-file tuning constant.
        DEFAULT_HANDS = int(globals().get('DEFAULT_HANDS', globals().get('INITIAL_HANDS', 4)))
    except Exception:
        try:
            DEFAULT_HANDS = int(globals().get('INITIAL_HANDS', 4))
        except Exception:
            DEFAULT_HANDS = 4
    try:
        DEFAULT_DISCARDS = int(globals().get('DEFAULT_DISCARDS', 3))
    except Exception:
        DEFAULT_DISCARDS = 3
    try:
        DEFAULT_JOKER_SLOTS = int(globals().get('DEFAULT_JOKER_SLOTS', 5))
    except Exception:
        DEFAULT_JOKER_SLOTS = 5

    HANDS_REMAINING = DEFAULT_HANDS
    DISCARDS_REMAINING = DEFAULT_DISCARDS
    # Ensure JOKER_SLOTS_MAX is reset to default for a fresh run
    try:
        JOKER_SLOTS_MAX = int(DEFAULT_JOKER_SLOTS)
    except Exception:
        try:
            globals()['JOKER_SLOTS_MAX'] = DEFAULT_JOKER_SLOTS
        except Exception:
            pass

    # Reset money to zero for a fresh run
    MONEY = 0
    try:
        try:
            _ = globals().get('MONEY')
        except Exception:
            pass
    except Exception:
        pass

    # Clear jokers
    active_jokers = []
    # --- Clear boss ability rules so no boss-specific rule persists across runs ---
    try:
        current_boss_ability = None
    except Exception:
        try:
            globals()['current_boss_ability'] = None
        except Exception:
            pass
    try:
        current_boss_ability_desc = ""
    except Exception:
        try:
            globals()['current_boss_ability_desc'] = ""
        except Exception:
            pass
    # Reset any joker kill-banner marker
    try:
        joker_kill_banner_index = -1
    except Exception:
        try:
            globals()['joker_kill_banner_index'] = -1
        except Exception:
            pass
    # Reset any boss-disabled joker index
    try:
        globals()['disabled_joker_index'] = -1
    except Exception:
        try:
            disabled_joker_index = -1
        except Exception:
            pass
    # Clear shop offers
    shop_offers.clear()
    shop_offer_rects.clear()
    # reset one-time shop generation state
    shop_items_generated = False
    current_shop_items = []

    # New deck and shuffle
    deck = Deck()
    deck.shuffle()

    # Prepare hand slots and fill them
    hand = [None] * MAX_HAND_SLOTS
    fill_hand_slots()

    # Clear boss / enemy related state so a fresh run starts clean
    try:
        current_boss_key = None
    except Exception:
        try:
            globals()['current_boss_key'] = None
        except Exception:
            pass
    try:
        boss_encounter_count = 0
    except Exception:
        pass
    try:
        # remove any existing enemy instance; new boss will be loaded at ante start
        enemy = None
    except Exception:
        try:
            globals()['enemy'] = None
        except Exception:
            pass
    try:
        boss_banner_active = False
        boss_banner_image = None
        boss_banner_start = 0
    except Exception:
        pass
    try:
        is_boss_harmed = False
        boss_harm_end_time = 0
    except Exception:
        pass

    # Clear extra-round state
    try:
        extra_card = None
    except Exception:
        pass
    try:
        first_ante_completed = False
    except Exception:
        pass

    # Ensure Ante 1 starts with the extra-card slot enabled so the player
    # receives the extra card on the first ante of a new run.
    try:
        current_extra_card_slot_active = False
    except Exception:
        try:
            globals()['current_extra_card_slot_active'] = False
        except Exception:
            pass

    # Clear pending gambit/result UI state
    try:
        pending_gambit_choice = None
        gambit_result_message = ""
    except Exception:
        pass

    # Clear selection/interaction locks
    try:
        selected_cards.clear()
    except Exception:
        try:
            selected_cards = []
        except Exception:
            pass
    try:
        cards_locked = False
        is_hand_processing = False
    except Exception:
        pass


def reset_hand_state():
    global current_score, displayed_score, selected_cards, HANDS_REMAINING, DISCARDS_REMAINING, MONEY, MAX_HAND_SLOTS

    # 1. Geçici Değişkenleri Sıfırla
    try:
        current_score = 0
    except Exception:
        try:
            globals()['current_score'] = 0
        except Exception:
            pass
    try:
        displayed_score = 0
    except Exception:
        try:
            globals()['displayed_score'] = 0
        except Exception:
            pass
    try:
        selected_cards = []
    except Exception:
        try:
            globals()['selected_cards'] = []
        except Exception:
            pass

    # 2. Temel Değerleri Yükle (Varsayılanlar + Deste Bonusu)
    try:
        base_hands = int(globals().get('DEFAULT_HANDS', 4))
    except Exception:
        base_hands = 4
    try:
        base_discards = int(globals().get('DEFAULT_DISCARDS', 3))
    except Exception:
        base_discards = 3

    deck_perk = globals().get('SELECTED_DECK_PERK')
    try:
        if deck_perk == 'RED':
            base_hands += 1
        if deck_perk == 'BLUE':
            base_discards += 1
    except Exception:
        pass

    # 3. BOSS CEZALARINI UYGULA (EN SON - Override)
    try:
        boss_ability = globals().get('current_boss_ability')
    except Exception:
        boss_ability = None

    try:
        if boss_ability == 'REDUCE_DISCARDS_2':
            base_discards -= 2
            try:
                print("DEBUG: Boss Cezası Uygulandı: -2 Discard")
            except Exception:
                pass
    except Exception:
        pass

    # 4. Sonuçları Ata ve Sınırla
    try:
        HANDS_REMAINING = max(1, int(base_hands))
    except Exception:
        try:
            globals()['HANDS_REMAINING'] = max(1, int(base_hands))
        except Exception:
            pass
    try:
        DISCARDS_REMAINING = max(0, int(base_discards))
    except Exception:
        try:
            globals()['DISCARDS_REMAINING'] = max(0, int(base_discards))
            DISCARDS_REMAINING = globals()['DISCARDS_REMAINING']
        except Exception:
            pass

    # El Boyutu (Slot) Yönetimi
    try:
        MAX_HAND_SLOTS = 5
    except Exception:
        try:
            globals()['MAX_HAND_SLOTS'] = 5
        except Exception:
            pass

    try:
        if deck_perk == 'GHOST':
            pass
    except Exception:
        pass

    try:
        if boss_ability == 'MINUS_1_HAND_SIZE':
            MAX_HAND_SLOTS = max(1, MAX_HAND_SLOTS - 1)
    except Exception:
        pass
START_X = 50 # Elin başlamasını istediğimiz X konumu
CARD_SPACING = 110 # Kartlar arası boşluk (100 kart + 10 boşluk)
# Fixed slot X for the extra card (to the right of the current hand slots)
# Compute from MAX_HAND_SLOTS so increasing hand size pushes the extra slot outward
EXTRA_SLOT_X = START_X + (MAX_HAND_SLOTS * CARD_SPACING)


def compute_hand_positions(count: int):
    """Return a list of x positions for `count` cards.

    This keeps the hand within the area left of the extra slot. It centers the
    cards starting at START_X and uses a spacing that fits the available area.
    """
    # For deterministic fixed-slot layout we want positions for the full slot set
    slots = MAX_HAND_SLOTS
    if slots <= 0:
        return []
    # available horizontal space from START_X to just before EXTRA_SLOT_X
    available_width = max(0, EXTRA_SLOT_X - START_X - CARD_WIDTH)
    if slots == 1:
        return [START_X]
    # compute spacing so the last card (left edge) doesn't overlap the extra slot
    # spacing between card origins
    spacing = min(CARD_SPACING, available_width / (slots - 1))
    positions = [int(START_X + i * spacing) for i in range(slots)]
    return positions


def recalculate_hand_positions():
    """Recalculate target positions for cards in hand and set their target_x/target_y.

    This uses the current number of actual cards in `hand` (non-None entries) to
    compute TOTAL_HAND_WIDTH and centers the hand on screen. It sets each card's
    target_x/target_y (does not modify rect directly).
    """
    global START_X
    try:
        # number of visible cards (non-None)
        visible_cards = [c for c in hand if c is not None]
        count = len(visible_cards)
        if count == 0:
            count = max(1, len(hand))

        # --- YENİ GÜVENLİ YERLEŞİM MANTIĞI ---
        SAFE_MARGIN = 50
        MAX_AVAILABLE_WIDTH = SCREEN_WIDTH - (2 * SAFE_MARGIN)

        if count > 0:
            STANDARD_SPACING = 10
            native_width = (count * CARD_WIDTH) + ((count - 1) * STANDARD_SPACING)

            if native_width <= MAX_AVAILABLE_WIDTH:
                step = CARD_WIDTH + STANDARD_SPACING
                total_width = native_width
            else:
                if count > 1:
                    step = (MAX_AVAILABLE_WIDTH - CARD_WIDTH) / (count - 1)
                else:
                    step = CARD_WIDTH
                total_width = MAX_AVAILABLE_WIDTH

            START_X = int((SCREEN_WIDTH - total_width) / 2)
            if START_X < SAFE_MARGIN:
                START_X = SAFE_MARGIN

            # assign targets based on current visible ordering
            idx = 0
            for i, card in enumerate(hand):
                if card is None:
                    continue
                try:
                    card.target_x = float(START_X + idx * step)
                except Exception:
                    card.target_x = float(START_X + idx * (CARD_WIDTH + STANDARD_SPACING))
                # Y placement
                try:
                    if getattr(card, 'is_selected', False):
                        card.target_y = float(SELECTED_Y_POS)
                    elif getattr(card, 'is_hovered', False):
                        card.target_y = float(HOVER_Y_POS)
                    else:
                        card.target_y = float(NORMAL_Y_POS)
                except Exception:
                    card.target_y = float(SELECTED_Y if getattr(card, 'is_selected', False) else NORMAL_Y)
                try:
                    card.slot_index = i
                except Exception:
                    pass
                idx += 1

            # EXTRA_SLOT_X: place to right of last card, then clamp to screen
            try:
                last_card_edge = START_X + ((count - 1) * step) + CARD_WIDTH
                globals()['EXTRA_SLOT_X'] = int(last_card_edge + 20)
                if globals()['EXTRA_SLOT_X'] + CARD_WIDTH > SCREEN_WIDTH - 20:
                    globals()['EXTRA_SLOT_X'] = SCREEN_WIDTH - CARD_WIDTH - 20
            except Exception:
                try:
                    globals()['EXTRA_SLOT_X'] = START_X + (len(hand) * step) + 20
                except Exception:
                    pass
    except Exception:
        pass


def update_hand_layout():
    """Compute centered hand layout and assign target positions for each card.

    This centers the hand horizontally and sets each card.target_x/target_y so
    the per-card update() lerps them into place.
    """
    global START_X
    try:
        # number of slots to layout (respect current hand length)
        count = len(hand)
        if count <= 0:
            return

        # --- YENİ GÜVENLİ YERLEŞİM MANTIĞI ---
        SAFE_MARGIN = 50
        MAX_AVAILABLE_WIDTH = SCREEN_WIDTH - (2 * SAFE_MARGIN)

        if count > 0:
            STANDARD_SPACING = 10
            native_width = (count * CARD_WIDTH) + ((count - 1) * STANDARD_SPACING)

            if native_width <= MAX_AVAILABLE_WIDTH:
                step = CARD_WIDTH + STANDARD_SPACING
                total_width = native_width
            else:
                if count > 1:
                    step = (MAX_AVAILABLE_WIDTH - CARD_WIDTH) / (count - 1)
                else:
                    step = CARD_WIDTH
                total_width = MAX_AVAILABLE_WIDTH

            START_X = int((SCREEN_WIDTH - total_width) / 2)
            if START_X < SAFE_MARGIN:
                START_X = SAFE_MARGIN

            for i, card in enumerate(hand):
                if card is None:
                    continue
                try:
                    card.target_x = START_X + int(i * step)
                except Exception:
                    card.target_x = START_X + i * (CARD_WIDTH + STANDARD_SPACING)
                try:
                    if getattr(card, 'is_selected', False):
                        card.target_y = float(SELECTED_Y_POS)
                    elif getattr(card, 'is_hovered', False):
                        card.target_y = float(HOVER_Y_POS)
                    else:
                        card.target_y = float(NORMAL_Y_POS)
                except Exception:
                    card.target_y = float(SELECTED_Y if getattr(card, 'is_selected', False) else NORMAL_Y)

        # Clamp EXTRA_SLOT_X based on last card position
        try:
            last_card_edge = START_X + ((count - 1) * step) + CARD_WIDTH
            globals()['EXTRA_SLOT_X'] = int(last_card_edge + 20)
            if globals()['EXTRA_SLOT_X'] + CARD_WIDTH > SCREEN_WIDTH - 20:
                globals()['EXTRA_SLOT_X'] = SCREEN_WIDTH - CARD_WIDTH - 20
        except Exception:
            try:
                globals()['EXTRA_SLOT_X'] = START_X + (count * (CARD_WIDTH + STANDARD_SPACING)) + 20
            except Exception:
                pass
    except Exception:
        pass


def load_boss_for_ante(level: int):
    """Load boss for given `level` with endless-mode support and direct `assets/` image lookup.

    Scaling: after ante 9 the difficulty scales increasingly. Boss selection:
      - ante 1..9: normal sequence from `BOSS_SEQUENCE_KEYS`
      - ante 10..14: the five `endless1..endless5` in order
      - ante 15+: pick randomly from all bosses (including endless)
    """
    global enemy, TARGET_SCORE, current_boss_key, current_boss_ability
    global boss_banner_text, current_boss_story, current_boss_ability_desc, current_extra_card_slot_active
    global boss_banner_active, boss_banner_start, boss_banner_image, boss_sound
    try:
        lvl = max(1, int(level))
    except Exception:
        lvl = 1

    # --- 1) Scaling ---
    try:
        base_ante1 = int(globals().get('ANTE_1_TARGET', 60))
    except Exception:
        base_ante1 = 60
    try:
        ante_inc = int(globals().get('ANTE_INCREMENT_PER_LEVEL', 100))
    except Exception:
        ante_inc = 100
    try:
        bh_start = int(globals().get('BOSS_HEALTH_START', base_ante1))
    except Exception:
        bh_start = base_ante1
    try:
        bh_inc = int(globals().get('BOSS_HEALTH_INCREMENT_PER_ANTE', ante_inc))
    except Exception:
        bh_inc = ante_inc

    scaling_factor = 1.0
    if lvl > 9:
        scaling_factor = 1.5 + ((lvl - 10) * 0.2)

    new_target_score = int((base_ante1 + (lvl - 1) * ante_inc) * scaling_factor)
    new_boss_health = int((bh_start + (lvl - 1) * bh_inc) * scaling_factor)
    try:
        TARGET_SCORE = int(new_target_score)
    except Exception:
        pass

    # Ensure enemy exists and set health
    try:
        if enemy is None:
            enemy = Enemy()
    except Exception:
        enemy = Enemy()
    try:
        if hasattr(enemy, 'set_health'):
            enemy.set_health(int(new_boss_health))
        else:
            enemy.max_health = int(new_boss_health)
            enemy.health = int(new_boss_health)
    except Exception:
        try:
            enemy.max_health = int(new_boss_health)
            enemy.health = int(new_boss_health)
        except Exception:
            pass

    # --- 2) Boss selection (normal vs endless vs random) ---
    try:
        BOSS_SEQUENCE_KEYS = globals().get('BOSS_SEQUENCE_KEYS') or ['boss1', 'boss2', 'mainboss1', 'smug', 'shi-shu', 'mainboss2', 'pimp', 'coby', 'mainboss3']
    except Exception:
        BOSS_SEQUENCE_KEYS = ['boss1', 'boss2', 'mainboss1']

    if lvl <= 9:
        # clamp index to available sequence
        idx = max(0, min(lvl - 1, len(BOSS_SEQUENCE_KEYS) - 1))
        boss_key = BOSS_SEQUENCE_KEYS[idx]
    elif 10 <= lvl <= 14:
        endless_keys = ['endless1', 'endless2', 'endless3', 'endless4', 'endless5']
        boss_key = endless_keys[lvl - 10]
    else:
        # free-for-all random selection from all known bosses
        try:
            all_bosses = list(BOSS_SEQUENCE_KEYS) + ['endless1', 'endless2', 'endless3', 'endless4', 'endless5']
            import random
            boss_key = random.choice(all_bosses)
        except Exception:
            boss_key = BOSS_SEQUENCE_KEYS[-1]

    # record key
    try:
        current_boss_key = boss_key
        globals()['current_boss_key'] = boss_key
    except Exception:
        pass

    # --- 3) Load metadata ---
    try:
        md = globals().get('BOSS_METADATA', {}) or {}
        entry = md.get(boss_key, {})
    except Exception:
        entry = {}

    try:
        boss_banner_text = entry.get('display_name', boss_key)
    except Exception:
        boss_banner_text = boss_key
    try:
        current_boss_story = entry.get('story', "") or ""
        current_boss_ability = entry.get('ability_key')
        current_boss_ability_desc = entry.get('ability_desc', "") or ""
        globals()['current_boss_story'] = current_boss_story
        globals()['current_boss_ability'] = current_boss_ability
        globals()['current_boss_ability_desc'] = current_boss_ability_desc
        globals()['current_boss_display_name'] = boss_banner_text
    except Exception:
        try:
            globals()['current_boss_story'] = ""
            globals()['current_boss_ability'] = None
            globals()['current_boss_ability_desc'] = ""
            globals()['current_boss_display_name'] = boss_banner_text
        except Exception:
            pass

    # --- 4) GÖRSEL YÜKLEME ---
    # Sadece dosya adını veya basit yolu gönder, load_sprite gerisini halleder.
    # resource_path'i BURADA DEĞİL, load_sprite içinde kullanıyoruz.
    try:
        image_request_path = f"assets/bosses/{boss_key}.png"
        try:
            enemy.load_sprite(image_request_path)
        except Exception:
            try:
                enemy.load_sprite()
            except Exception:
                pass
    except Exception:
        try:
            enemy.load_sprite()
        except Exception:
            pass

    # --- GÖRSEL DURUM SIFIRLAMA (KRİTİK) ---
    # Yeni boss yüklendiğinde, eski boss'un "yaralı" durumu kalmasın.
    try:
        globals()['is_boss_harmed'] = False
    except Exception:
        pass
    try:
        globals()['boss_harm_end_time'] = 0
    except Exception:
        pass
    
    # Boss'un durumu da sıfırlansın
    try:
        if enemy:
            enemy.state = 'idle'
            enemy.hit_timer = 0
            enemy.dissolve_alpha = 255
    except Exception:
        pass

    # Defensive: ensure ability metadata exists and warn if missing
    try:
        if not current_boss_ability:
            try:
                print(f"UYARI: Boss '{boss_key}' için ability_key metadata eksik veya boş.")
            except Exception:
                pass
    except Exception:
        pass

    # Prepare boss banner image and activate banner
    try:
        boss_banner_image = enemy.current_sprite.copy() if getattr(enemy, 'current_sprite', None) is not None else None
    except Exception:
        boss_banner_image = None
    try:
        boss_banner_active = True
        boss_banner_start = pygame.time.get_ticks()
    except Exception:
        pass

    # Extra card active only for ante 1
    try:
        current_extra_card_slot_active = (lvl == 1)
        globals()['current_extra_card_slot_active'] = current_extra_card_slot_active
    except Exception:
        pass


def safe_draw(_deck=None):
    """Draw a card from `_deck` (or global `deck` if None).

    If the requested deck is empty and this is the main `deck`, attempt to
    recycle `discard_pile` back into the deck, shuffle, and draw again.
    Returns a Card instance or None if no card could be drawn.
    """
    try:
        d = _deck if _deck is not None else globals().get('deck')
    except Exception:
        d = globals().get('deck')
    if d is None:
        return None
    # Pre-draw: if this is the main global deck and it's empty, try to
    # rebuild it from `discard_pile` before attempting a draw. If both
    # are empty, transition to GAME_OVER and return None so callers stop.
    try:
        main_deck = globals().get('deck')
        if d is main_deck:
            try:
                deck_cards = getattr(d, 'cards', None) or []
                if len(deck_cards) == 0:
                    # Attempt to move discard_pile back into the deck
                    if 'discard_pile' in globals() and discard_pile:
                        new_cards = []
                        for it in list(discard_pile):
                            try:
                                if isinstance(it, tuple) and len(it) == 2:
                                    new_cards.append(DeckCard(suit=it[0], rank=it[1]))
                                elif hasattr(it, 'suit') and hasattr(it, 'rank'):
                                    new_cards.append(it)
                            except Exception:
                                pass
                        if new_cards:
                            try:
                                d.cards.extend(new_cards)
                            except Exception:
                                d.cards = list(new_cards)
                            try:
                                discard_pile.clear()
                            except Exception:
                                pass
                            try:
                                d.shuffle()
                            except Exception:
                                try:
                                    random.shuffle(d.cards)
                                except Exception:
                                    pass
                    # If still empty after attempted rebuild, treat as game over
                    deck_cards = getattr(d, 'cards', None) or []
                    if len(deck_cards) == 0:
                        try:
                            print("HATA: Deste ve discard pile boş! Kart çekilemiyor.")
                        except Exception:
                            pass
                        try:
                            globals()['game_state'] = STATE_GAME_OVER
                        except Exception:
                            try:
                                game_state = STATE_GAME_OVER
                            except Exception:
                                pass
                        return None
            except Exception:
                pass

    except Exception:
        pass

    try:
        card = d.draw()
    except Exception:
        card = None

    # If deck empty and this is the main deck, try to rebuild from discard_pile
    try:
        main_deck = globals().get('deck')
        if card is None and d is main_deck:
            try:
                if 'discard_pile' in globals() and discard_pile:
                    new_cards = []
                    for it in list(discard_pile):
                        try:
                            # (suit, rank) tuple stored in discard_pile
                            if isinstance(it, tuple) and len(it) == 2:
                                new_cards.append(DeckCard(suit=it[0], rank=it[1]))
                            # already a Card-like object
                            elif hasattr(it, 'suit') and hasattr(it, 'rank'):
                                new_cards.append(it)
                        except Exception:
                            pass
                    if new_cards:
                        try:
                            d.cards.extend(new_cards)
                        except Exception:
                            d.cards = list(new_cards)
                        try:
                            discard_pile.clear()
                        except Exception:
                            pass
                        try:
                            d.shuffle()
                        except Exception:
                            try:
                                random.shuffle(d.cards)
                            except Exception:
                                pass
                        try:
                            card = d.draw()
                        except Exception:
                            card = None
            except Exception:
                pass
    except Exception:
        pass

    return card


# Old grey Joker HUD drawing removed. JokerHUD will handle display.


# Old tooltip drawing removed. New HUD will render joker details on hover.


def ensure_hand_filled(_deck=None, _hand=None, target_slots=None):
    """Ensure `_hand` has `target_slots` filled by drawing from `_deck`.

    Places new Card instances into the first available None slots. Returns
    the number of cards drawn. Calls `recalculate_hand_positions()` at the end
    so targets update uniformly.
    """
    global deck, hand, discard_pile, game_state, MAX_HAND_SLOTS
    drawn = 0
    try:
        if _deck is None:
            _deck = deck
        if _hand is None:
            _hand = hand

        try:
            if target_slots is None:
                target_slots = int(MAX_HAND_SLOTS)
        except Exception:
            if target_slots is None:
                target_slots = MAX_HAND_SLOTS

        safety_counter = 0
        # While the visible (non-None) cards are fewer than target, keep drawing
        while len([c for c in _hand if c is not None]) < int(target_slots):
            safety_counter += 1
            if safety_counter > 100:
                try:
                    print("KRİTİK: Kart dağıtımı sonsuz döngüye girdi! Çıkılıyor.")
                except Exception:
                    pass
                break

            # If deck is empty, try to rebuild reliably from discard_pile
            try:
                deck_cards = getattr(_deck, 'cards', None) or []
            except Exception:
                deck_cards = []

            if not deck_cards:
                try:
                    if 'discard_pile' in globals() and discard_pile:
                        try:
                            print("DEBUG: Deste bitti, atılanlar karıştırılıyor...")
                        except Exception:
                            pass
                        try:
                            # simple and reliable reshuffle: copy discarded cards back
                            _deck.cards = list(discard_pile[:])
                        except Exception:
                            try:
                                _deck.cards = discard_pile[:]
                            except Exception:
                                _deck.cards = []
                        try:
                            discard_pile.clear()
                        except Exception:
                            try:
                                globals()['discard_pile'] = []
                            except Exception:
                                pass
                        try:
                            _deck.shuffle()
                        except Exception:
                            try:
                                random.shuffle(_deck.cards)
                            except Exception:
                                pass
                    else:
                        try:
                            print("KRİTİK: Kart kalmadı!")
                        except Exception:
                            pass
                        # No cards to draw -> break out and return what we have
                        break
                except Exception:
                    # on unexpected error, if no cards present end
                    if len([c for c in _hand if c is not None]) == 0:
                        try:
                            globals()['game_state'] = STATE_GAME_OVER
                        except Exception:
                            try:
                                game_state = STATE_GAME_OVER
                            except Exception:
                                pass
                    return drawn

            # Attempt to draw a card
            try:
                card_data = _deck.draw()
            except Exception:
                card_data = None
            if card_data is None:
                # nothing to draw right now
                if len([c for c in _hand if c is not None]) == 0:
                    try:
                        globals()['game_state'] = STATE_GAME_OVER
                    except Exception:
                        try:
                            game_state = STATE_GAME_OVER
                        except Exception:
                            pass
                return drawn

            # Convert drawn data to display Card (sprite)
            try:
                s = getattr(card_data, 'suit', None)
                r = getattr(card_data, 'rank', None)
                img = card_images.get(s, {}).get(r)
                if img is None:
                    img = get_card_image(s, r)
            except Exception:
                s = None
                r = None
                img = get_card_image(None, None)

            # place into first free slot
            placed = False
            for i in range(int(target_slots)):
                if i >= len(_hand):
                    _hand.append(None)
                if _hand[i] is None:
                    nc = Card(img or pygame.Surface((CARD_WIDTH, CARD_HEIGHT)), START_X + (i * CARD_SPACING), NORMAL_Y, r, s)
                    try:
                        maybe_apply_soul_holo(nc)
                    except Exception:
                        pass
                    nc.slot_index = i
                    nc.base_x = START_X + (i * CARD_SPACING)
                    nc.target_x = nc.base_x
                    _hand[i] = nc
                    drawn += 1
                    placed = True
                    break
            if not placed:
                nc = Card(img or pygame.Surface((CARD_WIDTH, CARD_HEIGHT)), START_X, NORMAL_Y, r, s)
                try:
                    maybe_apply_soul_holo(nc)
                except Exception:
                    pass
                _hand.append(nc)
                drawn += 1

        try:
            recalculate_hand_positions()
        except Exception:
            try:
                recompute_ui_layout()
            except Exception:
                pass
    except Exception:
        pass
    return drawn

# 5 kartlık bir el oluşturmak için slotlara kart yerleştir
hand = [None] * MAX_HAND_SLOTS
fill_hand_slots()

# By default do NOT auto-grant the extra card at startup; it should be
# created only when a voucher/joker that grants it is purchased via `buy_item()`.
# Ensure `extra_card` starts as None.
try:
    extra_card = None
except Exception:
    globals()['extra_card'] = None

# Ensure layout variables are computed for the current SCREEN_WIDTH/SCREEN_HEIGHT
try:
    recompute_ui_layout()
except Exception:
    pass

# --- Adım 5: Ana Oyun Döngüsü (Oyunun Sürekli Çalışması) ---
# Copilot'a: "# Pygame ana oyun döngüsünü (main game loop) oluştur"

running = True
while running:
    # Frame timing (ms) and delta seconds
    dt_ms = clock.tick(FPS)
    dt = dt_ms / 1000.0
    # Central event capture for this frame (pull events once and process inline)
    events = pygame.event.get()

    # Her kare başında kilidi temizle (çok önemli — aynı karede birden fazla tıklamayı engelle)
    try:
        globals()['CLICK_LOCKED'] = False
    except Exception:
        try:
            CLICK_LOCKED = False
        except Exception:
            pass

    for event in events:
        # resize and quit are handled immediately
        if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
            handle_resize_event(event)
            continue
        if event.type == pygame.QUIT:
            running = False
            continue

        # Left mouse button released — handle per-state clicks inline
        if event.type == pygame.MOUSEBUTTONUP and getattr(event, 'button', None) == 1:
            try:
                if globals().get('CLICK_LOCKED', False):
                    continue
            except Exception:
                try:
                    if CLICK_LOCKED:
                        continue
                except Exception:
                    pass

            mouse_pos = event.pos

            # --- DURUMA GÖRE İŞLE ---
            if game_state == STATE_MAIN_MENU:
                for button_text, button_rect in list(menu_buttons_data.items()):
                    try:
                        if button_rect.collidepoint(mouse_pos):
                            if button_text == 'OYNA':
                                try:
                                    globals()['CLICK_LOCKED'] = True
                                except Exception:
                                    try:
                                        CLICK_LOCKED = True
                                    except Exception:
                                        pass
                                game_state = STATE_DECK_SELECT
                            elif button_text == 'AYARLAR':
                                try:
                                    game_state = STATE_SETTINGS
                                    globals()['CLICK_LOCKED'] = True
                                except Exception:
                                    pass
                            elif button_text == 'YAPIMCILAR':
                                try:
                                    game_state = STATE_CREDITS
                                    globals()['CLICK_LOCKED'] = True
                                except Exception:
                                    pass
                            elif button_text == 'DESTEK/ÖNERİ':
                                try:
                                    webbrowser.open('mailto:adilbasri06161@gmail.com?subject=DESTEK/ÖNERİ')
                                    try:
                                        globals()['CLICK_LOCKED'] = True
                                    except Exception:
                                        pass
                                except Exception:
                                    print("DESTEK/ÖNERİ tıklandı, mailto entegrasyonu başarısız.")
                            elif button_text == 'ÇIKIŞ':
                                try:
                                    running = False
                                    try:
                                        globals()['CLICK_LOCKED'] = True
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                            break
                    except Exception:
                        pass

            elif game_state == STATE_CREDITS:
                try:
                    if menu_buttons_data.get('GERİ_credits') and menu_buttons_data['GERİ_credits'].collidepoint(mouse_pos):
                        game_state = STATE_MAIN_MENU
                except Exception:
                    pass

            elif game_state == STATE_PLAYING:
                try:
                    # Fate orb click handling on mouse-up: allow the HUD to consume clicks
                    try:
                        if 'fate_hud' in globals() and globals().get('fate_hud'):
                            try:
                                consumed = fate_hud.handle_click(mouse_pos)
                                if consumed:
                                    try:
                                        globals()['CLICK_LOCKED'] = True
                                    except Exception:
                                        pass
                                    # consumed the click; skip other UI handling for this event
                                    continue
                            except Exception:
                                pass
                    except Exception:
                        pass

                    if menu_buttons_data.get('BTN_GAME_MENU') and menu_buttons_data['BTN_GAME_MENU'].collidepoint(mouse_pos):
                        try:
                            reset_game()
                        except Exception:
                            pass
                        game_state = STATE_MAIN_MENU
                except Exception:
                    pass

            elif game_state == STATE_SETTINGS:
                handle_settings_click(mouse_pos)

            elif game_state == STATE_SHOP:
                # Shop click handling may be more complex; keep existing shop logic
                # which may run elsewhere — ignore here to avoid duplicates.
                try:
                    pass
                except Exception:
                    pass

    # --- AYAR GÖZETMENİ (Konum Bilgili) ---
    try:
        target_res = settings_data['resolution']
        target_fullscreen = (settings_data['display_mode'] == 'fullscreen')

        # 1. HEDEF: TAM EKRAN (ve şu an değilsek)
        if target_fullscreen and not current_applied_fullscreen:
            print(f"AYARLAR UYGULANIYOR: {DESKTOP_SIZE} @ NOFRAME (Simulated Fullscreen)")
            
            # Pencereyi sol üste (0,0) konumlandır
            os.environ['SDL_VIDEO_WINDOW_POS'] = '0,0' 
            screen = pygame.display.set_mode(DESKTOP_SIZE, pygame.NOFRAME)
            
            current_applied_res = DESKTOP_SIZE
            current_applied_fullscreen = True
            continue

        # 2. HEDEF: PENCERE (ve şu an değilsek veya çözünürlük değiştiyse)
        elif not target_fullscreen and (current_applied_fullscreen or current_applied_res != target_res):
            print(f"AYARLAR UYGULANIYOR: {target_res} @ RESIZABLE (Windowed)")
            
            # Pencereyi işletim sisteminin ortalamasını iste
            os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'
            screen = pygame.display.set_mode(target_res, pygame.RESIZABLE)
            
            current_applied_res = target_res
            current_applied_fullscreen = False
            continue

    except Exception as e:
        print(f"FELAKET HATA: Ekran ayarı uygulanamadı: {e}")
        # Güvenli moda dön
        os.environ['SDL_VIDEO_WINDOW_POS'] = 'center'
        screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
        settings_data['display_mode'] = 'windowed'
        settings_data['resolution'] = (1280, 720)
        current_applied_res = (1280, 720)
        current_applied_fullscreen = False
    # --- AYAR GÖZETMENİ BİTİŞ ---

    # Clear background each frame (individual states may overdraw)
    screen.fill(BLACK)

    # Top-level menu/state branches
    if game_state == STATE_VIDEO_INTRO:
        # Simplified, robust video / splash handling.
        # Determine whether the player requested a skip this frame.
        skip_now = any((ev.type == pygame.KEYDOWN) or (ev.type == pygame.MOUSEBUTTONUP and getattr(ev, 'button', None) == 1) for ev in events)

        # If skipping, ensure any playing clip is closed and jump to end
        if skip_now:
            try:
                vc = globals().get('video_clip')
                if vc is not None:
                    try:
                        vc.close()
                    except Exception:
                        pass
                globals()['video_clip'] = None
            except Exception:
                globals()['video_clip'] = None
            globals()['current_video_index'] = len(globals().get('VIDEO_PATHS', []))

        # If moviepy isn't available, use a 5s skippable splash image
        if not MOVIEPY_AVAILABLE:
            if globals().get('splash_screen_end_time', 0) == 0:
                # first frame: initialize and warn
                try:
                    print('--- UYARI: VİDEO OYNATILAMADI ---')
                    print("Gerekli 'moviepy' veya 'numpy' kütüphaneleri bulunamadı.")
                    print('Videolar yerine 5 saniyelik açılış görseli gösteriliyor.')
                    print('Yüklemek için: pip install moviepy numpy')
                    print('---------------------------------')
                except Exception:
                    pass
                globals()['splash_screen_end_time'] = pygame.time.get_ticks() + 5000
                # attempt to load fallback image (non-fatal)
                try:
                    fb = pygame.image.load(resource_path('assets/logo_menu.png')).convert_alpha()
                    tw = min(int(SCREEN_WIDTH * 0.5), fb.get_width())
                    th = int(fb.get_height() * (tw / max(1, fb.get_width())))
                    fb = pygame.transform.smoothscale(fb, (tw, th))
                    globals()['splash_fallback_image'] = fb
                except Exception:
                    globals()['splash_fallback_image'] = None

            # Transition to main menu when timer expired (or if skipped)
            if skip_now or (pygame.time.get_ticks() >= globals().get('splash_screen_end_time', 0)):
                globals()['splash_screen_end_time'] = 0
                # Stop entrance track and start main music (looping)
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                try:
                    pygame.mixer.music.load(MAIN_MUSIC_PATH)
                    pygame.mixer.music.play(-1)
                except Exception as e:
                    try:
                        print(f"HATA: Ana Menü müziği başlatılamadı: {e}")
                    except Exception:
                        pass
                game_state = STATE_MAIN_MENU
            else:
                # Draw splash
                screen.fill((0, 0, 0))
                fb = globals().get('splash_fallback_image')
                if fb:
                    try:
                        rect = fb.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                        screen.blit(fb, rect)
                    except Exception:
                        pass
                else:
                    try:
                        txt = game_font.render('Açılış: (tıklayın veya bir tuşa basın atlamak için)', True, WHITE)
                        r = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
                        screen.blit(txt, r)
                    except Exception:
                        pass
        else:
            # moviepy path: attempt to play videos sequentially with guarded errors
            try:
                vc = globals().get('video_clip')
                vid_paths = globals().get('VIDEO_PATHS', [])
                if vc is None:
                    # start next video if any
                    if globals().get('current_video_index', 0) >= len(vid_paths):
                        # Videos finished: stop entrance, load and play main music
                        try:
                            pygame.mixer.music.stop()
                        except Exception:
                            pass
                        try:
                            pygame.mixer.music.load(MAIN_MUSIC_PATH)
                            pygame.mixer.music.play(-1)
                        except Exception as e:
                            try:
                                print(f"HATA: Ana Menü müziği başlatılamadı: {e}")
                            except Exception:
                                pass
                        game_state = STATE_MAIN_MENU
                    else:
                        path = vid_paths[globals().get('current_video_index', 0)]
                        try:
                            vc = VideoFileClip(resource_path(path))
                            globals()['video_clip'] = vc
                            globals()['video_start_ticks'] = pygame.time.get_ticks()
                            try:
                                try:
                                    _ = vc.duration
                                    _ = globals().get('current_video_index', 0)
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        except Exception as e:
                            print(f"HATA: Video yüklenemedi: {path} -> {e}")
                            globals()['current_video_index'] = len(vid_paths)
                else:
                    # render current frame
                    try:
                        start = globals().get('video_start_ticks', pygame.time.get_ticks())
                        t = (pygame.time.get_ticks() - start) / 1000.0
                        if t >= vc.duration:
                            try:
                                vc.close()
                            except Exception:
                                pass
                            globals()['video_clip'] = None
                            globals()['current_video_index'] = globals().get('current_video_index', 0) + 1
                        else:
                            frame = vc.get_frame(t)
                            try:
                                if globals().get('np') is not None:
                                    arr = globals()['np'].asarray(frame)
                                    surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
                                    surf = pygame.transform.scale(surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                                    screen.blit(surf, (0, 0))
                                else:
                                    raise Exception('numpy not available')
                            except Exception:
                                try:
                                    h, w = frame.shape[0], frame.shape[1]
                                    buf = frame.tobytes()
                                    surf = pygame.image.frombuffer(buf, (w, h), 'RGB')
                                    surf = pygame.transform.scale(surf, (SCREEN_WIDTH, SCREEN_HEIGHT))
                                    screen.blit(surf, (0, 0))
                                except Exception:
                                    try:
                                        vc.close()
                                    except Exception:
                                        pass
                                    globals()['video_clip'] = None
                                    globals()['current_video_index'] = len(vid_paths)
                    except Exception:
                        try:
                            vc.close()
                        except Exception:
                            pass
                        globals()['video_clip'] = None
                        globals()['current_video_index'] = len(vid_paths)
            except Exception:
                try:
                    if globals().get('video_clip') is not None:
                        globals()['video_clip'].close()
                except Exception:
                    pass
                globals()['video_clip'] = None
                globals()['current_video_index'] = len(globals().get('VIDEO_PATHS', []))

            # If we've advanced past the last video, go to main menu
            if globals().get('current_video_index', 0) >= len(globals().get('VIDEO_PATHS', [])):
                # Videos finished: ensure entrance stopped and main music starts
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass
                try:
                    pygame.mixer.music.load(MAIN_MUSIC_PATH)
                    pygame.mixer.music.play(-1)
                except Exception as e:
                    try:
                        print(f"HATA: Ana Menü müziği başlatılamadı: {e}")
                    except Exception:
                        pass
                game_state = STATE_MAIN_MENU

    elif game_state == STATE_MAIN_MENU:
        # --- ANA MENÜ ÇİZİMİ BAŞLANGIÇ ---
        screen_width = screen.get_width()
        screen_height = screen.get_height()

        # Logo: ekranın üst-orta kısmında olacak
        # --- Draw decorative hands in the background (before logo/buttons) ---
        try:
            # Bottom-left hand: scale-adjusted placement so fingertips reach toward logo/menu
            if globals().get('hand_bottom_left_img'):
                hb = globals().get('hand_bottom_left_img')
                try:
                    hand_bl_rect = hb.get_rect()
                    # Start with most of the hand off-screen so it feels like it's reaching in
                    hand_bl_rect.bottomleft = (-int(hand_bl_rect.width * 0.4), screen_height + int(hand_bl_rect.height * 0.2))
                    # Nudge the fingertip area toward the center/logo
                    hand_bl_rect.x += int(hand_bl_rect.width * 0.1)
                    hand_bl_rect.y -= int(hand_bl_rect.height * 0.15)
                    screen.blit(hb, hand_bl_rect)
                except Exception:
                    try:
                        screen.blit(hb, (int(SCREEN_WIDTH * 0.05), screen_height - hb.get_height()))
                    except Exception:
                        pass
        except Exception:
            pass

        try:
            # Top-right hand: position so it reaches toward logo/menu center-right
            if globals().get('hand_top_right_img'):
                ht = globals().get('hand_top_right_img')
                try:
                    hand_tr_rect = ht.get_rect()
                    # Most of the hand remains off-screen; it reaches in from the top-right
                    hand_tr_rect.topright = (SCREEN_WIDTH + int(hand_tr_rect.width * 0.4), 0 - int(hand_tr_rect.height * 0.2))
                    # Nudge the fingertip area toward the logo/center
                    hand_tr_rect.x -= int(hand_tr_rect.width * 0.1)
                    hand_tr_rect.y += int(hand_tr_rect.height * 0.15)
                    screen.blit(ht, hand_tr_rect)
                except Exception:
                    try:
                        screen.blit(ht, (SCREEN_WIDTH - ht.get_width(), int(SCREEN_HEIGHT * 0.05)))
                    except Exception:
                        pass
        except Exception:
            pass

        # Logo (draw after hands so logo appears above them)
        if logo_image:
            logo_rect = logo_image.get_rect()
            logo_rect.centerx = screen_width // 2
            # move the logo more aggressively higher to lift the whole menu group upwards
            logo_rect.top = (screen_height // 2) - (logo_rect.height // 2) - 200
            screen.blit(logo_image, logo_rect)

        # Menü butonları: logonun altında dikey olarak ortalanmış
        button_texts = ['OYNA', 'AYARLAR', 'YAPIMCILAR', 'DESTEK/ÖNERİ', 'ÇIKIŞ']
        menu_buttons_data.clear()  # Buton konumlarını her frame yeniden hesapla

        # Düzen parametreleri (daha agresif yer tasarrufu)
        padding_below_logo = 20
        spacing = 3
        # Determine a consistent button height from the small menu font (add small vertical padding)
        try:
            button_height = menu_font_small_menu.get_height() + 6
        except Exception:
            try:
                button_height = menu_font_medium.get_height() + 6
            except Exception:
                button_height = BUTTON_HEIGHT

        # start_y is just below the logo (or a sensible default if logo missing)
        if logo_image:
            start_y = logo_rect.bottom + padding_below_logo
        else:
            start_y = int(screen_height * 0.3)

        # --- Buton Çizimi ve Hover Efekti ---
        mouse_pos = pygame.mouse.get_pos()

        for i, text in enumerate(button_texts):
            center_x = screen_width // 2
            # Each button stacked vertically: use button_height + spacing
            btn_center_y = int(start_y + i * (button_height + spacing) + (button_height // 2))

            # Prepare stored rect (used for click detection) centered at true center
            stored_rect = menu_font_small_menu.render(text, True, WHITE).get_rect()
            stored_rect.center = (center_x, btn_center_y)

            # Determine hover using the stored rect
            is_hovered = stored_rect.collidepoint(mouse_pos)

            color = (255, 255, 255)
            x_offset = 0
            if is_hovered:
                color = (255, 215, 0)
                x_offset = 15

            text_surface = menu_font_small_menu.render(text, True, color)
            text_rect = text_surface.get_rect(center=(center_x + x_offset, btn_center_y))
            screen.blit(text_surface, text_rect)

            # Save click rect without the hover x_offset so clicks are centered
            menu_buttons_data[text] = stored_rect
        # --- Animasyonlu Butonlar Bitiş ---

        # --- TEAM HUSK LOGO (SAĞ ALT) ---
        try:
            if globals().get('team_husk_logo_img'):
                try:
                    husk = globals().get('team_husk_logo_img')
                    husk_rect = husk.get_rect()
                    husk_rect.bottomright = (SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20)
                    # Optional subtle transparency (commented out by default)
                    # try:
                    #     husk.set_alpha(180)
                    # except Exception:
                    #     pass
                    screen.blit(husk, husk_rect)
                except Exception:
                    try:
                        screen.blit(globals().get('team_husk_logo_img'), (SCREEN_WIDTH - 20, SCREEN_HEIGHT - 20))
                    except Exception:
                        pass
        except Exception:
            pass

        # --- ANA MENÜ ÇİZİMİ BİTİŞ ---
    elif game_state == STATE_SETTINGS:
        # --- AYARLAR EKRANI ÇİZİMİ ---
        screen_width = screen.get_width()
        screen_height = screen.get_height()
        
        # "GERİ" butonu (Sol alt köşe)
        geri_text_surface = menu_font.render('GERİ', True, (200, 200, 200))
        geri_rect = geri_text_surface.get_rect(bottomleft=(50, screen_height - 50))
        screen.blit(geri_text_surface, geri_rect)
        menu_buttons_data['GERİ_settings'] = geri_rect

        # --- AYARLAR ---
        start_y = screen_height * 0.2
        
        # 1. Çözünürlük
        res_text = f"Ekran Boyutu: {settings_data['resolution'][0]}x{settings_data['resolution'][1]}"
        res_surface = menu_font.render(res_text, True, WHITE)
        res_rect = res_surface.get_rect(center=(screen_width / 2, start_y))
        screen.blit(res_surface, res_rect)
        menu_buttons_data['BTN_RES'] = res_rect # Tıklama alanı

        # --- Çözünürlük Dropdown Çizimi ---
        if dropdown_active:
            dropdown_x = res_rect.x # Ekran Boyutu metniyle hizalı
            dropdown_y = res_rect.bottom + 5 # Hemen altından başla
            
            for i, res in enumerate(available_resolutions):
                res_text = f"{res[0]}x{res[1]}"
                res_surface = menu_font.render(res_text, True, (150, 150, 150)) # Hafif gri
                res_rect_i = res_surface.get_rect(topleft=(dropdown_x, dropdown_y + (i * 60)))
                
                # Tıklama tespiti için sakla
                menu_buttons_data[f'RES_{i}'] = res_rect_i 
                
                # Eğer bu aktif çözünürlükse, rengini değiştir
                if res == settings_data['resolution']:
                    res_surface = menu_font.render(res_text, True, (0, 255, 0)) # Yeşil
                    
                screen.blit(res_surface, res_rect_i)
        # --- Dropdown Çizimi Bitiş ---

        

        # 3. Müzik Sesi (Görseli)
        # --- Müzik Sesi (Yeni 3 Parçalı Görsel) ---
        volume_y_pos = start_y + 200
        center_x = screen_width / 2

        # 1. Sol Buton: < (Kısma)
        vol_down_surface = menu_font.render('<', True, WHITE)
        vol_down_rect = vol_down_surface.get_rect(center=(center_x - 100, volume_y_pos))
        screen.blit(vol_down_surface, vol_down_rect)
        menu_buttons_data['BTN_VOL_DOWN'] = vol_down_rect # Gerçek tıklama alanı

        # 2. Ortadaki Metin (Sadece Sayı)
        vol_text_surface = menu_font.render(f"{int(settings_data['music_volume'] * 100)}", True, (200, 200, 200)) # Gri renk
        vol_text_rect = vol_text_surface.get_rect(center=(center_x, volume_y_pos))
        screen.blit(vol_text_surface, vol_text_rect)

        # 3. Sağ Buton: > (Artırma)
        vol_up_surface = menu_font.render('>', True, WHITE)
        vol_up_rect = vol_up_surface.get_rect(center=(center_x + 100, volume_y_pos))
        screen.blit(vol_up_surface, vol_up_rect)
        menu_buttons_data['BTN_VOL_UP'] = vol_up_rect # Gerçek tıklama alanı
        # --- Müzik Sesi Bitiş ---

        # 4. Müzik Açık/Kapalı
        music_toggle_text = f"Müzik: {'Açık' if settings_data['music_on'] else 'Kapalı'}"
        music_toggle_surface = menu_font.render(music_toggle_text, True, WHITE)
        music_toggle_rect = music_toggle_surface.get_rect(center=(screen_width / 2, start_y + 300))
        screen.blit(music_toggle_surface, music_toggle_rect)
        menu_buttons_data['BTN_MUSIC_TOGGLE'] = music_toggle_rect

        # 5. Ses Efektleri (SFX)
        sfx_toggle_text = f"Sesler: {'Açık' if settings_data['sfx_on'] else 'Kapalı'}"
        sfx_toggle_surface = menu_font.render(sfx_toggle_text, True, WHITE)
        sfx_toggle_rect = sfx_toggle_surface.get_rect(center=(screen_width / 2, start_y + 400))
        screen.blit(sfx_toggle_surface, sfx_toggle_rect)
        menu_buttons_data['BTN_SFX_TOGGLE'] = sfx_toggle_rect
        
        # --- AYARLAR EKRANI BİTİŞ ---
    elif game_state == STATE_CREDITS:
        # --- YAPIMCILAR EKRANI ÇİZİMİ ---
        screen_width = screen.get_width()
        screen_height = screen.get_height()

        # Metni ortala
        credits_text_surface = menu_font.render('ADİL BASRİ ERDEM', True, WHITE)
        credits_rect = credits_text_surface.get_rect(center=(screen_width / 2, screen_height / 2))
        screen.blit(credits_text_surface, credits_rect)
        
        # "Geri" butonu (Sol alt köşe)
        geri_text_surface = menu_font.render('GERİ', True, (200, 200, 200))
        geri_rect = geri_text_surface.get_rect(bottomleft=(50, screen_height - 50))
        screen.blit(geri_text_surface, geri_rect)
        
        # "Geri" butonunun tıklama alanını sakla
        menu_buttons_data['GERİ_credits'] = geri_rect
        # --- YAPIMCILAR EKRANI BİTİŞ ---

    # GAME LOGIC STATES (playing, shop, deck selection, game over) will run below.
    # Per-state code still runs as before but uses the shared `events` list.
    # Helper functions for computing starting hands and selected deck
    def get_selected_deck_code():
        try:
            sel = globals().get('SELECTED_DECK')
            if not sel:
                return None
            for e in DECK_LIST:
                if str(e.get('name')).strip().lower() == str(sel).strip().lower():
                    return e.get('code')
        except Exception:
            pass
        return None

    def compute_starting_hands(base_hands=None, deck_code=None):
        try:
            b = int(base_hands) if base_hands is not None else int(globals().get('DEFAULT_HANDS', globals().get('INITIAL_HANDS', 4)))
        except Exception:
            b = int(globals().get('INITIAL_HANDS', 4))
        try:
            dc = deck_code or get_selected_deck_code()
            if dc is not None and str(dc).upper() == 'RED':
                b += 1
        except Exception:
            pass
        try:
            for v in globals().get('player_vouchers', []) or []:
                try:
                    if str(v.get('effect_id', '')).upper() == 'INC_HAND_SIZE':
                        b += 1
                except Exception:
                    pass
        except Exception:
            pass
        try:
            for j in globals().get('active_jokers', []) or []:
                try:
                    if str(getattr(j, 'effect_id', '')).upper() == 'INC_HAND_SIZE':
                        b += 1
                except Exception:
                    pass
        except Exception:
            pass
        return int(b)

    # Helper: start a fresh run with deck-specific modifiers
    def start_new_run(deck_type):
        global MONEY, JOKER_SLOTS_MAX, ANTE_TARGET_MODIFIER, SELECTED_DECK_PERK, HOLOPITY_COUNTER
        global game_state, HANDS_REMAINING, DISCARDS_REMAINING, active_jokers
        # Ensure core game state is fully reset first so deck bonuses
        # applied below are not overwritten by reset_game().
        try:
            reset_game()
        except Exception:
            pass

        # Apply deck advantages (must run after reset_game)
        try:
            dt = str(deck_type).upper()
            # compute starting hands using global helper (includes deck + vouchers + jokers)
            try:
                HANDS_REMAINING = compute_starting_hands(base_hands=None, deck_code=dt)
            except Exception:
                if dt == 'RED':
                    try:
                        HANDS_REMAINING = int(HANDS_REMAINING) + 1
                    except Exception:
                        HANDS_REMAINING = 1
                else:
                    HANDS_REMAINING = int(globals().get('DEFAULT_HANDS', globals().get('INITIAL_HANDS', 4)))
            if dt == 'BLUE':
                try:
                    DISCARDS_REMAINING = int(DISCARDS_REMAINING) + 1
                except Exception:
                    DISCARDS_REMAINING = 1
            elif dt == 'GOLD':
                # Give the player 25 Para after reset so it isn't cleared
                MONEY = 25
                try:
                    try:
                        _ = globals().get('MONEY')
                    except Exception:
                        pass
                except Exception:
                    pass
            elif dt == 'GHOST':
                try:
                    JOKER_SLOTS_MAX = int(JOKER_SLOTS_MAX) + 1
                except Exception:
                    JOKER_SLOTS_MAX = globals().get('JOKER_SLOTS_MAX', 5) + 1
            elif dt == 'SOUL':
                SELECTED_DECK_PERK = 'SOUL'
                HOLOPITY_COUNTER = 0
            elif dt == 'CHAOS':
                ANTE_TARGET_MODIFIER = 1.2
                # give one random joker as a simple chaos reward (best-effort)
                try:
                    j = Joker('Rastgele Joker', 'RANDOM', 'Kaos tarafından verilen rastgele joker')
                    try:
                        if len(active_jokers) < globals().get('JOKER_SLOTS_MAX', 5):
                            active_jokers.append(j)
                        else:
                            try:
                                print("UYARI: Joker limiti dolu! Kaos jokeri eklenemedi.")
                            except Exception:
                                pass
                    except Exception:
                        try:
                            active_jokers.append(j)
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

        # Load initial boss/ante and transition to playing state
        try:
            load_boss_for_ante(1)
        except Exception:
            pass
        try:
            game_state = STATE_PLAYING
        except Exception:
            try:
                globals()['game_state'] = STATE_PLAYING
            except Exception:
                pass

    # GAME STATE: DECK SELECTION
    if game_state == STATE_DECK_SELECTION:
        # Initialize persistent deck-selection state in globals if missing
        try:
            if 'current_deck_selection_index' not in globals():
                globals()['current_deck_selection_index'] = 0
            if 'deck_images_loaded' not in globals():
                globals()['deck_images_loaded'] = False
            if 'deck_anim_offset' not in globals():
                globals()['deck_anim_offset'] = 0.0
        except Exception:
            pass

        # Deck definitions (code, display name, mechanic text, filename)
        DECK_LIST = [
            {'code': 'RED', 'name': 'Kırmızı Deste', 'mech': 'Başlangıç el sayısı: +1', 'file': 'deck_red.png'},
            {'code': 'BLUE', 'name': 'Mavi Deste', 'mech': 'Değiştirme hakkı: +1', 'file': 'deck_blue.png'},
            {'code': 'GOLD', 'name': 'Altın Deste', 'mech': 'Başlangıç Para: +25', 'file': 'deck_gold.png'},
            {'code': 'GHOST', 'name': 'Hayalet Deste', 'mech': 'Gizli Joker: 1', 'file': 'deck_ghost.png'},
            {'code': 'SOUL', 'name': 'Ruh Deste', 'mech': 'Holo Garantisi (pity 10)', 'file': 'deck_soul.png'},
            {'code': 'CHAOS', 'name': 'Kaos Deste', 'mech': 'Kaos Modu: Rastgele', 'file': 'deck_chaos.png'},
        ]

        # Load images once
        try:
            if not globals().get('deck_images_loaded'):
                imgs = []
                for entry in DECK_LIST:
                    fname = entry.get('file')
                    path = os.path.join('assets', 'decks', fname)
                    try:
                        im = pygame.image.load(resource_path(path)).convert_alpha()
                    except Exception:
                        # fallback placeholder
                        im = pygame.Surface((240, 160), pygame.SRCALPHA)
                        im.fill((80, 80, 90))
                        try:
                            t = game_font_small.render(str(fname).split('.')[0], True, WHITE)
                            im.blit(t, (10, 10))
                        except Exception:
                            pass
                    imgs.append(im)
                globals()['deck_images'] = imgs
                globals()['deck_images_loaded'] = True
        except Exception:
            pass

        # Input handling
        for event in events:
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.MOUSEMOTION:
                try:
                    joker_hud.update(event.pos, active_jokers)
                except Exception:
                    pass
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                    # keyboard navigation
                    if event.key == pygame.K_RIGHT:
                        globals()['current_deck_selection_index'] = (globals().get('current_deck_selection_index', 0) + 1) % len(DECK_LIST)
                    elif event.key == pygame.K_LEFT:
                        globals()['current_deck_selection_index'] = (globals().get('current_deck_selection_index', 0) - 1) % len(DECK_LIST)
                    elif event.key == pygame.K_RETURN:
                        # emulate click on currently focused deck
                        sel = globals().get('current_deck_selection_index', 0)
                        globals()['deck_click_select'] = sel
                except Exception:
                    pass
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # Check left/right arrow areas
                try:
                    aw = 64
                    ah = 64
                    left_arrow = pygame.Rect(20, SCREEN_HEIGHT//2 - ah//2, aw, ah)
                    right_arrow = pygame.Rect(SCREEN_WIDTH - 20 - aw, SCREEN_HEIGHT//2 - ah//2, aw, ah)
                    if left_arrow.collidepoint((mx, my)):
                        globals()['current_deck_selection_index'] = (globals().get('current_deck_selection_index', 0) - 1) % len(DECK_LIST)
                        continue
                    if right_arrow.collidepoint((mx, my)):
                        globals()['current_deck_selection_index'] = (globals().get('current_deck_selection_index', 0) + 1) % len(DECK_LIST)
                        continue
                except Exception:
                    pass
                # Check click on focused deck image
                try:
                    focus = int(globals().get('current_deck_selection_index', 0))
                    imgs = globals().get('deck_images', [])
                    img = imgs[focus] if focus < len(imgs) else None
                    # compute centered rect for focused image (use scaled size)
                    if img is None:
                        w = int(min(SCREEN_WIDTH * 0.5, 360))
                        h = int(w * 0.66)
                    else:
                        w = int(min(SCREEN_WIDTH * 0.6, img.get_width()))
                        h = int(w * img.get_height() / max(1, img.get_width()))
                    cx = SCREEN_WIDTH // 2
                    cy = SCREEN_HEIGHT // 2 - 30
                    r = pygame.Rect(0, 0, w, h)
                    r.center = (cx, cy)
                    if r.collidepoint((mx, my)):
                        globals()['deck_click_select'] = focus
                except Exception:
                    pass

                # Check select button (may be stored from previous frame in menu_buttons_data)
                try:
                    mbd = globals().get('menu_buttons_data', {})
                    sel_r = mbd.get('BTN_SELECT_DECK')
                    if sel_r and sel_r.collidepoint((mx, my)):
                        # evaluate lock state and start only if unlocked
                        entry = DECK_LIST[int(globals().get('current_deck_selection_index', 0))]
                        deck_key = entry.get('code')
                        unlocked = globals().get('DECK_UNLOCKS', {}).get(deck_key, False)
                        if unlocked:
                            try:
                                start_new_run(deck_key)
                            except Exception:
                                pass
                        # otherwise ignore click (button is disabled)
                except Exception:
                    pass
                

        # If keyboard/propagated selection flag set, process selection
        try:
            sel_idx = globals().pop('deck_click_select', None)
            if sel_idx is not None:
                sel_idx = int(sel_idx) % len(DECK_LIST)
                entry = DECK_LIST[sel_idx]
                deck_code = entry.get('code', 'RED')
                # record selection for session
                try:
                    globals()['SELECTED_DECK'] = entry.get('name')
                    globals()['current_deck_selection_index'] = sel_idx
                except Exception:
                    pass

                # start the run with the selected deck's modifiers
                try:
                    # Only start if deck unlocked
                    unlocked = globals().get('DECK_UNLOCKS', {}).get(deck_code, False)
                    if unlocked:
                        start_new_run(deck_code)
                    else:
                        # locked: ignore selection (button should be disabled)
                        pass
                except Exception:
                    # fallback: ensure we at least reset and go to playing
                    try:
                        reset_game()
                    except Exception:
                        pass
                    try:
                        game_state = STATE_PLAYING
                    except Exception:
                        game_state = STATE_MAIN_MENU
        except Exception:
            pass

        # Drawing
        screen.fill((18, 18, 28))
        screen.blit(background_image, (0, 0))
        try:
            draw_particles(screen)
        except Exception:
            pass
        try:
            draw_particles(screen)
        except Exception:
            pass
        title = game_font.render('DESTE SEÇİN', True, WHITE)
        screen.blit(title, (SCREEN_WIDTH//2 - title.get_width()//2, 48))

        # draw arrows and focused deck only (carousel)
        try:
            aw = 64
            ah = 64
            left_arrow = pygame.Rect(20, SCREEN_HEIGHT//2 - ah//2, aw, ah)
            right_arrow = pygame.Rect(SCREEN_WIDTH - 20 - aw, SCREEN_HEIGHT//2 - ah//2, aw, ah)
            pygame.draw.polygon(screen, (200,200,200), [(left_arrow.right-10, left_arrow.top+10), (left_arrow.left+10, left_arrow.centery), (left_arrow.right-10, left_arrow.bottom-10)])
            pygame.draw.polygon(screen, (200,200,200), [(right_arrow.left+10, right_arrow.top+10), (right_arrow.right-10, right_arrow.centery), (right_arrow.left+10, right_arrow.bottom-10)])
            # register arrow button rects for click handling
            try:
                menu_buttons_data['BTN_ARROW_LEFT'] = left_arrow
                menu_buttons_data['BTN_ARROW_RIGHT'] = right_arrow
            except Exception:
                pass
        except Exception:
            pass

        imgs = globals().get('deck_images', [])
        focus = int(globals().get('current_deck_selection_index', 0))
        entry = DECK_LIST[focus]
        # load focused image (use preloaded imgs if possible)
        try:
            img = imgs[focus] if focus < len(imgs) else None
            if img is None:
                path = os.path.join('assets', 'decks', entry.get('file'))
                try:
                    img = pygame.image.load(resource_path(path)).convert_alpha()
                except Exception:
                    img = None
        except Exception:
            img = None

        # compute scaled size for focused image
        try:
            max_w = int(min(SCREEN_WIDTH * 0.6, 560))
            if img is not None:
                iw = img.get_width()
                ih = img.get_height()
                scale_w = min(max_w, iw)
                target_w = int(scale_w)
                target_h = int(target_w * ih / max(1, iw))
                surf = pygame.transform.smoothscale(img, (target_w, target_h))
            else:
                target_w = int(min(SCREEN_WIDTH * 0.5, 360))
                target_h = int(target_w * 0.66)
                surf = pygame.Surface((target_w, target_h))
                surf.fill((80, 80, 100))
                try:
                    t = game_font_small.render(entry.get('file', ''), True, WHITE)
                    surf.blit(t, (8, 8))
                except Exception:
                    pass
            cx = SCREEN_WIDTH // 2
            cy = SCREEN_HEIGHT // 2 - 30
            r = surf.get_rect(center=(cx, cy))
            screen.blit(surf, r.topleft)
        except Exception:
            try:
                r = pygame.Rect(SCREEN_WIDTH//2 - 160, SCREEN_HEIGHT//2 - 90, 320, 180)
                surf = pygame.Surface((r.width, r.height))
                surf.fill((90,90,100))
                screen.blit(surf, r.topleft)
            except Exception:
                r = pygame.Rect(SCREEN_WIDTH//2 - 160, SCREEN_HEIGHT//2 - 90, 320, 180)

        # Draw focused deck name + mechanic under the image
        try:
            name_s = game_font.render(entry.get('name', ''), True, WHITE)
            mech_s = game_font_small.render(entry.get('mech', ''), True, (200,200,200))
            screen.blit(name_s, (r.centerx - name_s.get_width()//2, r.bottom + 8))
            screen.blit(mech_s, (r.centerx - mech_s.get_width()//2, r.bottom + 12 + name_s.get_height()))
        except Exception:
            pass

        # Draw select button below the mechanic text
        try:
            sel_w = 140
            sel_h = 48
            sel_rect = pygame.Rect(0, 0, sel_w, sel_h)
            sel_rect.centerx = r.centerx
            sel_rect.top = r.bottom + 20 + name_s.get_height() + mech_s.get_height()
            # Check unlock state
            deck_key = entry.get('code')
            unlocked = globals().get('DECK_UNLOCKS', {}).get(deck_key, False)
            if unlocked:
                pygame.draw.rect(screen, (28,160,80), sel_rect, border_radius=8)
                sel_text = game_font_small.render('SEÇ', True, WHITE)
            else:
                # grayed disabled button
                pygame.draw.rect(screen, (90,90,90), sel_rect, border_radius=8)
                sel_text = game_font_small.render('KİLİTLİ', True, (200,200,200))
            screen.blit(sel_text, (sel_rect.centerx - sel_text.get_width()//2, sel_rect.centery - sel_text.get_height()//2))
            try:
                menu_buttons_data['BTN_SELECT_DECK'] = sel_rect
            except Exception:
                pass
        except Exception:
            pass

        # If deck is locked, draw overlay + "KİLİTLİ" label on the deck image
        try:
            deck_key = entry.get('code')
            unlocked = globals().get('DECK_UNLOCKS', {}).get(deck_key, False)
            if not unlocked:
                try:
                    overlay = pygame.Surface((r.width, r.height), pygame.SRCALPHA)
                    overlay.fill((60, 60, 60, 140))
                    screen.blit(overlay, r.topleft)
                    lock_font = pygame.font.SysFont(None, 56)
                    lock_surf = lock_font.render('KİLİTLİ', True, (240,240,240))
                    lock_rect = lock_surf.get_rect(center=r.center)
                    screen.blit(lock_surf, lock_rect.topleft)
                except Exception:
                    pass
        except Exception:
            pass

        # draw joker hud
        try:
            joker_hud.draw(screen, active_jokers)
        except Exception:
            pass
    # GAME STATE: PLAYING
    if game_state == STATE_PLAYING:
        # Ensure background cleared at start of PLAYING state
        try:
            screen.fill((0, 0, 0))
        except Exception:
            try:
                screen.fill(BLACK)
            except Exception:
                pass

        # --- OYUN İÇİ MENÜ BUTONU ÇİZİMİ ---
        try:
            menu_btn_text = menu_font.render("ANA MENÜ", True, (255, 255, 255)) # Saf Beyaz
            menu_btn_rect = menu_btn_text.get_rect(topleft=(20, 20))
            screen.blit(menu_btn_text, menu_btn_rect)
            menu_buttons_data['BTN_GAME_MENU'] = menu_btn_rect # Tıklama alanı saklanıyor
        except Exception:
            pass
        # --- OYNANACAK EL ÖNİZLEMESİ (Nihai Mantık) ---
        if selected_cards and len(selected_cards) > 0:
            hand_result = evaluate_hand(selected_cards)
            hand_key = str(hand_result[0]).upper().replace(' ', '_') if isinstance(hand_result, (list, tuple)) and len(hand_result) > 0 else 'HIGH_CARD'
            preview_text = POKER_HAND_NAMES.get(hand_key, "Tanımlanamayan El")

            # FINAL RENDERING
            preview_font = pygame.font.Font(None, 80)
            text_color = (255, 255, 255)
            if hand_key == 'HIGH_CARD':
                text_color = (150, 150, 150)

            screen_width = screen.get_width()
            text_surface = preview_font.render(preview_text, True, text_color)
            text_rect = text_surface.get_rect(center=(screen_width / 2, 80))
            screen.blit(text_surface, text_rect)
        # Draw Fate Orb HUD (shows player_fate_orbs)
        try:
            if globals().get('fate_orb_hud'):
                try:
                    fate_orb_hud.draw(screen)
                except Exception:
                    pass
        except Exception:
            pass
        # PLAYING state: enemy is created when an ante is started via the SHOP
        # Do not auto-create or reload bosses here to avoid state resets.
        # check banner expiry
        try:
            if boss_banner_active:
                now_b = pygame.time.get_ticks()
                if now_b - boss_banner_start >= BOSS_BANNER_DURATION_MS:
                    boss_banner_active = False
                    boss_banner_image = None
        except Exception:
            pass
        # 1. GİRDİ (Input) KONTROLÜ
        for event in events:
            # handle resize events and fullscreen toggle
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            # If boss banner is active, block most input except resize/quit/fullscreen toggle
            try:
                if boss_banner_active:
                    # allow resize and quit events always
                    if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None), pygame.QUIT):
                        pass
                    elif event.type == pygame.KEYDOWN and getattr(event, 'key', None) == pygame.K_F11:
                        try:
                            toggle_fullscreen()
                        except Exception:
                            pass
                        # do not swallow other input frames
                    else:
                        # previously input was ignored while banner active; allow clicks now
                        pass
            except Exception:
                pass
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                except Exception:
                    pass
            # Pencereyi kapatma tuşuna bastı mı?
            if event.type == pygame.QUIT:
                running = False
                
            # Fareye tıkladı mı?
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Tıkladıysa, önce ekstra karta veya eldeki hangi karta tıkladığını bulalım
                handled = False
                # check extra card first (clickable but not part of hand for discards)
                try:
                    # if right mouse button pressed -> start drag instead of click
                    if getattr(event, 'button', 0) == 3:
                        # begin drag of whole group
                        drag_active = True
                        drag_origin = event.pos
                        for c in hand:
                            if c is None:
                                continue
                            c.drag_base_x = c.rect.x
                            c.drag_base_y = c.rect.y
                        if extra_card is not None:
                            extra_card.drag_base_x = extra_card.rect.x
                            extra_card.drag_base_y = extra_card.rect.y
                        handled = True
                    elif extra_card is not None and extra_card.rect.collidepoint(event.pos):
                        try:
                            extra_card.is_selected = not getattr(extra_card, 'is_selected', False)
                            if getattr(extra_card, 'is_selected', False):
                                try:
                                    extra_card.target_y = SELECTED_Y_POS
                                except Exception:
                                    extra_card.target_y = SELECTED_Y
                            else:
                                try:
                                    extra_card.target_y = NORMAL_Y_POS
                                except Exception:
                                    extra_card.target_y = NORMAL_Y
                        except Exception:
                            try:
                                extra_card.is_selected = True
                            except Exception:
                                pass
                        try:
                            print(f"Ekstra kart tıklandı: {extra_card.rank} - {extra_card.suit}  selected={getattr(extra_card, 'is_selected', False)}")
                        except Exception:
                            pass
                        # play click sound for card click
                        try:
                            if click_sound:
                                play_sound(click_sound)
                        except Exception:
                            pass
                        handled = True
                except Exception:
                    pass

                if not handled:
                    # --- KADER KÜRESİ TIKLAMA ---
                    if 'fate_hud' in globals() and fate_hud:
                        try:
                            if fate_hud.handle_click(event.pos):
                                # Küreye tıklandıysa başka şeye tıklama
                                continue
                        except Exception:
                            pass
                    for card in hand:
                        if card is None:
                            continue
                        # right-click drag start
                        if getattr(event, 'button', 0) == 3 and card.rect.collidepoint(event.pos):
                            drag_active = True
                            drag_origin = event.pos
                            for c in hand:
                                if c is None:
                                    continue
                                c.drag_base_x = c.rect.x
                                c.drag_base_y = c.rect.y
                            if extra_card is not None:
                                extra_card.drag_base_x = extra_card.rect.x
                                extra_card.drag_base_y = extra_card.rect.y
                            handled = True
                            break
                        if card.rect.collidepoint(event.pos):
                            try:
                                card.is_selected = not getattr(card, 'is_selected', False)
                                if getattr(card, 'is_selected', False):
                                    try:
                                        card.target_y = SELECTED_Y_POS
                                    except Exception:
                                        card.target_y = SELECTED_Y
                                else:
                                    try:
                                        card.target_y = NORMAL_Y_POS
                                    except Exception:
                                        card.target_y = NORMAL_Y
                            except Exception:
                                try:
                                    card.is_selected = True
                                except Exception:
                                    pass
                            try:
                                print(f"Kart tıklandı: {card.rank} - {card.suit}  selected={getattr(card, 'is_selected', False)}")
                            except Exception:
                                pass
                            # play click sound for card click
                            try:
                                if click_sound:
                                    play_sound(click_sound)
                            except Exception:
                                pass
                            handled = True
                            break # Bir kartı bulduktan sonra aramayı durdur

                # Eğer kartlardan hiçbiri tıklanmamışsa, butonu kontrol et
                if not handled:
                    # Önce 'Kart Değiştir' butonunu kontrol et
                    if discard_button_rect.collidepoint(event.pos):
                        # (Legacy NO_DISCARDS removed) rely on DISCARDS_REMAINING value only
                        # play click sound for button
                        try:
                            if click_sound:
                                play_sound(click_sound)
                        except Exception:
                            pass
                        # trigger small press animation for discard image/button
                        try:
                            discard_button_pressed = True
                            discard_button_pressed_time = pygame.time.get_ticks()
                        except Exception:
                            pass
                        # Eğer hakkı varsa işlem yap
                        if DISCARDS_REMAINING > 0:
                            # Seçili kartları topla (hand içindekiler)
                            selected_cards = [c for c in hand if c is not None and c.is_selected]
                            # Eğer ekstra kart seçiliyse, dahil et (özel davranışla)
                            extra_selected = False
                            try:
                                if extra_card is not None and getattr(extra_card, 'is_selected', False):
                                    extra_selected = True
                            except Exception:
                                extra_selected = False

                            if not selected_cards and not extra_selected:
                                print("Kart Değiştir tıklandı ama seçili kart yok.")
                                continue

                            # Bir adet discard hakkı kullan
                            DISCARDS_REMAINING -= 1
                            print(f"Kart Değiştirildi. Kalan değişiklik hakkı: {DISCARDS_REMAINING}")

                            # Yeni kartları çek
                            new_cards = []
                            # draw replacements for cards from hand
                            for _ in range(len(selected_cards)):
                                new_card_data = safe_draw()
                                if new_card_data is None:
                                    break
                                s = new_card_data.suit
                                r = new_card_data.rank
                                img = card_images.get(s, {}).get(r)
                                if img is None:
                                    img = get_card_image(s, r)
                                # create with temporary x; will position into free slot below
                                tmpc = Card(img, 0, NORMAL_Y, r, s)
                                try:
                                    maybe_apply_soul_holo(tmpc)
                                except Exception:
                                    pass
                                new_cards.append(tmpc)
                            # if extra card was selected, replace its content from deck (slot persists)
                            if extra_selected:
                                try:
                                    new_extra = safe_draw()
                                    if new_extra is not None:
                                        s_e = new_extra.suit
                                        r_e = new_extra.rank
                                        img_e = card_images.get(s_e, {}).get(r_e)
                                        if img_e is None:
                                            img_e = get_card_image(s_e, r_e)
                                        try:
                                            # move the old extra card to discard pile before replacing
                                            if 'discard_pile' in globals() and extra_card is not None:
                                                discard_pile.append((extra_card.suit, extra_card.rank))
                                        except Exception:
                                            pass
                                        extra_card = Card(img_e, EXTRA_SLOT_X, NORMAL_Y, r_e, s_e)
                                        try:
                                            maybe_apply_soul_holo(extra_card)
                                        except Exception:
                                            pass
                                        # ensure not selected after replace
                                        extra_card.is_selected = False
                                except Exception:
                                    pass

                            # Eski seçili kartları slotlarından çıkar (slot becomes free)
                            for sc in selected_cards:
                                try:
                                    si = getattr(sc, 'slot_index', None)
                                    if si is not None and 0 <= si < MAX_HAND_SLOTS:
                                        try:
                                            if 'discard_pile' in globals():
                                                discard_pile.append((sc.suit, sc.rank))
                                        except Exception:
                                            pass
                                        hand[si] = None
                                except Exception:
                                    pass

                            # After removing cards, recalculate positions so remaining cards shift correctly
                            try:
                                recalculate_hand_positions()
                            except Exception:
                                pass

                            # Yeni kartları boş slotlara yerleştir
                            for new_card in new_cards:
                                placed = False
                                for i in range(MAX_HAND_SLOTS):
                                    if hand[i] is None:
                                        new_card.slot_index = i
                                        # place at slot x (will animate into target)
                                        new_card.base_x = START_X + (i * CARD_SPACING)
                                        new_card.target_x = new_card.base_x
                                        hand[i] = new_card
                                        placed = True
                                        break
                                if not placed:
                                    # no free slot (shouldn't happen) -> append to first slot
                                    new_card.slot_index = 0
                                    hand[0] = new_card

                            # Enforce minimum hand size: draw from deck until we have MAX_HAND_SLOTS visible cards
                            try:
                                cur_non_none = len([c for c in hand if c is not None])
                                cards_to_draw = max(0, MAX_HAND_SLOTS - cur_non_none)
                                for _ in range(cards_to_draw):
                                    nd = safe_draw()
                                    if nd is None:
                                        break
                                    s = nd.suit
                                    r = nd.rank
                                    img = card_images.get(s, {}).get(r)
                                    if img is None:
                                        img = get_card_image(s, r)
                                    nc = Card(img, 0, NORMAL_Y, r, s)
                                    try:
                                        maybe_apply_soul_holo(nc)
                                    except Exception:
                                        pass
                                    # place into first free slot
                                    placed = False
                                    for i in range(MAX_HAND_SLOTS):
                                        if i >= len(hand):
                                            hand.append(None)
                                        if hand[i] is None:
                                            nc.slot_index = i
                                            nc.base_x = START_X + (i * CARD_SPACING)
                                            nc.target_x = nc.base_x
                                            hand[i] = nc
                                            placed = True
                                            break
                                    if not placed:
                                        hand.append(nc)
                            except Exception:
                                pass

                            # Pozisyonları yeniden hesapla ve seçimleri sıfırla for existing cards
                            # Recompute layout so START_X matches current hand size
                            try:
                                recompute_ui_layout()
                            except Exception:
                                pass
                            for i, card in enumerate(hand):
                                if card is None:
                                    continue
                                nx = START_X + (i * CARD_SPACING)
                                card.base_x = nx
                                card.target_x = nx
                                # Debug: log when selections are cleared during refill
                                try:
                                    if getattr(card, 'is_selected', False):
                                        pass
                                except Exception:
                                    pass
                                card.is_selected = False
                            # Clear hovered_card so any lift/hover effect from a removed
                            # or replaced card does not persist after a discard operation.
                            try:
                                hovered_card = None
                            except Exception:
                                pass
                            # update extra card target x to fixed slot (do not change base_x)
                            try:
                                if extra_card is not None:
                                    extra_card.target_x = EXTRA_SLOT_X
                            except Exception:
                                pass

                            # After discarding/replacing, ensure hand is filled up to MAX_HAND_SLOTS.
                            # This should happen here (discard does not consume a hand turn).
                            try:
                                fill_hand_slots()
                            except Exception:
                                pass

                            # Eğer discard hakkı kalmadıysa bilgi ver
                            if DISCARDS_REMAINING == 0:
                                print("Tüm kart değiştirme hakları kullanıldı. 'Kart Değiştir' devre dışı.")
                        else:
                            print("Kart Değiştirme hakkı kalmadı.")
                        continue
                    if button_rect.collidepoint(event.pos):
                        # Safety reset: clear stuck locks so a second click still works
                        try:
                            cards_locked = False
                            is_hand_processing = False
                        except Exception:
                            pass

                        # play click sound for button
                        try:
                            if click_sound:
                                play_sound(click_sound)
                        except Exception:
                            pass
                        # Butona tıklandı: görsel geri bildirim için basıldı zamanını kaydet
                        button_pressed = True
                        button_pressed_time = pygame.time.get_ticks()
                        try:
                            play_button_pressed = True
                            play_button_pressed_time = pygame.time.get_ticks()
                        except Exception:
                            pass

                        # Mark that hand processing is in-progress to prevent re-entrancy
                        try:
                            is_hand_processing = True
                            cards_locked = True
                        except Exception:
                            pass

                        # Ensure processing cleanup always runs (covers early continues/exceptions)
                        # Include selected extra_card (if any) in selected_cards for play
                        selected_cards = [c for c in hand if c is not None and c.is_selected]
                        if extra_card is not None and getattr(extra_card, 'is_selected', False):
                            selected_cards.append(extra_card)
                        # Eğer seçili kart yoksa, hiçbir işlem yapmadan olay işleyicisinden çık
                        if len(selected_cards) == 0:
                            print("Buton tıklandı ama seçili kart yok.")
                            try:
                                is_hand_processing = False
                                cards_locked = False
                            except Exception:
                                pass
                            continue

                        # (Removed old boss rule that blocked plays containing spades.)

                        # Additional boss ability validations (based on current_boss_ability)
                        try:
                            ab = globals().get('current_boss_ability')
                        except Exception:
                            ab = None

                        try:
                            # ALPHA_RULE: require at least 3 selected cards
                            if ab == 'ALPHA_RULE' and len(selected_cards) < 3:
                                invalid_message = 'Bu boss için en az 3 kart oynamalısın.'
                                invalid_message_time = pygame.time.get_ticks()
                                try:
                                    if click_sound:
                                        play_sound(click_sound)
                                except Exception:
                                    pass
                                is_hand_processing = False
                                cards_locked = False
                                continue

                            # PECKING: the lowest-value card in hand must be included in selected_cards
                            if ab == 'PECKING':
                                try:
                                    visible = [c for c in hand if c is not None]
                                    if extra_card is not None:
                                        visible.append(extra_card)
                                    # compute lowest by rank value
                                    min_card = None
                                    min_val = None
                                    for c in visible:
                                        v = get_rank_value(getattr(c, 'rank', None))
                                        if v is None:
                                            continue
                                        if min_val is None or v < min_val:
                                            min_val = v
                                            min_card = c
                                    # check presence by rank+suit to avoid identity mismatch
                                    if min_card is not None:
                                        found = False
                                        for sc in selected_cards:
                                            try:
                                                if getattr(sc, 'rank', None) == getattr(min_card, 'rank', None) and getattr(sc, 'suit', None) == getattr(min_card, 'suit', None):
                                                    found = True
                                                    break
                                            except Exception:
                                                pass
                                        if not found:
                                            invalid_message = 'En düşük kart oynanmalı (PECKING).'
                                            invalid_message_time = pygame.time.get_ticks()
                                            try:
                                                if click_sound:
                                                    play_sound(click_sound)
                                            except Exception:
                                                pass
                                            is_hand_processing = False
                                            cards_locked = False
                                            continue
                                except Exception:
                                    pass

                            # NO_HIGH_CARDS_HELD: remaining (unplayed) cards cannot contain K or A
                            # BUT: if a remaining high card is unplayable due to other rules
                            # (e.g., DEBUFF_SPADES forbids spades), ignore it for this check.
                            if ab == 'NO_HIGH_CARDS_HELD':
                                try:
                                    remaining = [c for c in hand if c is not None and c not in selected_cards]
                                    try:
                                        if extra_card is not None and (not getattr(extra_card, 'is_selected', False)):
                                            remaining.append(extra_card)
                                    except Exception:
                                        pass

                                    # Helper: determine whether a single card would have been playable
                                    def _card_playable(card):
                                        try:
                                            # Previous logic blocked spades under a boss debuff; that rule
                                            # has been removed. All cards are considered playable here
                                            # for this check.
                                            return True
                                        except Exception:
                                            return True

                                    bad = False
                                    for rc in remaining:
                                        rv = get_rank_value(getattr(rc, 'rank', None))
                                        if rv is not None and rv >= 13:
                                            # Only count this as a violation if the high card
                                            # would have been playable under other rules.
                                            if _card_playable(rc):
                                                bad = True
                                                break
                                    if bad:
                                        invalid_message = 'Elde K/A kalmamalı.'
                                        invalid_message_time = pygame.time.get_ticks()
                                        try:
                                            if click_sound:
                                                play_sound(click_sound)
                                        except Exception:
                                            pass
                                        is_hand_processing = False
                                        cards_locked = False
                                        continue
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        result = evaluate_hand(selected_cards)
                        print(f"El değerlendirme sonucu: {result}")
                        # Calculate score (may be modified by active jokers)
                        def calculate_score(selected_cards, result_name):
                            """Return the points for the played hand using a chips x multiplier model.

                            Returns an integer number of points to add to current_score.
                            """
                            # Support both new-style evaluate_hand result tuples and legacy string names.
                            # If evaluate_hand returns (KEY, base_chips, base_mult) use it directly.
                            result_key = None
                            display_name = None
                            base_chips = None
                            base_mult = None

                            # If new-style (tuple/list)
                            if isinstance(result_name, (list, tuple)) and len(result_name) >= 1:
                                try:
                                    result_key = str(result_name[0]).upper()
                                except Exception:
                                    result_key = None
                                if len(result_name) >= 3:
                                    try:
                                        base_chips = int(result_name[1])
                                    except Exception:
                                        base_chips = None
                                    try:
                                        base_mult = float(result_name[2])
                                    except Exception:
                                        base_mult = None

                            # If legacy string (e.g. 'Per', 'Full House')
                            if isinstance(result_name, str):
                                display_name = result_name

                            # Reverse mapping for display->key (covers POKER_HAND_NAMES values)
                            try:
                                rev_map = {v: k for k, v in POKER_HAND_NAMES.items()}
                            except Exception:
                                rev_map = {}

                            # Compatibility map for previous Turkish/english labels used in code
                            compat_map = {
                                'Per': 'PAIR',
                                'Döper': 'TWO_PAIR',
                                'Üçlü': 'THREE_OF_A_KIND',
                                'Kent': 'STRAIGHT',
                                'Kare': 'FOUR_OF_A_KIND',
                                'High Card': 'HIGH_CARD',
                                'Full House': 'FULL_HOUSE',
                                'Flush': 'FLUSH',
                                'Straight Flush': 'STRAIGHT_FLUSH',
                                'Royal Flush': 'ROYAL_FLUSH'
                            }

                            if result_key is None and isinstance(display_name, str):
                                # try compat map first
                                result_key = compat_map.get(display_name)
                                if result_key is None:
                                    result_key = rev_map.get(display_name)

                            # reward table keyed by standardized keys (same values as evaluate_hand)
                            reward_table = {
                                'HIGH_CARD': (5, 1),
                                'PAIR': (10, 2),
                                'TWO_PAIR': (20, 3),
                                'THREE_OF_A_KIND': (30, 4),
                                'STRAIGHT': (40, 5),
                                'FLUSH': (50, 5),
                                'FLUSH_FIVE': (70, 7),
                                'FULL_HOUSE': (60, 6),
                                'FOUR_OF_A_KIND': (80, 8),
                                'STRAIGHT_FLUSH': (120, 10),
                                'ROYAL_FLUSH': (200, 12),
                                'FIVE_OF_A_KIND': (250, 15),
                            }

                            # If we still don't have base_chips/base_mult, try to derive them
                            if base_chips is None or base_mult is None:
                                if result_key and result_key in reward_table:
                                    base_chips, base_mult = reward_table[result_key]
                                elif isinstance(display_name, str):
                                    # legacy lookup table (old labels)
                                    table = {
                                        'High Card': (5, 1),
                                        'Per': (10, 2),
                                        'Döper': (20, 3),
                                        'Üçlü': (30, 4),
                                        'Kent': (40, 5),
                                        'Flush': (50, 5),
                                        'Full House': (60, 6),
                                        'Kare': (80, 8),
                                        'Straight Flush': (120, 10),
                                        'Royal Flush': (200, 12)
                                    }
                                    base_chips, base_mult = table.get(display_name, (0, 1))
                                else:
                                    base_chips, base_mult = (0, 1)

                            # Compute display_name from result_key for compatibility checks and PLANET_LEVELS lookup
                            if result_key and result_key in POKER_HAND_NAMES:
                                display_name = POKER_HAND_NAMES.get(result_key)
                            if display_name is None and isinstance(result_name, str):
                                display_name = result_name

                            # Apply planet levels: scale base chips and multiplier by current planet level
                            level = PLANET_LEVELS.get(display_name, 1)
                            total_chips = int(base_chips * level)
                            total_mult = base_mult * level
                            # jokers_to_remove = []  # removed: jokers are persistent now

                            try:
                                disabled_idx = int(globals().get('disabled_joker_index', -1))
                            except Exception:
                                disabled_idx = -1
                            for jk_idx, jk in enumerate(list(active_jokers)):
                                # If this joker is disabled by boss (JOKER_ENVY), skip its effect
                                try:
                                    if jk_idx == disabled_idx:
                                        continue
                                except Exception:
                                    pass
                                try:
                                    # Maça çarpanı: eğer elde herhangi bir maça varsa +4 ekle (bir kere el için)
                                    if jk.effect_id == 'ADD_MULTIPLIER_SPADES':
                                        for sc in selected_cards:
                                            if getattr(sc, 'suit', None) == 'spades':
                                                total_mult += 4
                                                print('Joker etkisi uygulandı! (ADD_MULTIPLIER_SPADES)')
                                                break

                                    # Per güçlendirici: eğer el tipi 'Per' ise +4
                                    elif jk.effect_id == 'PER_GUCLENDIRICI':
                                        if result_name == 'Per':
                                            total_mult += 4
                                            print('Joker etkisi uygulandı! (PER_GUCLENDIRICI)')

                                    # Kare uzmanı: eğer el tipi 'Kare' ise +6
                                    elif jk.effect_id == 'KARE_UZMANI':
                                        if result_name == 'Kare':
                                            total_mult += 6
                                            print('Joker etkisi uygulandı! (KARE_UZMANI)')

                                    # Backward-compatible MULTIPLY_SPADES (multiplicative)
                                    elif jk.effect_id == 'MULTIPLY_SPADES':
                                        for sc in selected_cards:
                                            if getattr(sc, 'suit', None) == 'spades':
                                                total_mult *= 1.5
                                                print('Joker etkisi uygulandı! (MULTIPLY_SPADES)')
                                                break

                                    # PLUS_4_MULTIPLIER_IF_PER: eski id (ilişkili) — yine Per için +4
                                    elif jk.effect_id == 'PLUS_4_MULTIPLIER_IF_PER':
                                        if result_name == 'Per':
                                            total_mult += 4
                                            print('Joker etkisi uygulandı! (PLUS_4_MULTIPLIER_IF_PER)')

                                    # --- New joker effects added: COLLECTOR, SPADE_ACE, RED_KING, MINIMALIST, TIMER_DECAY ---
                                    elif jk.effect_id == 'COLLECTOR_MONEY_MULT':
                                        try:
                                            money = int(globals().get('MONEY', 0))
                                            add_mult = int(money // 10)
                                            if add_mult:
                                                total_mult += add_mult
                                                print(f'Joker etkisi uygulandı! (COLLECTOR_MONEY_MULT) +{add_mult} mult')
                                        except Exception:
                                            pass

                                    elif jk.effect_id == 'SPADE_ACE_CHIP':
                                        try:
                                            for sc in selected_cards:
                                                if getattr(sc, 'suit', None) == 'spades':
                                                    total_chips += 3
                                                    print('Joker etkisi uygulandı! (SPADE_ACE_CHIP) +3 chips for a spade')
                                        except Exception:
                                            pass

                                    elif jk.effect_id == 'RED_KING_MULT':
                                        try:
                                            for sc in selected_cards:
                                                if getattr(sc, 'suit', None) in ('hearts', 'diamonds'):
                                                    total_mult += 2
                                                    print('Joker etkisi uygulandı! (RED_KING_MULT) +2 mult for red suit')
                                        except Exception:
                                            pass

                                    elif jk.effect_id == 'MINIMALIST_HAND_X3':
                                        try:
                                            if isinstance(selected_cards, (list, tuple)) and len(selected_cards) == 3:
                                                # Multiply the multiplier so final total is x3
                                                total_mult = float(total_mult) * 3
                                                print('Joker etkisi uygulandı! (MINIMALIST_HAND_X3) x3 multiplier')
                                        except Exception:
                                            pass

                                    elif jk.effect_id == 'TIMER_DECAY_MULT':
                                        try:
                                            # Ensure the joker has a starting bonus_value; default 20
                                            if not hasattr(jk, 'bonus_value') or jk.bonus_value is None:
                                                try:
                                                    jk.bonus_value = 20
                                                except Exception:
                                                    pass
                                            bv = int(getattr(jk, 'bonus_value', 20))
                                            total_mult += bv
                                            print(f'Joker etkisi uygulandı! (TIMER_DECAY_MULT) +{bv} mult (will decay after hand)')
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                            # end jokers loop

                            # Edition bonuses: Foil gives flat chips, Holo gives extra multiplier
                            try:
                                for sc in selected_cards:
                                    try:
                                        if getattr(sc, 'edition', None) == 'Foil':
                                            total_chips += 50
                                        elif getattr(sc, 'edition', None) == 'Holo':
                                            total_mult += 10
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                            # --- Fate orb active rules: check active_fate_rules and apply effects ---
                            try:
                                afr = globals().get('active_fate_rules', []) or []
                                # gather rank values and suits once
                                ranks = [get_rank_value(getattr(sc, 'rank', None)) for sc in selected_cards]
                                suits = [getattr(sc, 'suit', None) for sc in selected_cards]

                                # CURSED_7: if any played card is rank 7, multiply total_mult by 7 and reduce discards
                                if 'CURSED_7' in afr:
                                    try:
                                        if any((r == 7) for r in ranks if r is not None):
                                            total_mult = float(total_mult) * 7
                                            try:
                                                globals()['DISCARDS_REMAINING'] = max(0, int(globals().get('DISCARDS_REMAINING', 0)) - 1)
                                            except Exception:
                                                pass
                                            print('Fate rule CURSED_7 applied: x7 multiplier and -1 discard')
                                    except Exception:
                                        pass

                                # ACE_KING_BOND: if both Ace(14) and King(13) present, multiply by 4
                                if 'ACE_KING_BOND' in afr:
                                    try:
                                        has_ace = any((r == 14) for r in ranks if r is not None)
                                        has_king = any((r == 13) for r in ranks if r is not None)
                                        if has_ace and has_king:
                                            total_mult = float(total_mult) * 4
                                            print('Fate rule ACE_KING_BOND applied: x4 multiplier')
                                    except Exception:
                                        pass

                                # BLOOD_DIAMOND: +50 chips per diamond played and -1$ per diamond
                                if 'BLOOD_DIAMOND' in afr:
                                    try:
                                        diamond_count = sum(1 for s in suits if str(s).lower() == 'diamonds')
                                        if diamond_count > 0:
                                            try:
                                                total_chips += 50 * int(diamond_count)
                                            except Exception:
                                                pass
                                            try:
                                                # subtract money per diamond (may go negative)
                                                globals()['MONEY'] = int(globals().get('MONEY', 0)) - int(diamond_count)
                                            except Exception:
                                                pass
                                            print(f'Fate rule BLOOD_DIAMOND applied: +{50*diamond_count} chips, -{diamond_count}$')
                                    except Exception:
                                        pass
                            except Exception:
                                pass

                            # Compute final chips x multiplier
                            try:
                                # If any card in the played set has a Red seal, double the multiplier
                                has_red_seal = any(getattr(sc, 'seal', None) == 'Red' for sc in selected_cards)
                            except Exception:
                                has_red_seal = False

                            try:
                                applied_multiplier = float(total_mult)
                                if has_red_seal:
                                    applied_multiplier = applied_multiplier * 2
                                total = int(total_chips * applied_multiplier)
                            except Exception:
                                total = 0

                            # Return total points, the base chips, and the applied multiplier
                            return total, total_chips, applied_multiplier

                        # Initialize score_to_add to 0 for safety, then compute
                        score_to_add = 0
                        # Apply MONEY_TAX boss ability immediately before score calculation
                        try:
                            if globals().get('current_boss_ability') == 'MONEY_TAX':
                                try:
                                    globals()['MONEY'] = max(0, int(globals().get('MONEY', 0)) - 1)
                                    print('Boss MONEY_TAX applied: -1$')
                                    try:
                                        try:
                                            _ = globals().get('MONEY')
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        calc = calculate_score(selected_cards, result)
                        try:
                            score_to_add, total_chips_gained, total_multiplier_applied = calc
                        except Exception:
                            # backward-compat fallback if function returned single value
                            score_to_add = calc if isinstance(calc, int) else int(calc)
                            total_chips_gained = int(score_to_add)
                            total_multiplier_applied = 1

                        # Debug before applying score: show current, to-add, and current splash group size
                        try:
                            try:
                                _ = (current_score, score_to_add, len(scores_splash_group))
                            except Exception:
                                pass
                        except Exception:
                            pass

                        current_score += score_to_add
                        # Recalculate hand positions now that cards will be removed/updated
                        try:
                            recalculate_hand_positions()
                        except Exception:
                            pass
                        # Apply post-score boss effects
                        try:
                            ab_post = globals().get('current_boss_ability')
                            if ab_post == 'RECOIL_DAMAGE':
                                try:
                                    current_score = max(0, int(current_score) - 10)
                                except Exception:
                                    pass
                            if ab_post == 'DESPAIR':
                                try:
                                    DISCARDS_REMAINING = max(0, int(DISCARDS_REMAINING) - 1)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # TIMER_DECAY_MULT jokerleri: her el sonrası bonus değeri 1 azalır (0'a kadar)
                        try:
                            for jk in list(globals().get('active_jokers', [])):
                                try:
                                    eid = getattr(jk, 'effect_id', None) or getattr(jk, 'effect_key', None)
                                    if eid == 'TIMER_DECAY_MULT':
                                        # Eğer bonus_value yoksa, başlat (safeguard)
                                        if not hasattr(jk, 'bonus_value') or jk.bonus_value is None:
                                            try:
                                                jk.bonus_value = 20
                                            except Exception:
                                                setattr(jk, 'bonus_value', 20)
                                        try:
                                            if getattr(jk, 'bonus_value', 0) > 0:
                                                jk.bonus_value = int(jk.bonus_value) - 1
                                                # optional: log the decay for debugging
                                                try:
                                                    print(f"TIMER_DECAY_MULT jokeri azaldı: yeni bonus={jk.bonus_value}")
                                                except Exception:
                                                    pass
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                        except Exception:
                            pass
                        print(f"Puan eklendi: {score_to_add} -> current_score={current_score}")
                        # play score sound when player gains points
                        try:
                            if score_to_add and score_sound:
                                play_sound(score_sound)
                        except Exception:
                            pass

                        # --- SCORE SPLASH TETİKLEME ---
                        try:
                            # Position the splash above the played cards if available
                            try:
                                if 'selected_cards' in locals() and selected_cards and len(selected_cards) > 0:
                                    avg_x = sum(getattr(c.rect, 'centerx', (getattr(c.rect, 'x', 0) + CARD_WIDTH // 2)) for c in selected_cards) / len(selected_cards)
                                    top_y = min(getattr(c.rect, 'y', 0) for c in selected_cards)
                                    splash_x = avg_x
                                    # Position splash relative to card height so it stays aligned
                                    try:
                                        splash_y = top_y - int(CARD_HEIGHT * 0.6)
                                    except Exception:
                                        splash_y = top_y - 70
                                else:
                                    splash_x = screen.get_width() / 2
                                    splash_y = screen.get_height() / 2 - 50
                            except Exception:
                                splash_x = screen.get_width() / 2
                                splash_y = screen.get_height() / 2 - 50

                            # Fişleri fırlat (kazanılan nihai puan miktarı)
                            splash_chips = ScoreSplash(f"+{score_to_add} Puan!", splash_x - 50, splash_y, (255, 215, 0))
                            scores_splash_group.add(splash_chips)
                            try:
                                _ = len(scores_splash_group)
                            except Exception:
                                pass

                            # Çarpanı fırlat (uygulanan çarpan değeri)
                            mult_val = int(total_multiplier_applied) if total_multiplier_applied is not None else 1
                            splash_mult = ScoreSplash(f"x{mult_val} Çarpan!", splash_x + 50, splash_y + int(CARD_HEIGHT * 0.2), (255, 100, 100))
                            scores_splash_group.add(splash_mult)
                            try:
                                _ = len(scores_splash_group)
                            except Exception:
                                pass
                        except Exception:
                            pass
                        # --- SPLASH BİTİŞ ---

                        # After splash spawn debug: report score and splash group size
                        try:
                            try:
                                _ = (current_score, len(scores_splash_group))
                            except Exception:
                                pass
                        except Exception:
                            pass

                        # Apply the earned score as damage to the current Enemy instance.
                        # If an Enemy doesn't exist yet, create one so damage can be applied.
                        try:
                            damage = int(score_to_add) if score_to_add is not None else 0
                            if damage > 0 and enemy is not None:
                                try:
                                    enemy.take_damage(damage)
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        # Oynanan kartları slotlarından çıkar (sadece 'hand' içindekiler)
                        # and determine how many replacements are needed
                        replacement_needed = 0
                        for sc in selected_cards:
                            if sc is None:
                                continue
                            si = getattr(sc, 'slot_index', None)
                            if si is not None and 0 <= si < MAX_HAND_SLOTS and hand[si] is sc:
                                try:
                                    if 'discard_pile' in globals():
                                        discard_pile.append((sc.suit, sc.rank))
                                except Exception:
                                    pass
                                hand[si] = None
                                replacement_needed += 1

                        # If extra_card was used (selected), replace its card from deck (slot persists)
                        try:
                            if extra_card is not None and getattr(extra_card, 'is_selected', False):
                                new_extra_data = safe_draw()
                                if new_extra_data is not None:
                                    s_e = new_extra_data.suit
                                    r_e = new_extra_data.rank
                                    img_e = card_images[s_e][r_e]
                                    # replace the content but keep the extra slot fixed
                                    extra_card = Card(img_e, EXTRA_SLOT_X, NORMAL_Y, r_e, s_e)
                                    try:
                                        maybe_apply_soul_holo(extra_card)
                                    except Exception:
                                        pass
                                    try:
                                        maybe_apply_soul_holo(extra_card)
                                    except Exception:
                                        pass
                                else:
                                    # if deck empty, keep the old extra card
                                    pass
                        except Exception:
                            pass

                        # Desteden replacement_needed yeni kart çek ve boş slotlara yerleştir
                        for _ in range(replacement_needed):
                            new_card_data = safe_draw()
                            if new_card_data is None:
                                break
                            s = new_card_data.suit
                            r = new_card_data.rank
                            img = card_images.get(s, {}).get(r)
                            if img is None:
                                img = get_card_image(s, r)
                            new_card = Card(img, 0, NORMAL_Y, r, s)
                            try:
                                maybe_apply_soul_holo(new_card)
                            except Exception:
                                pass
                            # place into first free slot
                            placed = False
                            for i in range(MAX_HAND_SLOTS):
                                if hand[i] is None:
                                    new_card.slot_index = i
                                    new_card.base_x = START_X + (i * CARD_SPACING)
                                    new_card.target_x = new_card.base_x
                                    hand[i] = new_card
                                    placed = True
                                    break
                            if not placed:
                                # fallback - overwrite first slot
                                new_card.slot_index = 0
                                new_card.base_x = START_X
                                new_card.target_x = START_X
                                hand[0] = new_card

                        # Enforce minimum hand size: if there are fewer than MAX_HAND_SLOTS visible
                        # cards, draw the difference from the deck and place into empty slots.
                        try:
                            cur_non_none = len([c for c in hand if c is not None])
                            cards_to_draw = max(0, MAX_HAND_SLOTS - cur_non_none)
                            for _ in range(cards_to_draw):
                                nd = safe_draw()
                                if nd is None:
                                    break
                                s = nd.suit
                                r = nd.rank
                                img = card_images.get(s, {}).get(r)
                                if img is None:
                                    img = get_card_image(s, r)
                                nc = Card(img, 0, NORMAL_Y, r, s)
                                try:
                                    maybe_apply_soul_holo(nc)
                                except Exception:
                                    pass
                                # place into first free slot
                                placed = False
                                for i in range(MAX_HAND_SLOTS):
                                    if i >= len(hand):
                                        hand.append(None)
                                    if hand[i] is None:
                                        nc.slot_index = i
                                        nc.base_x = START_X + (i * CARD_SPACING)
                                        nc.target_x = nc.base_x
                                        hand[i] = nc
                                        placed = True
                                        break
                                if not placed:
                                    hand.append(nc)
                        except Exception:
                            pass
                        # Clear hovered_card so hovering doesn't continue to be applied
                        # based on a card instance that may have been removed/replaced.
                        try:
                            hovered_card = None
                        except Exception:
                            pass

                        # ensure extra card stays at fixed extra slot (do not change base_x)
                        try:
                            if extra_card is not None:
                                extra_card.target_x = EXTRA_SLOT_X
                                # if it still exists, reset its selection flag
                                try:
                                    if getattr(extra_card, 'is_selected', False):
                                        pass
                                except Exception:
                                    pass
                                extra_card.is_selected = False
                        except Exception:
                            pass

                        # Bir el oynandı: kalan el sayısını azalt (aktif jokerlere göre dinamik)
                        try:
                            # 1. Varsayılan olarak 1 el azalt
                            hands_to_reduce = 1
                            # 2. Joker'leri kontrol et (örnek effect_id: CHANCE_TO_NOT_CONSUME_HAND)
                            for j in active_jokers:
                                try:
                                    eff = str(getattr(j, 'effect_id', '')).upper()
                                    if eff == 'CHANCE_TO_NOT_CONSUME_HAND':
                                        # chance may be stored on the joker instance as `chance` (0..1)
                                        chance = float(getattr(j, 'chance', 0.25) or 0.25)
                                        if random.random() < chance:
                                            hands_to_reduce = 0
                                            break
                                except Exception:
                                    pass
                        except Exception:
                            hands_to_reduce = 1

                        try:
                            HANDS_REMAINING -= int(hands_to_reduce)
                        except Exception:
                            try:
                                HANDS_REMAINING = int(HANDS_REMAINING) - int(hands_to_reduce)
                            except Exception:
                                HANDS_REMAINING = 0

                        # Keep the extra card for the entire ante; it will be cleared when the ante ends
                        try:
                            print(f"Bir el oynandı. Kalan el: {HANDS_REMAINING}")
                        except Exception:
                            pass

                        # Refill hand only if there are still hands remaining in this ante.
                        # This prevents refilling when the round has ended and we transition
                        # to SHOP or GAME_OVER.
                        try:
                            if HANDS_REMAINING > 0:
                                fill_hand_slots()
                        except Exception:
                            pass

                        # Eğer kalan el hakkı bitti ise sonucu kontrol et
                        if HANDS_REMAINING == 0:
                            if current_score >= TARGET_SCORE:
                                # Kazanma durumu: oyuncuya para kazandır ve mağazaya git
                                try:
                                    money_gain = calculate_round_money(current_score, TARGET_SCORE)
                                except Exception:
                                    money_gain = 10
                                try:
                                    MONEY += int(money_gain)
                                except Exception:
                                    MONEY += int(money_gain)
                                print(f"Kazandınız! Para kazandınız: {money_gain} -> Para={MONEY}")
                                try:
                                    try:
                                        _ = globals().get('MONEY')
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                                # Ante başarılı: ilerleme, unlock ve boss mantığı
                                try:
                                    # increment ante/section level
                                    ante_level += 1
                                    try:
                                        try:
                                            _ = ante_level
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                                    # Recompute TARGET_SCORE based on configured progression
                                    try:
                                        base_target = int(globals().get('ANTE_1_TARGET', 60))
                                        inc = int(globals().get('ANTE_INCREMENT_PER_LEVEL', 100))
                                        TARGET_SCORE = base_target + (ante_level - 1) * inc
                                    except Exception:
                                        try:
                                            TARGET_SCORE = 60
                                        except Exception:
                                            pass
                                    # If enemy exists, adjust its health according to configured boss health progression
                                    try:
                                        bh_start = int(globals().get('BOSS_HEALTH_START', globals().get('ANTE_1_TARGET', 60)))
                                        bh_inc = int(globals().get('BOSS_HEALTH_INCREMENT_PER_ANTE', 100))
                                        boss_health = bh_start + (ante_level - 1) * bh_inc
                                        if enemy is not None:
                                            try:
                                                enemy.set_health(boss_health)
                                            except Exception:
                                                pass
                                    except Exception:
                                        pass
                                    # If we've reached every 3rd ante, pick a boss effect
                                    if ante_level % 3 == 0:
                                        try:
                                            current_boss_effect = random.choice(BOSS_EFFECTS) if BOSS_EFFECTS else None
                                            print(f"Boss effect seçildi: {current_boss_effect}")
                                        except Exception:
                                            current_boss_effect = None
                                    else:
                                        # Clear boss effect by default
                                        current_boss_effect = None

                                    # mark first shop visit so extra card is removed for subsequent antes
                                    if not first_ante_completed:
                                        first_ante_completed = True
                                        # ensure extra card removed going forward
                                        try:
                                            extra_card = None
                                        except Exception:
                                            pass
                                    if not unlocks.get('Mavi Deste', False):
                                        unlocks['Mavi Deste'] = True
                                        with open(UNLOCKS_FILE, 'w') as uf:
                                            json.dump(unlocks, uf)
                                        print('Mavi Deste kilidi açıldı!')
                                except Exception:
                                    pass
                                game_state = STATE_SHOP
                            else:
                                # Kaybetme durumu: oyun bitti ekranına git
                                print('Ante Başarısız! Oyun Bitti.')
                                game_state = STATE_GAME_OVER
                                # play lose sound if available
                                try:
                                    if lose_sound:
                                        play_sound(lose_sound)
                                except Exception:
                                    pass
                        # Oynanış tamamlandı, kart seçimine izin ver
                        try:
                            is_hand_processing = False
                            cards_locked = False
                        except Exception:
                            pass


            # Mouse move: update hovered_joker if cursor is over any joker rect
            elif event.type == pygame.MOUSEMOTION:
                    pos = event.pos
                    found = None
                    for jk in active_jokers:
                        try:
                            rect = getattr(jk, 'rect', None)
                            if rect and rect.collidepoint(pos):
                                found = jk
                                break
                        except Exception:
                            pass
                    hovered_joker = found

                    try:
                        joker_hud.update(pos, active_jokers)
                    except Exception:
                        pass

                    # Per-card hover flag: set only the card currently under the mouse
                    for card in hand:
                        if card is None:
                            continue
                        try:
                            if card.rect.collidepoint(pos):
                                card.is_hovered = True
                            else:
                                card.is_hovered = False
                        except Exception:
                            try:
                                card.is_hovered = False
                            except Exception:
                                pass
                    # handle extra_card separately
                    try:
                        if extra_card is not None:
                            try:
                                if extra_card.rect.collidepoint(pos):
                                    extra_card.is_hovered = True
                                else:
                                    extra_card.is_hovered = False
                            except Exception:
                                extra_card.is_hovered = False
                    except Exception:
                        pass

                    # Update hovered card (hand / extra card) for group hover animation when not dragging
                    if not drag_active:
                        hcard = None
                        try:
                            # check extra_card first
                            if extra_card is not None and extra_card.rect.collidepoint(pos):
                                hcard = extra_card
                            else:
                                for c in hand:
                                    if c is None:
                                        continue
                                    if c.rect.collidepoint(pos):
                                        hcard = c
                                        break
                        except Exception:
                            hcard = None
                        hovered_card = hcard
                    else:
                        # when dragging, update group target positions
                        dx = pos[0] - drag_origin[0]
                        dy = pos[1] - drag_origin[1]
                        for c in hand:
                            if c is None:
                                continue
                            c.target_x = c.drag_base_x + dx
                            # small vertical perspective based on distance from drag origin
                            dist = (c.drag_base_x - drag_origin[0])
                            c.target_y = c.drag_base_y + int(math.sin(dist * 0.01) * 10) + int(dy * 0.05)
                        try:
                            if extra_card is not None:
                                extra_card.target_x = extra_card.drag_base_x + dx
                                extra_card.target_y = extra_card.drag_base_y + int(dy * 0.05)
                        except Exception:
                            pass

        # Safety guard: clear stuck processing locks if they remain set
        # This prevents the UI from remaining locked if an exception or
        # early continue prevented the normal cleanup after playing a hand.
        try:
            if 'is_hand_processing' in globals() and is_hand_processing and not button_pressed:
                is_hand_processing = False
                cards_locked = False
        except Exception:
            pass

        # 2. GÜNCELLEME (Logic)
        # Smoothly animate displayed_score toward current_score so HUD counts up
        try:
            if displayed_score < current_score:
                diff = current_score - displayed_score
                displayed_score += (diff * 0.1) + 1
                # avoid overshoot
                if displayed_score > current_score:
                    displayed_score = current_score
        except Exception:
            pass

        # 3. ÇİZİM (Render)
        # Ekranı her karede siyahla temizle
        screen.fill(BLACK) 
        
        # Eldeki tüm kartları ekrana çiz
        # Önce arka plan çiz
        screen.blit(background_image, (0, 0))

        # Draw background effects, then the enemy immediately after background
        # so the boss appears above background but beneath cards and UI.
        try:
            try:
                draw_particles(screen)
            except Exception:
                pass

            try:
                # Ensure we reference the global `enemy` safely and draw it
                # immediately after the background so it sits under cards/UI.
                if 'enemy' in globals() and globals().get('enemy'):
                    try:
                        globals()['enemy'].update()
                    except Exception:
                        pass
                    try:
                        globals()['enemy'].draw(screen)
                    except Exception:
                        pass
            except Exception:
                pass
        except Exception:
            pass

        # Draw fixed boss name label above the boss sprite during PLAYING state
        try:
            if globals().get('game_state') == globals().get('STATE_PLAYING'):
                current_name = globals().get('current_boss_display_name', '')
                if current_name and enemy is not None:
                    # prefer enemy.rect if available
                    erect = getattr(enemy, 'rect', None)
                    try:
                        if erect is None:
                            # try to derive from current_sprite
                            spr = getattr(enemy, 'current_sprite', None)
                            if spr is not None:
                                erect = spr.get_rect()
                                # center it near top-center if we couldn't obtain exact on-screen rect
                                erect.centerx = SCREEN_WIDTH // 2
                                erect.top = int(SCREEN_HEIGHT * 0.18)
                    except Exception:
                        erect = None

                    if erect is not None:
                        try:
                            name_font = globals().get('game_font_medium') or globals().get('game_font')
                            if name_font is None:
                                name_font = pygame.font.SysFont(None, 28)
                            name_color = (255, 255, 255)
                            text_surface = name_font.render(current_name, True, name_color)
                            # Position the label centered horizontally and 80px above the
                            # boss sprite's top edge so it does not overlap the image.
                            # Increased offset for clearer separation from the sprite.
                            text_rect = text_surface.get_rect(center=(erect.centerx, erect.top - 115))
                            screen.blit(text_surface, text_rect)
                        except Exception as e:
                            try:
                                print(f"HATA: Boss adı çizilemedi: {e}")
                            except Exception:
                                pass
        except Exception:
            pass

        # Boss arrival overlay/banner (draw on top if active)
        try:
            if boss_banner_active:
                now = pygame.time.get_ticks()
                elapsed = max(0, now - boss_banner_start)
                t = min(1.0, float(elapsed) / float(max(1, BOSS_BANNER_DURATION_MS)))
                # semi-transparent dim background
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                alpha = int(180 * (1.0 - (0.4 * t)))
                overlay.fill((0, 0, 0, max(40, alpha)))
                screen.blit(overlay, (0, 0))

                # boss image (if any) scaled to fit ~45% width
                bimg = boss_banner_image or (enemy.current_sprite if enemy is not None else None)
                if bimg is not None:
                    try:
                        # scale image relative to screen
                        max_w = int(SCREEN_WIDTH * 0.45)
                        w0, h0 = bimg.get_width(), bimg.get_height()
                        scale_w = min(max_w, max(80, int(w0 * (1.0 + 0.5 * (1.0 - t)))))
                        scale_h = int(h0 * (scale_w / max(1, w0)))
                        bi = pygame.transform.smoothscale(bimg, (scale_w, scale_h))
                        # vertical slide in: start above then settle
                        slide = int((1.0 - t) * -120)
                        bref = bi.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40 + slide))
                        screen.blit(bi, bref.topleft)
                    except Exception:
                        pass

                # (Banner visual effects only) — the boss display name is
                # intentionally NOT drawn here so the animated banner keeps
                # its decorative graphics separate from the permanent label.

                # if elapsed finished, deactivate
                if elapsed >= BOSS_BANNER_DURATION_MS:
                    boss_banner_active = False
                    boss_banner_image = None
        except Exception:
            pass

        # Update hand layout targets each frame so cards smoothly lerp into place
        try:
            if not drag_active:
                # Draw HUD panels (stat boxes) now before card/UI drawing so
                # they occupy the intended Z-order above the boss but beneath
                # the interactive cards and final HUD text overlays.
                try:
                    draw_hud(screen, mode='panels')
                except Exception:
                    pass

                update_hand_layout()
                # ensure extra card slot stays fixed
                if extra_card is not None:
                    extra_card.base_x = EXTRA_SLOT_X
                    extra_card.target_x = EXTRA_SLOT_X
        except Exception:
            pass

        # Önce kartların animasyon güncellemelerini çalıştır
        for card in hand:
            if card is None:
                continue
            card.update()
        # extra_card should also animate towards its targets
        if extra_card is not None:
            try:
                extra_card.update()
            except Exception:
                pass

        for card in hand:
            if card is None:
                continue
            # --- KADER KÜRELERİNİ ÇİZ ---
            if 'fate_hud' in globals() and fate_hud:
                try:
                    fate_hud.draw(screen)
                except Exception:
                    pass
            card.draw(screen) # Kartın kendi 'draw' fonksiyonunu çağır

        # Hover and selection target positions are handled centrally by
        # update_hand_layout() / recalculate_hand_positions() based on
        # card.is_hovered and card.is_selected flags — do not override
        # per-card target_y values here.

        # Draw the extra special card (only during the first ante)
        try:
                if extra_card is not None and HANDS_REMAINING >= 1:
                    # Position the extra card at the hand's extra slot (animated by update())
                    try:
                        extra_card.target_x = float(globals().get('EXTRA_SLOT_X', 0))
                    except Exception:
                        try:
                            extra_card.target_x = float(EXTRA_SLOT_X)
                        except Exception:
                            pass

                    # Y konumu: seçili/hover durumuna göre ayarla
                    try:
                        if getattr(extra_card, 'is_selected', False):
                            extra_card.target_y = float(globals().get('SELECTED_Y_POS', 460))
                        elif getattr(extra_card, 'is_hovered', False):
                            extra_card.target_y = float(globals().get('HOVER_Y_POS', 475))
                        else:
                            extra_card.target_y = float(globals().get('NORMAL_Y_POS', 490))
                    except Exception:
                        try:
                            extra_card.target_y = float(NORMAL_Y)
                        except Exception:
                            pass

                # Ensure the extra card has a usable image. If missing,
                # attempt to reconstruct from suit/rank or create a placeholder.
                try:
                    if getattr(extra_card, 'image', None) is None:
                        try:
                            rebuilt = None
                            # Try to regenerate from known suit/rank
                            try:
                                s = getattr(extra_card, 'suit', None)
                                r = getattr(extra_card, 'rank', None)
                                if s is not None and r is not None:
                                    rebuilt = get_card_image(s, r)
                            except Exception:
                                rebuilt = None

                            # Fallback: simple placeholder surface
                            if rebuilt is None:
                                try:
                                    ph = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
                                    ph.fill((100, 100, 100))
                                    try:
                                        lbl = game_font_small.render(str(getattr(extra_card, 'rank', '?')), True, (255,255,255))
                                        ph.blit(lbl, (6, 6))
                                    except Exception:
                                        pass
                                    rebuilt = ph
                                except Exception:
                                    rebuilt = None

                            # Apply rebuilt image (scale to card dimensions like Card.__init__)
                            if rebuilt is not None:
                                try:
                                    extra_card.image = pygame.transform.scale(rebuilt, (CARD_WIDTH, CARD_HEIGHT))
                                except Exception:
                                    extra_card.image = rebuilt
                            else:
                                # As a last resort, remove the extra_card to avoid recurring warnings
                                try:
                                    globals()['extra_card'] = None
                                except Exception:
                                    extra_card = None
                        except Exception:
                            try:
                                globals()['extra_card'] = None
                            except Exception:
                                extra_card = None
                except Exception:
                    pass

                # Draw the extra card only via its own draw method.
                # Any decorative label/placeholder drawing removed so nothing
                # appears when `extra_card` is None. Keep only the explicit
                # call to the card's draw routine here.
                try:
                    extra_card.draw(screen)
                except Exception:
                    pass
        except Exception:
            pass
        
        # Draw HUD (text overlays) and joker area values (panels were drawn earlier)
        try:
            # Ensure joker HUD is rendered (if present) before the HUD text overlays
            try:
                if 'joker_hud' in globals():
                    try:
                        joker_hud.draw(screen)
                    except Exception:
                        # best-effort: some versions expect (screen, active_jokers)
                        try:
                            globals().get('joker_hud').draw(screen, active_jokers)
                        except Exception:
                            pass
            except Exception:
                pass

            draw_hud(screen, mode='texts')
        except Exception:
            try:
                draw_hud(screen)
            except Exception:
                pass

        # Alt-ortadaki butonu çiz (dolgu + kenarlık)
        # Buton hover / press efektleri
        mouse_pos = pygame.mouse.get_pos()
        hovering = button_rect.collidepoint(mouse_pos)

        base_color = (30, 144, 255)  # DodgerBlue
        hover_color = (65, 170, 255)
        pressed_color = (10, 100, 200)

        # Eğer butona az önce basıldıysa ve süre dolmadıysa pressed rengini kullan
        now = pygame.time.get_ticks()
        if button_pressed and (now - button_pressed_time) < BUTTON_PRESS_DURATION_MS:
            button_color = pressed_color
        else:
            button_color = hover_color if hovering else base_color
            # Reset button_pressed flag if the press duration elapsed
            if button_pressed and (now - button_pressed_time) >= BUTTON_PRESS_DURATION_MS:
                button_pressed = False
        button_border = (255, 255, 255)
        # modern rounded buttons
        # Draw primary "Eli Oyna" button as image if available, otherwise fallback to rect+text
        now_t = pygame.time.get_ticks()
        hovering = button_rect.collidepoint(mouse_pos)

        if PLAY_BTN_IMG:
            # animated glow when hovered (red glow for play button)
            if hovering:
                glow_alpha = 100 + int(40 * math.sin(now_t * 0.015))
                grow = 6 + int(3 * abs(math.sin(now_t * 0.01)))
                glow_surf = pygame.Surface((button_rect.width + grow * 2, button_rect.height + grow * 2), pygame.SRCALPHA)
                try:
                    pygame.draw.rect(glow_surf, (200, 40, 40, glow_alpha), (0, 0, glow_surf.get_width(), glow_surf.get_height()), border_radius=12)
                except Exception:
                    glow_surf.fill((200, 40, 40, glow_alpha))
                screen.blit(glow_surf, (button_rect.x - grow, button_rect.y - grow))

            # pressed effect: slight offset + darken
            play_pressed_active = (play_button_pressed and (now_t - play_button_pressed_time) < BUTTON_PRESS_DURATION_MS) or (button_pressed and (now_t - button_pressed_time) < BUTTON_PRESS_DURATION_MS)
            offset_x = 2 if play_pressed_active else 0
            offset_y = 2 if play_pressed_active else 0

            try:
                scaled = pygame.transform.smoothscale(PLAY_BTN_IMG, (button_rect.width, button_rect.height))
            except Exception:
                scaled = pygame.transform.scale(PLAY_BTN_IMG, (button_rect.width, button_rect.height))

            if play_pressed_active:
                # darken overlay
                try:
                    dark = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
                    dark.fill((0, 0, 0, 80))
                    scaled.blit(dark, (0, 0))
                except Exception:
                    pass

            screen.blit(scaled, (button_rect.x + offset_x, button_rect.y + offset_y))

            # keep hit rect as-is for clicks
        else:
            try:
                pygame.draw.rect(screen, button_color, button_rect, border_radius=10)
                pygame.draw.rect(screen, button_border, button_rect, 2, border_radius=10)
            except Exception:
                pygame.draw.rect(screen, button_color, button_rect)
                pygame.draw.rect(screen, button_border, button_rect, 2)
            btn_text = game_font.render("Eli Oyna", True, WHITE)
            btn_text_rect = btn_text.get_rect(center=button_rect.center)
            screen.blit(btn_text, btn_text_rect)
        
        # Kart Değiştir butonunu çiz (ana butonun solunda)
        discard_hover = discard_button_rect.collidepoint(mouse_pos)
        # If boss forbids discards, show as disabled regardless of remaining uses
        try:
            if DISCARDS_REMAINING == 0:
                discard_color = (120, 120, 120)
                discard_text_color = (200, 200, 200)
            else:
                discard_color = (200, 140, 0) if discard_hover else (220, 160, 20)
                discard_text_color = WHITE
        except Exception:
            discard_color = (200, 140, 0) if discard_hover else (220, 160, 20)
            discard_text_color = WHITE
        # discard/replace button (left of primary) - image if available
        discard_hover = discard_button_rect.collidepoint(mouse_pos)
        if DISCARD_BTN_IMG:
            # blue glow when hovered
            if discard_hover:
                glow_alpha = 100 + int(40 * math.sin(now_t * 0.015))
                grow = 5 + int(3 * abs(math.sin(now_t * 0.01)))
                glow_surf = pygame.Surface((discard_button_rect.width + grow * 2, discard_button_rect.height + grow * 2), pygame.SRCALPHA)
                try:
                    pygame.draw.rect(glow_surf, (50, 120, 220, glow_alpha), (0, 0, glow_surf.get_width(), glow_surf.get_height()), border_radius=12)
                except Exception:
                    glow_surf.fill((50, 120, 220, glow_alpha))
                screen.blit(glow_surf, (discard_button_rect.x - grow, discard_button_rect.y - grow))

            discard_pressed_active = (discard_button_pressed and (now_t - discard_button_pressed_time) < BUTTON_PRESS_DURATION_MS)
            doff_x = 2 if discard_pressed_active else 0
            doff_y = 2 if discard_pressed_active else 0

            try:
                scaled_d = pygame.transform.smoothscale(DISCARD_BTN_IMG, (discard_button_rect.width, discard_button_rect.height))
            except Exception:
                scaled_d = pygame.transform.scale(DISCARD_BTN_IMG, (discard_button_rect.width, discard_button_rect.height))

            if discard_pressed_active:
                try:
                    dark = pygame.Surface(scaled_d.get_size(), pygame.SRCALPHA)
                    dark.fill((0, 0, 0, 80))
                    scaled_d.blit(dark, (0, 0))
                except Exception:
                    pass

            screen.blit(scaled_d, (discard_button_rect.x + doff_x, discard_button_rect.y + doff_y))
        else:
            # fallback: colored rounded rect
            try:
                pygame.draw.rect(screen, discard_color, discard_button_rect, border_radius=10)
                pygame.draw.rect(screen, button_border, discard_button_rect, 2, border_radius=10)
            except Exception:
                pygame.draw.rect(screen, discard_color, discard_button_rect)
                pygame.draw.rect(screen, button_border, discard_button_rect, 2)
            discard_text = game_font.render("Kart Değiştir", True, discard_text_color)
            discard_text_rect = discard_text.get_rect(center=discard_button_rect.center)
            screen.blit(discard_text, discard_text_rect)
        
        # Ekrana çizilen her şeyi görünür yap
        try:
            joker_hud.draw(screen, active_jokers)
        except Exception:
            pass

        # Draw a small hamburger menu icon on top so it's always visible
        try:
            mpos = pygame.mouse.get_pos()
            icon_x, icon_y = 20, 20
            icon_w = 22
            line_h = 3
            spacing = 6
            # bounding rect for hover/click area (with small padding)
            bbox = pygame.Rect(icon_x - 6, icon_y - 6, icon_w + 12, line_h * 3 + spacing * 2 + 12)
            is_hover = bbox.collidepoint(mpos)

            # draw semi-transparent background for contrast
            try:
                bg_surf = pygame.Surface((bbox.width, bbox.height), pygame.SRCALPHA)
                alpha = 210 if is_hover else 160
                bg_surf.fill((8, 8, 8, alpha))
                screen.blit(bg_surf, bbox.topleft)
            except Exception:
                pygame.draw.rect(screen, (8, 8, 8), bbox)

            # draw three horizontal lines (hamburger)
            try:
                color = (255, 215, 0) if is_hover else (255, 255, 255)
                for i in range(3):
                    ly = icon_y + i * (line_h + spacing)
                    pygame.draw.rect(screen, color, (icon_x, ly, icon_w, line_h))
                menu_buttons_data['BTN_GAME_MENU'] = bbox
            except Exception:
                pass
        except Exception:
            pass

    # GAME STATE: SHOP
    elif game_state == STATE_SHOP:
        # Generate shop items once per visit and keep them in `current_shop_items`.
        if not shop_items_generated:
            current_shop_items = []
            # progression unlocks: check if we've just entered a new ante that
            # should grant deck unlocks (e.g., entering ante 4 means ante 3 finished)
            try:
                check_progression_unlocks(int(globals().get('ante_level', 0)))
            except Exception:
                pass
            try:
                # pick 3 jokers
                jokers = random.sample(JOKER_POOL, min(3, len(JOKER_POOL)))
                for j in jokers:
                    current_shop_items.append(dict(j))
            except Exception:
                for j in JOKER_POOL[:3]:
                    current_shop_items.append(dict(j))
            # pick one voucher
            try:
                if len(VOUCHER_POOL) > 0:
                    v = random.choice(VOUCHER_POOL)
                    vv = dict(v)
                    vv['type'] = 'voucher'
                    current_shop_items.append(vv)
            except Exception:
                pass
            # sometimes offer a planet card
            try:
                if len(PLANET_POOL) > 0 and random.random() < 0.6:
                    p = random.choice(PLANET_POOL)
                    pp = dict(p)
                    pp['type'] = 'planet'
                    current_shop_items.append(pp)
            except Exception:
                pass
            # shuffle so voucher/planet don't always appear in same slot
            random.shuffle(current_shop_items)

            # --- Assign rects now to avoid first-frame click race ---
            try:
                PADDING = 20
                START_X = 50
                available_width = max(200, SCREEN_WIDTH - START_X * 2)
                min_item_w = 160
                ITEMS_PER_ROW = max(1, min(4, available_width // (min_item_w + PADDING)))
                ITEM_WIDTH = int((available_width - (ITEMS_PER_ROW - 1) * PADDING) / ITEMS_PER_ROW)
                ITEM_HEIGHT = int(max(80, ITEM_WIDTH * 0.6))
                # compute grid height (rows x item height + paddings)
                try:
                    num_items = max(1, len(current_shop_items))
                    rows = int(math.ceil(float(num_items) / float(ITEMS_PER_ROW)))
                except Exception:
                    rows = 1
                grid_height = rows * ITEM_HEIGHT + max(0, (rows - 1) * PADDING)
                # Determine vertical placement: center grid between the shop title
                # area and the Ante button so header and the button don't overlap the grid.
                try:
                    # Use a conservative title bottom estimate; drawing code uses a header at ~y=80
                    title_bottom_y = HUD_Y + 50
                except Exception:
                    title_bottom_y = HUD_Y + 50 if 'HUD_Y' in globals() else 120
                try:
                    button_top_y = int(ante_button_rect.top)
                except Exception:
                    try:
                        button_top_y = SCREEN_HEIGHT - 70
                    except Exception:
                        button_top_y = int(SCREEN_HEIGHT * 0.85)

                PADDING = 20
                ROW_PADDING = PADDING
                # available vertical space between title and button (reserve padding)
                available_vertical_space = max(80, button_top_y - title_bottom_y - (2 * PADDING))

                # compute how tall the grid will be (rows * item height + paddings)
                grid_total_height = rows * ITEM_HEIGHT + max(0, (rows - 1) * ROW_PADDING)

                # center the grid inside the available vertical space
                START_Y = int(title_bottom_y + PADDING + (available_vertical_space / 2.0) - (grid_total_height / 2.0))
                # clamp to avoid overlapping HUD or going offscreen
                START_Y = max(START_Y, HUD_Y + HUD_HEIGHT + 8 if 'HUD_Y' in globals() and 'HUD_HEIGHT' in globals() else title_bottom_y + 8)

                shop_offer_rects = []
                for i, item in enumerate(current_shop_items):
                    row = i // ITEMS_PER_ROW
                    col = i % ITEMS_PER_ROW
                    item_x = START_X + col * (ITEM_WIDTH + PADDING)
                    item_y = START_Y + row * (ITEM_HEIGHT + PADDING)
                    rect = pygame.Rect(item_x, item_y, ITEM_WIDTH, ITEM_HEIGHT)
                    shop_offer_rects.append(rect)
                    try:
                        item['rect'] = rect
                    except Exception:
                        pass
            except Exception:
                # If layout calc fails for any reason, ensure lists are cleared
                shop_offer_rects.clear()

            shop_items_generated = True

        # Handle shop input and drawing separately
        for event in events:
            # handle resize events and fullscreen toggle
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                except Exception:
                    pass
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Ignore clicks if click lock is active for this frame
                try:
                    if globals().get('CLICK_LOCKED'):
                        break
                except Exception:
                    pass
                if ante_button_rect.collidepoint(event.pos):
                    # play click sound for Ante button in shop
                    try:
                        if click_sound:
                            play_sound(click_sound)
                    except Exception:
                        pass

                    # Start next ante/round: apply next-round settings and go back to PLAYING
                    TARGET_SCORE += 100
                    # Reset round scores; actual hand/discard counts will be
                    # computed by `reset_hand_state()` after the boss is loaded.
                    current_score = 0
                    displayed_score = 0

                    # Start next ante: load the boss first so its penalties/abilities
                    # are available to `reset_hand_state()` when we compute discards
                    # and hands for the new round.
                    try:
                        # Do NOT increment ante_level here; progression should be
                        # driven by the GAMBIT_RESULT 'DEVAM ET' action only.
                        # Load the boss for the current ante_level first.
                        load_boss_for_ante(ante_level)
                    except Exception:
                        pass

                    # Reset hand/round state after boss is loaded so boss penalties
                    # are applied during reset. `reset_hand_state()` will set
                    # `HANDS_REMAINING` and `DISCARDS_REMAINING` appropriately.
                    try:
                        reset_hand_state()
                    except Exception:
                        # fallback: compute starting hands if reset fails
                        try:
                            HANDS_REMAINING = compute_starting_hands(base_hands=INITIAL_HANDS)
                        except Exception:
                            HANDS_REMAINING = INITIAL_HANDS

                    # Refill the hand slots to keep 5 fixed cards
                    try:
                        fill_hand_slots()
                    except Exception:
                        pass

                    # Ensure extra card is provided for the new ante only if still allowed
                    try:
                        if (not first_ante_completed) and extra_card is None and HANDS_REMAINING == INITIAL_HANDS:
                            extra_card_data = safe_draw()
                            if extra_card_data is not None:
                                s = extra_card_data.suit
                                r = extra_card_data.rank
                                img = card_images.get(s, {}).get(r)
                                if img is None:
                                    img = get_card_image(s, r)
                                extra_card = Card(img, EXTRA_SLOT_X, NORMAL_Y, r, s)
                                try:
                                    maybe_apply_soul_holo(extra_card)
                                except Exception:
                                    pass
                    except Exception:
                        pass

                    # Transition to playing state for the new ante (set after boss load and resets)
                    game_state = STATE_PLAYING
                    # reset shop so new offers will be generated next time
                    shop_items_generated = False
                    current_shop_items = []
                    shop_offer_rects.clear()
                elif joker_button_rect.collidepoint(event.pos):
                    # (Deprecated single joker button) ignore
                    pass
                else:
                    # Check if player clicked on one of their owned jokers to sell
                    # First check toggle button for entering/exiting Sell Mode
                    try:
                        tb = menu_buttons_data.get('SHOP_TOGGLE_SELL')
                        if tb and tb.collidepoint(event.pos):
                            globals()['is_sell_mode'] = not globals().get('is_sell_mode', False)
                            print(f"Satış Modu: {globals().get('is_sell_mode')}")
                            break
                    except Exception:
                        pass

                    # If in sell mode, check HUD-exposed joker rects (JokerHUD sets jk.rect)
                    sold_handled = False
                    try:
                        if globals().get('is_sell_mode'):
                            for jk_idx, jk in enumerate(list(active_jokers)):
                                try:
                                    r = getattr(jk, 'rect', None)
                                    if r and r.collidepoint(event.pos):
                                        sold = active_jokers.pop(jk_idx)
                                        try:
                                            purchase_price = int(getattr(sold, 'purchase_price', 10))
                                        except Exception:
                                            purchase_price = 10
                                        try:
                                            sell_price = int(purchase_price * 0.5)
                                        except Exception:
                                            sell_price = purchase_price // 2
                                        try:
                                            globals()['MONEY'] = int(globals().get('MONEY', 0)) + sell_price
                                            try:
                                                try:
                                                    _ = globals().get('MONEY')
                                                except Exception:
                                                    pass
                                            except Exception:
                                                pass
                                        except Exception:
                                            try:
                                                MONEY += sell_price
                                            except Exception:
                                                pass
                                            try:
                                                try:
                                                    _ = globals().get('MONEY')
                                                except Exception:
                                                    pass
                                            except Exception:
                                                pass
                                        # exit sell mode after successful sale
                                        try:
                                            globals()['is_sell_mode'] = False
                                        except Exception:
                                            pass
                                        print(f"Joker satıldı: {sold.name} -> +{sell_price}$ | Para={globals().get('MONEY')}")
                                        sold_handled = True
                                        break
                                except Exception:
                                    pass
                            if sold_handled:
                                break
                    except Exception:
                        pass

                    # Clicks on shop items: iterate items and check their rects, then buy
                    for i, item in enumerate(current_shop_items):
                        try:
                            item_rect = item.get('rect') if isinstance(item, dict) else getattr(item, 'rect', None)
                        except Exception:
                            item_rect = None

                        # 1. Click check
                        if item_rect and item_rect.collidepoint(event.pos):

                            # 2. Joker limit check
                            try:
                                is_joker_item = (str(item.get('type', '')).upper() == 'JOKER') or ('Joker' in str(item.get('name', '')))
                            except Exception:
                                is_joker_item = False

                            if is_joker_item:
                                try:
                                    max_slots = int(globals().get('JOKER_SLOTS_MAX', 6))
                                except Exception:
                                    max_slots = 6
                                try:
                                    if len(active_jokers) >= int(max_slots):
                                        try:
                                            # Prefer showing user-facing UI message if available
                                            show_error_message(f"Joker slotları dolu! (Maksimum {max_slots})")
                                        except Exception:
                                            try:
                                                print(f"HATA: Joker slotları dolu! (Maksimum {max_slots})")
                                            except Exception:
                                                pass
                                        # Can't buy: break without clearing events; rely on CLICK_LOCKED
                                        break
                                except Exception:
                                    pass

                            # 3. Money check
                            try:
                                price = int(item.get('price', 0))
                            except Exception:
                                price = 0
                            try:
                                if globals().get('MONEY', 0) < price:
                                    try:
                                        show_error_message("Yetersiz para!")
                                    except Exception:
                                        print('Yetersiz para: Teklif satın alınamadı')
                                    break
                            except Exception:
                                pass

                            # 4. Attempt purchase
                            try:
                                satın_alma_basarili_mi = buy_item(item)
                            except Exception:
                                satın_alma_basarili_mi = False

                            if satın_alma_basarili_mi:
                                try:
                                    # remove by identity/index to avoid mismatches
                                    if item in current_shop_items:
                                        current_shop_items.remove(item)
                                    else:
                                        # try safe pop by index if list hasn't changed
                                        try:
                                            current_shop_items.pop(i)
                                        except Exception:
                                            pass
                                except Exception:
                                    pass

                                # 5. Prevent double-buy: set one-frame lock, clear mouse events and break
                                try:
                                    globals()['CLICK_LOCKED'] = True
                                except Exception:
                                    try:
                                        CLICK_LOCKED = True
                                    except Exception:
                                        pass
                                try:
                                    # clear pending mouse-up events to avoid double-buy
                                    pygame.event.clear(pygame.MOUSEBUTTONUP)
                                except Exception:
                                    pass
                                break

        # Draw shop UI (image-based joker grid)
        screen.fill((20, 20, 30))
        screen.blit(background_image, (0, 0))
        try:
            draw_particles(screen)
        except Exception:
            pass
        draw_hud(screen)
        # Shop header
        header = game_font.render("DÜKKAN", True, WHITE)
        header_rect = header.get_rect(center=(SCREEN_WIDTH // 2, 80))
        screen.blit(header, header_rect)

        # Image grid: up to 6 items, 3 columns x 2 rows
        GRID_COLS = 3
        MAX_SHOW = 6
        items = current_shop_items[:MAX_SHOW]

        # Use fixed slot width (3 columns) and center horizontally
        SLOT_WIDTH = int(SCREEN_WIDTH // 3)
        PADDING = 20
        TOTAL_GRID_WIDTH = (SLOT_WIDTH * GRID_COLS) + (PADDING * (GRID_COLS - 1))
        START_X = int((SCREEN_WIDTH - TOTAL_GRID_WIDTH) // 2)

        # compute grid vertical placement so it fits between header and Ante button
        try:
            num_items = max(1, len(items))
            rows = int(math.ceil(float(num_items) / float(GRID_COLS)))
        except Exception:
            rows = 1

        try:
            title_bottom_y = header_rect.bottom
        except Exception:
            title_bottom_y = HUD_Y + 50 if 'HUD_Y' in globals() else 120

        try:
            button_top_y = int(ante_button_rect.top)
        except Exception:
            try:
                button_top_y = SCREEN_HEIGHT - 70
            except Exception:
                button_top_y = int(SCREEN_HEIGHT * 0.85)

        ROW_PADDING = PADDING
        available_vertical_space = max(80, button_top_y - title_bottom_y - (2 * PADDING))

        SLOT_HEIGHT = int(max(120, SLOT_WIDTH * 0.75))
        grid_height = rows * SLOT_HEIGHT + max(0, (rows - 1) * ROW_PADDING)

        START_Y = int(title_bottom_y + PADDING + (available_vertical_space / 2.0) - (grid_height / 2.0))
        START_Y = max(START_Y, title_bottom_y + 8)

        # prepare an image cache on globals to avoid reloading every frame
        if 'shop_image_cache' not in globals():
            globals()['shop_image_cache'] = {}
        cache = globals().get('shop_image_cache')

        shop_offer_rects = []
        for idx, item in enumerate(items):
            row = idx // GRID_COLS
            col = idx % GRID_COLS
            item_x = START_X + col * (SLOT_WIDTH + PADDING)
            item_y = START_Y + row * (SLOT_HEIGHT + ROW_PADDING)

            rect = pygame.Rect(item_x, item_y, SLOT_WIDTH, SLOT_HEIGHT)
            shop_offer_rects.append(rect)
            try:
                item['rect'] = rect
            except Exception:
                pass
            # also register clickable area under a standardized key
            try:
                menu_buttons_data[f'JOKER_SLOT_{idx}'] = rect
            except Exception:
                pass

            # Load image (cached)
            img_path = item.get('image_path') or 'assets/jokers/joker_default.png'
            img = None
            try:
                if img_path in cache:
                    img = cache[img_path]
                else:
                    # check existence using resource_path so bundled assets are found
                    if not os.path.exists(resource_path(img_path)):
                        img_path = 'assets/jokers/joker_default.png'
                    loaded = pygame.image.load(resource_path(img_path)).convert_alpha()
                    cache[img_path] = loaded
                    img = loaded
            except Exception:
                try:
                    img = pygame.image.load(resource_path('assets/jokers/joker_default.png')).convert_alpha()
                except Exception:
                    img = pygame.Surface((SLOT_WIDTH, int(SLOT_HEIGHT * 0.6)))
                    img.fill((90,90,90))

            # Scale image to target width relative to slot while preserving aspect
            try:
                img_w = img.get_width()
                img_h = img.get_height()
                target_w = int(SLOT_WIDTH * 0.8)
                max_img_h = int(SLOT_HEIGHT * 0.62)
                # compute scaled size preserving aspect ratio
                scale_w = min(target_w, img_w)
                scale_h = int(scale_w * (img_h / max(1, img_w)))
                if scale_h > max_img_h:
                    scale_h = max_img_h
                    scale_w = int(scale_h * (img_w / max(1, img_h)))
                surf = pygame.transform.smoothscale(img, (max(1, scale_w), max(1, scale_h)))
            except Exception:
                surf = pygame.Surface((int(SLOT_WIDTH * 0.8), int(SLOT_HEIGHT * 0.6)))
                surf.fill((100,100,100))

            # draw image centered in the upper area of rect
            try:
                img_x = rect.x + (rect.width - surf.get_width()) // 2
                img_y = rect.y + 8
                screen.blit(surf, (img_x, img_y))
            except Exception:
                pass

            # draw name, price and short desc within the slot
            try:
                name = item.get('name', 'Teklif')
                price = item.get('price', 10)
                name_s = game_font_small.render(name, True, WHITE)
                price_s = game_font_small.render(f"${price}", True, WHITE)

                # place name centered under the image
                name_y = img_y + surf.get_height() + 6
                nx = rect.x + (rect.width - name_s.get_width()) // 2
                screen.blit(name_s, (nx, name_y))

                # description smaller and wrapped to slot width minus padding
                desc = item.get('desc', '')
                wrap_width = SLOT_WIDTH - 2 * PADDING
                lines = wrap_text(desc, game_font_small, wrap_width)
                for li, line in enumerate(lines[:2]):
                    ls = game_font_small.render(line, True, (200,200,200))
                    screen.blit(ls, (rect.x + PADDING, name_y + name_s.get_height() + 6 + li * (game_font_small.get_height() + 2)))

                # price centered at bottom
                px = rect.x + (rect.width - price_s.get_width()) // 2
                py = rect.y + rect.height - price_s.get_height() - 8
                screen.blit(price_s, (px, py))
            except Exception:
                pass

        # Integrated Sell Mode: a single toggle button replaces the crude
        # right-side owned-joker list. When active, the Joker HUD highlights
        # jokers and clicking a HUD joker will sell it.
        player_joker_rects.clear()
        try:
            sell_btn_w = 160
            sell_btn_h = 40
            sell_btn_rect = pygame.Rect(SCREEN_WIDTH - sell_btn_w - 20, header_rect.bottom + 8, sell_btn_w, sell_btn_h)
            sell_hover = sell_btn_rect.collidepoint(pygame.mouse.get_pos())
            if globals().get('is_sell_mode'):
                sell_color = (200, 80, 60)  # active red-tinted
                sell_label = "Satış Modu: ON"
            else:
                sell_color = (80, 140, 80)  # inactive green
                sell_label = "Satış Modu: OFF"
            pygame.draw.rect(screen, sell_color, sell_btn_rect)
            pygame.draw.rect(screen, (255,255,255), sell_btn_rect, 2)
            lbl = game_font_small.render(sell_label, True, WHITE)
            screen.blit(lbl, (sell_btn_rect.centerx - lbl.get_width()//2, sell_btn_rect.centery - lbl.get_height()//2))
            # store button for click handling
            menu_buttons_data['SHOP_TOGGLE_SELL'] = sell_btn_rect
            # show a small hint when active
            if globals().get('is_sell_mode'):
                try:
                    hint = game_font_small.render("HUD'a tıklayın: Joker sat", True, (220,220,220))
                    screen.blit(hint, (sell_btn_rect.x - hint.get_width() - 12, sell_btn_rect.y + 6))
                except Exception:
                    pass
        except Exception:
            pass

        # Draw Ante button
        ante_hover = ante_button_rect.collidepoint(pygame.mouse.get_pos())
        ante_color = (30, 144, 255) if ante_hover else (65, 170, 255)
        pygame.draw.rect(screen, ante_color, ante_button_rect)
        pygame.draw.rect(screen, (255,255,255), ante_button_rect, 2)
        ante_text = game_font_small.render("Ante'yi Başlat", True, WHITE)
        at_rect = ante_text.get_rect(center=ante_button_rect.center)
        screen.blit(ante_text, at_rect)

        

    # GAME STATE: GAME_OVER

    # GAME STATE: GAMBIT RESULT (show reward/spare message and confirm)
    elif game_state == STATE_GAMBIT_RESULT:
        # Draw result message centered and a CONTINUE button
        screen.fill((10, 10, 20))
        screen.blit(background_image, (0, 0))
        try:
            draw_particles(screen)
        except Exception:
            pass
        draw_hud(screen)
        try:
            msg = gambit_result_message or "Sonuç"
            font_big = pygame.font.Font(None, 64)
            txt = font_big.render(msg, True, WHITE)
            trect = txt.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 40))
            screen.blit(txt, trect)

            # Continue button
            btn_w = 260
            btn_h = 56
            btn_rect = pygame.Rect((SCREEN_WIDTH // 2) - (btn_w // 2), trect.bottom + 20, btn_w, btn_h)
            hover = btn_rect.collidepoint(pygame.mouse.get_pos())
            col = (60, 160, 80) if hover else (40, 120, 60)
            pygame.draw.rect(screen, col, btn_rect)
            pygame.draw.rect(screen, WHITE, btn_rect, 2)
            btxt = game_font_small.render('DEVAM ET', True, WHITE)
            screen.blit(btxt, (btn_rect.centerx - btxt.get_width()//2, btn_rect.centery - btxt.get_height()//2))
            menu_buttons_data['GAMBIT_RESULT_CONTINUE'] = btn_rect
        except Exception:
            pass

        # Input handling for confirming result
        for event in events:
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                except Exception:
                    pass
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', None) == 1:
                mp = event.pos
                try:
                    if menu_buttons_data.get('GAMBIT_RESULT_CONTINUE') and menu_buttons_data['GAMBIT_RESULT_CONTINUE'].collidepoint(mp):
                        # On confirm: apply corrected progression logic
                        try:
                            # Reset transient hand/score state (do not touch ante/enemy)
                            try:
                                reset_hand_state()
                            except Exception:
                                pass

                            # 1) Always increment ante level by exactly 1
                            try:
                                ante_level = int(ante_level or 0) + 1
                            except Exception:
                                ante_level = 1

                            # 2) If we've reached ante level 10 -> that means player finished ante 9
                            if int(ante_level) == 10:
                                try:
                                    # Only now perform True Ending check
                                    min_sp = globals().get('TRUE_ENDING_MIN_SPARE', None)
                                    max_sp = globals().get('TRUE_ENDING_MAX_SPARE', None)
                                    if min_sp is not None and max_sp is not None:
                                        try:
                                            if int(min_sp) <= int(total_spared_bosses or 0) <= int(max_sp):
                                                game_state = STATE_TRUE_ENDING
                                            else:
                                                # True Ending koşulu sağlanmadı -> Başka yol: başlat Sonsuz Mod (Ante 10)
                                                try:
                                                    load_boss_for_ante(10)
                                                except Exception:
                                                    pass
                                                try:
                                                    game_state = STATE_SHOP
                                                except Exception:
                                                    pass
                                                try:
                                                    globals()['CLICK_LOCKED'] = True
                                                except Exception:
                                                    try:
                                                        CLICK_LOCKED = True
                                                    except Exception:
                                                        pass
                                        except Exception:
                                            # on error, fall back to starting endless mode
                                            try:
                                                load_boss_for_ante(10)
                                            except Exception:
                                                pass
                                            try:
                                                game_state = STATE_SHOP
                                            except Exception:
                                                pass
                                            try:
                                                globals()['CLICK_LOCKED'] = True
                                            except Exception:
                                                try:
                                                    CLICK_LOCKED = True
                                                except Exception:
                                                    pass
                                    else:
                                        # No true-ending bounds defined -> start endless mode
                                        try:
                                            load_boss_for_ante(10)
                                        except Exception:
                                            pass
                                        try:
                                            game_state = STATE_SHOP
                                        except Exception:
                                            pass
                                        try:
                                            globals()['CLICK_LOCKED'] = True
                                        except Exception:
                                            try:
                                                CLICK_LOCKED = True
                                            except Exception:
                                                pass
                                except Exception:
                                    # final fallback -> start endless mode
                                    try:
                                        load_boss_for_ante(10)
                                    except Exception:
                                        pass
                                    try:
                                        game_state = STATE_SHOP
                                    except Exception:
                                        pass
                                    try:
                                        globals()['CLICK_LOCKED'] = True
                                    except Exception:
                                        try:
                                            CLICK_LOCKED = True
                                        except Exception:
                                            pass
                            else:
                                # Normal flow for antes 2-9: load boss for current ante and go to shop
                                try:
                                    load_boss_for_ante(ante_level)
                                except Exception:
                                    pass
                                try:
                                    game_state = STATE_SHOP
                                except Exception:
                                    pass
                                # Lock click for this frame to avoid ghost clicks when entering shop
                                try:
                                    globals()['CLICK_LOCKED'] = True
                                except Exception:
                                    try:
                                        CLICK_LOCKED = True
                                    except Exception:
                                        pass
                        except Exception:
                            pass
                        # clear pending message/choice and message text
                        try:
                            pending_gambit_choice = None
                        except Exception:
                            pass
                        try:
                            gambit_result_message = ""
                        except Exception:
                            pass
                        break
                except Exception:
                    pass

    # GAME STATE: TRUE ENDING
    elif game_state == STATE_TRUE_ENDING:
        # Themed true-ending screen: show boss image left and a narrative box on the right
        try:
            screen.fill((10, 10, 20))
            try:
                screen.blit(background_image, (0, 0))
                try:
                    draw_particles(screen)
                except Exception:
                    pass
            except Exception:
                pass
            draw_hud(screen)
        except Exception:
            pass

        # Left: boss/harmed image
        try:
            left_cx = int(SCREEN_WIDTH * 0.25)
            left_cy = int(SCREEN_HEIGHT * 0.5)
            bimg = None
            if enemy is not None:
                bimg = getattr(enemy, 'harmed_sprite', None) or getattr(enemy, 'current_sprite', None)
            if bimg is None:
                bimg = pygame.Surface((200, 200))
                bimg.fill((80, 80, 120))
            max_w = int(SCREEN_WIDTH * 0.4)
            w0, h0 = bimg.get_width(), bimg.get_height()
            scale_w = min(max_w, max(80, w0))
            scale_h = int(h0 * (scale_w / max(1, w0)))
            bi = pygame.transform.smoothscale(bimg, (scale_w, scale_h))
            bref = bi.get_rect(center=(left_cx, left_cy))
            screen.blit(bi, bref.topleft)
        except Exception:
            pass

        # Right: narrative box with dynamic content based on player choices
        try:
            box_x = int(SCREEN_WIDTH * 0.52)
            box_w = int(SCREEN_WIDTH * 0.44)
            box_y = int(HUD_Y + 20)
            box_h = int(SCREEN_HEIGHT - box_y - 40)
            panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 200))
            screen.blit(panel, (box_x, box_y))

            # Build dynamic ending story using globals
            try:
                ck = int(consecutive_kills or 0)
            except Exception:
                ck = 0
            try:
                ts = int(total_spared_bosses or 0)
            except Exception:
                ts = 0

            story = (
                "Gerçek Son\n\n"
                f"Ardı ardına öldürmeler: {ck}\n"
                f"Toplam bağışlanan canavarlar: {ts}\n\n"
                "Seçimlerin bir döngüyü kırdı veya daha derinlere itti.\n"
                "Ruhunu saklamak ve hikâyeyi sonlandırmak istiyorsan aşağıdaki butona bas."
            )

            lines = wrap_text(story, game_font_small, box_w - 30)
            ty = box_y + 20
            for ln in lines:
                s = game_font_small.render(ln, True, WHITE)
                screen.blit(s, (box_x + 16, ty))
                ty += s.get_height() + 6

            # Two-action panel: Enter Endless Mode (left) and Save & Exit (right)
            btn_h = 56
            btn_w = 300
            gap = 24
            total_w = (btn_w * 2) + gap
            base_x = box_x + (box_w - total_w) // 2
            btn_y = box_y + box_h - btn_h - 20

            btn_enter = pygame.Rect(base_x, btn_y, btn_w, btn_h)
            btn_save = pygame.Rect(base_x + btn_w + gap, btn_y, btn_w, btn_h)

            # draw Enter Endless button
            hover_enter = btn_enter.collidepoint(pygame.mouse.get_pos())
            col_enter = (200, 140, 40) if hover_enter else (160, 110, 30)
            pygame.draw.rect(screen, col_enter, btn_enter)
            pygame.draw.rect(screen, WHITE, btn_enter, 2)
            t_enter = game_font_small.render('SONSUZ MODA GİR', True, WHITE)
            screen.blit(t_enter, (btn_enter.centerx - t_enter.get_width()//2, btn_enter.centery - t_enter.get_height()//2))

            # draw Save & Exit button
            hover_save = btn_save.collidepoint(pygame.mouse.get_pos())
            col_save = (120, 80, 200) if hover_save else (90, 60, 160)
            pygame.draw.rect(screen, col_save, btn_save)
            pygame.draw.rect(screen, WHITE, btn_save, 2)
            t_save = game_font_small.render('RUHUNU KAYDET ve ÇIK', True, WHITE)
            screen.blit(t_save, (btn_save.centerx - t_save.get_width()//2, btn_save.centery - t_save.get_height()//2))

            # register click rects
            menu_buttons_data['TRUE_ENDING_ENTER_ENDLESS'] = btn_enter
            menu_buttons_data['TRUE_ENDING_SAVE_EXIT'] = btn_save
        except Exception:
            pass

        for event in events:
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', None) == 1:
                mp = event.pos
                try:
                    # Enter Endless Mode button: jump into ante 10 and go to shop,
                    # preserving MONEY/deck/state (do not call reset_game())
                    if menu_buttons_data.get('TRUE_ENDING_ENTER_ENDLESS') and menu_buttons_data['TRUE_ENDING_ENTER_ENDLESS'].collidepoint(mp):
                        try:
                            globals()['ante_level'] = 10
                        except Exception:
                            try:
                                ante_level = 10
                            except Exception:
                                pass
                        try:
                            load_boss_for_ante(10)
                        except Exception:
                            pass
                        try:
                            globals()['game_state'] = STATE_SHOP
                        except Exception:
                            try:
                                game_state = STATE_SHOP
                            except Exception:
                                pass
                        try:
                            globals()['CLICK_LOCKED'] = True
                        except Exception:
                            try:
                                CLICK_LOCKED = True
                            except Exception:
                                pass
                        break

                    if menu_buttons_data.get('TRUE_ENDING_SAVE_EXIT') and menu_buttons_data['TRUE_ENDING_SAVE_EXIT'].collidepoint(mp):
                        try:
                            reset_game()
                        except Exception:
                            pass
                        try:
                            game_state = STATE_MAIN_MENU
                        except Exception:
                            pass
                        break
                except Exception:
                    pass

    # GAME STATE: BOSS DEFEAT / NARRATIVE FLOW
    elif game_state == STATE_BOSS_DEFEATED_A:
        # New RPG-style gambit UI: left = harmed boss, right-top = opening (typewriter),
        # right-bottom = three stacked choice buttons.
        screen.fill((10, 10, 18))
        try:
            screen.blit(background_image, (0, 0))
        except Exception:
            pass
        try:
            draw_particles(screen)
        except Exception:
            pass
        draw_hud(screen)

        # --- Left: Boss image (harmed preferred) ---
        try:
            left_cx = int(SCREEN_WIDTH * 0.25)
            left_cy = int(SCREEN_HEIGHT * 0.5)
            bimg = None
            if enemy is not None:
                bimg = getattr(enemy, 'harmed_sprite', None) or getattr(enemy, 'current_sprite', None)
            if bimg is None:
                bimg = pygame.Surface((200, 200))
                bimg.fill((80, 80, 120))
            max_w = int(SCREEN_WIDTH * 0.4)
            w0, h0 = bimg.get_width(), bimg.get_height()
            scale_w = min(max_w, max(80, w0))
            scale_h = int(h0 * (scale_w / max(1, w0)))
            bi = pygame.transform.smoothscale(bimg, (scale_w, scale_h))
            bref = bi.get_rect(center=(left_cx, left_cy))
            screen.blit(bi, bref.topleft)
        except Exception:
            pass

        # --- Right: dialog panel ---
        try:
            panel_x = int(SCREEN_WIDTH * 0.52)
            panel_w = int(SCREEN_WIDTH * 0.44)
            panel_y = int(HUD_Y + 20)
            panel_h = int(SCREEN_HEIGHT - panel_y - 40)
            panel_rect = pygame.Rect(panel_x, panel_y, panel_w, panel_h)
            panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            panel_surf.fill((6, 6, 8, 220))
            screen.blit(panel_surf, (panel_x, panel_y))

            # fetch dialogue for current boss
            ck = globals().get('current_boss_key')
            dialogues = globals().get('BOSS_DIALOGUES', {}) or {}
            entry = dialogues.get(ck) or {}
            opening = entry.get('opening', "...")
            options = entry.get('options', [])[:3]

            # initialize typewriter state per boss key
            if globals().get('last_boss_dialogue_key') != ck:
                globals()['last_boss_dialogue_key'] = ck
                globals()['boss_dialogue_full'] = str(opening or "")
                globals()['boss_dialogue_index'] = 0
                globals()['boss_dialogue_visible'] = ""
                globals()['boss_dialogue_timer'] = 0.0

            # typewriter progression (STORY_CHAR_DELAY in ms)
            try:
                bd_timer = float(globals().get('boss_dialogue_timer', 0.0))
                bd_idx = int(globals().get('boss_dialogue_index', 0))
                full = str(globals().get('boss_dialogue_full', ''))
                bd_timer += float(dt_ms if 'dt_ms' in locals() else 16)
                delay = int(globals().get('STORY_CHAR_DELAY', 30))
                while bd_idx < len(full) and bd_timer >= delay:
                    bd_timer -= delay
                    bd_idx += 1
                visible = full[:bd_idx]
                globals()['boss_dialogue_timer'] = bd_timer
                globals()['boss_dialogue_index'] = bd_idx
                globals()['boss_dialogue_visible'] = visible
            except Exception:
                try:
                    globals()['boss_dialogue_visible'] = opening
                except Exception:
                    globals()['boss_dialogue_visible'] = opening

            # Draw opening (typewriter) in right-top area
            try:
                text_x = panel_x + 20
                text_y = panel_y + 18
                available_w = panel_w - 40
                lines = wrap_text(globals().get('boss_dialogue_visible', ''), game_font_small, available_w)
                ty = text_y
                for ln in lines:
                    s = game_font_small.render(ln, True, WHITE)
                    screen.blit(s, (text_x, ty))
                    ty += s.get_height() + 6
            except Exception:
                pass

            # --- Right-bottom: 3 stacked wide buttons for options ---
            try:
                btn_area_top = panel_y + int(panel_h * 0.52)
                btn_w = panel_w - 40
                btn_h = max(48, int((panel_h - (btn_area_top - panel_y) - 40) / 4))
                btn_x = panel_x + 20
                btns = []
                # Ensure exactly 3 options (pad with blanks if needed)
                while len(options) < 3:
                    options.append({'label': 'PAS', 'type': 'RATIONAL', 'text': '...','effect_desc': ''})
                for i, opt in enumerate(options[:3]):
                    by = btn_area_top + i * (btn_h + 12)
                    r = pygame.Rect(btn_x, by, btn_w, btn_h)
                    # button color depends on type
                    t = (opt.get('type') or '').upper()
                    if t == 'AGGRESSIVE':
                        color = (200, 50, 60)
                    elif t == 'EMPATHETIC':
                        color = (50, 140, 220)
                    else:
                        color = (120, 120, 120)
                    pygame.draw.rect(screen, color, r, border_radius=6)
                    # main text (option text)
                    try:
                        txt = opt.get('text', '')
                        t_s = game_font.render(txt, True, WHITE)
                        screen.blit(t_s, (r.x + 12, r.y + 8))
                    except Exception:
                        pass
                    # effect_desc small text under the main label
                    try:
                        eff = opt.get('effect_desc', '')
                        eff_s = pygame.font.SysFont(None, 18).render(eff, True, (230, 230, 230))
                        screen.blit(eff_s, (r.x + 12, r.y + 8 + (t_s.get_height() if 't_s' in locals() else 20)))
                    except Exception:
                        pass
                    key = f'GAMBIT_OPT_{i}'
                    menu_buttons_data[key] = r
                    # store mapping from key to option type
                    try:
                        if 'gambit_option_map' not in globals():
                            globals()['gambit_option_map'] = {}
                        globals()['gambit_option_map'][key] = (opt.get('type') or 'RATIONAL')
                    except Exception:
                        pass
            except Exception:
                pass

        except Exception:
            pass

        # --- Input handling for these buttons ---
        for event in events:
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                except Exception:
                    pass
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', None) == 1:
                mp = event.pos
                try:
                    for i in range(3):
                        key = f'GAMBIT_OPT_{i}'
                        if menu_buttons_data.get(key) and menu_buttons_data[key].collidepoint(mp):
                            # Map dialog type to gambit choice expected by handle_gambit_choice
                            typ = (globals().get('gambit_option_map', {}) or {}).get(key, 'RATIONAL')
                            mapping = {'AGGRESSIVE': 'KILL', 'EMPATHETIC': 'SPARE', 'RATIONAL': 'SPARE'}
                            mapped = mapping.get(typ.upper(), 'SPARE')
                            try:
                                handle_gambit_choice(mapped)
                            except Exception:
                                try:
                                    globals()['pending_gambit_choice'] = mapped
                                    globals()['game_state'] = STATE_GAMBIT_CHOICE
                                except Exception:
                                    pass
                            try:
                                globals()['CLICK_LOCKED'] = True
                            except Exception:
                                pass
                            break
                except Exception:
                    pass

    # Inserted Mercy (SPARE) phase handler if player chooses to spare a boss.
    elif game_state == STATE_MERCY_PHASE:
        # 1. ARKA PLANI TEMİZLE (EN ALT KATMAN)
        screen.fill((0, 0, 0))

        # 2. ARENAYI HESAPLA VE ÇİZ
        arena_w = 300
        arena_h = 300
        arena_x = (SCREEN_WIDTH - arena_w) // 2
        arena_y = (SCREEN_HEIGHT - arena_h) // 2
        # Global değişkeni güncelle
        globals()['mercy_arena_rect'] = pygame.Rect(arena_x, arena_y, arena_w, arena_h)

        # Beyaz Çerçeveyi Çiz (4px kalınlık)
        try:
            pygame.draw.rect(screen, (255, 255, 255), globals()['mercy_arena_rect'], 4)
        except Exception:
            pass

        # 3. OYUNCU (RUH) KONTROLÜ VE ÇİZİMİ
        if 'mercy_player' not in globals() or globals().get('mercy_player') is None:
            try:
                # MercySoul sınıfının tanımlı olduğundan emin ol, yoksa basit rect kullan
                if 'MercySoul' in globals():
                    globals()['mercy_player'] = MercySoul()
            except Exception:
                pass
        
        mercy_p = globals().get('mercy_player')
        if mercy_p:
            try:
                # dt_ms değişkeni ana döngüden gelmeli
                dt_sec = dt_ms / 1000.0 if 'dt_ms' in locals() else 0.016
                if hasattr(mercy_p, 'update'):
                    mercy_p.update(dt_sec)
                if hasattr(mercy_p, 'draw'):
                    mercy_p.draw(screen)
            except Exception:
                pass

        # 4. MERMİLERİ GÜNCELLE VE ÇİZ
        w_timer = globals().get('mercy_warmup_timer', 0)
        if w_timer > 0:
            globals()['mercy_warmup_timer'] = w_timer - (dt_ms / 1000.0 if 'dt_ms' in locals() else 0.016)
            try:
                font = globals().get('game_font', pygame.font.SysFont(None, 40))
                txt = font.render("HAZIR OL!", True, (255, 0, 0))
                screen.blit(txt, (SCREEN_WIDTH//2 - txt.get_width()//2, arena_y - 50))
            except Exception:
                pass
        else:
            try:
                # update_mercy_logic fonksiyonunun varlığını kontrol et
                if 'update_mercy_logic' in globals():
                    update_mercy_logic(dt_ms / 1000.0 if 'dt_ms' in locals() else 0.016)
            except Exception:
                pass

        proj_list = globals().get('mercy_projectiles', [])
        # Clip drawing to arena so projectiles don't render outside
        try:
            screen.set_clip(globals().get('mercy_arena_rect'))
        except Exception:
            pass

        for p in list(proj_list):
            try:
                if hasattr(p, 'update'):
                    p.update(dt_ms / 1000.0 if 'dt_ms' in locals() else 0.016)
                if hasattr(p, 'draw'):
                    p.draw(screen)
                
                # Çarpışma (daraltılmış hitbox)
                try:
                    hitbox = None
                    if mercy_p and hasattr(mercy_p, 'rect'):
                        # shrink hitbox from center; with 64x64 visual, -30,-30 -> 34x34 hitbox
                        try:
                            hitbox = mercy_p.rect.inflate(-30, -30)
                        except Exception:
                            hitbox = mercy_p.rect
                except Exception:
                    hitbox = None

                if mercy_p and hasattr(p, 'rect') and hitbox is not None and p.rect.colliderect(hitbox):
                    p.alive = False
                    globals()['mercy_hit_count'] = globals().get('mercy_hit_count', 0) + 1
                    current_money = globals().get('MONEY', 0)
                    penalty = 5 * globals().get('mercy_hit_count', 1)
                    globals()['MONEY'] = max(0, current_money - penalty)
                    # Create score splash and flash timer
                    try:
                        s = ScoreSplash(f"-{int(penalty)}$", mercy_p.rect.centerx, mercy_p.rect.top, (255, 0, 0))
                        try:
                            scores_splash_group.add(s)
                        except Exception:
                            try:
                                globals()['scores_splash_group'].add(s)
                            except Exception:
                                pass
                    except Exception:
                        pass
                    try:
                        globals()['mercy_hit_flash_time'] = pygame.time.get_ticks()
                    except Exception:
                        pass
                    
                if hasattr(p, 'alive') and not p.alive:
                    try:
                        proj_list.remove(p)
                    except ValueError:
                        pass
            except Exception:
                pass
        # restore clip so HUD and other UI draw normally
        try:
            screen.set_clip(None)
        except Exception:
            pass

        # Update and draw score splashes for immediate feedback
        try:
            try:
                scores_splash_group.update(dt_ms / 1000.0 if 'dt_ms' in locals() else 0.016)
            except Exception:
                scores_splash_group.update()
            for sp in list(scores_splash_group.sprites()):
                try:
                    if hasattr(sp, 'draw'):
                        sp.draw(screen)
                except Exception:
                    pass
        except Exception:
            pass
        # 5. SÜRE VE BİTİŞ KONTROLÜ
        m_timer = globals().get('mercy_timer', 0)
        m_duration = globals().get('mercy_duration', 10000)
        
        m_timer += (dt_ms if 'dt_ms' in locals() else 16)
        globals()['mercy_timer'] = m_timer
        
        # Süre çubuğu
        bar_width = 300
        try:
            bar_fill = int(bar_width * min(1.0, m_timer / m_duration))
        except Exception:
            bar_fill = 0
        pygame.draw.rect(screen, (50, 50, 50), (SCREEN_WIDTH//2 - 150, arena_y + arena_h + 20, 300, 10))
        pygame.draw.rect(screen, (255, 255, 0), (SCREEN_WIDTH//2 - 150, arena_y + arena_h + 20, bar_fill, 10))

        if m_timer >= m_duration:
            globals()['gambit_result_message'] = "Ruhunu arındırdın."
            globals()['game_state'] = STATE_GAMBIT_RESULT

        # 6. HASAR FLAŞI (HUD'dan ÖNCE)
        try:
            hit_t = globals().get('mercy_hit_flash_time', 0)
            if hit_t and pygame.time.get_ticks() < (int(hit_t) + 100):
                try:
                    overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                    overlay.fill((255, 0, 0, 100))
                    screen.blit(overlay, (0, 0))
                except Exception:
                    pass
        except Exception:
            pass

        # 7. HUD
        try:
            draw_hud(screen)
        except Exception:
            pass

    elif game_state == STATE_BOSS_DEFEATED_B:
        # Show the boss harmed image left and the current_boss_story on the right
        screen.fill((10, 10, 20))
        screen.blit(background_image, (0, 0))
        draw_hud(screen)
        try:
            left_cx = int(SCREEN_WIDTH * 0.25)
            left_cy = int(SCREEN_HEIGHT * 0.5)
            bimg = None
            if enemy is not None:
                bimg = getattr(enemy, 'harmed_sprite', None) or getattr(enemy, 'current_sprite', None)
            if bimg is None:
                bimg = pygame.Surface((200, 200))
                bimg.fill((80, 80, 120))
            max_w = int(SCREEN_WIDTH * 0.4)
            w0, h0 = bimg.get_width(), bimg.get_height()
            scale_w = min(max_w, max(80, w0))
            scale_h = int(h0 * (scale_w / max(1, w0)))
            bi = pygame.transform.smoothscale(bimg, (scale_w, scale_h))
            bref = bi.get_rect(center=(left_cx, left_cy))
            screen.blit(bi, bref.topleft)
        except Exception:
            pass

        # Right story box
        try:
            box_x = int(SCREEN_WIDTH * 0.52)
            box_w = int(SCREEN_WIDTH * 0.44)
            box_y = int(HUD_Y + 20)
            box_h = int(SCREEN_HEIGHT - box_y - 40)
            panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 200))
            screen.blit(panel, (box_x, box_y))

            # --- HİKAYE METNİ (TYPEWRITER + TİTREŞİM) ---
            # Update the typewriter state using dt in milliseconds.
            try:
                # accumulate elapsed ms for this frame (dt_ms available in main loop)
                try:
                    story_timer += int(dt_ms)
                except Exception:
                    # fallback to clock.get_time() if dt_ms isn't present
                    try:
                        story_timer += int(clock.get_time())
                    except Exception:
                        story_timer += 16

                # reveal next character when timer exceeds delay
                if story_timer >= STORY_CHAR_DELAY and story_text_index < len(current_boss_story):
                    story_timer = 0
                    try:
                        visible_story_text += current_boss_story[story_text_index]
                    except Exception:
                        # if current_boss_story indexing fails, append nothing
                        pass
                    story_text_index += 1
            except Exception:
                pass

            # choose what to draw: the progressively revealed visible_story_text
            text_to_draw = visible_story_text if visible_story_text else current_boss_story
            if not text_to_draw:
                text_to_draw = "HATA: Boss hikayesi yüklenemedi. (Kod: B_STORY_NF)"

            # Wrap and draw lines; while still typing, apply a tiny random shake per-line
            try:
                lines = wrap_text(text_to_draw, game_font_small, box_w - 30)
                ty = box_y + 20
                for i, ln in enumerate(lines):
                    s = game_font_small.render(ln, True, WHITE)
                    text_rect = s.get_rect()
                    base_x = box_x + 16
                    base_y = ty

                    # If the story is still being typed, apply a small vibrate offset
                    if story_text_index < len(current_boss_story):
                        draw_x = base_x + random.randint(-1, 1)
                        draw_y = base_y + random.randint(-1, 1)
                        screen.blit(s, (draw_x, draw_y))
                    else:
                        screen.blit(s, (base_x, base_y))

                    ty += s.get_height() + 6
            except Exception:
                pass

            # Continue button appears after story text
            btn_h = 46
            btn_w = 200
            btn_x = box_x + (box_w - btn_w) // 2
            btn_y = box_y + box_h - btn_h - 20
            btn = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            pygame.draw.rect(screen, (60, 160, 80), btn)
            t = game_font_small.render('DEVAM ET', True, WHITE)
            screen.blit(t, (btn.centerx - t.get_width()//2, btn.centery - t.get_height()//2))
            menu_buttons_data['BOSS_CONTINUE'] = btn
        except Exception:
            pass

        for event in events:
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                except Exception:
                    pass
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', None) == 1:
                mp = event.pos
                try:
                    if menu_buttons_data.get('BOSS_CONTINUE') and menu_buttons_data['BOSS_CONTINUE'].collidepoint(mp):
                        game_state = STATE_GAMBIT_CHOICE
                        break
                except Exception:
                    pass

    elif game_state == STATE_GAMBIT_CHOICE:
        # Gambit choice: left boss image; right two buttons: ÖLDÜR / BAĞIŞLA
        screen.fill((10, 10, 20))
        screen.blit(background_image, (0, 0))
        draw_hud(screen)
        try:
            left_cx = int(SCREEN_WIDTH * 0.25)
            left_cy = int(SCREEN_HEIGHT * 0.5)
            bimg = None
            if enemy is not None:
                bimg = getattr(enemy, 'harmed_sprite', None) or getattr(enemy, 'current_sprite', None)
            if bimg is None:
                bimg = pygame.Surface((200, 200))
                bimg.fill((80, 80, 120))
            max_w = int(SCREEN_WIDTH * 0.4)
            w0, h0 = bimg.get_width(), bimg.get_height()
            scale_w = min(max_w, max(80, w0))
            scale_h = int(h0 * (scale_w / max(1, w0)))
            bi = pygame.transform.smoothscale(bimg, (scale_w, scale_h))
            bref = bi.get_rect(center=(left_cx, left_cy))
            screen.blit(bi, bref.topleft)
        except Exception:
            pass

        try:
            box_x = int(SCREEN_WIDTH * 0.52)
            box_w = int(SCREEN_WIDTH * 0.44)
            box_y = int(HUD_Y + 20)
            box_h = int(SCREEN_HEIGHT - box_y - 40)
            panel = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            panel.fill((0, 0, 0, 200))
            screen.blit(panel, (box_x, box_y))

            prompt = 'Bir karar ver: Bu canavarı ÖLDÜR ya da BAĞIŞLA.'
            lines = wrap_text(prompt, game_font_small, box_w - 30)
            ty = box_y + 20
            for ln in lines:
                s = game_font_small.render(ln, True, WHITE)
                screen.blit(s, (box_x + 16, ty))
                ty += s.get_height() + 6

            # Two large buttons
            btn_h = 56
            btn_w = int((box_w - 48) / 2)
            btn_y = box_y + box_h - btn_h - 20
            b1 = pygame.Rect(box_x + 16, btn_y, btn_w, btn_h)
            b2 = pygame.Rect(box_x + 16 + btn_w + 16, btn_y, btn_w, btn_h)
            pygame.draw.rect(screen, (200, 60, 60), b1)
            pygame.draw.rect(screen, (60, 160, 80), b2)
            t1 = game_font_small.render('ÖLDÜR', True, WHITE)
            t2 = game_font_small.render('BAĞIŞLA', True, WHITE)
            screen.blit(t1, (b1.centerx - t1.get_width()//2, b1.centery - t1.get_height()//2))
            screen.blit(t2, (b2.centerx - t2.get_width()//2, b2.centery - t2.get_height()//2))
            menu_buttons_data['GAMBIT_KILL'] = b1
            menu_buttons_data['GAMBIT_SPARE'] = b2
        except Exception:
            pass

        for event in events:
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                except Exception:
                    pass
            if event.type == pygame.MOUSEBUTTONDOWN and getattr(event, 'button', None) == 1:
                mp = event.pos
                try:
                    if menu_buttons_data.get('GAMBIT_KILL') and menu_buttons_data['GAMBIT_KILL'].collidepoint(mp):
                        try:
                            handle_gambit_choice('KILL')
                        except Exception:
                            pass
                        break
                    if menu_buttons_data.get('GAMBIT_SPARE') and menu_buttons_data['GAMBIT_SPARE'].collidepoint(mp):
                        try:
                            handle_gambit_choice('SPARE')
                        except Exception:
                            pass
                        break
                except Exception:
                    pass

    elif game_state == STATE_GAME_OVER:
        for event in events:
            # handle resize events and fullscreen toggle
            if event.type in (pygame.VIDEORESIZE, getattr(pygame, 'WINDOWRESIZED', None)):
                handle_resize_event(event)
                continue
            if event.type == pygame.KEYDOWN:
                try:
                    if event.key == pygame.K_F11:
                        toggle_fullscreen()
                        continue
                except Exception:
                    pass
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Restart button (we'll place it in the center)
                mx, my = event.pos
                restart_rect = pygame.Rect((SCREEN_WIDTH//2) - 100, (SCREEN_HEIGHT//2) + 40, 200, 50)
                if restart_rect.collidepoint((mx, my)):
                    try:
                        reset_game()
                    except Exception:
                        pass
                    # After a full reset, return player to the main menu
                    try:
                        game_state = STATE_MAIN_MENU
                    except Exception:
                        pass

        # Draw game over screen (with HUD)
        screen.fill((10, 10, 20))
        screen.blit(background_image, (0, 0))
        draw_hud(screen)
        over_text = game_font.render("OYUN BİTTİ", True, WHITE)
        over_rect = over_text.get_rect(center=(SCREEN_WIDTH//2, SCREEN_HEIGHT//2 - 40))
        screen.blit(over_text, over_rect)

        # Draw restart button
        restart_rect = pygame.Rect((SCREEN_WIDTH//2) - 100, (SCREEN_HEIGHT//2) + 40, 200, 50)
        hover = restart_rect.collidepoint(pygame.mouse.get_pos())
        rcolor = (70, 180, 70) if hover else (50, 160, 50)
        pygame.draw.rect(screen, rcolor, restart_rect)
        pygame.draw.rect(screen, (255,255,255), restart_rect, 2)
        restart_text = game_font_small.render("Yeniden Başla", True, WHITE)
        rt_rect = restart_text.get_rect(center=restart_rect.center)
        screen.blit(restart_text, rt_rect)

        

    # End of frame: present the composed frame
    # Update and draw lightweight particles (background ambience)
    try:
        update_particles(dt_ms)
        try:
            draw_particles(screen)
        except Exception:
            pass
    except Exception:
        pass

    # --- GENEL GÜNCELLEME: ScoreSplash (her kare çalışmalı) ---
    try:
        try:
            dt_seconds = float(clock.get_time()) / 1000.0
        except Exception:
            dt_seconds = float(dt) if 'dt' in globals() else 0.016

        try:
            scores_splash_group.update(dt_seconds)
        except Exception as e:
            try:
                print(f"HATA: Splash group güncellenemedi: {e}")
            except Exception:
                pass

        try:
            # Use individual draw to respect sprite draw implementation
            for s in scores_splash_group:
                s.draw(screen)
        except Exception:
            try:
                scores_splash_group.draw(screen)
            except Exception:
                pass
    except Exception:
        pass

    

    try:
        # Reset one-frame click lock so next frame can accept clicks
        try:
            if globals().get('CLICK_LOCKED'):
                try:
                    pass
                except Exception:
                    pass
            globals()['CLICK_LOCKED'] = False
        except Exception:
            try:
                if CLICK_LOCKED:
                    try:
                        pass
                    except Exception:
                        pass
                CLICK_LOCKED = False
            except Exception:
                pass
        pygame.display.flip()
    except Exception:
        pass

# Döngü bittiğinde (pencere kapandığında) oyunu düzgünce kapat
pygame.quit()
sys.exit()