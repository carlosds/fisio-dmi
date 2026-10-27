# Ventana del día (calendario): pestañas «Puntuar ejercicios» y «Añadir ejercicios».
import sys
from datetime import date
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
hoy = date.today().isoformat()
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(); errs = []; page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_timeout(400)
    page.evaluate("openPatient('p1')")
    # día vacío: se abre en «Añadir ejercicios»
    page.evaluate("db.pautas = []; render(); openDay(todayIso())"); page.wait_for_timeout(200)
    tabs = page.locator('#tabsDia [role=tab]')
    check(tabs.all_inner_texts() == ['Puntuar ejercicios (0)', 'Añadir ejercicios'], f'pestañas en orden: {tabs.all_inner_texts()}')
    check(page.locator('#tabsDia .on').inner_text() == 'Añadir ejercicios' and page.locator('#secAdd .lista-sel').count() == 1, 'día vacío: se abre en Añadir')
    check(page.locator('#modal details').count() == 0, 'sin secciones plegables')
    page.locator('#secAdd .exItem input').first.check(); page.get_by_role('button', name='Añadir al día').click(); page.wait_for_timeout(250)
    check(page.locator('#tabsDia .on').inner_text() == 'Puntuar ejercicios (1)' and page.locator('#secPun .ej-dia').count() == 1 and page.locator('#secAdd').count() == 0, 'tras añadir se pasa a Puntuar, con el ejercicio')
    page.locator('#secPun .scores button').nth(2).click(); page.wait_for_timeout(150)
    check(page.locator('#tabsDia .on').inner_text().startswith('Puntuar') and page.locator('#secPun .scores button.on').count() == 1, 'puntuar no cambia de pestaña')
    page.locator('#modal .modalx').click(); page.wait_for_timeout(100)
    page.evaluate("openDay(todayIso())"); page.wait_for_timeout(150)
    check(page.locator('#tabsDia .on').inner_text().startswith('Puntuar'), 'día con ejercicios: se abre en Puntuar')
    page.get_by_role('tab', name='Añadir ejercicios').click(); page.wait_for_timeout(150)
    check(page.locator('#secAdd').count() == 1 and page.locator('#secPun').count() == 0, 'cambiar a la pestaña Añadir')
    page.locator('#modal .modalx').click(); page.evaluate("ui.tabP = 'calendario'; ui.vista = 'dia'; ui.fecha = new Date(); render()"); page.wait_for_timeout(200)
    btn = page.locator('#main').get_by_role('button', name='Añadir ejercicios')
    if btn.count():
        btn.first.click(); page.wait_for_timeout(150)
        check(page.locator('#tabsDia .on').inner_text() == 'Añadir ejercicios', 'el botón «Añadir ejercicios» del calendario abre esa pestaña')
    check(not errs, f'sin errores JS {errs}')
    b.close()
sys.exit(1 if fails else 0)
