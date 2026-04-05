"""
EasyStock — ventana principal (PyQt6).
"""
import sqlite3
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QFrame, QInputDialog, QMessageBox,
    QSplitter, QSizePolicy, QApplication, QFileDialog,
    QComboBox,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QTimer, QPoint,
)
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtGui import QColor

import pandas as pd

from easystock.config import C, QSS
from easystock.database import DBManager
from easystock.ui.widgets import (
    make_btn, make_label, h_sep, v_sep,
    KPICard, AccentBar, show_toast,
)
from easystock.ui.store_selector  import StoreSelectorDialog
from easystock.ui.product_form    import ProductFormDialog
from easystock.ui.sale_window     import SaleWindow
from easystock.ui.history_window  import HistoryWindow
from easystock.ui.stats_window    import StatsWindow
from easystock.ui.offer_window    import OfferWindow
from easystock.ui.category_window import CategoryWindow
from easystock.ui.ticket_printer  import imprimir_ticket
from easystock.config             import PASSWORD, INACTIVITY_MS


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EASYSTOCK")
        self.setMinimumSize(1100, 660)
        self.resize(1200, 720)

        self.db            = DBManager()
        self.tienda_id     = None
        self.tienda_nombre = "—"
        self.productos     = []
        self._cat_filtro: int | None = None

        self._excels_dir = Path("excels")
        self._excels_dir.mkdir(exist_ok=True)

        self._build_ui()
        self._animate_open()

        self._inactivity_timer = QTimer(self)
        self._inactivity_timer.setSingleShot(True)
        self._inactivity_timer.setInterval(INACTIVITY_MS)
        self._inactivity_timer.timeout.connect(self._pedir_password)
        self._inactivity_timer.start()

        QTimer.singleShot(160, self._seleccionar_tienda)

    # ── Animacion de apertura ──────────────────────────────────────────────────
    def _animate_open(self):
        fx = QGraphicsOpacityEffect(self.centralWidget())
        self.centralWidget().setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", self)
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ── Construccion UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background: {C['bg_deep']};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        topbar = QWidget()
        topbar.setFixedHeight(60)
        topbar.setStyleSheet(f"background: {C['bg_deep']};")
        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(0, 0, 20, 0)
        tb_lay.setSpacing(0)

        tb_lay.addWidget(AccentBar(C["amber"]))

        lbl_easy = QLabel("  EASY")
        lbl_easy.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {C['amber']}; "
            f"background: transparent; padding-left: 14px;")
        lbl_stock = QLabel("STOCK")
        lbl_stock.setStyleSheet(
            f"font-size: 20px; font-weight: bold; color: {C['text_hi']}; "
            f"background: transparent;")

        self.lbl_tienda = QLabel("  /  —")
        self.lbl_tienda.setStyleSheet(
            f"font-size: 13px; font-weight: bold; color: {C['text_dim']}; "
            f"background: transparent; padding-left: 10px;")

        tb_lay.addWidget(lbl_easy)
        tb_lay.addWidget(lbl_stock)
        tb_lay.addWidget(self.lbl_tienda)
        tb_lay.addStretch()

        btn_cambiar = make_btn("CAMBIAR TIENDA", "ghost", min_w=180, h=36)
        btn_cambiar.clicked.connect(self._seleccionar_tienda)
        tb_lay.addWidget(btn_cambiar)
        root.addWidget(topbar)
        root.addWidget(h_sep())

        # Barra de busqueda + filtro categoria
        search_bar = QWidget()
        search_bar.setFixedHeight(52)
        search_bar.setStyleSheet(f"background: {C['bg_panel']};")
        sb_lay = QHBoxLayout(search_bar)
        sb_lay.setContentsMargins(20, 8, 20, 8)
        sb_lay.setSpacing(12)

        lbl_srch = QLabel("🔍")
        lbl_srch.setStyleSheet(
            f"color: {C['text_dim']}; background: transparent; font-size: 13px;")

        self.f_buscar = QLineEdit()
        self.f_buscar.setPlaceholderText(
            "Buscar producto por nombre o codigo de barras...")
        self.f_buscar.textChanged.connect(self._filtrar)

        lbl_cat = QLabel("CATEGORIA")
        lbl_cat.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 9px; "
            f"font-weight: bold; background: transparent;")

        self.cb_cat = QComboBox()
        self.cb_cat.setMinimumWidth(160)
        self.cb_cat.addItem("TODAS", None)
        self.cb_cat.currentIndexChanged.connect(self._on_cat_change)

        self.lbl_count = QLabel("0 productos")
        self.lbl_count.setStyleSheet(
            f"color: {C['text_dim']}; font-size: 10px; "
            f"background: transparent; min-width: 90px;")

        sb_lay.addWidget(lbl_srch)
        sb_lay.addWidget(self.f_buscar, 1)
        sb_lay.addWidget(lbl_cat)
        sb_lay.addWidget(self.cb_cat)
        sb_lay.addWidget(self.lbl_count)
        root.addWidget(search_bar)
        root.addWidget(h_sep())

        # Tabla de productos
        tbl_wrapper = QWidget()
        tbl_wrapper.setStyleSheet(f"background: {C['bg_panel']};")
        tbl_lay = QVBoxLayout(tbl_wrapper)
        tbl_lay.setContentsMargins(20, 10, 20, 6)
        tbl_lay.setSpacing(0)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["NOMBRE", "STOCK", "PRECIO", "CODIGO"])
        self.tabla.setAlternatingRowColors(True)
        self.tabla.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tabla.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabla.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.setShowGrid(False)
        self.tabla.setSortingEnabled(True)
        self.tabla.setStyleSheet(f"""
            QTableWidget {{
                background: {C['bg_card']};
                alternate-background-color: {C['bg_panel']};
                border: 1px solid {C['border']};
                border-radius: 6px;
                selection-background-color: {C['bg_select']};
                selection-color: {C['amber_glow']};
                outline: none;
                gridline-color: transparent;
            }}
            QTableWidget::item {{
                padding: 6px 12px;
                border-bottom: 1px solid {C['border']};
                font-size: 12px;
            }}
            QTableWidget::item:hover {{
                background: {C['bg_hover']};
            }}
            QHeaderView::section {{
                background: {C['bg_input']};
                color: {C['amber']};
                font-size: 9px;
                font-weight: bold;
                padding: 8px 12px;
                border: none;
                border-right: 1px solid {C['border']};
                border-bottom: 1px solid {C['border']};
                letter-spacing: 1px;
            }}
        """)
        self.tabla.setRowHeight(0, 36)

        hdr = self.tabla.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(1, 90)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(2, 110)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.tabla.setColumnWidth(3, 160)

        tbl_lay.addWidget(self.tabla)
        root.addWidget(tbl_wrapper, 1)
        root.addWidget(h_sep())

        # Barra de acciones
        actions = QWidget()
        actions.setFixedHeight(62)
        actions.setStyleSheet(f"background: {C['bg_deep']};")
        act_lay = QHBoxLayout(actions)
        act_lay.setContentsMargins(20, 10, 20, 10)
        act_lay.setSpacing(10)

        btn_defs = [
            ("+ AGREGAR",    "primary", self.abrir_agregar),
            ("EDITAR",       "ghost",   self.abrir_editar),
            ("x ELIMINAR",   "danger",  self.eliminar_producto),
            ("IMPORTAR XLS", "ghost",   self.cargar_excel),
            ("OFERTAS",      "ghost",   self.abrir_ofertas),
            ("CATEGORIAS",   "ghost",   self.abrir_categorias),
        ]
        for text, variant, cmd in btn_defs:
            b = make_btn(text, variant, min_w=140, h=40)
            b.clicked.connect(cmd)
            act_lay.addWidget(b)

        act_lay.addWidget(v_sep())

        btn_sale   = make_btn("$  VENTA",       "success", min_w=130, h=40)
        btn_hist   = make_btn("HISTORIAL",      "ghost",   min_w=120, h=40)
        btn_cierre = make_btn("CIERRE DE CAJA", "danger",  min_w=150, h=40)
        btn_stats  = make_btn("ESTADISTICAS",   "primary", min_w=150, h=40)

        btn_sale.clicked.connect(self.abrir_venta)
        btn_hist.clicked.connect(self.abrir_historial)
        btn_cierre.clicked.connect(self.cerrar_caja)
        btn_stats.clicked.connect(self.abrir_estadisticas)

        act_lay.addWidget(btn_sale)
        act_lay.addWidget(btn_hist)
        act_lay.addWidget(btn_cierre)
        act_lay.addWidget(btn_stats)
        act_lay.addStretch()

        root.addWidget(actions)

    # ── Filtro categoria ───────────────────────────────────────────────────────
    def _refresh_cat_combo(self):
        """Recarga el combo de categorias sin perder la seleccion actual."""
        current_id = self.cb_cat.currentData()
        self.cb_cat.blockSignals(True)
        self.cb_cat.clear()
        self.cb_cat.addItem("TODAS", None)
        for cat in self.db.list_categorias():
            self.cb_cat.addItem(cat["nombre"], cat["id"])
        # restaurar seleccion
        idx = self.cb_cat.findData(current_id)
        self.cb_cat.setCurrentIndex(idx if idx >= 0 else 0)
        self.cb_cat.blockSignals(False)

    def _on_cat_change(self, _):
        self._cat_filtro = self.cb_cat.currentData()
        self._llenar_tabla(self.f_buscar.text())

    # ── Seleccion de tienda ────────────────────────────────────────────────────
    def _seleccionar_tienda(self):
        tiendas = self.db.list_tiendas()
        if not tiendas:
            nombre, ok = QInputDialog.getText(
                self, "Primera sucursal",
                "No hay sucursales registradas.\nNombre de la primera sucursal:")
            if ok and nombre.strip():
                tid = self.db.add_tienda(nombre.strip())
                self.tienda_id     = tid
                self.tienda_nombre = nombre.strip()
                self._reload()
                show_toast(f"Sucursal '{nombre}' creada", "success", self)
            else:
                if not self.tienda_id:
                    self.close()
            return

        dlg = StoreSelectorDialog(self, self.db)
        if dlg.exec() and dlg.result_id:
            self.tienda_id     = dlg.result_id
            self.tienda_nombre = dlg.result_name
            self._reload()
            show_toast(f"Sucursal: {self.tienda_nombre}", "info", self)

    # ── Reload tabla ───────────────────────────────────────────────────────────
    def _reload(self):
        self.productos = self.db.list_productos(self.tienda_id)
        self.lbl_tienda.setText(f"  /  {self.tienda_nombre.upper()}")
        self._refresh_cat_combo()
        self._llenar_tabla(self.f_buscar.text())

    def _llenar_tabla(self, filtro: str = ""):
        filtro = filtro.lower()

        visibles = []
        for p in self.productos:
            if filtro and filtro not in p["nombre"].lower() \
                    and filtro not in (p.get("codigo_barras") or "").lower():
                continue
            if self._cat_filtro is not None:
                cats = [c["id"] for c in p.get("categorias", [])]
                if self._cat_filtro not in cats:
                    continue
            visibles.append(p)

        self.lbl_count.setText(f"{len(visibles)} productos")
        self.tabla.setSortingEnabled(False)
        self.tabla.setRowCount(len(visibles))

        for row, p in enumerate(visibles):
            self.tabla.setRowHeight(row, 36)

            nombre_item = QTableWidgetItem(p["nombre"])

            stock = p["stock"]
            stock_item = QTableWidgetItem(str(stock))
            stock_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if stock <= 0:
                stock_item.setForeground(QColor(C["red"]))
            elif stock <= 5:
                stock_item.setForeground(QColor(C["amber"]))
            else:
                stock_item.setForeground(QColor(C["green"]))

            precio_item = QTableWidgetItem(f"${p['precio']:,.2f}")
            precio_item.setTextAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            precio_item.setForeground(QColor(C["text_hi"]))

            codigo_item = QTableWidgetItem(p.get("codigo_barras") or "—")
            codigo_item.setForeground(QColor(C["text_dim"]))

            nombre_item.setData(Qt.ItemDataRole.UserRole, p["id"])

            self.tabla.setItem(row, 0, nombre_item)
            self.tabla.setItem(row, 1, stock_item)
            self.tabla.setItem(row, 2, precio_item)
            self.tabla.setItem(row, 3, codigo_item)

        self.tabla.setSortingEnabled(True)

    def _filtrar(self, text: str):
        self._llenar_tabla(text)

    def _get_selected_producto(self) -> dict | None:
        rows = self.tabla.selectedItems()
        if not rows:
            return None
        prod_id = self.tabla.item(self.tabla.currentRow(), 0).data(
            Qt.ItemDataRole.UserRole)
        return next((p for p in self.productos if p["id"] == prod_id), None)

    # ── Acciones ───────────────────────────────────────────────────────────────
    def abrir_agregar(self):
        if not self.tienda_id:
            return
        ProductFormDialog(self, self.db, self.tienda_id,
                          callback=self._reload).exec()

    def abrir_editar(self):
        p = self._get_selected_producto()
        if not p:
            show_toast("Selecciona un producto primero", "warning", self)
            return
        ProductFormDialog(self, self.db, self.tienda_id,
                          producto=p, callback=self._reload).exec()

    def eliminar_producto(self):
        p = self._get_selected_producto()
        if not p:
            show_toast("Selecciona un producto primero", "warning", self)
            return
        r = QMessageBox.question(
            self, "Confirmar", f"Eliminar '{p['nombre']}'?")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_producto(p["id"])
            self._reload()
            show_toast(f"'{p['nombre']}' eliminado", "info", self)

    def cargar_excel(self):
        if not self.tienda_id:
            show_toast("Selecciona una tienda primero", "warning", self)
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Excel",
            str(self._excels_dir.resolve()),
            "Archivos Excel (*.xlsx *.xls)",
        )
        if not path:
            return

        try:
            df   = pd.read_excel(path)
            cols = [c.lower() for c in df.columns]
            if not all(c in cols for c in ["nombre", "stock", "precio"]):
                QMessageBox.critical(
                    self, "Error",
                    "El Excel debe tener columnas: nombre, stock, precio")
                return
            n, omitidos = 0, 0
            for _, row in df.iterrows():
                codigo = str(row.get("codigo_barras", "")).strip() or None
                try:
                    self.db.add_producto(
                        str(row["nombre"]), int(row["stock"]),
                        float(row["precio"]), self.tienda_id, codigo)
                    n += 1
                except sqlite3.IntegrityError:
                    omitidos += 1
                    continue
            self._reload()
            msg = f"{n} productos importados"
            if omitidos:
                msg += f" ({omitidos} omitidos por codigo duplicado)"
            show_toast(msg, "success", self)
        except Exception as e:
            QMessageBox.critical(self, "Error al leer Excel", str(e))

    def abrir_venta(self):
        if not self.productos:
            show_toast("No hay productos cargados", "warning", self)
            return
        SaleWindow(self, self.db, self.productos,
                   tienda_id=self.tienda_id,
                   refresh_callback=self._reload).exec()

    def abrir_historial(self):
        if not self.tienda_id:
            return
        HistoryWindow(self, self.db, self.tienda_id).exec()

    def abrir_estadisticas(self):
        if not self.tienda_id:
            show_toast("Selecciona una tienda primero", "warning", self)
            return
        StatsWindow(self, self.db, self.tienda_id, self.tienda_nombre).exec()

    def abrir_ofertas(self):
        if not self.tienda_id:
            show_toast("Selecciona una tienda primero", "warning", self)
            return
        OfferWindow(self, self.db, self.tienda_id,
                    callback=self._reload).exec()

    def abrir_categorias(self):
        CategoryWindow(self, self.db, callback=self._reload).exec()

    # ── Cierre de caja ─────────────────────────────────────────────────────────
    def cerrar_caja(self):
        if not self.tienda_id:
            show_toast("Selecciona una tienda primero", "warning", self)
            return

        r = QMessageBox.question(
            self,
            "Cerrar Caja",
            "Estas por cerrar la caja.\n\n"
            "Se registraran todas las ventas pendientes desde el ultimo cierre.\n\n"
            "Continuar?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if r != QMessageBox.StandardButton.Yes:
            return

        resultado = self.db.cerrar_caja(self.tienda_id)

        resumen = (
            f"CIERRE REGISTRADO\n\n"
            f"Periodo: {resultado['fecha_apertura'][:16]} "
            f"-> {resultado['fecha_cierre'][:16]}\n\n"
            f"Efectivo:       ${resultado['total_efectivo']:,.2f}\n"
            f"Transferencia:  ${resultado['total_transferencia']:,.2f}\n"
            f"QR:             ${resultado['total_qr']:,.2f}\n\n"
            f"Subtotal items: ${resultado['subtotal_productos']:,.2f}\n"
            f"TOTAL:          ${resultado['total']:,.2f}"
        )
        QMessageBox.information(self, "Caja Cerrada", resumen)
        show_toast("Caja cerrada correctamente", "success", self)

    # ── Seguridad ──────────────────────────────────────────────────────────────
    def _pedir_password(self):
        while True:
            pwd, ok = QInputDialog.getText(
                self, "Contrasena requerida",
                "Introduce la contrasena para continuar:",
                QLineEdit.EchoMode.Password)
            if not ok:
                continue
            if pwd == PASSWORD:
                show_toast("Sesion renovada", "success", self)
                break
            else:
                QMessageBox.critical(self, "Error", "Contrasena incorrecta.")
        self._inactivity_timer.start()

    def on_closing(self):
        self.db.close()
        self.close()