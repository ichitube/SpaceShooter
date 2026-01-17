import random
import pygame as pg
from .config import (
    WIDTH, HEIGHT,
    PLAYER_SPEED, PLAYER_HP_MAX,
    ENERGY_MAX, ENERGY_REGEN_PER_SEC, ENERGY_SHOT_COST, ENERGY_BOOST_COST_PER_SEC, BOOST_MULT,
    BULLET_SPEED_PLAYER, BULLET_SPEED_ENEMY, PLAYER_FIRE_COOLDOWN,
    METEOR_SPEED_MIN, METEOR_SPEED_MAX,
    ENEMY1_HP, ENEMY2_HP, BOSS_HP, BOSS_ENTRY_Y,
)


def clamp_rect(rect: pg.Rect):
    if rect.left < 0:
        rect.left = 0
    if rect.right > WIDTH:
        rect.right = WIDTH
    if rect.top < 0:
        rect.top = 0
    if rect.bottom > HEIGHT:
        rect.bottom = HEIGHT


class Bullet(pg.sprite.Sprite):
    def __init__(self, image, x, y, vx, vy, owner="player"):
        super().__init__()
        self.image = image
        self.rect = self.image.get_rect(center=(x, y))
        self.vx = float(vx)
        self.vy = float(vy)
        self.owner = owner

    def update(self, dt):
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)
        if (self.rect.right < 0 or self.rect.left > WIDTH or
                self.rect.bottom < 0 or self.rect.top > HEIGHT):
            self.kill()


class Explosion(pg.sprite.Sprite):
    def __init__(self, frames, pos, duration=0.32):
        super().__init__()
        self.frames = frames
        self.duration = duration
        self.t = 0.0
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=pos)

    def update(self, dt):
        self.t += dt
        p = min(1.0, self.t / self.duration)
        idx = int(p * (len(self.frames) - 1))
        self.image = self.frames[idx]
        self.rect = self.image.get_rect(center=self.rect.center)
        if self.t >= self.duration:
            self.kill()


class Player(pg.sprite.Sprite):
    def __init__(self, assets):
        super().__init__()
        self.assets = assets

        self.image = assets.image("player.png", size=(74, 84), fallback_draw=None)
        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT - 88))

        self.hp = PLAYER_HP_MAX
        self.hp_max = PLAYER_HP_MAX
        self.energy = ENERGY_MAX

        self.weapon_level = 1
        self.weapon_level_max = 4

        self.fire_cd = PLAYER_FIRE_COOLDOWN
        self.fire_timer = 0.0

        self.snd_shoot = assets.sound("shoot.wav", volume=0.38)
        self.snd_hit = assets.sound("hit.wav", volume=0.35)

        self.bullet_img = assets.image("spark.png", size=(10, 18), fallback_draw=None)

    def update(self, dt, keys):
        self.energy = min(ENERGY_MAX, self.energy + ENERGY_REGEN_PER_SEC * dt)

        speed = PLAYER_SPEED
        boosting = keys[pg.K_LSHIFT] or keys[pg.K_RSHIFT]
        if boosting and self.energy > 0:
            speed *= BOOST_MULT
            self.energy = max(0.0, self.energy - ENERGY_BOOST_COST_PER_SEC * dt)

        vx = vy = 0
        if keys[pg.K_w] or keys[pg.K_UP]:
            vy -= 1
        if keys[pg.K_s] or keys[pg.K_DOWN]:
            vy += 1
        if keys[pg.K_a] or keys[pg.K_LEFT]:
            vx -= 1
        if keys[pg.K_d] or keys[pg.K_RIGHT]:
            vx += 1

        if vx and vy:
            speed *= 0.7071

        self.rect.x += int(vx * speed * dt)
        self.rect.y += int(vy * speed * dt)
        clamp_rect(self.rect)

        self.fire_timer = max(0.0, self.fire_timer - dt)

    def can_shoot(self):
        need = ENERGY_SHOT_COST * self.weapon_level
        return self.fire_timer <= 0.0 and self.energy >= need

    def shoot(self):
        self.fire_timer = self.fire_cd
        self.energy -= ENERGY_SHOT_COST * self.weapon_level
        if self.snd_shoot:
            self.snd_shoot.play()

        cx = self.rect.centerx
        y = self.rect.top + 2

        if self.weapon_level == 1:
            pattern = [(0, 0)]
        elif self.weapon_level == 2:
            pattern = [(-14, -160), (14, 160)]
        elif self.weapon_level == 3:
            pattern = [(-18, -190), (0, 0), (18, 190)]
        else:
            pattern = [(-22, -220), (-8, -70), (8, 70), (22, 220)]

        bullets = []
        for xoff, vx in pattern:
            bullets.append(Bullet(self.bullet_img, cx + xoff, y, vx, -BULLET_SPEED_PLAYER, owner="player"))
        return bullets

    def damage(self, amount=1):
        self.hp -= amount
        if self.snd_hit:
            self.snd_hit.play()

    def heal(self, amount=1):
        self.hp = min(self.hp_max, self.hp + amount)

    def upgrade_weapon(self):
        self.weapon_level = min(self.weapon_level_max, self.weapon_level + 1)


class Pickup(pg.sprite.Sprite):
    def __init__(self, assets, kind, pos):
        super().__init__()
        self.kind = kind
        if kind == "hp":
            self.image = assets.image("hp.png", size=(36, 36), fallback_draw=None)
        else:
            self.image = assets.image("upgrade_module.png", size=(38, 38), fallback_draw=None)
        self.rect = self.image.get_rect(center=pos)
        self.vy = 180

    def update(self, dt):
        self.rect.y += int(self.vy * dt)
        if self.rect.top > HEIGHT + 50:
            self.kill()


class FormationController:
    def __init__(self, left_span, right_span, start_y):
        self.offset_x = 0.0
        self.offset_y = float(start_y)
        self.dir = 1
        self.left_span = float(left_span)
        self.right_span = float(right_span)

    def update(self, dt, speed, drop, margin):
        self.offset_x += self.dir * speed * dt
        left_world = self.offset_x + self.left_span
        right_world = self.offset_x + self.right_span

        if right_world > (WIDTH - margin):
            self.offset_x -= (right_world - (WIDTH - margin))
            self.dir *= -1
            self.offset_y += drop

        if left_world < margin:
            self.offset_x += (margin - left_world)
            self.dir *= -1
            self.offset_y += drop


class FormationEnemy(pg.sprite.Sprite):
    def __init__(self, assets, controller, base_pos, kind, shoot_rate):
        super().__init__()
        self.assets = assets
        self.controller = controller
        self.base_x, self.base_y = base_pos
        self.kind = kind

        if kind == "enemy1":
            self.hp = ENEMY1_HP
            self.image = assets.image("enemy1.png", size=(68, 44), fallback_draw=None)
            self.fire_min, self.fire_max = 1.35, 2.25
            self.bullet_speed_mul = 0.90
            self.snd_vol = 0.12
        else:
            self.hp = ENEMY2_HP
            self.image = assets.image("enemy2.png", size=(74, 50), fallback_draw=None)
            self.fire_min, self.fire_max = 0.85, 1.55
            self.bullet_speed_mul = 1.05
            self.snd_vol = 0.14

        self.rect = self.image.get_rect(center=(0, 0))
        self._sync_pos()

        self.shoot_rate = shoot_rate
        self.fire_timer = random.uniform(self.fire_min, self.fire_max) / max(0.35, self.shoot_rate)

        b = assets.image("spark.png", size=(10, 16), fallback_draw=None)
        self.bullet_img = pg.transform.rotate(b, 180)
        self.snd_shoot = assets.sound("shoot.wav", volume=self.snd_vol)

    def _sync_pos(self):
        cx = int(self.base_x + self.controller.offset_x)
        cy = int(self.base_y + self.controller.offset_y)
        self.rect = self.image.get_rect(center=(cx, cy))

    def update(self, dt):
        self.fire_timer -= dt
        self._sync_pos()

    def damage(self, amount=1):
        self.hp -= amount
        return self.hp <= 0

    def try_shoot(self, player_pos):
        if self.fire_timer > 0:
            return None

        px, _ = player_pos
        dx = px - self.rect.centerx
        dist = max(1.0, abs(dx))

        vx = (dx / dist) * (BULLET_SPEED_ENEMY * 0.32)
        vy = BULLET_SPEED_ENEMY * self.bullet_speed_mul

        self.fire_timer = random.uniform(self.fire_min, self.fire_max) / max(0.35, self.shoot_rate)

        if self.snd_shoot:
            self.snd_shoot.play()

        return Bullet(self.bullet_img, self.rect.centerx, self.rect.bottom - 2, vx, vy, owner="enemy")


class Boss(pg.sprite.Sprite):
    def __init__(self, assets):
        super().__init__()
        self.assets = assets
        self.kind = "boss"
        self.hp = BOSS_HP

        self.image = assets.image("boss.png", size=(280, 200), fallback_draw=None)
        self.rect = self.image.get_rect(midtop=(WIDTH // 2, -220))

        self.state = "enter"
        self.vx = 240
        self.fire_timer = 1.2

        b = assets.image("spark.png", size=(12, 20), fallback_draw=None)
        self.bullet_img = pg.transform.rotate(b, 180)
        self.snd_shoot = assets.sound("shoot.wav", volume=0.18)

    def update(self, dt):
        if self.state == "enter":
            self.rect.y += int(220 * dt)
            if self.rect.y >= BOSS_ENTRY_Y:
                self.rect.y = BOSS_ENTRY_Y
                self.state = "fight"
        else:
            self.rect.x += int(self.vx * dt)
            if self.rect.left < 60:
                self.rect.left = 60
                self.vx *= -1
            if self.rect.right > WIDTH - 60:
                self.rect.right = WIDTH - 60
                self.vx *= -1

        self.fire_timer -= dt

    def damage(self, amount=1):
        self.hp -= amount
        return self.hp <= 0

    def try_shoot(self):
        if self.fire_timer > 0:
            return None

        self.fire_timer = random.uniform(0.55, 0.95)

        bullets = []
        for vx in (-240, -120, 0, 120, 240):
            bullets.append(Bullet(self.bullet_img, self.rect.centerx, self.rect.bottom - 6, vx, BULLET_SPEED_ENEMY * 1.20, owner="enemy"))

        if self.snd_shoot:
            self.snd_shoot.play()

        return bullets


class Meteor(pg.sprite.Sprite):
    def __init__(self, assets, level=1):
        super().__init__()
        size = random.choice([(52, 52), (66, 66), (82, 82)])
        self.image = assets.image("meteor.png", size=size, fallback_draw=None)

        x = random.randint(40, WIDTH - 40)
        y = -random.randint(90, 280)
        self.rect = self.image.get_rect(center=(x, y))

        self.vy = random.randint(METEOR_SPEED_MIN, METEOR_SPEED_MAX) + level * 12
        self.vx = random.randint(-140, 140)

        self.hp = 3 if self.rect.width >= 80 else 2

    def update(self, dt):
        self.rect.x += int(self.vx * dt)
        self.rect.y += int(self.vy * dt)
        if self.rect.left < 0 or self.rect.right > WIDTH:
            self.vx *= -1
        if self.rect.top > HEIGHT + 60:
            self.kill()

    def damage(self, amount=1):
        self.hp -= amount
        return self.hp <= 0
