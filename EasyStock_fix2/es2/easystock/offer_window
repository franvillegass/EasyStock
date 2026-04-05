"""
EasyStock — gestion de ofertas (PyQt6).
"""
from datetime import datetime
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QWidget, QMessageBox,
    QListWidget, QListWidgetItem, QScrollArea,
    QFrame, QCheckBox, QDateTimeEdit,
    QRadioButton, QButtonGroup,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QDateTime
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import make_btn, h_sep, AccentBar


class OfferWindow(QDialog):
    def __init__(self, parent, db: DBManager, tienda_id: int, callback=None):
        super().__init__(parent)
        self.db        = db
        self.tienda_id = tienda_id
        self.callback  = callback
        self._checks: dict[int, QCheckBox] = {}  # producto_id -> checkbox

        self.setWindowTitle("EasyStock — Ofertas")
        self.setMinimumSize(900, 580)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._productos = self.db.list_productos(tienda_id)
        self._ofertas   = []

        self._build()
        self._load_ofertas()
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

    # ── Layout ────────────────────────────────────────────────────────────────
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
        hdr_lay.addWidget(AccentBar(C["amber"]))
        lbl = QLabel("  GESTION DE OFERTAS")
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {C['amber']}; "
            f"background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(lbl)
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Splitter: ofertas existentes | formulario nueva oferta
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {C['border']}; }}")

        # Panel izquierdo — lista de ofertas
        left = QWidget()
        left.setStyleSheet(f"background: {C['bg_card']};")
        left_lay = QVBoxLayout(left)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        lhdr = QWidget()
        lhdr.setFixedHeight(32)
        lhdr.setStyleSheet(f"background: {C['bg_input']};")
        lh = QHBoxLayout(lhdr)
        lh.setContentsMargins(14, 0, 14, 0)
        lbl_o = QLabel("OFERTAS ACTIVAS")
        lbl_o.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        lh.addWidget(lbl_o)
        left_lay.addWidget(lhdr)

        self.list_ofertas = QListWidget()
        self.list_ofertas.setAlternatingRowColors(True)
        self.list_ofertas.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_card']}; border: none; outline: none;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {C['border']};
                font-size: 11px;
            }}
            QListWidget::item:selected {{
                background: {C['bg_select']}; color: {C['amber_glow']};
            }}
            QListWidget::item:hover:!selected {{
                background: {C['bg_hover']};
            }}
        """)
        self.list_ofertas.currentRowChanged.connect(self._on_oferta_select)
        left_lay.addWidget(self.list_ofertas, 1)

        # Boton eliminar
        del_row = QWidget()
        del_row.setStyleSheet(f"background: {C['bg_card']};")
        del_lay = QHBoxLayout(del_row)
        del_lay.setContentsMargins(12, 8, 12, 12)
        btn_del = make_btn("x  ELIMINAR OFERTA", "danger", min_w=160, h=36)
        btn_del.clicked.connect(self._eliminar)
        del_lay.addWidget(btn_del)
        del_lay.addStretch()
        left_lay.addWidget(del_row)
        splitter.addWidget(left)

        # Panel derecho — formulario
        right = QWidget()
        right.setStyleSheet(f"background: {C['bg_panel']};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        rhdr = QWidget()
        rhdr.setFixedHeight(32)
        rhdr.setStyleSheet(f"background: {C['bg_input']};")
        rh = QHBoxLayout(rhdr)
        rh.setContentsMargins(14, 0, 14, 0)
        lbl_n = QLabel("NUEVA OFERTA")
        lbl_n.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        rh.addWidget(lbl_n)
        right_lay.addWidget(rhdr)

        form = QWidget()
        form.setStyleSheet("background: transparent;")
        form_lay = QVBoxLayout(form)
        form_lay.setContentsMargins(20, 16, 20, 8)
        form_lay.setSpacing(12)

        def mk_lbl(text):
            l = QLabel(text)
            l.setStyleSheet(
                f"color: {C['text_dim']}; font-size: 9px; "
                f"font-weight: bold; letter-spacing: 1px;")
            return l

        # Nombre
        form_lay.addWidget(mk_lbl("NOMBRE DE LA OFERTA"))
        self.f_nombre = QLineEdit()
        self.f_nombre.setPlaceholderText("ej: Combo Desayuno")
        form_lay.addWidget(self.f_nombre)

        # Precio
        form_lay.addWidget(mk_lbl("PRECIO DE LA OFERTA"))
        self.f_precio = QLineEdit()
        self.f_precio.setPlaceholderText("ej: 1500.00")
        form_lay.addWidget(self.f_precio)

        # Expiracion
        form_lay.addWidget(mk_lbl("EXPIRACION"))
        exp_row = QHBoxLayout()
        exp_row.setSpacing(12)

        self._grp_exp = QButtonGroup(self)
        rb_style = f"""
            QRadioButton {{
                spacing: 6px; color: {C['text_mid']};
                font-size: 11px; font-weight: bold; background: transparent;
            }}
            QRadioButton:checked {{ color: {C['amber']}; }}
            QRadioButton::indicator {{
                width: 13px; height: 13px; border-radius: 7px;
                border: 2px solid {C['border_lit']}; background: {C['bg_input']};
            }}
            QRadioButton::indicator:checked {{
                border-color: {C['amber']}; background: {C['amber_dim']};
            }}
        """
        self.rb_sin_exp = QRadioButton("Sin vencimiento")
        self.rb_con_exp = QRadioButton("Vence el:")
        self.rb_sin_exp.setStyleSheet(rb_style)
        self.rb_con_exp.setStyleSheet(rb_style)
        self.rb_sin_exp.setChecked(True)
        self._grp_exp.addButton(self.rb_sin_exp)
        self._grp_exp.addButton(self.rb_con_exp)
        self.rb_sin_exp.toggled.connect(self._toggle_exp)
        exp_row.addWidget(self.rb_sin_exp)
        exp_row.addWidget(self.rb_con_exp)
        form_lay.addLayout(exp_row)

        self.dt_exp = QDateTimeEdit()
        self.dt_exp.setDisplayFormat("dd/MM/yyyy HH:mm")
        self.dt_exp.setMinimumDateTime(QDateTime.currentDateTime())
        self.dt_exp.setDateTime(QDateTime.currentDateTime().addDays(30))
        self.dt_exp.setEnabled(False)
        self.dt_exp.setStyleSheet(f"""
            QDateTimeEdit {{
                background: {C['bg_input']}; border: 1px solid {C['border']};
                border-radius: 6px; padding: 6px 10px; color: {C['text_hi']};
            }}
            QDateTimeEdit:disabled {{
                color: {C['text_dim']}; background: {C['bg_panel']};
            }}
            QDateTimeEdit::drop-down {{ border: none; width: 20px; }}
        """)
        form_lay.addWidget(self.dt_exp)

        # Selector de productos
        form_lay.addWidget(mk_lbl("PRODUCTOS (minimo 2)"))

        prod_scroll = QScrollArea()
        prod_scroll.setWidgetResizable(True)
        prod_scroll.setFrameShape(QFrame.Shape.NoFrame)
        prod_scroll.setStyleSheet(f"background: {C['bg_input']}; border-radius: 6px;")

        prod_widget = QWidget()
        prod_widget.setStyleSheet(f"background: {C['bg_input']};")
        prod_lay = QVBoxLayout(prod_widget)
        prod_lay.setContentsMargins(10, 8, 10, 8)
        prod_lay.setSpacing(5)

        cb_style = f"""
            QCheckBox {{
                color: {C['text_hi']}; font-size: 11px;
                spacing: 8px; background: transparent;
            }}
            QCheckBox::indicator {{
                width: 13px; height: 13px;
                border: 2px solid {C['border_lit']}; border-radius: 3px;
                background: {C['bg_card']};
            }}
            QCheckBox::indicator:checked {{
                background: {C['amber_dim']}; border-color: {C['amber']};
            }}
        """
        for p in self._productos:
            cb = QCheckBox(f"{p['nombre']}  (${p['precio']:.2f})")
            cb.setStyleSheet(cb_style)
            self._checks[p["id"]] = cb
            prod_lay.addWidget(cb)
        prod_lay.addStretch()
        prod_scroll.setWidget(prod_widget)
        form_lay.addWidget(prod_scroll, 1)

        right_lay.addWidget(form, 1)
        right_lay.addWidget(h_sep())

        # Boton guardar
        foot_r = QWidget()
        foot_r.setStyleSheet(f"background: {C['bg_panel']};")
        foot_r_lay = QHBoxLayout(foot_r)
        foot_r_lay.setContentsMargins(20, 10, 20, 16)
        btn_save = make_btn("+ CREAR OFERTA", "primary", min_w=160, h=38)
        btn_save.clicked.connect(self._crear)
        foot_r_lay.addStretch()
        foot_r_lay.addWidget(btn_save)
        right_lay.addWidget(foot_r)
        splitter.addWidget(right)

        splitter.setSizes([360, 520])
        root.addWidget(splitter, 1)
        root.addWidget(h_sep())

        # Footer global
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(20, 10, 20, 16)
        btn_close = make_btn("CERRAR", "ghost", min_w=110, h=38)
        btn_close.clicked.connect(self.accept)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_close)
        root.addWidget(foot)

    # ── Logica ────────────────────────────────────────────────────────────────
    def _toggle_exp(self, sin: bool):
        self.dt_exp.setEnabled(not sin)

    def _load_ofertas(self):
        self._ofertas = self.db.list_ofertas(self.tienda_id)
        self.list_ofertas.clear()
        for o in self._ofertas:
            exp = o["expira_at"][:16] if o["expira_at"] else "Sin vencimiento"
            prods = ", ".join(p["nombre"] for p in o["productos"])
            item = QListWidgetItem(
                f"  {o['nombre']}  —  ${o['precio']:.2f}\n"
                f"  Vence: {exp}\n"
                f"  {prods}")
            item.setData(Qt.ItemDataRole.UserRole, o["id"])
            self.list_ofertas.addItem(item)

    def _on_oferta_select(self, row: int):
        pass  # seleccion visual, no se editan

    def _crear(self):
        nombre  = self.f_nombre.text().strip()
        precio_s = self.f_precio.text().strip()

        if not nombre:
            QMessageBox.critical(self, "Error", "El nombre no puede estar vacio.")
            return
        try:
            precio_f = float(precio_s)
        except ValueError:
            QMessageBox.critical(self, "Error", "El precio debe ser numerico.")
            return
        if precio_f <= 0:
            QMessageBox.critical(self, "Error", "El precio debe ser mayor a 0.")
            return

        prod_ids = [pid for pid, cb in self._checks.items() if cb.isChecked()]
        if len(prod_ids) < 2:
            QMessageBox.critical(
                self, "Error", "Debes seleccionar al menos 2 productos.")
            return

        expira_at = None
        if self.rb_con_exp.isChecked():
            expira_at = self.dt_exp.dateTime().toString("yyyy-MM-dd HH:mm:ss")

        self.db.add_oferta(nombre, precio_f, self.tienda_id, prod_ids, expira_at)
        self._load_ofertas()

        # Limpiar formulario
        self.f_nombre.clear()
        self.f_precio.clear()
        self.rb_sin_exp.setChecked(True)
        for cb in self._checks.values():
            cb.setChecked(False)

        if self.callback:
            self.callback()

    def _eliminar(self):
        row = self.list_ofertas.currentRow()
        if row < 0:
            return
        oferta = self._ofertas[row]
        r = QMessageBox.question(
            self, "Confirmar",
            f"Eliminar oferta '{oferta['nombre']}'?")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_oferta(oferta["id"])
            self._load_ofertas()
            if self.callback:
                self.callback()