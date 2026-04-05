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
from easystock.ui.store_selector import StoreSelectorDialog
from easystock.ui.product_form   import ProductFormDialog
from easystock.ui.sale_window    import SaleWindow
from easystock.ui.history_window import HistoryWindow
from easystock.ui.stats_window   import StatsWindow
from easystock.config            import PASSWORD, INACTIVITY_MS
from easystock.ui.offer_window import OfferWindow
from easystock.ui.ticket_printer import imprimir_ticket


class MainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EASYSTOCK")
        self.setMinimumSize(1100, 660)
        self.resize(1200, 720)

        self.db             = DBManager()
        self.tienda_id      = None
        self.tienda_nombre  = "—"
        self.productos      = []

        # Crear carpeta de excels si no existe
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

    # ── Animación de apertura ──────────────────────────────────────────────────
    def _animate_open(self):
        fx = QGraphicsOpacityEffect(self.centralWidget())
        self.centralWidget().setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", self)
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


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
            f"→ {resultado['fecha_cierre'][:16]}\n\n"
            f"Efectivo:       ${resultado['total_efectivo']:,.2f}\n"
            f"Transferencia:  ${resultado['total_transferencia']:,.2f}\n"
            f"QR:             ${resultado['total_qr']:,.2f}\n\n"
            f"Subtotal items: ${resultado['subtotal_productos']:,.2f}\n"
            f"TOTAL:          ${resultado['total']:,.2f}"
        )
        QMessageBox.information(self, "Caja Cerrada", resumen)
        show_toast("Caja cerrada correctamente", "success", self)


    # ── Construcción UI ────────────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setStyleSheet(f"background: {C['bg_deep']};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──
        topbar = QWidget()
        topbar.setFixedHeight(60)
        topbar.setStyleSheet(f"background: {C['bg_deep']};")
        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(0, 0, 20, 0)
        tb_lay.setSpacing(0)

        tb_lay.addWidget(AccentBar(C["amber"]))

        lbl_easy = QLabel("  EASY")
        lbl_easy.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {C['amber']}; background: transparent; padding-left: 14px;")
        lbl_stock = QLabel("STOCK")
        lbl_stock.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {C['text_hi']}; background: transparent;")

        self.lbl_tienda = QLabel("  /  —")
        self.lbl_tienda.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {C['text_dim']}; background: transparent; padding-left: 10px;")

        tb_lay.addWidget(lbl_easy)
        tb_lay.addWidget(lbl_stock)
        tb_lay.addWidget(self.lbl_tienda)
        tb_lay.addStretch()

        btn_cambiar = make_btn("⇄  CAMBIAR TIENDA", "ghost", min_w=180, h=36)
        btn_cambiar.clicked.connect(self._seleccionar_tienda)
        tb_lay.addWidget(btn_cambiar)
        root.addWidget(topbar)
        root.addWidget(h_sep())

        # ── Barra de búsqueda ──
        search_bar = QWidget()
        search_bar.setFixedHeight(52)
        search_bar.setStyleSheet(f"background: {C['bg_panel']};")
        sb_lay = QHBoxLayout(search_bar)
        sb_lay.setContentsMargins(20, 8, 20, 8)
        sb_lay.setSpacing(12)

        lbl_srch = QLabel("🔍")
        lbl_srch.setStyleSheet(f"color: {C['text_dim']}; background: transparent; font-size: 13px;")

        self.f_buscar = QLineEdit()
        self.f_buscar.setPlaceholderText("Buscar producto por nombre o código de barras...")
        self.f_buscar.textChanged.connect(self._filtrar)

        self.lbl_count = QLabel("0 productos")
        self.lbl_count.setStyleSheet(f"color: {C['text_dim']}; font-size: 10px; background: transparent; min-width: 90px;")

        sb_lay.addWidget(lbl_srch)
        sb_lay.addWidget(self.f_buscar, 1)
        sb_lay.addWidget(self.lbl_count)
        root.addWidget(search_bar)
        root.addWidget(h_sep())

        # ── Tabla de productos ──
        tbl_wrapper = QWidget()
        tbl_wrapper.setStyleSheet(f"background: {C['bg_panel']};")
        tbl_lay = QVBoxLayout(tbl_wrapper)
        tbl_lay.setContentsMargins(20, 10, 20, 6)
        tbl_lay.setSpacing(0)

        self.tabla = QTableWidget()
        self.tabla.setColumnCount(4)
        self.tabla.setHorizontalHeaderLabels(["NOMBRE", "STOCK", "PRECIO", "CÓDIGO"])
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

        # ── Barra de acciones ──
        actions = QWidget()
        actions.setFixedHeight(62)
        actions.setStyleSheet(f"background: {C['bg_deep']};")
        act_lay = QHBoxLayout(actions)
        act_lay.setContentsMargins(20, 10, 20, 10)
        act_lay.setSpacing(10)

        # reemplazá btn_defs por:
        btn_defs = [
            ("+ AGREGAR",      "primary", self.abrir_agregar),
            ("EDITAR",         "ghost",   self.abrir_editar),
            ("x  ELIMINAR",    "danger",  self.eliminar_producto),
            ("IMPORTAR XLS",   "ghost",   self.cargar_excel),
            ("OFERTAS",        "ghost",   self.abrir_ofertas),
        ]
        for text, variant, cmd in btn_defs:
            b = make_btn(text, variant, min_w=150, h=40)
            b.clicked.connect(cmd)
            act_lay.addWidget(b)

            act_lay.addWidget(v_sep())

        btn_sale   = make_btn("$  VENTA",        "success", min_w=140, h=40)
        btn_hist   = make_btn("HISTORIAL",        "ghost",   min_w=130, h=40)
        btn_cierre = make_btn("CIERRE DE CAJA",   "danger",  min_w=160, h=40)
        btn_stats  = make_btn("ESTADISTICAS",     "primary", min_w=160, h=40)
 
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

    # ── Selección de tienda ────────────────────────────────────────────────────
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
        self.lbl_count.setText(f"{len(self.productos)} productos")
        self._llenar_tabla(self.f_buscar.text())

    def _llenar_tabla(self, filtro: str = ""):
        filtro = filtro.lower()
        visibles = [p for p in self.productos
                    if filtro in p["nombre"].lower()
                    or filtro in (p.get("codigo_barras") or "").lower()]

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
            precio_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
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
        ProductFormDialog(self, self.db, self.tienda_id, callback=self._reload).exec()

    def abrir_editar(self):
        p = self._get_selected_producto()
        if not p:
            show_toast("Seleccioná un producto primero", "warning", self)
            return
        ProductFormDialog(self, self.db, self.tienda_id,
                          producto=p, callback=self._reload).exec()

    def eliminar_producto(self):
        p = self._get_selected_producto()
        if not p:
            show_toast("Seleccioná un producto primero", "warning", self)
            return
        r = QMessageBox.question(
            self, "Confirmar", f"¿Eliminar '{p['nombre']}'?")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_producto(p["id"])
            self._reload()
            show_toast(f"'{p['nombre']}' eliminado", "info", self)

    def cargar_excel(self):
        if not self.tienda_id:
            show_toast("Seleccioná una tienda primero", "warning", self)
            return

        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar Excel",
            str(self._excels_dir.resolve()),
            "Archivos Excel (*.xlsx *.xls)",
        )
        if not path:
            return  # canceló el diálogo

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
                msg += f" ({omitidos} omitidos por código duplicado)"
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
            show_toast("Seleccioná una tienda primero", "warning", self)
            return
        StatsWindow(self, self.db, self.tienda_id, self.tienda_nombre).exec()

    # ── Seguridad ──────────────────────────────────────────────────────────────
    def _pedir_password(self):
        while True:
            pwd, ok = QInputDialog.getText(
                self, "Contraseña requerida",
                "Introducí la contraseña para continuar:",
                QLineEdit.EchoMode.Password)
            if not ok:
                continue
            if pwd == PASSWORD:
                show_toast("Sesión renovada", "success", self)
                break
            else:
                QMessageBox.critical(self, "Error", "Contraseña incorrecta.")
        self._inactivity_timer.start()

    def on_closing(self):
        self.db.close()
        self.close()