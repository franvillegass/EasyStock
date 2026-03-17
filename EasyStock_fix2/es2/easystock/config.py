"""
EasyStock — configuración global.
Paleta: carbón profundo + acento ámbar eléctrico.
UI: PyQt6 con QSS completo.
"""

# ── App ────────────────────────────────────────────────────────────────────────
DB_FILE        = "EasyStock.db"
PASSWORD       = "2000"
INACTIVITY_MS  = 5 * 60 * 1000

# ── Colores ────────────────────────────────────────────────────────────────────
C = {
    "bg_deep":    "#08080f",
    "bg_panel":   "#0e0e1a",
    "bg_card":    "#13131f",
    "bg_input":   "#1a1a2e",
    "bg_hover":   "#1e1e35",
    "bg_select":  "#252540",
    "bg_sidebar": "#0b0b16",

    "border":     "#252538",
    "border_lit": "#3a3a60",
    "border_focus":"#f5a623",

    "text_hi":    "#eeeef8",
    "text_mid":   "#8888aa",
    "text_dim":   "#44445a",

    "amber":      "#f5a623",
    "amber_dim":  "#a06b10",
    "amber_glow": "#ffd080",
    "amber_bg":   "#2a1e08",

    "green":      "#2ecc71",
    "green_dim":  "#0f3d22",
    "red":        "#e74c3c",
    "red_dim":    "#3d0f0f",
    "blue":       "#3498db",
    "blue_dim":   "#0d2a3d",
    "purple":     "#9b59b6",

    "chart_bg":   "#0a0a14",
    "chart_grid": "#181828",
    "chart_line": "#f5a623",
    "chart_bar":  "#3498db",
    "chart_bar2": "#2ecc71",
    "chart_acc":  "#e74c3c",
    "chart_purple":"#9b59b6",
}

# ── Tipografía ─────────────────────────────────────────────────────────────────
FONT_FAMILY = "JetBrains Mono, Cascadia Code, Consolas, Courier New"
FONT_SIZE   = 11

# ── QSS global ─────────────────────────────────────────────────────────────────
# Se inyecta en QApplication.setStyleSheet() al arrancar.
QSS = f"""
/* ── Reset base ── */
* {{
    font-family: {FONT_FAMILY};
    font-size: {FONT_SIZE}px;
    color: {C['text_hi']};
    outline: none;
}}

QMainWindow, QDialog, QWidget {{
    background-color: {C['bg_deep']};
}}

/* ── Scroll bars ── */
QScrollBar:vertical {{
    background: {C['bg_panel']};
    width: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:vertical {{
    background: {C['border_lit']};
    border-radius: 3px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: {C['amber_dim']};
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{
    background: {C['bg_panel']};
    height: 6px;
    margin: 0;
    border-radius: 3px;
}}
QScrollBar::handle:horizontal {{
    background: {C['border_lit']};
    border-radius: 3px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ── QLineEdit ── */
QLineEdit {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 8px 12px;
    color: {C['text_hi']};
    selection-background-color: {C['amber_dim']};
}}
QLineEdit:focus {{
    border: 1px solid {C['amber']};
}}
QLineEdit:disabled {{
    color: {C['text_dim']};
    background: {C['bg_panel']};
}}

/* ── QPushButton base (solo dialogs nativos de Qt) ── */
/* RoundButton usa paintEvent con AA, no QSS */
QPushButton {{
    background: {C['bg_card']};
    border: 1px solid {C['border']};
    border-radius: 5px;
    padding: 7px 16px;
    color: {C['text_hi']};
    font-weight: bold;
}}
QPushButton:hover {{
    background: {C['bg_hover']};
    border-color: {C['border_lit']};
}}
QPushButton:pressed {{
    background: {C['bg_select']};
}}
QPushButton:disabled {{
    color: {C['text_dim']};
    border-color: {C['border']};
}}

/* ── QLabel ── */
QLabel {{
    background: transparent;
    border: none;
}}
QLabel[role="title"] {{
    font-size: 20px;
    font-weight: bold;
    color: {C['text_hi']};
}}
QLabel[role="subtitle"] {{
    font-size: 13px;
    font-weight: bold;
    color: {C['amber']};
}}
QLabel[role="dim"] {{
    color: {C['text_dim']};
    font-size: 10px;
}}
QLabel[role="kpi_value"] {{
    font-size: 24px;
    font-weight: bold;
    color: {C['amber']};
}}
QLabel[role="kpi_label"] {{
    font-size: 9px;
    font-weight: bold;
    color: {C['text_dim']};
    letter-spacing: 1px;
}}
QLabel[role="tag"] {{
    font-size: 9px;
    font-weight: bold;
    color: {C['text_dim']};
}}
QLabel[role="green"] {{
    color: {C['green']};
    font-weight: bold;
}}
QLabel[role="red"] {{
    color: {C['red']};
    font-weight: bold;
}}
QLabel[role="amber"] {{
    color: {C['amber']};
    font-weight: bold;
}}

/* ── QTableWidget / QTreeWidget ── */
QHeaderView::section {{
    background: {C['bg_input']};
    color: {C['amber']};
    font-weight: bold;
    font-size: 10px;
    padding: 6px 10px;
    border: none;
    border-right: 1px solid {C['border']};
    border-bottom: 1px solid {C['border']};
}}
QTableWidget, QTreeWidget {{
    background: {C['bg_card']};
    alternate-background-color: {C['bg_panel']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    gridline-color: {C['border']};
    selection-background-color: {C['bg_select']};
    selection-color: {C['amber_glow']};
}}
QTableWidget::item, QTreeWidget::item {{
    padding: 4px 8px;
    border: none;
}}
QTableWidget::item:hover, QTreeWidget::item:hover {{
    background: {C['bg_hover']};
}}

/* ── QTabWidget ── */
QTabWidget::pane {{
    border: 1px solid {C['border']};
    border-radius: 0 6px 6px 6px;
    background: {C['bg_panel']};
    top: -1px;
}}
QTabBar::tab {{
    background: {C['bg_card']};
    color: {C['text_dim']};
    padding: 9px 22px;
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
    border-color: {C['border']};
    border-bottom: 2px solid {C['amber']};
}}
QTabBar::tab:hover:!selected {{
    background: {C['bg_hover']};
    color: {C['text_hi']};
}}

/* ── QComboBox ── */
QComboBox {{
    background: {C['bg_input']};
    border: 1px solid {C['border']};
    border-radius: 6px;
    padding: 7px 12px;
    color: {C['text_hi']};
    min-width: 160px;
}}
QComboBox:focus {{
    border-color: {C['amber']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 6px solid {C['text_mid']};
    width: 0; height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background: {C['bg_input']};
    border: 1px solid {C['border_lit']};
    selection-background-color: {C['bg_select']};
    selection-color: {C['amber_glow']};
    outline: none;
}}

/* ── QRadioButton ── */
QRadioButton {{
    spacing: 8px;
    color: {C['text_mid']};
    font-size: 10px;
    font-weight: bold;
}}
QRadioButton:checked {{
    color: {C['amber']};
}}
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

/* ── QMessageBox ── */
QMessageBox {{
    background: {C['bg_panel']};
}}
QMessageBox QLabel {{
    color: {C['text_hi']};
}}
QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ── QInputDialog ── */
QInputDialog {{
    background: {C['bg_panel']};
}}

/* ── QSplitter ── */
QSplitter::handle {{
    background: {C['border']};
    width: 1px;
    height: 1px;
}}

/* ── QFrame separador ── */
QFrame[frameShape="4"],
QFrame[frameShape="5"] {{
    color: {C['border']};
    background: {C['border']};
}}

/* ── Tooltips ── */
QToolTip {{
    background: {C['bg_card']};
    color: {C['text_hi']};
    border: 1px solid {C['amber_dim']};
    border-radius: 4px;
    padding: 4px 8px;
}}
"""
