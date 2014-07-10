from __future__ import print_function, division

import pygame
from pygame.locals import *
import pygame.joystick

import os
stdout_fd = os.dup(1)
stdout = os.fdopen(stdout_fd, "w")
fd = os.open( "/dev/null", os.O_WRONLY )

pygame.init()
clock = pygame.time.Clock()
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
 
screen = pygame.display.set_mode([1600, 1200])
pygame.display.set_caption("TROLOLO joysticks!!!1")


def imgload(names, step=1):
	for name in names:
		if name not in _images:
			img = pygame.image.load(name).convert_alpha()
			def rot(deg):
				i = pygame.transform.rotate(img, deg)
				return i, pygame.mask.from_surface(i)
			_images[name] = dict([(deg, rot(deg)) for deg in range(0, 360, step or 360)])
	return [_images[name] for name in names]


screen.fill((255, 0, 228))
background = pygame.image.load("map1.png").convert_alpha()
screen.blit(background, (0, 0))
pygame.display.flip()

done = False
while done==False:
	# EVENT PROCESSING STEP
	for event in pygame.event.get(): # User did something
			if event.type == pygame.QUIT: # If user clicked close
					done=True # Flag that we are done so we exit this loop
			elif event.type == KEYDOWN and event.key == K_ESCAPE:
					done=True

	for j in joysticks:
		j.init()
		print(j.get_name(), file=stdout)
		for i in range( j.get_numaxes() ):
			os.dup2(fd, 1)
			axis = j.get_axis( i )
			print("Axis {} value: {:>6.3f}".format(i, axis), file=stdout)
		for i in range( j.get_numbuttons() ):
			button = j.get_button( i )
			print("Button {:>2} value: {}".format(i, button), file=stdout )

	clock.tick(60)
	pygame.display.flip()

print("Why you quit already? :(", file=stdout)
