# La lista de pacientes al aplicar una plantilla hace scroll cuando hay muchos.
import sys
from playwright.sync_api import sync_playwright
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 700}); errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(BASE); page.wait_for_selector('#main')
    page.evaluate("""() => { for (let i = 0; i < 80; i++) db.patients.push({id:'x'+i, nombre:'Nombre'+i, apellidos:'Apellido'+i, fechaAlta:'2026-01-01', telefono:'', email:'', observaciones:''});
      db.plantillas.push({id:'t9', nombre:'Prueba', semanas:1, creada:'2026-10-01', aplicaciones:[], items:[{id:'i9', dia:1, exerciseId:db.exercises[0].id, bloqueId:'', orden:1, nota:'', grupo:'', notaGrupo:''}]}); }""")
    page.evaluate("openAplicarPlantilla('', 't9')"); page.wait_for_selector('#apIni')
    r = page.evaluate("""() => { const l = document.querySelector('#modal .lista-sel'); return [l.scrollHeight > l.clientHeight + 50, l.clientHeight, getComputedStyle(l).overflowY]; }""")
    check(r[0] and r[2] in ('auto', 'scroll') and r[1] <= 260, f'la lista de pacientes tiene scroll propio ({r})')
    page.locator('#modal .lista-sel').evaluate("e => e.scrollTop = e.scrollHeight")
    check(page.get_by_role('button', name='Crear plan', exact=True).is_visible(), 'el botón Crear plan sigue accesible')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
