"""
EasyStock — panel de estadísticas (PyQt6 + matplotlib).
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget,
    QLabel, QComboBox, QTabWidget, QRadioButton,
    QButtonGroup, QTableWidget, QTableWidgetItem,
    QHeaderView, QSplitter, QSizePolicy,
)
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QTimer
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from PyQt6.QtGui import QColor

import matplotlib
matplotlib.use("QtAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.ticker as mticker

from easystock.config import C
from easystock.database import DBManager
from easystock.ui.widgets import (
    make_btn, h_sep, AccentBar, KPICard, SectionPanel
)


# ── Matplotlib helpers ────────────────────────────────────────────────────────
def _style_ax(ax, fig):
    fig.patch.set_facecolor(C["chart_bg"])
    ax.set_facecolor(C["chart_bg"])
    for spine in ax.spines.values():
        spine.set_color(C["border"])
        spine.set_linewidth(0.5)
    ax.tick_params(colors=C["text_mid"], labelsize=7.5, length=3)
    ax.xaxis.label.set_color(C["text_mid"])
    ax.yaxis.label.set_color(C["text_mid"])
    ax.title.set_color(C["text_hi"])
    ax.grid(True, color=C["chart_grid"], linestyle="--",
            linewidth=0.4, alpha=0.8, zorder=0)
    ax.set_axisbelow(True)


def _money_fmt(ax):
    ax.yaxis.set_major_formatter(
        mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))


def _xlabels(ax, labels, max_n=8):
    n    = len(labels)
    step = max(1, n // max_n)
    ax.set_xticks(range(0, n, step))
    ax.set_xticklabels(labels[::step], rotation=32,
                       ha="right", fontsize=7)


def make_canvas(parent=None) -> tuple:
    fig = Figure(figsize=(5, 3.2), dpi=92)
    fig.patch.set_facecolor(C["chart_bg"])
    ax  = fig.add_subplot(111)
    _style_ax(ax, fig)
    canvas = FigureCanvasQTAgg(fig)
    canvas.setStyleSheet(f"background: {C['chart_bg']};")
    if parent:
        canvas.setParent(parent)
    return fig, ax, canvas


# ── StatsWindow ───────────────────────────────────────────────────────────────
class StatsWindow(QDialog):
    PERIODOS = [("semana", "SEMANA"), ("mes", "MES"),
                ("año", "AÑO"), ("siempre", "SIEMPRE")]

    def __init__(self, parent, db: DBManager,
                 tienda_id: int, nombre_tienda: str):
        super().__init__(parent)
        self.db            = db
        self.tienda_id     = tienda_id
        self.nombre_tienda = nombre_tienda

        self.setWindowTitle(f"EasyStock — Estadísticas · {nombre_tienda}")
        self.setMinimumSize(1300, 800)
        self.setStyleSheet(f"background: {C['bg_deep']};")
        self.setModal(False)

        self._build()
        self._animate_in()
        QTimer.singleShot(60, self._refresh_all)

    def _animate_in(self):
        fx = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(fx)
        anim = QPropertyAnimation(fx, b"opacity", self)
        anim.setDuration(280)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    # ── Layout ────────────────────────────────────────────────────────────────
    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──
        topbar = QWidget()
        topbar.setFixedHeight(62)
        topbar.setStyleSheet(f"background: {C['bg_deep']};")
        tb_lay = QHBoxLayout(topbar)
        tb_lay.setContentsMargins(0, 0, 20, 0)
        tb_lay.setSpacing(0)

        tb_lay.addWidget(AccentBar(C["amber"]))

        lbl_stats = QLabel("  ESTADÍSTICAS")
        lbl_stats.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {C['amber']}; background: transparent; padding-left: 14px;")
        lbl_tienda = QLabel(f"  /  {self.nombre_tienda.upper()}")
        lbl_tienda.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {C['text_mid']}; background: transparent;")

        tb_lay.addWidget(lbl_stats)
        tb_lay.addWidget(lbl_tienda)
        tb_lay.addStretch()

        btn_refresh = make_btn("↺  ACTUALIZAR", "ghost", min_w=150, h=36)
        btn_close   = make_btn("✕  CERRAR",     "ghost", min_w=120, h=36)
        btn_refresh.clicked.connect(self._refresh_all)
        btn_close.clicked.connect(self.accept)

        tb_lay.addWidget(btn_refresh)
        tb_lay.addWidget(btn_close)
        root.addWidget(topbar)
        root.addWidget(h_sep())

        # ── KPI row ──
        kpi_row = QWidget()
        kpi_row.setStyleSheet(f"background: {C['bg_deep']};")
        kpi_lay = QHBoxLayout(kpi_row)
        kpi_lay.setContentsMargins(20, 14, 20, 14)
        kpi_lay.setSpacing(12)

        self.kpi_ingresos  = KPICard("Ingresos este mes",     C["amber"])
        self.kpi_ventas    = KPICard("Ventas este mes",       C["blue"])
        self.kpi_unidades  = KPICard("Unidades vendidas",     C["green"])
        self.kpi_historico = KPICard("Ingresos históricos",   C["purple"])

        for kpi in [self.kpi_ingresos, self.kpi_ventas,
                    self.kpi_unidades, self.kpi_historico]:
            kpi.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            kpi_lay.addWidget(kpi)

        root.addWidget(kpi_row)
        root.addWidget(h_sep())

        # ── Tabs ──
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { margin-top: 0; }")
        root.addWidget(self.tabs, 1)

        tab_charts = QWidget()
        tab_charts.setStyleSheet(f"background: {C['bg_panel']};")
        self.tabs.addTab(tab_charts, "  GRÁFICOS DE TIEMPO  ")
        self._build_tab_charts(tab_charts)

        tab_top = QWidget()
        tab_top.setStyleSheet(f"background: {C['bg_panel']};")
        self.tabs.addTab(tab_top, "  TOP PRODUCTOS  ")
        self._build_tab_top(tab_top)

    # ── Tab: Gráficos ─────────────────────────────────────────────────────────
    def _build_tab_charts(self, parent: QWidget):
        root = QVBoxLayout(parent)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Controles
        ctrl = QWidget()
        ctrl.setStyleSheet(f"background: {C['bg_card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        ctrl_lay = QHBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(14, 8, 14, 8)
        ctrl_lay.setSpacing(16)

        lbl_p = QLabel("PRODUCTO")
        lbl_p.setProperty("role", "tag")
        self.cb_producto = QComboBox()
        self.cb_producto.setMinimumWidth(240)
        self.cb_producto.currentTextChanged.connect(lambda _: self._refresh_charts())

        sep1 = QLabel("│")
        sep1.setStyleSheet(f"color: {C['border']}; font-size: 18px;")

        lbl_a = QLabel("AGRUPACIÓN")
        lbl_a.setProperty("role", "tag")

        self._grp_agrup = QButtonGroup(self)
        self._agrup_btns = {}
        for val, label in [("dia","DÍA"), ("semana","SEMANA"), ("mes","MES")]:
            rb = QRadioButton(label)
            self._grp_agrup.addButton(rb)
            self._agrup_btns[val] = rb
            rb.toggled.connect(lambda checked, v=val: checked and self._refresh_charts())
            ctrl_lay.addWidget(rb) if val != "dia" else None
        self._agrup_btns["dia"].setChecked(True)

        ctrl_lay.addWidget(lbl_p)
        ctrl_lay.addWidget(self.cb_producto)
        ctrl_lay.addWidget(sep1)
        ctrl_lay.addWidget(lbl_a)
        for val in ["dia", "semana", "mes"]:
            ctrl_lay.addWidget(self._agrup_btns[val])
        ctrl_lay.addStretch()

        root.addWidget(ctrl)

        # Grid 2×2 de gráficos
        top_row = QWidget()
        top_row.setStyleSheet("background: transparent;")
        top_lay = QHBoxLayout(top_row)
        top_lay.setContentsMargins(0, 0, 0, 0)
        top_lay.setSpacing(10)

        bot_row = QWidget()
        bot_row.setStyleSheet("background: transparent;")
        bot_lay = QHBoxLayout(bot_row)
        bot_lay.setContentsMargins(0, 0, 0, 0)
        bot_lay.setSpacing(10)

        def wrap_canvas(canvas):
            w = QWidget()
            w.setStyleSheet(f"background: {C['chart_bg']}; border: 1px solid {C['border']}; border-radius: 6px;")
            lay = QVBoxLayout(w)
            lay.setContentsMargins(4, 4, 4, 4)
            lay.addWidget(canvas)
            return w

        self.fig1, self.ax1, self.cv1 = make_canvas()
        self.fig2, self.ax2, self.cv2 = make_canvas()
        self.fig3, self.ax3, self.cv3 = make_canvas()
        self.fig4, self.ax4, self.cv4 = make_canvas()

        top_lay.addWidget(wrap_canvas(self.cv1), 1)
        top_lay.addWidget(wrap_canvas(self.cv2), 1)
        bot_lay.addWidget(wrap_canvas(self.cv3), 1)
        bot_lay.addWidget(wrap_canvas(self.cv4), 1)

        root.addWidget(top_row, 1)
        root.addWidget(bot_row, 1)

    # ── Tab: Top productos ────────────────────────────────────────────────────
    def _build_tab_top(self, parent: QWidget):
        root = QVBoxLayout(parent)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(10)

        # Controles
        ctrl = QWidget()
        ctrl.setStyleSheet(f"background: {C['bg_card']}; border: 1px solid {C['border']}; border-radius: 6px;")
        ctrl_lay = QHBoxLayout(ctrl)
        ctrl_lay.setContentsMargins(14, 8, 14, 8)
        ctrl_lay.setSpacing(10)

        lbl = QLabel("PERÍODO")
        lbl.setProperty("role", "tag")
        ctrl_lay.addWidget(lbl)

        self._grp_periodo = QButtonGroup(self)
        self._periodo_btns = {}
        for val, label in self.PERIODOS:
            rb = QRadioButton(label)
            self._grp_periodo.addButton(rb)
            self._periodo_btns[val] = rb
            rb.toggled.connect(lambda checked, v=val: checked and self._refresh_top())
            ctrl_lay.addWidget(rb)
        self._periodo_btns["mes"].setChecked(True)
        ctrl_lay.addStretch()
        root.addWidget(ctrl)

        # Dos tablas lado a lado
        tables_row = QWidget()
        tables_row.setStyleSheet("background: transparent;")
        tables_lay = QHBoxLayout(tables_row)
        tables_lay.setContentsMargins(0, 0, 0, 0)
        tables_lay.setSpacing(12)

        self.tbl_ing = self._make_table(
            ["#", "Producto", "Ingresos $", "Unidades"],
            "💰  MÁS INGRESOS", C["amber"])
        self.tbl_uni = self._make_table(
            ["#", "Producto", "Unidades", "Ingresos $"],
            "📦  MÁS UNIDADES", C["blue"])

        tables_lay.addWidget(self.tbl_ing[0], 1)
        tables_lay.addWidget(self.tbl_uni[0], 1)
        root.addWidget(tables_row, 1)

    def _make_table(self, columns: list[str],
                    title: str, accent: str) -> tuple:
        """Retorna (container_widget, QTableWidget)."""
        panel = SectionPanel(title, accent)

        tbl = QTableWidget()
        tbl.setColumnCount(len(columns))
        tbl.setHorizontalHeaderLabels(columns)
        tbl.setAlternatingRowColors(True)
        tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        tbl.verticalHeader().setVisible(False)
        tbl.setShowGrid(False)
        tbl.setSortingEnabled(False)
        tbl.setStyleSheet(f"""
            QTableWidget {{
                background: {C['bg_card']};
                alternate-background-color: {C['bg_panel']};
                border: none;
                selection-background-color: {C['bg_select']};
                selection-color: {C['amber_glow']};
                gridline-color: {C['border']};
                outline: none;
            }}
            QTableWidget::item {{
                padding: 5px 10px;
                border-bottom: 1px solid {C['border']};
                font-size: 11px;
            }}
            QTableWidget::item:hover {{
                background: {C['bg_hover']};
            }}
            QHeaderView::section {{
                background: {C['bg_input']};
                color: {accent};
                font-size: 9px;
                font-weight: bold;
                padding: 6px 10px;
                border: none;
                border-right: 1px solid {C['border']};
                border-bottom: 1px solid {C['border']};
            }}
        """)

        hdr = tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        tbl.setColumnWidth(0, 36)
        if len(columns) > 1:
            hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, len(columns)):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
            tbl.setColumnWidth(i, 110)

        panel.layout_body.addWidget(tbl)
        return panel, tbl

    # ── Refresh ───────────────────────────────────────────────────────────────
    def _refresh_all(self):
        self._refresh_kpis()
        self._load_combo()
        self._refresh_charts()
        self._refresh_top()

    def _refresh_kpis(self):
        r = self.db.resumen_tienda(self.tienda_id)
        self.kpi_ingresos.animate_to(float(r["total_mes"]),   prefix="$", decimals=2)
        self.kpi_ventas.animate_to(int(r["ventas_mes"]),      decimals=0)
        self.kpi_unidades.animate_to(int(r["uds_mes"]),       decimals=0)
        self.kpi_historico.animate_to(float(r["total_historico"]), prefix="$", decimals=2)

    def _load_combo(self):
        prods = self.db.productos_con_ventas(self.tienda_id)
        self.cb_producto.blockSignals(True)
        self.cb_producto.clear()
        if prods:
            self.cb_producto.addItems(prods)
        else:
            self.cb_producto.addItem("(sin ventas)")
        self.cb_producto.blockSignals(False)

    def _get_agrupacion(self) -> str:
        for val, btn in self._agrup_btns.items():
            if btn.isChecked():
                return val
        return "dia"

    def _get_periodo(self) -> str:
        for val, btn in self._periodo_btns.items():
            if btn.isChecked():
                return val
        return "mes"

    def _refresh_charts(self):
        if not hasattr(self, "ax1"):
            return
        producto   = self.cb_producto.currentText()
        agrupacion = self._get_agrupacion()

        periodos, unidades, ingresos = self.db.serie_tiempo_producto(
            self.tienda_id, producto, agrupacion)

        # Chart 1: ingresos del producto (línea + área)
        self.ax1.clear()
        _style_ax(self.ax1, self.fig1)
        if periodos:
            xs = list(range(len(periodos)))
            self.ax1.plot(xs, ingresos, color=C["chart_line"],
                          linewidth=2, marker="o", markersize=3.5, zorder=3)
            self.ax1.fill_between(xs, ingresos, alpha=0.12,
                                   color=C["chart_line"])
            _xlabels(self.ax1, periodos)
            _money_fmt(self.ax1)
        short = producto[:26]
        self.ax1.set_title(f"Ingresos · {short}", fontsize=9, pad=6,
                           color=C["text_hi"], fontfamily="monospace")
        self.fig1.tight_layout(pad=1.6)
        self.cv1.draw()

        # Chart 2: unidades del producto (barras)
        self.ax2.clear()
        _style_ax(self.ax2, self.fig2)
        if periodos:
            xs = list(range(len(periodos)))
            bars = self.ax2.bar(xs, unidades, color=C["chart_bar"],
                                alpha=0.82, width=0.6, zorder=3)
            for bar, val in zip(bars, unidades):
                if val > 0:
                    self.ax2.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height(), f"{int(val)}",
                        ha="center", va="bottom",
                        color=C["chart_bar"], fontsize=7)
            _xlabels(self.ax2, periodos)
        self.ax2.set_title(f"Unidades · {short}", fontsize=9, pad=6,
                           color=C["text_hi"], fontfamily="monospace")
        self.fig2.tight_layout(pad=1.6)
        self.cv2.draw()

        # Chart 3: ingresos totales tienda últimos 30d
        self.ax3.clear()
        _style_ax(self.ax3, self.fig3)
        dias, ing_total = self.db.ingresos_por_dia(self.tienda_id, dias=30)
        if dias:
            xs = list(range(len(dias)))
            self.ax3.fill_between(xs, ing_total, alpha=0.15,
                                   color=C["chart_bar2"])
            self.ax3.plot(xs, ing_total, color=C["chart_bar2"],
                          linewidth=2, marker="o", markersize=3, zorder=3)
            _xlabels(self.ax3, dias)
            _money_fmt(self.ax3)
        self.ax3.set_title("Ingresos totales · 30 días",
                           fontsize=9, pad=6,
                           color=C["text_hi"], fontfamily="monospace")
        self.fig3.tight_layout(pad=1.6)
        self.cv3.draw()

        # Chart 4: top 5 barras horizontales
        self.ax4.clear()
        _style_ax(self.ax4, self.fig4)
        top5 = self.db.top_productos(
            self.tienda_id, periodo="siempre", metrica="ingresos", limit=5)
        if top5:
            nombres = [r["producto"][:22] for r in top5][::-1]
            vals    = [float(r["ingresos"]) for r in top5][::-1]
            colors  = [C["amber"] if i == len(top5) - 1 else C["chart_bar"]
                       for i in range(len(top5))][::-1]
            bars = self.ax4.barh(nombres, vals, color=colors,
                                  alpha=0.86, height=0.55)
            mx = max(vals) if vals else 1
            for bar, val in zip(bars, vals):
                self.ax4.text(
                    val + mx * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    f"${val:,.0f}", va="center", ha="left",
                    color=C["text_mid"], fontsize=7)
        self.ax4.set_title("Top 5 por ingresos (histórico)",
                           fontsize=9, pad=6,
                           color=C["text_hi"], fontfamily="monospace")
        self.ax4.xaxis.set_major_formatter(
            mticker.FuncFormatter(lambda x, _: f"${x:,.0f}"))
        self.fig4.tight_layout(pad=1.6)
        self.cv4.draw()

    def _refresh_top(self):
        if not hasattr(self, "tbl_ing"):
            return
        periodo = self._get_periodo()

        # Tabla ingresos
        top_ing = self.db.top_productos(
            self.tienda_id, periodo=periodo, metrica="ingresos", limit=20)
        tbl = self.tbl_ing[1]
        tbl.setRowCount(0)
        for i, r in enumerate(top_ing):
            tbl.insertRow(i)
            self._set_row(tbl, i, [
                str(i + 1),
                r["producto"],
                f"${float(r['ingresos']):,.2f}",
                str(int(r["unidades"])),
            ], highlight=(i == 0))

        # Tabla unidades
        top_uni = self.db.top_productos(
            self.tienda_id, periodo=periodo, metrica="unidades", limit=20)
        tbl2 = self.tbl_uni[1]
        tbl2.setRowCount(0)
        for i, r in enumerate(top_uni):
            tbl2.insertRow(i)
            self._set_row(tbl2, i, [
                str(i + 1),
                r["producto"],
                str(int(r["unidades"])),
                f"${float(r['ingresos']):,.2f}",
            ], highlight=(i == 0))

    def _set_row(self, tbl: QTableWidget, row: int,
                 values: list[str], highlight: bool = False):
        for col, val in enumerate(values):
            item = QTableWidgetItem(val)
            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter if col in (0, 2, 3)
                else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            if highlight:
                item.setForeground(QColor(C["amber_glow"]))
            tbl.setItem(row, col, item)
