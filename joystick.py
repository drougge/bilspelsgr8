#!/usr/bin/env python

from __future__ import print_function, division

import pygame
import pygame.joystick
from operator import add, sub, div
from math import atan2, degrees, radians, sin, cos
from functools import partial
import argparse
from settings import settings

pygame.init()
dispinfo = pygame.display.Info()
max_w, max_h = dispinfo.current_w, dispinfo.current_h
reasonble_x = (640, 800, 960, 1024, 1152, 1280, 1366, 1400, 1440, 1600, 1920, 2048, 2560, 2880, 3200, 3840, 4096, 5120, 6400, 7680, 15360)
for cand in reasonble_x:
	if cand <= max_w and cand * 3 // 4 <= max_h:
		screen_x_size = cand

parser = argparse.ArgumentParser(description='An amazing game with cars in a cave.')
parser.add_argument('--xres', metavar='PIXELS', type=int, default=screen_x_size, help='Screen/window width (default %d, ideal 1600)' % (screen_x_size, ))
parser.add_argument('--fullscreen', action='store_const', const=pygame.FULLSCREEN, default=0, help='Run fullscreen')
parser.add_argument('--map', type=int, default=1, help='Map number to play on')
args = parser.parse_args()

# After possibly printing help, not before
from workarounds import print

screen_x_size = args.xres
# Some sort of sanity check
assert screen_x_size in reasonble_x, "Invalid screen size"

pygame.joystick.init()
joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]
pygame.font.init()
clock = pygame.time.Clock()

if screen_x_size == 1600:
	def scaled(s):
		return s
	collcmp = pygame.sprite.collide_mask
else:
	def adjust_size(size):
		return size * screen_x_size // 1600
	def scaled(s):
		if isinstance(s, pygame.rect.Rect):
			return pygame.rect.Rect(*map(adjust_size, (s.left, s.top, s.width, s.height)), center=map(adjust_size, s.center))
		elif isinstance(s, (tuple, list)):
			return map(adjust_size, s)
		elif isinstance(s, int):
			return adjust_size(s)
		else:
			return pygame.transform.smoothscale(s, map(adjust_size, s.get_size()))
	def collcmp(a, b):
		a.rect, a._rect = a._rect, a.rect
		b.rect, b._rect = b._rect, b.rect
		r = pygame.sprite.collide_mask(a, b)
		a.rect, a._rect = a._rect, a.rect
		b.rect, b._rect = b._rect, b.rect
		return r

screen = pygame.display.set_mode(scaled([1600, 1200]), args.fullscreen)
pygame.display.set_caption(settings['game']['name'].encode('utf-8')) # stupid pygame
verdana16 = pygame.font.SysFont("Verdana", scaled(16), True)

if not pygame.mixer: print('Warning, sound disabled')
pygame.mixer.init(44100, -16, 2, 2048)
_snd_beep = pygame.mixer.Sound("beep.wav")
_snd_bump = pygame.mixer.Sound("bump.wav")
_snd_shot = pygame.mixer.Sound("shot.wav")
_snd_death = pygame.mixer.Sound("trollandi_death.wav")
_snd_hispeed = pygame.mixer.Sound("hispeed.wav")
_snd_midspeed = pygame.mixer.Sound("midspeed.wav")
_snd_lowspeed = pygame.mixer.Sound("lowspeed.wav")

global things
_images = {}

def imgload(names, step=1, rect_instead_of_mask=False):
	for name in names:
		if name not in _images:
			img = pygame.image.load(name).convert_alpha()
			def rot(deg):
				i = pygame.transform.rotozoom(img, deg, 1)
				if rect_instead_of_mask:
					return scaled(i), i.get_rect()
				else:
					return scaled(i), pygame.mask.from_surface(i)
			_images[name] = {deg: rot(deg) for deg in range(0, 360, step or 360)}
	return [_images[name] for name in names]

def load_map(num):
	m = "map%d" % (num,)
	background = scaled(pygame.image.load(m + ".png").convert_alpha())
	map_mask = pygame.image.load(m + ".mask.png")
	map_mask.set_colorkey((255, 255, 255, ))
	map_mask = pygame.mask.from_surface(map_mask)
	map_goals = load_goals(m + ".goals", map_mask.get_size())
	map_towers = load_towers(m + ".towers", map_mask.get_size())
	car_positions = load_cars(m + ".cars")
	return background, map_mask, map_goals, map_towers, car_positions

class Sprite(pygame.sprite.Sprite):
	_animate = False
	_offset = (0, 0)
	_speed = 0

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
		self._speed = speed
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
		image, mask = self._imgs[0][rot]
		z = map(div, map(add, mask.get_size(), self._offset), (2, 2))
		x, y = map(int, self._pos)
		xz, yz = z
		xo, yo = self._offset
		rect = (x - xz + xo, y - yz + yo)
		if not map_mask.overlap(mask, rect):
			self._rot = rot
	def update(self):
		self._newimg()
		z = map(div, map(add, self.mask.get_size(), self._offset), (2, 2))
		xz, yz = z
		xo, yo = self._offset
		if self._move:
			#self._pathify(z)
			new_pos = map(add, self._pos, self._move)
			x, y = map(int, new_pos)
			if map_mask.overlap(self.mask, (x - xz + xo, y - yz + yo)):
				if isinstance(self, Car):
					effects.add(Effect(self._pos, "Bump!", 60, self.player.color))
					_snd_bump.play()
					self._health -= abs(self._speed)
				if isinstance(self, Bullet):
					self.kill()
				if self._stuck:
					new_pos = self._pos
				else:
					new_pos = map(sub, self._pos, self._move) # don't get stuck
					self._stuck = True
				self.set_speed(0)
			else:
				self._stuck = False
			self._pos = new_pos
		x, y = map(int, self._pos)
		self._rect = pygame.rect.Rect(x - xz + xo, y - yz + yo, xz * 2, yz * 2)
		self.rect = scaled(self._rect)

class Bullet(Sprite):
	_sprite_filenames = ("bullet.png",)

	def __init__(self, pos, rot, speed):
		x = pos[0]
		y = pos[1]
		Sprite.__init__(self, self._sprite_filenames, x, y)
		self._rot = rot
		self.set_speed(35 + speed)
		self.update()
		self.set_speed(max(2, speed * 0.7))

	def update(self):
		self.set_speed(self._speed * 0.997)
		if self._speed < .5:
			self.kill()
		Sprite.update(self)

class Car(Sprite):
	_sprite_filenames = ("car_white.png",)
	_speed = 0
	_accel = 0
	_turn = 0
	_health = 100
	_beeping = False
	_sound = None
	_fired_last_tick = False

	def __init__(self, pos, first_goal, player):
		x = pos[0]
		y = pos[1]
		Sprite.__init__(self, self._sprite_filenames, x, y)
		self._rot = pos[2]
		self._colourize(player.color)
		self.player=player
		self.j=player.joystick # Joystick settings
		self.J=joysticks[self.j['joystick_id']] # (pygame) Joystick object
		self._light, = imgload(["light.png"], rect_instead_of_mask=True)
		self._first_goal = self._next_goal = (first_goal + 1) % 4

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
		_snd_death.play()
		self.player.respawn_soon()
		Sprite.kill(self)

	def fire(self):
		self._fired_last_tick = True
		bullets.add(Bullet(self._pos, self._rot, self._speed))
		print("Fire!!")

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
		self._accel = (axis_value * (max(self.friction*1.5, self.max_accel * self._health/100))) - self.friction

		if self.J.get_button(self.j['fire_button']):
			if not self._fired_last_tick:
				self.fire()
		else:
			self._fired_last_tick = False

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

		# Engine sounds!!1
		snd = None
		if self._speed > self.max_speed * 0.8:
			snd = _snd_hispeed
		elif self._speed > self.max_speed * 0.4:
			snd = _snd_midspeed
		elif self._speed > self.max_speed * 0.03:
			snd = _snd_lowspeed
		if snd:
			if self._sound is not snd:
				if self._sound:
					self._sound.stop()
				snd.play(-1)
				self._sound = snd
		elif self._sound:
			self._sound.stop()
			self._sound = None

		Sprite.update(self)

		if map_goals[self._next_goal].overlap(self.mask, map(int, self._pos)):
			self._next_goal = (self._next_goal + 1) % 4
			if self._next_goal == self._first_goal:
				self.player._lap += 1

	def draw_light(self, surface):
		visible, rect = self._light[self._rot]
		r = radians(self._rot)
		off = [sin(r) * 240, cos(r) * 240]
		center = rect.center
		blt_pos = (self._pos[0] + off[0] - center[0], self._pos[1] + off[1] - center[1], )
		area = rect.copy()
		area.left, area.top = blt_pos
		area = scaled(area)
		visible = visible.copy()
		visible.blit(background, (0, 0), area, pygame.BLEND_ADD)
		surface.blit(visible, scaled(blt_pos))

	def bump(self, force, sound):
		effects.add(Effect(self._pos, "Bump!", 60, self.player.color))
		sound.play()
		self._health -= force
		self._pos = map(sub, self._pos, self._move)
		self._speed = 0
		self._move = [0, 0]

class SportyCar(Car):
	max_speed = 10
	reverse_speed = 1
	max_accel = .3
	max_turn = 4
	friction = 0.1

class CheapCar(Car):
	max_speed = 4
	reverse_speed = 1
	max_accel = .15
	max_turn = 4
	friction = 0.1

car_types = {t.__name__: t for t in globals().values() if isinstance(t, type) and Car in t.mro() and t is not Car}

class Effect(pygame.sprite.Sprite):
	def __init__(self, pos, text, lifetime, color):
		pygame.sprite.Sprite.__init__(self)
		self._pos = pos = scaled(pos)
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

class Stopwatch(pygame.sprite.Sprite):
	_time = 0
	color = (255, 255, 255)
	def __init__(self):
		pygame.sprite.Sprite.__init__(self)
		s = "00:00.00"
		render = verdana16.render(s, True, self.color)
		self._pos = (int(screen.get_size()[0]/2 - render.get_size()[0]/2), 10)
		self.rect = render.get_rect(left=self._pos[0], top=self._pos[1])
		self.image = render
		self._draw = partial(screen.blit, dest=self._pos)
	def update(self):
		self._time += 1
	def draw(self):
		ticks = self._time % 60
		seconds = (self._time % (60*60)) // 60
		minutes = self._time // (60*60)
		s = "%2d:%2d.%2d" % (minutes, seconds, ticks)
		render = verdana16.render(s, True, self.color)
		self._draw(render)

class Tower(Sprite):
	_timer = 0
	def __init__(self, pos):
		x = pos[0]
		y = pos[1]
		Sprite.__init__(self, self._sprite_filenames, x, y)

	def update(self):
		Sprite.update(self)
		self._timer += 1
		if self._timer >= self.interval:
			self._timer = 0
			self.fire()

class Ext(Tower):
	_sprite_filenames = ("exttower_1.png", "exttower_2.png", "exttower_3.png", "exttower_4.png")
	interval = 40

	def __init__(self, pos):
		Tower.__init__(self, pos)
		self._animate = 10

	def fire(self):
		bullets.add(Bullet(self._pos, 0, 5))
		bullets.add(Bullet(self._pos, 90, 5))
		bullets.add(Bullet(self._pos, 180, 5))
		bullets.add(Bullet(self._pos, 270, 5))

class Player():
	_respawn_delay = -1

	def __init__(self, settings, pos):
		for key, value in settings.iteritems():
			setattr(self, key, value)
		car_type = car_types.get(self.car, CheapCar)
		self._lap = 1
		self._mk_car = partial(car_type, car_positions[pos], pos, self)
		self.car = self._mk_car()
		cars.add(self.car)
		s = u"%s (%d %%), lap %d of 3" % (self.name, 100, self._lap)
		render = verdana16.render(s, True, self.color)
		text_positions = {
			0: [10, 10],
			1: [10, screen.get_size()[1]-10-render.get_size()[1]],
			2: [screen.get_size()[0]-10-render.get_size()[0], screen.get_size()[1]-10-render.get_size()[1]],
			3: [screen.get_size()[0]-10-render.get_size()[0], 10],
		}
		self._draw = partial(screen.blit, dest=text_positions[pos])
	
	def draw(self):
		s = u"%s (%d %%), lap %d of 3" % (self.name, self.car._health, self._lap)
		render = verdana16.render(s, True, self.color)
		self._draw(render)

	def update(self):
		if self._respawn_delay > 0:
			self._respawn_delay -= 1
		if self._respawn_delay == 0:
			self._respawn_delay = -1
			self._lap = 1
			self.car = self._mk_car()
			cars.add(self.car)

	def respawn_soon(self):
		self._respawn_delay = 300

def load_goals(name, size):
	goals = []
	with open(name, "r") as fh:
		for line in fh:
			plist = [map(int, p.split()) for p in line.split(",")]
			g = pygame.Surface(size)
			g.set_colorkey((0, 0, 0))
			pygame.draw.polygon(g, (255, 255, 255), plist)
			goals.append(pygame.mask.from_surface(g))
	assert len(goals) == 4
	return goals

def load_towers(name, size):
	towers = []
	try:
		with open(name, "r") as fh:
			for line in fh:
				pos = map(int, line.split())
				print(pos)
				towers.append(Ext(pos))
	except IOError:
		pass
	return towers

def load_cars(name):
	cars = []
	with open(name, "r") as fh:
		for line in fh:
			p = map(int, line.split())
			assert len(p) == 3
			cars.append(p)
	assert len(cars) == 4
	return cars

screen.fill((0, 0, 0))
pygame.display.flip()
background, map_mask, map_goals, map_towers, car_positions = load_map(args.map)

cars = pygame.sprite.RenderClear([])
effects = pygame.sprite.RenderClear([])
bullets = pygame.sprite.RenderClear([])
towers = pygame.sprite.RenderClear([])

for t in map_towers:
	towers.add(t)

players = []
for pos, player in enumerate(settings['players']):
	players.append(Player(player, pos))

things = [cars, effects, bullets, towers]

sw = Stopwatch()

done = False
while not done:
	screen.fill((0, 0, 0))

	sw.update()
	sw.draw()

	for p in players:
		p.update()
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
	for _ in range(3):
		for b in bullets:
			b.update()
		for c in cars:
			for b in pygame.sprite.spritecollide(c, bullets, True, collcmp):
				c.bump(15, _snd_shot)
	for thing in things:
		thing.draw(screen)

	for e in cars:
		for c in pygame.sprite.spritecollide(e, cars, False, collcmp):
			if c is not e:
				c.bump(5, _snd_bump)


	clock.tick(60)
	pygame.display.flip()

print("Why you quit already? :(")
