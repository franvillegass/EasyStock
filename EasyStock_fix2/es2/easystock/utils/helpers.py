


def bring_to_front(win):
    win.lift()
    win.attributes("-topmost", True)
    win.after(50, lambda: win.attributes("-topmost", False))
    win.focus_force()


def lerp(a: float, b: float, t: float) -> float:
    """Interpolación lineal entre a y b con t ∈ [0,1]."""
    return a + (b - a) * t


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def interpolate_color(color_a: str, color_b: str, t: float) -> str:
    """Interpola dos colores hex y devuelve hex resultante."""
    ra, ga, ba = hex_to_rgb(color_a)
    rb, gb, bb = hex_to_rgb(color_b)
    r = int(lerp(ra, rb, t))
    g = int(lerp(ga, gb, t))
    b = int(lerp(ba, bb, t))
    return f"#{r:02x}{g:02x}{b:02x}"


def animate_value(widget, attr: str, start: float, end: float,
                  duration_ms: int, steps: int = 12, callback=None):
    """
    Anima un atributo numérico de widget usando .after().
    callback(value) se llama en cada paso; al finalizar se llama con end.
    """
    if steps <= 0 or duration_ms <= 0:
        if callback:
            callback(end)
        return

    interval = duration_ms // steps

    def _step(i):
        t = i / steps
        # ease-out cuadratic
        t_eased = 1 - (1 - t) ** 2
        val = lerp(start, end, t_eased)
        if callback:
            callback(val)
        if i < steps:
            widget.after(interval, lambda: _step(i + 1))

    _step(1)
