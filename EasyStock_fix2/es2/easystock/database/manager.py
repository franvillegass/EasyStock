"""
EasyStock — capa de acceso a datos.
Toda interacción con SQLite pasa por DBManager.
"""
import sqlite3
from datetime import datetime, timedelta
from easystock.config import DB_FILE


class DBManager:
    def __init__(self, filename: str = DB_FILE):
        self.conn = sqlite3.connect(filename, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._ensure_schema()

    # ── Schema ──────────────────────────────────────────────────────────────────
    def _ensure_schema(self):
        self.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tiendas (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS productos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre        TEXT    NOT NULL,
            stock         INTEGER NOT NULL DEFAULT 0,
            precio        REAL    NOT NULL DEFAULT 0,
            id_tienda     INTEGER NOT NULL,
            codigo_barras TEXT    UNIQUE
        );

        CREATE TABLE IF NOT EXISTS ventas (
            id       INTEGER   PRIMARY KEY AUTOINCREMENT,
            total    REAL      NOT NULL,
            fecha    TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            id_tienda INTEGER
        );

        CREATE TABLE IF NOT EXISTS venta_items (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id   INTEGER NOT NULL,
            producto_id INTEGER,
            producto   TEXT    NOT NULL,
            cantidad   INTEGER NOT NULL,
            precio     REAL    NOT NULL,
            subtotal   REAL    NOT NULL,
            id_tienda  INTEGER,
            FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
        );
        """)
        # Migraciones silenciosas para bases de datos existentes
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        """Agrega columnas faltantes a tablas existentes."""
        migrations = [
            ("ventas",      "id_tienda",   "INTEGER"),
            ("venta_items", "id_tienda",   "INTEGER"),
            ("venta_items", "producto_id", "INTEGER"),
        ]
        for table, col, typ in migrations:
            try:
                self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass  # ya existe

    # ── Tiendas ────────────────────────────────────────────────────────────────
    def list_tiendas(self) -> list[dict]:
        self.cursor.execute("SELECT id, nombre FROM tiendas ORDER BY id")
        return [dict(r) for r in self.cursor.fetchall()]

    def add_tienda(self, nombre: str) -> int:
        self.cursor.execute("INSERT INTO tiendas (nombre) VALUES (?)", (nombre,))
        self.conn.commit()
        return self.cursor.lastrowid

    def delete_tienda(self, tienda_id: int):
        prods = self.list_productos(tienda_id)
        for p in prods:
            self.delete_producto(p["id"])
        self.cursor.execute("DELETE FROM tiendas WHERE id = ?", (tienda_id,))
        self.conn.commit()

    def rename_tienda(self, tienda_id: int, nuevo_nombre: str):
        self.cursor.execute(
            "UPDATE tiendas SET nombre = ? WHERE id = ?", (nuevo_nombre, tienda_id))
        self.conn.commit()

    # ── Productos ──────────────────────────────────────────────────────────────
    def list_productos(self, id_tienda: int | None = None) -> list[dict]:
        if id_tienda is None:
            self.cursor.execute(
                "SELECT id, nombre, stock, precio, id_tienda, codigo_barras FROM productos")
        else:
            self.cursor.execute(
                "SELECT id, nombre, stock, precio, id_tienda, codigo_barras "
                "FROM productos WHERE id_tienda = ? ORDER BY nombre",
                (id_tienda,))
        return [dict(r) for r in self.cursor.fetchall()]

    def add_producto(self, nombre: str, stock: int, precio: float,
                     id_tienda: int, codigo_barras: str | None = None) -> int:
        self.cursor.execute(
            "INSERT INTO productos (nombre, stock, precio, id_tienda, codigo_barras) "
            "VALUES (?, ?, ?, ?, ?)",
            (nombre, int(stock), float(precio), id_tienda, codigo_barras or None))
        self.conn.commit()
        return self.cursor.lastrowid

    def update_producto(self, prod_id: int, nombre: str, stock: int,
                        precio: float, codigo_barras: str | None):
        self.cursor.execute(
            "UPDATE productos SET nombre=?, stock=?, precio=?, codigo_barras=? WHERE id=?",
            (nombre, int(stock), float(precio), codigo_barras or None, prod_id))
        self.conn.commit()

    def delete_producto(self, prod_id: int):
        self.cursor.execute("DELETE FROM productos WHERE id = ?", (prod_id,))
        self.conn.commit()

    def get_producto_by_barcode(self, codigo: str, id_tienda: int) -> dict | None:
        self.cursor.execute(
            "SELECT * FROM productos WHERE codigo_barras = ? AND id_tienda = ?",
            (codigo, id_tienda))
        r = self.cursor.fetchone()
        return dict(r) if r else None

    # ── Ventas ─────────────────────────────────────────────────────────────────
    def create_venta(self, lineas: list[dict], total: float, tienda_id: int | None = None) -> int:
        self.cursor.execute(
            "INSERT INTO ventas (total, id_tienda) VALUES (?, ?)", (total, tienda_id))
        venta_id = self.cursor.lastrowid
        for l in lineas:
            self.cursor.execute(
                "INSERT INTO venta_items "
                "(venta_id, producto_id, producto, cantidad, precio, subtotal, id_tienda) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (venta_id, l["producto_id"], l["producto"],
                 l["cantidad"], l["precio"], l["subtotal"], tienda_id))
            self.cursor.execute(
                "UPDATE productos SET stock = stock - ? WHERE id = ?",
                (l["cantidad"], l["producto_id"]))
        self.conn.commit()
        return venta_id

    def list_ventas(self, tienda_id: int | None = None) -> list[dict]:
        if tienda_id is None:
            self.cursor.execute("SELECT id, total, fecha FROM ventas ORDER BY fecha DESC")
        else:
            self.cursor.execute(
                "SELECT id, total, fecha FROM ventas WHERE id_tienda = ? ORDER BY fecha DESC",
                (tienda_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def list_items_by_venta(self, venta_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT producto, cantidad, precio, subtotal FROM venta_items WHERE venta_id = ?",
            (venta_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def delete_venta(self, venta_id: int):
        self.cursor.execute("DELETE FROM venta_items WHERE venta_id = ?", (venta_id,))
        self.cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
        self.conn.commit()

    # ── Queries de estadísticas ────────────────────────────────────────────────
    def productos_con_ventas(self, tienda_id: int) -> list[str]:
        """Nombres de productos que tienen al menos una venta en la tienda."""
        self.cursor.execute("""
            SELECT DISTINCT vi.producto
            FROM venta_items vi
            WHERE vi.id_tienda = ?
            ORDER BY vi.producto
        """, (tienda_id,))
        vendidos = [r[0] for r in self.cursor.fetchall()]
        registrados = [p["nombre"] for p in self.list_productos(tienda_id)]
        # union: registrados primero, luego los que tienen ventas pero ya no están
        seen = set()
        result = []
        for n in registrados + vendidos:
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result

    def serie_tiempo_producto(self, tienda_id: int, nombre_producto: str,
                               agrupacion: str = "dia") -> tuple:
        """
        Retorna (periodos, unidades, ingresos) agrupado.
        agrupacion: 'dia' | 'semana' | 'mes'
        """
        fmt = {
            "dia":    "%Y-%m-%d",
            "semana": "%Y-%W",
            "mes":    "%Y-%m",
        }.get(agrupacion, "%Y-%m-%d")

        self.cursor.execute(f"""
            SELECT strftime('{fmt}', v.fecha) AS periodo,
                   SUM(vi.cantidad)           AS unidades,
                   SUM(vi.subtotal)           AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE vi.id_tienda = ? AND vi.producto = ?
            GROUP BY periodo
            ORDER BY periodo
        """, (tienda_id, nombre_producto))
        rows = self.cursor.fetchall()
        if not rows:
            return [], [], []
        return (
            [r[0] for r in rows],
            [float(r[1]) for r in rows],
            [float(r[2]) for r in rows],
        )

    def top_productos(self, tienda_id: int, periodo: str = "siempre",
                      metrica: str = "ingresos", limit: int = 20) -> list[dict]:
        """
        Top de productos por ingresos o unidades.
        periodo: 'semana' | 'mes' | 'año' | 'siempre'
        metrica: 'ingresos' | 'unidades'
        """
        params = [tienda_id]
        where_extra = ""
        now = datetime.now()

        if periodo == "semana":
            params.append((now - timedelta(days=7)).strftime("%Y-%m-%d"))
            where_extra = "AND v.fecha >= ?"
        elif periodo == "mes":
            params.append(now.strftime("%Y-%m"))
            where_extra = "AND strftime('%Y-%m', v.fecha) = ?"
        elif periodo == "año":
            params.append(str(now.year))
            where_extra = "AND strftime('%Y', v.fecha) = ?"

        order_col = "SUM(vi.subtotal)" if metrica == "ingresos" else "SUM(vi.cantidad)"
        self.cursor.execute(f"""
            SELECT vi.producto,
                   SUM(vi.cantidad) AS unidades,
                   SUM(vi.subtotal) AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE vi.id_tienda = ? {where_extra}
            GROUP BY vi.producto
            ORDER BY {order_col} DESC
            LIMIT {limit}
        """, params)
        return [dict(r) for r in self.cursor.fetchall()]

    def ingresos_por_dia(self, tienda_id: int, dias: int = 30) -> tuple:
        """Serie de ingresos totales de la tienda en los últimos N días."""
        desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        self.cursor.execute("""
            SELECT strftime('%Y-%m-%d', v.fecha) AS dia,
                   SUM(vi.subtotal)              AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE vi.id_tienda = ? AND v.fecha >= ?
            GROUP BY dia
            ORDER BY dia
        """, (tienda_id, desde))
        rows = self.cursor.fetchall()
        return [r[0] for r in rows], [float(r[1]) for r in rows]

    def resumen_tienda(self, tienda_id: int) -> dict:
        """KPIs rápidos para el header de estadísticas."""
        now = datetime.now()
        mes_actual = now.strftime("%Y-%m")

        self.cursor.execute("""
            SELECT COALESCE(SUM(vi.subtotal), 0) AS total_mes,
                   COALESCE(SUM(vi.cantidad), 0) AS uds_mes,
                   COUNT(DISTINCT vi.venta_id)   AS ventas_mes
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE vi.id_tienda = ?
              AND strftime('%Y-%m', v.fecha) = ?
        """, (tienda_id, mes_actual))
        r = dict(self.cursor.fetchone())

        self.cursor.execute(
            "SELECT COALESCE(SUM(subtotal),0) FROM venta_items WHERE id_tienda = ?",
            (tienda_id,))
        r["total_historico"] = float(self.cursor.fetchone()[0])

        self.cursor.execute(
            "SELECT COUNT(*) FROM productos WHERE id_tienda = ?", (tienda_id,))
        r["n_productos"] = self.cursor.fetchone()[0]

        return r

    # ── Cierre ─────────────────────────────────────────────────────────────────
    def close(self):
        self.conn.commit()
        self.conn.close()
