import os
import pygame as pg

class Assets:
    def __init__(self, base_dir="assets"):
        self.base_dir = base_dir
        self._img_cache = {}
        self._snd_cache = {}

    def _path(self, *parts):
        return os.path.join(self.base_dir, *parts)

    def image(self, rel_path, size=None, fallback_draw=None, alpha=True):
        key = (rel_path, size, alpha)
        if key in self._img_cache:
            return self._img_cache[key].copy()

        path = self._path("images", rel_path)
        surf = None
        if os.path.exists(path):
            surf = pg.image.load(path)
            surf = surf.convert_alpha() if alpha else surf.convert()
            if size is not None:
                surf = pg.transform.smoothscale(surf, size)
        else:
            # Плейсхолдер
            w, h = size if size else (64, 64)
            surf = pg.Surface((w, h), pg.SRCALPHA)
            if fallback_draw:
                fallback_draw(surf)
            else:
                pg.draw.rect(surf, (180, 180, 180), (0, 0, w, h), 2)

        self._img_cache[key] = surf
        return surf.copy()

    def sound(self, rel_path, volume=0.4):
        path = self._path("sounds", rel_path)
        if not os.path.exists(path):
            return None
        if rel_path in self._snd_cache:
            s = self._snd_cache[rel_path]
            s.set_volume(volume)
            return s
        s = pg.mixer.Sound(path)
        s.set_volume(volume)
        self._snd_cache[rel_path] = s
        return s

    def music(self, rel_path, volume=0.25):
        path = self._path("sounds", rel_path)
        if not os.path.exists(path):
            return False
        pg.mixer.music.load(path)
        pg.mixer.music.set_volume(volume)
        return True
