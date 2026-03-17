import pygame
import cv2
import mediapipe as mp
import random
import sys
import math
import os

# ==========================================
# 1. INITIALIZATION & SETTINGS
# ==========================================
pygame.init()
pygame.mixer.init()

# Screen settings
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
WIDTH, HEIGHT = screen.get_size()
pygame.display.set_caption("Gesture Dash - Webcam Controlled")
clock = pygame.time.Clock()

# Colors (Playful & Modern Design)
BG_COLOR = (25, 25, 35)         # Dark/Modern background
GROUND_COLOR = (20, 20, 20)     # Dark Grey/Black for cave floor
PLAYER_COLOR = (0, 220, 255)    # Neon light blue
OBSTACLE_COLOR = (255, 60, 110) # Neon pink/red
TEXT_COLOR = (250, 250, 250)    # Glowing white

# Set fonts
try:
    font = pygame.font.SysFont("segoeui", 42, bold=True)
    big_font = pygame.font.SysFont("segoeui", 80, bold=True)
except:
    font = pygame.font.Font(None, 46)
    big_font = pygame.font.Font(None, 90)

# ==========================================
# 2. MEDIAPIPE & WEBCAM SETUP
# ==========================================
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)
mp_draw = mp.solutions.drawing_utils

# Start the webcam
cap = cv2.VideoCapture(0)

# ==========================================
# CUSTOM IMAGES (OPTIONAL)
# ==========================================
IMAGE_DIR = "images"
if not os.path.exists(IMAGE_DIR):
    os.makedirs(IMAGE_DIR)

def load_image(filename):
    path = os.path.join(IMAGE_DIR, filename)
    if os.path.exists(path):
        return pygame.image.load(path).convert_alpha()
    return None

PLAYER_IMG_1 = load_image("player1.png")
PLAYER_IMG_2 = load_image("player2.png")

# Load running animation frames
RUN_FRAMES = []
run_dir = os.path.join(IMAGE_DIR, "run")
if os.path.exists(run_dir):
    # Sort files to ensure running_000 to running_049
    files = sorted([f for f in os.listdir(run_dir) if f.startswith("running_") and f.endswith(".png")])
    for f in files:
        img = pygame.image.load(os.path.join(run_dir, f)).convert_alpha()
        RUN_FRAMES.append(img)

OBSTACLE_IMG = load_image("obstacle.png")
BAT_IMG = load_image("bat.png")
GROUND_IMG = load_image("ground.png")
BG_IMG = load_image("background.png")
if BG_IMG:
    BG_IMG = pygame.transform.scale(BG_IMG, (WIDTH, HEIGHT))
if GROUND_IMG:
    # Scale width to screen width, and keep a fixed ground height of 200 for better proportion
    ground_w = WIDTH
    ground_h = 240
    GROUND_IMG = pygame.transform.scale(GROUND_IMG, (ground_w, ground_h))

# ==========================================
# SOUNDS (CAVE THEME)
# ==========================================
SOUND_DIR = "sounds"
if not os.path.exists(SOUND_DIR):
    os.makedirs(SOUND_DIR)

def load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    if os.path.exists(path):
        return pygame.mixer.Sound(path)
    return None

JUMP_SOUND = load_sound("jump.wav")
GAMEOVER_SOUND = load_sound("gameover.wav")

# Try to load and play background music
bg_music_path = os.path.join(SOUND_DIR, "cave_theme.mp3")
if os.path.exists(bg_music_path):
    pygame.mixer.music.load(bg_music_path)
    pygame.mixer.music.set_volume(0.2)
    pygame.mixer.music.play(-1) # Loop indefinitely
else:
    # Look for .wav alternative if .mp3 not present
    bg_music_path_alt = os.path.join(SOUND_DIR, "cave_theme.wav")
    if os.path.exists(bg_music_path_alt):
        pygame.mixer.music.load(bg_music_path_alt)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)

# ==========================================
# 3. GAME OBJECTS (CLASSES)
# ==========================================
class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.width = 250
        self.height = 250
        self.x = (WIDTH // 3)  # Shifted even more to the right, but not full middle
        
        # Determine logical ground for the player
        # Ground image is 240 tall. The player should overlap it slightly to look like running *on* it, not floating.
        ground_visual_height = 240
        player_offset = 60 # Push player down into the image a bit
        self.ground_y = HEIGHT - ground_visual_height - self.height + player_offset
        
        self.y = self.ground_y
        self.vel_y = 0
        self.gravity = 1.2      # Higher gravity for bigger jumps
        self.jump_power = -28   # Huge jump power to clear obstacles cleanly
        self.anim_tick = 0
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def jump(self):
        # Player can only jump when standing on the ground
        if self.y >= self.ground_y:
            self.vel_y = self.jump_power
            if JUMP_SOUND:
                JUMP_SOUND.play()

    def update(self):
        # Gravity logic
        self.vel_y += self.gravity
        self.y += self.vel_y
        
        # Ground check (touching the ground?)
        if self.y >= self.ground_y:
            self.y = self.ground_y
            self.vel_y = 0
            
        self.anim_tick += 1
        self.rect.topleft = (self.x, self.y)

    def draw(self, surface):
        # Decide which player image to draw based on animation tick and state
        current_img = None
        
        # If we have run frames and are on the ground, animate through them
        if RUN_FRAMES and self.y == self.ground_y:
            # anim_tick increments by 1 each frame (60fps). 
            # We have 50 frames. Play them at e.g. 1 frame advance every 2 ticks (30fps animation).
            frame_idx = (self.anim_tick // 2) % len(RUN_FRAMES)
            current_img = RUN_FRAMES[frame_idx]
        elif RUN_FRAMES and self.y < self.ground_y:
            # While jumping, just show one specific frame (e.g. frame 20 looks like jumping/midair)
            current_img = RUN_FRAMES[len(RUN_FRAMES) // 2]
        else:
            # Fallback to player1/player2 if no run frames exist
            if PLAYER_IMG_1 and PLAYER_IMG_2:
                if self.y == self.ground_y and (self.anim_tick // 10) % 2 == 0:
                    current_img = PLAYER_IMG_1
                else:
                    current_img = PLAYER_IMG_2
            elif PLAYER_IMG_1 or PLAYER_IMG_2:
                current_img = PLAYER_IMG_1 if PLAYER_IMG_1 else PLAYER_IMG_2

        # Draw the selected image or a fallback shape
        if current_img:
            # We don't apply math.sin hovering if we have full run frames since the animation handles movement
            draw_y = self.y if RUN_FRAMES else self.y + ((math.sin(self.anim_tick * 0.3) * 4) if self.y == self.ground_y else 0)
            scaled_img = pygame.transform.scale(current_img, (self.width, self.height))
            surface.blit(scaled_img, (self.x, draw_y))
        else:
            draw_y = self.y + ((math.sin(self.anim_tick * 0.3) * 4) if self.y == self.ground_y else 0)
            # Base body (Robot square) fallback
            body_rect = pygame.Rect(self.x, draw_y, self.width, self.height)
            pygame.draw.rect(surface, PLAYER_COLOR, body_rect, border_radius=12)
            
            # Glowing ring around it to make it sci-fi/playful
            pygame.draw.rect(surface, (255, 255, 255), body_rect.inflate(10, 10), 2, border_radius=15)
            
            # Eye (Looking forward)
            eye_x = self.x + 28
            eye_y = int(draw_y + 16)
            pygame.draw.circle(surface, (255, 255, 255), (eye_x, eye_y), 8)
            pygame.draw.circle(surface, (0, 0, 0), (eye_x, eye_y), 3)

class FlyingBat(pygame.sprite.Sprite):
    def __init__(self, speed):
        super().__init__()
        self.width = 120
        self.height = 100
        self.x = WIDTH + 50
        self.is_bat = True
        
        # The bat flies right in the jumping path.
        ground_visual_height = 240
        obstacle_offset = 40 # Push obstacle down into the visual ground
        player_running_y = HEIGHT - ground_visual_height - 250 + 60 # approx 170 on 600p screen
        
        # Set bat slightly higher than the running player's head, but perfectly in jump trajectory
        self.y = player_running_y - self.height + 40 
        
        self.speed = speed + 2  # Bats fly slightly faster than ground speed
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.anim_tick = 0

    def update(self):
        self.x -= self.speed
        
        # Sine wave flying movement
        self.anim_tick += 1
        hover = math.sin(self.anim_tick * 0.1) * 15
        
        self.rect.topleft = (self.x, self.y + hover)

    def draw(self, surface):
        hover = math.sin(self.anim_tick * 0.1) * 15
        draw_y = self.y + hover
        
        if BAT_IMG:
            scaled_img = pygame.transform.scale(BAT_IMG, (self.width, self.height))
            surface.blit(scaled_img, (self.x, draw_y))
        else:
            # Fallback drawing for a bat
            pygame.draw.ellipse(surface, (50, 50, 50), (self.x, draw_y, self.width, self.height))
            pygame.draw.polygon(surface, (50, 50, 50), [(self.x, draw_y+self.height//2), (self.x-30, draw_y-20), (self.x+20, draw_y+20)])
            pygame.draw.polygon(surface, (50, 50, 50), [(self.x+self.width, draw_y+self.height//2), (self.x+self.width+30, draw_y-20), (self.x+self.width-20, draw_y+20)])

class Obstacle(pygame.sprite.Sprite):
    def __init__(self, speed):
        super().__init__()
        self.width = 100
        self.height = 100
        self.x = WIDTH + 50
        
        ground_visual_height = 240
        obstacle_offset = 40 # Push obstacle down into the visual ground
        self.y = HEIGHT - ground_visual_height - self.height + obstacle_offset
        self.speed = speed
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    def update(self):
        self.x -= self.speed
        self.rect.topleft = (self.x, self.y)

    def draw(self, surface):
        if OBSTACLE_IMG:
            scaled_img = pygame.transform.scale(OBSTACLE_IMG, (self.width, self.height))
            surface.blit(scaled_img, (self.x, self.y))
        else:
            # Unique appearance: Alien crystals / Dangerous triangles
            points = [
                (self.x, self.y + self.height), 
                (self.x + self.width // 2, self.y), 
                (self.x + self.width, self.y + self.height)
            ]
            pygame.draw.polygon(surface, OBSTACLE_COLOR, points)
            # Crystal glow effect line
            pygame.draw.polygon(surface, (255, 150, 180), points, 2)


# ==========================================
# 4. START VARIABLES
# ==========================================
player = Player()
obstacles = pygame.sprite.Group()
global_speed = 10  # Increased starting speed
score = 0
high_score = 0
spawn_timer = 0
state = "START" # Possible states: START, PLAYING, GAMEOVER
was_fist = False
bg_scroll = 0
ground_scroll = 0

# Simulating moving stars in the background for depth
bg_particles = [(random.randint(0, WIDTH), random.randint(0, HEIGHT - 200)) for _ in range(50)]

def draw_background():
    global bg_scroll, ground_scroll
    
    # Background layer
    if BG_IMG:
        if state == "PLAYING":
            bg_scroll -= global_speed * 0.2
        if bg_scroll <= -WIDTH:
            bg_scroll += WIDTH
        screen.blit(BG_IMG, (bg_scroll, 0))
        screen.blit(BG_IMG, (bg_scroll + WIDTH, 0))
    else:
        screen.fill(BG_COLOR)
        # Parallax particles fallback
        for i in range(len(bg_particles)):
            x, y = bg_particles[i]
            if state == "PLAYING":
                x -= global_speed * 0.2
            if x < 0:
                x = WIDTH
            bg_particles[i] = (x, y)
            pygame.draw.circle(screen, (100, 100, 120), (int(x), int(y)), 2)
            
    # Ground layer
    ground_h = 240
    if GROUND_IMG:
        # Ground moves exactly same speed as obstacles
        if state == "PLAYING":
            ground_scroll -= global_speed
        if ground_scroll <= -WIDTH:
            ground_scroll += WIDTH
            
        screen.blit(GROUND_IMG, (ground_scroll, HEIGHT - ground_h))
        screen.blit(GROUND_IMG, (ground_scroll + WIDTH, HEIGHT - ground_h))
    else:
        # Fallback solid ground
        pygame.draw.rect(screen, GROUND_COLOR, (0, HEIGHT - ground_h, WIDTH, ground_h))
        pygame.draw.line(screen, (80, 80, 80), (0, HEIGHT - ground_h), (WIDTH, HEIGHT - ground_h), 8)

def reset_game():
    global score, global_speed, spawn_timer
    score = 0
    global_speed = 10  # Match the increased starting speed
    spawn_timer = 0
    player.y = player.ground_y
    player.vel_y = 0
    obstacles.empty()
    pygame.mixer.music.unpause() # Resume cave theme music

# ==========================================
# 5. MAIN GAME LOOP
# ==========================================
running = True
while running:
    # A) Event handling (Cross or Keyboard Fallback)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                if state == "PLAYING":
                    player.jump()
                elif state in ["START", "GAMEOVER"]:
                    reset_game()
                    state = "PLAYING"

    # B) Read the webcam via OpenCV
    ret, frame = cap.read()
    is_fist = False
    is_open = False
    
    if ret:
        frame = cv2.flip(frame, 1) # mirror the image left-right
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = hands.process(rgb_frame)

        # C) MediaPipe Hand Detection Logic
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Draw the lines on the cam image
                mp_draw.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
                
                # Check which fingers are up
                fingers_up = 0
                tips = [8, 12, 16, 20]     # Top of the finger landmarks
                mcps = [5, 9, 13, 17]      # Knuckle of the finger landmarks
                
                for tip, mcp in zip(tips, mcps):
                    # In the screen, Y=0 is the top of your monitor, so lower y means the finger is physically higher.
                    if hand_landmarks.landmark[tip].y < hand_landmarks.landmark[mcp].y:
                        fingers_up += 1
                        
                # 0 or 1 fingers we see as a "Fist"
                if fingers_up <= 1:
                    is_fist = True
                else:
                    is_open = True

    # State mechanism based on hand movement
    # Trigger only if it's a NEW fist movement
    if is_fist and not was_fist:
        if state == "PLAYING":
            player.jump()
        elif state in ["START", "GAMEOVER"]:
            reset_game()
            state = "PLAYING"
            
    was_fist = is_fist

    # D) Update Game
    if state == "PLAYING":
        player.update()
        
        # Generate obstacles at random moments
        spawn_timer -= 1
        if spawn_timer <= 0:
            # Randomly choose between ground obstacle and flying bat (e.g. 30% chance for bat after score > 200)
            if score > 200 and random.random() < 0.3:
                obstacles.add(FlyingBat(global_speed))
            else:
                obstacles.add(Obstacle(global_speed))
                
            # timer depends partly on score to remain random but go faster
            spawn_timer = random.randint(max(40, 100 - score//10), max(60, 150 - score//10))
            
        # Make obstacles disappear
        for obs in obstacles:
            obs.update()
            if obs.x + obs.width < 0:
                obstacles.remove(obs)
                
        # Collision Detection - we make the player hitbox significantly smaller for fairness
        # Since the player is 250x250, inflating by -100 makes the hitbox 150x150 in the core
        player_hitbox = player.rect.inflate(-100, -80)
        
        for obs in obstacles:
            # Hitbox for the obstacle (bat or rock) 
            obs_hitbox = obs.rect.inflate(-40, -40) if getattr(obs, 'is_bat', False) else obs.rect.inflate(-20, -20)
            
            if player_hitbox.colliderect(obs_hitbox):
                state = "GAMEOVER"
                if GAMEOVER_SOUND:
                    GAMEOVER_SOUND.play()
                pygame.mixer.music.pause() # Pause cave music on game over
                if score > high_score:
                    high_score = score
                    
        # Score update
        score += 1
        # Slowly make the game harder
        if score % 300 == 0:
            global_speed += 1

    # E) Graphical display in the PyGame window
    draw_background()
    
    # Render gameplay
    if state == "PLAYING" or state == "GAMEOVER":
        player.draw(screen)
        for obs in obstacles:
            obs.draw(screen)
            
        # UI: Current Score
        score_text = font.render(f"Score: {score}  (Record: {high_score})", True, TEXT_COLOR)
        screen.blit(score_text, (20, 20))
        
    # Start screen
    if state == "START":
        title = big_font.render("AI WEBCAM RUNNER", True, PLAYER_COLOR)
        sub = font.render("Make a FIST with your hand to start and jump!", True, TEXT_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//3 - 30))
        screen.blit(sub, (WIDTH//2 - sub.get_width()//2, HEIGHT//2))
        
    # Result screen
    elif state == "GAMEOVER":
        go_title = big_font.render("GAME OVER", True, OBSTACLE_COLOR)
        go_sub = font.render(f"Final Score: {score} - Make a FIST to play again", True, TEXT_COLOR)
        screen.blit(go_title, (WIDTH//2 - go_title.get_width()//2, HEIGHT//3 - 30))
        screen.blit(go_sub, (WIDTH//2 - go_sub.get_width()//2, HEIGHT//2))

    # F) Picture-in-Picture: Place the webcam top right
    if ret:
        # Maak deze ook een stukje groter voor fullscreen
        pip_width = 240
        pip_height = 180
        
        # Transform the OpenCV NumPy array safely directly to a Pygame Surface
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.image.frombuffer(frame_rgb.tobytes(), (frame.shape[1], frame.shape[0]), "RGB")
        surf = pygame.transform.scale(surf, (pip_width, pip_height))
        
        # Border around PIP
        pip_x = WIDTH - pip_width - 20
        pip_y = 20
        pygame.draw.rect(screen, (255, 255, 255), (pip_x - 3, pip_y - 3, pip_width + 6, pip_height + 6), 3)
        screen.blit(surf, (pip_x, pip_y))
        
        # Subtitle Text in webcam whether you are Open/Closed seen by the AI
        status_text = "FIST (Jump)" if is_fist else ("OPEN HAND" if is_open else "Show hand!")
        status_color = (0, 255, 0) if is_fist else (255, 255, 0)
        status_surf = font.render(status_text, True, status_color)
        status_surf = pygame.transform.scale(status_surf, (int(status_surf.get_width() * 0.6), int(status_surf.get_height() * 0.6)))
        screen.blit(status_surf, (pip_x + 8, pip_y + 8))

    # Show resulting frame on screen
    pygame.display.flip()
    clock.tick(60)

# Clean up after closing
cap.release()
pygame.quit()
sys.exit()
