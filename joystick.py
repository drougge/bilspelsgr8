#!/usr/bin/env python

from __future__ import print_function, division

import pygame
import pygame.joystick
from operator import add, div
from math import atan2, degrees, radians, sin, cos
from workarounds import print
from settings import settings

pygame.init()
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
pygame.font.init()
clock = pygame.time.Clock()

screen = pygame.display.set_mode([1600, 1200])
pygame.display.set_caption(settings['game']['name'])

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
	max_speed = 20
	_speed = 0
	max_accel = 1
	_accel = 0
	max_turn = 5
	_turn = 0
	friction = 0.3

	def __init__(self, x, y):
		Sprite.__init__(self, self._sprite_filenames, x, y)
	def update(self):
		axis_value = joysticks[0].get_axis(0)
		self._turn = -int(axis_value*self.max_turn)
		self._rot = (self._rot + self._turn) % 360

		axis_value = (1+joysticks[0].get_axis(13))/2 - (1+joysticks[0].get_axis(12))/2
		print("Axis value={:>6.3f}".format(axis_value))
		self._accel = (axis_value * self.max_accel) - self.friction
		self._speed += self._accel
		if(self._speed > self.max_speed):
			self._speed = self.max_speed
		if(self._speed < 0):
			self._speed = 0 # No reversing!
		self.set_speed(self._speed)

		print("Accel={:>6.3f}".format(self._accel))
		print("Speed={:>6.3f}".format(self._speed))

		Sprite.update(self)

class Player():
	def __init__(self, name):
		self.name = name
	def draw(self, offset):
		font = pygame.font.SysFont("Verdana", 14, True)
		render = font.render(self.name, True, (0,0,0))
		screen.blit(render, (10,10+(20*offset)))

screen.fill((255, 0, 228))
background = pygame.image.load("map1.png").convert_alpha()
screen.blit(background, (0, 0))
pygame.display.flip()

players = []
for player in settings['players']:
	players.append(Player(player['name']))


cars = pygame.sprite.RenderClear([])
things = [cars]
cars.add(Car(800, 600))

done = False
while not done:
	screen.blit(background, (0, 0))
	drawcounter = 0
	for p in players:
		p.draw(drawcounter)
		drawcounter += 1

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
				done = True
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
				done = True

	for j in joysticks:
		j.init()
		#print(j.get_name())
		for i in range(j.get_numaxes()):
			axis = j.get_axis(i)
			#print("Axis {} value: {:>6.3f}".format(i, axis))
		for i in range(j.get_numbuttons()):
			button = j.get_button(i)
			#print("Button {:>2} value: {}".format(i, button))

	for thing in things:
		thing.update()
		thing.draw(screen)

	clock.tick(60)
	pygame.display.flip()

print("Why you quit already? :(")
