#!/usr/bin/env python3
"""
UI Kit Quy Chuẩn Toàn Diện (Unified UI Kit) cho Hệ Thống Widget Taskbar Windows & Widget Manager.
Bao gồm:
1. Design Tokens: Spacing (Grid 8pt/4pt), Corner Radii, Shadows, Kích thước chuẩn Taskbar & Flyout.
2. Color Palettes: Bảng màu chuẩn Fluent Dark & Light, Status Colors (OK/WARN/DANGER), Brand Accents.
3. Typography System: Tỉ lệ font Segoe UI đồng bộ, bộ nạp cache font mượt mà.
4. BasePainter & Standard Draw Helpers: Động cơ vẽ PIL siêu lấy mẫu (Supersampling) cho nền kính mờ Acrylic,
   header chuẩn, thanh tiến trình gradient, thẻ thống kê (telemetry cards), và hàng nút tác vụ (action rows).
5. Vector Icons: Bộ icon vector vẽ chuẩn (GPU, VRAM, Fan, Power, Nhiệt kế, Mũi tên mạng, Ping, Sparkle, Calendar, Gear, Refresh, Chevron).
6. Tkinter Form & UI Controls: ModernButton, ModernCard, ModernFormRow, create_styled_menu, Theme Styler cho giao diện cấu hình / Widget Manager.
"""

import io
import json
import math
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
from tkinter import ttk
from typing import Tuple, Dict, Any, Optional, List, Callable
import urllib.request
import zipfile

# =============================================================================
# 1. DESIGN TOKENS (KHOẢNG CÁCH, BO GÓC, KÍCH THƯỚC CHUẨN)
# =============================================================================

# Hệ thống khoảng cách (8pt / 4pt Grid)
SPACE_2XS = 2     # 2px: căn chỉnh vi mô
SPACE_XS  = 4     # 4px: khoảng cách biểu tượng & chữ nhỏ
SPACE_SM  = 8     # 8px: khoảng cách thẻ, padding nhỏ
SPACE_MD  = 12    # 12px: khoảng cách nội dung trung bình
SPACE_LG  = 16    # 16px: padding biên chuẩn (standard page/panel margin)
SPACE_XL  = 20    # 20px: phân tách các nhóm khối
SPACE_2XL = 24    # 24px: khoảng cách giữa các phần lớn
SPACE_3XL = 32    # 32px: khoảng cách tiêu đề lớn

# Bán kính bo góc (Corner Radii)
RADIUS_XS   = 2.0   # Icon nhỏ, viền thanh bar siêu mỏng
RADIUS_SM   = 4.0   # Thanh tiến trình, tag nhỏ
RADIUS_MD   = 8.0   # Thẻ thông tin (telemetry / stat card), nút bấm
RADIUS_LG   = 12.0  # Panel mở rộng (Flyout Window)
RADIUS_XL   = 16.0  # Hộp thoại lớn
RADIUS_PILL = 999.0 # Nút dạng viên thuốc tròn 2 đầu

# Kích thước Taskbar Compact chuẩn (px logic)
CH_TASKBAR    = 40    # Chiều cao chuẩn tuyệt đối cho mọi Widget trên Taskbar (Win 10/11)
CW_STACKED    = 106   # Widget 2 dòng xếp tầng siêu gọn (GPU, Network)
CW_INLINE     = 176   # Widget 1 dòng ngang thanh thoát
CW_HORIZONTAL = 236   # Widget 2 cột ngang đối xứng (Claude Usage)

# Kích thước Flyout Panel chuẩn (px logic)
FW_PANEL      = 328   # Chiều rộng panel mở rộng đồng bộ 100% cho TẤT CẢ widget
FM_SHADOW     = 14    # Lề ngoài mở rộng cho hiệu ứng đổ bóng Gaussian mềm
HEADER_HEIGHT = 60    # Chiều cao thanh tiêu đề chuẩn của Flyout Panel
ACTION_HEIGHT = 38    # Chiều cao mỗi dòng tác vụ ở đáy panel

# Hệ số siêu lấy mẫu (Supersampling)
SS_COMPACT = 3        # Siêu lấy mẫu 3x cho widget taskbar nét từng điểm ảnh
SS_FLYOUT  = 2        # Siêu lấy mẫu 2x cho panel mở rộng mượt mà

# Phông chữ menu ngữ cảnh chuẩn (Context Menu Font)
MENU_FONT = ("Segoe UI", 9)


# =============================================================================
# 2. BẢNG MÀU CHUẨN (COLOR PALETTES & THEMES)
# =============================================================================

# Mã màu HEX cho Giao diện Tkinter Forms / Widget Manager
HEX_BG_DARK       = "#0B0F19"
HEX_BG_SURFACE    = "#111827"
HEX_BG_CARD       = "#1E293B"
HEX_BG_CARD_HOVER = "#243248"
HEX_BG_INPUT      = "#0F172A"
HEX_BORDER        = "#334155"
HEX_BORDER_LIGHT  = "#475569"

HEX_TEXT_MAIN     = "#F8FAFC"
HEX_TEXT_MUTED    = "#94A3B8"
HEX_TEXT_DIM      = "#64748B"

HEX_CYAN          = "#38BDF8"
HEX_BLUE          = "#3B82F6"
HEX_GREEN         = "#10B981"
HEX_EMERALD       = "#10B981"
HEX_YELLOW        = "#F59E0B"
HEX_RED           = "#EF4444"

# Tuple RGB cho Vẽ Đồ Hoạ PIL (Layered Window)
# Trạng thái hệ thống (Status Colors)
COLOR_OK     = (52, 214, 166)    # Emerald / Mint Green (<70% hoặc ping tốt)
COLOR_WARN   = (245, 184, 46)    # Amber / Vàng ấm (70% - 85% hoặc ping trung bình)
COLOR_DANGER = (255, 90, 106)    # Coral Red (>=85% hoặc cảnh báo tải cao)

# Màu Brand & Accent
ACCENT_CYAN  = (56, 189, 248)    # Sky Cyan
ACCENT_BLUE  = (59, 130, 246)    # Royal Blue
ACCENT_MINT  = (52, 224, 170)    # Soft Mint
ACCENT_SPARK = (96, 165, 250)    # Sparkle Blue (Claude)
COLOR_WHITE  = (255, 255, 255)

# Bảng màu Dark Fluent Theme (Mặc định cho Panel Kính Mờ Acrylic)
THEME_DARK = {
    "is_dark": True,
    "bg_panel": (17, 24, 39),
    "panel_alpha": 246,
    "border_panel": (148, 163, 184),
    "border_alpha": 50,
    "card_bg": (28, 36, 52),
    "card_alpha": 180,
    "card_border": (71, 85, 105),
    "card_border_alpha": 100,
    "text_main": (248, 250, 252),
    "text_muted": (156, 163, 175),
    "text_subtle": (100, 116, 139),
    "track": (255, 255, 255),
    "track_alpha": 30,
    "divider": (255, 255, 255),
    "divider_alpha": 22,
    "hover_bg": (255, 255, 255, 24),
    "shadow_fill": 130,
}

# Bảng màu Light Fluent Theme (Cho Taskbar Sáng hoặc Nền Tương Phản)
THEME_LIGHT = {
    "is_dark": False,
    "bg_panel": (248, 250, 252),
    "panel_alpha": 252,
    "border_panel": (203, 213, 225),
    "border_alpha": 180,
    "card_bg": (241, 245, 249),
    "card_alpha": 220,
    "card_border": (203, 213, 225),
    "card_border_alpha": 160,
    "text_main": (15, 23, 42),
    "text_muted": (71, 85, 105),
    "text_subtle": (148, 163, 184),
    "track": (203, 213, 225),
    "track_alpha": 160,
    "divider": (148, 163, 184),
    "divider_alpha": 60,
    "hover_bg": (0, 0, 0, 18),
    "shadow_fill": 80,
}


def get_level(percent: Optional[float], warn_at: float = 70.0, danger_at: float = 85.0) -> str:
    """Trả về trạng thái 'ok', 'warn', 'danger' dựa trên phần trăm."""
    if percent is None:
        return "none"
    if percent >= danger_at:
        return "danger"
    if percent >= warn_at:
        return "warn"
    return "ok"


def get_level_color(level: str, default_color: Tuple[int, int, int] = COLOR_OK) -> Tuple[int, int, int]:
    """Trả về màu RGB tương ứng với mức độ tải."""
    if level == "danger":
        return COLOR_DANGER
    if level == "warn":
        return COLOR_WARN
    if level == "ok":
        return COLOR_OK
    return default_color


def get_bar_gradient(level: str, default_grad: Tuple[Tuple[int, int, int], Tuple[int, int, int]]) -> Tuple[Tuple[int, int, int], Tuple[int, int, int]]:
    """Trả về màu gradient cho thanh bar tuỳ theo mức tải."""
    if level == "danger":
        return (COLOR_DANGER, COLOR_DANGER)
    if level == "warn":
        return (COLOR_WARN, COLOR_WARN)
    return default_grad


# =============================================================================
# 3. TYPOGRAPHY SYSTEM (HỆ THỐNG PHÔNG CHỮ & KÍCH THƯỚC)
# =============================================================================

# Thang kích thước font chuẩn (Logic px, sẽ nhân với scale * ss khi tải)
FONT_SCALE = {
    "panel_title": 13.0,     # Tiêu đề chính Flyout Panel (Semibold, vừa vặn không lấn át)
    "panel_sub": 9.5,        # Phụ đề card / phiên / driver (Regular, mờ dịu)
    "block_title": 11.0,     # Tiêu đề từng nhóm / thông số lớn (Màu text_muted, không lấn át số)
    "metric_hero": 23.0,     # CHỈ SỐ QUAN TRỌNG: Phần trăm / Dung lượng cực lớn (Semibold nổi bật)
    "metric_unit": 10.5,     # Đơn vị / Trạng thái bên cạnh số to (Regular, text_muted)
    "metric_detail": 9.5,    # Dòng ghi chú xung nhịp / thời gian reset (Regular, text_subtle)
    "card_title": 9.0,       # Tiêu đề thẻ con (Semibold, text_muted)
    "card_val": 14.5,        # Giá trị thẻ con nhiệt độ / điện năng (Semibold to rõ)
    "card_sub": 8.8,         # Ghi chú thẻ con (Regular, text_subtle)
    "net_speed_val": 17.5,   # CHỈ SỐ QUAN TRỌNG MẠNG: Tốc độ Tải xuống / Tải lên (Hero Metric to rõ)
    "action": 11.2,          # Chữ hàng nút tác vụ đáy panel (Regular, text_muted không tranh chấp)
    "taskbar_val": 12.5,     # Chữ số widget taskbar (Semibold, rõ ràng)
    "taskbar_lbl": 8.8,      # Nhãn widget taskbar (Regular, mờ dịu)
    "taskbar_sub": 9.0,      # Chữ phụ widget taskbar (Regular)
}

_FONT_CACHE: Dict[Tuple[str, int], Any] = {}


def load_font(px: float, weight: str = "regular"):
    """Nạp font chuẩn Segoe UI từ Windows với bộ đệm (cache) tự động."""
    from PIL import ImageFont
    key_size = max(1, round(px))
    cache_key = (weight, key_size)
    if cache_key in _FONT_CACHE:
        return _FONT_CACHE[cache_key]

    family_map = {
        "bold": ("segoeuib.ttf", "arialbd.ttf", "seguisb.ttf", "DejaVuSans-Bold.ttf"),
        "semibold": ("seguisb.ttf", "segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"),
        "regular": ("segoeui.ttf", "arial.ttf", "DejaVuSans.ttf")
    }
    candidates = family_map.get(weight, family_map["regular"])

    font_obj = None
    for fname in candidates:
        try:
            font_obj = ImageFont.truetype(fname, key_size)
            break
        except Exception:
            continue

    if font_obj is None:
        font_obj = ImageFont.load_default()

    _FONT_CACHE[cache_key] = font_obj
    return font_obj


# =============================================================================
# 4. BASE PAINTER (ĐỘNG CƠ VẼ ĐỒ HOẠ PIL SUPERSAMPLING)
# =============================================================================

class BasePainter:
    """
    Bộ vẽ đồ họa pixel logic hỗ trợ khử răng cưa siêu mẫu (Supersampling).
    Mọi toạ độ đầu vào tính bằng pixel logic (DPI 100%), tự động scale mượt mà.
    """
    def __init__(self, w: float, h: float, scale: float = 1.0, ss: int = 2, margin: float = 0.0):
        from PIL import Image
        self.scale = scale
        self.ss = ss
        self.dx = margin
        self.u = scale * ss
        self.w_logic = w
        self.h_logic = h
        self.W = round((w + 2 * margin) * self.u)
        self.H = round((h + 2 * margin) * self.u)
        self.out_size = (round((w + 2 * margin) * scale), round((h + 2 * margin) * scale))
        self.out = self.out_size
        self.img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))

    def _bbox(self, x0: float, y0: float, x1: float, y1: float, pad: int = 2):
        u, d = self.u, self.dx
        return (max(0, math.floor((x0 + d) * u) - pad),
                max(0, math.floor((y0 + d) * u) - pad),
                min(self.W, math.ceil((x1 + d) * u) + pad),
                min(self.H, math.ceil((y1 + d) * u) + pad))

    def shape(self, bbox, draw_fn: Callable, color: Tuple[int, int, int], alpha: int = 255, gradient=None):
        """Vẽ hình tuỳ biến qua mặt nạ Alpha đảm bảo viền mềm không ám đen."""
        from PIL import Image, ImageDraw
        x0, y0, x1, y1 = self._bbox(*bbox)
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            return

        u, d0 = self.u, self.dx
        mask = Image.new("L", (w, h), 0)
        draw_fn(ImageDraw.Draw(mask), lambda x, y: ((x + d0) * u - x0, (y + d0) * u - y0))

        if alpha < 255:
            mask = mask.point(lambda v: (v * alpha) // 255)

        if gradient:
            c1, c2 = gradient
            g = Image.new("RGB", (w, 1))
            for i in range(w):
                t = i / max(1, w - 1)
                g.putpixel((i, 0), tuple(round(c1[k] + (c2[k] - c1[k]) * t) for k in range(3)))
            layer = g.resize((w, h)).convert("RGBA")
        else:
            layer = Image.new("RGBA", (w, h), tuple(color) + (255,))

        layer.putalpha(mask)
        region = self.img.crop((x0, y0, x1, y1))
        self.img.paste(Image.alpha_composite(region, layer), (x0, y0))

    def rrect(self, x0: float, y0: float, x1: float, y1: float, r: float,
              color: Tuple[int, int, int], alpha: int = 255, gradient=None):
        """Vẽ hình chữ nhật bo góc với bán kính r."""
        u = self.u
        self.shape((x0, y0, x1, y1),
                   lambda d, T: d.rounded_rectangle([T(x0, y0), T(x1, y1)], radius=r * u, fill=255),
                   color, alpha, gradient)

    def ring(self, x0: float, y0: float, x1: float, y1: float, r: float,
             color: Tuple[int, int, int], width: float = 1.0, alpha: int = 255):
        """Vẽ viền hình chữ nhật bo góc."""
        u = self.u
        self.shape((x0, y0, x1, y1),
                   lambda d, T: d.rounded_rectangle([T(x0, y0), T(x1, y1)], radius=r * u,
                                                   outline=255, width=max(1, round(width * u))),
                   color, alpha)

    def line(self, pts: List[Tuple[float, float]], color: Tuple[int, int, int], width: float = 1.0, alpha: int = 255):
        """Vẽ đoạn thẳng hoặc đường gấp khúc mềm."""
        u = self.u
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.shape((min(xs) - width, min(ys) - width, max(xs) + width, max(ys) + width),
                   lambda d, T: d.line([T(*p) for p in pts], fill=255,
                                       width=max(1, round(width * u)), joint="curve"),
                   color, alpha)

    def polygon(self, pts: List[Tuple[float, float]], color: Tuple[int, int, int], alpha: int = 255):
        """Vẽ đa giác đặc."""
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.shape((min(xs), min(ys), max(xs), max(ys)),
                   lambda d, T: d.polygon([T(*p) for p in pts], fill=255), color, alpha)

    def text(self, x: float, y: float, s: str, font, color: Tuple[int, int, int],
             alpha: int = 255, anchor: str = "ls"):
        """Vẽ văn bản độ nét cao với căn lề chính xác."""
        from PIL import Image, ImageDraw
        u, d0 = self.u, self.dx
        px, py = (x + d0) * u, (y + d0) * u
        l, t, r, b = font.getbbox(s, anchor=anchor)
        x0, y0 = max(0, math.floor(px + l) - 2), max(0, math.floor(py + t) - 2)
        x1, y1 = min(self.W, math.ceil(px + r) + 2), min(self.H, math.ceil(py + b) + 2)
        if x1 <= x0 or y1 <= y0:
            return

        mask = Image.new("L", (x1 - x0, y1 - y0), 0)
        ImageDraw.Draw(mask).text((px - x0, py - y0), s, font=font, fill=255, anchor=anchor)
        if alpha < 255:
            mask = mask.point(lambda v: (v * alpha) // 255)

        layer = Image.new("RGBA", mask.size, tuple(color) + (255,))
        layer.putalpha(mask)
        self.img.paste(Image.alpha_composite(self.img.crop((x0, y0, x1, y1)), layer), (x0, y0))

    def text_width(self, s: str, font) -> float:
        """Đo chiều rộng logic của chuỗi văn bản."""
        return font.getlength(s) / self.u

    def get_font(self, font_key: str, weight: str = "regular"):
        """Lấy phông chữ theo tỉ lệ thiết kế chuẩn của UI Kit."""
        logic_size = FONT_SCALE.get(font_key, 12.0)
        return load_font(logic_size * self.u, weight)

    # -------------------------------------------------------------------------
    # VECTOR ICONS TIÊU CHUẨN
    # -------------------------------------------------------------------------
    def chevron(self, cx: float, cy: float, color: Tuple[int, int, int], direction: str = "right",
                size: float = 4.5, width: float = 1.4, alpha: int = 255):
        k = size
        if direction == "down":
            pts = [(cx - k, cy - k * 0.5), (cx, cy + k * 0.5), (cx + k, cy - k * 0.5)]
        elif direction == "up":
            pts = [(cx - k, cy + k * 0.5), (cx, cy - k * 0.5), (cx + k, cy + k * 0.5)]
        else:  # right
            pts = [(cx - k * 0.5, cy - k), (cx + k * 0.5, cy), (cx - k * 0.5, cy + k)]
        self.line(pts, color, width, alpha=alpha)

    def dot(self, cx: float, cy: float, r: float, color: Tuple[int, int, int], alpha: int = 255):
        self.shape((cx - r, cy - r, cx + r, cy + r),
                   lambda d, T: d.ellipse([T(cx - r, cy - r), T(cx + r, cy + r)], fill=255),
                   color, alpha)

    def arrow_down(self, cx: float, cy: float, size: float, color: Tuple[int, int, int], width: float = 1.5):
        k = size
        w = max(1.0, width)
        self.line([(cx, cy - k * 0.9), (cx, cy + k * 0.5)], color, w)
        pts = [(cx - k * 0.7, cy + k * 0.2), (cx, cy + k * 0.95), (cx + k * 0.7, cy + k * 0.2)]
        self.polygon(pts, color)

    def arrow_up(self, cx: float, cy: float, size: float, color: Tuple[int, int, int], width: float = 1.5):
        k = size
        w = max(1.0, width)
        self.line([(cx, cy + k * 0.9), (cx, cy - k * 0.5)], color, w)
        pts = [(cx - k * 0.7, cy - k * 0.2), (cx, cy - k * 0.95), (cx + k * 0.7, cy - k * 0.2)]
        self.polygon(pts, color)

    def sparkle_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int]):
        """Biểu tượng ngôi sao 4 cánh Sparkle (Claude AI)."""
        pts = []
        for i in range(8):
            r = s if (i % 2 == 0) else (s * 0.32)
            a = math.radians(i * 45)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        self.polygon(pts, color)

    def sparkle(self, cx: float, cy: float, r: float, color: Tuple[int, int, int]):
        """Ngôi sao 4 cánh lõm (tương thích cho compact và flyout)."""
        pts = []
        for i in range(8):
            a = math.radians(i * 45 - 90)
            rr = r if i % 2 == 0 else r * 0.30
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
        self.polygon(pts, color)

    def calendar_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int]):
        """Biểu tượng lịch tuần."""
        w, h = s * 0.9, s * 0.8
        x0, y0 = cx - w / 2, cy - h / 2
        self.rrect(x0, y0, x0 + w, y0 + h, 1.8, color, alpha=180)
        self.rrect(x0 + 1, y0 + h * 0.35, x0 + w - 1, y0 + h - 1, 1.2, (15, 23, 42), alpha=220)
        self.line([(cx - w * 0.25, y0 - 1.5), (cx - w * 0.25, y0 + 1)], color, 1.2)
        self.line([(cx + w * 0.25, y0 - 1.5), (cx + w * 0.25, y0 + 1)], color, 1.2)

    def calendar(self, x: float, y: float, s: float, color: Tuple[int, int, int]):
        """Biểu tượng lịch tuần dạng toạ độ x, y góc trái trên."""
        lw = s * 0.09
        top = y + s * 0.16
        self.ring(x, top, x + s, y + s, s * 0.22, color, lw)
        hy = top + s * 0.27
        self.line([(x, hy), (x + s, hy)], color, lw)
        for fx in (0.28, 0.66):
            rx = x + s * fx
            self.rrect(rx - lw / 2, y, rx + lw / 2, top + s * 0.14, lw / 2, color)
        cell = s * 0.12
        for r in range(3):
            for c in range(3):
                cx0, cy0 = x + s * (0.17 + 0.27 * c), hy + s * (0.13 + 0.20 * r)
                self.rrect(cx0, cy0, cx0 + cell, cy0 + cell, 0, color)

    def gpu_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int]):
        """Chip GPU với chân pins xung quanh và lõi xử lý bên trong."""
        half = s * 0.42
        self.rrect(cx - half, cy - half, cx + half, cy + half, 2.0, color, alpha=220)
        pin_len = s * 0.16
        pin_w = max(1.0, s * 0.10)
        for offset in (-half * 0.5, 0, half * 0.5):
            self.line([(cx + offset, cy - half - pin_len), (cx + offset, cy - half)], color, pin_w, alpha=180)
            self.line([(cx + offset, cy + half), (cx + offset, cy + half + pin_len)], color, pin_w, alpha=180)
            self.line([(cx - half - pin_len, cy + offset), (cx - half, cy + offset)], color, pin_w, alpha=180)
            self.line([(cx + half, cy + offset), (cx + half + pin_len, cy + offset)], color, pin_w, alpha=180)
        inner = half * 0.45
        self.rrect(cx - inner, cy - inner, cx + inner, cy + inner, 1.0, (15, 23, 42), alpha=230)

    def vram_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int]):
        """Biểu tượng thanh nhớ VRAM."""
        w, h = s * 0.85, s * 0.55
        self.rrect(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2, 1.5, color, alpha=220)
        cw, ch = w * 0.22, h * 0.60
        for fx in (-0.27, 0.0, 0.27):
            bx = cx + w * fx
            self.rrect(bx - cw / 2, cy - ch / 2, bx + cw / 2, cy + ch / 2, 0.8, (15, 23, 42), alpha=220)

    def temp_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int]):
        """Nhiệt kế đo nhiệt độ phần cứng."""
        r = s * 0.22
        top_y = cy - s * 0.40
        bot_y = cy + s * 0.20
        self.rrect(cx - r * 0.6, top_y, cx + r * 0.6, bot_y, r * 0.6, color, alpha=230)
        self.rrect(cx - r, bot_y - r * 0.5, cx + r, bot_y + r * 1.5, r, color, alpha=255)

    def power_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int]):
        """Tia chớp điện năng (Watts)."""
        k = s * 0.5
        pts = [
            (cx - k * 0.2, cy - k),
            (cx + k * 0.6, cy - k * 0.1),
            (cx + k * 0.1, cy - k * 0.1),
            (cx + k * 0.4, cy + k),
            (cx - k * 0.6, cy + k * 0.1),
            (cx - k * 0.1, cy + k * 0.1),
        ]
        self.polygon(pts, color)

    def network_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int]):
        """Biểu tượng quả cầu mạng / kết nối internet sắc nét."""
        r = s * 0.44
        u = self.u
        # Vòng tròn ngoài
        def draw_circle(d, T):
            (x0, y0), (x1, y1) = T(cx - r, cy - r), T(cx + r, cy + r)
            d.ellipse([x0, y0, x1, y1], outline=255, width=max(1, round(1.2 * u)))
        self.shape((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), draw_circle, color)
        # Đường xích đạo ngang
        self.line([(cx - r + 1, cy), (cx + r - 1, cy)], color, 1.1, alpha=200)
        # Đường kinh tuyến đứng cong
        def draw_meridian(d, T):
            (x0, y0), (x1, y1) = T(cx - r * 0.45, cy - r), T(cx + r * 0.45, cy + r)
            d.ellipse([x0, y0, x1, y1], outline=255, width=max(1, round(1.1 * u)))
        self.shape((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), draw_meridian, color, alpha=200)

    def swap_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int], width: float = 1.4):
        """Biểu tượng chuyển đổi 2 chiều (đổi đơn vị Bytes ↔ Bits) vector thay cho ký tự unicode bị lỗi."""
        w = s * 0.85
        h = s * 0.50
        y_top = cy - h * 0.45
        y_bot = cy + h * 0.45
        # Mũi tên trên chỉ sang phải ->
        self.line([(cx - w * 0.45, y_top), (cx + w * 0.30, y_top)], color, width)
        pts_r = [
            (cx + w * 0.15, y_top - s * 0.20),
            (cx + w * 0.48, y_top),
            (cx + w * 0.15, y_top + s * 0.20)
        ]
        self.polygon(pts_r, color)
        # Mũi tên dưới chỉ sang trái <-
        self.line([(cx + w * 0.45, y_bot), (cx - w * 0.30, y_bot)], color, width)
        pts_l = [
            (cx - w * 0.15, y_bot - s * 0.20),
            (cx - w * 0.48, y_bot),
            (cx - w * 0.15, y_bot + s * 0.20)
        ]
        self.polygon(pts_l, color)

    def fan_icon(self, cx: float, cy: float, r: float, color: Tuple[int, int, int]):
        """Quạt tản nhiệt 3 cánh."""
        self.rrect(cx - r * 0.25, cy - r * 0.25, cx + r * 0.25, cy + r * 0.25, r * 0.25, color)
        for i in range(3):
            ang = math.radians(i * 120)
            ax = cx + math.cos(ang) * (r * 0.85)
            ay = cy + math.sin(ang) * (r * 0.85)
            ang_perp = ang + math.radians(45)
            bx = cx + math.cos(ang_perp) * (r * 0.45)
            by = cy + math.sin(ang_perp) * (r * 0.45)
            self.polygon([(cx, cy), (bx, by), (ax, ay)], color, alpha=210)

    def refresh_icon(self, cx: float, cy: float, r: float, color: Tuple[int, int, int], width: float = 1.5):
        """Mũi tên tròn Làm mới (Refresh)."""
        u = self.u
        def draw(d, T):
            a, b = T(cx - r, cy - r), T(cx + r, cy + r)
            d.arc([a, b], 25, 305, fill=255, width=max(1, round(width * u)))
        self.shape((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), draw, color)
        ang = math.radians(305)
        px, py = cx + r * math.cos(ang), cy + r * math.sin(ang)
        tx, ty = -math.sin(ang), math.cos(ang)
        nx, ny = -ty, tx
        s = r * 0.62
        self.polygon([(px + tx * s * 1.1, py + ty * s * 1.1),
                      (px + nx * s * 0.8, py + ny * s * 0.8),
                      (px - nx * s * 0.8, py - ny * s * 0.8)], color)

    def gear_icon(self, cx: float, cy: float, r: float, color: Tuple[int, int, int]):
        """Bánh răng cài đặt (Settings)."""
        u = self.u
        def draw(d, T):
            (x0, y0), (x1, y1) = T(cx - r * 0.60, cy - r * 0.60), T(cx + r * 0.60, cy + r * 0.60)
            d.ellipse([x0, y0, x1, y1], fill=255)
            for i in range(8):
                a = math.radians(i * 45)
                ca, sa = math.cos(a), math.sin(a)
                w = r * 0.14
                pts = [(cx + ca * r * 0.5 - sa * w, cy + sa * r * 0.5 + ca * w),
                       (cx + ca * r - sa * w * 0.8, cy + sa * r + ca * w * 0.8),
                       (cx + ca * r + sa * w * 0.8, cy + sa * r - ca * w * 0.8),
                       (cx + ca * r * 0.5 + sa * w, cy + sa * r * 0.5 - ca * w)]
                d.polygon([T(*p) for p in pts], fill=255)
            (ix0, iy0), (ix1, iy1) = T(cx - r * 0.28, cy - r * 0.28), T(cx + r * 0.28, cy + r * 0.28)
            d.ellipse([ix0, iy0, ix1, iy1], fill=0)
        self.shape((cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2), draw, color)

    def gear(self, cx: float, cy: float, r: float, color: Tuple[int, int, int]):
        """Bí danh (alias) tương thích cho gear_icon."""
        return self.gear_icon(cx, cy, r, color)

    def download_icon(self, cx: float, cy: float, s: float, color: Tuple[int, int, int], width: float = 1.4):
        """Biểu tượng tải về / cập nhật (Mũi tên chỉ xuống khay)."""
        w = max(1.0, width)
        self.line([(cx, cy - s * 0.45), (cx, cy + s * 0.15)], color, w)
        k = s * 0.35
        pts = [(cx - k * 0.8, cy), (cx, cy + s * 0.22), (cx + k * 0.8, cy)]
        self.polygon(pts, color)
        tray_pts = [
            (cx - s * 0.42, cy + s * 0.10),
            (cx - s * 0.42, cy + s * 0.42),
            (cx + s * 0.42, cy + s * 0.42),
            (cx + s * 0.42, cy + s * 0.10)
        ]
        self.line(tray_pts, color, w)

    def finish(self):
        """Hoàn tất bản vẽ và thu nhỏ siêu mẫu (LANCZOS) để đạt độ nét tối đa."""
        from PIL import Image
        return self.img.resize(self.out_size, Image.LANCZOS)


# =============================================================================
# 5. CÁC HÀM DỰNG GIAO DIỆN CHUẨN (STANDARD UI COMPONENT RENDERERS)
# =============================================================================

import tempfile
import os

ACTIVE_FLYOUT_FILE = os.path.join(tempfile.gettempdir(), "agy_active_flyout.txt")

def notify_flyout_opened(widget_id: str):
    """Ghi nhận widget này đang mở Flyout để các widget khác tự động đóng (tránh chồng chéo)."""
    try:
        with open(ACTIVE_FLYOUT_FILE, "w", encoding="utf-8") as f:
            f.write(widget_id)
    except Exception:
        pass

def notify_flyout_closed(widget_id: str):
    """Xoá trạng thái khi Flyout của widget này đóng."""
    try:
        if os.path.exists(ACTIVE_FLYOUT_FILE):
            with open(ACTIVE_FLYOUT_FILE, "r", encoding="utf-8") as f:
                cur = f.read().strip()
            if cur == widget_id:
                os.remove(ACTIVE_FLYOUT_FILE)
    except Exception:
        pass

def should_close_flyout(widget_id: str) -> bool:
    """Kiểm tra xem có widget khác vừa mở Flyout hay không để đóng ngay lập tức."""
    try:
        if os.path.exists(ACTIVE_FLYOUT_FILE):
            with open(ACTIVE_FLYOUT_FILE, "r", encoding="utf-8") as f:
                cur = f.read().strip()
            if cur and cur != widget_id:
                return True
    except Exception:
        pass
    return False


def draw_panel_shell(p: BasePainter, theme: Dict[str, Any], fw: float = FW_PANEL, fh: float = 360.0):
    """Vẽ vỏ ngoài panel kính mờ Acrylic với bóng đổ Gaussian mềm phía sau."""
    from PIL import Image, ImageFilter, ImageDraw
    u = p.u
    fm = p.dx

    # 1. Đổ bóng Gaussian
    sh = Image.new("L", (p.W, p.H), 0)
    ImageDraw.Draw(sh).rounded_rectangle(
        [fm * u, (fm + 4) * u, (fm + fw) * u, (fm + fh + 4) * u],
        radius=RADIUS_LG * u, fill=theme.get("shadow_fill", 130))
    sh = sh.filter(ImageFilter.GaussianBlur(8 * u))
    shadow = Image.new("RGBA", (p.W, p.H), (0, 0, 0, 255))
    shadow.putalpha(sh)
    p.img = Image.alpha_composite(p.img, shadow)

    # 2. Thân panel chính
    bg_col = theme.get("bg_panel") or theme.get("panel_fill", (17, 24, 39))
    bg_alpha = theme.get("panel_alpha", 246)
    border_col = theme.get("border_panel") or theme.get("panel_border", (148, 163, 184))
    border_alpha = theme.get("border_alpha") or theme.get("panel_border_a", 50)
    p.rrect(0, 0, fw, fh, RADIUS_LG, bg_col, alpha=bg_alpha)
    p.ring(0.5, 0.5, fw - 0.5, fh - 0.5, RADIUS_LG, border_col, 1.0, alpha=border_alpha)


def draw_panel_header(p: BasePainter, theme: Dict[str, Any],
                      icon_fn: Callable[[float, float], None],
                      title: str, subtitle: str,
                      fw: float = FW_PANEL,
                      right_badge_fn: Optional[Callable[[BasePainter, float, float], None]] = None) -> float:
    """
    Vẽ thanh Header chuẩn cao 60px:
    - Biểu tượng bên trái tại (x=30, y=30)
    - Tiêu đề chính + Subtitle
    - Nút / Badge bên phải (mặc định là chevron mở trang)
    - Đường gạch phân cách ở y=60
    """
    f_title = p.get_font("panel_title", "semibold")
    f_sub = p.get_font("panel_sub", "regular")

    icon_fn(30, 30)

    max_title_w = fw - 100
    display_title = title
    if p.text_width(display_title, f_title) > max_title_w:
        while len(display_title) > 4 and p.text_width(display_title + "…", f_title) > max_title_w:
            display_title = display_title[:-1]
        display_title = display_title + "…"

    p.text(54, 27, display_title, f_title, theme["text_main"])
    p.text(54, 46, subtitle, f_sub, theme["text_muted"])

    if right_badge_fn:
        right_badge_fn(p, fw, 30)
    else:
        p.chevron(fw - 22, 30, theme["text_muted"], direction="right", size=5, width=1.5)

    p.line([(0, HEADER_HEIGHT), (fw, HEADER_HEIGHT)], theme["divider"], 1.0, alpha=theme["divider_alpha"])
    return HEADER_HEIGHT


def draw_metric_block(p: BasePainter, theme: Dict[str, Any],
                      top_y: float,
                      title: str,
                      big_val_str: str,
                      unit_or_status: str,
                      percent: Optional[float],
                      gradient: Tuple[Tuple[int, int, int], Tuple[int, int, int]],
                      detail_str: str,
                      val_color: Optional[Tuple[int, int, int]] = None,
                      fw: float = FW_PANEL,
                      pad: float = SPACE_LG) -> float:
    """
    Vẽ khối đo tiến trình lớn chuẩn (GPU Load, VRAM, Claude Session, Claude Week, v.v.):
    - Tiêu đề khối (Semibold)
    - Giá trị lớn (Hero Value) + Đơn vị / Trạng thái
    - Thanh tiến trình bo góc mượt mà
    - Dòng mô tả chi tiết dưới thanh tiến trình
    - Đường gạch đáy phân cách
    """
    f_blk = p.get_font("block_title", "semibold")
    f_big = p.get_font("metric_hero", "semibold")
    f_unit = p.get_font("metric_unit", "regular")
    f_detail = p.get_font("metric_detail", "regular")

    # 1. Tiêu đề khối (màu dịu text_muted để không lấn át số)
    p.text(pad, top_y + 22, title, f_blk, theme.get("text_muted", (148, 163, 184)))

    # 2. Giá trị lớn (Chỉ số quan trọng: size to, màu nổi bật)
    col = val_color or theme["text_main"]
    p.text(pad, top_y + 50, big_val_str, f_big, col)

    val_w = p.text_width(big_val_str, f_big)
    if unit_or_status:
        p.text(pad + val_w + 8, top_y + 49, unit_or_status, f_unit, theme.get("text_muted", (148, 163, 184)))

    # 3. Thanh tiến trình
    bar_w = fw - 2 * pad
    p.rrect(pad, top_y + 59, pad + bar_w, top_y + 65, RADIUS_SM, theme["track"], alpha=theme["track_alpha"])
    if percent is not None and percent > 0:
        c1, c2 = gradient
        fill_w = max(6.0, bar_w * min(1.0, percent / 100.0))
        p.rrect(pad, top_y + 59, pad + fill_w, top_y + 65, RADIUS_SM, c1, gradient=(c1, c2))

    # 4. Dòng thông tin phụ (màu dịu nhẹ)
    p.text(pad, top_y + 80, detail_str, f_detail, theme.get("text_subtle", (100, 116, 139)))

    bot_y = top_y + 90
    p.line([(0, bot_y), (fw, bot_y)], theme["divider"], 1.0, alpha=theme["divider_alpha"])
    return bot_y


def draw_stat_cards(p: BasePainter, theme: Dict[str, Any],
                    top_y: float,
                    cards: List[Dict[str, Any]],
                    card_h: float = 68.0,
                    fw: float = FW_PANEL,
                    pad: float = SPACE_LG) -> float:
    """
    Vẽ lưới thẻ thống kê đồng bộ (2 cột hoặc 3 cột):
    cards: list các dict {
        "title": str,
        "value": str,
        "val_color": tuple(r,g,b),
        "icon_fn": callable(cx, cy, color),
        "sub": Optional[str]
    }
    """
    f_val = p.get_font("card_val", "semibold")
    f_lbl = p.get_font("card_title", "semibold")
    f_sub = p.get_font("card_sub", "regular")

    n = len(cards)
    gap = SPACE_SM
    card_w = (fw - 2 * pad - (n - 1) * gap) / n

    for i, c in enumerate(cards):
        cx0 = pad + i * (card_w + gap)
        cx1 = cx0 + card_w
        cy0 = top_y
        cy1 = top_y + card_h

        # Thân thẻ
        p.rrect(cx0, cy0, cx1, cy1, RADIUS_MD, theme["card_bg"], alpha=theme["card_alpha"])
        p.ring(cx0, cy0, cx1, cy1, RADIUS_MD, theme["card_border"], 1.0, alpha=theme["card_border_alpha"])

        val_col = c.get("val_color", theme["text_main"])
        if "icon_fn" in c and c["icon_fn"]:
            c["icon_fn"](cx0 + 16, cy0 + 20, val_col)
            p.text(cx0 + 30, cy0 + 25, c["value"], f_val, val_col)
        else:
            p.text(cx0 + 14, cy0 + 25, c["value"], f_val, val_col)

        p.text(cx0 + 14, cy0 + card_h - 17, c["title"], f_lbl, theme["text_muted"])

        if c.get("sub"):
            p.text(cx0 + 14, cy0 + card_h - 6, c["sub"], f_sub, theme["text_subtle"])

    bot_y = top_y + card_h + 8
    p.line([(0, bot_y), (fw, bot_y)], theme["divider"], 1.0, alpha=theme["divider_alpha"])
    return bot_y


def draw_action_rows(p: BasePainter, theme: Dict[str, Any],
                     start_y: float,
                     actions: List[Dict[str, Any]],
                     fw: float = FW_PANEL,
                     pad: float = SPACE_LG) -> Dict[str, Tuple[int, int, int, int]]:
    """
    Vẽ các hàng nút tác vụ ở đáy Flyout panel (Làm mới, Đổi đơn vị, Cài đặt):
    actions: list các dict {
        "key": str,
        "label": str,
        "icon_fn": callable(cx, cy, color)
    }
    Trả về dict các bounding boxes (logic px) để xử lý click / hover.
    """
    f_act = p.get_font("action", "regular")
    rects = {}
    curr_y = start_y
    action_col = theme.get("text_muted") or (156, 163, 175)

    for act in actions:
        key = act["key"]
        h = ACTION_HEIGHT
        mid_y = curr_y + h / 2.0
        act["icon_fn"](pad + 12, mid_y, action_col)
        p.text(pad + 32, mid_y + 4.5, act["label"], f_act, action_col)

        rects[key] = (0, curr_y, fw, curr_y + h)
        curr_y += h

    return rects


def apply_hover_highlight(img, rects: Dict[str, Tuple[int, int, int, int]],
                          hover_key: Optional[str], scale: float = 1.0,
                          is_dark: bool = True):
    """Vẽ lớp phủ bán trong suốt bo góc khi người dùng rê chuột lên hàng tác vụ."""
    from PIL import Image, ImageDraw
    if not hover_key or hover_key not in rects:
        return img

    x0, y0, x1, y1 = rects[hover_key]
    inset_x = round(SPACE_SM * scale)
    inset_y = round(SPACE_2XS * scale)
    r = round(7.0 * scale)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    fill_color = (255, 255, 255, 24) if is_dark else (0, 0, 0, 18)

    ImageDraw.Draw(overlay).rounded_rectangle(
        [x0 + inset_x, y0 + inset_y, x1 - inset_x, y1 - inset_y],
        radius=r, fill=fill_color
    )
    return Image.alpha_composite(img, overlay)


# =============================================================================
# 6. TKINTER FORMS & MODERN CONTROLS (CHO WIDGET MANAGER & CÀI ĐẶT)
# =============================================================================

def create_styled_menu(parent) -> tk.Menu:
    """Tạo Menu ngữ cảnh Tkinter với phông chữ chuẩn đồng bộ MENU_FONT = ('Segoe UI', 9)."""
    return tk.Menu(parent, tearoff=0, font=MENU_FONT)


class ModernButton(tk.Canvas):
    """
    Nút bấm Tkinter bo góc chuẩn UI Kit với hiệu ứng hover mượt mà và hỗ trợ icon text.
    """
    def __init__(self, parent, text: str, command: Optional[Callable] = None,
                 bg: str = HEX_CYAN, fg: str = "#0F172A",
                 hover_bg: Optional[str] = None,
                 width: int = 120, height: int = 34, radius: int = 8,
                 font_spec: Tuple = ("Segoe UI", 9, "bold"), **kwargs):
        super().__init__(parent, width=width, height=height, bg=parent["bg"],
                         highlightthickness=0, bd=0, cursor="hand2", **kwargs)
        self.text = text
        self.command = command
        self.base_bg = bg
        self.hover_bg = hover_bg or self._lighten(bg)
        self.current_bg = self.base_bg
        self.fg = fg
        self.width = width
        self.height = height
        self.radius = radius
        self.font_spec = font_spec
        self.is_disabled = False

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        self.draw()

    def _lighten(self, hex_color: str) -> str:
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = min(255, int(r * 1.15))
        g = min(255, int(g * 1.15))
        b = min(255, int(b * 1.15))
        return f"#{r:02x}{g:02x}{b:02x}"

    def set_text(self, text: str):
        self.text = text
        self.draw()

    def set_state(self, enabled: bool):
        self.is_disabled = not enabled
        self.config(cursor="hand2" if enabled else "arrow")
        self.draw()

    def set_bg(self, bg: str, hover_bg: Optional[str] = None):
        self.base_bg = bg
        self.hover_bg = hover_bg or self._lighten(bg)
        self.current_bg = self.base_bg
        self.draw()

    def set_fg(self, fg: str):
        self.fg = fg
        self.draw()

    def draw(self):
        self.delete("all")
        r = self.radius
        w, h = self.width, self.height
        bg = "#475569" if self.is_disabled else self.current_bg
        fg = "#94A3B8" if self.is_disabled else self.fg

        # 4 góc tròn
        self.create_arc((0, 0, 2*r, 2*r), start=90, extent=90, fill=bg, outline=bg)
        self.create_arc((w - 2*r, 0, w, 2*r), start=0, extent=90, fill=bg, outline=bg)
        self.create_arc((w - 2*r, h - 2*r, w, h), start=270, extent=90, fill=bg, outline=bg)
        self.create_arc((0, h - 2*r, 2*r, h), start=180, extent=90, fill=bg, outline=bg)
        # Các khối thân
        self.create_rectangle((r, 0, w - r, h), fill=bg, outline=bg)
        self.create_rectangle((0, r, w, h - r), fill=bg, outline=bg)
        # Nhãn chữ
        self.create_text((w / 2, h / 2), text=self.text, fill=fg, font=self.font_spec)

    def _on_enter(self, _):
        if not self.is_disabled:
            self.current_bg = self.hover_bg
            self.draw()

    def _on_leave(self, _):
        if not self.is_disabled:
            self.current_bg = self.base_bg
            self.draw()

    def _on_click(self, _):
        if not self.is_disabled and self.command:
            self.command()


class ModernCard(tk.Frame):
    """Khung thẻ chứa thông tin bo góc có đường viền vi tế."""
    def __init__(self, parent, bg: str = HEX_BG_CARD, border_color: str = HEX_BORDER,
                 padx: int = SPACE_LG, pady: int = SPACE_MD, **kwargs):
        super().__init__(parent, bg=border_color, padx=1, pady=1, **kwargs)
        self.inner = tk.Frame(self, bg=bg, padx=padx, pady=pady)
        self.inner.pack(fill=tk.BOTH, expand=True)

    def get_content_frame(self) -> tk.Frame:
        return self.inner


class ModernFormRow(tk.Frame):
    """Dòng nhập liệu chuẩn trong bảng cài đặt: Nhãn bên trái, Điều khiển bên phải."""
    def __init__(self, parent, label_text: str, desc_text: Optional[str] = None,
                 bg: str = HEX_BG_SURFACE, **kwargs):
        super().__init__(parent, bg=bg, pady=SPACE_SM, **kwargs)
        lbl_box = tk.Frame(self, bg=bg)
        lbl_box.pack(side="left", fill="y", anchor="w")

        self.title_lbl = tk.Label(lbl_box, text=label_text, font=("Segoe UI", 9, "bold"),
                                  bg=bg, fg=HEX_TEXT_MAIN)
        self.title_lbl.pack(anchor="w")

        if desc_text:
            self.desc_lbl = tk.Label(lbl_box, text=desc_text, font=("Segoe UI", 8),
                                     bg=bg, fg=HEX_TEXT_MUTED)
            self.desc_lbl.pack(anchor="w", pady=(2, 0))

        self.control_box = tk.Frame(self, bg=bg)
        self.control_box.pack(side="right", fill="y", anchor="e")

    def get_control_box(self) -> tk.Frame:
        return self.control_box


def apply_fluent_ttk_theme(style: ttk.Style):
    """Áp dụng theme Fluent Dark đồng bộ cho toàn bộ ttk widgets (Combobox, Radio, Entry)."""
    try:
        style.theme_use("clam")
    except Exception:
        pass

    # Combobox
    style.configure("TCombobox",
                    fieldbackground=HEX_BG_INPUT,
                    background=HEX_BG_CARD,
                    foreground=HEX_TEXT_MAIN,
                    arrowcolor=HEX_CYAN,
                    bordercolor=HEX_BORDER,
                    darkcolor=HEX_BG_INPUT,
                    lightcolor=HEX_BORDER,
                    padding=6)
    style.map("TCombobox",
              fieldbackground=[("readonly", HEX_BG_INPUT)],
              selectbackground=[("readonly", HEX_BG_CARD_HOVER)],
              selectforeground=[("readonly", HEX_TEXT_MAIN)])

    # Checkbutton
    style.configure("TCheckbutton",
                    background=HEX_BG_SURFACE,
                    foreground=HEX_TEXT_MAIN,
                    font=("Segoe UI", 9))

    # Radiobutton
    style.configure("TRadiobutton",
                    background=HEX_BG_SURFACE,
                    foreground=HEX_TEXT_MAIN,
                    font=("Segoe UI", 9))


# =============================================================================
# 7. CHỨC NĂNG CẬP NHẬT TỪ GITHUB QUA HTTP (HTTP GITHUB UPDATER)
# =============================================================================

import io
import zipfile
import urllib.request
import tempfile
import shutil
import threading
import json


def normalize_github_url(url: str) -> str:
    """Chuẩn hóa đường dẫn repository GitHub thành định dạng https://github.com/owner/repo"""
    if not url:
        return ""
    clean = url.strip()
    if clean.startswith("git@github.com:"):
        clean = "https://github.com/" + clean[len("git@github.com:"):]
    clean = clean.rstrip("/")
    if clean.endswith(".git"):
        clean = clean[:-4]
    return clean


def get_local_version(widget_dir: str) -> str:
    """Đọc phiên bản hiện tại của widget từ file VERSION hoặc widget.json, mặc định '1.0.0'."""
    v_file = os.path.join(widget_dir, "VERSION")
    if os.path.isfile(v_file):
        try:
            with open(v_file, "r", encoding="utf-8") as f:
                v = f.read().strip()
                if v:
                    return v
        except Exception:
            pass
    m_file = os.path.join(widget_dir, "widget.json")
    if os.path.isfile(m_file):
        try:
            with open(m_file, "r", encoding="utf-8-sig") as f:
                v = json.load(f).get("version")
                if v:
                    return str(v).strip()
        except Exception:
            pass
    return "1.0.0"


def parse_version(ver_str: str) -> Tuple[int, ...]:
    """Phân tích chuỗi phiên bản semver (vd '1.2.0', 'v1.1.0') thành tuple số nguyên."""
    if not ver_str:
        return (0, 0, 0)
    clean = re.sub(r'^[vV]', '', str(ver_str).strip())
    parts = []
    for p in clean.split('.'):
        digits = re.findall(r'\d+', p)
        if digits:
            parts.append(int(digits[0]))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts)


def compare_versions(v_local: str, v_remote: str) -> int:
    """
    So sánh 2 chuỗi phiên bản:
     1: remote > local (Có bản cập nhật mới)
     0: remote == local (Đã là bản mới nhất)
    -1: local > remote (Bản trên máy mới hơn bản trên GitHub)
    """
    p_loc = parse_version(v_local)
    p_rem = parse_version(v_remote)
    if p_rem > p_loc:
        return 1
    elif p_rem < p_loc:
        return -1
    return 0


def fetch_remote_info(github_url: str, branch: str = "main") -> Tuple[bool, Optional[str], Optional[dict], str]:
    """
    Kiểm tra thông tin phiên bản trên GitHub qua HTTP (raw.githubusercontent.com):
    Trả về: (thành_công, remote_version, metadata_dict, thông_điệp)
    """
    base_url = normalize_github_url(github_url)
    if "github.com/" not in base_url:
        return False, None, None, "URL không hợp lệ. Vui lòng cung cấp link GitHub (https://github.com/owner/repo)"
    parts = base_url.split("github.com/")[-1].split("/")
    if len(parts) < 2:
        return False, None, None, "Đường dẫn GitHub phải có dạng https://github.com/owner/repo"
    owner, repo = parts[0], parts[1]

    headers = {"User-Agent": "MediaWorkspace-Widget-Updater/1.0"}
    branches = [branch]
    if branch != "main" and "main" not in branches:
        branches.append("main")
    if branch != "master" and "master" not in branches:
        branches.append("master")

    for br in branches:
        # 1. Thử đọc widget.json
        raw_json_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/widget.json"
        try:
            req = urllib.request.Request(raw_json_url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8", errors="replace"))
                    ver = str(data.get("version", "1.0.0")).strip()
                    return True, ver, data, f"Nhánh '{br}'"
        except urllib.error.HTTPError as he:
            if he.code == 404:
                pass
        except Exception:
            pass

        # 2. Thử đọc VERSION
        raw_v_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{br}/VERSION"
        try:
            req = urllib.request.Request(raw_v_url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                if resp.status == 200:
                    ver = resp.read().decode("utf-8", errors="replace").strip()
                    if ver:
                        return True, ver, {"version": ver}, f"Nhánh '{br}'"
        except Exception:
            pass

    return False, None, None, f"Không tìm thấy repository trên GitHub ({owner}/{repo}). Repo có thể là Private hoặc chưa push lên."


# =============================================================================
# 7.1. QUẢN LÝ KIỂM TRA PHIÊN BẢN NGẦM (BACKGROUND UPDATE CHECKER)
# =============================================================================

class UpdateChecker:
    """
    Quản lý kiểm tra phiên bản mới ngầm trên GitHub khi khởi chạy widget:
    - Chạy fetch repo 1 lần không đồng bộ (thread daemon).
    - Lưu trạng thái: checked, has_update, remote_ver, local_ver, msg.
    - Cung cấp callback thông báo khi có kết quả.
    """
    _instances = {}

    @classmethod
    def get_instance(cls, widget_id: str, widget_dir: str):
        key = (widget_id, os.path.abspath(widget_dir))
        if key not in cls._instances:
            cls._instances[key] = cls(widget_id, widget_dir)
        return cls._instances[key]

    def __init__(self, widget_id: str, widget_dir: str):
        self.widget_id = widget_id
        self.widget_dir = widget_dir
        self.local_ver = get_local_version(widget_dir)
        self.has_update = False
        self.remote_ver = None
        self.checked = False
        self.msg = ""
        self._listeners = []
        self._lock = threading.Lock()
        self._running = False

    def add_listener(self, fn: Callable[[bool, Optional[str]], None]):
        with self._lock:
            self._listeners.append(fn)
            already_done = self.checked
            has_up = self.has_update
            rem_v = self.remote_ver
        if already_done:
            try:
                fn(has_up, rem_v)
            except Exception:
                pass

    def start_check(self, github_url: Optional[str] = None):
        """Khởi chạy ngầm fetch repo 1 lần để kiểm tra phiên bản mới."""
        with self._lock:
            if self._running:
                return
            self._running = True

        def _worker():
            url = github_url
            if not url:
                manifest_p = os.path.join(self.widget_dir, "widget.json")
                if os.path.isfile(manifest_p):
                    try:
                        with open(manifest_p, "r", encoding="utf-8-sig") as f:
                            url = json.load(f).get("github_url")
                    except Exception:
                        pass
            if not url:
                defaults = {
                    "claude": "https://github.com/Code4Fun-Free/claude-usage-bar",
                    "token": "https://github.com/Code4Fun-Free/claude-usage-bar",
                    "gpu": "https://github.com/Code4Fun-Free/gpu-usage-bar",
                    "network": "https://github.com/Code4Fun-Free/network-meter-bar",
                }
                url = defaults.get(self.widget_id, "https://github.com/Code4Fun-Free/widget-manager")

            ok, rem_ver, meta, msg = fetch_remote_info(url)
            with self._lock:
                self.checked = True
                self._running = False
                self.remote_ver = rem_ver
                self.msg = msg
                if ok and rem_ver:
                    cmp = compare_versions(self.local_ver, rem_ver)
                    self.has_update = (cmp == 1)
                else:
                    self.has_update = False
                callbacks = list(self._listeners)

            for cb in callbacks:
                try:
                    cb(self.has_update, self.remote_ver)
                except Exception:
                    pass

        t = threading.Thread(target=_worker, daemon=True, name=f"UpdateChecker-{self.widget_id}")
        t.start()
        return t


def check_update_on_startup(widget_id: str, widget_dir: str, callback: Optional[Callable[[bool, Optional[str]], None]] = None) -> UpdateChecker:
    """
    Hàm tiện ích gọi mỗi lần khởi chạy widget để fetch repo 1 lần kiểm tra phiên bản mới.
    """
    checker = UpdateChecker.get_instance(widget_id, widget_dir)
    if callback:
        checker.add_listener(callback)
    if not checker.checked and not checker._running:
        checker.start_check()
    return checker


def get_update_status(widget_id: str, widget_dir: str) -> Tuple[bool, Optional[str]]:
    """Trả về (has_update, remote_ver) từ cache của UpdateChecker."""
    checker = UpdateChecker.get_instance(widget_id, widget_dir)
    return checker.has_update, checker.remote_ver


def download_and_extract_github_zip(github_url: str, target_dir: str, branch: str = "main",
                                    callback: Optional[Callable[[str, str], None]] = None) -> Tuple[bool, str]:
    """
    Tải bản cập nhật mới nhất từ GitHub bằng giao thức HTTP (file zip) và ghi đè an toàn vào target_dir:
    - callback(status_type, message): callback nhận tiến trình ('info', 'success', 'error')
    - Bảo vệ các tệp tin cấu hình cá nhân: config.json, .venv-win, .venv, .git, v.v.
    - Cập nhật file VERSION và widget.json với số phiên bản mới tải về.
    """
    base_url = normalize_github_url(github_url)
    if "github.com/" not in base_url:
        return False, "URL không hợp lệ. Vui lòng cung cấp link repository GitHub (ví dụ: https://github.com/owner/repo)"

    parts = base_url.split("github.com/")[-1].split("/")
    if len(parts) < 2:
        return False, "Đường dẫn GitHub phải có dạng https://github.com/owner/repo"

    owner, repo = parts[0], parts[1]
    branches_to_try = [branch]
    if branch != "main" and "main" not in branches_to_try:
        branches_to_try.append("main")
    if branch != "master" and "master" not in branches_to_try:
        branches_to_try.append("master")

    zip_bytes = None
    used_branch = None

    if callback:
        callback("info", f"[1/4] Đang kết nối tới GitHub ({owner}/{repo})...")

    headers = {"User-Agent": "MediaWorkspace-Widget-Updater/1.0"}
    for br in branches_to_try:
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{br}.zip"
        if callback:
            callback("info", f"[1/4] Đang tải zip từ nhánh '{br}'...")
        try:
            req = urllib.request.Request(zip_url, headers=headers)
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.status == 200:
                    zip_bytes = resp.read()
                    used_branch = br
                    break
        except Exception:
            continue

    if not zip_bytes:
        return False, f"Không thể tải file zip từ GitHub '{owner}/{repo}'. Hãy kiểm tra lại URL hoặc kết nối mạng."

    if callback:
        callback("info", f"[2/4] Tải về thành công ({len(zip_bytes) // 1024} KB). Đang giải nén...")

    # Giải nén ra thư mục tạm
    try:
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        namelist = zf.namelist()
        if not namelist:
            return False, "File zip tải về bị rỗng."
        root_dir_in_zip = namelist[0].split("/")[0]

        with tempfile.TemporaryDirectory() as tmp_extract:
            zf.extractall(tmp_extract)
            source_folder = os.path.join(tmp_extract, root_dir_in_zip)
            if not os.path.isdir(source_folder):
                source_folder = tmp_extract

            # Kiểm tra phiên bản mới từ gói zip vừa tải về
            downloaded_ver = None
            v_in_zip = os.path.join(source_folder, "VERSION")
            if os.path.isfile(v_in_zip):
                try:
                    with open(v_in_zip, "r", encoding="utf-8") as f:
                        downloaded_ver = f.read().strip()
                except Exception:
                    pass
            if not downloaded_ver:
                m_in_zip = os.path.join(source_folder, "widget.json")
                if os.path.isfile(m_in_zip):
                    try:
                        with open(m_in_zip, "r", encoding="utf-8-sig") as f:
                            downloaded_ver = json.load(f).get("version")
                    except Exception:
                        pass

            # Danh sách các file/thư mục được bảo vệ (KHÔNG GHI ĐÈ để giữ cấu hình người dùng)
            PROTECTED_ITEMS = {
                "config.json", ".venv-win", ".venv", ".git", ".env",
                "__pycache__", ".idea", ".vscode"
            }

            os.makedirs(target_dir, exist_ok=True)

            # Tự động sao lưu mã nguồn hiện tại trước khi ghi đè để khôi phục khi cần
            backup_dir = os.path.join(target_dir, "_backup_pre_update")
            try:
                os.makedirs(backup_dir, exist_ok=True)
                for item in os.listdir(target_dir):
                    if item not in PROTECTED_ITEMS and item != "_backup_pre_update":
                        s_p = os.path.join(target_dir, item)
                        d_p = os.path.join(backup_dir, item)
                        if os.path.isfile(s_p):
                            shutil.copy2(s_p, d_p)
            except Exception:
                pass

            updated_files_count = 0

            for root, dirs, files in os.walk(source_folder):
                rel_path = os.path.relpath(root, source_folder)
                dest_root = target_dir if rel_path == "." else os.path.join(target_dir, rel_path)

                dirs[:] = [d for d in dirs if d not in PROTECTED_ITEMS]
                os.makedirs(dest_root, exist_ok=True)

                for f in files:
                    if f in PROTECTED_ITEMS and os.path.exists(os.path.join(dest_root, f)):
                        continue  # Giữ nguyên cấu hình cá nhân
                    src_f = os.path.join(root, f)
                    dest_f = os.path.join(dest_root, f)
                    shutil.copy2(src_f, dest_f)
                    updated_files_count += 1

            # Đảm bảo file VERSION và widget.json ghi nhận đúng phiên bản mới
            if downloaded_ver:
                try:
                    with open(os.path.join(target_dir, "VERSION"), "w", encoding="utf-8") as vf:
                        vf.write(f"{downloaded_ver}\n")
                except Exception:
                    pass

            manifest_p = os.path.join(target_dir, "widget.json")
            if os.path.isfile(manifest_p):
                try:
                    with open(manifest_p, "r", encoding="utf-8-sig") as mf:
                        m_data = json.load(mf)
                    m_data["github_url"] = base_url
                    if downloaded_ver:
                        m_data["version"] = str(downloaded_ver)
                    with open(manifest_p, "w", encoding="utf-8") as mf:
                        json.dump(m_data, mf, indent=2, ensure_ascii=False)
                except Exception:
                    pass

            if callback:
                callback("info", f"[3/4] Đã ghi đè {updated_files_count} tệp tin từ nhánh '{used_branch}'.")

            # Cập nhật dependencies nếu có requirements.txt và virtualenv
            req_file = os.path.join(target_dir, "requirements.txt")
            venv_py = os.path.join(target_dir, ".venv-win", "Scripts", "python.exe") if sys.platform == "win32" else os.path.join(target_dir, ".venv", "bin", "python")
            if os.path.isfile(req_file) and os.path.isfile(venv_py):
                if callback:
                    callback("info", "[3/4] Đang kiểm tra thư viện phụ thuộc (pip install)...")
                try:
                    subprocess.run([venv_py, "-m", "pip", "install", "-r", req_file, "--quiet"],
                                   timeout=45, capture_output=True)
                except Exception:
                    pass

    except Exception as e:
        return False, f"Lỗi trong quá trình giải nén và cập nhật: {e}"

    final_msg = f"[4/4] Cập nhật thành công từ nhánh '{used_branch}'"
    if downloaded_ver:
        final_msg += f" (Phiên bản v{downloaded_ver})"
    if callback:
        callback("success", final_msg + "!")
    return True, final_msg


def restart_widget_process(widget_dir: str, entry_script: Optional[str] = None):
    """Khởi động lại tiến trình widget hiện tại và thoát tiến trình cũ."""
    manifest_p = os.path.join(widget_dir, "widget.json")
    script = entry_script
    if not script and os.path.isfile(manifest_p):
        try:
            with open(manifest_p, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                script = data.get("entry") or data.get("widget_script")
        except Exception:
            pass

    if not script:
        for candidate in ["run.py", "claude_usage_app.py", "gpu_usage_app.py", "network_meter_app.py"]:
            if os.path.isfile(os.path.join(widget_dir, candidate)):
                script = candidate
                break

    if not script:
        script = sys.argv[0]

    py_exe = sys.executable
    venv_pyw = os.path.join(widget_dir, ".venv-win", "Scripts", "pythonw.exe")
    venv_py = os.path.join(widget_dir, ".venv-win", "Scripts", "python.exe")
    if os.path.isfile(venv_pyw):
        py_exe = venv_pyw
    elif os.path.isfile(venv_py):
        py_exe = venv_py

    cmd = [py_exe, os.path.join(widget_dir, script)]
    if sys.platform == "win32":
        creationflags = (subprocess.CREATE_NO_WINDOW
                         | getattr(subprocess, "DETACHED_PROCESS", 0x00000008)
                         | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0x00000200))
    else:
        creationflags = 0
    subprocess.Popen(cmd, cwd=widget_dir, creationflags=creationflags)
    sys.exit(0)


def show_update_dialog(parent_root, widget_id: str, widget_name: str, widget_dir: str,
                       default_github_url: Optional[str] = None, on_restart=None):
    """
    Hiển thị hộp thoại giao diện Tkinter cập nhật widget từ GitHub qua HTTP với Quản lý Phiên bản (Version Management):
    - Đọc phiên bản trên máy (Local Version) vs phiên bản trên GitHub (Remote Version).
    - Cảnh báo trực quan nếu bản trên máy mới hơn bản trên GitHub.
    - Cung cấp nút nâng cấp, cài đặt lại và hiển thị tiến trình chi tiết.
    - Tự động đếm ngược khởi động lại widget sau khi hoàn thành.
    """
    gh_url = default_github_url or ""
    manifest_p = os.path.join(widget_dir, "widget.json")
    if os.path.isfile(manifest_p):
        try:
            with open(manifest_p, "r", encoding="utf-8-sig") as f:
                gh_url = json.load(f).get("github_url") or gh_url
        except Exception:
            pass

    if not gh_url:
        defaults = {
            "claude": "https://github.com/Code4Fun-Free/claude-usage-bar",
            "token": "https://github.com/Code4Fun-Free/claude-usage-bar",
            "gpu": "https://github.com/Code4Fun-Free/gpu-usage-bar",
            "network": "https://github.com/Code4Fun-Free/network-meter-bar",
        }
        gh_url = defaults.get(widget_id, "https://github.com/Code4Fun-Free/widget-manager")

    local_ver = get_local_version(widget_dir)

    try:
        if parent_root is not None and parent_root.winfo_exists():
            win = tk.Toplevel(parent_root)
        else:
            win = tk.Tk()
    except Exception:
        win = tk.Tk()
    win.title(f"Kiểm Tra Cập Nhật — {widget_name}")
    win.geometry("560x440")
    win.minsize(520, 420)
    win.configure(bg=HEX_BG_SURFACE)
    win.attributes("-topmost", True)

    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - 560) // 2)
    y = max(0, (sh - 440) // 2)
    win.geometry(f"+{x}+{y}")

    # Header
    hdr = tk.Frame(win, bg=HEX_BG_SURFACE, padx=20, pady=14)
    hdr.pack(fill="x")

    t_box = tk.Frame(hdr, bg=HEX_BG_SURFACE)
    t_box.pack(side="left")
    tk.Label(t_box, text=f"🔄 Kiểm Tra Cập Nhật {widget_name}", font=("Segoe UI", 12, "bold"),
             bg=HEX_BG_SURFACE, fg=HEX_TEXT_MAIN).pack(anchor="w")
    tk.Label(t_box, text="Tự động kiểm tra phiên bản và nâng cấp widget trực tiếp từ GitHub qua HTTP",
             font=("Segoe UI", 8), bg=HEX_BG_SURFACE, fg=HEX_TEXT_MUTED).pack(anchor="w", pady=(2, 0))

    # Khung Thẻ Quản Lý Phiên Bản (Version Card)
    ver_card = ModernCard(win, bg=HEX_BG_CARD, padx=14, pady=12)
    ver_card.pack(fill="x", padx=20, pady=(0, 10))
    vf = ver_card.get_content_frame()

    row_cols = tk.Frame(vf, bg=HEX_BG_CARD)
    row_cols.pack(fill="x")

    # Cột Trái: Phiên bản trên máy
    col_loc = tk.Frame(row_cols, bg=HEX_BG_CARD)
    col_loc.pack(side="left", fill="both", expand=True)
    tk.Label(col_loc, text="📦 PHIÊN BẢN TRÊN MÁY", font=("Segoe UI", 8, "bold"),
             bg=HEX_BG_CARD, fg=HEX_TEXT_MUTED).pack(anchor="w")
    lbl_loc_ver = tk.Label(col_loc, text=f"v{local_ver}", font=("Segoe UI", 13, "bold"),
                           bg=HEX_BG_CARD, fg=HEX_TEXT_MAIN)
    lbl_loc_ver.pack(anchor="w", pady=(2, 0))

    # Vạch phân cách giữa
    tk.Frame(row_cols, bg=HEX_BORDER, width=1).pack(side="left", fill="y", padx=14)

    # Cột Phải: Phiên bản trên GitHub
    col_rem = tk.Frame(row_cols, bg=HEX_BG_CARD)
    col_rem.pack(side="left", fill="both", expand=True)
    tk.Label(col_rem, text="🌐 PHIÊN BẢN TRÊN GITHUB", font=("Segoe UI", 8, "bold"),
             bg=HEX_BG_CARD, fg=HEX_TEXT_MUTED).pack(anchor="w")
    lbl_rem_ver = tk.Label(col_rem, text="Đang kiểm tra...", font=("Segoe UI", 13, "bold"),
                           bg=HEX_BG_CARD, fg=HEX_CYAN)
    lbl_rem_ver.pack(anchor="w", pady=(2, 0))

    # Dải trạng thái so sánh phiên bản (Status Banner)
    lbl_ver_status = tk.Label(vf, text="⏳ Đang truy vấn thông tin phiên bản từ GitHub...",
                              font=("Segoe UI", 8), bg=HEX_BG_CARD, fg=HEX_TEXT_MUTED,
                              wraplength=480, justify="left", anchor="w")
    lbl_ver_status.pack(fill="x", pady=(10, 0))

    # Thân Form: Nhập GitHub URL & Kiểm tra
    card_url = ModernCard(win, bg=HEX_BG_CARD, padx=14, pady=10)
    card_url.pack(fill="x", padx=20, pady=(0, 10))
    cf = card_url.get_content_frame()

    tk.Label(cf, text="Đường dẫn GitHub Repository (HTTP):", font=("Segoe UI", 8, "bold"),
             bg=HEX_BG_CARD, fg=HEX_TEXT_MAIN).pack(anchor="w")

    url_row = tk.Frame(cf, bg=HEX_BG_CARD)
    url_row.pack(fill="x", pady=(6, 6))

    url_var = tk.StringVar(value=gh_url)
    entry_url = tk.Entry(url_row, textvariable=url_var, font=("Segoe UI", 9),
                         bg=HEX_BG_INPUT, fg=HEX_TEXT_MAIN, insertbackground="white",
                         relief="flat", highlightthickness=1, highlightbackground=HEX_BORDER,
                         highlightcolor=HEX_CYAN)
    entry_url.pack(side="left", fill="x", expand=True, ipady=3)

    btn_check_ver = ModernButton(url_row, text="Kiểm tra", width=75, height=28,
                                 bg=HEX_BG_SURFACE, fg=HEX_TEXT_MAIN,
                                 command=lambda: trigger_version_check())
    btn_check_ver.pack(side="right", padx=(8, 0))

    auto_restart_var = tk.BooleanVar(value=True)
    cb_restart = tk.Checkbutton(cf, text="Tự động khởi động lại widget sau khi cập nhật thành công",
                                variable=auto_restart_var, font=("Segoe UI", 8),
                                bg=HEX_BG_CARD, fg=HEX_TEXT_MUTED, selectcolor=HEX_BG_INPUT,
                                activebackground=HEX_BG_CARD, activeforeground=HEX_TEXT_MAIN)
    cb_restart.pack(anchor="w")

    # Khung Trạng Thái / Nhật Ký Quá Trình (Progress Log)
    log_box = tk.Frame(win, bg=HEX_BG_INPUT, padx=12, pady=8, relief="flat",
                       highlightthickness=1, highlightbackground=HEX_BORDER)
    log_box.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    status_lbl = tk.Label(log_box, text="[i] Hãy nhấn 'Bắt đầu Cập Nhật' để tải bản mới nhất từ GitHub qua HTTP.",
                          font=("Segoe UI", 8), bg=HEX_BG_INPUT, fg=HEX_TEXT_MUTED,
                          wraplength=480, justify="left", anchor="nw")
    status_lbl.pack(fill="both", expand=True)

    # Nút Bấm Hành Động
    btn_bar = tk.Frame(win, bg=HEX_BG_SURFACE, padx=20, pady=12)
    btn_bar.pack(fill="x", side="bottom")

    btn_close = ModernButton(btn_bar, text="Đóng", width=80, height=32,
                             bg=HEX_BG_CARD, fg=HEX_TEXT_MAIN, command=win.destroy)
    btn_close.pack(side="right")

    btn_update = None
    is_running = {"v": False}
    remote_data = {"ver": None, "ok": False}
    ui_queue = queue.Queue()

    def update_version_ui(ok: bool, rem_ver: Optional[str], branch_msg: str):
        remote_data["ok"] = ok
        remote_data["ver"] = rem_ver
        if ok and rem_ver:
            lbl_rem_ver.config(text=f"v{rem_ver}", fg=HEX_EMERALD)
            cmp = compare_versions(local_ver, rem_ver)
            if cmp == 1:
                lbl_ver_status.config(
                    text=f"🟢 Có bản cập nhật mới (v{rem_ver}) từ {branch_msg}! Nhấn nút bên dưới để nâng cấp.",
                    fg=HEX_EMERALD
                )
                if btn_update and not is_running["v"]:
                    btn_update.set_text(f"🚀 Nâng Cấp Lên v{rem_ver}")
                    btn_update.set_bg(HEX_CYAN)
            elif cmp == 0:
                lbl_ver_status.config(
                    text=f"⚪ Phiên bản hiện tại (v{local_ver}) đã là mới nhất so với GitHub ({branch_msg}).",
                    fg=HEX_TEXT_MUTED
                )
                if btn_update and not is_running["v"]:
                    btn_update.set_text("Cài Đặt Lại")
                    btn_update.set_bg(HEX_BG_CARD)
            else:
                lbl_ver_status.config(
                    text=f"⚠️ Bản trên máy (v{local_ver}) mới hơn trên GitHub (v{rem_ver}). Cập nhật sẽ bị ghi đè về bản cũ trên GitHub!",
                    fg="#F59E0B"
                )
                if btn_update and not is_running["v"]:
                    btn_update.set_text("Ghi Đè từ GitHub")
                    btn_update.set_bg(HEX_BG_CARD)
        else:
            lbl_rem_ver.config(text="Không tìm thấy", fg="#F87171")
            lbl_ver_status.config(
                text=f"❌ {branch_msg}",
                fg="#F87171"
            )
            if btn_update and not is_running["v"]:
                btn_update.set_text("Cập Nhật Bắt Buộc")
                btn_update.set_bg(HEX_BG_CARD)

    def finish_ui(ok: bool, msg: str):
        if ok:
            btn_update.set_state(True)
            btn_update.set_bg(HEX_EMERALD)
            btn_update.set_fg(HEX_BG_DARK)
            btn_update.command = on_do_restart

            countdown = {"t": 3}
            if auto_restart_var.get():
                btn_update.set_text(f"Khởi động lại ngay ({countdown['t']}s)")
                def tick():
                    countdown["t"] -= 1
                    if countdown["t"] <= 0:
                        on_do_restart()
                    else:
                        btn_update.set_text(f"Khởi động lại ngay ({countdown['t']}s)")
                        win.after(1000, tick)
                win.after(1000, tick)
            else:
                btn_update.set_text("Khởi động lại ngay")
        else:
            btn_update.set_state(True)
            btn_update.set_text("Thử lại")
            btn_update.set_bg(HEX_CYAN)

    def poll_ui_queue():
        try:
            while not ui_queue.empty():
                item = ui_queue.get_nowait()
                tag = item[0]
                if tag == "version":
                    _, ok, ver, msg = item
                    update_version_ui(ok, ver, msg)
                elif tag == "progress":
                    _, kind, msg = item
                    color_map = {"info": HEX_CYAN, "success": HEX_EMERALD, "error": "#F87171"}
                    prefix = {"info": "[🔄] ", "success": "[✅] ", "error": "[❌] "}
                    status_lbl.config(text=prefix.get(kind, "") + msg, fg=color_map.get(kind, HEX_TEXT_MAIN))
                elif tag == "finish":
                    _, ok, msg = item
                    finish_ui(ok, msg)
        except Exception as e:
            import traceback
            traceback.print_exc()
        if win.winfo_exists():
            win.after(50, poll_ui_queue)

    def trigger_version_check():
        lbl_rem_ver.config(text="Đang kiểm tra...", fg=HEX_CYAN)
        lbl_ver_status.config(text="⏳ Đang kết nối tới GitHub để kiểm tra phiên bản...", fg=HEX_TEXT_MUTED)
        target_url = url_var.get().strip()
        def worker():
            ok, ver, meta, msg = fetch_remote_info(target_url)
            ui_queue.put(("version", ok, ver, msg))
        threading.Thread(target=worker, daemon=True).start()

    def do_update():
        if is_running["v"]:
            return
        is_running["v"] = True
        target_url = url_var.get().strip()
        if not target_url:
            status_lbl.config(text="[!] Vui lòng nhập đường dẫn GitHub repository.", fg="#F87171")
            is_running["v"] = False
            return

        btn_update.set_state(False)
        btn_update.set_text("Đang cập nhật...")

        def on_msg(kind, msg):
            ui_queue.put(("progress", kind, msg))

        def run_thread():
            ok, msg = download_and_extract_github_zip(target_url, widget_dir, callback=on_msg)
            is_running["v"] = False
            ui_queue.put(("finish", ok, msg))

        threading.Thread(target=run_thread, daemon=True).start()

    def on_do_restart():
        try:
            win.destroy()
        except Exception:
            pass
        if on_restart:
            on_restart()
        else:
            restart_widget_process(widget_dir)

    btn_update = ModernButton(btn_bar, text="Bắt đầu Cập Nhật", width=160, height=32,
                              bg=HEX_CYAN, fg=HEX_BG_DARK, command=do_update)
    btn_update.pack(side="right", padx=(0, 10))

    # Bắt đầu vòng lặp đọc hàng đợi giao diện an toàn
    win.after(50, poll_ui_queue)

    # Nếu UpdateChecker đã kiểm tra trước đó, nạp ngay dữ liệu để hiển thị tức thì
    cached_checker = UpdateChecker.get_instance(widget_id, widget_dir)
    if cached_checker.checked and cached_checker.remote_ver:
        update_version_ui(True, cached_checker.remote_ver, cached_checker.msg)

    # Kích hoạt kiểm tra phiên bản mới nhất từ GitHub
    trigger_version_check()

    if isinstance(win, tk.Tk):
        win.mainloop()


