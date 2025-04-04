import pygame
pygame.init()
WIDTH, HEIGHT = 1024, 940
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
running = True
screen = pygame.display.set_caption("Spider-Man")
back_ground = pygame.image.load("NY_BackGround.jpeg")
# Timer for fps and screen refresh rate
timer = pygame.time.Clock()
fps = 60
 
character = pygame.image.load("SpiderMan_Standing.png")
Spidey_rect = character.get_rect()
Spidey_rect.midbottom = (WIDTH // 2, HEIGHT // 2)

# Character image and demensions
def draw():
    WIN.blit(back_ground, (0, 0))
    WIN.blit(character, Spidey_rect)
    pygame.display.update()
    

def draw_window():
    WIN.blit(back_ground, (0, 0))
    pygame.display.update()
    
def main():
    running = True
    while running == True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        draw()
    
    pygame.quit()
    
main()