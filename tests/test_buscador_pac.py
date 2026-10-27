# Buscador de bloques y ejercicios en Pautas, Calendario y Plan en casa.
import sys
from playwright.sync_api import sync_playwright
from ayuda_planes import PLAN_PRUEBA
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1400, 'height': 900}); errors = []
    page.on('pageerror', lambda e: errors.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE); page.wait_for_selector('#main')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    # --- Pautas ---
    n = page.locator('#pautasLista > .item').count()
    check(n == 2, f'sin búsqueda, 2 pautas (bloque + suelta) [{n}]')
    page.fill('#qPautas', 'plancha'); check(page.locator('#pautasLista > .item').count() == 1 and 'Core básico' in page.locator('#pautasLista').inner_text(), 'buscar un ejercicio de un bloque muestra el bloque')
    page.fill('#qPautas', 'core'); check(page.locator('#pautasLista > .item').count() == 1, 'buscar por nombre de bloque')
    page.fill('#qPautas', 'estiramiento'); check(page.locator('#pautasLista > .item').count() == 1 and 'Estiramiento' in page.locator('#pautasLista').inner_text(), 'buscar un ejercicio suelto')
    page.fill('#qPautas', 'zzzz'); check('Ninguna pauta coincide' in page.locator('#pautasLista').inner_text(), 'sin coincidencias, avisa')
    page.fill('#qPautas', '')
    # --- Calendario ---
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Calendario').click(); page.wait_for_selector('#qCal')
    page.get_by_role('button', name='Semana', exact=True).click(); page.wait_for_selector('#calCuerpo .cal.semana')
    todos = page.locator('#calCuerpo .chip').count()
    page.fill('#qCal', 'estiramiento'); page.wait_for_timeout(100)
    chips = page.locator('#calCuerpo .chip .nom').all_inner_texts()
    check(0 < len(chips) < todos and all('Estiramiento' in c for c in chips), f'el calendario solo muestra el ejercicio buscado ({len(chips)} de {todos})')
    page.fill('#qCal', 'core'); chips = page.locator('#calCuerpo .chip .nom').all_inner_texts()
    check(len(chips) > 0 and all(('Puente' in c or 'Plancha' in c) for c in chips), 'buscar por bloque muestra sus ejercicios')
    page.get_by_role('button', name='Día', exact=True).click(); page.wait_for_timeout(200)
    check(page.locator('#qCal').input_value() == 'core' and 'de 3' in page.locator('#calCuerpo').inner_text(), 'la búsqueda se mantiene en la vista Día (X de Y)')
    page.fill('#qCal', '')
    # --- Plan en casa ---
    page.evaluate(PLAN_PRUEBA)
    page.evaluate("""() => { const l = iso(inicioSemana(new Date())), g = uid();
      planPrueba(ui.patientId, l, 1, [{dia:1,e:'e1',b:'b1',g},{dia:1,e:'e2',b:'b1',g},{dia:3,e:'e3'}], false); }""")
    page.get_by_role('tab', name='Plan en casa').click(); page.locator('.fila-plan').first.get_by_role('button', name='Editar plan').click(); page.wait_for_selector('#qCasa')
    check(page.locator('#casaCuerpo .pc-it').count() >= 4, 'sin búsqueda se ve todo')
    page.fill('#qCasa', 'plancha'); t = page.locator('#casaCuerpo').inner_text()
    check('Plancha' in t and 'Puente' not in t and 'Estiramiento' not in t and 'Core básico' in t, 'buscar un ejercicio deja el bloque con solo ese ejercicio')
    page.fill('#qCasa', 'core'); t = page.locator('#casaCuerpo').inner_text()
    check('Puente' in t and 'Plancha' in t and 'Estiramiento' not in t, 'un bloque que coincide se muestra entero')
    page.fill('#qCasa', 'estiramiento'); check('Sin coincidencias' in page.locator('.pc-semana .pc-dia').first.inner_text() and page.locator('.pc-semana .pc-dia').first.get_by_role('button', name='Editar').count() == 1, 'los días sin coincidencias lo indican y conservan Editar')
    page.fill('#qCasa', '')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
