"""Small image filters shared by the camera fit and the residual-motion step."""

import torch
import torch.nn.functional as F

BLUR = torch.tensor([1.0, 4.0, 6.0, 4.0, 1.0]) / 16.0  # 5-tap binomial, sigma ~1 px


def blur(x):
    """Separable binomial blur of (K, h, w) frames with replicated borders."""
    k = BLUR.to(x.dtype)
    y = F.conv2d(F.pad(x[:, None], (2, 2, 0, 0), mode="replicate"), k.view(1, 1, 1, 5))
    y = F.conv2d(F.pad(y, (0, 0, 2, 2), mode="replicate"), k.view(1, 1, 5, 1))
    return y[:, 0]


def gradients(x):
    """Central-difference gradients of (K, h, w) frames (0 on the outermost pixels)."""
    gx = torch.zeros_like(x)
    gy = torch.zeros_like(x)
    gx[:, :, 1:-1] = (x[:, :, 2:] - x[:, :, :-2]) / 2
    gy[:, 1:-1, :] = (x[:, 2:, :] - x[:, :-2, :]) / 2
    return gx, gy
