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
	_sprite_filenames = ("car_white.png",)
	max_speed = 20
	_speed = 0
	max_accel = 1
	_accel = 0
	max_turn = 5
	_turn = 0
	friction = 0.3

	def __init__(self, x, y, player):
		Sprite.__init__(self, self._sprite_filenames, x, y)
		self.player=player
		self.j=player.joystick
		self._light, = imgload(["light.png"])

	def update(self):
		axis_value = joysticks[self.j['joystick_id']].get_axis(self.j['turn_axis'])
		self._turn = -int(axis_value*self.max_turn)
		self._rot = (self._rot + self._turn) % 360

		axis_value = (1+joysticks[self.j['joystick_id']].get_axis(self.j['accelerate_axis']))/2 - (1+joysticks[self.j['joystick_id']].get_axis(self.j['retard_axis']))/2
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

	def draw_light(self, surface):
		visible = self._light[self._rot][0].copy()
		r = radians(self._rot)
		off = [sin(r) * 240, cos(r) * 240]
		center = visible.get_rect().center
		blt_pos = (self._pos[0] + off[0] - center[0], self._pos[1] + off[1] - center[1], )
		area = visible.get_rect(top=blt_pos[1], left=blt_pos[0])
		visible.blit(background, (0, 0), area, pygame.BLEND_ADD)
		surface.blit(visible, blt_pos)

class Player():
	def __init__(self, settings):
		for key, value in settings.iteritems():
			setattr(self, key, value)
		self.car = Car(800,600,self)
		cars.add(self.car)

	def draw(self, offset):
		font = pygame.font.SysFont("Verdana", 14, True)
		render = font.render(self.name, True, (0,0,0))
		screen.blit(render, (10,10+(20*offset)))

screen.fill((255, 0, 228))
background = pygame.image.load("map1.png").convert_alpha()
pygame.display.flip()

cars = pygame.sprite.RenderClear([])
players = []
for player in settings['players']:
	players.append(Player(player))

things = [cars]

done = False
while not done:
	screen.fill((255, 0, 228))
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
	for car in cars:
		car.draw_light(screen)
	for thing in things:
		thing.draw(screen)

	clock.tick(60)
	pygame.display.flip()

print("Why you quit already? :(")
