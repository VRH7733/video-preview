"""Timeline chart as an IMAGE tensor (no plotting library).

Layout, left to right = time:
  green bars  : % of the picture that moves on its own (scale: 0 .. max(3 x min_area, peak))
  yellow dash : the min_area threshold
  blue line   : camera speed (scale: 0 .. max(3 x camera threshold, peak))
  bottom strip: green = moving on its own, red = not moving, grey = too little detail
"""

import torch

WIDTH, HEIGHT, STRIP = 768, 192, 14
BG = (0.11, 0.11, 0.12)
BAR = (0.25, 0.78, 0.38)
LINE = (0.35, 0.62, 1.0)
THRESH = (0.95, 0.82, 0.25)
STILL = (0.85, 0.27, 0.25)
FLAT = (0.45, 0.45, 0.45)


def _paint(img, mask, color):
    img[mask] = torch.tensor(color)


def timeline(moving, camera, min_area, camera_min, low_texture):
    """moving, camera: per time step lists; low_texture: list of bools. Returns (1, HEIGHT, WIDTH, 3)."""
    img = torch.empty(HEIGHT, WIDTH, 3)
    img[:] = torch.tensor(BG)
    n = len(moving)
    if n == 0:
        return img[None]
    plot_h = HEIGHT - STRIP - 6
    col = torch.arange(WIDTH)
    step = (col * n // WIDTH).clamp(max=n - 1)
    mv = torch.tensor(moving, dtype=torch.float32)[step]
    cm = torch.tensor(camera, dtype=torch.float32)[step]
    flat = torch.tensor(low_texture, dtype=torch.bool)[step]
    top_m = max(3 * min_area, float(mv.max()), 1e-6)
    top_c = max(3 * camera_min, float(cm.max()), 1e-6)
    rows = torch.arange(HEIGHT)[:, None]
    base = plot_h + 2  # y of the zero line
    bar_h = (mv / top_m * plot_h).round()
    _paint(img, (rows < base) & (rows >= base - bar_h[None]), BAR)
    thr_y = int(base - round(min_area / top_m * plot_h))
    _paint(img, (rows == thr_y) & ((col // 6) % 2 == 0)[None], THRESH)
    cam_y = (base - cm / top_c * plot_h).round()
    prev = torch.cat([cam_y[:1], cam_y[:-1]])
    lo, hi = torch.minimum(cam_y, prev) - 1, torch.maximum(cam_y, prev)
    _paint(img, (rows >= lo[None]) & (rows <= hi[None]), LINE)
    strip = (rows >= HEIGHT - STRIP) & torch.ones(WIDTH, dtype=torch.bool)[None]
    active = (mv >= min_area) & ~flat
    _paint(img, strip & active[None], BAR)
    _paint(img, strip & (~active & ~flat)[None], STILL)
    _paint(img, strip & flat[None], FLAT)
    return img[None]
