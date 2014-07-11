#!/usr/bin/env python

from __future__ import print_function, division

import pygame
import pygame.joystick
from operator import add, sub, div
from math import atan2, degrees, radians, sin, cos
from functools import partial
from workarounds import print
from settings import settings

pygame.init()
pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
pygame.font.init()
clock = pygame.time.Clock()
collcmp = pygame.sprite.collide_mask

screen = pygame.display.set_mode([1600, 1200])
pygame.display.set_caption(settings['game']['name'])
verdana16 = pygame.font.SysFont("Verdana", 16, True)

if not pygame.mixer: print('Warning, sound disabled')
pygame.mixer.init(44100, -16, 2, 2048)
_snd_beep = pygame.mixer.Sound("beep.wav")

global things
_images = {}

def imgload(names, step=1):
	for name in names:
		if name not in _images:
			img = pygame.image.load(name).convert_alpha()
			def rot(deg):
				i = pygame.transform.rotozoom(img, deg, 1)
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
		self.rect = pygame.rect.Rect(0, 0, 1, 1)
		self._stuck = False
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
	def try_set_rotate(self, rot):
		z = map(div, map(add, self.image.get_size(), self._offset), (2, 2))
		x, y = map(int, self._pos)
		xz, yz = z
		xo, yo = self._offset
		rect = (x - xz + xo, y - yz + yo)
		print(self._imgs[0][int(rot)][1], rect)
		if not map_mask.overlap(self._imgs[0][rot][1], rect):
			self._rot = rot
	def update(self):
		z = map(div, map(add, self.image.get_size(), self._offset), (2, 2))
		xz, yz = z
		xo, yo = self._offset
		if self._move:
			#self._pathify(z)
			new_pos = map(add, self._pos, self._move)
			x, y = map(int, new_pos)
			if map_mask.overlap(self.mask, (x - xz + xo, y - yz + yo)):
				effects.add(Effect(self._pos, "Bump!", 60, self.player.color))
				self._health -= abs(self._speed)
				self._speed = 0
				self.set_speed(0)
				if self._stuck:
					new_pos = self._pos
				else:
					new_pos = map(sub, self._pos, self._move) # don't get stuck
					self._stuck = True
			else:
				self._stuck = False
			self._pos = new_pos
		self._newimg()
		x, y = map(int, self._pos)
		self.rect = pygame.rect.Rect(x - xz + xo, y - yz + yo, xz * 2, yz * 2)

class Car(Sprite):
	_sprite_filenames = ("car_white.png",)
	_speed = 0
	_accel = 0
	_turn = 0
	_health = 100
	_beeping = False

	def __init__(self, pos, player):
		x = pos[0]
		y = pos[1]
		Sprite.__init__(self, self._sprite_filenames, x, y)
		self._rot = pos[2]
		self._colourize(player.color)
		self.player=player
		self.j=player.joystick # Joystick settings
		self.J=joysticks[self.j['joystick_id']] # (pygame) Joystick object
		self._light, = imgload(["light.png"])

	def _colourize(self, color): # dat spelling
		imgs = []
		colour = pygame.Surface([1000, 1000])
		colour.fill(color)
		for i in self._imgs:
			d = {}
			for k, (s, m) in i.iteritems():
				s = s.copy()
				s.blit(colour, (0, 0), None, pygame.BLEND_RGB_MIN)
				d[k] = s, m
			imgs.append(d)
		self._imgs = imgs
		if self._move:
			self._newimg()
		else:
			self._img = self._imgs[0]
			self.image, self.mask = self._img[0]

	def death(self):
		effects.add(Effect(self._pos, "R.I.P.", 120, self.player.color))
		Sprite.kill(self)

	def update(self):
		if self._health <= 0:
			self.death()

		axis_value = self.J.get_axis(self.j['turn_axis'])
		if self._speed != 0:
			self._turn = -int(axis_value*self.max_turn)
			self.try_set_rotate((self._rot + self._turn) % 360)

		accel_value = (1+self.J.get_axis(self.j['accelerate_axis']))/2
		retard_value = (1+self.J.get_axis(self.j['retard_axis']))/2
		if accel_value > 0.5 and retard_value > 0.5:
			self._health -= .1
		axis_value = accel_value - retard_value
		print("Axis value={:>6.3f}".format(axis_value))
		self._accel = (axis_value * (max(self.friction*1.5, self.max_accel * self._health/100))) - self.friction

		if((self.J.get_button(self.j['reverse_button']))):
			if(self._speed <= 0):
				self._speed = -self.reverse_speed
				if not self._beeping:
					self._beeping = True
					_snd_beep.play(-1)
				self._accel = 0
			else:
				pass # Stop before you reverse!
		else:
			if self._beeping:
				self._beeping = False
				_snd_beep.stop()

		self._speed += self._accel
		if(self._speed > self.max_speed):
			self._speed = self.max_speed
		if(self._speed < 0):
			if(not (self.J.get_button(self.j['reverse_button']))):
				self._speed = 0 # Stop unintentional reversing

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

	def bump(self, force):
		effects.add(Effect(self._pos, "Bump!", 60, self.player.color))
		self._health -= force
		self._pos = map(sub, self._pos, self._move)
		self._speed = 0
		self._move = [0, 0]

class SportyCar(Car):
	max_speed = 10
	reverse_speed = 1
	max_accel = .3
	max_turn = 5
	friction = 0.1

class CheapCar(Car):
	max_speed = 4
	reverse_speed = 1
	max_accel = .15
	max_turn = 7
	friction = 0.1

car_types = {t.__name__: t for t in globals().values() if isinstance(t, type) and Car in t.mro() and t is not Car}

class Effect(pygame.sprite.Sprite):
	def __init__(self, pos, text, lifetime, color):
		pygame.sprite.Sprite.__init__(self)
		self._pos = pos
		self._lifetime = lifetime
		render = verdana16.render(text, True, color, (0, 0, 0))
		self.rect = render.get_rect(left=pos[0], top=pos[1])
		self.image = render
		self.image.set_alpha(255)
		self.image.set_colorkey((0, 0, 0))
	def update(self):
		step = 255/self._lifetime
		alpha = self.image.get_alpha() - step
		if alpha <= 0:
			self.kill()
		self.image.set_alpha(alpha)

class Player():
	def __init__(self, settings, pos):
		for key, value in settings.iteritems():
			setattr(self, key, value)
		car_type = car_types.get(self.car, CheapCar)
		car_positions = {
			0: [240,145,320],
			1: [1460,255,220],
			2: [150,1085,90],
			3: [1340,1064,180]
		}
		self.car = car_type(car_positions[pos], self)
		print(self.car)
		cars.add(self.car)
		s = "%s (%d %%)" % (self.name, 100)
		render = verdana16.render(s, True, self.color)
		text_positions = {
			0: [10, 10],
			1: [screen.get_size()[0]-10-render.get_size()[0], 10],
			2: [10, screen.get_size()[1]-10-render.get_size()[1]],
			3: [screen.get_size()[0]-10-render.get_size()[0], screen.get_size()[1]-10-render.get_size()[1]]
		}
		self._draw = partial(screen.blit, dest=text_positions[pos])
	
	def draw(self):
		s = "%s (%d %%)" % (self.name, self.car._health)
		render = verdana16.render(s, True, self.color)
		self._draw(render)

screen.fill((0, 0, 0))
background = pygame.image.load("map1.png").convert_alpha()
map_mask = pygame.image.load("map1.mask.png")
map_mask.set_colorkey((255, 255, 255, ))
map_mask = pygame.mask.from_surface(map_mask)
pygame.display.flip()

cars = pygame.sprite.RenderClear([])
effects = pygame.sprite.RenderClear([])
players = []
for pos, player in enumerate(settings['players']):
	players.append(Player(player, pos))

things = [cars, effects]

done = False
while not done:
	screen.fill((0, 0, 0))
	for p in players:
		p.draw()

	for event in pygame.event.get():
		if event.type == pygame.QUIT:
				done = True
		elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
				done = True

	for j in joysticks:
		j.init()

	for thing in things:
		thing.update()
	for car in cars:
		car.draw_light(screen)
	for thing in things:
		thing.draw(screen)

	coll = list(cars)
	for e in list(cars):
		for c in pygame.sprite.spritecollide(e, coll, False, collcmp):
			if c is not e:
				c.bump(5)

	clock.tick(60)
	pygame.display.flip()

print("Why you quit already? :(")
