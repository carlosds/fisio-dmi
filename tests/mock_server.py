import json, os, re, sys, threading
from urllib.parse import urlparse, parse_qs
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
INDEX = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code', 'index.html'), encoding='utf-8').read().replace('__APP_VERSION__', 'test-1.5.0')
# La app usa ventanas propias para avisos y confirmaciones. Para que las pruebas antiguas sigan contestando con
# page.on('dialog'), el servidor de pruebas hace que esas ventanas pasen por alert/confirm/prompt del navegador.
# Con MOCK_DIALOGOS=propios se usan las ventanas de verdad (test_dialogos.py). En las de elegir, aceptar sin texto
# es la primera opción; para otra, se acepta con su valor (d.accept('copiar')).
if os.environ.get('MOCK_DIALOGOS') != 'propios':
    INDEX = INDEX.replace('<script>', "<script>window.__dialogoAuto = (t, m, v) => t === 'alert' ? void alert(m) : t === 'confirm' ? confirm(m) : t === 'choice' ? ((r) => r === '' ? v : r)(prompt(m, v)) : prompt(m, v);</script>\n<script>", 1)
FOTOS = {}
STATE = {"exercises": [], "patients": [], "pautas": [], "puntuaciones": {}, "ajustes": {}, "bloques": [], "planCasa": [], "hitos": [], "evaluaciones": [], "plantillas": [], "planesGuardados": []}
STATS = {"puts": 0, "gets": 0, "rev": 100}
# Google Calendar simulado: /__google (POST JSON) cambia el estado; «cambios» y «ocupados» los devuelve la próxima
# sincronización; «falla» hace que falle con ese mensaje.
GOOGLE = {"configurado": False, "clientId": "", "conectado": False, "cuenta": "", "activo": False, "calendario": False,
          "ultima": None, "error": "", "ocupados": [], "cambios": [], "falla": "", "syncs": 0, "pedidos": [], "calendarios": []}
EXPDIR = os.environ.get('EXPDIR', '/tmp/fisio_exports')
EXPORTS = []
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, body, ctype='application/json'):
        b = body if isinstance(body, bytes) else body.encode('utf-8')
        self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if self.path.startswith('/fotos/'):
            b = FOTOS.get(self.path[7:])
            if b is None: return self._send(404, 'no')
            self.send_response(200); self.send_header('Content-Type','image/jpeg'); self.send_header('Content-Length', str(len(b))); self.end_headers(); self.wfile.write(b); return
        if self.path == '/' or self.path.startswith('/?'): return self._send(200, INDEX, 'text/html; charset=utf-8')
        if self.path == '/api/state':
            STATS['gets'] += 1
            b = json.dumps(STATE).encode()
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length', str(len(b))); self.send_header('X-Revision', str(STATS['rev'])); self.end_headers(); self.wfile.write(b); return
        if self.path == '/__bump': STATS['rev'] += 1; return self._send(200, '{}')
        if self.path == '/api/ajustes': return self._send(200, json.dumps({"dataDir": "/tmp/datos", "defaultDir": "/tmp/datos"}))
        if self.path == '/api/ayuda': return self._send(200, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'AYUDA.md'), encoding='utf-8').read(), 'text/markdown; charset=utf-8')
        if self.path == '/api/changelog':
            # Versión anunciada: MOCK_VERSION o, si no, la primera del CHANGELOG (la que se va a entregar).
            texto = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'CHANGELOG.md'), encoding='utf-8').read()
            m = re.search(r'^## (\S+)', texto, re.M)
            return self._send(200, json.dumps({"version": os.environ.get('MOCK_VERSION', m.group(1) if m else 'dev'), "texto": texto}))
        if self.path == '/api/copias': return self._send(200, '[]')
        if self.path == '/api/copias-auto': return self._send(200, json.dumps({"error": "", "ultima": None}))
        if self.path == '/api/copiando': return self._send(200, json.dumps({"copiando": bool(STATS.get('copiando'))}))
        if self.path.startswith('/__copiando/'): STATS['copiando'] = self.path.endswith('/1'); return self._send(200, '{}')
        if self.path == '/pdf-lib.min.js': return self._send(200, open(os.path.join(RAIZ, 'code', 'pdf-lib.min.js'), 'rb').read(), 'text/javascript')
        if self.path == '/__exports': return self._send(200, json.dumps(EXPORTS))
        if self.path.startswith('/__dialogo/'): STATS['dialogo'] = self.path.rsplit('/', 1)[1]; return self._send(200, '{}')
        if self.path == '/api/informes/existen': return self._send(200, json.dumps({x['id']: os.path.exists(x['ruta']) for x in STATE.get('informes', [])}))
        if self.path == '/api/google/estado':
            return self._send(200, json.dumps({k: GOOGLE[k] for k in ("configurado", "clientId", "conectado", "cuenta", "activo", "calendario", "ultima", "error", "ocupados")}))
        if self.path == '/api/google/calendarios':
            return self._send(200, json.dumps([{"id": c, "nombre": c, "principal": i == 0, "marcado": i == 0} for i, c in enumerate(GOOGLE["calendarios"])]))
        if self.path == '/__google': return self._send(200, json.dumps(GOOGLE))
        if self.path == '/__stats': return self._send(200, json.dumps(STATS))
        if self.path == '/__state': return self._send(200, json.dumps(STATE))
        self._send(404, 'no')
    def do_PUT(self):
        if self.path == '/api/state':
            n = int(self.headers['Content-Length']); body = json.loads(self.rfile.read(n))
            h = self.headers.get('X-Revision')
            if h and h != str(STATS['rev']): return self._send(409, 'conflicto')
            STATS['rev'] += 1
            STATE.clear(); STATE.update(body); STATS['puts'] += 1
            b = b'{"ok":true}'
            self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length', str(len(b))); self.send_header('X-Revision', str(STATS['rev'])); self.end_headers(); self.wfile.write(b); return
        self._send(404, 'no')
    def do_POST(self):
        n = int(self.headers.get('Content-Length') or 0); data = self.rfile.read(n)
        if self.path == '/api/foto':
            import hashlib
            nombre = hashlib.sha256(data).hexdigest()[:16] + '.jpg'; FOTOS[nombre] = data
            return self._send(200, json.dumps({"url": "/fotos/" + nombre}))
        if self.path.startswith('/api/exportar'):
            # Simula el diálogo «Guardar como»: /__dialogo/cancelar hace que se cancele.
            q = parse_qs(urlparse(self.path).query); json_ = q.get('tipo', [''])[0] == 'json'; nombre = q.get('nombre', ['x'])[0] + ('.json' if json_ else '.pdf'); carpeta = q.get('carpeta', [''])[0]
            STATS.setdefault('inicios', []).append(q.get('inicio', [''])[0])
            if carpeta:
                if not os.path.isdir(carpeta): return self._send(400, 'la carpeta no existe')
                ruta = os.path.join(carpeta, nombre); base, ext = os.path.splitext(ruta); k = 2
                while os.path.exists(ruta): ruta = f'{base} ({k}){ext}'; k += 1
            else:
                if STATS.get('dialogo') == 'cancelar': return self._send(409, 'cancelado')
                d = os.path.join(EXPDIR, 'maestros' if json_ else 'informes' if '_Informe_de_pautas_' in nombre else 'planes')
                os.makedirs(d, exist_ok=True); ruta = os.path.join(d, nombre)
            open(ruta, 'wb').write(data); EXPORTS.append(ruta)
            return self._send(200, json.dumps({"path": ruta, "nombre": os.path.basename(ruta), "carpeta": os.path.dirname(ruta)}))
        if self.path == '/__google': GOOGLE.update(json.loads(data or b'{}')); return self._send(200, '{}')
        if self.path == '/api/google/credenciales':
            b = json.loads(data); 
            if not b.get('clientId', '').endswith('.apps.googleusercontent.com'): return self._send(400, 'el ID de cliente no parece correcto')
            GOOGLE.update(configurado=True, clientId=b['clientId']); return self._send(200, '{"ok":true}')
        if self.path == '/api/google/activar': GOOGLE['activo'] = json.loads(data)['activo']; return self._send(200, '{"ok":true}')
        if self.path == '/api/google/desconectar': GOOGLE.update(conectado=False, activo=False, cuenta=''); return self._send(200, '{"ok":true}')
        if self.path == '/api/google/calendarios': GOOGLE['pedidos'].append(json.loads(data)); return self._send(200, '{"ok":true}')
        if self.path == '/api/google/sincronizar':
            GOOGLE['syncs'] += 1
            if GOOGLE['falla']: GOOGLE['error'] = GOOGLE['falla']; return self._send(502, GOOGLE['falla'])
            import datetime
            res = {"cambios": GOOGLE['cambios'], "ocupados": GOOGLE['ocupados'], "subidas": 0, "borradas": 0, "pendientes": 0, "hora": datetime.datetime.now().isoformat()}
            GOOGLE['cambios'] = []; GOOGLE['ultima'] = res['hora']; GOOGLE['error'] = ''
            return self._send(200, json.dumps(res))
        if self.path == '/api/salir': STATS['salir'] = STATS.get('salir', 0) + 1; return self._send(200, json.dumps({'ok': True}))
        if self.path.startswith('/api/elegir-carpeta'):
            if STATS.get('dialogo') == 'cancelar': return self._send(409, 'cancelado')
            d = os.path.join(EXPDIR, 'lote'); os.makedirs(d, exist_ok=True)
            return self._send(200, json.dumps({"path": d}))
        if self.path.startswith('/api/informes/abrir'):
            q = parse_qs(urlparse(self.path).query); i = q.get('id', [''])[0]; modo = q.get('modo', [''])[0]
            x = next((x for x in STATE.get('informes', []) if x['id'] == i), None)
            if not x: return self._send(404, 'informe no encontrado')
            if not os.path.exists(x['ruta']): return self._send(410, 'no se encuentra el archivo ' + x['ruta'])
            STATS.setdefault('abiertos', []).append([i, modo]); return self._send(200, json.dumps({"ruta": x['ruta']}))
        self._send(200, '{"ok":true}')
if __name__ == '__main__':
    if len(sys.argv) > 2:   # estado inicial desde un archivo
        STATE.update(json.load(open(sys.argv[2], encoding='utf-8')))
    ThreadingHTTPServer(('127.0.0.1', int(sys.argv[1])), H).serve_forever()
