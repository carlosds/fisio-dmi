# Editar un día del plan en casa, nombres sin repetir y carpetas de exportación.
import json, sys, os, urllib.request
from playwright.sync_api import sync_playwright
from ayuda_planes import PLAN_PRUEBA
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def st(): return json.load(urllib.request.urlopen(BASE + '__state'))
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 900}); errors = []
    page.on('pageerror', lambda e: errors.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE); page.wait_for_selector('#main')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    page.get_by_role('tab', name='Plan en casa').click(); page.wait_for_timeout(200)
    # bloque «Core básico» con ejercicios que repiten su nombre + uno que coincide del todo
    page.evaluate(PLAN_PRUEBA)
    page.evaluate("""() => { const l = iso(inicioSemana(new Date())); const g = uid();
      db.exercises.push({id:'e9',nombre:'Core básico',descripcion:'',fotos:[]}, {id:'e8',nombre:'Core básico – Por los tobillos',descripcion:'',fotos:[]});
      db.bloques.find(b => b.id==='b1').ejercicios.push('e9','e8');
      planPrueba(ui.patientId, l, 1, [{dia:1,e:'e9',b:'b1',g,ng:'prueba',orden:1},{dia:1,e:'e8',b:'b1',g,ng:'prueba',orden:2},{dia:1,e:'e3',orden:3}]); }""")
    dia = page.locator('.pc-semana .pc-dia').first
    t = dia.inner_text()
    check(t.count('Core básico') == 1, 'el nombre del bloque aparece una sola vez en la tarjeta')
    check('Por los tobillos' in t and 'Core básico – Por' not in t, 'el ejercicio se muestra sin el prefijo del bloque')
    dia.get_by_role('button', name='Editar', exact=True).click(); page.wait_for_selector('#modal .dc-u')
    check(page.locator('#modal input[type=search]').count() == 1 and page.locator('#modal .bCheck').count() >= 1, 'Editar abre el selector igual que Añadir')
    check(page.locator('#modal .dc-u').count() == 2, 'arriba, 2 unidades: bloque y ejercicio suelto')
    page.locator('#modal .dc-u').nth(0).get_by_role('button', name='Bajar').click(); page.wait_for_timeout(200)
    check('Core básico' in page.locator('#modal .dc-u').nth(1).inner_text(), 'bajar mueve el bloque entero')
    page.locator('#modal .dc-u').nth(0).locator('.dc-nota').fill('30 segundos'); page.locator('#modal .dc-u').nth(0).locator('.dc-nota').blur(); page.wait_for_timeout(300)
    check(any(x['nota'] == '30 segundos' for p in st()['planes'] for x in p['items']), 'la nota se guarda al editarla')
    page.locator('#modal .exCheck').first.check()
    page.get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(300)
    check(page.locator('#modal .dc-u').count() == 3 and page.locator('#modal').count() == 1, 'añadir desde Editar deja el modal abierto con 3 unidades')
    page.locator('#modal .dc-u').nth(0).get_by_role('button', name='Quitar').click(); page.wait_for_timeout(300)
    check(page.locator('#modal .dc-u').count() == 2, 'quitar una unidad')
    while page.locator('#modal .dc-u').count(): page.locator('#modal .dc-u').first.get_by_role('button', name='Quitar').click(); page.wait_for_timeout(200)
    check(page.locator('#modal .dc-lista').count() == 1 and page.locator('#modal .lista-sel').count() == 1, 'al quitar lo último, la ventana sigue abierta con el selector')
    page.locator('#modal .exCheck').first.check(); page.get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(300)
    check(page.locator('#modal .dc-u').count() == 1, 'se puede añadir tras dejar el día vacío')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
