# En negrita solo salen los bloques; los ejercicios (sueltos o dentro de un bloque) van en texto normal.
import sys
from playwright.sync_api import sync_playwright
from ayuda_planes import PLAN_PRUEBA
PORT = int(sys.argv[1]); ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
peso = "e => parseInt(getComputedStyle(e).fontWeight, 10)"
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = br.new_page(viewport={'width': 1300, 'height': 900}); page.on('dialog', lambda d: d.accept())
    page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_selector('#main')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    # pautas de ejemplo: el bloque b1 (e1, e2) y el ejercicio suelto e3 ya están en el seed
    t = page.locator('#sec-pautas .item')
    pesos = [t.nth(i).locator(':scope > div > span').first.evaluate(peso) for i in range(t.count())]
    nombres = [t.nth(i).inner_text().split('\n')[0] for i in range(t.count())]
    for n, w in zip(nombres, pesos):
        esbloque = 'Core' in n
        check((w >= 600) == esbloque, f'Pautas: «{n}» {"(bloque) en negrita" if esbloque else "(ejercicio suelto) en texto normal"} [{w}]')
    # ventana del día y vista de día
    page.evaluate("ui.selDay = '2026-06-10'; renderDayModal()"); page.wait_for_selector('#modal .ej-dia')
    check(page.locator('#modal .grp-titulo').first.evaluate(peso) >= 600, 'Puntuación: el título del bloque va en negrita')
    ws = page.locator('#modal .ej-dia .ej-nom-dia').evaluate_all(f"els => els.map({peso})")
    check(ws and all(w < 600 for w in ws), f'Puntuación: los ejercicios van en texto normal {ws}')
    page.get_by_role('button', name='Cerrar').last.click()
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Calendario').click(); page.evaluate("cambiarVista('dia')"); page.wait_for_timeout(200)
    ws = page.locator('#sec-calendario .ej-dia .ej-nom-dia').evaluate_all(f"els => els.map({peso})")
    check(ws and all(w < 600 for w in ws), 'Vista de día: ejercicios en texto normal')
    # plan en casa (bloque + suelto) y ventana de edición del día
    page.get_by_role('tab', name='Plan en casa').click()
    page.evaluate(PLAN_PRUEBA)
    page.evaluate("""() => { const l = iso(inicioSemana(new Date())), g = uid();
      planPrueba(ui.patientId, l, 1, [{dia:1,e:'e1',b:'b1',g},{dia:1,e:'e2',b:'b1',g},{dia:1,e:'e3'}]); }""")
    check(page.locator('.pc-semana .pc-dia').first.locator('.pc-g .pc-it strong').count() == 1, 'Plan en casa: solo el bloque lleva negrita')
    ws = page.locator('.pc-semana .pc-dia').first.locator('.pc-g-ej .pc-it > div > div, .pc-suelto .pc-it > div > div').evaluate_all(f"els => els.map({peso})")
    check(ws and all(w < 600 for w in ws), 'Plan en casa: ejercicios en texto normal')
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
