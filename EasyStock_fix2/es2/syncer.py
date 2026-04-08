import uuid
import json
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime
from easystock.config import DB_FILE
from easystock.database import DBManager

SUPABASE_URL = "https://tfotecboxtfkjhgxyrtg.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InRmb3RlY2JveHRma2poZ3h5cnRnIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzU0Mjg0NzYsImV4cCI6MjA5MTAwNDQ3Nn0.6cxFCChJFk-tvvAaFZA-iAJUBzGh7dyubk7eXfj6CIc"
SYNC_INTERVAL = 15

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
            raw = r.read()
            return json.loads(raw) if raw else {}
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
        self._running   = False
        self._thread    = None
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
        # Solo productos no sincronizados
        prods = self._db.list_productos_no_sync(tienda_id)
        if not prods:
            return
            
        rows  = [{
            "id":           p["id"],
            "sucursal_id":  sid,
            "nombre":       p["nombre"],
            "stock":        p["stock"],
            "precio":       p["precio"],
            "codigo_barras": p.get("codigo_barras"),
        } for p in prods]
        _upsert("productos", rows)
        
        # Marcar como sincronizados
        self._db.mark_productos_synced([p["id"] for p in prods])

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
        ofertas = self._db.list_ofertas_no_sync(tienda_id)
        if not ofertas:
            return
            
        rows = [{
            "id":          o["id"],
            "sucursal_id": sid,
            "nombre":      o["nombre"],
            "precio":      o["precio"],
            "expira_at":   o["expira_at"],
            "activa":      True,
        } for o in ofertas]
        _upsert("ofertas", rows)
        
        # Marcar como sincronizados
        self._db.mark_ofertas_synced([o["id"] for o in ofertas])

    def _sync_ventas(self, sid: str, tienda_id: int):
        ventas = self._db.list_ventas_no_sync(tienda_id)
        if not ventas:
            return
            
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
        
        # Marcar ventas como sincronizadas
        self._db.mark_ventas_synced([v["id"] for v in ventas])

    def _sync_cierres(self, sid: str, tienda_id: int):
        cierres = self._db.list_cierres_no_sync(tienda_id)
        if not cierres:
            return
            
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
        
        # Marcar como sincronizados
        self._db.mark_cierres_synced([c["id"] for c in cierres])

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

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._sync_loop, daemon=True)
        self._thread.start()
        print("[sync] started")

    def _sync_loop(self):
        """Loop infinito que sincroniza cada SYNC_INTERVAL segundos"""
        while self._running:
            self.sync_all()
            time.sleep(SYNC_INTERVAL)
            print("sincronizando")


    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[sync] stopped")

    