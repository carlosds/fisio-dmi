# 0.0.7 (análisis de usabilidad): buscador de pacientes en la barra, lista de pacientes en columnas, acciones que
# borran en el menú «⋯», filtros de fecha plegados, cabecera de la ficha sin días por semana, atajos en el «?» y
# bloques en una columna.
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_v007.py PUERTO
import sys
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; BASE = f'http://127.0.0.1:{PORT}/'
fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)

with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_page(viewport={'width': 1300, 'height': 900})
    errs = []; page.on('pageerror', lambda e: errs.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE); page.wait_for_selector('#listaPacientes')
    ev = page.evaluate
    ev("""() => { db.patients.push({ id: 'p2', nombre: 'Luis', apellidos: 'Beltrán', telefono: '', email: '', archivado: false },
                                  { id: 'p3', nombre: 'Lucía', apellidos: 'Otero', telefono: '', email: '', archivado: true });
      db.citas.push({ id: 'c1', patientId: 'p2', fecha: addDays(todayIso(), 2), hora: '10:00', duracion: 45, nota: '', color: '', serieId: '', fechaSerie: '' });
      go('pacientes'); }""")
    page.wait_for_timeout(200)

    print('\n[1] Buscador de pacientes en la barra')
    page.locator('#listaPacientes .fila-pac a').first.click(); page.wait_for_selector('.sticky-head')
    page.keyboard.press('Control+k')
    check(ev("document.activeElement.id") == 'buscaPacInput', 'Ctrl+K enfoca el buscador de la barra')
    page.keyboard.type('lu'); page.wait_for_timeout(100)
    ops = page.locator('#buscaPacRes .busca-op')
    check(ops.count() == 2 and 'Beltrán, Luis' in ops.first.inner_text() and 'Archivado' in ops.nth(1).inner_text(), f'muestra los que coinciden, los archivados al final ({ops.all_inner_texts()})')
    check('Próxima sesión' in ops.first.inner_text(), 'con su próxima sesión')
    page.keyboard.press('Enter'); page.wait_for_timeout(200)
    check(ev("[ui.view, ui.patientId]") == ['paciente', 'p2'] and page.input_value('#buscaPacInput') == '' and page.locator('#buscaPacRes').is_hidden(), 'Intro abre su ficha y limpia el buscador')
    ev("openDay(todayIso())"); page.wait_for_selector('#modal .card')
    page.fill('#buscaPacInput', 'lópez'); page.keyboard.press('ArrowDown'); page.keyboard.press('Enter'); page.wait_for_timeout(200)
    check(ev("ui.patientId") == 'p1' and not ev("$('#modal').innerHTML"), 'desde una ventana abierta también: la cierra y abre la ficha')
    page.fill('#buscaPacInput', 'zzz'); page.wait_for_timeout(100)
    check('Ningún paciente coincide' in page.locator('#buscaPacRes').inner_text(), 'sin coincidencias, lo dice')
    page.keyboard.press('Escape'); check(page.locator('#buscaPacRes').is_hidden(), 'Esc lo cierra')

    print('\n[2] Cabecera de la ficha y pautas')
    check('por semana' not in page.locator('.sticky-head').inner_text(), 'la cabecera ya no dice los días por semana')
    sec = page.locator('#sec-pautas')
    check(sec.locator('button.danger').count() == 0, 'Pautas: ningún botón rojo a la vista')
    sec.locator('.menu-mas').first.click()
    check(sec.get_by_role('button', name='Quitar todas las pautas…').is_visible(), 'el «⋯» de arriba tiene «Quitar todas las pautas…»')
    page.keyboard.press('Escape')
    check(sec.locator('.fila-pauta .menu-mas').count() == sec.locator('.fila-pauta').count(), 'cada pauta tiene su «⋯»')
    check(not page.locator('#fpaDesde').is_visible() and page.locator('#fpaFechas > summary').inner_text().startswith('Filtrar por fecha'), 'los filtros de fecha están plegados')
    page.locator('#fpaFechas > summary').click(); page.select_option('#fpaAnio', page.locator('#fpaAnio option').nth(1).get_attribute('value') or page.locator('#fpaAnio option').nth(1).inner_text()); page.wait_for_timeout(100)
    check(page.locator('#fpaFechas .filtro-activo').is_visible(), 'con un filtro puesto, el botón dice «activo»')
    ev("irTab('calendario'); irTab('pautas')"); page.wait_for_timeout(100)
    check(page.locator('#fpaDesde').is_visible(), 'y al volver sigue abierto')

    print('\n[3] Ventana del día')
    ev("openDay(todayIso(), 'puntuar')"); page.wait_for_selector('#modal .ej-dia')
    m = page.locator('#modal')
    check('Teclado:' not in m.inner_text() and 'atajos de teclado en el «?»' in m.inner_text(), 'los atajos de teclado están en el «?»')
    check(m.locator('.ej-dia button.danger, .ej-dia button.quitar').count() == 0 and m.locator('.ej-dia .menu-mas').count() == m.locator('.ej-dia').count(), '«Quitar» de cada ejercicio va en su «⋯»')
    m.locator('.ej-dia .menu-mas').first.click()
    m.locator('.ej-dia').first.get_by_role('button', name='Quitar de este día').click(); page.wait_for_timeout(300)
    check(m.locator('.ej-dia').count() == 2, 'y quita el ejercicio de ese día')
    ev('closeModal()')

    print('\n[4] Lista de pacientes en columnas')
    ev("go('pacientes')"); page.wait_for_timeout(200)
    fila = page.locator('#listaPacientes .fila-pac', has_text='Beltrán')
    check(ev("getComputedStyle(document.querySelector('#listaPacientes .fila-pac')).display") == 'grid', 'cada paciente es una fila en columnas')
    xs = ev("[...document.querySelectorAll('#listaPacientes .cab-pac > *')].map(e => Math.round(e.getBoundingClientRect().left))")
    xf = ev("[...document.querySelectorAll('#listaPacientes .fila-pac')[0].children].map(e => Math.round(e.getBoundingClientRect().left))")
    check(xs[:5] == xf[:5], f'las columnas de la cabecera y de las filas coinciden ({xs[:5]} / {xf[:5]})')
    check(page.locator('#listaPacientes .cab-pac input[type=checkbox]').count() == 1 and 'Seleccionar los' in page.locator('#listaPacientes .cab-pac input').get_attribute('aria-label'), 'la casilla de marcar todos está en la cabecera')
    check(fila.get_by_role('button', name='Próxima sesión').count() == 1, 'la próxima sesión, en su columna y enlazada')
    alto = fila.bounding_box()['height']
    check(alto < 70, f'cada fila ocupa poco ({alto:.0f} px)')
    cy = lambda sel: (lambda bb: bb['y'] + bb['height'] / 2)(page.locator(sel).bounding_box())
    check(abs(cy('#filtroSesiones') - cy('#buscarPac')) < 12, 'el filtro «Con sesiones» está en la fila del buscador')

    print('\n[5] Bloques en una columna, con su «⋯»')
    ev("go('bloques')"); page.wait_for_selector('#listaBloques .item')
    check(ev("getComputedStyle(document.querySelector('#listaBloques')).columnWidth") in ('auto', 'normal'), 'la lista de bloques es de una columna')
    check(page.locator('#listaBloques button.danger').count() == 0 and page.locator('#listaBloques .menu-mas').count() >= 1, '«Eliminar bloque…» va en el «⋯»')

    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
