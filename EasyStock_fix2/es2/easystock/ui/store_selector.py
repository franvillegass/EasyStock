"""
EasyStock — selector de tiendas (PyQt6).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QLabel, QLineEdit, QInputDialog,
    QMessageBox, QWidget,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import make_btn, make_label, h_sep, AccentBar


class StoreSelectorDialog(QDialog):
    def __init__(self, parent, db: DBManager):
        super().__init__(parent)
        self.db     = db
        self.result_id   = None
        self.result_name = None

        self.setWindowTitle("EasyStock — Seleccionar Sucursal")
        self.setMinimumSize(460, 500)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._build()
        self._load()
        self._animate_in()

    def _animate_in(self):
        fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", self)
        anim.setDuration(220)
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
        hdr.setFixedHeight(60)
        hdr.setStyleSheet(f"background: {C['bg_deep']};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(0, 0, 20, 0)
        hdr_lay.setSpacing(0)

        bar = AccentBar(C["amber"])
        hdr_lay.addWidget(bar)

        title = QLabel("  SUCURSALES")
        title.setProperty("role", "title")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {C['amber']}; background: transparent;")
        hdr_lay.addWidget(title)
        hdr_lay.addStretch()
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Lista
        body = QWidget()
        body.setStyleSheet(f"background: {C['bg_panel']};")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(16, 14, 16, 8)
        body_lay.setSpacing(8)

        hint = QLabel("Seleccioná una sucursal para continuar")
        hint.setProperty("role", "dim")
        body_lay.addWidget(hint)

        self.list_w = QListWidget()
        self.list_w.setAlternatingRowColors(True)
        self.list_w.setStyleSheet(f"""
            QListWidget {{
                background: {C['bg_card']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 10px 14px;
                border-bottom: 1px solid {C['border']};
                font-size: 13px;
            }}
            QListWidget::item:selected {{
                background: {C['bg_select']};
                color: {C['amber_glow']};
            }}
            QListWidget::item:hover:!selected {{
                background: {C['bg_hover']};
            }}
        """)
        self.list_w.itemDoubleClicked.connect(self._on_select)
        body_lay.addWidget(self.list_w, 1)
        root.addWidget(body, 1)

        root.addWidget(h_sep())

        # Botones
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(16, 10, 16, 16)
        foot_lay.setSpacing(8)

        self.btn_sel = make_btn("SELECCIONAR", "primary", min_w=150)
        btn_new      = make_btn("+ NUEVA",     "ghost",   min_w=110)
        btn_del      = make_btn("ELIMINAR",    "danger",  min_w=110)
        btn_cancel   = make_btn("CANCELAR",    "ghost",   min_w=100)

        self.btn_sel.clicked.connect(self._on_select)
        btn_new.clicked.connect(self._on_new)
        btn_del.clicked.connect(self._on_delete)
        btn_cancel.clicked.connect(self.reject)

        foot_lay.addWidget(self.btn_sel)
        foot_lay.addWidget(btn_new)
        foot_lay.addWidget(btn_del)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_cancel)
        root.addWidget(foot)

    def _load(self):
        self._tiendas = self.db.list_tiendas()
        self.list_w.clear()
        for t in self._tiendas:
            item = QListWidgetItem(f"  {t['nombre']}")
            item.setData(Qt.ItemDataRole.UserRole, t["id"])
            self.list_w.addItem(item)

    def _on_select(self):
        items = self.list_w.selectedItems()
        if not items:
            return
        item = items[0]
        self.result_id   = item.data(Qt.ItemDataRole.UserRole)
        self.result_name = item.text().strip()
        self.accept()

    def _on_new(self):
        nombre, ok = QInputDialog.getText(
            self, "Nueva sucursal", "Nombre de la sucursal:")
        if ok and nombre.strip():
            self.db.add_tienda(nombre.strip())
            self._load()

    def _on_delete(self):
        items = self.list_w.selectedItems()
        if not items:
            return
        nombre = items[0].text().strip()
        tid    = items[0].data(Qt.ItemDataRole.UserRole)
        r = QMessageBox.question(
            self, "Confirmar",
            f"¿Eliminar sucursal '{nombre}' y todos sus productos?")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_tienda(tid)
            self._load()
