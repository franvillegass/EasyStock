"""
EasyStock — historial de ventas + cierres de caja (PyQt6).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QListWidget, QListWidgetItem,
    QTextEdit, QWidget, QMessageBox, QTabWidget,
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
        self.cierres   = []

        self.setWindowTitle("EasyStock — Historial")
        self.setMinimumSize(900, 560)
        self.setStyleSheet(f"background: {C['bg_panel']};")
        self.setModal(True)

        self._build()
        self._load_ventas()
        self._load_cierres()
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
        hdr_lay.addWidget(AccentBar(C["blue"]))
        lbl = QLabel("  HISTORIAL")
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: bold; color: {C['blue']}; "
            f"background: transparent; padding-left: 12px;")
        hdr_lay.addWidget(lbl)
        root.addWidget(hdr)
        root.addWidget(h_sep())

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: none;
                background: {C['bg_panel']};
            }}
            QTabBar::tab {{
                background: {C['bg_card']};
                color: {C['text_dim']};
                padding: 9px 24px;
                font-weight: bold;
                font-size: 10px;
                border: 1px solid {C['border']};
                border-bottom: none;
                border-radius: 6px 6px 0 0;
                margin-right: 2px;
            }}
            QTabBar::tab:selected {{
                background: {C['bg_panel']};
                color: {C['amber']};
                border-bottom: 2px solid {C['amber']};
            }}
            QTabBar::tab:hover:!selected {{
                background: {C['bg_hover']};
                color: {C['text_hi']};
            }}
        """)
        root.addWidget(self.tabs, 1)

        # Tab ventas
        tab_ventas = QWidget()
        tab_ventas.setStyleSheet(f"background: {C['bg_panel']};")
        self.tabs.addTab(tab_ventas, "  VENTAS  ")
        self._build_tab_ventas(tab_ventas)

        # Tab cierres
        tab_cierres = QWidget()
        tab_cierres.setStyleSheet(f"background: {C['bg_panel']};")
        self.tabs.addTab(tab_cierres, "  CIERRES DE CAJA  ")
        self._build_tab_cierres(tab_cierres)

        root.addWidget(h_sep())

        # Footer
        foot = QWidget()
        foot.setStyleSheet(f"background: {C['bg_panel']};")
        foot_lay = QHBoxLayout(foot)
        foot_lay.setContentsMargins(20, 10, 20, 16)

        self.btn_del  = make_btn("x  ELIMINAR VENTA", "danger", min_w=180, h=38)
        btn_close     = make_btn("CERRAR",            "ghost",  min_w=110, h=38)
        self.btn_del.clicked.connect(self._eliminar_venta)
        btn_close.clicked.connect(self.accept)

        foot_lay.addWidget(self.btn_del)
        foot_lay.addStretch()
        foot_lay.addWidget(btn_close)
        root.addWidget(foot)

    # ── Tab: Ventas ───────────────────────────────────────────────────────────
    def _build_tab_ventas(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {C['border']}; }}")

        # Lista
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
        lbl_v = QLabel("VENTAS")
        lbl_v.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        lh.addWidget(lbl_v)
        left_lay.addWidget(lhdr)

        self.list_ventas = QListWidget()
        self.list_ventas.setAlternatingRowColors(True)
        self.list_ventas.setStyleSheet(self._list_style())
        self.list_ventas.currentRowChanged.connect(self._on_venta_select)
        left_lay.addWidget(self.list_ventas, 1)
        splitter.addWidget(left)

        # Detalle
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
        lbl_d = QLabel("DETALLE")
        lbl_d.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        rh.addWidget(lbl_d)
        right_lay.addWidget(rhdr)

        self.txt_venta = QTextEdit()
        self.txt_venta.setReadOnly(True)
        self.txt_venta.setStyleSheet(
            f"QTextEdit {{ background: {C['bg_panel']}; border: none; "
            f"color: {C['text_hi']}; padding: 12px; font-size: 12px; }}")
        right_lay.addWidget(self.txt_venta, 1)
        splitter.addWidget(right)

        splitter.setSizes([340, 520])
        lay.addWidget(splitter, 1)

    # ── Tab: Cierres ──────────────────────────────────────────────────────────
    def _build_tab_cierres(self, parent: QWidget):
        lay = QVBoxLayout(parent)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(
            f"QSplitter::handle {{ background: {C['border']}; }}")

        # Lista cierres
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
        lbl_c = QLabel("CIERRES")
        lbl_c.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        lh.addWidget(lbl_c)
        left_lay.addWidget(lhdr)

        self.list_cierres = QListWidget()
        self.list_cierres.setAlternatingRowColors(True)
        self.list_cierres.setStyleSheet(self._list_style())
        self.list_cierres.currentRowChanged.connect(self._on_cierre_select)
        left_lay.addWidget(self.list_cierres, 1)
        splitter.addWidget(left)

        # Detalle cierre
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
        lbl_d = QLabel("DETALLE DEL CIERRE")
        lbl_d.setStyleSheet(
            f"color: {C['amber']}; font-size: 9px; font-weight: bold;")
        rh.addWidget(lbl_d)
        right_lay.addWidget(rhdr)

        self.txt_cierre = QTextEdit()
        self.txt_cierre.setReadOnly(True)
        self.txt_cierre.setStyleSheet(
            f"QTextEdit {{ background: {C['bg_panel']}; border: none; "
            f"color: {C['text_hi']}; padding: 12px; font-size: 12px; }}")
        right_lay.addWidget(self.txt_cierre, 1)
        splitter.addWidget(right)

        splitter.setSizes([340, 520])
        lay.addWidget(splitter, 1)

    # ── Helpers de estilo ─────────────────────────────────────────────────────
    def _list_style(self) -> str:
        return f"""
            QListWidget {{
                background: {C['bg_card']}; border: none; outline: none;
            }}
            QListWidget::item {{
                padding: 9px 14px;
                border-bottom: 1px solid {C['border']};
                font-size: 11px;
            }}
            QListWidget::item:selected {{
                background: {C['bg_select']}; color: {C['amber_glow']};
            }}
            QListWidget::item:hover:!selected {{
                background: {C['bg_hover']};
            }}
        """

    # ── Carga de datos ────────────────────────────────────────────────────────
    def _load_ventas(self):
        self.ventas = self.db.list_ventas(self.tienda_id)
        self.list_ventas.clear()
        for v in self.ventas:
            fecha  = (v["fecha"] or "")[:16]
            metodo = v.get("metodo_pago", "efectivo").upper()
            item   = QListWidgetItem(
                f"  {fecha}   [{metodo}]   ${float(v['total']):>10,.2f}")
            item.setData(Qt.ItemDataRole.UserRole, v["id"])
            self.list_ventas.addItem(item)

    def _load_cierres(self):
        self.cierres = self.db.list_cierres(self.tienda_id)
        self.list_cierres.clear()
        for c in self.cierres:
            fecha = (c["fecha_cierre"] or "")[:16]
            item  = QListWidgetItem(
                f"  {fecha}   ${float(c['total']):>10,.2f}")
            item.setData(Qt.ItemDataRole.UserRole, c["id"])
            self.list_cierres.addItem(item)

    # ── Seleccion venta ───────────────────────────────────────────────────────
    def _on_venta_select(self, row: int):
        if row < 0 or row >= len(self.ventas):
            return
        venta = self.ventas[row]
        items = self.db.list_items_by_venta(venta["id"])
        fecha  = (venta["fecha"] or "")[:16]
        metodo = venta.get("metodo_pago", "efectivo").upper()
        desc_g = float(venta.get("descuento_total", 0))

        self.txt_venta.clear()
        cur = self.txt_venta.textCursor()

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
        append(f"Metodo de pago: {metodo}\n", color=C["blue"], bold=True)
        append("─" * 52 + "\n", color=C["text_dim"])

        subtotal_items = 0.0
        if items:
            for it in items:
                nombre   = it["producto"][:28]
                qty      = it["cantidad"]
                precio_b = float(it["precio"])
                desc_i   = float(it.get("descuento_item", 0))
                sub      = float(it["subtotal"])
                es_of    = it.get("es_oferta", 0)

                color_n = C["amber"] if es_of else C["text_hi"]
                append(f"  {nombre:<28}", color=color_n)
                append(f"  x{qty}  ", color=C["text_mid"])
                if desc_i > 0:
                    append(f"(-{desc_i:.1f}%)  ", color=C["amber_dim"])
                append(f"${sub:,.2f}\n", color=C["text_hi"], bold=True)
                subtotal_items += sub

            append("─" * 52 + "\n", color=C["text_dim"])
            append(f"\n  Subtotal items    ${subtotal_items:,.2f}\n",
                   color=C["text_mid"])
            if desc_g > 0:
                append(f"  Descuento global  -{desc_g:.1f}%\n",
                       color=C["amber_dim"], bold=True)
            append(f"\n  TOTAL  ${float(venta['total']):,.2f}\n",
                   color=C["green"], bold=True, size=14)
        else:
            append("  Sin items registrados.\n", color=C["text_dim"])

    # ── Seleccion cierre ──────────────────────────────────────────────────────
    def _on_cierre_select(self, row: int):
        if row < 0 or row >= len(self.cierres):
            return
        cierre = self.cierres[row]
        ventas = self.db.list_ventas_by_cierre(cierre["id"])

        self.txt_cierre.clear()
        cur = self.txt_cierre.textCursor()

        def append(text, color=None, bold=False, size=None):
            fmt = QTextCharFormat()
            if color:
                fmt.setForeground(QColor(color))
            if bold:
                fmt.setFontWeight(QFont.Weight.Bold)
            if size:
                fmt.setFontPointSize(size)
            cur.insertText(text, fmt)

        apertura = (cierre["fecha_apertura"] or "")[:16]
        cierre_f = (cierre["fecha_cierre"]   or "")[:16]

        append(f"Cierre #{cierre['id']}\n", color=C["amber"], bold=True, size=13)
        append(f"Apertura: {apertura}\n",   color=C["text_mid"])
        append(f"Cierre:   {cierre_f}\n",   color=C["text_mid"])
        append("─" * 52 + "\n", color=C["text_dim"])

        # Ventas incluidas
        append(f"\n  VENTAS ({len(ventas)})\n", color=C["blue"], bold=True)
        for v in ventas:
            fecha  = (v["fecha"] or "")[:16]
            metodo = v.get("metodo_pago", "efectivo").upper()
            append(f"  {fecha}  [{metodo}]  ${float(v['total']):,.2f}\n",
                   color=C["text_hi"])

        append("\n" + "─" * 52 + "\n", color=C["text_dim"])

        # Subtotales por metodo
        append("\n  POR METODO DE PAGO\n", color=C["amber"], bold=True)
        ef  = float(cierre["total_efectivo"])
        tr  = float(cierre["total_transferencia"])
        qr  = float(cierre["total_qr"])
        sub = float(cierre["subtotal_productos"])
        tot = float(cierre["total"])

        append(f"  Efectivo       ${ef:,.2f}\n",      color=C["green"])
        append(f"  Transferencia  ${tr:,.2f}\n",      color=C["blue"])
        append(f"  QR             ${qr:,.2f}\n",      color=C["purple"])
        append("─" * 52 + "\n", color=C["text_dim"])
        append(f"  Subtotal items ${sub:,.2f}\n",     color=C["text_mid"])
        append(f"\n  TOTAL  ${tot:,.2f}\n",
               color=C["amber"], bold=True, size=14)

    # ── Eliminar venta ────────────────────────────────────────────────────────
    def _eliminar_venta(self):
        if self.tabs.currentIndex() != 0:
            return
        row = self.list_ventas.currentRow()
        if row < 0:
            return
        venta = self.ventas[row]
        fecha = (venta["fecha"] or "")[:16]
        r = QMessageBox.question(
            self, "Confirmar", f"Eliminar venta del {fecha}?")
        if r == QMessageBox.StandardButton.Yes:
            self.db.delete_venta(venta["id"])
            self._load_ventas()
            self.txt_venta.clear()