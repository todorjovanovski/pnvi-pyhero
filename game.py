import pygame, sys, math, random, tkinter as tk, os, librosa
from tkinter import filedialog
import pygame.gfxdraw

# ------------------ Game Constants ------------------
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

HIT_WINDOW = 0.2  # Allowed timing error (seconds)

TRAVEL_TIME_MIN = 1.5
TRAVEL_TIME_MAX = 2.5

# Long note parameters.
LONG_NOTE_PROB = 0.2  # 20% chance a note is long
LONG_NOTE_DURATION_MIN = 0.5  # Minimum hold duration (seconds)
LONG_NOTE_DURATION_MAX = 2.0  # Maximum hold duration (seconds)
hold_score_rate = 50  # Points per second for holding a long note

base_score = 100

# Lane geometry: five lanes.
lane_width = SCREEN_WIDTH / 5
bottom_lane_centers = [lane_width * i + lane_width / 2 for i in range(5)]
top_boundaries = [SCREEN_WIDTH / 2 + (i - 2.5) * (lane_width / 3) for i in range(6)]
top_lane_centers = [(top_boundaries[i] + top_boundaries[i + 1]) / 2 for i in range(5)]

# Mapping keys to lanes.
lane_keys = {
    0: pygame.K_z,
    1: pygame.K_x,
    2: pygame.K_c,
    3: pygame.K_v,
    4: pygame.K_b
}

# Colors for lanes/buttons.
lane_colors = {
    0: (0, 255, 0),  # Green
    1: (255, 0, 0),  # Red
    2: (255, 255, 0),  # Yellow
    3: (0, 0, 255),  # Blue
    4: (255, 150, 0)  # White
}

allowed_misses = 6  # Default medium difficulty

bottom_margin = 50  # Margin from the bottom of the screen.
game_area_height = 400  # Height of the game area (notes travel area).

# Update the global positions so that the game area is at the bottom.
SPAWN_Y = SCREEN_HEIGHT - bottom_margin - game_area_height
HIT_Y = SCREEN_HEIGHT - bottom_margin

# ------------------ File Selection & Loading ------------------
root = tk.Tk()
root.withdraw()

pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
SCREEN_WIDTH, SCREEN_HEIGHT = screen.get_size()

pygame.display.set_caption("PyHero - Loading")
clock = pygame.time.Clock()

try:
    miss_sound = pygame.mixer.Sound("utils/missed_note.wav")
except Exception as e:
    print("Miss sound not found, continuing without it.")
    miss_sound = None


# ------------------ Helper Functions ------------------
def draw_text(surface, text, font, color, center):
    """Render and blit text centered on the given surface."""
    text_surf = font.render(text, True, color)
    surface.blit(text_surf, text_surf.get_rect(center=center))


def create_button_rects(start_y, count, button_width, button_height, spacing, screen_width):
    """Generate a list of pygame.Rect for buttons."""
    rects = []
    for i in range(count):
        rect = pygame.Rect((screen_width - button_width) // 2,
                           start_y + i * (button_height + spacing),
                           button_width, button_height)
        rects.append(rect)
    return rects


def draw_options(surface, options, button_rects, font, mouse_pos,
                 default_color=(50, 50, 50), hover_color=(100, 100, 100),
                 border_color=(255, 255, 255)):
    """Draw a list of option buttons with text."""
    for i, (text, _) in enumerate(options):
        rect = button_rects[i]
        color = hover_color if rect.collidepoint(mouse_pos) else default_color
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, border_color, rect, 2)
        text_surf = font.render(text, True, border_color)
        surface.blit(text_surf, text_surf.get_rect(center=rect.center))


def update_and_draw_effects(effects, surface, color):
    """
    Update each effect’s life and radius, then draw it.
    Expects each effect to be a dict with keys: 'life', 'radius', and 'pos'.
    """
    for effect in effects[:]:
        effect['life'] -= 1
        if effect['life'] <= 0:
            effects.remove(effect)
            continue
        effect['radius'] += 2
        s = pygame.Surface((effect['radius'] * 2, effect['radius'] * 2), pygame.SRCALPHA)
        alpha = max(0, int(255 * (effect['life'] / 20)))
        pygame.gfxdraw.filled_circle(s, effect['radius'], effect['radius'],
                                     effect['radius'], (*color, alpha))
        pygame.gfxdraw.aacircle(s, effect['radius'], effect['radius'],
                                effect['radius'], (*color, alpha))
        s_rect = s.get_rect(center=effect['pos'])
        surface.blit(s, s_rect)


def update_and_draw_hit_effects(surface):
    update_and_draw_effects(hit_effects, surface, (255, 255, 255))


def update_and_draw_miss_effects(surface):
    update_and_draw_effects(miss_effects, surface, (255, 50, 50))


def option_screen(title, title_color, score, options):
    """
    Generic screen to display a title, a score, and a list of options.
    Returns the option value when one is selected.
    """
    running = True
    title_font = pygame.font.SysFont("Arial", 64)
    button_font = pygame.font.SysFont("Arial", 36)
    button_width = 400
    button_height = 60
    spacing = 20
    start_y = 300
    button_rects = create_button_rects(start_y, len(options), button_width, button_height, spacing, SCREEN_WIDTH)

    while running:
        screen.fill((20, 20, 20))
        draw_text(screen, title, title_font, title_color, (SCREEN_WIDTH // 2, 100))
        draw_text(screen, f"Your Score: {score}", button_font, (255, 255, 255), (SCREEN_WIDTH // 2, 200))

        mouse_pos = pygame.mouse.get_pos()
        draw_options(screen, options, button_rects, button_font, mouse_pos)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(button_rects):
                    if rect.collidepoint(event.pos):
                        return options[i][1]
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return "restart"
                elif event.key == pygame.K_n:
                    return "new"
                elif event.key == pygame.K_m:
                    return "menu"
                elif event.key == pygame.K_q:
                    return "quit"
        clock.tick(FPS)


# ------------------ Screens ------------------
def menu_screen():
    """Main menu screen."""
    menu_running = True
    title_font = pygame.font.SysFont("Arial", 64)
    button_font = pygame.font.SysFont("Arial", 36)
    options = [
        ("Start Game (S)", "start"),
        ("Difficulty (D)", "difficulty"),
        ("Guide (G)", "guide"),
        ("Quit (Q)", "quit")
    ]
    button_width = 400
    button_height = 60
    spacing = 20
    start_y = 200
    button_rects = create_button_rects(start_y, len(options), button_width, button_height, spacing, SCREEN_WIDTH)
    selected = None

    while menu_running:
        screen.fill((20, 20, 20))
        draw_text(screen, "PyHero", title_font, (255, 255, 255), (SCREEN_WIDTH // 2, 100))
        mouse_pos = pygame.mouse.get_pos()
        draw_options(screen, options, button_rects, button_font, mouse_pos)
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(button_rects):
                    if rect.collidepoint(event.pos):
                        selected = options[i][1]
                        menu_running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_s:
                    selected = "start"
                    menu_running = False
                elif event.key == pygame.K_d:
                    selected = "difficulty"
                    menu_running = False
                elif event.key == pygame.K_g:
                    selected = "guide"
                    menu_running = False
                elif event.key == pygame.K_q:
                    selected = "quit"
                    menu_running = False
        clock.tick(FPS)
    return selected


def difficulty_screen():
    """Screen to select game difficulty."""
    running = True
    title_font = pygame.font.SysFont("Arial", 48)
    button_font = pygame.font.SysFont("Arial", 36)
    options = [
        ("Chill (no limit) - [C]", -1),
        ("Easy (10 misses allowed) - [E]", 10),
        ("Medium (6 misses allowed) - [M]", 6),
        ("Hard (3 misses allowed) - [H]", 3),
        ("Extreme (0 misses allowed) - [X]", 0)
    ]
    button_width = 500
    button_height = 50
    spacing = 15
    start_y = 200
    button_rects = create_button_rects(start_y, len(options), button_width, button_height, spacing, SCREEN_WIDTH)
    selected = None

    while running:
        screen.fill((20, 20, 20))
        draw_text(screen, "Select Difficulty", title_font, (255, 255, 255), (SCREEN_WIDTH // 2, 100))
        mouse_pos = pygame.mouse.get_pos()

        # Draw each option with custom coloring if it matches the current difficulty.
        for i, (text, value) in enumerate(options):
            rect = button_rects[i]
            base_color = (255, 125, 0, 50) if allowed_misses == value else (50, 50, 50)
            color = (100, 100, 100) if rect.collidepoint(mouse_pos) else base_color
            pygame.draw.rect(screen, color, rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 2)
            text_surf = button_font.render(text, True, (255, 255, 255))
            screen.blit(text_surf, text_surf.get_rect(center=rect.center))

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for i, rect in enumerate(button_rects):
                    if rect.collidepoint(event.pos):
                        selected = options[i][1]
                        running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_e:
                    selected = 10
                    running = False
                elif event.key == pygame.K_m:
                    selected = 6
                    running = False
                elif event.key == pygame.K_h:
                    selected = 3
                    running = False
                elif event.key == pygame.K_x:
                    selected = 0
                    running = False
                elif event.key == pygame.K_c:
                    selected = -1
                    running = False
        clock.tick(FPS)
    return selected


def guide_screen():
    """Display the guide and controls."""
    running = True
    title_font = pygame.font.SysFont("Arial", 48)
    instr_font = pygame.font.SysFont("Arial", 28)
    button_font = pygame.font.SysFont("Arial", 26)
    guide_lines = [
        "Guide:",
        "PUT THE SONGS THAT YOU WANT TO PLAY ON IN THE GAME FOLDER.",
        "Hit falling notes as they reach the hit line.",
        "For long notes, hold the key to earn extra points.",
        "Avoid too many misses!"
    ]
    back_rect = pygame.Rect(20, SCREEN_HEIGHT - 70, 150, 50)

    while running:
        screen.fill((20, 20, 20))
        y = 80
        for line in guide_lines:
            text = instr_font.render(line, True, (255, 255, 255))
            screen.blit(text, (50, y))
            y += 40

        # Draw controls information.
        controls_title = instr_font.render("Controls:", True, (255, 255, 255))
        screen.blit(controls_title, (50, y + 10))
        keys = [("Z", lane_colors[0]), ("X", lane_colors[1]),
                ("C", lane_colors[2]), ("V", lane_colors[3]),
                ("B", lane_colors[4])]
        x_start = 100
        y_start = y + 150
        for i, (key, color) in enumerate(keys):
            pygame.gfxdraw.filled_circle(screen, x_start + i * 150, y_start, 40, color)
            pygame.gfxdraw.aacircle(screen, x_start + i * 150, y_start, 40, color)
            key_text = instr_font.render(key, True, (255, 255, 255))
            screen.blit(key_text, key_text.get_rect(center=(x_start + i * 150, y_start + 70)))

        # Draw back button.
        pygame.draw.rect(screen, (50, 50, 50), back_rect)
        pygame.draw.rect(screen, (255, 255, 255), back_rect, 2)
        back_text = button_font.render("Back (ESC)", True, (255, 255, 255))
        screen.blit(back_text, back_text.get_rect(center=back_rect.center))

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_SPACE:
                    running = False
        clock.tick(FPS)


def song_completed_screen(score):
    """Screen shown when a song is successfully completed."""
    return option_screen("Song Completed!", (255, 255, 0), score, [
        ("Restart (R)", "restart"),
        ("New Song (N)", "new"),
        ("Main Menu (M)", "menu"),
        ("Quit (Q)", "quit")
    ])


def game_over_screen(score):
    """Screen shown when the game is over."""
    return option_screen("Game Over!", (255, 0, 0), score, [
        ("Restart (R)", "restart"),
        ("New Song (N)", "new"),
        ("Main Menu (M)", "menu"),
        ("Quit (Q)", "quit")
    ])


def song_selection_screen():
    """Screen for selecting a song from the current folder."""
    allowed_extensions = ['.ogg', '.mp3', '.wav']
    button_font = pygame.font.SysFont("Arial", 26)
    files = [f for f in os.listdir('.') if os.path.isfile(f) and
             os.path.splitext(f)[1].lower() in allowed_extensions]

    files.sort()
    selected_index = 0
    running = True
    back_rect = pygame.Rect(20, SCREEN_HEIGHT - 20 - 70, 150, 70)
    option_font = pygame.font.SysFont("Arial", 36)
    start_y = 200
    spacing = 50

    while running:
        screen.fill((20, 20, 20))
        title_font = pygame.font.SysFont("Arial", 48)
        if not files:
            draw_text(screen, "You have no songs in the current folder.", title_font, (255, 125, 0), (SCREEN_WIDTH // 2, 100))
            pygame.display.flip()
            pygame.time.delay(2000)
            return None
                
        draw_text(screen, "Select a Song", title_font, (255, 255, 255), (SCREEN_WIDTH // 2, 100))

        # Draw back button.
        pygame.draw.rect(screen, (50, 50, 50), back_rect)
        pygame.draw.rect(screen, (255, 255, 255), back_rect, 2)
        back_text = button_font.render("Back", True, (255, 255, 255))
        screen.blit(back_text, back_text.get_rect(center=back_rect.center))

        mouse_pos = pygame.mouse.get_pos()
        for i, song in enumerate(files):
            option_rect = pygame.Rect(0, 0, SCREEN_WIDTH, spacing)
            option_rect.center = (SCREEN_WIDTH // 2, start_y + i * spacing)
            if option_rect.collidepoint(mouse_pos):
                color = (255, 255, 0)
                selected_index = i
            elif i == selected_index:
                color = (255, 255, 0)
            else:
                color = (255, 255, 255)
            option_text = option_font.render(song, True, color)
            screen.blit(option_text, option_text.get_rect(center=option_rect.center))

        pygame.display.flip()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_index = (selected_index - 1) % len(files)
                elif event.key == pygame.K_DOWN:
                    selected_index = (selected_index + 1) % len(files)
                elif event.key == pygame.K_RETURN:
                    return files[selected_index]
                elif event.key == pygame.K_ESCAPE:
                    return None
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if back_rect.collidepoint(event.pos):
                    return None
                for i, song in enumerate(files):
                    option_rect = pygame.Rect(0, 0, SCREEN_WIDTH, spacing)
                    option_rect.center = (SCREEN_WIDTH // 2, start_y + i * spacing)
                    if option_rect.collidepoint(event.pos):
                        return song
        clock.tick(FPS)


# ------------------ Effects Data ------------------
hit_effects = []
miss_effects = []

# ------------------ Note Class ------------------
class Note:
    def __init__(self, hit_time, lane, travel_time, duration=0.0):
        self.hit_time = hit_time  # Scheduled hit time (seconds)
        self.lane = lane  # Lane index (0-4)
        self.travel_time = travel_time  # Note-specific travel time
        self.duration = duration  # Duration for long notes; 0 means short
        self.hit = False
        self.missed = False

    def update(self, current_time):
        return (self.hit_time - current_time) / self.travel_time

    def get_head_pos(self, current_time):
        progress = self.update(current_time)
        clamped = max(0, min(1, 1 - progress))
        y = SPAWN_Y + clamped * (HIT_Y - SPAWN_Y)
        top_x = top_lane_centers[self.lane]
        bottom_x = bottom_lane_centers[self.lane]
        x = top_x + (bottom_x - top_x) * clamped
        scale = 0.5 + 0.5 * clamped
        return (x, y, scale)

    def draw(self, surface, current_time, key_pressed=False):
        x, y, scale = self.get_head_pos(current_time)
        if self.duration > 0:
            tail_time = self.hit_time + self.duration
            tail_progress = (tail_time - current_time) / self.travel_time
            clamped_tail = max(0, min(1, 1 - tail_progress))
            top_x = top_lane_centers[self.lane]
            bottom_x = bottom_lane_centers[self.lane]
            tail_x = top_x + (bottom_x - top_x) * clamped_tail
            tail_y = SPAWN_Y + clamped_tail * (HIT_Y - SPAWN_Y)
            temp_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            glow_alpha = 255 if key_pressed else 100
            glow_color = (255, 255, 255, glow_alpha)
            pygame.draw.line(temp_surf, glow_color, (int(x), int(y)), (int(tail_x), int(tail_y)), 20)
            pygame.draw.line(temp_surf, lane_colors[self.lane], (int(x), int(y)), (int(tail_x), int(tail_y)), 10)
            surface.blit(temp_surf, (0, 0))
        note_width = 75 * scale
        note_height = 50 * scale
        rect = pygame.Rect(0, 0, note_width, note_height)
        rect.center = (x, y)
        pygame.gfxdraw.filled_ellipse(surface, rect.centerx, rect.centery, int(note_width / 2), int(note_height / 2),
                                      lane_colors[self.lane])
        pygame.gfxdraw.aaellipse(surface, rect.centerx, rect.centery, int(note_width / 2), int(note_height / 2),
                                 (0, 0, 0))


# ------------------ Main Game Loop ------------------
def run_game():
    global hit_effects, miss_effects, chart, SPAWN_Y, HIT_Y, lane_width, bottom_lane_centers, top_lane_centers
    # Outer loop to allow restarting with the same song.
    while True:
        # Recalculate geometry values based on the full-screen dimensions.
        lane_width = SCREEN_WIDTH / 5
        bottom_lane_centers = [lane_width * i + lane_width / 2 for i in range(5)]
        # Set spawn and hit lines at 15% and 85% of the screen height for a centered layout.
        SPAWN_Y = SCREEN_HEIGHT * 0.15
        HIT_Y = SCREEN_HEIGHT * 0.85
        top_boundaries = [SCREEN_WIDTH / 2 + (i - 2.5) * (lane_width / 3) for i in range(6)]
        top_lane_centers = [(top_boundaries[i] + top_boundaries[i + 1]) / 2 for i in range(5)]

        # Initialize game state.
        active_notes = []
        chart_index = 0
        score = 0
        multiplier = 1
        consecutive_hits = 0
        consecutive_misses = 0
        multiplier_flash_timer = 0
        button_flash = [0 for _ in range(5)]

        # Restart song playback.
        pygame.mixer.music.rewind()
        pygame.mixer.music.play()
        song_start_ticks = pygame.time.get_ticks()
        game_over = False
        finished_normally = False
        action = None  # To capture end-of-game action.

        # Main game loop.
        while True:
            dt = clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                # Allow immediate return to main menu by pressing ESC, even during gameplay.
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        action = "menu"
                        pygame.mixer.music.stop()
                        game_over = True
                        break
                    # Process note hit keys if the game is not over.
                    if not game_over:
                        for guitar_lane, key in lane_keys.items():
                            if event.key == key:
                                hit_success = False
                                for note in active_notes:
                                    if note.lane == guitar_lane and not note.hit:
                                        current_time = (pygame.time.get_ticks() - song_start_ticks) / 1000.0
                                        if abs(note.hit_time - current_time) <= HIT_WINDOW:
                                            note.hit = True
                                            hit_success = True
                                            consecutive_hits += 1
                                            consecutive_misses = 0
                                            multiplier = min(5, 1 + consecutive_hits // 10)
                                            score += base_score * multiplier
                                            multiplier_flash_timer = 20
                                            button_flash[guitar_lane] = 10
                                            pos = note.get_head_pos(current_time)[:2]
                                            hit_effects.append({'pos': pos, 'radius': 10, 'life': 20})
                                            break
                                if not hit_success:
                                    consecutive_hits = 0
                                    multiplier = 1
                                    consecutive_misses += 1
                                    current_time = (pygame.time.get_ticks() - song_start_ticks) / 1000.0
                                    for note in active_notes:
                                        if note.lane == guitar_lane and not note.hit:
                                            pos = note.get_head_pos(current_time)[:2]
                                            break
                                    else:
                                        pos = (bottom_lane_centers[guitar_lane], HIT_Y)
                                    if miss_sound:
                                        miss_sound.play()
                                    miss_effects.append({'pos': pos, 'radius': 10, 'life': 20})
                                    if allowed_misses != -1 and consecutive_misses >= allowed_misses:
                                        game_over = True
                # Process end-of-game key presses (when game_over is True).
                if game_over and event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        action = "restart"
                    elif event.key == pygame.K_n:
                        action = "new"
                    elif event.key == pygame.K_m:
                        action = "menu"
                    elif event.key == pygame.K_q:
                        action = "quit"
                    break
            # If ESC was pressed (or another game-ending key), exit the event loop.
            if game_over:
                break

            current_time = (pygame.time.get_ticks() - song_start_ticks) / 1000.0
            pressed = pygame.key.get_pressed()

            if not game_over:
                # Spawn new notes based on the chart.
                while chart_index < len(chart) and chart[chart_index][0] <= current_time + chart[chart_index][2]:
                    hit_time, guitar_lane, travel_time, duration = chart[chart_index]
                    active_notes.append(Note(hit_time, guitar_lane, travel_time, duration))
                    chart_index += 1

                # Update each note.
                for note in active_notes[:]:
                    progress = note.update(current_time)
                    if note.duration == 0:
                        if (not note.hit) and progress < -0.2:
                            note.missed = True
                            if miss_sound:
                                miss_sound.play()
                            pos = note.get_head_pos(current_time)[:2]
                            miss_effects.append({'pos': pos, 'radius': 10, 'life': 20})
                            active_notes.remove(note)
                            consecutive_hits = 0
                            multiplier = 1
                            consecutive_misses += 1
                            if allowed_misses != -1 and consecutive_misses >= allowed_misses:
                                game_over = True
                        elif note.hit:
                            active_notes.remove(note)
                    else:
                        if (not note.hit) and progress < -0.2:
                            note.missed = True
                            if miss_sound:
                                miss_sound.play()
                            pos = note.get_head_pos(current_time)[:2]
                            miss_effects.append({'pos': pos, 'radius': 10, 'life': 20})
                            active_notes.remove(note)
                            consecutive_hits = 0
                            multiplier = 1
                            consecutive_misses += 1
                            if allowed_misses != -1 and consecutive_misses >= allowed_misses:
                                game_over = True
                        elif note.hit:
                            if current_time < note.hit_time + note.duration:
                                if pressed[lane_keys[note.lane]]:
                                    additional = int(hold_score_rate * (dt / 1000.0) * multiplier)
                                    score += additional
                            else:
                                active_notes.remove(note)

            update_and_draw_hit_effects(screen)
            update_and_draw_miss_effects(screen)

            # --- Rendering ---
            screen.fill((30, 30, 30))
            top_boundaries = [SCREEN_WIDTH / 2 + (i - 2.5) * (lane_width / 3) for i in range(6)]
            lane_boundaries = []
            for i in range(6):
                bottom_x = i * lane_width
                top_x = top_boundaries[i]
                lane_boundaries.append((top_x, SPAWN_Y, bottom_x, HIT_Y))
            for i in range(5):
                t_left, _, b_left, _ = lane_boundaries[i]
                t_right, _, b_right, _ = lane_boundaries[i + 1]
                poly = [(t_left, SPAWN_Y), (t_right, SPAWN_Y),
                        (b_right, HIT_Y), (b_left, HIT_Y)]
                color = tuple(min(255, int(c * 0.2)) for c in lane_colors[i])
                pygame.draw.polygon(screen, color, poly)
                num_strings = 3
                for j in range(1, num_strings + 1):
                    f = j / (num_strings + 1)
                    left_x = t_left + f * (b_left - t_left)
                    left_y = SPAWN_Y + f * (HIT_Y - SPAWN_Y)
                    right_x = t_right + f * (b_right - t_right)
                    right_y = SPAWN_Y + f * (HIT_Y - SPAWN_Y)
                    pygame.draw.aaline(screen, (180, 180, 180), (int(left_x), int(left_y)),
                                       (int(right_x), int(right_y)))

            for note in active_notes:
                key_state = pressed[lane_keys[note.lane]]
                note.draw(screen, current_time, key_pressed=key_state)

            pygame.draw.line(screen, (255, 255, 255), (0, HIT_Y), (SCREEN_WIDTH, HIT_Y), 2)

            for i in range(5):
                x = bottom_lane_centers[i]
                y = HIT_Y  # position on the horizontal hit line
                if pressed[lane_keys[i]]:
                    scale = 1.2
                else:
                    scale = 1.0
                button_width = 75 * scale
                button_height = 50 * scale
                rect = pygame.Rect(0, 0, button_width, button_height)
                rect.center = (x, y)
                pygame.gfxdraw.filled_ellipse(screen, rect.centerx, rect.centery, int(button_width / 2),
                                              int(button_height / 2), lane_colors[i])
                pygame.gfxdraw.aaellipse(screen, rect.centerx, rect.centery, int(button_width / 2),
                                         int(button_height / 2), (0, 0, 0))

            score_font = pygame.font.SysFont("Arial", 40)
            if allowed_misses != -1 and consecutive_misses > 0:
                miss_text = score_font.render(f"Miss Streak: {consecutive_misses}", True, (255, 0, 0))
                screen.blit(miss_text, (SCREEN_WIDTH - 220, 10))
            elif allowed_misses != -1 and consecutive_misses > 0:
                miss_text = score_font.render(f"Miss Streak: {consecutive_misses}", True, (255, 100, 100))
                screen.blit(miss_text, (SCREEN_WIDTH - 220, 10))

            multiplier_text = f"Multiplier: {multiplier}x"
            base_size = 70
            if multiplier_flash_timer > 0:
                scale_factor = 1.0 + 0.3 * abs(math.sin(pygame.time.get_ticks() / 100.0))
                flash_size = int(base_size * scale_factor)
                multiplier_flash_timer -= 1
            else:
                flash_size = base_size
            mult_font = pygame.font.SysFont("Arial", flash_size)
            mult_label_shadow = mult_font.render(multiplier_text, True, (0, 0, 0))
            screen.blit(mult_label_shadow, (12, 62))
            mult_label = mult_font.render(multiplier_text, True, (255, 215, 0))
            screen.blit(mult_label, (10, 62))


            score_label = score_font.render(f"Score: {score}", True, (255, 255, 255))
            screen.blit(score_label, (10, 10))

            pygame.display.flip()

            # End-of-song condition.
            if not game_over and not pygame.mixer.music.get_busy() and chart_index >= len(chart) and not active_notes:
                pygame.time.delay(3000)
                game_over = True
                finished_normally = True
                break

            if game_over:
                break

        # End-of-game: show the appropriate end screen if not already set by ESC.
        if action is None:
            if finished_normally:
                pygame.mixer.music.stop()
                action = song_completed_screen(score)
            else:
                pygame.mixer.music.stop()
                action = game_over_screen(score)
        # If the player chose "restart", restart the game with the same song.
        if action == "restart":
            continue
        else:
            return action


# ------------------ Outer Loop ------------------
next_action = None
while True:
    choice = menu_screen()  # "start", "difficulty", "guide", or "quit"
    if choice == "quit":
        break
    elif choice == "difficulty":
        diff = difficulty_screen()
        if diff is not None:
            allowed_misses = diff
        continue
    elif choice == "guide":
        guide_screen()
        continue
    elif choice == "start":
        action = "new"
        if action == "new":
            song_file = song_selection_screen()
            if not song_file:
                action = "menu"
                continue
            try:
                pygame.mixer.music.load(song_file)
            except Exception as e:
                print("Error loading song:", e)
                action = "menu"
                continue
            # Provide a loading screen while the song is analyzed.
            screen.fill((0, 0, 0))
            loading_font = pygame.font.SysFont("Arial", 36)
            loading_text = loading_font.render("Analyzing song... Please wait.", True, (255, 255, 255))
            screen.blit(loading_text, loading_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)))
            pygame.display.flip()
            try:
                y, sr = librosa.load(song_file, sr=None)
                tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
                if hasattr(tempo, "item"):
                    tempo = tempo.item()
                beat_times = librosa.frames_to_time(beat_frames, sr=sr)
                chart = []
                for t in beat_times:
                    lane = random.randint(0, 4)
                    travel_time = random.uniform(TRAVEL_TIME_MIN, TRAVEL_TIME_MAX)
                    if random.random() < LONG_NOTE_PROB:
                        duration = random.uniform(LONG_NOTE_DURATION_MIN, LONG_NOTE_DURATION_MAX)
                    else:
                        duration = 0.0
                    chart.append((t, lane, travel_time, duration))
                chart.sort(key=lambda x: x[0])
                print("Detected BPM: {:.2f}".format(tempo))
            except Exception as e:
                print("Error during beat detection:", e)
                action = "menu"
                continue
            action = run_game()

        if action in ["restart", "menu"]:
            next_action = action
        elif action == "quit":
            break
    else:
        break

pygame.quit()
sys.exit()
