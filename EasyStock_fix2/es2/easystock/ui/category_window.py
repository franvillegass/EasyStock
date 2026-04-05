"""
EasyStock — gestion de categorias (PyQt6).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QWidget, QMessageBox,
    QListWidget, QListWidgetItem,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import make_btn, h_sep, AccentBar


class CategoryWindow(QDialog):
    def __init__(self, parent, db: DBManager, callback=None):
        super().__init__(parent)
        self.db       = db
        self.callback = callback
        self._cats    = []

        self.setWindowTitle("EasyStock — Categorias")
        self.setFixedSize(420, 480)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._build()
        self._load()
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
        hdr_lay.addWidget(AccentBar(C["purple"]))
        lbl = QLabel("  CATEGORIAS")
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {C['purple']}; "
            f"background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(lbl)
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Lista
        body = QWidget()
        body.setStyleSheet(f"background: {C['bg_panel']};")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 8)
        body_lay.setSpacing(10)

        hint = QLabel("Las categorias del sistema no pueden eliminarse.")
        hint.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 10px; background: transparent;")
        body_lay.addWidget(hint)

        list_hdr = QWidget()
        list_hdr.setFixedHeight(28)
        list_hdr.setStyleSheet(f"background: {C['bg_input']};")
        lh_lay = QHBoxLayout(list_hdr)
        lh_lay.setContentsMargins(12, 0, 12, 0)
        lbl_lista = QLabel("CATEGORIAS EXISTENTES")
        lbl_lista.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        lh_lay.addWidget(lbl_lista)
        body_lay.addWidget(list_hdr)

        self.lista = QListWidget()
        self.lista.setAlternatingRowColors(True)
        # color alternado manejado por QSS
        self.lista.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_card']}; border: 1px solid {C['border']};
                border-radius: 6px; outline: none;
            }}
            QListWidget::item {{
                padding: 9px 12px;
                border-bottom: 1px solid {C['border']};
                font-size: 12px;
                background: {C['bg_card']};
                color: {C['text_hi']};
            }}
            QListWidget::item:alternate {{
                background: {C['bg_panel']};
            }}
            QListWidget::item:selected {{
                background: {C['bg_select']}; color: {C['amber_glow']};
            }}
            QListWidget::item:hover:!selected {{
                background: {C['bg_hover']};
            }}
        """)
        body_lay.addWidget(self.lista, 1)
        root.addWidget(body, 1)
        root.addWidget(h_sep())

        # Nueva categoria
        new_hdr = QWidget()
        new_hdr.setFixedHeight(28)
        new_hdr.setStyleSheet(f"background: {C['bg_input']};")
        nh_lay = QHBoxLayout(new_hdr)
        nh_lay.setContentsMargins(16, 0, 16, 0)
        lbl_new = QLabel("NUEVA CATEGORIA")
        lbl_new.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        nh_lay.addWidget(lbl_new)
        root.addWidget(new_hdr)

        new_row = QWidget()
        new_row.setStyleSheet(f"background: {C['bg_panel']};")
        new_lay = QHBoxLayout(new_row)
        new_lay.setContentsMargins(16, 10, 16, 10)
        new_lay.setSpacing(8)

        self.f_nueva = QLineEdit()
        self.f_nueva.setPlaceholderText("Nombre de la nueva categoria...")
        self.f_nueva.returnPressed.connect(self._crear)

        btn_crear = make_btn("+ CREAR", "primary", min_w=100, h=36)
        btn_crear.clicked.connect(self._crear)

        new_lay.addWidget(self.f_nueva, 1)
        new_lay.addWidget(btn_crear)
        root.addWidget(new_row)
        root.addWidget(h_sep())

        # Footer
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(16, 10, 16, 16)
        foot_lay.setSpacing(8)

        btn_del   = make_btn("x ELIMINAR", "danger", min_w=130, h=36)
        btn_close = make_btn("CERRAR",     "ghost",  min_w=100, h=36)
        btn_del.clicked.connect(self._eliminar)
        btn_close.clicked.connect(self.accept)

        foot_lay.addWidget(btn_del)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_close)
        root.addWidget(foot)

    def _load(self):
        self._cats = self.db.list_categorias()
        self.lista.clear()
        for cat in self._cats:
            suffix = "  [sistema]" if cat["es_sistema"] else ""
            item = QListWidgetItem(f"  {cat['nombre']}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, cat["id"])
            if cat["es_sistema"]:
                from PyQt6.QtGui import QColor
                item.setForeground(QColor(C["text_dim"]))
            self.lista.addItem(item)

    def _crear(self):
        nombre = self.f_nueva.text().strip()
        if not nombre:
            return
        try:
            self.db.add_categoria(nombre)
            self.f_nueva.clear()
            self._load()
            if self.callback:
                self.callback()
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _eliminar(self):
        row = self.lista.currentRow()
        if row < 0:
            return
        cat = self._cats[row]
        if cat["es_sistema"]:
            QMessageBox.warning(
                self, "No permitido",
                f"'{cat['nombre']}' es una categoria del sistema y no puede eliminarse.")
            return
        r = QMessageBox.question(
            self, "Confirmar",
            f"Eliminar categoria '{cat['nombre']}'?\n"
            f"Los productos que la tenian la perderan.")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_categoria(cat["id"])
            self._load()
            if self.callback:
                self.callback()