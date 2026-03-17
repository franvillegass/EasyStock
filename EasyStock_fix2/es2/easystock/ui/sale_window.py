"""
EasyStock — ventana de venta (PyQt6).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QWidget, QScrollArea,
    QMessageBox, QFrame, QSpinBox,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import make_btn, h_sep, AccentBar, SectionPanel


class SaleWindow(QDialog):
    def __init__(self, parent, db: DBManager, productos: list[dict],
                 tienda_id: int, refresh_callback=None):
        super().__init__(parent)
        self.db               = db
        self.productos        = productos
        self.tienda_id        = tienda_id
        self.refresh_callback = refresh_callback
        self._carrito: dict[int, dict] = {}

        self.setWindowTitle("EasyStock — Registrar Venta")
        self.setMinimumSize(880, 580)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._build()
        self._refresh_productos()
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
        hdr.setFixedHeight(56)
        hdr.setStyleSheet(f"background: {C['bg_deep']};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(0, 0, 20, 0)
        hdr_lay.setSpacing(0)
        hdr_lay.addWidget(AccentBar(C["green"]))
        lbl = QLabel("  REGISTRAR VENTA")
        lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {C['green']}; background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Scanner row
        scan_row = QWidget()
        scan_row.setStyleSheet(f"background: {C['bg_panel']};")
        scan_lay = QHBoxLayout(scan_row)
        scan_lay.setContentsMargins(16, 10, 16, 6)
        scan_lay.setSpacing(10)

        scan_lbl = QLabel("CÓDIGO / BUSCAR")
        scan_lbl.setProperty("role", "tag")
        self.f_scan = QLineEdit()
        self.f_scan.setPlaceholderText("Escanear código de barras o buscar por nombre...")
        self.f_scan.returnPressed.connect(self._on_scan_enter)
        self.f_scan.textChanged.connect(self._on_search)

        scan_lay.addWidget(scan_lbl)
        scan_lay.addWidget(self.f_scan, 1)
        root.addWidget(scan_row)
        root.addWidget(h_sep())

        # Splitter: productos | carrito
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {C['border']}; width: 1px; }}")
        splitter.setHandleWidth(1)

        # Panel izquierdo: productos disponibles
        left_panel = QWidget()
        left_panel.setStyleSheet(f"background: {C['bg_card']};")
        left_lay = QVBoxLayout(left_panel)
        left_lay.setContentsMargins(0, 0, 0, 0)
        left_lay.setSpacing(0)

        left_hdr = QWidget()
        left_hdr.setFixedHeight(34)
        left_hdr.setStyleSheet(f"background: {C['bg_input']};")
        left_hdr_lay = QHBoxLayout(left_hdr)
        left_hdr_lay.setContentsMargins(14, 0, 14, 0)
        for text, stretch in [("NOMBRE", 4), ("STOCK", 1), ("PRECIO", 1)]:
            lbl = QLabel(text)
            lbl.setStyleSheet(f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
            left_hdr_lay.addWidget(lbl, stretch)
        left_lay.addWidget(left_hdr)

        self._scroll_prods = QScrollArea()
        self._scroll_prods.setWidgetResizable(True)
        self._scroll_prods.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_prods.setStyleSheet("background: transparent;")
        self._prods_container = QWidget()
        self._prods_container.setStyleSheet(f"background: {C['bg_card']};")
        self._prods_layout = QVBoxLayout(self._prods_container)
        self._prods_layout.setContentsMargins(0, 0, 0, 0)
        self._prods_layout.setSpacing(0)
        self._prods_layout.addStretch()
        self._scroll_prods.setWidget(self._prods_container)
        left_lay.addWidget(self._scroll_prods, 1)
        splitter.addWidget(left_panel)

        # Panel derecho: carrito
        right_panel = QWidget()
        right_panel.setStyleSheet(f"background: {C['bg_panel']};")
        right_lay = QVBoxLayout(right_panel)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        cart_hdr = QWidget()
        cart_hdr.setFixedHeight(34)
        cart_hdr.setStyleSheet(f"background: {C['bg_input']};")
        cart_hdr_lay = QHBoxLayout(cart_hdr)
        cart_hdr_lay.setContentsMargins(14, 0, 14, 0)
        lbl_cart = QLabel("CARRITO")
        lbl_cart.setStyleSheet(f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        cart_hdr_lay.addWidget(lbl_cart)
        right_lay.addWidget(cart_hdr)

        self._scroll_cart = QScrollArea()
        self._scroll_cart.setWidgetResizable(True)
        self._scroll_cart.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_cart.setStyleSheet("background: transparent;")
        self._cart_container = QWidget()
        self._cart_container.setStyleSheet(f"background: {C['bg_panel']};")
        self._cart_layout = QVBoxLayout(self._cart_container)
        self._cart_layout.setContentsMargins(8, 8, 8, 8)
        self._cart_layout.setSpacing(4)
        self._cart_layout.addStretch()
        self._scroll_cart.setWidget(self._cart_container)
        right_lay.addWidget(self._scroll_cart, 1)
        splitter.addWidget(right_panel)

        splitter.setSizes([560, 300])
        root.addWidget(splitter, 1)
        root.addWidget(h_sep())

        # Footer: total + botones
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_deep']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(20, 12, 20, 16)

        self.lbl_total = QLabel("TOTAL  $0.00")
        self.lbl_total.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {C['amber']};")

        btn_cancel  = make_btn("CANCELAR",        "ghost",   min_w=120, h=42)
        btn_confirm = make_btn("✓  CONFIRMAR VENTA", "success", min_w=200, h=42)
        btn_cancel.clicked.connect(self.reject)
        btn_confirm.clicked.connect(self._confirmar)

        foot_lay.addWidget(self.lbl_total)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_cancel)
        foot_lay.addWidget(btn_confirm)
        root.addWidget(foot)

    # ── Productos disponibles ──────────────────────────────────────────────────
    def _refresh_productos(self, filtro: str = ""):
        # limpiar (menos el stretch)
        while self._prods_layout.count() > 1:
            item = self._prods_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtro = filtro.lower()
        visible = [p for p in self.productos
                   if filtro in p["nombre"].lower()
                   or filtro in (p.get("codigo_barras") or "").lower()]

        for i, p in enumerate(visible):
            row = QWidget()
            row_bg = C["bg_card"] if i % 2 == 0 else C["bg_panel"]
            row.setStyleSheet(f"""
                QWidget {{ background: {row_bg}; border: none; }}
                QWidget:hover {{ background: {C['bg_hover']}; }}
            """)
            row.setFixedHeight(36)
            row.setCursor(Qt.CursorShape.PointingHandCursor)

            lay = QHBoxLayout(row)
            lay.setContentsMargins(14, 0, 14, 0)
            lay.setSpacing(0)

            nombre_lbl = QLabel(p["nombre"])
            nombre_lbl.setStyleSheet("background: transparent;")

            stock_c = C["green"] if p["stock"] > 5 else C["red"]
            stock_lbl = QLabel(str(p["stock"]))
            stock_lbl.setStyleSheet(f"color: {stock_c}; font-weight: bold; background: transparent;")
            stock_lbl.setFixedWidth(60)
            stock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

            precio_lbl = QLabel(f"${p['precio']:.2f}")
            precio_lbl.setStyleSheet(f"color: {C['text_mid']}; background: transparent;")
            precio_lbl.setFixedWidth(80)
            precio_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

            lay.addWidget(nombre_lbl, 4)
            lay.addWidget(stock_lbl, 1)
            lay.addWidget(precio_lbl, 1)

            # doble click → agregar al carrito
            prod_ref = p
            row.mouseDoubleClickEvent = lambda e, pr=prod_ref: self._agregar(pr)
            self._prods_layout.insertWidget(self._prods_layout.count() - 1, row)

    def _on_search(self, text: str):
        self._refresh_productos(text)

    def _on_scan_enter(self):
        codigo = self.f_scan.text().strip()
        self.f_scan.clear()
        if not codigo:
            return
        p = next((x for x in self.productos
                  if (x.get("codigo_barras") or "") == codigo), None)
        if not p:
            QMessageBox.critical(self, "Error", f"Código '{codigo}' no encontrado.")
            return
        self._agregar(p)

    # ── Carrito ────────────────────────────────────────────────────────────────
    def _agregar(self, producto: dict):
        pid = producto["id"]
        if pid in self._carrito:
            spin = self._carrito[pid]["spin"]
            spin.setValue(spin.value() + 1)
            self._update_total()
            return

        row = QWidget()
        row.setStyleSheet(f"background: {C['bg_card']}; border-radius: 4px;")
        row.setFixedHeight(38)
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 0, 8, 0)
        lay.setSpacing(8)

        nombre_lbl = QLabel(producto["nombre"][:26])
        nombre_lbl.setStyleSheet("background: transparent;")

        spin = QSpinBox()
        spin.setMinimum(1)
        spin.setMaximum(producto["stock"])
        spin.setValue(1)
        spin.setFixedWidth(64)
        spin.setFixedHeight(28)
        spin.setStyleSheet(f"""
            QSpinBox {{
                background: {C['bg_input']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                color: {C['amber']};
                font-weight: bold;
                padding: 2px 4px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                width: 16px;
                border: none;
                background: {C['bg_hover']};
            }}
        """)
        spin.valueChanged.connect(self._update_total)

        btn_rm = make_btn("✕", "danger", h=28)
        btn_rm.setFixedWidth(28)

        def quitar(pid=pid, r=row):
            del self._carrito[pid]
            r.deleteLater()
            self._update_total()

        btn_rm.clicked.connect(quitar)

        lay.addWidget(nombre_lbl, 1)
        lay.addWidget(spin)
        lay.addWidget(btn_rm)

        self._carrito[pid] = {"producto": producto, "spin": spin}
        self._cart_layout.insertWidget(self._cart_layout.count() - 1, row)
        self._update_total()

    def _update_total(self):
        total = sum(
            data["spin"].value() * float(data["producto"]["precio"])
            for data in self._carrito.values()
        )
        self.lbl_total.setText(f"TOTAL  ${total:,.2f}")

    def _confirmar(self):
        lineas = []
        total  = 0.0
        for pid, data in self._carrito.items():
            p    = data["producto"]
            cant = data["spin"].value()
            if cant <= 0:
                continue
            if cant > p["stock"]:
                QMessageBox.critical(
                    self, "Error",
                    f"Stock insuficiente para '{p['nombre']}'.\n"
                    f"Disponible: {p['stock']}, pedido: {cant}")
                return
            sub = cant * float(p["precio"])
            lineas.append({
                "producto":    p["nombre"],
                "producto_id": p["id"],
                "cantidad":    cant,
                "precio":      float(p["precio"]),
                "subtotal":    sub,
            })
            total += sub

        if not lineas:
            QMessageBox.information(self, "Venta", "El carrito está vacío.")
            return

        self.db.create_venta(lineas, total, tienda_id=self.tienda_id)
        if self.refresh_callback:
            self.refresh_callback()
        self.accept()
