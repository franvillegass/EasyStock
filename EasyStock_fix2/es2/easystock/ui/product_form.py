"""
EasyStock — formulario de producto (PyQt6).
"""
import sqlite3
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QWidget, QMessageBox,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import make_btn, h_sep, AccentBar


class ProductFormDialog(QDialog):
    def __init__(self, parent, db: DBManager, tienda_id: int,
                 producto: dict | None = None, callback=None):
        super().__init__(parent)
        self.db        = db
        self.tienda_id = tienda_id
        self.producto  = producto
        self.callback  = callback

        is_new = producto is None
        self.setWindowTitle("EasyStock — " + ("Nuevo Producto" if is_new else "Editar Producto"))
        self.setFixedSize(460, 420)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._build(is_new)
        if not is_new:
            self._prefill()
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

    def _build(self, is_new: bool):
        accent = C["amber"] if is_new else C["blue"]
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
        hdr_lay.addWidget(AccentBar(accent))
        title_text = "  NUEVO PRODUCTO" if is_new else "  EDITAR PRODUCTO"
        title = QLabel(title_text)
        title.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {accent}; background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(title)
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Formulario
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        form_lay = QFormLayout(body)
        form_lay.setContentsMargins(24, 20, 24, 16)
        form_lay.setSpacing(14)
        form_lay.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        def mk_label(text):
            l = QLabel(text)
            l.setStyleSheet(f"color: {C['text_dim']}; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
            return l

        self.f_codigo = QLineEdit()
        self.f_codigo.setPlaceholderText("ej: 7790001234567 (opcional)")
        self.f_nombre = QLineEdit()
        self.f_nombre.setPlaceholderText("ej: Agua mineral 500ml")
        self.f_stock  = QLineEdit()
        self.f_stock.setPlaceholderText("ej: 100")
        self.f_precio = QLineEdit()
        self.f_precio.setPlaceholderText("ej: 450.00")

        form_lay.addRow(mk_label("CÓDIGO DE BARRAS"), self.f_codigo)
        form_lay.addRow(mk_label("NOMBRE"),            self.f_nombre)
        form_lay.addRow(mk_label("STOCK INICIAL"),     self.f_stock)
        form_lay.addRow(mk_label("PRECIO UNITARIO"),   self.f_precio)

        root.addWidget(body, 1)
        root.addWidget(h_sep())

        # Botones
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(24, 12, 24, 16)
        foot_lay.setSpacing(8)

        btn_save   = make_btn("GUARDAR",   "primary", min_w=150, h=38)
        btn_cancel = make_btn("CANCELAR",  "ghost",   min_w=120, h=38)
        btn_save.clicked.connect(self._on_save)
        btn_cancel.clicked.connect(self.reject)

        foot_lay.addWidget(btn_save)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_cancel)
        root.addWidget(foot)

    def _prefill(self):
        p = self.producto
        self.f_codigo.setText(p.get("codigo_barras") or "")
        self.f_nombre.setText(p["nombre"])
        self.f_stock.setText(str(p["stock"]))
        self.f_precio.setText(str(p["precio"]))

    def _on_save(self):
        codigo = self.f_codigo.text().strip() or None
        nombre = self.f_nombre.text().strip()
        stock_s  = self.f_stock.text().strip() or "0"
        precio_s = self.f_precio.text().strip() or "0"

        if not nombre:
            QMessageBox.critical(self, "Error", "El nombre no puede estar vacío.")
            return
        try:
            stock_i  = int(stock_s)
            precio_f = float(precio_s)
        except ValueError:
            QMessageBox.critical(self, "Error", "Stock debe ser entero y precio numérico.")
            return
        if stock_i < 0 or precio_f < 0:
            QMessageBox.critical(self, "Error", "Stock y precio deben ser ≥ 0.")
            return

        try:
            if self.producto:
                self.db.update_producto(
                    self.producto["id"], nombre, stock_i, precio_f, codigo)
            else:
                self.db.add_producto(
                    nombre, stock_i, precio_f, self.tienda_id, codigo)
        except sqlite3.IntegrityError:
            QMessageBox.critical(
                self, "Error", "Ya existe un producto con ese código de barras.")
            return

        if self.callback:
            self.callback()
        self.accept()