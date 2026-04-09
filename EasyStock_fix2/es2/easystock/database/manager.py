"""
EasyStock — capa de acceso a datos.
Toda interacción con SQLite pasa por DBManager.
"""
import sqlite3
from datetime import datetime, timedelta
from easystock.config import DB_FILE

CATEGORIAS_DEFAULT = [
    "Alimentos", "Bebidas", "Limpieza", "Higiene",
    "Electrónica", "Indumentaria", "Varios", "Ofertas",
]


class DBManager:
    def __init__(self, filename: str = DB_FILE):
        self.conn = sqlite3.connect(filename, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.cursor = self.conn.cursor()
        self._ensure_schema()

    # ── Schema ─────────────────────────────────────────────────────────────────
    def _ensure_schema(self):
        self.cursor.executescript("""
        CREATE TABLE IF NOT EXISTS tiendas (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS categorias (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre    TEXT NOT NULL UNIQUE,
            es_sistema INTEGER NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS productos (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre        TEXT    NOT NULL,
            stock         INTEGER NOT NULL DEFAULT 0,
            precio        REAL    NOT NULL DEFAULT 0,
            id_tienda     INTEGER NOT NULL,
            codigo_barras TEXT    UNIQUE
        );

        CREATE TABLE IF NOT EXISTS producto_categorias (
            producto_id  INTEGER NOT NULL,
            categoria_id INTEGER NOT NULL,
            PRIMARY KEY (producto_id, categoria_id),
            FOREIGN KEY (producto_id)  REFERENCES productos(id)  ON DELETE CASCADE,
            FOREIGN KEY (categoria_id) REFERENCES categorias(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS ofertas (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre    TEXT NOT NULL,
            precio    REAL NOT NULL,
            tienda_id INTEGER NOT NULL,
            expira_at TEXT
        );

        CREATE TABLE IF NOT EXISTS oferta_productos (
            oferta_id   INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            PRIMARY KEY (oferta_id, producto_id),
            FOREIGN KEY (oferta_id)   REFERENCES ofertas(id)   ON DELETE CASCADE,
            FOREIGN KEY (producto_id) REFERENCES productos(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS cierres_caja (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            tienda_id          INTEGER NOT NULL,
            fecha_apertura     TEXT NOT NULL,
            fecha_cierre       TEXT NOT NULL,
            total_efectivo     REAL NOT NULL DEFAULT 0,
            total_transferencia REAL NOT NULL DEFAULT 0,
            total_qr           REAL NOT NULL DEFAULT 0,
            total              REAL NOT NULL DEFAULT 0,
            subtotal_productos REAL NOT NULL DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ventas (
            id            INTEGER   PRIMARY KEY AUTOINCREMENT,
            total         REAL      NOT NULL,
            fecha         TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            id_tienda     INTEGER,
            metodo_pago   TEXT      NOT NULL DEFAULT 'efectivo',
            descuento_total REAL    NOT NULL DEFAULT 0,
            cierre_id     INTEGER,
            FOREIGN KEY (cierre_id) REFERENCES cierres_caja(id)
        );

        CREATE TABLE IF NOT EXISTS venta_items (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id        INTEGER NOT NULL,
            producto_id     INTEGER,
            producto        TEXT    NOT NULL,
            cantidad        INTEGER NOT NULL,
            precio          REAL    NOT NULL,
            descuento_item  REAL    NOT NULL DEFAULT 0,
            subtotal        REAL    NOT NULL,
            id_tienda       INTEGER,
            es_oferta       INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (venta_id) REFERENCES ventas(id) ON DELETE CASCADE
        );
        """)
        self._migrate()
        self._seed_categorias()
        self.conn.commit()

    def _migrate(self):
        migrations = [
            ("ventas",      "id_tienda",        "INTEGER"),
            ("ventas",      "metodo_pago",       "TEXT NOT NULL DEFAULT 'efectivo'"),
            ("ventas",      "descuento_total",   "REAL NOT NULL DEFAULT 0"),
            ("ventas",      "cierre_id",         "INTEGER"),
            ("ventas",      "synced_at",         "TIMESTAMP"),
            ("venta_items", "id_tienda",         "INTEGER"),
            ("venta_items", "producto_id",       "INTEGER"),
            ("venta_items", "descuento_item",    "REAL NOT NULL DEFAULT 0"),
            ("venta_items", "es_oferta",         "INTEGER NOT NULL DEFAULT 0"),
            ("venta_items", "synced_at",         "TIMESTAMP"),
            ("productos",   "synced_at",         "TIMESTAMP"),
            ("ofertas",     "synced_at",         "TIMESTAMP"),
            ("cierres_caja","synced_at",         "TIMESTAMP"),
        ]
        for table, col, typ in migrations:
            try:
                self.cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            except sqlite3.OperationalError:
                pass

    def _seed_categorias(self):
        """Inserta categorías por defecto si no existen."""
        for nombre in CATEGORIAS_DEFAULT:
            try:
                self.cursor.execute(
                    "INSERT INTO categorias (nombre, es_sistema) VALUES (?, 1)",
                    (nombre,))
            except sqlite3.IntegrityError:
                pass

    # ── Tiendas ────────────────────────────────────────────────────────────────
    def list_tiendas(self) -> list[dict]:
        self.cursor.execute("SELECT id, nombre FROM tiendas ORDER BY id")
        return [dict(r) for r in self.cursor.fetchall()]

    def add_tienda(self, nombre: str) -> int:
        self.cursor.execute("INSERT INTO tiendas (nombre) VALUES (?)", (nombre,))
        self.conn.commit()
        return self.cursor.lastrowid

    def delete_tienda(self, tienda_id: int):
        for p in self.list_productos(tienda_id):
            self.delete_producto(p["id"])
        self.cursor.execute("DELETE FROM tiendas WHERE id = ?", (tienda_id,))
        self.conn.commit()

    def rename_tienda(self, tienda_id: int, nuevo_nombre: str):
        self.cursor.execute(
            "UPDATE tiendas SET nombre = ? WHERE id = ?", (nuevo_nombre, tienda_id))
        self.conn.commit()

    # ── Categorías ─────────────────────────────────────────────────────────────
    def list_categorias(self) -> list[dict]:
        self.cursor.execute("SELECT id, nombre, es_sistema FROM categorias ORDER BY nombre")
        return [dict(r) for r in self.cursor.fetchall()]

    def add_categoria(self, nombre: str) -> int:
        self.cursor.execute(
            "INSERT INTO categorias (nombre, es_sistema) VALUES (?, 0)", (nombre,))
        self.conn.commit()
        return self.cursor.lastrowid

    def delete_categoria(self, categoria_id: int):
        self.cursor.execute("DELETE FROM categorias WHERE id = ? AND es_sistema = 0",
                            (categoria_id,))
        self.conn.commit()

    def get_categorias_producto(self, producto_id: int) -> list[dict]:
        self.cursor.execute("""
            SELECT c.id, c.nombre FROM categorias c
            JOIN producto_categorias pc ON c.id = pc.categoria_id
            WHERE pc.producto_id = ?
        """, (producto_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def set_categorias_producto(self, producto_id: int, categoria_ids: list[int]):
        self.cursor.execute(
            "DELETE FROM producto_categorias WHERE producto_id = ?", (producto_id,))
        for cid in categoria_ids:
            try:
                self.cursor.execute(
                    "INSERT INTO producto_categorias (producto_id, categoria_id) VALUES (?,?)",
                    (producto_id, cid))
            except sqlite3.IntegrityError:
                pass
        self.conn.commit()

    # ── Productos ──────────────────────────────────────────────────────────────
    def list_productos(self, id_tienda: int | None = None,
                       categoria_id: int | None = None) -> list[dict]:
        if id_tienda is None:
            self.cursor.execute(
                "SELECT id, nombre, stock, precio, id_tienda, codigo_barras FROM productos")
        elif categoria_id is not None:
            self.cursor.execute("""
                SELECT p.id, p.nombre, p.stock, p.precio, p.id_tienda, p.codigo_barras
                FROM productos p
                JOIN producto_categorias pc ON p.id = pc.producto_id
                WHERE p.id_tienda = ? AND pc.categoria_id = ?
                ORDER BY p.nombre
            """, (id_tienda, categoria_id))
        else:
            self.cursor.execute(
                "SELECT id, nombre, stock, precio, id_tienda, codigo_barras "
                "FROM productos WHERE id_tienda = ? ORDER BY nombre",
                (id_tienda,))
        rows = [dict(r) for r in self.cursor.fetchall()]
        for r in rows:
            r["categorias"] = self.get_categorias_producto(r["id"])
        return rows

    def add_producto(self, nombre: str, stock: int, precio: float,
                     id_tienda: int, codigo_barras: str | None = None,
                     categoria_ids: list[int] | None = None) -> int:
        self.cursor.execute(
            "INSERT INTO productos (nombre, stock, precio, id_tienda, codigo_barras) "
            "VALUES (?, ?, ?, ?, ?)",
            (nombre, int(stock), float(precio), id_tienda, codigo_barras or None))
        prod_id = self.cursor.lastrowid
        self.conn.commit()
        if categoria_ids:
            self.set_categorias_producto(prod_id, categoria_ids)
        return prod_id

    def update_producto(self, prod_id: int, nombre: str, stock: int,
                        precio: float, codigo_barras: str | None,
                        categoria_ids: list[int] | None = None):
        # FIX: resetear synced_at para que el sync incremental reenvíe el producto
        self.cursor.execute(
            "UPDATE productos SET nombre=?, stock=?, precio=?, codigo_barras=?, synced_at=NULL WHERE id=?",
            (nombre, int(stock), float(precio), codigo_barras or None, prod_id))
        self.conn.commit()
        if categoria_ids is not None:
            self.set_categorias_producto(prod_id, categoria_ids)

    def delete_producto(self, prod_id: int):
        self.cursor.execute("DELETE FROM productos WHERE id = ?", (prod_id,))
        self.conn.commit()

    def get_producto_by_barcode(self, codigo: str, id_tienda: int) -> dict | None:
        self.cursor.execute(
            "SELECT * FROM productos WHERE codigo_barras = ? AND id_tienda = ?",
            (codigo, id_tienda))
        r = self.cursor.fetchone()
        return dict(r) if r else None

    # ── Ofertas ────────────────────────────────────────────────────────────────
    def _purge_ofertas_expiradas(self):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cursor.execute(
            "DELETE FROM ofertas WHERE expira_at IS NOT NULL AND expira_at <= ?", (now,))
        self.conn.commit()

    def list_ofertas(self, tienda_id: int) -> list[dict]:
        self._purge_ofertas_expiradas()
        self.cursor.execute(
            "SELECT id, nombre, precio, expira_at FROM ofertas WHERE tienda_id = ? ORDER BY nombre",
            (tienda_id,))
        ofertas = [dict(r) for r in self.cursor.fetchall()]
        for o in ofertas:
            self.cursor.execute("""
                SELECT p.id, p.nombre FROM productos p
                JOIN oferta_productos op ON p.id = op.producto_id
                WHERE op.oferta_id = ?
            """, (o["id"],))
            o["productos"] = [dict(r) for r in self.cursor.fetchall()]
        return ofertas

    def add_oferta(self, nombre: str, precio: float, tienda_id: int,
                   producto_ids: list[int], expira_at: str | None = None) -> int:
        self.cursor.execute(
            "INSERT INTO ofertas (nombre, precio, tienda_id, expira_at) VALUES (?,?,?,?)",
            (nombre, float(precio), tienda_id, expira_at))
        oferta_id = self.cursor.lastrowid
        for pid in producto_ids:
            self.cursor.execute(
                "INSERT INTO oferta_productos (oferta_id, producto_id) VALUES (?,?)",
                (oferta_id, pid))
        self.conn.commit()
        return oferta_id

    def delete_oferta(self, oferta_id: int):
        self.cursor.execute("DELETE FROM ofertas WHERE id = ?", (oferta_id,))
        self.conn.commit()

    # ── Ventas ─────────────────────────────────────────────────────────────────
    def create_venta(self, lineas: list[dict], total: float,
                     tienda_id: int | None = None,
                     metodo_pago: str = "efectivo",
                     descuento_total: float = 0.0) -> int:
        self.cursor.execute(
            "INSERT INTO ventas (total, id_tienda, metodo_pago, descuento_total) "
            "VALUES (?, ?, ?, ?)",
            (total, tienda_id, metodo_pago, descuento_total))
        venta_id = self.cursor.lastrowid
        for l in lineas:
            self.cursor.execute(
                "INSERT INTO venta_items "
                "(venta_id, producto_id, producto, cantidad, precio, "
                "descuento_item, subtotal, id_tienda, es_oferta) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (venta_id, l.get("producto_id"), l["producto"],
                 l["cantidad"], l["precio"], l.get("descuento_item", 0.0),
                 l["subtotal"], tienda_id, int(l.get("es_oferta", False))))
            # FIX: resetear synced_at del producto al descontar stock
            if not l.get("es_oferta") and l.get("producto_id"):
                self.cursor.execute(
                    "UPDATE productos SET stock = stock - ?, synced_at = NULL WHERE id = ?",
                    (l["cantidad"], l["producto_id"]))
        self.conn.commit()
        return venta_id

    def list_ventas(self, tienda_id: int | None = None,
                    sin_cierre: bool = False) -> list[dict]:
        extra = ""
        params = []
        if tienda_id is not None:
            params.append(tienda_id)
            extra += " WHERE id_tienda = ?"
            if sin_cierre:
                extra += " AND cierre_id IS NULL"
        elif sin_cierre:
            extra += " WHERE cierre_id IS NULL"

        self.cursor.execute(
            f"SELECT id, total, fecha, metodo_pago, descuento_total, cierre_id "
            f"FROM ventas{extra} ORDER BY fecha DESC",
            params)
        return [dict(r) for r in self.cursor.fetchall()]

    def list_items_by_venta(self, venta_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT producto, cantidad, precio, descuento_item, subtotal, es_oferta "
            "FROM venta_items WHERE venta_id = ?",
            (venta_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def delete_venta(self, venta_id: int):
        items = self.list_items_by_venta(venta_id)
        for it in items:
            if not it["es_oferta"]:
                # FIX: resetear synced_at del producto al restaurar stock
                self.cursor.execute("""
                    UPDATE productos SET stock = stock + ?, synced_at = NULL
                    WHERE id = (
                        SELECT producto_id FROM venta_items
                        WHERE venta_id = ? AND producto = ?
                        LIMIT 1
                    )
                """, (it["cantidad"], venta_id, it["producto"]))
        self.cursor.execute("DELETE FROM venta_items WHERE venta_id = ?", (venta_id,))
        self.cursor.execute("DELETE FROM ventas WHERE id = ?", (venta_id,))
        self.conn.commit()

    # ── Cierres de caja ────────────────────────────────────────────────────────
    def get_fecha_ultimo_cierre(self, tienda_id: int) -> str | None:
        self.cursor.execute(
            "SELECT fecha_cierre FROM cierres_caja WHERE tienda_id = ? "
            "ORDER BY fecha_cierre DESC LIMIT 1",
            (tienda_id,))
        r = self.cursor.fetchone()
        return r[0] if r else None

    def cerrar_caja(self, tienda_id: int) -> dict:
        ultimo       = self.get_fecha_ultimo_cierre(tienda_id)
        fecha_cierre = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if ultimo:
            fecha_apertura = ultimo
        else:
            self.cursor.execute("""
                SELECT MIN(fecha) FROM ventas
                WHERE id_tienda = ? AND cierre_id IS NULL
            """, (tienda_id,))
            r = self.cursor.fetchone()[0]
            fecha_apertura = r if r else fecha_cierre

        self.cursor.execute("""
            SELECT metodo_pago, SUM(total) as subtotal
            FROM ventas
            WHERE id_tienda = ? AND fecha > ? AND cierre_id IS NULL
            GROUP BY metodo_pago
        """, (tienda_id, fecha_apertura))
        rows = self.cursor.fetchall()

        totales = {"efectivo": 0.0, "transferencia": 0.0, "qr": 0.0}
        for r in rows:
            if r["metodo_pago"] in totales:
                totales[r["metodo_pago"]] = float(r["subtotal"])

        self.cursor.execute("""
            SELECT COALESCE(SUM(vi.subtotal), 0)
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE v.id_tienda = ? AND v.fecha > ? AND v.cierre_id IS NULL
        """, (tienda_id, fecha_apertura))
        subtotal_productos = float(self.cursor.fetchone()[0])

        total = sum(totales.values())

        self.cursor.execute("""
            INSERT INTO cierres_caja
            (tienda_id, fecha_apertura, fecha_cierre,
             total_efectivo, total_transferencia, total_qr,
             total, subtotal_productos)
            VALUES (?,?,?,?,?,?,?,?)
        """, (tienda_id, fecha_apertura, fecha_cierre,
              totales["efectivo"], totales["transferencia"], totales["qr"],
              total, subtotal_productos))
        cierre_id = self.cursor.lastrowid

        self.cursor.execute("""
            UPDATE ventas SET cierre_id = ?
            WHERE id_tienda = ? AND fecha > ? AND cierre_id IS NULL
        """, (cierre_id, tienda_id, fecha_apertura))
        self.conn.commit()

        return {
            "id":                  cierre_id,
            "fecha_apertura":      fecha_apertura,
            "fecha_cierre":        fecha_cierre,
            "total_efectivo":      totales["efectivo"],
            "total_transferencia": totales["transferencia"],
            "total_qr":            totales["qr"],
            "subtotal_productos":  subtotal_productos,
            "total":               total,
        }

    def list_cierres(self, tienda_id: int) -> list[dict]:
        self.cursor.execute("""
            SELECT id, fecha_apertura, fecha_cierre,
                   total_efectivo, total_transferencia, total_qr,
                   total, subtotal_productos
            FROM cierres_caja WHERE tienda_id = ?
            ORDER BY fecha_cierre DESC
        """, (tienda_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def list_ventas_by_cierre(self, cierre_id: int) -> list[dict]:
        self.cursor.execute(
            "SELECT id, total, fecha, metodo_pago, descuento_total "
            "FROM ventas WHERE cierre_id = ? ORDER BY fecha DESC",
            (cierre_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    # ── Queries de estadísticas ────────────────────────────────────────────────
    def productos_con_ventas(self, tienda_id: int) -> list[str]:
        self.cursor.execute("""
            SELECT DISTINCT vi.producto FROM venta_items vi
            WHERE vi.id_tienda = ? ORDER BY vi.producto
        """, (tienda_id,))
        vendidos = [r[0] for r in self.cursor.fetchall()]
        registrados = [p["nombre"] for p in self.list_productos(tienda_id)]
        seen, result = set(), []
        for n in registrados + vendidos:
            if n not in seen:
                seen.add(n)
                result.append(n)
        return result

    def serie_tiempo_producto(self, tienda_id: int, nombre_producto: str,
                               agrupacion: str = "dia") -> tuple:
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
            GROUP BY periodo ORDER BY periodo
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
        desde = (datetime.now() - timedelta(days=dias)).strftime("%Y-%m-%d")
        self.cursor.execute("""
            SELECT strftime('%Y-%m-%d', v.fecha) AS dia,
                   SUM(vi.subtotal)              AS ingresos
            FROM venta_items vi
            JOIN ventas v ON vi.venta_id = v.id
            WHERE vi.id_tienda = ? AND v.fecha >= ?
            GROUP BY dia ORDER BY dia
        """, (tienda_id, desde))
        rows = self.cursor.fetchall()
        return [r[0] for r in rows], [float(r[1]) for r in rows]

    def resumen_tienda(self, tienda_id: int) -> dict:
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
            "SELECT COUNT(*) FROM productos WHERE id_tienda = ?", (tienda_id,   ))
        r["n_productos"] = self.cursor.fetchone()[0]

        return r

    # ── Sync incremental ──────────────────────────────────────────────────────
    def list_productos_no_sync(self, tienda_id: int) -> list[dict]:
        self.cursor.execute("""
            SELECT id, nombre, stock, precio, codigo_barras
            FROM productos 
            WHERE id_tienda = ? AND synced_at IS NULL
            ORDER BY id
        """, (tienda_id,))
        productos = [dict(r) for r in self.cursor.fetchall()]
        for p in productos:
            self.cursor.execute("""
                SELECT c.id, c.nombre FROM categorias c
                JOIN producto_categorias pc ON c.id = pc.categoria_id
                WHERE pc.producto_id = ?
            """, (p["id"],))
            p["categorias"] = [dict(r) for r in self.cursor.fetchall()]
        return productos

    def mark_productos_synced(self, ids: list[int]):
        now = datetime.now().isoformat()
        self.cursor.executemany(
            "UPDATE productos SET synced_at = ? WHERE id = ?",
            [(now, id_) for id_ in ids]
        )
        self.conn.commit()

    def list_ofertas_no_sync(self, tienda_id: int) -> list[dict]:
        self._purge_ofertas_expiradas()
        self.cursor.execute("""
            SELECT id, nombre, precio, expira_at
            FROM ofertas 
            WHERE tienda_id = ? AND synced_at IS NULL
            ORDER BY id
        """, (tienda_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def mark_ofertas_synced(self, ids: list[int]):
        now = datetime.now().isoformat()
        self.cursor.executemany(
            "UPDATE ofertas SET synced_at = ? WHERE id = ?",
            [(now, id_) for id_ in ids]
        )
        self.conn.commit()

    def list_ventas_no_sync(self, tienda_id: int) -> list[dict]:
        self.cursor.execute("""
            SELECT id, total, fecha, metodo_pago, descuento_total
            FROM ventas 
            WHERE id_tienda = ? AND synced_at IS NULL
            ORDER BY fecha
        """, (tienda_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def mark_ventas_synced(self, ids: list[int]):
        now = datetime.now().isoformat()
        self.cursor.executemany(
            "UPDATE ventas SET synced_at = ? WHERE id = ?",
            [(now, id_) for id_ in ids]
        )
        self.conn.commit()

    def list_cierres_no_sync(self, tienda_id: int) -> list[dict]:
        self.cursor.execute("""
            SELECT id, fecha_apertura, fecha_cierre,
                   total_efectivo, total_transferencia, total_qr,
                   total, subtotal_productos
            FROM cierres_caja 
            WHERE tienda_id = ? AND synced_at IS NULL
            ORDER BY fecha_cierre
        """, (tienda_id,))
        return [dict(r) for r in self.cursor.fetchall()]

    def mark_cierres_synced(self, ids: list[int]):
        now = datetime.now().isoformat()
        self.cursor.executemany(
            "UPDATE cierres_caja SET synced_at = ? WHERE id = ?",
            [(now, id_) for id_ in ids]
        )
        self.conn.commit()

    # ── Cierre de conexión ─────────────────────────────────────────────────────
    def close(self):
        self.conn.commit()
        self.conn.close()