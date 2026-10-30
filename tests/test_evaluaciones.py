import json, sys, urllib.request
from playwright.sync_api import sync_playwright
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
    check(page.locator('.ptabs [role=tab]').all_inner_texts() == ['Pautas', 'Calendario', 'Plan en casa', 'Sesiones', 'Progreso ▾', 'Informes'], 'orden de pestañas: Pautas, Calendario, Plan en casa, Sesiones, Progreso, Informes')
    page.get_by_role('tab', name='Progreso').click(); page.get_by_role('menuitem', name='Evaluación inicial').click(); page.wait_for_selector('#sec-evaluaciones')
    check('Todavía no hay evaluaciones' in page.locator('#listaEvaluaciones').inner_text(), 'estado vacío')
    check(page.locator('#sec-evaluaciones label', has_text='Evaluación').count() == 1, 'el campo se llama «Evaluación»')
    (page.get_by_role('button', name='Nueva evaluación…').click() if page.locator('#evTexto').is_hidden() else None); page.fill('#evFecha', '2026-03-10'); page.fill('#evTexto', 'Flexión lumbar 40º, dolor 6/10')
    page.get_by_role('button', name='Añadir evaluación').click(); page.wait_for_timeout(300)
    (page.get_by_role('button', name='Nueva evaluación…').click() if page.locator('#evTexto').is_hidden() else None); page.fill('#evFecha', '2026-04-10'); page.fill('#evTexto', 'Flexión lumbar 55º, dolor 3/10')
    page.get_by_role('button', name='Añadir evaluación').click(); page.wait_for_timeout(300)
    ev = st()['evaluaciones']
    check(len(ev) == 2 and ev[0]['evaluacion'].startswith('Flexión lumbar 40'), 'se guardan en el servidor')
    check(page.locator('#listaEvaluaciones tbody tr').first.inner_text().startswith('10/04/2026') or '55º' in page.locator('#listaEvaluaciones tbody tr').first.inner_text(), 'la más reciente primero')
    page.fill('#evBuscar', '40º'); page.wait_for_timeout(200)
    check(page.locator('#listaEvaluaciones tbody tr').count() == 1, 'buscar filtra')
    page.fill('#evBuscar', '')
    page.locator('#listaEvaluaciones tbody tr').first.get_by_role('button', name='Editar').click()
    page.fill('#eevTexto', 'Flexión lumbar 60º'); page.get_by_role('button', name='Guardar', exact=True).click(); page.wait_for_timeout(300)
    check(any(e['evaluacion'] == 'Flexión lumbar 60º' for e in st()['evaluaciones']), 'editar')
    fila = page.locator('#listaEvaluaciones tbody tr').first
    fila.locator('.menu-mas').click(); fila.get_by_role('button', name='Eliminar evaluación…').click(); page.wait_for_timeout(300)
    check(len(st()['evaluaciones']) == 1, 'eliminar')
    page.get_by_role('tab', name='Progreso').click(); page.get_by_role('menuitem', name='Hitos').click(); check(page.locator('#sec-hitos').count() == 1, 'Hitos sigue funcionando')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
