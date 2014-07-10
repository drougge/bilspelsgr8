#!/usr/bin/env python

from __future__ import print_function, division

import pygame
import pygame.joystick
from operator import add, div
from math import atan2, degrees, radians, sin, cos
import os

# Pygame prints lots of internal debug, so redirect stdout to /dev/null
stdout_fd = os.dup(1)
stdout = os.fdopen(stdout_fd, "w")
null_fd = os.open("/dev/null", os.O_WRONLY)
os.dup2(null_fd, 1)

pygame.init()
clock = pygame.time.Clock()
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

screen = pygame.display.set_mode([1600, 1200])
pygame.display.set_caption("TROLOLO joysticks!!!1")

global things
_images = {}

def imgload(names, step=1):
	for name in names:
		if name not in _images:
			img = pygame.image.load(name).convert_alpha()
			def rot(deg):
				i = pygame.transform.rotate(img, deg)
				return i, pygame.mask.from_surface(i)
			_images[name] = {deg: rot(deg) for deg in range(0, 360, step or 360)}
	return [_images[name] for name in names]


class Sprite(pygame.sprite.Sprite):
	_animate = False
	_offset = (0, 0)
	def __init__(self, imgs, x, y, move=False):
		pygame.sprite.Sprite.__init__(self)
		self._imgs = imgload(imgs)
		self._pos = (x, y)
		self._dir = dir
		self._move = move
		self._cur_img = 0
		self._rot = 0
		self._anim = 0
		if move:
			self._setrot()
			self._newimg()
		else:
			self._img = self._imgs[0]
			self.image, self.mask = self._img[0]
	def _setrot(self):
		self._rot = int(degrees(atan2(*self._move)) - 90) % 360
	def set_speed(self, speed):
		r = radians(self._rot)
		self._move = [sin(r) * speed, cos(r) * speed]
	def _newimg(self, force=False):
		if self._animate:
			self._anim += 1
		if force or self._animate is self._anim:
			self._anim = 0
			self._cur_img += 1
			self._cur_img %= len(self._imgs)
		self._img = self._imgs[self._cur_img]
		self.image, self.mask = self._img[self._rot]
	def update(self):
		z = map(div, map(add, self.image.get_size(), self._offset), (2, 2))
		if self._move:
			#self._pathify(z)
			self._pos = map(add, self._pos, self._move)
		self._newimg()
		x, y = map(int, self._pos)
		xz, yz = z
		xo, yo = self._offset
		self.rect = pygame.rect.Rect(x - xz + xo, y - yz + yo, xz * 2, yz * 2)

class Car(Sprite):
	_sprite_filenames = ("car_red.png",)
	max_speed = 10
	def __init__(self, x, y):
		Sprite.__init__(self, self._sprite_filenames, x, y)
	def update(self):
		axis_value = joysticks[0].get_axis(0)
		#print(axis_value, file=stdout)
		self._rot = int(360*axis_value) % 360

		axis_value = joysticks[0].get_axis(13)
		print (axis_value, file=stdout)
		speed = (axis_value * self.max_speed)
		if speed < 0:
			speed = 0
		self.set_speed(speed)
		print("Speed={:>6.3f}".format(speed), file=stdout)

		Sprite.update(self)



screen.fill((255, 0, 228))
background = pygame.image.load("map1.png").convert_alpha()
screen.blit(background, (0, 0))
pygame.display.flip()



cars = pygame.sprite.RenderClear([])
things = [cars]
cars.add(Car(800, 600))

done = False
while not done:
	screen.blit(background, (0, 0))
	# EVENT PROCESSING STEP
	for event in pygame.event.get(): # User did something
		if event.type == pygame.QUIT: # If user clicked close
				done = True # Flag that we are done so we exit this loop
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
				done = True

	for j in joysticks:
		j.init()
		#print(j.get_name(), file=stdout)
		for i in range(j.get_numaxes()):
			axis = j.get_axis(i)
			#print("Axis {} value: {:>6.3f}".format(i, axis), file=stdout)
		for i in range(j.get_numbuttons()):
			button = j.get_button(i)
			#print("Button {:>2} value: {}".format(i, button), file=stdout)

	for thing in things:
		thing.update()
		thing.draw(screen)

	clock.tick(60)
	pygame.display.flip()

print("Why you quit already? :(", file=stdout)
