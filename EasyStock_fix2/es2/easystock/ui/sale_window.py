"""
EasyStock — ventana de venta (PyQt6).
Incluye: filtro por categoria, ofertas, descuentos por item,
descuento total y selector de metodo de pago al confirmar.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QWidget, QScrollArea,
    QMessageBox, QFrame, QSpinBox, QComboBox,
    QDoubleSpinBox, QButtonGroup, QRadioButton,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import make_btn, h_sep, AccentBar


# ── Dialog de confirmacion (metodo de pago + descuento global) ────────────────
class ConfirmVentaDialog(QDialog):
    def __init__(self, parent, subtotal: float):
        super().__init__(parent)
        self.setWindowTitle("Confirmar Venta")
        self.setFixedSize(360, 300)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self.metodo   = "efectivo"
        self.descuento = 0.0

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(f"background: {C['bg_deep']};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(0, 0, 0, 0)
        hdr_lay.addWidget(AccentBar(C["green"]))
        lbl = QLabel("  CONFIRMAR VENTA")
        lbl.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {C['green']}; "
            f"background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(lbl)
        root.addWidget(hdr)
        root.addWidget(h_sep())

        body = QWidget()
        body.setStyleSheet("background: transparent;")
        body_lay = QVBoxLayout(body)
        body_lay.setContentsMargins(24, 18, 24, 8)
        body_lay.setSpacing(16)

        # Metodo de pago
        lbl_mp = QLabel("METODO DE PAGO")
        lbl_mp.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 9px; font-weight: bold; "
            f"letter-spacing: 1px; background: transparent;")
        body_lay.addWidget(lbl_mp)

        rb_style = f"""
            QRadioButton {{
                color: {C['text_hi']}; font-size: 12px;
                spacing: 8px; background: transparent;
            }}
            QRadioButton:checked {{ color: {C['amber']}; font-weight: bold; }}
            QRadioButton::indicator {{
                width: 14px; height: 14px;
                border-radius: 7px;
                border: 2px solid {C['border_lit']};
                background: {C['bg_input']};
            }}
            QRadioButton::indicator:checked {{
                border-color: {C['amber']};
                background: {C['amber_dim']};
            }}
        """
        mp_row = QHBoxLayout()
        mp_row.setSpacing(16)
        self._grp = QButtonGroup(self)
        for valor, label in [("efectivo","Efectivo"),("transferencia","Transferencia"),("qr","QR")]:
            rb = QRadioButton(label)
            rb.setStyleSheet(rb_style)
            rb.setProperty("valor", valor)
            if valor == "efectivo":
                rb.setChecked(True)
            self._grp.addButton(rb)
            mp_row.addWidget(rb)
        body_lay.addLayout(mp_row)

        # Descuento global
        lbl_desc = QLabel("DESCUENTO GLOBAL (%)")
        lbl_desc.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 9px; font-weight: bold; "
            f"letter-spacing: 1px; background: transparent;")
        body_lay.addWidget(lbl_desc)

        self.spin_desc = QDoubleSpinBox()
        self.spin_desc.setRange(0, 100)
        self.spin_desc.setDecimals(1)
        self.spin_desc.setSuffix(" %")
        self.spin_desc.setValue(0)
        self.spin_desc.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {C['bg_input']};
                border: 1px solid {C['border']};
                border-radius: 5px;
                color: {C['text_hi']};
                padding: 6px 10px;
                font-size: 12px;
            }}
            QDoubleSpinBox:focus {{ border-color: {C['amber']}; }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 18px; border: none;
                background: {C['bg_hover']};
            }}
        """)
        self.spin_desc.valueChanged.connect(self._update_total_label)
        body_lay.addWidget(self.spin_desc)

        self._subtotal = subtotal
        self.lbl_total = QLabel(f"TOTAL  ${subtotal:,.2f}")
        self.lbl_total.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {C['amber']}; "
            f"background: transparent;")
        body_lay.addWidget(self.lbl_total)

        root.addWidget(body, 1)
        root.addWidget(h_sep())

        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(24, 10, 24, 14)
        foot_lay.setSpacing(8)

        btn_ok     = make_btn("CONFIRMAR", "success", min_w=140, h=38)
        btn_cancel = make_btn("CANCELAR",  "ghost",   min_w=110, h=38)
        btn_ok.clicked.connect(self._on_ok)
        btn_cancel.clicked.connect(self.reject)
        foot_lay.addWidget(btn_ok)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_cancel)
        root.addWidget(foot)

    def _update_total_label(self, pct: float):
        total = self._subtotal * (1 - pct / 100)
        self.lbl_total.setText(f"TOTAL  ${total:,.2f}")

    def _on_ok(self):
        btn = self._grp.checkedButton()
        self.metodo    = btn.property("valor") if btn else "efectivo"
        self.descuento = self.spin_desc.value()
        self.accept()

    def get_total_final(self) -> float:
        return self._subtotal * (1 - self.descuento / 100)


# ── Ventana principal de venta ────────────────────────────────────────────────
class SaleWindow(QDialog):
    def __init__(self, parent, db: DBManager, productos: list[dict],
                 tienda_id: int, refresh_callback=None):
        super().__init__(parent)
        self.db               = db
        self.productos        = productos
        self.tienda_id        = tienda_id
        self.refresh_callback = refresh_callback
        self._carrito: dict[str, dict] = {}  # key: "p_{id}" o "o_{id}"
        self._cat_filtro: int | None = None

        self.setWindowTitle("EasyStock — Registrar Venta")
        self.setMinimumSize(960, 620)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._ofertas = self.db.list_ofertas(tienda_id)
        self._categorias = self.db.list_categorias()

        self._build()
        self._refresh_lista()
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
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(f"background: {C['bg_deep']};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(0, 0, 20, 0)
        hdr_lay.setSpacing(0)
        hdr_lay.addWidget(AccentBar(C["green"]))
        lbl = QLabel("  REGISTRAR VENTA")
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {C['green']}; "
            f"background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(lbl)
        hdr_lay.addStretch()
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Barra busqueda + filtro categoria
        top_bar = QWidget()
        top_bar.setStyleSheet(f"background: {C['bg_panel']};")
        top_lay = QHBoxLayout(top_bar)
        top_lay.setContentsMargins(16, 8, 16, 8)
        top_lay.setSpacing(10)

        self.f_scan = QLineEdit()
        self.f_scan.setPlaceholderText("Escanear codigo o buscar por nombre...")
        self.f_scan.returnPressed.connect(self._on_scan_enter)
        self.f_scan.textChanged.connect(lambda _: self._refresh_lista())

        self.cb_cat = QComboBox()
        self.cb_cat.setMinimumWidth(160)
        self.cb_cat.addItem("Todas las categorias", None)
        for cat in self._categorias:
            self.cb_cat.addItem(cat["nombre"], cat["id"])
        self.cb_cat.currentIndexChanged.connect(self._on_cat_change)

        top_lay.addWidget(QLabel("🔍", styleSheet=f"color:{C['text_dim']};background:transparent;"))
        top_lay.addWidget(self.f_scan, 1)
        top_lay.addWidget(QLabel("CAT:", styleSheet=f"color:{C['text_dim']};font-size:10px;font-weight:bold;background:transparent;"))
        top_lay.addWidget(self.cb_cat)
        root.addWidget(top_bar)
        root.addWidget(h_sep())

        # Splitter productos | carrito
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {C['border']}; width: 1px; }}")
        splitter.setHandleWidth(1)

        # Panel izquierdo: lista de productos y ofertas
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
        for text, stretch in [("NOMBRE", 4), ("STOCK", 1), ("PRECIO", 1)]:
            lbl2 = QLabel(text)
            lbl2.setStyleSheet(
                f"color: {C['amber']}; font-size: 9px; font-weight: bold; background: transparent;")
            lh_lay.addWidget(lbl2, stretch)
        left_lay.addWidget(left_hdr)

        self._scroll_lista = QScrollArea()
        self._scroll_lista.setWidgetResizable(True)
        self._scroll_lista.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_lista.setStyleSheet("background: transparent;")
        self._lista_container = QWidget()
        self._lista_container.setStyleSheet(f"background: {C['bg_card']};")
        self._lista_layout = QVBoxLayout(self._lista_container)
        self._lista_layout.setContentsMargins(0, 0, 0, 0)
        self._lista_layout.setSpacing(0)
        self._lista_layout.addStretch()
        self._scroll_lista.setWidget(self._lista_container)
        left_lay.addWidget(self._scroll_lista, 1)
        splitter.addWidget(left)

        # Panel derecho: carrito
        right = QWidget()
        right.setStyleSheet(f"background: {C['bg_panel']};")
        right_lay = QVBoxLayout(right)
        right_lay.setContentsMargins(0, 0, 0, 0)
        right_lay.setSpacing(0)

        cart_hdr = QWidget()
        cart_hdr.setFixedHeight(32)
        cart_hdr.setStyleSheet(f"background: {C['bg_input']};")
        ch_lay = QHBoxLayout(cart_hdr)
        ch_lay.setContentsMargins(14, 0, 14, 0)
        lbl_cart = QLabel("CARRITO")
        lbl_cart.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold; background: transparent;")
        ch_lay.addWidget(lbl_cart)
        right_lay.addWidget(cart_hdr)

        self._scroll_cart = QScrollArea()
        self._scroll_cart.setWidgetResizable(True)
        self._scroll_cart.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll_cart.setStyleSheet("background: transparent;")
        self._cart_container = QWidget()
        self._cart_container.setStyleSheet(f"background: {C['bg_panel']};")
        self._cart_layout = QVBoxLayout(self._cart_container)
        self._cart_layout.setContentsMargins(8, 8, 8, 8)
        self._cart_layout.setSpacing(6)
        self._cart_layout.addStretch()
        self._scroll_cart.setWidget(self._cart_container)
        right_lay.addWidget(self._scroll_cart, 1)
        splitter.addWidget(right)

        splitter.setSizes([580, 340])
        root.addWidget(splitter, 1)
        root.addWidget(h_sep())

        # Footer
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_deep']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(20, 12, 20, 16)

        self.lbl_total = QLabel("SUBTOTAL  $0.00")
        self.lbl_total.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {C['amber']};")

        btn_cancel  = make_btn("CANCELAR",           "ghost",   min_w=120, h=42)
        btn_confirm = make_btn("CONFIRMAR VENTA",  "success", min_w=200, h=42)
        btn_cancel.clicked.connect(self.reject)
        btn_confirm.clicked.connect(self._confirmar)

        foot_lay.addWidget(self.lbl_total)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_cancel)
        foot_lay.addWidget(btn_confirm)
        root.addWidget(foot)

    # ── Filtro categoria ───────────────────────────────────────────────────────
    def _on_cat_change(self, idx: int):
        self._cat_filtro = self.cb_cat.itemData(idx)
        self._refresh_lista()

    # ── Lista de productos y ofertas ───────────────────────────────────────────
    def _refresh_lista(self):
        while self._lista_layout.count() > 1:
            item = self._lista_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        filtro = self.f_scan.text().lower()
        cat_id = self._cat_filtro

        # Productos
        items = []
        for p in self.productos:
            if cat_id is not None:
                cats = [c["id"] for c in p.get("categorias", [])]
                if cat_id not in cats:
                    continue
            if filtro and filtro not in p["nombre"].lower() \
                    and filtro not in (p.get("codigo_barras") or "").lower():
                continue
            items.append(("producto", p))

        # Ofertas (solo si no hay filtro de cat distinto a Ofertas, o si es Ofertas)
        cat_ofertas = next((c for c in self._categorias if c["nombre"] == "Ofertas"), None)
        mostrar_ofertas = (cat_id is None or
                           (cat_ofertas and cat_id == cat_ofertas["id"]))
        if mostrar_ofertas:
            for o in self._ofertas:
                if filtro and filtro not in o["nombre"].lower():
                    continue
                items.append(("oferta", o))

        for i, (tipo, item) in enumerate(items):
            row = QWidget()
            bg = C["bg_card"] if i % 2 == 0 else C["bg_panel"]
            row.setStyleSheet(f"""
                QWidget {{ background: {bg}; border: none; }}
                QWidget:hover {{ background: {C['bg_hover']}; }}
            """)
            row.setFixedHeight(36)
            row.setCursor(Qt.CursorShape.PointingHandCursor)

            lay = QHBoxLayout(row)
            lay.setContentsMargins(14, 0, 14, 0)
            lay.setSpacing(0)

            if tipo == "producto":
                nombre_lbl = QLabel(item["nombre"])
                nombre_lbl.setStyleSheet("background: transparent;")

                stock_c = C["green"] if item["stock"] > 5 else C["red"]
                stock_lbl = QLabel(str(item["stock"]))
                stock_lbl.setStyleSheet(
                    f"color: {stock_c}; font-weight: bold; background: transparent;")
                stock_lbl.setFixedWidth(60)
                stock_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

                precio_lbl = QLabel(f"${item['precio']:.2f}")
                precio_lbl.setStyleSheet(
                    f"color: {C['text_mid']}; background: transparent;")
                precio_lbl.setFixedWidth(90)
                precio_lbl.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                lay.addWidget(nombre_lbl, 4)
                lay.addWidget(stock_lbl, 1)
                lay.addWidget(precio_lbl, 1)
                row.mouseDoubleClickEvent = lambda e, p=item: self._agregar_producto(p)

            else:  # oferta
                tag = QLabel("OFERTA")
                tag.setStyleSheet(
                    f"color: {C['bg_deep']}; background: {C['amber']}; "
                    f"font-size: 8px; font-weight: bold; padding: 1px 5px; border-radius: 3px;")
                tag.setFixedWidth(52)

                nombre_lbl = QLabel(f"  {item['nombre']}")
                nombre_lbl.setStyleSheet(
                    f"color: {C['amber_glow']}; background: transparent;")

                precio_lbl = QLabel(f"${item['precio']:.2f}")
                precio_lbl.setStyleSheet(
                    f"color: {C['text_mid']}; background: transparent;")
                precio_lbl.setFixedWidth(90)
                precio_lbl.setAlignment(
                    Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                lay.addWidget(tag)
                lay.addWidget(nombre_lbl, 5)
                lay.addWidget(precio_lbl, 1)
                row.mouseDoubleClickEvent = lambda e, o=item: self._agregar_oferta(o)

            self._lista_layout.insertWidget(self._lista_layout.count() - 1, row)

    def _on_scan_enter(self):
        codigo = self.f_scan.text().strip()
        self.f_scan.clear()
        if not codigo:
            return
        p = next((x for x in self.productos
                  if (x.get("codigo_barras") or "") == codigo), None)
        if not p:
            QMessageBox.critical(self, "Error", f"Codigo '{codigo}' no encontrado.")
            return
        self._agregar_producto(p)

    # ── Carrito ────────────────────────────────────────────────────────────────
    def _agregar_producto(self, producto: dict):
        key = f"p_{producto['id']}"
        if key in self._carrito:
            self._carrito[key]["spin"].setValue(
                self._carrito[key]["spin"].value() + 1)
            self._update_total()
            return
        self._add_carrito_row(key, producto["nombre"], producto["precio"],
                              producto["stock"], producto, None)

    def _agregar_oferta(self, oferta: dict):
        key = f"o_{oferta['id']}"
        if key in self._carrito:
            self._carrito[key]["spin"].setValue(
                self._carrito[key]["spin"].value() + 1)
            self._update_total()
            return
        self._add_carrito_row(key, f"[OFERTA] {oferta['nombre']}",
                              oferta["precio"], 999, None, oferta)

    def _add_carrito_row(self, key: str, nombre: str, precio: float,
                         stock_max: int, producto, oferta):
        row = QWidget()
        row.setStyleSheet(f"background: {C['bg_card']}; border-radius: 4px;")
        lay = QHBoxLayout(row)
        lay.setContentsMargins(10, 4, 8, 4)
        lay.setSpacing(6)

        nombre_lbl = QLabel(nombre[:28])
        nombre_lbl.setStyleSheet("background: transparent; font-size: 11px;")

        # Descuento por item
        spin_desc = QDoubleSpinBox()
        spin_desc.setRange(0, 100)
        spin_desc.setDecimals(1)
        spin_desc.setSuffix("%")
        spin_desc.setValue(0)
        spin_desc.setFixedWidth(74)
        spin_desc.setFixedHeight(28)
        spin_desc.setToolTip("Descuento individual (%)")
        spin_desc.setStyleSheet(f"""
            QDoubleSpinBox {{
                background: {C['bg_input']};
                border: 1px solid {C['border']};
                border-radius: 4px;
                color: {C['blue']};
                font-weight: bold;
                font-size: 10px;
                padding: 1px 2px;
            }}
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
                width: 14px; border: none;
                background: {C['bg_hover']};
            }}
        """)
        spin_desc.valueChanged.connect(self._update_total)

        # Cantidad
        spin = QSpinBox()
        spin.setMinimum(1)
        spin.setMaximum(stock_max)
        spin.setValue(1)
        spin.setFixedWidth(60)
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
                width: 16px; border: none;
                background: {C['bg_hover']};
            }}
        """)
        spin.valueChanged.connect(self._update_total)

        btn_rm = make_btn("✕", "danger", h=28)
        btn_rm.setFixedWidth(28)

        def quitar(k=key, r=row):
            del self._carrito[k]
            r.deleteLater()
            self._update_total()

        btn_rm.clicked.connect(quitar)

        lay.addWidget(nombre_lbl, 1)
        lay.addWidget(spin_desc)
        lay.addWidget(spin)
        lay.addWidget(btn_rm)

        self._carrito[key] = {
            "producto": producto,
            "oferta":   oferta,
            "spin":     spin,
            "spin_desc": spin_desc,
            "precio":   precio,
        }
        self._cart_layout.insertWidget(self._cart_layout.count() - 1, row)
        self._update_total()

    def _update_total(self):
        subtotal = self._calc_subtotal()
        self.lbl_total.setText(f"SUBTOTAL  ${subtotal:,.2f}")

    def _calc_subtotal(self) -> float:
        total = 0.0
        for data in self._carrito.values():
            cant   = data["spin"].value()
            desc   = data["spin_desc"].value() / 100
            precio = data["precio"]
            total += cant * precio * (1 - desc)
        return total

    # ── Confirmar ──────────────────────────────────────────────────────────────
    def _confirmar(self):
        if not self._carrito:
            QMessageBox.information(self, "Venta", "El carrito esta vacio.")
            return

        # Validar stock productos normales
        for key, data in self._carrito.items():
            if key.startswith("p_") and data["producto"]:
                p    = data["producto"]
                cant = data["spin"].value()
                if cant > p["stock"]:
                    QMessageBox.critical(
                        self, "Error",
                        f"Stock insuficiente para '{p['nombre']}'.\n"
                        f"Disponible: {p['stock']}, pedido: {cant}")
                    return

        subtotal = self._calc_subtotal()

        dlg = ConfirmVentaDialog(self, subtotal)
        if not dlg.exec():
            return

        metodo_pago     = dlg.metodo
        descuento_total = dlg.descuento
        total_final     = dlg.get_total_final()

        lineas = []
        for key, data in self._carrito.items():
            cant      = data["spin"].value()
            desc_item = data["spin_desc"].value()
            precio    = data["precio"]
            sub       = cant * precio * (1 - desc_item / 100)

            if key.startswith("o_") and data["oferta"]:
                o = data["oferta"]
                # Para ofertas: descontar stock de cada producto componente
                for prod_comp in o["productos"]:
                    self.db.cursor.execute(
                        "UPDATE productos SET stock = stock - ? WHERE id = ?",
                        (cant, prod_comp["id"]))
                self.db.conn.commit()
                lineas.append({
                    "producto":     o["nombre"],
                    "producto_id":  None,
                    "cantidad":     cant,
                    "precio":       precio,
                    "descuento_item": desc_item,
                    "subtotal":     sub,
                    "es_oferta":    True,
                })
            else:
                p = data["producto"]
                lineas.append({
                    "producto":     p["nombre"],
                    "producto_id":  p["id"],
                    "cantidad":     cant,
                    "precio":       precio,
                    "descuento_item": desc_item,
                    "subtotal":     sub,
                    "es_oferta":    False,
                })

        self.db.create_venta(
            lineas, total_final,
            tienda_id=self.tienda_id,
            metodo_pago=metodo_pago,
            descuento_total=descuento_total,
        )

        if self.refresh_callback:
            self.refresh_callback()
        self.accept()