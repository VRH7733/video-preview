"""Small image filters shared by the camera fit and the residual-motion step."""

import torch
import torch.nn.functional as F


def blur(x):
    """Separable 5-tap binomial blur [1 4 6 4 1] / 16 (sigma ~1 px) of (K, h, w) frames, replicated borders.

    Written as shifted adds: on CPU this is ~6x faster than conv2d with a 1x5 kernel on one channel.
    """
    h, w = x.shape[-2:]
    p = F.pad(x[:, None], (2, 2, 2, 2), mode="replicate")[:, 0]
    y = p[:, :, 0:w] + p[:, :, 4:w + 4] + 4 * (p[:, :, 1:w + 1] + p[:, :, 3:w + 3]) + 6 * p[:, :, 2:w + 2]
    return (y[:, 0:h] + y[:, 4:h + 4] + 4 * (y[:, 1:h + 1] + y[:, 3:h + 3]) + 6 * y[:, 2:h + 2]) / 256


def gradients(x):
    """Central-difference gradients of (K, h, w) frames (0 on the outermost pixels)."""
    gx = torch.zeros_like(x)
    gy = torch.zeros_like(x)
    gx[:, :, 1:-1] = (x[:, :, 2:] - x[:, :, :-2]) / 2
    gy[:, 1:-1, :] = (x[:, 2:, :] - x[:, :-2, :]) / 2
    return gx, gy
