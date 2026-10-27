# Repeticiones en calendario y resumen, buscador del resumen e informe PDF del periodo visto.
import sys
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
hoy = date.today()
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(viewport={'width': 1300, 'height': 900}); errs = []; page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_timeout(400)
    page.evaluate("descartarNovedades(); openPatient('p1')")
    e1 = page.evaluate("db.pautas.find(x => x.patientId === 'p1').exerciseId"); n1 = page.evaluate(f"getE('{e1}').nombre")
    page.evaluate(f"db.puntuaciones[scoreKey('p1', todayIso(), '{e1}', 1)] = 3; db.puntuaciones[scoreKey('p1', todayIso(), '{e1}', 2)] = 1; db.puntuaciones[scoreKey('p1', todayIso(), '{e1}', 3)] = null; idxPunt = null; ui.vista = 'mes'; render()")
    page.get_by_role('tab', name='Calendario').click(); page.wait_for_timeout(200)
    check('Pulsa un día para añadir, quitar o puntuar ejercicios de ese día.' in page.locator('#sec-calendario').inner_text(), 'texto de ayuda nuevo')
    page.evaluate("cambiarVista('semana')"); page.wait_for_timeout(150)   # en el mes, las celdas solo resumen; los chips se ven en la semana
    chip = page.locator('.day.today .chip', has_text=n1).first
    check(chip.locator('.nrep').inner_text() == '(3)' and chip.locator('.pun').inner_text() == '2', f'chip: «(3)» antes de la media 2 ({chip.inner_text()!r})')
    check('3 repeticiones' in chip.get_attribute('title'), 'el chip explica las repeticiones al pasar el ratón')
    otros = page.locator('.day.today .chip').filter(has_not_text=n1)
    check(otros.count() == 0 or otros.first.locator('.nrep').count() == 0, 'con una sola repetición no se añade nada')
    page.evaluate("cambiarVista('mes')"); page.wait_for_timeout(150)
    # informe del periodo del calendario (mes)
    page.locator('#btnInformeCal').click(); page.wait_for_selector('#expDesde')
    ini = hoy.replace(day=1).isoformat(); fin = (hoy.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    check(page.input_value('#expDesde') == ini and page.input_value('#expHasta') == fin.isoformat(), f'Calendario (mes): el informe propone el mes ({page.input_value("#expDesde")} – {page.input_value("#expHasta")})')
    page.evaluate('closeModal()')
    # Resumen
    page.locator('#subCal').get_by_role('button', name='Resumen').click(); page.wait_for_timeout(200)
    check(page.locator('#btnInformeCal').count() == 1, 'el botón de informe también está en Resumen')
    page.locator('#sec-resumen .tabs:not(#subCal)').first.get_by_role('button', name='Semana', exact=True).click(); page.wait_for_timeout(200)
    page.locator('#btnInformeCal').click(); page.wait_for_selector('#expDesde')
    lunes = hoy - timedelta(days=hoy.weekday())
    check(page.input_value('#expDesde') == lunes.isoformat() and page.input_value('#expHasta') == (lunes + timedelta(days=6)).isoformat(), 'Resumen (semana): el informe propone la semana')
    page.evaluate('closeModal()')
    page.get_by_role('button', name='Lista', exact=True).click(); page.wait_for_timeout(150)
    fila = page.locator('#resCuerpo tr', has_text=n1).first
    check('(1–3 reps)' in fila.inner_text() or '(3 reps)' in fila.inner_text(), f'lista: el ejercicio indica sus repeticiones ({fila.inner_text()!r})')
    check(page.locator('#resCuerpo tr.rep-sub').count() == 0, 'lista: por defecto, sin subfilas de repeticiones')
    page.get_by_label('Ver cada repetición').check(); page.wait_for_timeout(150)
    subs = page.locator('#resCuerpo tr.rep-sub')
    check(subs.count() == 3 and subs.nth(0).inner_text().startswith('Rep. 1') and subs.nth(2).inner_text().startswith('Rep. 3'), f'lista: una subfila por repetición ({subs.count()})')
    check(subs.nth(1).locator('td').nth(3).inner_text() == '1.0' and subs.nth(2).locator('td').nth(2).inner_text() == '0', 'lista: media y puntuadas por repetición')
    # buscador
    page.fill('#qRes', 'zzzz'); page.wait_for_timeout(150)
    check('Ningún bloque o ejercicio coincide' in page.locator('#resCuerpo').inner_text(), 'buscador: sin coincidencias')
    page.fill('#qRes', n1); page.wait_for_timeout(150)
    check(page.locator('#resCuerpo tbody tr:not(.rep-sub):not(.grp)').count() == 1 and page.evaluate("document.activeElement.id") == 'qRes', 'buscador: filtra y mantiene el foco')
    page.fill('#qRes', ''); page.wait_for_timeout(100)
    # puntos
    page.get_by_role('button', name='Puntos', exact=True).click(); page.wait_for_timeout(200)
    textos = page.locator('#resCuerpo svg text').all_text_contents()
    check(all(f'Rep. {k}' in textos for k in (1, 2, 3)), 'puntos: subfilas Rep. 1, 2 y 3')
    check(page.locator('#resCuerpo svg circle title', has_text='Rep. 2').count() >= 1, 'puntos: cada punto de repetición tiene su descripción')
    page.evaluate(f"db.puntuaciones[scoreKey('p1', todayIso(), '{e1}', 2)] = 2; idxPunt = null; render()"); page.wait_for_timeout(200)
    check('2,5' in page.locator('#resCuerpo svg').text_content(), 'puntos: la media del ejercicio no se redondea (3 y 2 → 2,5)')
    # líneas
    page.get_by_role('button', name='Líneas', exact=True).click(); page.wait_for_timeout(200)
    ley = page.locator('#resCuerpo .legend').inner_text()
    check(n1 + ' (' in ley and 'reps)' in ley, f'líneas: la leyenda indica las repeticiones ({ley[:80]!r})')
    tit = page.locator('#resCuerpo svg circle title').all_text_contents()
    check(any('(3 reps)' in t and 'media 2' in t for t in tit), 'líneas: el punto de hoy indica 3 reps y la media')
    check(not errs, f'sin errores JS {errs}')
    b.close()
sys.exit(1 if fails else 0)
