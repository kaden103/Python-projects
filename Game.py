import pygame
import random
pygame.init()
WIDTH, HEIGHT = 1024, 940
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
running = True
screen = pygame.display.set_caption("Spider-Man")
back_ground = pygame.image.load("NY_BackGround.jpeg")
timer = pygame.time.Clock()
fps = 60
dt = 0
moving = False
First_Drop = False
Second_Drop = False
Life = 3
Goblin_Heads = 3

# Surfaces In Game

X_wall = pygame.Surface((2, 940))
X_wall.fill((255,0,0))
X_wall_rect = X_wall.get_rect()

# Green Goblin Movement
Villian = pygame.image.load('Green_Goblin.png')
Green_Gob = Villian.get_rect()
Green_GobX = 2



# Spider Man Movement
moves = [pygame.image.load('Standing.png'), pygame.image.load('Left_direction.png'), pygame.image.load('Right_direction.png'),pygame.image.load('Jumppp.png')]
frame_moment = 0
Spidey_rect = moves[frame_moment].get_rect()
Spidey_rect.midbottom = (512, 940)

# Web_Shooter
Webs = pygame.image.load('Web_Shot.png')
Web_Shot = Webs.get_rect()
Web_ShotY = 4
Web_Shot.x = 500

# Pumkin Image
Gob_Attack = pygame.image.load('Gob_Pumkin.png')
Pumkin = Gob_Attack.get_rect()
PumkinY = 3

# Life Count
Heart_One = pygame.image.load('Hearts.png')
Show_Heart = Heart_One.get_rect()
Show_Heart.x = 880
Show_Heart.y = 10
Heart_Two = pygame.image.load('Hearts_2.png')
Show_Heart_2 = Heart_Two.get_rect()
Show_Heart_2.x = 930
Show_Heart_2.y = 10
Heart_Three = pygame.image.load('Hearts_3.png')
Show_Heart_3 = Heart_Three.get_rect()
Show_Heart_3.x = 980
Show_Heart_3.y = 10

# Green Goblin Life Count
Goblin_Life = pygame.image.load('Goblin_Life.png')
Goblin_Life_Count = Goblin_Life.get_rect()
Goblin_Life_Count.x = 15
Goblin_Life_Count.y = 10
Goblin_Life_Second = pygame.image.load('Goblin_Life_2.png')
Goblin_Life_2 = Goblin_Life_Second.get_rect()
Goblin_Life_2.x = 65
Goblin_Life_2.y = 10
Goblin_Life_Third = pygame.image.load('Goblin_Life_3.png')
Goblin_Life_3 = Goblin_Life_Third.get_rect()
Goblin_Life_3.x = 115
Goblin_Life_3.y = 10
# Spider_Man Hit Sound




def Movement():
    global frame_moment
    keys = pygame.key.get_pressed()
    if keys[pygame.K_a]:
        frame_moment = 1
    if keys[pygame.K_d]:
        frame_moment = 2
    if keys[pygame.K_SPACE]:
        frame_moment = 3
    if not(keys[pygame.K_a] or keys[pygame.K_d] or keys[pygame.K_SPACE]):
        frame_moment = 0


    
def draw():
    global Life
    global moving
    WIN.blit(back_ground, (0, 0))
    WIN.blit(moves[frame_moment], Spidey_rect)
    WIN.blit(X_wall, (0,0))
    WIN.blit(Villian, Green_Gob)
    if moving == True:
        WIN.blit(Webs, Web_Shot)
    if First_Drop == True or Second_Drop == True:
        WIN.blit(Gob_Attack, Pumkin)
    if Life == 3:
        WIN.blit(Heart_One, Show_Heart)
        WIN.blit(Heart_Two, Show_Heart_2)
        WIN.blit(Heart_Three, Show_Heart_3)
    if Life == 2:
         WIN.blit(Heart_One, Show_Heart)
         WIN.blit(Heart_Two, Show_Heart_2)
    if Life == 1:
        WIN.blit(Heart_One, Show_Heart)
    if Goblin_Heads == 3:
        WIN.blit(Goblin_Life, Goblin_Life_Count)
        WIN.blit(Goblin_Life_Second, Goblin_Life_2)
        WIN.blit(Goblin_Life_Third, Goblin_Life_3)
    if Goblin_Heads == 2:
        WIN.blit(Goblin_Life, Goblin_Life_Count)
        WIN.blit(Goblin_Life_Second, Goblin_Life_2)
    if Goblin_Heads == 1:
        WIN.blit(Goblin_Life, Goblin_Life_Count)
    
        
        
def Boundaries():
    End_of_Screen = WIN.get_width()
    End_of_Screen2 = WIN.get_height()
    if Spidey_rect.colliderect(X_wall_rect):
        Spidey_rect.left = X_wall_rect.right
    if Spidey_rect.right >= End_of_Screen:
        Spidey_rect.right = End_of_Screen
    if Spidey_rect.bottom >= End_of_Screen2:
        Spidey_rect.bottom = End_of_Screen2



def Green_Goblin_Movement():
    global Green_Gob, Green_GobX
    End_of_Screen = WIN.get_width()
    if Green_Gob.colliderect(X_wall_rect):
        Green_GobX = 2
        Green_Gob.y = random.randint(0,200)
    if Green_Gob.right >= End_of_Screen:
        Green_GobX = -Green_GobX
        Green_Gob.y = random.randint(0,200)
    if Green_Gob.x == 490:
        Green_Gob.y = random.randint(0,200)
    Green_Gob.x += Green_GobX

def Web_Shooter():
    global Web_Shot, Web_ShotY, moving, Spidey_rect
    keys = pygame.key.get_pressed()
    if keys[pygame.K_SPACE] and not moving:
        Web_Shot.y = Spidey_rect.y
        Web_Shot.x = Spidey_rect.right
        moving = True
    if moving and Web_Shot.y > 0:
        Web_Shot.y -= Web_ShotY
    if Web_Shot.y <= 0:
        moving = False
        Web_Shot.y = Spidey_rect.y
        Web_Shot.x = Spidey_rect.right

def Pumkin_Drop():
    global Green_Gob, Pumkin, First_Drop, Second_Drop
    if Green_Gob.x == 490 and not First_Drop:
        First_Drop = True
    if First_Drop:
        Pumkin.y += PumkinY
    if not First_Drop:
        Pumkin.x = Green_Gob.x + 20
        Pumkin.y = Green_Gob.y - 20
    if Pumkin.y >= 940:
        First_Drop = False
    if Green_Gob.x == 240 and not First_Drop:
        First_Drop = True
    if First_Drop:
        Pumkin.y += PumkinY
    if not First_Drop:
        Pumkin.x = Green_Gob.x + 20
        Pumkin.y = Green_Gob.y - 20
    if Pumkin.y >= 940:
        First_Drop = False
    if Green_Gob.x == 700 and not First_Drop:
        First_Drop = True
    if First_Drop:
        Pumkin.y += PumkinY
    if not First_Drop:
        Pumkin.x = Green_Gob.x + 20
        Pumkin.y = Green_Gob.y - 20
    if Pumkin.y >= 940:
        First_Drop = False
   

def damage():
    global running, Life, First_Drop
    if Spidey_rect.colliderect(Pumkin):
        Life -= 1
        First_Drop = False
    if Life == 0:
        running = False

def damage_Goblin():
    global Green_Gob, Goblin_Life, Goblin_Heads, running, moving
    if Green_Gob.colliderect(Web_Shot):
        Goblin_Heads -= 1
        moving = False
        Web_Shot.y = Spidey_rect.y
        Web_Shot.x = Spidey_rect.right
    if Goblin_Heads == 0:
        running = False
    


def main():
    global running
    running = True
    dt = timer.tick(60) / 1000
    while running == True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        Movement()
        damage()
        keys = pygame.key.get_pressed()
        if keys[pygame.K_s]:
            Spidey_rect.y += 300 * dt
        if keys[pygame.K_a]:
            Spidey_rect.x -= 300 * dt
        if keys[pygame.K_d]:
            Spidey_rect.x += 300 * dt
            
        damage_Goblin()
        Pumkin_Drop()
        Green_Goblin_Movement()
        Web_Shooter()
        Boundaries()
        WIN.fill((0, 0, 0)) 
        draw()
        pygame.display.update()
    
    pygame.quit()
    
main()