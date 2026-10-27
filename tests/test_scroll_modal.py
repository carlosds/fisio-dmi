# La ventana de puntuaciones debe poder desplazarse hasta el final cuando hay muchos bloques y ejercicios.
import sys
from playwright.sync_api import sync_playwright
PORT = int(sys.argv[1]); ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    for w, h in [(1300, 700), (900, 500)]:
        page = br.new_page(viewport={'width': w, 'height': h}); page.on('dialog', lambda d: d.accept())
        page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_selector('#main')
        page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
        page.evaluate("""() => { for (let b = 0; b < 12; b++){ const e = []; for (let i = 0; i < 5; i++){ const id = 'x' + b + '_' + i; db.exercises.push({id, nombre: 'Bloque ' + b + ' – ej ' + i, descripcion: '', fotos: []}); e.push(id); }
          db.bloques.push({id: 'bb' + b, nombre: 'Bloque ' + b, nivel: 'A', ejercicios: e});
          e.forEach((id, i) => db.pautas.push({id: 'pp' + b + '_' + i, patientId: ui.patientId, exerciseId: id, desde: '2026-06-01', hasta: '', asignacion: 'bloque', bloqueId: 'bb' + b, orden: b})); }
          ui.selDay = '2026-06-03'; render(); renderDayModal(); }""")
        page.wait_for_timeout(300)
        q = "(() => { const c = document.querySelector('#modal .mwrap > .card'); const r = c.getBoundingClientRect(); return {top: c.scrollTop, max: c.scrollHeight - c.clientHeight, bottom: r.bottom, vh: innerHeight}; })()"
        a = page.evaluate(q)
        check(a['max'] > 0 and a['bottom'] <= a['vh'], f'{w}x{h}: la ventana cabe en la pantalla y su contenido desborda ({a["max"]} px por ver)')
        for _ in range(400): page.mouse.move(w // 2, h // 2); page.mouse.wheel(0, 80)
        page.wait_for_timeout(300)
        b = page.evaluate(q)
        check(b['top'] >= b['max'] - 1, f'{w}x{h}: se llega al final con la rueda')
        check(page.get_by_role('button', name='Cerrar').last.is_visible(), f'{w}x{h}: el botón Cerrar queda accesible')
        page.close()
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
