"""
EasyStock — impresion de ticket (PyQt6).
Funciona con cualquier impresora instalada en el sistema.
Genera un ticket minimalista en formato termico (ancho fijo ~280px).
"""
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from PyQt6.QtGui import QPainter, QFont, QFontMetrics
from PyQt6.QtCore import Qt, QRectF


# ancho del ticket en mm (tipico termico 58mm o 80mm, usamos 72mm como base)
TICKET_WIDTH_MM  = 72
MARGIN_MM        = 4
LINE_HEIGHT_PT   = 11
FONT_NORMAL      = ("Courier New", 9)
FONT_BOLD        = ("Courier New", 9)
FONT_TITLE       = ("Courier New", 11)
FONT_TOTAL       = ("Courier New", 13)
CHARS_PER_LINE   = 32  # aprox para 72mm con Courier 9pt


def _mm_to_px(mm: float, dpi: int) -> float:
    return mm * dpi / 25.4


def imprimir_ticket(parent, venta_data: dict):
    """
    venta_data debe tener:
        - items: list[dict] con keys: producto, cantidad, precio,
                 descuento_item, subtotal, es_oferta
        - total: float
        - metodo_pago: str
        - descuento_total: float
        - fecha: str
        - venta_id: int
    """
    printer = QPrinter(QPrinter.PrinterMode.HighResolution)
    printer.setPageSize(printer.pageLayout().pageSize())

    dlg = QPrintDialog(printer, parent)
    dlg.setWindowTitle("Imprimir Ticket")
    if dlg.exec() != QPrintDialog.DialogCode.Accepted:
        return

    dpi    = printer.resolution()
    margin = _mm_to_px(MARGIN_MM, dpi)
    width  = printer.pageRect(QPrinter.Unit.DevicePixel).width() - margin * 2

    painter = QPainter(printer)
    painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)

    x   = margin
    y   = margin
    lh  = _mm_to_px(LINE_HEIGHT_PT * 0.353, dpi)  # pt a mm a px

    def set_font(family, size, bold=False):
        f = QFont(family, size)
        f.setBold(bold)
        # escalar size a DPI del printer
        f.setPixelSize(int(_mm_to_px(size * 0.353, dpi)))
        painter.setFont(f)

    def line_height() -> float:
        return QFontMetrics(painter.font()).height() * 1.25

    def draw_text(text: str, align=Qt.AlignmentFlag.AlignLeft, color=None):
        nonlocal y
        if color:
            painter.setPen(color)
        else:
            from PyQt6.QtGui import QColor
            painter.setPen(QColor("#000000"))
        lh_cur = line_height()
        rect = QRectF(x, y, width, lh_cur * 2)
        painter.drawText(rect, align | Qt.TextFlag.TextWordWrap, text)
        # avanzar segun lineas reales
        lines = max(1, len(text) // CHARS_PER_LINE + 1)
        y += lh_cur * lines

    def draw_sep(char="-"):
        draw_text(char * CHARS_PER_LINE)

    def draw_sep_double():
        draw_text("=" * CHARS_PER_LINE)

    def draw_blank():
        nonlocal y
        set_font(*FONT_NORMAL)
        y += line_height() * 0.6

    # ── Contenido del ticket ──────────────────────────────────────────────────

    draw_blank()

    # Titulo
    set_font(*FONT_TITLE, bold=True)
    draw_text("EASYSTOCK", Qt.AlignmentFlag.AlignCenter)
    draw_blank()

    # Fecha y numero
    set_font(*FONT_NORMAL)
    fecha = (venta_data.get("fecha") or "")[:16]
    draw_text(f"Fecha: {fecha}")
    draw_text(f"Venta #: {venta_data.get('venta_id', '-')}")
    draw_blank()
    draw_sep_double()

    # Items
    set_font(*FONT_NORMAL)
    items = venta_data.get("items", [])
    for it in items:
        nombre   = str(it["producto"])[:22]
        qty      = int(it["cantidad"])
        precio   = float(it["precio"])
        desc_i   = float(it.get("descuento_item", 0))
        subtotal = float(it["subtotal"])

        # Linea nombre x cantidad
        left_part  = f"{nombre}"
        right_part = f"x{qty}"
        pad = CHARS_PER_LINE - len(left_part) - len(right_part)
        draw_text(left_part + " " * max(1, pad) + right_part)

        # Linea precio unitario + descuento + subtotal
        precio_str = f"  ${precio:.2f}"
        if desc_i > 0:
            precio_str += f" -{desc_i:.0f}%"
        sub_str = f"${subtotal:.2f}"
        pad2 = CHARS_PER_LINE - len(precio_str) - len(sub_str)
        set_font(*FONT_NORMAL, bold=True)
        draw_text(precio_str + " " * max(1, pad2) + sub_str)
        set_font(*FONT_NORMAL)

    draw_sep_double()
    draw_blank()

    # Subtotal items
    subtotal_items = sum(float(it["subtotal"]) for it in items)
    set_font(*FONT_NORMAL)
    sub_label = "Subtotal"
    sub_val   = f"${subtotal_items:.2f}"
    pad = CHARS_PER_LINE - len(sub_label) - len(sub_val)
    draw_text(sub_label + " " * max(1, pad) + sub_val)

    # Descuento global
    desc_g = float(venta_data.get("descuento_total", 0))
    if desc_g > 0:
        desc_label = f"Descuento global"
        desc_val   = f"-{desc_g:.1f}%"
        pad = CHARS_PER_LINE - len(desc_label) - len(desc_val)
        draw_text(desc_label + " " * max(1, pad) + desc_val)

    draw_blank()

    # Total
    set_font(*FONT_TOTAL, bold=True)
    total     = float(venta_data.get("total", 0))
    tot_label = "TOTAL"
    tot_val   = f"${total:.2f}"
    pad = CHARS_PER_LINE - len(tot_label) - len(tot_val)
    draw_text(tot_label + " " * max(1, pad) + tot_val)

    draw_blank()

    # Metodo de pago
    set_font(*FONT_NORMAL)
    metodo = str(venta_data.get("metodo_pago", "efectivo")).upper()
    draw_text(f"Pago: {metodo}")

    draw_blank()
    draw_sep()
    draw_blank()

    # Pie
    set_font("Courier New", 8)
    draw_text("Gracias por su compra", Qt.AlignmentFlag.AlignCenter)
    draw_blank()

    painter.end()