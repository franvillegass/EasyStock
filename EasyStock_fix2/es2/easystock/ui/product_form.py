"""
EasyStock — formulario de producto (PyQt6).
"""
import sqlite3
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QWidget, QMessageBox,
    QScrollArea, QFrame, QCheckBox,
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
        self._checks: dict[int, QCheckBox] = {}

        is_new = producto is None
        self.setWindowTitle("EasyStock — " + ("Nuevo Producto" if is_new else "Editar Producto"))
        self.setFixedSize(480, 540)
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
        title.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {accent}; "
            f"background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(title)
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Formulario
        body = QWidget()
        body.setStyleSheet("background: transparent;")
        form_lay = QFormLayout(body)
        form_lay.setContentsMargins(24, 20, 24, 8)
        form_lay.setSpacing(14)
        form_lay.setLabelAlignment(Qt.AlignmentFlag.AlignLeft)

        def mk_label(text):
            l = QLabel(text)
            l.setStyleSheet(
                f"color: {C['text_dim']}; font-size: 9px; "
                f"font-weight: bold; letter-spacing: 1px;")
            return l

        self.f_codigo = QLineEdit()
        self.f_codigo.setPlaceholderText("ej: 7790001234567 (opcional)")
        self.f_nombre = QLineEdit()
        self.f_nombre.setPlaceholderText("ej: Agua mineral 500ml")
        self.f_stock  = QLineEdit()
        self.f_stock.setPlaceholderText("ej: 100")
        self.f_precio = QLineEdit()
        self.f_precio.setPlaceholderText("ej: 450.00")

        form_lay.addRow(mk_label("CODIGO DE BARRAS"), self.f_codigo)
        form_lay.addRow(mk_label("NOMBRE"),           self.f_nombre)
        form_lay.addRow(mk_label("STOCK INICIAL"),    self.f_stock)
        form_lay.addRow(mk_label("PRECIO UNITARIO"),  self.f_precio)
        root.addWidget(body)

        # Categorias header
        cat_header = QWidget()
        cat_header.setStyleSheet(f"background: {C['bg_input']};")
        cat_header.setFixedHeight(28)
        cat_h_lay = QHBoxLayout(cat_header)
        cat_h_lay.setContentsMargins(24, 0, 24, 0)
        lbl_cat = QLabel("CATEGORIAS")
        lbl_cat.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold; "
            f"letter-spacing: 1px; background: transparent;")
        cat_h_lay.addWidget(lbl_cat)
        root.addWidget(cat_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setFixedHeight(140)
        scroll.setStyleSheet(f"background: {C['bg_panel']};")

        cat_widget = QWidget()
        cat_widget.setStyleSheet(f"background: {C['bg_panel']};")
        cat_inner = QVBoxLayout(cat_widget)
        cat_inner.setContentsMargins(24, 8, 24, 8)
        cat_inner.setSpacing(6)

        categorias = self.db.list_categorias()
        mid = (len(categorias) + 1) // 2
        cols_lay = QHBoxLayout()
        cols_lay.setSpacing(16)
        col1 = QVBoxLayout()
        col1.setSpacing(6)
        col2 = QVBoxLayout()
        col2.setSpacing(6)

        cb_style = f"""
            QCheckBox {{
                color: {C['text_hi']}; font-size: 11px;
                spacing: 8px; background: transparent;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 2px solid {C['border_lit']};
                border-radius: 3px;
                background: {C['bg_input']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['amber_dim']};
                border-color: {C['amber']};
            }}
        """
        for i, cat in enumerate(categorias):
            cb = QCheckBox(cat["nombre"])
            cb.setStyleSheet(cb_style)
            self._checks[cat["id"]] = cb
            if i < mid:
                col1.addWidget(cb)
            else:
                col2.addWidget(cb)

        col1.addStretch()
        col2.addStretch()
        cols_lay.addLayout(col1)
        cols_lay.addLayout(col2)
        cat_inner.addLayout(cols_lay)
        scroll.setWidget(cat_widget)
        root.addWidget(scroll)
        root.addWidget(h_sep())

        # Botones
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(24, 12, 24, 16)
        foot_lay.setSpacing(8)

        btn_save   = make_btn("GUARDAR",  "primary", min_w=150, h=38)
        btn_cancel = make_btn("CANCELAR", "ghost",   min_w=120, h=38)
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
        cats_actuales = {c["id"] for c in self.db.get_categorias_producto(p["id"])}
        for cid, cb in self._checks.items():
            cb.setChecked(cid in cats_actuales)

    def _get_categoria_ids(self) -> list[int]:
        return [cid for cid, cb in self._checks.items() if cb.isChecked()]

    def _on_save(self):
        codigo   = self.f_codigo.text().strip() or None
        nombre   = self.f_nombre.text().strip()
        stock_s  = self.f_stock.text().strip() or "0"
        precio_s = self.f_precio.text().strip() or "0"

        if not nombre:
            QMessageBox.critical(self, "Error", "El nombre no puede estar vacio.")
            return
        try:
            stock_i  = int(stock_s)
            precio_f = float(precio_s)
        except ValueError:
            QMessageBox.critical(self, "Error", "Stock debe ser entero y precio numerico.")
            return
        if stock_i < 0 or precio_f < 0:
            QMessageBox.critical(self, "Error", "Stock y precio deben ser >= 0.")
            return

        cat_ids = self._get_categoria_ids()

        try:
            if self.producto:
                self.db.update_producto(
                    self.producto["id"], nombre, stock_i, precio_f,
                    codigo, categoria_ids=cat_ids)
            else:
                self.db.add_producto(
                    nombre, stock_i, precio_f, self.tienda_id,
                    codigo, categoria_ids=cat_ids)
        except sqlite3.IntegrityError:
            QMessageBox.critical(
                self, "Error", "Ya existe un producto con ese codigo de barras.")
            return

        if self.callback:
            self.callback()
        self.accept()