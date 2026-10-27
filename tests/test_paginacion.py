# Paginación de las listas: 10, 25, 50, 100 o todos por página; se recuerda por lista; la búsqueda vuelve a la primera página.
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_paginacion.py PUERTO
import json, sys, urllib.request
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; BASE = f'http://127.0.0.1:{PORT}'
fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
st = lambda: json.loads(urllib.request.urlopen(BASE + '/__state').read())

with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_page(viewport={'width': 1300, 'height': 900})
    errs = []; page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(BASE + '/'); page.wait_for_selector('#listaPacientes'); page.evaluate('descartarNovedades()')
    # 60 pacientes (Apellido00…Apellido59) y 30 ejercicios.
    page.evaluate("""for (let i = 0; i < 60; i++) db.patients.push({ id: 'pp' + i, nombre: 'Nombre', apellidos: 'Apellido' + String(i).padStart(2, '0'), telefono: '', email: '', fechaAlta: '2026-01-01', foto: '' });
      for (let i = 0; i < 30; i++) db.exercises.push({ id: 'ee' + i, nombre: 'Ejercicio paginado ' + String(i).padStart(2, '0') });
      render()""")
    filas = lambda: page.locator('#listaPacientes .fila-pac').count()
    pag = page.locator('#pag-pacientes')

    print('\n[1] Lista de pacientes')
    total = page.evaluate('pacientesVisibles().length')
    check(filas() == 25, f'por defecto se ven 25 de {total}')
    check(f'1–25 de {total}' in pag.inner_text() and 'Página 1 de' in pag.inner_text(), 'la botonera dice qué se ve y en qué página')
    check(pag.get_by_role('button', name='‹ Anterior').is_disabled(), 'en la primera página, «Anterior» está desactivado')
    pag.get_by_role('button', name='Siguiente ›').click()
    check(f'26–50 de {total}' in pag.inner_text(), '«Siguiente» pasa a la página 2')
    pag.locator('select').select_option('10')
    check(filas() == 10, 'con 10 por página se ven 10')
    check(f'21–30 de {total}' in pag.inner_text(), 'al cambiar el tamaño se sigue viendo el primero que se veía (el 26.º, en la página 21–30)')
    check(st()['ajustes'].get('pagina.pacientes') == '10', 'el tamaño elegido se guarda en los ajustes')
    pag.locator('select').select_option('todos')
    check(filas() == total and 'Página' not in pag.inner_text(), '«Todos» muestra la lista entera, sin páginas')
    pag.locator('select').select_option('50')
    pag.get_by_role('button', name='Siguiente ›').click()
    check(filas() == total - 50, 'la última página muestra el resto')
    page.fill('#buscarPac', 'Apellido0')
    check(filas() == 10 and page.locator('#pag-pacientes').count() == 0, 'al buscar se vuelve a la primera página; con 10 o menos no hay botonera')
    page.fill('#buscarPac', '')
    check('1–50' in pag.inner_text(), 'al quitar la búsqueda, primera página')
    page.locator('#listaPacientes input[type=checkbox]').first.check()
    check(page.evaluate('ui.selected.size') == total, '«Seleccionar los N» marca a todos, también los de otras páginas')
    page.locator('#listaPacientes input[type=checkbox]').first.uncheck()
    page.reload(); page.wait_for_selector('#listaPacientes')
    check(filas() == 50, 'tras recargar se recuerda cuántos por página')

    print('\n[2] Ejercicios (otra lista, su propio tamaño)')
    page.evaluate("go('ejercicios')"); page.wait_for_selector('#listaEjercicios')
    n = page.evaluate('biblioteca().length')
    check(page.locator('#listaEjercicios .item').count() == min(25, n), 'ejercicios: 25 por defecto, sin heredar el de pacientes')
    page.locator('#pag-ejercicios select').select_option('10')
    page.locator('#pag-ejercicios').get_by_role('button', name='Siguiente ›').click()
    check('11–20' in page.locator('#pag-ejercicios').inner_text(), 'ejercicios: página 2 de 10 en 10')
    check(st()['ajustes'].get('pagina.pacientes') == '50', 'cada lista recuerda el suyo')

    print('\n[3] Hitos del paciente')
    page.evaluate("for (let i = 0; i < 14; i++) db.hitos.push({ id: 'hh' + i, patientId: 'pp0', fecha: addDays('2026-01-01', i), nota: 'Nota ' + i, fotos: [] }); openPatient('pp0'); irTab('hitos')")
    page.wait_for_selector('#listaHitos tbody tr')
    hp = page.locator('#pag-hitos')
    hp.locator('select').select_option('10')
    check(page.locator('#listaHitos tbody tr').count() == 10 and 'Página 1 de 2' in hp.inner_text(), 'hitos: 10 por página, dos páginas')
    hp.get_by_role('button', name='Siguiente ›').click()
    check(page.locator('#listaHitos tbody tr').count() == 4, 'hitos: la segunda página tiene los 4 que faltan')

    print('\n[4] Sin errores')
    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS'); sys.exit(1 if fails else 0)
