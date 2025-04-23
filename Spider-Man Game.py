import asyncio
import pygame
import random



# Screen Settings
def init_screen():
    pygame.init()
    global WIN, WIDTH, HEIGHT, FPS, timer
    WIDTH, HEIGHT = 1024, 940
    WIN = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Spider-Man")
    FPS = 100
    timer = pygame.time.Clock()
    


        
def quit_game():
    pygame.display.quit()  # Close the display but avoid full quit
    loop = asyncio.get_event_loop()
    loop.stop()  # Properly stop the async event loop in pygbag
 

# Spider-Man Class
class SpiderMan:
    def __init__(self):
        self.moves = []
        self.frame_moment = 0
        self.heart = 3
        self.speed = 500
        self.life = 3
        self.moving = False
        self.load_images()
    def load_images(self):
        try:
            self.moves = [
                pygame.image.load('Standing.png').convert_alpha(),
                pygame.image.load('Left_direction.png').convert_alpha(),
                pygame.image.load('Right_direction.png').convert_alpha(),
                pygame.image.load('Jumppp.png').convert_alpha()
            ]
            self.heart_one =  pygame.image.load('Hearts.png').convert_alpha()
            self.heart_two = pygame.image.load('Hearts_2.png').convert_alpha()
            self.heart_three = pygame.image.load('Hearts_3.png').convert_alpha()
            self.heart_one_image = self.heart_one.get_rect()
            self.heart_one_image.x = 880
            self.heart_one_image.y = 10
            self.heart_two_image = self.heart_two.get_rect()
            self.heart_two_image.x = 930
            self.heart_two_image.y = 10
            self.heart_three_image = self.heart_three.get_rect()
            self.heart_three_image.x = 980
            self.heart_three_image.y = 10
            self.rect = self.moves[self.frame_moment].get_rect(midbottom=(512, HEIGHT))
            self.web_shot = pygame.image.load('Web_Shot.png').convert_alpha()
            self.web_rect = self.web_shot.get_rect(midbottom=self.rect.midtop)
            self.web_button_still = pygame.Rect(940, 730, 100, 50)  # (X, Y, Width, Height)
        except pygame.error as e:
            print(f"Error loading images: {e}")

    def move(self, keys, dt):
        if keys[pygame.K_a]:
            self.frame_moment = 1
            self.rect.x -= self.speed * dt
        elif keys[pygame.K_d]:
            self.frame_moment = 2
            self.rect.x += self.speed * dt
        elif keys[pygame.K_SPACE]:
            self.frame_moment = 3
        else:
            self.frame_moment = 0


    def enforce_boundaries(self):
        self.rect.clamp_ip(WIN.get_rect())  # Prevents Spider-Man from leaving screen bounds

    def shoot_web(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and not self.moving:
            self.web_rect.midbottom = self.rect.midtop
            self.moving = True
        if self.moving:
            self.web_rect.y -= 11 # Speed of web shot
        if self.web_rect.y <= 0:
            self.moving = False
        if self.moving is False:
            self.web_rect.midbottom = self.rect.midtop
        
        
    def draw(self):
        WIN.blit(self.moves[self.frame_moment], self.rect)
        if self.moving:
            WIN.blit(self.web_shot, self.web_rect)
        if self.heart == 3:
            WIN.blit(self.heart_one, self.heart_one_image)
            WIN.blit(self.heart_two, self.heart_two_image)
            WIN.blit(self.heart_two, self.heart_three_image)
        if self.heart == 2:
            WIN.blit(self.heart_one, self.heart_one_image)
            WIN.blit(self.heart_two, self.heart_two_image)
        if self.heart == 1:
            WIN.blit(self.heart_one, self.heart_one_image)

# Green Goblin Class
class GreenGoblin:
    def __init__(self):
        self.image = None
        self.rect = None
        self.speed_x = 10
        self.health = 3
        self.pumpkin_image = None
        self.pumkin_image2 = None
    def load_images(self):
        try:
            self.image = pygame.image.load('Green_Goblin.png').convert_alpha()
            self.rect = self.image.get_rect(topleft=(2, random.randint(0, 200)))
            self.pumpkin_image = pygame.image.load('Gob_Pumkin.png').convert_alpha()
            self.pumkin_image2 = pygame.image.load('Gob_Pumkin_2.png').convert_alpha()
            self.pumpkin_rect = self.pumpkin_image.get_rect(midbottom=self.rect.midtop)
            self.pumkin_rect_2 = self.pumkin_image2.get_rect(midbottom=self.rect.midtop)
            self.life_one = pygame.image.load('Goblin_Life.png').convert_alpha()
            self.life_one_rect = self.life_one.get_rect()
            self.life_one_rect.x = 15
            self.life_one_rect.y = 10
            self.life_two = pygame.image.load('Goblin_Life_2.png').convert_alpha()
            self.life_two_rect = self.life_two.get_rect()
            self.life_two_rect.x = 65
            self.life_two_rect.y = 10
            self.life_three = pygame.image.load('Goblin_Life_3.png').convert_alpha()
            self.life_three_rect = self.life_three.get_rect()
            self.life_three_rect.x = 115
            self.life_three_rect.y = 10
            self.pumpkin_moving = False
            self.pumpkin_moving2 = False
        except pygame.error as e:
            print(f"Error loading images: {e}")

    def move(self):
        self.rect.x += self.speed_x  
        if self.rect.left <= 0 or self.rect.right >= WIDTH:
            self.speed_x = -self.speed_x
            self.rect.y = random.randint(0, 470)
            self.rect.x = random.randint(0, WIDTH - self.rect.width)
        if 450 <= self.rect.x <= 460:
            self.rect.y = random.randint(0, 400)
        if 200 <= self.rect.x <= 210:
            self.rect.y = random.randint(0, 400)

    def drop_pumpkin(self):
        if not self.pumpkin_moving:
            self.pumpkin_rect.midbottom = self.rect.midtop
        if 0 <= self.pumpkin_rect.x <= 100:
            self.pumpkin_moving = True
            self.pumpkin_rect.y += 10
        if 490 <= self.pumpkin_rect.x <= 500:
            self.pumpkin_moving = True
            self.pumpkin_rect.y += 10
        if 900 <= self.pumpkin_rect.x <= 1000:
            self.pumpkin_moving = True
            self.pumpkin_rect.y += 10
        if self.pumpkin_moving:
            self.pumpkin_rect.y += 10
        if self.pumpkin_rect.y >= HEIGHT:
            self.pumpkin_moving = False
        if not self.pumpkin_moving2:
            self.pumkin_rect_2.midbottom = self.rect.midtop
            self.pumpkin_moving2 = True
        if self.pumpkin_moving2:
            self.pumkin_rect_2.y += 15
        if self.pumkin_rect_2.y >= HEIGHT:
            self.pumpkin_moving2 = False

    def draw(self):
        WIN.blit(self.image, self.rect)
        WIN.blit(self.pumpkin_image, self.pumpkin_rect)
        WIN.blit(self.pumkin_image2, self.pumkin_rect_2 )
        if self.health == 3:
            WIN.blit(self.life_one, self.life_one_rect)
            WIN.blit(self.life_two, self.life_two_rect)
            WIN.blit(self.life_three, self.life_three_rect)
        if self.health == 2:
            WIN.blit(self.life_one, self.life_one_rect)
            WIN.blit(self.life_two, self.life_two_rect)
        if self.health == 1:
            WIN.blit(self.life_one, self.life_one_rect)
            
async def End_game_screen():
    image = pygame.image.load("Game End.png")
    WIN.blit(image, (0, 0))
    pygame.display.update()
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:  # Correct key detection
                return True
            if event.type == pygame.QUIT:
                quit_game()
        await asyncio.sleep(0.05)  # Delay to prevent high CPU usage
           
    return False
# Game Loop
async def main():
    init_screen()
    spiderman = SpiderMan()
    green_goblin = GreenGoblin()
    while True:
        spiderman.heart = 3
        green_goblin.health = 3
        spiderman.load_images()
        green_goblin.load_images()
        running = True
        while running:
            dt = timer.tick(FPS) / 1000 # Time delta for smooth movement
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    quit_game()
                    return

            # Input Handling
            keys = pygame.key.get_pressed()
            spiderman.move(keys, dt)
            spiderman.enforce_boundaries()
            spiderman.shoot_web()

            green_goblin.move()
            green_goblin.drop_pumpkin()

            # Collision Detection
            if spiderman.web_rect.colliderect(green_goblin.rect):
                spiderman.moving = False
                green_goblin.health -= 1
                spiderman.moving = False  # Reset web
            if spiderman.rect.colliderect(green_goblin.pumpkin_rect):
                green_goblin.pumpkin_moving = False
                spiderman.heart -= 1
                green_goblin.pumpkin_rect.midbottom = green_goblin.rect.midtop
            if spiderman.rect.colliderect(green_goblin.pumkin_rect_2):
                green_goblin.pumpkin_moving2 = False
                spiderman.heart -= 1
                green_goblin.pumkin_rect_2.midbottom = green_goblin.rect.midtop

            # End Game Conditions
            if green_goblin.health <= 0 or spiderman.heart <= 0:
                if await End_game_screen():
                    break
                
            if pygame.display.get_surface():
                WIN.blit(pygame.image.load("NY_BackGround.png").convert(), (0, 0))
                spiderman.draw()
                green_goblin.draw()
                pygame.display.update()
            else:
                print("Error: Pygame display not initialized!")

            await asyncio.sleep(0.01)
            if not running:
                quit_game()
                return

asyncio.run( main() )
