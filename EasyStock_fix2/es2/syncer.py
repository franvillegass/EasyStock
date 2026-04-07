import uuid
import json
import threading
import urllib.request
import urllib.error
from datetime import datetime
from easystock.config import DB_FILE
from easystock.database import DBManager

SUPABASE_URL = "https://TU_PROJECT.supabase.co"
SUPABASE_KEY = "TU_ANON_KEY"
SYNC_INTERVAL = 15 * 60

_HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "resolution=merge-duplicates",
}


def _req(method: str, path: str, body=None):
    url  = f"{SUPABASE_URL}/rest/v1/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req  = urllib.request.Request(url, data=data, headers=_HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read()) if r.read() else {}
    except urllib.error.HTTPError as e:
        print(f"[sync] HTTP {e.code}: {e.read().decode()}")
    except Exception as e:
        print(f"[sync] error: {e}")
    return None


def _upsert(table: str, rows):
    if not rows:
        return
    _req("POST", f"{table}?on_conflict=id", rows if isinstance(rows, list) else [rows])


def generate_entity_id() -> str:
    return str(uuid.uuid4())[:8].upper()


class Syncer:
    def __init__(self, entidad_id: str):
        self.entidad_id = entidad_id
        self._db        = DBManager(DB_FILE)
        self._timer     = None
        self._ensure_entidad()

    def _ensure_entidad(self):
        _req("POST", "entidades?on_conflict=id", {
            "id": self.entidad_id, "nombre": self.entidad_id
        })

    def _sync_sucursal(self, tienda: dict) -> str:
        sid = f"{self.entidad_id}_{tienda['id']}"
        _upsert("sucursales", {
            "id": sid,
            "entidad_id": self.entidad_id,
            "nombre": tienda["nombre"],
            "ultima_sync": datetime.utcnow().isoformat(),
        })
        return sid

    def _sync_productos(self, sid: str, tienda_id: int):
        prods = self._db.list_productos(tienda_id)
        rows  = [{
            "id":           p["id"],
            "sucursal_id":  sid,
            "nombre":       p["nombre"],
            "stock":        p["stock"],
            "precio":       p["precio"],
            "codigo_barras": p.get("codigo_barras"),
        } for p in prods]
        _upsert("productos", rows)

        cats_rows = []
        pc_rows   = []
        for p in prods:
            for c in p.get("categorias", []):
                cats_rows.append({"id": c["id"], "sucursal_id": sid, "nombre": c["nombre"]})
                pc_rows.append({"producto_id": p["id"], "categoria_id": c["id"]})
        if cats_rows:
            _upsert("categorias", cats_rows)
        if pc_rows:
            _req("POST", "producto_categorias?on_conflict=producto_id,categoria_id", pc_rows)

    def _sync_ofertas(self, sid: str, tienda_id: int):
        ofertas = self._db.list_ofertas(tienda_id)
        rows = [{
            "id":          o["id"],
            "sucursal_id": sid,
            "nombre":      o["nombre"],
            "precio":      o["precio"],
            "expira_at":   o["expira_at"],
            "activa":      True,
        } for o in ofertas]
        _upsert("ofertas", rows)

    def _sync_ventas(self, sid: str, tienda_id: int):
        ventas = self._db.list_ventas(tienda_id)
        v_rows = [{
            "id":              v["id"],
            "sucursal_id":     sid,
            "total":           v["total"],
            "metodo_pago":     v.get("metodo_pago", "efectivo"),
            "descuento_total": v.get("descuento_total", 0),
            "fecha":           v["fecha"],
        } for v in ventas]
        _upsert("ventas", v_rows)

        for v in ventas:
            items = self._db.list_items_by_venta(v["id"])
            i_rows = [{
                "id":             f"{v['id']}_{i}",
                "venta_id":       v["id"],
                "producto":       it["producto"],
                "cantidad":       it["cantidad"],
                "precio":         it["precio"],
                "descuento_item": it.get("descuento_item", 0),
                "subtotal":       it["subtotal"],
                "es_oferta":      bool(it.get("es_oferta", False)),
            } for i, it in enumerate(items)]
            _upsert("venta_items", i_rows)

    def _sync_cierres(self, sid: str, tienda_id: int):
        cierres = self._db.list_cierres(tienda_id)
        rows = [{
            "id":                  c["id"],
            "sucursal_id":         sid,
            "fecha_apertura":      c["fecha_apertura"],
            "fecha_cierre":        c["fecha_cierre"],
            "total_efectivo":      c["total_efectivo"],
            "total_transferencia": c["total_transferencia"],
            "total_qr":            c["total_qr"],
            "total":               c["total"],
            "subtotal_productos":  c["subtotal_productos"],
        } for c in cierres]
        _upsert("cierres_caja", rows)

    def sync_all(self):
        try:
            tiendas = self._db.list_tiendas()
            for t in tiendas:
                sid = self._sync_sucursal(t)
                self._sync_productos(sid, t["id"])
                self._sync_ofertas(sid, t["id"])
                self._sync_ventas(sid, t["id"])
                self._sync_cierres(sid, t["id"])
            print(f"[sync] ok {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            print(f"[sync] failed: {e}")
        finally:
            self._schedule()

    def _schedule(self):
        self._timer = threading.Timer(SYNC_INTERVAL, self.sync_all)
        self._timer.daemon = True
        self._timer.start()

    def start(self):
        self._schedule()
        threading.Thread(target=self.sync_all, daemon=True).start()

    def stop(self):
        if self._timer:
            self._timer.cancel()