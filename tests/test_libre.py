# Ejercicio escrito a mano en el plan en casa.
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
    nbib = page.evaluate("biblioteca().length")
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    page.get_by_role('tab', name='Plan en casa').click(); page.wait_for_timeout(200)
    page.get_by_role('button', name='Nuevo plan').click(); page.wait_for_selector('#pcNombre')
    dia = page.locator('.pc-semana .pc-dia:not(.pc-fuera)').first
    dia.locator('.pc-add').click(); page.wait_for_selector('#acLibre')
    page.locator('#acLibre').fill('Caminar 20 minutos\nEstiramiento de isquiotibiales')
    page.locator('#acNota').fill('sin dolor')
    page.get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(500)
    dia = page.locator('.pc-semana .pc-dia:not(.pc-fuera)').first
    t = dia.inner_text()
    check('Caminar 20 minutos' in t and 'Estiramiento de isquiotibiales' in t, 'los dos textos libres salen en el día')
    s = st()
    libres = [e for e in s['exercises'] if e.get('libre')]
    check(len(libres) == 2 and sum(len(p['items']) for p in s['planes']) >= 2, 'se guardan como ejercicios libres y entradas del plan')
    check(page.evaluate("biblioteca().length") == nbib, 'no aparecen en la biblioteca de ejercicios')
    dia.get_by_role('button', name='Editar', exact=True).click(); page.wait_for_selector('#modal .dc-u')
    check('Caminar 20 minutos' in page.locator('#modal .dc-lista').inner_text(), 'se ven al editar el día')
    page.locator('#modal button.ghost', has_text='Cerrar').click()
    page.locator('.pc-semana .pc-dia:not(.pc-fuera)').first.get_by_role('button', name='Editar', exact=True).click(); page.wait_for_selector('#modal .dc-lista')
    page.locator('#modal').get_by_role('button', name='Vaciar el día…').click(); page.wait_for_timeout(300)
    page.get_by_role('tab', name='Pautas').click(); page.wait_for_timeout(500)
    check(not [e for e in st()['exercises'] if e.get('libre')], 'al quitarlos del plan se limpian solos')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
