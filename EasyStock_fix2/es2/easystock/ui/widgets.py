"""
EasyStock — widgets base (PyQt6).

Todos los elementos con bordes redondeados usan paintEvent + QPainter
con RenderHint.Antialiasing. Nunca border-radius en QSS para widgets
que necesitan bordes suaves — eso produce pixelado.
"""
from PyQt6.QtWidgets import (
    QPushButton, QLabel, QFrame, QWidget, QHBoxLayout,
    QVBoxLayout, QGraphicsOpacityEffect, QSizePolicy,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    QPoint, QTimer, QRectF,
)
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QBrush, QPainterPath,
)
from easystock.config import C


# ── Helpers ───────────────────────────────────────────────────────────────────
def make_label(text: str, role: str = "") -> QLabel:
    lbl = QLabel(text)
    if role:
        lbl.setProperty("role", role)
    return lbl


def h_sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Plain)
    f.setFixedHeight(1)
    f.setStyleSheet(f"background: {C['border']}; border: none; margin: 0;")
    return f


def v_sep() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.VLine)
    f.setFrameShadow(QFrame.Shadow.Plain)
    f.setFixedWidth(1)
    f.setStyleSheet(f"background: {C['border']}; border: none; margin: 0;")
    return f


# ── Barra de acento ───────────────────────────────────────────────────────────
class AccentBar(QWidget):
    """Barra vertical sólida de 4px, sin radius — rectángulo puro."""
    def __init__(self, color: str = None, parent=None):
        super().__init__(parent)
        self._color = QColor(color or C["amber"])
        self.setFixedWidth(4)

    def paintEvent(self, _):
        p = QPainter(self)
        p.fillRect(self.rect(), self._color)


# ── Botón con AA ──────────────────────────────────────────────────────────────
_VARIANTS = {
    "primary": (C["amber_dim"],  C["amber"],     C["amber_glow"], C["bg_deep"],  C["amber"]),
    "ghost":   (C["bg_card"],    C["bg_hover"],  C["bg_select"],  C["text_hi"],  C["border"]),
    "danger":  (C["red_dim"],    C["red"],       "#c0392b",       C["text_hi"],  C["red"]),
    "success": (C["green_dim"],  C["green"],     "#27ae60",       C["bg_deep"],  C["green"]),
}
# tupla: (bg, bg_hover, bg_press, fg, border)


class RoundButton(QPushButton):
    """
    Botón con esquinas redondeadas, hover animado y AA.
    No depende de border-radius en QSS.
    """
    R = 7  # radio

    def __init__(self, text: str = "", variant: str = "ghost", parent=None):
        super().__init__(parent)
        self.setText(text)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        # Sin ningún estilo QSS de fondo — todo va a paintEvent
        self.setStyleSheet("QPushButton { background: transparent; border: none; color: transparent; }")

        bg, bg_h, bg_p, fg, bdr = _VARIANTS.get(variant, _VARIANTS["ghost"])
        self._c_bg    = QColor(bg)
        self._c_hover = QColor(bg_h)
        self._c_press = QColor(bg_p)
        self._c_fg    = QColor(fg)
        self._c_bdr   = QColor(bdr)
        self._cur_bg  = QColor(bg)
        self._hovered = False

        # Animación de fondo (timer manual, 60fps aprox)
        self._tmr = QTimer(self)
        self._tmr.setInterval(12)
        self._tmr.timeout.connect(self._step)
        self._from = QColor(bg)
        self._to   = QColor(bg)
        self._t    = 1.0

    # ── color lerp ──
    @staticmethod
    def _lerp(a: QColor, b: QColor, t: float) -> QColor:
        t = max(0.0, min(1.0, t))
        return QColor(
            int(a.red()   + (b.red()   - a.red())   * t),
            int(a.green() + (b.green() - a.green()) * t),
            int(a.blue()  + (b.blue()  - a.blue())  * t),
        )

    def _anim_to(self, target: QColor):
        self._from = QColor(self._cur_bg)
        self._to   = target
        self._t    = 0.0
        self._tmr.start()

    def _step(self):
        self._t += 0.14
        t_e = 1 - (1 - min(self._t, 1.0)) ** 2
        self._cur_bg = self._lerp(self._from, self._to, t_e)
        self.update()
        if self._t >= 1.0:
            self._tmr.stop()

    # ── eventos ──
    def enterEvent(self, e):
        super().enterEvent(e)
        self._hovered = True
        self._anim_to(self._c_hover)

    def leaveEvent(self, e):
        super().leaveEvent(e)
        self._hovered = False
        self._anim_to(self._c_bg)

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self._cur_bg = self._c_press
        self._tmr.stop()
        self.update()

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        self._anim_to(self._c_hover if self._hovered else self._c_bg)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, self.R, self.R)

        p.fillPath(path, QBrush(self._cur_bg))
        p.setPen(QPen(self._c_bdr, 1.0))
        p.drawPath(path)

        p.setPen(QPen(self._c_fg))
        f = self.font()
        f.setBold(True)
        p.setFont(f)
        p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())


def make_btn(text: str, variant: str = "ghost",
             min_w: int = 0, h: int = 36) -> RoundButton:
    btn = RoundButton(text, variant)
    if min_w:
        btn.setMinimumWidth(min_w)
    btn.setFixedHeight(h)
    return btn


# ── Card genérica con AA ──────────────────────────────────────────────────────
class Card(QWidget):
    """Contenedor con fondo y borde redondeado pintados con AA."""
    R = 8

    def __init__(self, bg: str = None, border: str = None, parent=None):
        super().__init__(parent)
        self._bg  = QColor(bg or C["bg_card"])
        self._bdr = QColor(border or C["border"])
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._root_layout = QVBoxLayout(self)
        self._root_layout.setContentsMargins(0, 0, 0, 0)
        self._root_layout.setSpacing(0)

    @property
    def root_layout(self) -> QVBoxLayout:
        return self._root_layout

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, self.R, self.R)
        p.fillPath(path, QBrush(self._bg))
        p.setPen(QPen(self._bdr, 1.0))
        p.drawPath(path)


# ── KPI Card ──────────────────────────────────────────────────────────────────
class KPICard(QWidget):
    """
    Card de métrica: borde redondeado AA + barra izquierda de acento.
    Anima el valor numérico con ease-out cubic.
    """
    R = 8

    def __init__(self, label: str, accent: str = None, parent=None):
        super().__init__(parent)
        self._accent_str = accent or C["amber"]
        self._bg   = QColor(C["bg_card"])
        self._bdr  = QColor(C["border"])
        self._acc  = QColor(self._accent_str)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMinimumSize(160, 82)

        # Animación numérica
        self._target = 0.0
        self._prefix = ""
        self._suffix = ""
        self._dec    = 0
        self._step   = 0
        self._steps  = 28
        self._tmr    = QTimer(self)
        self._tmr.setInterval(16)
        self._tmr.timeout.connect(self._tick)

        inner = QVBoxLayout(self)
        inner.setContentsMargins(20, 12, 16, 12)
        inner.setSpacing(3)

        self._lbl_l = QLabel(label.upper())
        self._lbl_l.setStyleSheet(f"""
            color: {C['text_dim']}; font-size: 9px;
            font-weight: bold; letter-spacing: 1px;
            background: transparent;
        """)
        self._lbl_v = QLabel("—")
        self._lbl_v.setStyleSheet(f"""
            color: {self._accent_str}; font-size: 22px;
            font-weight: bold; background: transparent;
        """)
        inner.addWidget(self._lbl_l)
        inner.addWidget(self._lbl_v)

    def set_value(self, text: str):
        self._lbl_v.setText(text)

    def animate_to(self, target: float, prefix="", suffix="", decimals=0):
        self._target = target
        self._prefix = prefix
        self._suffix = suffix
        self._dec    = decimals
        self._step   = 0
        self._tmr.start()

    def _tick(self):
        self._step += 1
        t_e = 1 - (1 - self._step / self._steps) ** 3
        val = self._target * t_e
        self._lbl_v.setText(f"{self._prefix}{val:,.{self._dec}f}{self._suffix}")
        if self._step >= self._steps:
            self._tmr.stop()
            self._lbl_v.setText(
                f"{self._prefix}{self._target:,.{self._dec}f}{self._suffix}")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        # Fondo redondeado
        path = QPainterPath()
        path.addRoundedRect(r, self.R, self.R)
        p.fillPath(path, QBrush(self._bg))
        p.setPen(QPen(self._bdr, 1.0))
        p.drawPath(path)

        # Barra izquierda de acento (sin radius — recta en el interior)
        bar_w = 3
        bar_h = r.height() - self.R * 2
        p.fillRect(QRectF(r.x(), r.y() + self.R, bar_w, bar_h),
                   QBrush(self._acc))


# ── Section Panel ─────────────────────────────────────────────────────────────
class SectionPanel(QWidget):
    """
    Panel con borde redondeado AA, barra superior de acento (3px),
    header con título y cuerpo expandible.
    """
    R = 8

    def __init__(self, title: str, accent: str = None,
                 icon: str = "", parent=None):
        super().__init__(parent)
        self._bg    = QColor(C["bg_card"])
        self._bdr   = QColor(C["border"])
        self._acc   = QColor(accent or C["amber"])
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Espacio superior para la barra de acento (3px pintada en paintEvent)
        spacer_top = QWidget()
        spacer_top.setFixedHeight(3)
        spacer_top.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        root.addWidget(spacer_top)

        hdr = QWidget()
        hdr.setFixedHeight(36)
        hdr.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(14, 0, 14, 0)

        lbl = QLabel(f"{icon}  {title}" if icon else title)
        lbl.setStyleSheet(f"""
            font-size: 11px; font-weight: bold;
            color: {accent or C['amber']};
            letter-spacing: 1px; background: transparent;
        """)
        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()
        root.addWidget(hdr)

        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet(f"background: {C['border']};")
        root.addWidget(sep)

        self.body = QWidget()
        self.body.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._body_layout = QVBoxLayout(self.body)
        self._body_layout.setContentsMargins(12, 10, 12, 12)
        self._body_layout.setSpacing(8)
        root.addWidget(self.body, 1)

    @property
    def layout_body(self) -> QVBoxLayout:
        return self._body_layout

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)

        path = QPainterPath()
        path.addRoundedRect(r, self.R, self.R)
        p.fillPath(path, QBrush(self._bg))
        p.setPen(QPen(self._bdr, 1.0))
        p.drawPath(path)

        # Barra superior (3px, redondeada solo arriba)
        top = QPainterPath()
        top.addRoundedRect(QRectF(r.x(), r.y(), r.width(), self.R * 2),
                           self.R, self.R)
        clip = QPainterPath()
        clip.addRect(QRectF(r.x(), r.y(), r.width(), 3))
        p.fillPath(clip.intersected(top), QBrush(self._acc))


# ── Toast ─────────────────────────────────────────────────────────────────────
class Toast(QWidget):
    _COLORS = {"info": C["blue"], "success": C["green"],
               "error": C["red"], "warning": C["amber"]}
    _ICONS  = {"info": "ℹ", "success": "✓",
               "error": "✕", "warning": "⚠"}

    def __init__(self, message: str, kind: str = "info", parent=None):
        super().__init__(parent,
                         Qt.WindowType.ToolTip |
                         Qt.WindowType.FramelessWindowHint |
                         Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        color = self._COLORS.get(kind, C["blue"])
        icon  = self._ICONS.get(kind, "ℹ")
        self._bdr = QColor(color)
        self._bg  = QColor(C["bg_card"])

        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 12, 16, 12)
        lay.setSpacing(10)
        lay.addWidget(QLabel(icon,
            styleSheet=f"color:{color};font-size:14px;font-weight:bold;background:transparent;"))
        lay.addWidget(QLabel(message,
            styleSheet=f"color:{C['text_hi']};font-size:11px;background:transparent;"))
        self.adjustSize()

        fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(fx)
        fx.setOpacity(0)

        self._ain = QPropertyAnimation(fx, b"opacity", self)
        self._ain.setDuration(200); self._ain.setStartValue(0.0)
        self._ain.setEndValue(0.94)
        self._ain.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._aout = QPropertyAnimation(fx, b"opacity", self)
        self._aout.setDuration(280); self._aout.setStartValue(0.94)
        self._aout.setEndValue(0.0)
        self._aout.setEasingCurve(QEasingCurve.Type.InCubic)
        self._aout.finished.connect(self.deleteLater)

        self._tmr = QTimer(self)
        self._tmr.setSingleShot(True)
        self._tmr.timeout.connect(self._aout.start)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5)
        path = QPainterPath()
        path.addRoundedRect(r, 8, 8)
        p.fillPath(path, QBrush(self._bg))
        p.setPen(QPen(self._bdr, 1.5))
        p.drawPath(path)

    def show_for(self, ms: int = 2800):
        self.show()
        self._ain.start()
        self._tmr.start(ms)


def show_toast(message: str, kind: str = "info",
               parent=None, duration_ms: int = 2800):
    t = Toast(message, kind, parent)
    if parent:
        t.adjustSize()
        t.move(parent.mapToGlobal(
            QPoint(parent.width()  - t.width()  - 22,
                   parent.height() - t.height() - 26)))
    t.show_for(duration_ms)
