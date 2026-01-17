import os
import random
import pygame as pg

from .config import (
    WIDTH, HEIGHT, FPS, TITLE,
    UI_MARGIN,
    ENERGY_MAX,
    FORMATION_SPEED, FORMATION_DROP, FORMATION_MARGIN,
    ENABLE_METEORS, SPAWN_METEOR_BASE_MS, SPAWN_METEOR_MIN_MS,
    DROP_CHANCE, DROP_HP_WEIGHT,
)
from .assets import Assets
from .storage import load_highscore, save_highscore
from .sprites import Player, Meteor, Explosion, FormationController, FormationEnemy, Boss, Pickup


def draw_bar(surface, x, y, w, h, value01):
    value01 = max(0.0, min(1.0, value01))
    pg.draw.rect(surface, (40, 40, 55), (x, y, w, h), border_radius=6)
    pg.draw.rect(surface, (120, 200, 255), (x, y, int(w * value01), h), border_radius=6)
    pg.draw.rect(surface, (220, 220, 220), (x, y, w, h), 2, border_radius=6)


class Starfield:
    def __init__(self, count=170):
        self.stars = []
        for _ in range(count):
            self.stars.append([random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1), random.randint(40, 220)])

    def update(self, dt, speed=260):
        for s in self.stars:
            s[1] += int((speed + s[2]) * dt * 0.35)
            if s[1] > HEIGHT:
                s[1] = -random.randint(0, 80)
                s[0] = random.randint(0, WIDTH - 1)
                s[2] = random.randint(40, 220)

    def draw(self, surface):
        for x, y, b in self.stars:
            surface.set_at((x, y), (b, b, b))


class Game:
    def __init__(self):
        pg.init()
        try:
            pg.mixer.init()
        except Exception:
            pass

        self.screen = pg.display.set_mode((WIDTH, HEIGHT))
        pg.display.set_caption(TITLE)
        self.clock = pg.time.Clock()

        self.font = pg.font.SysFont("consolas", 22)
        self.big = pg.font.SysFont("consolas", 52)

        self.assets = Assets()
        self.state = "menu"
        self.running = True

        self.highscore = load_highscore()
        self.last_score = 0
        self.last_end = "lose"

        self.snd_press = self.assets.sound("button_press.wav", volume=0.55)
        self.snd_splash = self.assets.sound("splash.wav", volume=0.55)
        self.snd_lose = self.assets.sound("gamelose.wav", volume=0.75)
        self.snd_win = self.assets.sound("gamewin.wav", volume=0.75)

        if self.assets.music("music.ogg", volume=0.20):
            try:
                pg.mixer.music.play(-1)
            except Exception:
                pass

    def run(self):
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0
            if self.state == "menu":
                self._menu_loop()
            elif self.state == "play":
                self._play_loop(dt)
            elif self.state == "gameover":
                self._gameover_loop()
        pg.quit()

    def _menu_loop(self):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.running = False
                return
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_RETURN:
                    if self.snd_press:
                        self.snd_press.play()
                    self._start_game()
                    return
                if e.key == pg.K_ESCAPE:
                    self.running = False
                    return

        self.screen.fill((10, 10, 20))
        title = self.big.render("SPACE SHOOTER", True, (235, 235, 235))
        self.screen.blit(title, title.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 90)))

        info = self.font.render("ENTER - Start   ESC - Quit", True, (210, 210, 210))
        self.screen.blit(info, info.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 20)))

        controls = self.font.render("Move: WASD/Arrows | Shoot: HOLD SPACE | Boost: SHIFT | Pause: P", True, (180, 180, 180))
        self.screen.blit(controls, controls.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 20)))

        hs = self.font.render(f"High score: {self.highscore}", True, (200, 200, 200))
        self.screen.blit(hs, hs.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 70)))

        pg.display.flip()

    def _start_game(self):
        if self.snd_splash:
            self.snd_splash.play()
        self.play = PlaySession(self.screen, self.assets, self.font, self.big, self.highscore)
        self.state = "play"

    def _play_loop(self, dt):
        result = self.play.step(dt)
        if result is None:
            return

        mode, score = result
        self.last_score = score

        if score > self.highscore:
            self.highscore = score
            save_highscore(self.highscore)

        if mode == "menu":
            self.state = "menu"
        elif mode == "quit":
            self.running = False
        elif mode in ("win", "lose"):
            self.last_end = mode
            if mode == "win":
                if self.snd_win:
                    self.snd_win.play()
            else:
                if self.snd_lose:
                    self.snd_lose.play()
            self.state = "gameover"

    def _gameover_loop(self):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                self.running = False
                return
            if e.type == pg.KEYDOWN:
                uni = (e.unicode or "").lower()
                if e.key in (pg.K_RETURN, pg.K_r) or uni == "r":
                    if self.snd_press:
                        self.snd_press.play()
                    self._start_game()
                    return
                if e.key == pg.K_ESCAPE:
                    self.state = "menu"
                    return

        self.screen.fill((15, 8, 12))
        headline = "YOU WIN" if self.last_end == "win" else "GAME OVER"
        t = self.big.render(headline, True, (255, 230, 200) if self.last_end == "win" else (255, 200, 200))
        self.screen.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 70)))

        s = self.font.render(f"Score: {self.last_score}", True, (230, 230, 230))
        self.screen.blit(s, s.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 10)))

        h = self.font.render(f"High score: {self.highscore}", True, (230, 230, 230))
        self.screen.blit(h, h.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 25)))

        i = self.font.render("Restart: R / Enter    ESC - Menu", True, (200, 200, 200))
        self.screen.blit(i, i.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 70)))

        pg.display.flip()


class WaveManager:
    def __init__(self, assets):
        self.assets = assets
        self.wave_number = 1
        self.controller = None

    def _diamond(self, cx, cy, dx, dy):
        pts = []
        rows = [1, 2, 3, 2, 1]
        y = cy
        for n in rows:
            x0 = cx - (n - 1) * dx / 2
            for i in range(n):
                pts.append((x0 + i * dx, y))
            y += dy
        return pts

    def _line(self, cx, cy, n, dx):
        x0 = cx - (n - 1) * dx / 2
        return [(x0 + i * dx, cy) for i in range(n)]

    def _two_lines(self, cx, cy, n, dx, dy):
        top = self._line(cx, cy, n, dx)
        bot = self._line(cx, cy + dy, n, dx)
        return top + bot

    def _v_shape(self, cx, cy, n, dx, dy):
        pts = []
        half = n // 2
        for i in range(n):
            d = abs(i - half)
            x = cx + (i - half) * dx
            y = cy + d * dy
            pts.append((x, y))
        return pts

    def spawn_wave(self, enemies_group, all_group, bosses_group):
        self.controller = None

        if self.wave_number == 4:
            boss = Boss(self.assets)
            bosses_group.add(boss)
            all_group.add(boss)
            self.wave_number += 1
            return True

        cx = WIDTH // 2
        start_y = 70
        dx = 92
        dy = 70

        pattern_id = (self.wave_number - 1) % 4
        if pattern_id == 0:
            pts = self._diamond(cx, 0, dx, dy)
        elif pattern_id == 1:
            pts = self._line(cx, 0, 10, dx)
        elif pattern_id == 2:
            pts = self._two_lines(cx, 0, 8, dx, dy)
        else:
            pts = self._v_shape(cx, 0, 11, dx, dy)

        min_x = min(p[0] for p in pts)
        max_x = max(p[0] for p in pts)
        self.controller = FormationController(left_span=min_x, right_span=max_x, start_y=start_y)

        p_enemy2 = min(0.20 + (self.wave_number - 1) * 0.12, 0.75)
        shoot_rate = 1.0 + (self.wave_number * 0.06)

        for p in pts:
            kind = "enemy2" if random.random() < p_enemy2 else "enemy1"
            e = FormationEnemy(self.assets, self.controller, p, kind=kind, shoot_rate=shoot_rate)
            enemies_group.add(e)
            all_group.add(e)

        self.wave_number += 1
        return False


class PlaySession:
    def __init__(self, screen, assets, font, big_font, highscore):
        self.screen = screen
        self.assets = assets
        self.font = font
        self.big_font = big_font
        self.highscore = highscore

        self.starfield = Starfield()

        self.all_sprites = pg.sprite.Group()
        self.enemies = pg.sprite.Group()
        self.bosses = pg.sprite.Group()
        self.meteors = pg.sprite.Group()
        self.pickups = pg.sprite.Group()

        self.bullets_player = pg.sprite.Group()
        self.bullets_enemy = pg.sprite.Group()
        self.fx = pg.sprite.Group()

        self.player = Player(assets)
        self.all_sprites.add(self.player)

        self.snd_expl = assets.sound("explosion.wav", volume=0.35)
        self.snd_pick_hp = assets.sound("pick_hp.wav", volume=0.65)
        self.snd_pick_module = assets.sound("pick_module.wav", volume=0.65)
        self.snd_bosscoming = assets.sound("bosscoming.wav", volume=0.80)

        self.explosion_frames = self._proc_explosion_frames()

        self.score = 0
        self.paused = False

        self.hp_icon = assets.image("hp.png", size=(28, 28), fallback_draw=None)
        self.up_icon = assets.image("upgrade_module.png", size=(26, 26), fallback_draw=None)

        self.wave = WaveManager(assets)
        boss_spawned = self.wave.spawn_wave(self.enemies, self.all_sprites, self.bosses)
        if boss_spawned and self.snd_bosscoming:
            self.snd_bosscoming.play()

        self.meteor_timer = 0.0

        bg_path = os.path.join("assets", "images", "background.png")
        self.bg = assets.image("background.png", size=(WIDTH, HEIGHT), fallback_draw=None) if os.path.exists(bg_path) else None
        self.bg_scroll = 0.0

    def _proc_explosion_frames(self):
        frames = []
        base = None
        try:
            base = self.assets.image("spark.png", size=(40, 40), fallback_draw=None)
        except Exception:
            base = None

        if base is not None:
            for i in range(9):
                size = 26 + i * 10
                img = pg.transform.smoothscale(base, (size, size))
                img = pg.transform.rotate(img, i * 22)
                img = img.convert_alpha()
                img.set_alpha(max(0, 255 - i * 28))
                frames.append(img)
            return frames

        for r in range(6, 54, 6):
            s = pg.Surface((72, 72), pg.SRCALPHA)
            pg.draw.circle(s, (255, 210, 120), (36, 36), r)
            pg.draw.circle(s, (255, 140, 90), (36, 36), max(2, r - 12))
            pg.draw.circle(s, (80, 40, 30), (36, 36), max(2, r - 26), 2)
            frames.append(s)
        return frames

    def step(self, dt):
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return ("quit", self.score)
            if e.type == pg.KEYDOWN:
                if e.key == pg.K_ESCAPE:
                    return ("menu", self.score)
                if e.key == pg.K_p:
                    self.paused = not self.paused

        if self.paused:
            self._draw(paused=True)
            return None

        keys = pg.key.get_pressed()
        self.player.update(dt, keys)

        if keys[pg.K_SPACE]:
            if self.player.can_shoot():
                bullets = self.player.shoot()
                for b in bullets:
                    self.bullets_player.add(b)
                    self.all_sprites.add(b)

        if self.wave.controller is not None and len(self.enemies) > 0:
            speed = FORMATION_SPEED + (self.wave.wave_number * 5)
            self.wave.controller.update(dt, speed=speed, drop=FORMATION_DROP, margin=FORMATION_MARGIN)

        self.starfield.update(dt, speed=275 + self.wave.wave_number * 6)

        self.enemies.update(dt)
        self.bosses.update(dt)
        self.meteors.update(dt)
        self.pickups.update(dt)
        self.bullets_player.update(dt)
        self.bullets_enemy.update(dt)
        self.fx.update(dt)

        for en in list(self.enemies):
            bullet = en.try_shoot(self.player.rect.center)
            if bullet:
                self.bullets_enemy.add(bullet)
                self.all_sprites.add(bullet)

        for boss in list(self.bosses):
            bullets = boss.try_shoot()
            if bullets:
                for b in bullets:
                    self.bullets_enemy.add(b)
                    self.all_sprites.add(b)

        if len(self.enemies) == 0 and len(self.bosses) == 0:
            boss_spawned = self.wave.spawn_wave(self.enemies, self.all_sprites, self.bosses)
            if boss_spawned and self.snd_bosscoming:
                self.snd_bosscoming.play()

        if self.wave.controller is not None:
            for en in self.enemies:
                if en.rect.bottom >= HEIGHT - 130:
                    return ("lose", self.score)

        if ENABLE_METEORS and len(self.bosses) == 0:
            base_ms = max(SPAWN_METEOR_MIN_MS, SPAWN_METEOR_BASE_MS - (self.wave.wave_number * 30))
            interval = base_ms / 1000.0
            self.meteor_timer += dt
            if self.meteor_timer >= interval:
                self.meteor_timer = 0.0
                m = Meteor(self.assets, level=self.wave.wave_number)
                self.meteors.add(m)
                self.all_sprites.add(m)

        hits = pg.sprite.groupcollide(self.enemies, self.bullets_player, False, True)
        for enemy, bullets in hits.items():
            if enemy.damage(len(bullets)):
                self._explode(enemy.rect.center)
                self._maybe_drop(enemy.rect.center)
                self.score += 25 if enemy.kind == "enemy2" else 12
                enemy.kill()

        boss_hits = pg.sprite.groupcollide(self.bosses, self.bullets_player, False, True)
        for boss, bullets in boss_hits.items():
            if boss.damage(len(bullets)):
                self._explode(boss.rect.center)
                self.score += 500
                boss.kill()
                return ("win", self.score)

        hits_m = pg.sprite.groupcollide(self.meteors, self.bullets_player, False, True)
        for meteor, bullets in hits_m.items():
            if meteor.damage(len(bullets)):
                self._explode(meteor.rect.center)
                self._maybe_drop(meteor.rect.center)
                self.score += 8
                meteor.kill()

        if pg.sprite.spritecollide(self.player, self.bullets_enemy, True):
            self.player.damage(1)
            if self.player.hp <= 0:
                return ("lose", self.score)

        if (pg.sprite.spritecollide(self.player, self.enemies, True) or
                pg.sprite.spritecollide(self.player, self.bosses, False) or
                pg.sprite.spritecollide(self.player, self.meteors, True)):
            self.player.damage(1)
            if self.player.hp <= 0:
                return ("lose", self.score)

        collected = pg.sprite.spritecollide(self.player, self.pickups, True)
        for p in collected:
            if p.kind == "hp":
                self.player.heal(1)
                if self.snd_pick_hp:
                    self.snd_pick_hp.play()
            else:
                self.player.upgrade_weapon()
                if self.snd_pick_module:
                    self.snd_pick_module.play()

        self._draw(paused=False)
        return None

    def _maybe_drop(self, pos):
        if random.random() > DROP_CHANCE:
            return
        kind = "hp" if random.random() < DROP_HP_WEIGHT else "upgrade"
        p = Pickup(self.assets, kind, pos)
        self.pickups.add(p)
        self.all_sprites.add(p)

    def _explode(self, pos):
        if self.snd_expl:
            self.snd_expl.play()
        ex = Explosion(self.explosion_frames, pos, duration=0.30)
        self.fx.add(ex)
        self.all_sprites.add(ex)

    def _draw(self, paused=False):
        self.screen.fill((10, 10, 20))
        if self.bg is not None:
            self.bg_scroll = (self.bg_scroll + 200) % HEIGHT
            y = int(-self.bg_scroll)
            self.screen.blit(self.bg, (0, y))
            self.screen.blit(self.bg, (0, y + HEIGHT))
        else:
            self.starfield.draw(self.screen)

        self.all_sprites.draw(self.screen)

        x0 = UI_MARGIN
        y0 = UI_MARGIN
        for i in range(self.player.hp):
            self.screen.blit(self.hp_icon, (x0 + i * 30, y0))

        score_text = self.font.render(f"Score: {self.score}", True, (235, 235, 235))
        self.screen.blit(score_text, (UI_MARGIN, UI_MARGIN + 36))

        wave_text = self.font.render(f"Wave: {self.wave.wave_number - 1}", True, (235, 235, 235))
        self.screen.blit(wave_text, (UI_MARGIN, UI_MARGIN + 64))

        draw_bar(self.screen, UI_MARGIN, HEIGHT - 26 - UI_MARGIN, 240, 20, self.player.energy / ENERGY_MAX)

        self.screen.blit(self.up_icon, (UI_MARGIN + 260, HEIGHT - 30 - UI_MARGIN))
        wtxt = self.font.render(f"x{self.player.weapon_level}", True, (220, 220, 220))
        self.screen.blit(wtxt, (UI_MARGIN + 292, HEIGHT - 29 - UI_MARGIN))

        if len(self.bosses) > 0:
            boss = next(iter(self.bosses))
            bhp = self.font.render(f"BOSS HP: {boss.hp}", True, (255, 210, 210))
            self.screen.blit(bhp, (WIDTH - 240, UI_MARGIN))

        if paused:
            t = self.big_font.render("PAUSED", True, (240, 240, 240))
            self.screen.blit(t, t.get_rect(center=(WIDTH // 2, HEIGHT // 2)))

        pg.display.flip()
