#!/usr/bin/env python3
"""
Widget nổi hiển thị usage ở góc trái taskbar (Windows; có chạy thử được trên Linux).

Dạng gọn (nằm thẳng trên taskbar, không nền):   ✦ Session 33% ▬ | 📅 Week 69% ▬  ⌄
Bấm vào: mở panel mở rộng phía trên taskbar (Chi tiết sử dụng token, Phiên hiện tại,
Giới hạn tuần, Làm mới ngay, Cài đặt).

Icon tray của Windows chỉ nằm được ở khay thông báo phía phải taskbar, nên muốn hiện ở
góc trái thì cần cửa sổ riêng: không viền, luôn nổi trên cùng, nền trong suốt thật
(cửa sổ nhiều lớp alpha theo từng điểm ảnh, UpdateLayeredWindow).

- Kéo thả bằng chuột trái để đặt vị trí (được nhớ lại); bấm (không kéo) để mở/đóng panel.
- Tự ẩn khi có cửa sổ toàn màn hình (xem phim, chơi game).

Tkinter chạy trong thread riêng; các lời gọi từ thread khác đi qua hàng đợi (thread-safe).
"""

import ctypes
import math
import os
import queue
import sys
import threading
import time
import webbrowser

import ui_kit as ui

WIDGET_DIR = os.path.dirname(os.path.abspath(__file__))
WIDGET_VERSION = ui.get_local_version(WIDGET_DIR)

USAGE_URL = "https://claude.ai/settings/usage"

# ----------------------------------------------------------------------------- kích thước ----
CW, CH = ui.CW_HORIZONTAL, ui.CH_TASKBAR   # widget gọn (236x40 px logic)
FW, FH = ui.FW_PANEL, 356                 # panel mở rộng (328x320 px logic)
FM = ui.FM_SHADOW                         # lề quanh panel cho bóng đổ (14 px)
SS_COMPACT, SS_FLYOUT = ui.SS_COMPACT, ui.SS_FLYOUT   # siêu lấy mẫu
MENU_FONT = ui.MENU_FONT
TICK_MS = 400
CLICK_SLOP = 4            # kéo quá số px này thì coi là kéo thả, không phải bấm

# Ngưỡng đổi màu: >= WARN_AT vàng, >= DANGER_AT đỏ
WARN_AT = 75
DANGER_AT = 90

# ------------------------------------------------------------------------------- màu sắc ----
# Bảng màu tối (Dark Theme)
DARK_THEME = {
    "ink": ui.THEME_DARK["text_main"],
    "label": ui.THEME_DARK["text_muted"],
    "track": ui.THEME_DARK["track"],
    "track_a": ui.THEME_DARK["track_alpha"],
    "divider": ui.THEME_DARK["divider"],
    "divider_a": ui.THEME_DARK["divider_alpha"],
    "chevron": ui.THEME_DARK["text_muted"],
    "spark": (96, 165, 250),
    "spark_panel": (88, 196, 230),
    "cal_ok": ui.COLOR_OK,
    "cal_danger": ui.COLOR_DANGER,
    "yellow": ui.COLOR_WARN,
    "red": ui.COLOR_DANGER,
    "bar_session": ((56, 189, 248), (59, 130, 246)),
    "bar_week": ((52, 224, 170), (16, 185, 129)),
    "panel_fill": ui.THEME_DARK["bg_panel"],
    "panel_alpha": ui.THEME_DARK["panel_alpha"],
    "panel_border": ui.THEME_DARK["border_panel"],
    "panel_border_a": ui.THEME_DARK["border_alpha"],
    "panel_shadow_fill": ui.THEME_DARK["shadow_fill"],
    "panel_muted": ui.THEME_DARK["text_muted"],
    "hover_fill": ui.THEME_DARK["hover_bg"],
}

# Bảng màu sáng (Light Theme) - tinh chỉnh độ tương phản cao chống mờ trên nền sáng
LIGHT_THEME = {
    "ink": (15, 23, 42),            # Slate-900: chữ số đậm, tương phản cao
    "label": (51, 65, 85),          # Slate-700: nhãn rõ nét
    "track": (203, 213, 225),       # Slate-300: rãnh thanh tiến trình sắc nét
    "track_a": 160,
    "divider": (148, 163, 184),     # Slate-400
    "divider_a": 100,
    "chevron": (71, 85, 105),       # Slate-600
    "spark": (29, 78, 216),         # Blue-700: tương phản cao trên nền sáng
    "spark_panel": (37, 99, 235),   # Blue-600
    "cal_ok": (5, 150, 105),        # Emerald-600
    "cal_danger": (220, 38, 38),    # Red-600
    "yellow": (217, 119, 6),        # Amber-600
    "red": (220, 38, 38),           # Red-600
    "bar_session": ((2, 132, 199), (37, 99, 235)),  # Sky-600 đến Blue-600
    "bar_week": ((16, 185, 129), (5, 150, 105)),    # Emerald-500 đến Emerald-600
    "panel_fill": (248, 250, 252),  # Kính sáng Slate-50
    "panel_alpha": 250,
    "panel_border": (203, 213, 225),# Slate-300
    "panel_border_a": 180,
    "panel_shadow_fill": 80,
    "panel_muted": (100, 116, 139), # Slate-500
    "hover_fill": (0, 0, 0, 18),    # Hover xám nhẹ
}

# Tương thích ngược với các biến hằng số cũ
SPARK = DARK_THEME["spark"]
SPARK_PANEL = DARK_THEME["spark_panel"]
CAL_OK = DARK_THEME["cal_ok"]
YELLOW = DARK_THEME["yellow"]
RED = DARK_THEME["red"]
BAR_SESSION = DARK_THEME["bar_session"]
BAR_WEEK = DARK_THEME["bar_week"]
PANEL_FILL = DARK_THEME["panel_fill"]
PANEL_ALPHA = DARK_THEME["panel_alpha"]
PANEL_BORDER = DARK_THEME["panel_border"]
WHITE = (255, 255, 255)
PANEL_MUTED = DARK_THEME["panel_muted"]


def _dbg(*a):
    """Nhật ký sự kiện widget (bật bằng biến môi trường CLAUDE_USAGE_DEBUG=1) -> stderr / file log."""
    import os
    if os.environ.get("CLAUDE_USAGE_DEBUG"):
        print("[widget]", *a, file=sys.stderr, flush=True)


def _level(p):
    if p is None:
        return "none"
    if p >= DANGER_AT:
        return "danger"
    if p >= WARN_AT:
        return "warn"
    return "ok"


def _bar_colors(level, grad, theme=None):
    th = theme or DARK_THEME
    return {"warn": (th["yellow"], th["yellow"]), "danger": (th["red"], th["red"])}.get(level, grad)


def _pct_text(p):
    return "--%" if p is None else f"{int(round(p))}%"


# --------------------------------------------------------------------------------- bộ vẽ ----
_font = ui.load_font
_Painter = ui.BasePainter


# --------------------------------------------------------------------------- widget gọn ----
def render_compact(five, seven, scale=1.0, light=False):
    """Widget gọn trên taskbar: nền trong suốt (alpha=1 để vẫn bấm được), màu sắc thích ứng theme."""
    th = LIGHT_THEME if light else DARK_THEME
    p = _Painter(CW, CH, scale, SS_COMPACT)
    # font: nhãn bé 8.8px màu dịu, chỉ số quan trọng to 13.5px semibold nổi bật
    f_label = _font(8.8 * p.u, "regular")
    f_pct = _font(13.5 * p.u, "semibold")
    lv5, lv7 = _level(five), _level(seven)

    # Icon lấp lánh (Sparkle)
    p.sparkle(16, 21, 8.5, th["spark"])
    p.sparkle(24.5, 12, 3.2, th["spark"])

    # Icon lịch (Calendar)
    p.calendar(110, 13, 14.5, th["cal_danger"] if lv7 == "danger" else th["cal_ok"])

    bar_w = 48
    def column(x0, name, val, level, grad):
        dim = val is None
        # Nhãn "Session", "Week": font bé 8.8px, màu muted để không làm mất tập trung
        p.text(x0, 14.0, name, f_label, th["label"], alpha=170 if dim else 210)
        c1, c2 = _bar_colors(level, grad, th)
        val_col = c1 if level != "none" else th["ink"]
        # Chỉ số "0%", "100%": font to 13.5px, màu theo mức độ
        p.text(x0, 27.5, _pct_text(val), f_pct, val_col, alpha=150 if dim else 255)
        p.rrect(x0, 31.5, x0 + bar_w, 34.5, 1.5, th["track"], alpha=th["track_a"])
        if not dim:
            fw = max(3.0, bar_w * min(1.0, val / 100.0))
            p.rrect(x0, 31.5, x0 + fw, 34.5, 1.5, c1, gradient=(c1, c2))

    column(34, "Session", five, lv5, th["bar_session"])
    column(130, "Week", seven, lv7, th["bar_week"])

    # Vách ngăn phân cách giữa 2 cột
    p.line([(100, 10), (100, 30)], th["divider"], 1, alpha=th["divider_a"])
    # Mũi tên mở panel ở góc phải
    p.chevron(CW - 14, 21, th["chevron"], "down", 3.8, 1.2)

    img = p.finish()
    img.putalpha(img.getchannel("A").point(lambda v: v if v else 1))  # alpha=1: bấm được, vẫn vô hình
    return img


# ------------------------------------------------------------------------------- panel mở ----
def render_flyout(info, scale=1.0, show_abs=False, light=False):
    """
    Panel mở rộng chi tiết Claude Usage theo chuẩn UI Kit đồng bộ.
    """
    th = LIGHT_THEME if light else DARK_THEME
    five, seven = info.get("five"), info.get("seven")
    p = _Painter(FW, FH, scale, SS_FLYOUT, margin=FM)
    u = p.u

    # 1. Khung panel Acrylic + Bóng đổ Gaussian
    ui.draw_panel_shell(p, th, FW, FH)

    # Phông chữ đồng bộ theo UI Kit
    f_title = p.get_font("panel_title", "semibold")
    f_sub = p.get_font("panel_sub", "regular")
    f_blk = p.get_font("block_title", "semibold")
    f_big = p.get_font("metric_hero", "semibold")
    f_unit = p.get_font("metric_unit", "regular")
    f_detail = p.get_font("metric_detail", "regular")

    pad = 16
    sep = lambda y: p.line([(0, y), (FW, y)], th["divider"], 1.0, alpha=th["divider_a"])

    # ---- 1. Header (Y: 0 -> 60) ----
    p.sparkle(28, 29, 10, th["spark_panel"])
    p.sparkle(38, 19, 3.8, th["spark_panel"])
    p.text(54, 27, "Chi tiết sử dụng token", f_title, th["ink"])
    p.text(54, 46, f"Xem đầy đủ thông tin · v{WIDGET_VERSION}", f_sub, th["panel_muted"])
    p.chevron(FW - 22, 30, th["panel_muted"], "right", 5, 1.5)
    sep(60)

    # ---- 2. Các khối thông số (Blocks) ----
    def block(top, title, val, rel, absolute, grad):
        lv = _level(val)
        # Tiêu đề nhóm: dùng màu nhãn dịu th["label"]
        p.text(pad, top + 22, title, f_blk, th["label"])
        big = _pct_text(val)
        c1, c2 = _bar_colors(lv, grad, th)
        val_col = c1 if val is not None else th["panel_muted"]
        # Chỉ số quan trọng: Size to 23px, tô màu theo mức độ để nổi bật
        p.text(pad, top + 50, big, f_big, val_col)
        p.text(pad + p.text_width(big, f_big) + 8, top + 49, "đã sử dụng", f_unit, th["panel_muted"])
        w_bar = FW - 2 * pad
        p.rrect(pad, top + 59, pad + w_bar, top + 65, 3.0, th["track"], alpha=th["track_a"])
        if val is not None:
            p.rrect(pad, top + 59, pad + max(6.0, w_bar * min(1.0, val / 100.0)), top + 65, 3.0,
                    c1, gradient=(c1, c2))
        text = (((("Đặt lại " + absolute) if show_abs and absolute else rel)
                or ("Chưa có dữ liệu · Cài đặt › Đăng nhập" if val is None else "—")))
        p.text(pad, top + 80, text, f_detail, th["panel_muted"])

    block(60, "Phiên hiện tại (5 giờ)", five, info.get("five_long"), info.get("five_abs"), th["bar_session"])
    sep(148)
    block(148, "Giới hạn tuần (7 ngày)", seven, info.get("seven_long"), info.get("seven_abs"), th["bar_week"])
    sep(236)

    # ---- 3. Hàng hành động (Actions, Y: 244 -> 352) ----
    actions = [
        {"key": "refresh", "label": "Làm mới ngay", "icon_fn": lambda cx, cy, col: p.refresh_icon(cx, cy, 6.8, col)},
        {"key": "update", "label": f"Cập nhật từ GitHub (v{WIDGET_VERSION})…", "icon_fn": lambda cx, cy, col: p.download_icon(cx, cy, 14, col)},
        {"key": "settings", "label": "Cài đặt & Tùy chọn…", "icon_fn": lambda cx, cy, col: p.gear_icon(cx, cy, 7.8, col)},
    ]
    raw_rects = ui.draw_action_rows(p, th, start_y=244, actions=actions, fw=FW, pad=pad)

    raw_rects["header"] = (0, 0, FW, 60)
    raw_rects["reset_five"] = (pad, 60 + 64, FW - pad, 60 + 84)
    raw_rects["reset_seven"] = (pad, 148 + 64, FW - pad, 148 + 84)

    img = p.finish()

    s = scale
    scaled_rects = {k: tuple(round((v + FM) * s) for v in r) for k, r in raw_rects.items()}
    return img, scaled_rects


def apply_hover(img, rects, hover, scale=1.0, light=False):
    return ui.apply_hover_highlight(img, rects, hover, scale=scale, is_dark=not light)


# ----------------------------------------------------------------- cửa sổ nhiều lớp (Win32) ----
class _Win:
    """Gói ctypes cho cửa sổ nhiều lớp alpha theo từng điểm ảnh (UpdateLayeredWindow)."""
    ok = sys.platform == "win32"

    if ok:
        from ctypes import wintypes as _wt

        class _BLEND(ctypes.Structure):
            _fields_ = [("BlendOp", ctypes.c_ubyte), ("BlendFlags", ctypes.c_ubyte),
                        ("SourceConstantAlpha", ctypes.c_ubyte), ("AlphaFormat", ctypes.c_ubyte)]

        class _BMIH(ctypes.Structure):
            _fields_ = [("biSize", ctypes.c_uint32), ("biWidth", ctypes.c_int32),
                        ("biHeight", ctypes.c_int32), ("biPlanes", ctypes.c_uint16),
                        ("biBitCount", ctypes.c_uint16), ("biCompression", ctypes.c_uint32),
                        ("biSizeImage", ctypes.c_uint32), ("biXPelsPerMeter", ctypes.c_int32),
                        ("biYPelsPerMeter", ctypes.c_int32), ("biClrUsed", ctypes.c_uint32),
                        ("biClrImportant", ctypes.c_uint32)]

        u32 = ctypes.WinDLL("user32", use_last_error=True)
        g32 = ctypes.WinDLL("gdi32", use_last_error=True)
        _vp = ctypes.c_void_p
        u32.GetDC.argtypes, u32.GetDC.restype = [_vp], _vp
        u32.ReleaseDC.argtypes = [_vp, _vp]
        u32.GetParent.argtypes, u32.GetParent.restype = [_vp], _vp
        u32.GetWindowLongPtrW.argtypes, u32.GetWindowLongPtrW.restype = [_vp, ctypes.c_int], ctypes.c_ssize_t
        u32.SetWindowLongPtrW.argtypes = [_vp, ctypes.c_int, ctypes.c_ssize_t]
        u32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        u32.UpdateLayeredWindow.argtypes = [_vp, _vp, ctypes.POINTER(_wt.POINT), ctypes.POINTER(_wt.SIZE),
                                            _vp, ctypes.POINTER(_wt.POINT), ctypes.c_uint32,
                                            ctypes.POINTER(_BLEND), ctypes.c_uint32]
        u32.UpdateLayeredWindow.restype = ctypes.c_int
        g32.CreateCompatibleDC.argtypes, g32.CreateCompatibleDC.restype = [_vp], _vp
        g32.CreateDIBSection.argtypes = [_vp, _vp, ctypes.c_uint, ctypes.POINTER(_vp), _vp, ctypes.c_uint]
        g32.CreateDIBSection.restype = _vp
        g32.SelectObject.argtypes, g32.SelectObject.restype = [_vp, _vp], _vp
        g32.DeleteObject.argtypes = [_vp]
        g32.DeleteDC.argtypes = [_vp]

    @classmethod
    def hwnd(cls, tk_window):
        """HWND của khung ngoài của cửa sổ Tk (cái thật sự có kiểu cửa sổ/vị trí)."""
        inner = tk_window.winfo_id()
        return cls.u32.GetParent(inner) or inner

    @classmethod
    def rect(cls, hwnd):
        """(left, top, width, height) thật của cửa sổ."""
        r = cls._wt.RECT()
        cls.u32.GetWindowRect(hwnd, ctypes.byref(r))
        return r.left, r.top, r.right - r.left, r.bottom - r.top

    @classmethod
    def own_by_taskbar(cls, hwnd):
        """Đặt taskbar làm 'chủ' (owner) của cửa sổ. Cửa sổ có owner luôn nằm TRÊN owner trong z-order,
        kể cả khi taskbar Win11 đổi lớp sau khi bấm Start bằng chuột (topmost thường bị chìm xuống dưới)."""
        try:
            tray = cls.u32.FindWindowW("Shell_TrayWnd", None)
            if not tray:
                return False
            cls.u32.GetWindowLongPtrW.argtypes = [cls._vp, ctypes.c_int]
            cls.u32.SetWindowLongPtrW.argtypes = [cls._vp, ctypes.c_int, ctypes.c_ssize_t]
            if cls.u32.GetWindowLongPtrW(hwnd, -8) != tray:        # GWLP_HWNDPARENT
                cls.u32.SetWindowLongPtrW(hwnd, -8, tray)
                return True
        except Exception:
            pass
        return False

    @classmethod
    def make_layered(cls, hwnd, noactivate=False):
        GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TOOLWINDOW, WS_EX_NOACTIVATE = -20, 0x80000, 0x80, 0x08000000
        style = cls.u32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW | (WS_EX_NOACTIVATE if noactivate else 0)
        cls.u32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)

    @classmethod
    def update(cls, hwnd, img, x=None, y=None):
        """Đặt nội dung cửa sổ = ảnh RGBA (alpha thẳng) qua UpdateLayeredWindow."""
        from PIL import Image
        w, h = img.size
        r, g, b, a = img.convert("RGBa").split()          # RGBa = nhân sẵn alpha (yêu cầu của Win32)
        data = Image.merge("RGBA", (b, g, r, a)).tobytes()  # thứ tự byte BGRA

        hdc_screen = cls.u32.GetDC(None)
        memdc = cls.g32.CreateCompatibleDC(hdc_screen)
        bmi = cls._BMIH(40, w, -h, 1, 32, 0, 0, 0, 0, 0, 0)   # -h: ảnh từ trên xuống
        bits = ctypes.c_void_p()
        hbmp = cls.g32.CreateDIBSection(hdc_screen, ctypes.byref(bmi), 0, ctypes.byref(bits), None, 0)
        try:
            ctypes.memmove(bits, data, len(data))
            old = cls.g32.SelectObject(memdc, hbmp)
            size = cls._wt.SIZE(w, h)
            src = cls._wt.POINT(0, 0)
            blend = cls._BLEND(0, 0, 255, 1)                  # AC_SRC_OVER, dùng alpha của từng điểm
            dst = None if x is None else ctypes.byref(cls._wt.POINT(x, y))
            ok = cls.u32.UpdateLayeredWindow(hwnd, hdc_screen, dst, ctypes.byref(size), memdc,
                                             ctypes.byref(src), 0, ctypes.byref(blend), 2)  # ULW_ALPHA
            cls.g32.SelectObject(memdc, old)
            return bool(ok)
        finally:
            cls.g32.DeleteObject(hbmp)
            cls.g32.DeleteDC(memdc)
            cls.u32.ReleaseDC(None, hdc_screen)


def _enable_thread_dpi_awareness():
    """Cho riêng thread của widget nhận biết DPI -> vẽ theo px thật, nét sắc thay vì bị phóng mờ."""
    if sys.platform != "win32":
        return
    try:
        fn = ctypes.windll.user32.SetThreadDpiAwarenessContext
        fn.argtypes = [ctypes.c_void_p]
        fn.restype = ctypes.c_void_p
        fn(ctypes.c_void_p(-4))  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    except Exception:
        pass


def _dpi_scale():
    if sys.platform != "win32":
        return 1.0
    try:
        return max(1.0, ctypes.windll.user32.GetDpiForSystem() / 96.0)
    except Exception:
        return 1.0


def _taskbar_light():
    """Taskbar đang ở giao diện sáng? (để chọn bảng màu tương phản cao, chống mờ nét)"""
    if sys.platform != "win32":
        return False
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        sys_light = False
        try:
            sys_light = winreg.QueryValueEx(key, "SystemUsesLightTheme")[0] == 1
        except Exception:
            try:
                sys_light = winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 1
            except Exception:
                pass

        color_prev = False
        try:
            color_prev = winreg.QueryValueEx(key, "ColorPrevalence")[0] == 1
        except Exception:
            pass
        winreg.CloseKey(key)

        # Nếu taskbar bật "Show accent color on Start and taskbar", kiểm tra độ sáng màu chủ đạo
        if color_prev:
            try:
                dwm_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\DWM")
                accent = None
                for n in ("AccentColor", "ColorizationColor"):
                    try:
                        accent = winreg.QueryValueEx(dwm_key, n)[0]
                        if accent:
                            break
                    except Exception:
                        pass
                winreg.CloseKey(dwm_key)

                if accent is not None:
                    r = accent & 0xFF
                    g = (accent >> 8) & 0xFF
                    b = (accent >> 16) & 0xFF
                    lum = 0.299 * r + 0.587 * g + 0.114 * b
                    return lum > 140  # Nền sáng -> trả về True
            except Exception:
                pass

        return sys_light
    except Exception:
        return False


def _work_area(sw, sh):
    """(left, top, right, bottom) vùng làm việc (không gồm taskbar), px thật."""
    if sys.platform == "win32":
        try:
            from ctypes import wintypes
            r = wintypes.RECT()
            ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
            return r.left, r.top, r.right, r.bottom
        except Exception:
            pass
    return 0, 0, sw, sh


def _foreground_fullscreen():
    """True nếu cửa sổ đang ở foreground phủ kín cả màn hình (phim, game...)."""
    if sys.platform != "win32":
        return False
    try:
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        hwnd = u32.GetForegroundWindow()
        if not hwnd:
            return False
        cls = ctypes.create_unicode_buffer(64)
        u32.GetClassNameW(hwnd, cls, 64)
        if cls.value in ("Progman", "WorkerW", "Shell_TrayWnd", "Shell_SecondaryTrayWnd",
                         "Windows.UI.Core.CoreWindow", "XamlExplorerHostIslandWindow",
                         "TopLevelWindowForOverflowXamlIsland"):
            return False  # desktop / taskbar / Start, Search, trung tâm thông báo không tính
        if not u32.IsWindowVisible(hwnd):
            return False
        cloaked = ctypes.c_int(0)   # DWMWA_CLOAKED: cửa sổ UWP "ẩn" vẫn còn là foreground sau khi đóng
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), 4) == 0 and cloaked.value:
            return False
        rect = wintypes.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(rect))
        sw, sh = u32.GetSystemMetrics(0), u32.GetSystemMetrics(1)
        return rect.left <= 0 and rect.top <= 0 and rect.right >= sw and rect.bottom >= sh
    except Exception:
        return False


def _cursor_and_button():
    """(x, y, đang giữ chuột trái?) theo px thật; None nếu không hỗ trợ."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes
        pt = wintypes.POINT()
        ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
        down = bool(ctypes.windll.user32.GetAsyncKeyState(0x01) & 0x8000)
        return pt.x, pt.y, down
    except Exception:
        return None


def _default_position(sw, sh, w, h, scale):
    """Góc trái taskbar (taskbar ở dưới), ngay sau widget thời tiết; không rõ thì góc trái dưới."""
    l, t, r, b = _work_area(sw, sh)
    tb_h = sh - b
    if tb_h > 0 and t == 0 and l == 0 and r == sw:
        return round(200 * scale), b + (tb_h - h) // 2
    return round(8 * scale), sh - h - round(8 * scale)


# Điểm neo: dính vào một góc (luôn giữ đúng chỗ) hoặc "free" = kéo thả vị trí bất kỳ
ANCHORS = (("bottom-left", "Dưới trái (taskbar, cạnh widget thời tiết)"),
           ("bottom-right", "Dưới phải (taskbar, cạnh khay hệ thống)"),
           ("top-left", "Trên trái"),
           ("top-right", "Trên phải"),
           ("free", "Tự do (kéo thả)"))
ANCHOR_KEYS = tuple(k for k, _ in ANCHORS)


def _tray_left(sw, sh):
    """Mép trái của khay hệ thống trên taskbar (px thật), hoặc None nếu không tìm được."""
    if sys.platform != "win32":
        return None
    try:
        from ctypes import wintypes
        u32 = ctypes.windll.user32
        u32.FindWindowW.restype = ctypes.c_void_p
        u32.FindWindowExW.restype = ctypes.c_void_p
        u32.FindWindowExW.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_wchar_p, ctypes.c_wchar_p]
        bar = u32.FindWindowW("Shell_TrayWnd", None)
        tray = u32.FindWindowExW(bar, None, "TrayNotifyWnd", None) if bar else None
        if not tray:
            return None
        rect = wintypes.RECT()
        u32.GetWindowRect(ctypes.c_void_p(tray), ctypes.byref(rect))
        return rect.left if 0 < rect.left < sw and rect.right > rect.left else None
    except Exception:
        return None


def _anchor_position(anchor, sw, sh, w, h, scale):
    """Toạ độ (x, y) của widget theo điểm neo; None nếu 'free' (dùng vị trí do người dùng đặt)."""
    if anchor not in ANCHOR_KEYS or anchor == "free":
        return None
    l, t, r, b = _work_area(sw, sh)
    m = round(8 * scale)
    tb_h = sh - b
    taskbar_bottom = tb_h > 0 and t == 0 and l == 0 and r == sw
    if anchor == "bottom-left":
        return _default_position(sw, sh, w, h, scale)
    if anchor == "bottom-right":
        if taskbar_bottom:
            tray = _tray_left(sw, sh)
            x = (tray - m) if tray else (sw - round(360 * scale))
            return x - w, b + (tb_h - h) // 2
        return r - w - m, b - h - m
    if anchor == "top-left":
        return l + m, t + m
    return r - w - m, t + m          # top-right


# ----------------------------------------------------------------------------------- widget ----
class Widget:
    def __init__(self, on_refresh=None, on_login=None, on_session_key=None, on_quit=None,
                 on_hide=None, on_move=None, on_anchor=None, on_autostart_toggle=None,
                 autostart_status=None, position=None, anchor="bottom-left"):
        """
        Callback (chạy trong thread của widget; app nên tự đưa việc nặng sang thread khác):
        on_refresh / on_login / on_session_key / on_quit / on_hide / on_move((x, y)) /
        on_anchor(tên điểm neo mới, do người dùng chọn trong menu của widget)
        anchor: một trong ANCHOR_KEYS. Khác "free" thì widget bị khoá ở góc đó (không kéo được).
        position: (x, y) đã lưu (px thật) cho chế độ "free"; None để dùng vị trí mặc định
        """
        self._cb = dict(refresh=on_refresh, login=on_login, session_key=on_session_key,
                        quit=on_quit, hide=on_hide, move=on_move, anchor=on_anchor,
                        autostart_toggle=on_autostart_toggle, autostart_status=autostart_status)
        self._anchor = anchor if anchor in ANCHOR_KEYS else "bottom-left"
        self._position = tuple(position) if position else None
        self._q = queue.Queue()
        self._lock = threading.Lock()
        self._thread = None
        self._info = {"five": None, "seven": None}
        self._show_abs = False
        self._wanted = False
        self._shown = False
        self._last_fs = None

    # ---- gọi được từ thread bất kỳ ---------------------------------------------------
    def show(self):
        self._start()
        self._q.put(("show", None))

    def hide(self):
        if self._thread:
            self._q.put(("hide", None))

    def set_info(self, info):
        """info: dict five, seven, five_long, five_abs, seven_long, seven_abs"""
        self._info = dict(info)
        if self._thread:
            self._q.put(("info", self._info))

    def set_anchor(self, anchor):
        """Đổi điểm neo từ bên ngoài (vd. menu tray). Không gọi lại on_anchor."""
        if anchor in ANCHOR_KEYS:
            self._anchor = anchor
            if self._thread:
                self._q.put(("anchor", anchor))

    def stop(self):
        if self._thread:
            self._q.put(("stop", None))

    # ---- nội bộ -----------------------------------------------------------------------
    def _start(self):
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._run_safely, daemon=True)
                self._thread.start()

    def _run_safely(self):
        try:
            self._run()
        except Exception as e:  # lỗi Tk/Win32... -> ghi ra log (stderr) rồi cho phép khởi động lại
            import traceback
            print("widget lỗi:", e, file=sys.stderr)
            traceback.print_exc()
        finally:
            with self._lock:
                self._thread = None
            self._shown = False

    def _call(self, name):
        cb = self._cb.get(name)
        if cb:
            cb()

    def _run(self):
        import tkinter as tk

        _enable_thread_dpi_awareness()  # phải gọi trước khi tạo cửa sổ Tk
        scale = _dpi_scale()
        cw, ch = round(CW * scale), round(CH * scale)

        root = tk.Tk()
        root.withdraw()
        root.overrideredirect(True)
        root.attributes("-topmost", True)

        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()

        def target_pos():
            """Vị trí cần có: theo điểm neo, hoặc (chế độ tự do) vị trí đã lưu / mặc định."""
            pos = _anchor_position(self._anchor, sw, sh, cw, ch, scale)
            if pos:
                return pos
            x, y = self._position or (None, None)
            if x is None or not (0 <= x <= sw - cw and 0 <= y <= sh - ch):
                return _default_position(sw, sh, cw, ch, scale)
            return x, y

        x, y = target_pos()
        root.geometry(f"{cw}x{ch}+{x}+{y}")
        root.update_idletasks()
        hwnd = _Win.hwnd(root)
        _Win.make_layered(hwnd, noactivate=False)

        current_theme = {"light": _taskbar_light()}
        compact = {"img": None, "light": None}

        def draw_compact(rerender=True):
            """rerender=False: chỉ đẩy lại ảnh đã vẽ (rẻ) -- dùng để 'vỗ về' DWM sau khi hiện cửa sổ."""
            is_light = current_theme["light"]
            if compact.get("light") != is_light:
                rerender = True
            if rerender or compact["img"] is None:
                compact["img"] = render_compact(self._info.get("five"), self._info.get("seven"),
                                                scale, light=is_light)
                compact["light"] = is_light
            ok = _Win.update(hwnd, compact["img"])
            _dbg("vẽ widget gọn:", "OK" if ok else f"THẤT BẠI (lỗi Win32 {ctypes.get_last_error()})")

        # ================= panel mở rộng =================
        fly = {"win": None, "hwnd": None, "rects": {}, "hover": None, "rect": None, "base": None, "light": None}
        # Menu Win32 chạy vòng lặp riêng nhưng bộ đếm giờ của Tk vẫn kích hoạt bên trong nó.
        # Cú bấm vào mục menu nằm ngoài panel -> poll_outside sẽ đóng panel và HUỶ menu trước khi
        # lệnh kịp chạy. Cờ này làm poll_outside đứng yên trong lúc có menu mở.
        menu_state = {"open": False}

        def show_menu(m, x_root, y_root):
            menu_state["open"] = True
            try:
                m.tk_popup(x_root, y_root)
            finally:
                m.grab_release()
                menu_state["open"] = False
                fly["was_down"] = True  # cú bấm vừa chọn menu đừng bị tính là "bấm ra ngoài"

        def fly_render(rebuild=True):
            """Ảnh panel hiện tại. rebuild=False: dùng lại ảnh nền đã vẽ, chỉ đổi lớp tô sáng hover."""
            is_light = current_theme["light"]
            if rebuild or fly["base"] is None or fly.get("light") != is_light:
                fly["base"], fly["rects"] = render_flyout(self._info, scale, self._show_abs, light=is_light)
                fly["light"] = is_light
            return apply_hover(fly["base"], fly["rects"], fly["hover"], scale, light=is_light)

        def open_flyout():
            if fly["win"] is not None:
                return
            win = tk.Toplevel(root)
            win.withdraw()
            win.overrideredirect(True)
            win.attributes("-topmost", True)
            img = fly_render()
            fw, fh = img.size
            off = round(FM * scale)
            pw = fw - 2 * off
            ph = fh - 2 * off
            l, t, r, b = _work_area(sw, sh)
            wx, wy = root.winfo_x(), root.winfo_y()
            gap = round(8 * scale)
            # Căn mép trái panel với widget nếu widget ở nửa trái màn hình, ngược lại căn mép phải
            if wx + cw / 2 < sw / 2:
                panel_x = wx
            else:
                panel_x = wx + cw - pw
            panel_x = min(max(panel_x, l + gap), r - pw - gap)
            # Widget ở nửa dưới -> mở lên trên (ngay trên taskbar); ở nửa trên -> mở xuống dưới
            if wy + ch / 2 >= sh / 2:
                panel_y = min(wy, b) - ph - gap
            else:
                panel_y = max(wy + ch, t) + gap
            panel_y = min(max(panel_y, t + gap), b - ph - gap)
            win.geometry(f"{fw}x{fh}+{panel_x - off}+{panel_y - off}")
            win.update_idletasks()
            fhwnd = _Win.hwnd(win)
            _Win.make_layered(fhwnd)
            _Win.update(fhwnd, img)         # nội dung trước, rồi mới hiện (xem ghi chú ở tick)
            win.deiconify()
            win.after(150, lambda: fly["win"] is win and _Win.update(fhwnd, fly_render(rebuild=False)))
            fly.update(win=win, hwnd=fhwnd, hover=None,
                       rect=(panel_x - off, panel_y - off, panel_x - off + fw, panel_y - off + fh))
            win.bind("<Motion>", fly_motion)
            win.bind("<Leave>", lambda e: set_hover(None))
            win.bind("<ButtonRelease-1>", fly_click)
            root.after(60, poll_outside)

        def close_flyout():
            win = fly["win"]
            _dbg("close_flyout, đang mở =", win is not None)
            if win is None:
                return
            fly.update(win=None, hwnd=None, hover=None)
            try:
                win.destroy()
            except Exception:
                pass

        def fly_refresh_image():
            if fly["win"] is not None:
                _Win.update(fly["hwnd"], fly_render())

        def hit(ex, ey):
            for name, (x0, y0, x1, y1) in fly["rects"].items():
                if x0 <= ex < x1 and y0 <= ey < y1:
                    return name
            return None

        def set_hover(name):
            if name != fly["hover"] and fly["win"] is not None:
                fly["hover"] = name
                _Win.update(fly["hwnd"], fly_render(rebuild=False))

        def fly_motion(e):
            n = hit(e.x, e.y)
            set_hover(n if n in ("header", "refresh", "update", "settings") else None)

        def move_to_target():
            x, y = target_pos()
            if (x, y) != (root.winfo_x(), root.winfo_y()):
                _dbg("di chuyển widget", (root.winfo_x(), root.winfo_y()), "->", (x, y),
                     "neo =", self._anchor)
                root.geometry(f"+{x}+{y}")
                root.update_idletasks()
                _dbg("vị trí thật của cửa sổ sau khi dời:", _Win.rect(hwnd))

        def apply_anchor(new, notify=True):
            """Đổi điểm neo. notify=False khi thay đổi đến từ bên ngoài (app đã biết rồi)."""
            _dbg("apply_anchor", new, "notify =", notify)
            self._anchor = new
            close_flyout()
            if new == "free":
                # giữ nguyên chỗ đang đứng để widget không bị nhảy; coi đó là vị trí tự do đã lưu
                cur = (root.winfo_x(), root.winfo_y())
                self._position = cur
                if notify and self._cb.get("move"):
                    self._cb["move"](cur)
            else:
                move_to_target()
            if notify and self._cb.get("anchor"):
                self._cb["anchor"](new)

        def add_anchor_menu(m):
            sub = tk.Menu(m, tearoff=0, font=MENU_FONT)
            var = tk.StringVar(master=root, value=self._anchor)
            m._anchor_var = var  # giữ tham chiếu kẻo biến bị thu hồi khi menu còn mở
            for key, label in ANCHORS:
                sub.add_radiobutton(label=label, variable=var, value=key,
                                    command=lambda k=key: apply_anchor(k))
            m.add_cascade(label="Điểm neo", menu=sub)

        def settings_menu(x_root, y_root):
            m = tk.Menu(root, tearoff=0, font=MENU_FONT)

            def later(name):  # đóng panel rồi chạy việc (việc nặng do app tự đưa sang thread khác)
                return lambda: (close_flyout(), self._call(name))

            m.add_command(label="Đăng nhập claude.ai…", command=later("login"))
            m.add_command(label="Nhập sessionKey…", command=later("session_key"))
            m.add_separator()
            add_anchor_menu(m)
            m.add_command(label=f"Cập nhật từ GitHub (v{WIDGET_VERSION})…",
                          command=lambda: (close_flyout(), ui.show_update_dialog(root, "claude", "Claude Usage Bar", WIDGET_DIR)))
            if self._cb.get("autostart_status") and self._cb.get("autostart_toggle"):
                lbl = "Khởi động cùng Windows" if sys.platform == "win32" else "Khởi động cùng hệ thống"
                auto_var = tk.BooleanVar(master=root, value=bool(self._cb["autostart_status"]()))
                m._auto_var = auto_var
                m.add_checkbutton(label=lbl, variable=auto_var,
                                  command=lambda: (close_flyout(), self._call("autostart_toggle")))
            def on_menu_quit():
                close_flyout()
                try:
                    root.withdraw()
                except Exception:
                    pass
                try:
                    root.quit()
                except Exception:
                    pass
                self._call("quit")

            m.add_command(label="Ẩn widget", command=lambda: (close_flyout(), hide_cmd()))
            m.add_command(label="Thoát", command=on_menu_quit)
            show_menu(m, x_root, y_root)

        def fly_click(e):
            n = hit(e.x, e.y)
            if n == "header":
                webbrowser.open(USAGE_URL)
                close_flyout()
            elif n in ("reset_five", "reset_seven"):
                self._show_abs = not self._show_abs
                fly_refresh_image()
            elif n == "refresh":
                self._call("refresh")
            elif n == "update":
                close_flyout()
                ui.show_update_dialog(root, "claude", "Claude Usage Bar", WIDGET_DIR)
            elif n == "settings":
                settings_menu(e.x_root, e.y_root)

        def poll_outside():
            """Bấm chuột ra ngoài panel/widget -> đóng panel."""
            if fly["win"] is None:
                return
            if menu_state["open"]:          # đang có menu mở: không xử lý "bấm ra ngoài"
                root.after(60, poll_outside)
                return
            cur = _cursor_and_button()
            if cur:
                cx, cy, down = cur
                if down and not fly.get("was_down"):
                    fx0, fy0, fx1, fy1 = fly["rect"]
                    in_fly = fx0 <= cx < fx1 and fy0 <= cy < fy1
                    in_wid = (root.winfo_x() <= cx < root.winfo_x() + cw
                              and root.winfo_y() <= cy < root.winfo_y() + ch)
                    if not in_fly and not in_wid:
                        close_flyout()
                        return
                fly["was_down"] = down
            root.after(60, poll_outside)

        def toggle_flyout():
            if fly["win"] is None:
                fly["was_down"] = True  # lần bấm này đang diễn ra, đừng tính là "bấm ra ngoài"
                open_flyout()
            else:
                close_flyout()

        # ================= tương tác widget gọn =================
        def hide_cmd():
            self._wanted = False
            self._call("hide")

        drag = {}

        def press(e):
            _dbg("press", e.x_root, e.y_root)
            drag.update(sx=e.x_root, sy=e.y_root, dx=e.x_root - root.winfo_x(),
                        dy=e.y_root - root.winfo_y(), moved=False)

        def motion(e):
            if not drag:
                _dbg("motion bỏ qua (chưa có press)")
                return
            if not drag["moved"] and max(abs(e.x_root - drag["sx"]), abs(e.y_root - drag["sy"])) < CLICK_SLOP:
                return
            if self._anchor != "free":
                # đã neo vào góc -> khoá, không dời widget; nhưng thử kéo thì không phải cú bấm
                drag["dragged_locked"] = True
                return
            if not drag["moved"]:
                close_flyout()
            drag["moved"] = True
            root.geometry(f"+{e.x_root - drag['dx']}+{e.y_root - drag['dy']}")
            root.update_idletasks()  # Tk hay trì hoãn geometry tới lúc rảnh -> ép áp dụng ngay

        def release(_e):
            _dbg("release moved=", drag.get("moved"), "drag=", bool(drag))
            if not drag:
                return
            if drag["moved"]:
                cb = self._cb.get("move")
                if cb:
                    cb((root.winfo_x(), root.winfo_y()))
            elif not drag.get("dragged_locked"):
                toggle_flyout()
            drag.clear()

        def popup_small(e):
            m = tk.Menu(root, tearoff=0, font=MENU_FONT)
            if self._cb.get("refresh"):
                m.add_command(label="Làm mới ngay", command=lambda: self._call("refresh"))
            m.add_command(label=f"Cập nhật từ GitHub (v{WIDGET_VERSION})…",
                          command=lambda: (close_flyout(), ui.show_update_dialog(root, "claude", "Claude Usage Bar", WIDGET_DIR)))
            add_anchor_menu(m)
            if self._cb.get("autostart_status") and self._cb.get("autostart_toggle"):
                lbl = "Khởi động cùng Windows" if sys.platform == "win32" else "Khởi động cùng hệ thống"
                auto_var = tk.BooleanVar(master=root, value=bool(self._cb["autostart_status"]()))
                m._auto_var = auto_var
                m.add_checkbutton(label=lbl, variable=auto_var,
                                  command=lambda: self._call("autostart_toggle"))
            m.add_command(label="Ẩn widget", command=hide_cmd)
            show_menu(m, e.x_root, e.y_root)

        root.bind("<ButtonPress-1>", press)
        root.bind("<B1-Motion>", motion)
        root.bind("<ButtonRelease-1>", release)
        root.bind("<Button-3>", popup_small)

        # ---- vòng lặp: xử lý lệnh, giữ cửa sổ nổi trên taskbar, ẩn khi toàn màn hình ----
        tick_n = {"n": 0}
        kick = {"fg": None, "n": 0}

        def tick():
            redraw = False
            # Tự động phát hiện khi Windows đổi giao diện Sáng / Tối trong thời gian thực
            is_light = _taskbar_light()
            if is_light != current_theme["light"]:
                _dbg("Theme hệ thống thay đổi -> chuyển sang:", "Sáng" if is_light else "Tối")
                current_theme["light"] = is_light
                compact["img"] = None
                if fly["win"] is not None:
                    fly["base"] = None
                    fly_refresh_image()
                redraw = True

            try:
                while True:
                    cmd, arg = self._q.get_nowait()
                    if cmd == "show":
                        self._wanted = True
                    elif cmd == "hide":
                        self._wanted = False
                    elif cmd == "info":
                        redraw = True
                    elif cmd == "anchor":
                        apply_anchor(arg, notify=False)
                    elif cmd == "stop":
                        root.destroy()
                        return
            except queue.Empty:
                pass
            fs = _foreground_fullscreen()
            if fs != self._last_fs:
                _dbg("toàn màn hình ở foreground =", fs)
                self._last_fs = fs
            if self._wanted and not fs:
                if not self._shown:
                    _dbg("hiện widget")
                    draw_compact()          # đặt nội dung TRƯỚC khi hiện: tránh lúc được lúc mất do đua với DWM
                    root.deiconify()
                    self._shown = True
                    redraw = False
                    root.after(150, lambda: draw_compact(rerender=False))   # đẩy lại sau khi cửa sổ đã hiện
                    root.after(600, lambda: draw_compact(rerender=False))
                if _Win.ok:
                    # Kéo lên lại khi cửa sổ đang dùng đổi (Start mở/đóng, bấm icon taskbar...) và định kỳ
                    # ~3 s. SetWindowPos không kích hoạt cửa sổ; không làm mỗi tick để khỏi giành z-order
                    # với taskbar (gây nháy khi bấm icon).
                    fg = _Win.u32.GetForegroundWindow()
                    kick["n"] += 1
                    owner_changed = _Win.own_by_taskbar(_Win.hwnd(root))   # explorer khởi động lại -> HWND mới
                    if owner_changed or fg != kick["fg"] or kick["n"] % 8 == 0:
                        kick["fg"] = fg
                        _Win.u32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p] + [ctypes.c_int] * 5
                        _Win.u32.SetWindowPos(_Win.hwnd(root), -1, 0, 0, 0, 0, 0x1 | 0x2 | 0x10)  # TOPMOST|NOSIZE|NOMOVE|NOACTIVATE
                        # DWM có thể bỏ nội dung cửa sổ nhiều lớp khi Start che qua -> đẩy hình lại
                        draw_compact(rerender=False)
                        root.after(200, lambda: draw_compact(rerender=False))
                        root.after(700, lambda: draw_compact(rerender=False))
                else:
                    root.attributes("-topmost", True)
                    root.lift()
                # Đã neo: tự đặt lại đúng góc khi bố cục đổi (taskbar, độ phân giải, độ rộng khay...)
                tick_n["n"] += 1
                if self._anchor != "free" and tick_n["n"] % 5 == 0 and fly["win"] is None:
                    move_to_target()
                if redraw:
                    draw_compact()
                    fly_refresh_image()
            elif self._shown:
                _dbg("ẩn widget (wanted=", self._wanted, ", fullscreen=", fs, ")")
                close_flyout()
                root.withdraw()
                self._shown = False
            root.after(TICK_MS, tick)

        root.after(50, tick)
        root.mainloop()
