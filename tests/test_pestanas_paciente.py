# Pestañas del paciente: submenú «Progreso» (Evaluación inicial, Hitos) y subpestañas Calendario / Resumen.
import sys
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(); errs = []; page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_timeout(400)
    page.evaluate("descartarNovedades(); openPatient('p1')"); page.wait_for_timeout(200)
    check(page.locator('.ptabs .on').inner_text() == 'Pautas', 'al abrir un paciente se ve Pautas')
    prog = page.get_by_role('tab', name='Progreso')
    check(page.locator('#tab-progreso .submenu').is_hidden(), 'el submenú Progreso empieza cerrado')
    prog.click(); page.wait_for_timeout(100)
    check(page.get_by_role('menuitem').all_inner_texts() == ['Evaluación inicial', 'Hitos'], 'Progreso: Evaluación inicial e Hitos')
    page.keyboard.press('Escape'); page.wait_for_timeout(100)
    check(page.locator('#tab-progreso .submenu').is_hidden(), 'Esc cierra el submenú')
    prog.click(); page.get_by_role('menuitem', name='Evaluación inicial').click(); page.wait_for_timeout(200)
    check(page.locator('#sec-evaluaciones').count() == 1 and 'Evaluación inicial' in page.locator('#sec-evaluaciones h3').first.inner_text(), 'abre la Evaluación inicial')
    check('on' in (prog.get_attribute('class') or '') and page.locator('#tab-progreso .submenu').is_hidden(), 'Progreso queda marcado y el submenú se cierra')
    prog.click(); page.get_by_role('menuitem', name='Hitos').click(); page.wait_for_timeout(200)
    check(page.locator('#sec-hitos').count() == 1, 'abre Hitos')
    prog.click(); page.locator('#main').click(position={'x': 5, 'y': 400}); page.wait_for_timeout(100)
    check(page.locator('#tab-progreso .submenu').is_hidden(), 'pulsar fuera cierra el submenú')
    # Calendario / Resumen
    page.get_by_role('tab', name='Calendario').click(); page.wait_for_timeout(200)
    check(page.locator('#sec-calendario').count() == 1 and page.locator('#subCal .on').inner_text() == 'Calendario', 'Calendario abre la vista de calendario')
    page.locator('#subCal').get_by_role('button', name='Resumen').click(); page.wait_for_timeout(200)
    check(page.locator('#sec-resumen').count() == 1 and page.locator('#sec-calendario').count() == 0 and page.locator('.ptabs .on').first.inner_text() == 'Calendario', 'subpestaña Resumen dentro de Calendario')
    page.get_by_role('tab', name='Pautas').click(); page.get_by_role('tab', name='Calendario').click(); page.wait_for_timeout(200)
    check(page.locator('#sec-resumen').count() == 1, 'al volver a Calendario se recuerda la subpestaña')
    page.locator('#subCal').get_by_role('button', name='Calendario').click(); page.wait_for_timeout(200)
    check(page.locator('#sec-calendario').count() == 1, 'volver a la vista Calendario')
    page.evaluate("irTab('resumen')"); page.wait_for_timeout(150)
    check(page.locator('#sec-resumen').count() == 1, "irTab('resumen') lleva al Resumen dentro de Calendario")
    check(not errs, f'sin errores JS {errs}')
    b.close()
sys.exit(1 if fails else 0)
