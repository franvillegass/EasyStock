"""
EasyStock — historial de ventas (PyQt6).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtGui import QColor, QTextCharFormat, QFont
from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import make_btn, h_sep, AccentBar


class HistoryWindow(QDialog):
    def __init__(self, parent, db: DBManager, tienda_id: int):
        super().__init__(parent)
        self.db        = db
        self.tienda_id = tienda_id
        self.ventas    = []

        self.setWindowTitle("EasyStock — Historial de Ventas")
        self.setMinimumSize(860, 540)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._build()
        self._load_ventas()
        self._animate_in()

    def _animate_in(self):
        fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", self)
        anim.setDuration(200)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(56)
        hdr.setStyleSheet(f"background: {C['bg_deep']};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        hdr_lay.setSpacing(0)
        hdr_lay.addWidget(AccentBar(C["blue"]))
        lbl = QLabel("  HISTORIAL DE VENTAS")
        lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {C['blue']}; background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(lbl)
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {C['border']}; }}")

        # Lista de ventas
        left = QWidget()
        left.setStyleSheet(f"background: {C['bg_card']};")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        left_hdr = QWidget()
        left_hdr.setFixedHeight(32)
        left_hdr.setStyleSheet(f"background: {C['bg_input']};")
        lh_lay = QHBoxLayout(left_hdr)
        lh_lay.setContentsMargins(14, 0, 14, 0)
        lbl_v = QLabel("VENTAS")
        lbl_v.setStyleSheet(f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        lh_lay.addWidget(lbl_v)
        left_lay.addWidget(left_hdr)

        self.list_ventas = QListWidget()
        self.list_ventas.setAlternatingRowColors(True)
        self.list_ventas.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_card']};
                border: none;
                outline: none;
            }}
            QListWidget::item {{
                padding: 9px 14px;
                border-bottom: 1px solid {C['border']};
                font-size: 11px;
            }}
            QListWidget::item:selected {{
                background: {C['bg_select']};
                color: {C['amber_glow']};
            }}
            QListWidget::item:hover:!selected {{
                background: {C['bg_hover']};
            }}
        """)
        self.list_ventas.currentRowChanged.connect(self._on_select)
        left_lay.addWidget(self.list_ventas, 1)
        splitter.addWidget(left)

        # Detalle
        right = QWidget()
        right.setStyleSheet(f"background: {C['bg_panel']};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        right_hdr = QWidget()
        right_hdr.setFixedHeight(32)
        right_hdr.setStyleSheet(f"background: {C['bg_input']};")
        rh_lay = QHBoxLayout(right_hdr)
        rh_lay.setContentsMargins(14, 0, 14, 0)
        lbl_d = QLabel("DETALLE")
        lbl_d.setStyleSheet(f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        rh_lay.addWidget(lbl_d)
        right_lay.addWidget(right_hdr)

        self.txt_detalle = QTextEdit()
        self.txt_detalle.setReadOnly(True)
        self.txt_detalle.setStyleSheet(f"""
            QTextEdit {{
                background: {C['bg_panel']};
                border: none;
                color: {C['text_hi']};
                padding: 12px;
                font-size: 12px;
            }}
        """)
        right_lay.addWidget(self.txt_detalle, 1)
        splitter.addWidget(right)

        splitter.setSizes([340, 500])
        root.addWidget(splitter, 1)
        root.addWidget(h_sep())

        # Footer
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(20, 10, 20, 16)

        btn_del   = make_btn("✕  ELIMINAR VENTA", "danger", min_w=180, h=38)
        btn_close = make_btn("CERRAR",            "ghost",  min_w=110, h=38)
        btn_del.clicked.connect(self._eliminar)
        btn_close.clicked.connect(self.accept)

        foot_lay.addWidget(btn_del)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_close)
        root.addWidget(foot)

    def _load_ventas(self):
        self.ventas = self.db.list_ventas(self.tienda_id)
        self.list_ventas.clear()
        for v in self.ventas:
            fecha = (v["fecha"] or "")[:16]
            item  = QListWidgetItem(f"  {fecha}   ${float(v['total']):>10,.2f}")
            item.setData(Qt.ItemDataRole.UserRole, v["id"])
            self.list_ventas.addItem(item)

    def _on_select(self, row: int):
        if row < 0 or row >= len(self.ventas):
            return
        venta = self.ventas[row]
        items = self.db.list_items_by_venta(venta["id"])
        fecha = (venta["fecha"] or "")[:16]

        self.txt_detalle.clear()
        cur = self.txt_detalle.textCursor()

        def append(text, color=None, bold=False, size=None):
            fmt = QTextCharFormat()
            if color:
                fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            if size:
                fmt.setFontPointSize(size)
            cur.insertText(text, fmt)

        append(f"Venta #{venta['id']}  —  {fecha}\n",
               color=C["amber"], bold=True, size=13)
        append("─" * 50 + "\n", color=C["text_dim"])

        total_calc = 0.0
        if items:
            for it in items:
                nombre = it["producto"][:30]
                qty    = it["cantidad"]
                sub    = float(it["subtotal"])
                append(f"  {nombre:<30}", color=C["text_hi"])
                append(f"  ×{qty}  ", color=C["text_mid"])
                append(f"${sub:,.2f}\n", color=C["text_hi"], bold=True)
                total_calc += sub
            append("─" * 50 + "\n", color=C["text_dim"])
            append(f"\n  TOTAL  ${total_calc:,.2f}\n",
                   color=C["green"], bold=True, size=14)
        else:
            append("  Sin ítems registrados.\n", color=C["text_dim"])

    def _eliminar(self):
        row = self.list_ventas.currentRow()
        if row < 0:
            return
        venta = self.ventas[row]
        fecha = (venta["fecha"] or "")[:16]
        r = QMessageBox.question(
            self, "Confirmar", f"¿Eliminar venta del {fecha}?")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_venta(venta["id"])
            self._load_ventas()
            self.txt_detalle.clear()
