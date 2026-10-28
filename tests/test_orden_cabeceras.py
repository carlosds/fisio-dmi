# Ordenar listas y tablas pulsando la cabecera de una columna: ascendente, descendente y vuelta al orden por
# defecto; se recuerda por lista, los vacíos van al final y no quedan desplegables «Ordenar por».
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_orden_cabeceras.py PUERTO
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
    errs = []; page.on('pageerror', lambda e: errs.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE + '/'); page.wait_for_selector('#listaPacientes')
    ev = page.evaluate
    ev("""() => { const hoy = todayIso(), d = n => addDays(hoy, n);
      db.patients.push({ id: 'p2', nombre: 'Luis', apellidos: 'Beltrán', archivado: false }, { id: 'p3', nombre: 'Marta', apellidos: 'Cruz', archivado: false });
      const cita = (id, pid, n, h) => ({ id, patientId: pid, fecha: d(n), hora: h, duracion: 45, nota: '', color: '', serieId: '', fechaSerie: '' });
      db.citas.push(cita('c1', 'p1', 2, '10:00'), cita('c2', 'p2', 1, '09:00'), cita('c3', 'p1', -3, '10:00'), cita('c4', 'p1', 5, '08:00'));
      db.hitos.push({ id: 'h1', patientId: 'p1', fecha: '2026-01-10', nota: 'Bravo', fotos: [] }, { id: 'h2', patientId: 'p1', fecha: '2026-03-10', nota: 'Alfa', fotos: [] });
      db.informes.push({ id: 'i1', patientId: 'p1', tipo: 'informe', nombre: 'a.pdf', ruta: '/x/a.pdf', fecha: '2026-09-01T10:00:00Z', desde: '2026-08-01', hasta: '2026-08-31', descripcion: 'Zeta' },
                       { id: 'i2', patientId: 'p1', tipo: 'plan', nombre: 'b.pdf', ruta: '/x/b.pdf', fecha: '2026-10-01T10:00:00Z', desde: '2026-10-01', hasta: '2026-10-31', descripcion: 'Alfa' });
      go('pacientes'); }""")
    page.wait_for_timeout(200)
    check(page.locator('select#ordenPac, select#ordenInformes').count() == 0 and 'Ordenar por' not in page.locator('#main').inner_text(), 'no quedan desplegables «Ordenar por»')

    print('\n[1] Pacientes: cabecera con tres estados')
    nombres = lambda: page.locator('#listaPacientes .fila-pac a').all_inner_texts()
    cab = page.locator('#listaPacientes .cab-lista')
    check(nombres() == ['Beltrán, Luis', 'Cruz, Marta', 'López Pérez, Ana'], 'por defecto, por apellidos')
    check(cab.locator('.orden-btn.on').inner_text().startswith('Paciente') and '▲' in cab.locator('.orden-btn.on').inner_text(), 'la cabecera marca la columna y el sentido')
    cab.get_by_role('button', name='Próxima sesión').click(); page.wait_for_timeout(100)
    check(nombres() == ['Beltrán, Luis', 'López Pérez, Ana', 'Cruz, Marta'], f'«Próxima sesión» ascendente, sin sesión al final {nombres()}')
    cab.get_by_role('button', name='Próxima sesión').click(); page.wait_for_timeout(100)
    check(nombres() == ['López Pérez, Ana', 'Beltrán, Luis', 'Cruz, Marta'], f'otra vez: descendente, sin sesión sigue al final {nombres()}')
    check(st()['ajustes'].get('orden.pacientes') == 'proxima:desc' or ev("db.ajustes['orden.pacientes']") == 'proxima:desc', 'el orden se recuerda en los ajustes')
    ev("go('ejercicios')"); ev("go('pacientes')"); page.wait_for_timeout(100)
    check(nombres() == ['López Pérez, Ana', 'Beltrán, Luis', 'Cruz, Marta'], 'al volver a la pantalla sigue el mismo orden')
    cab = page.locator('#listaPacientes .cab-lista')
    cab.get_by_role('button', name='Próxima sesión').click(); page.wait_for_timeout(100)
    check(nombres() == ['Beltrán, Luis', 'Cruz, Marta', 'López Pérez, Ana'] and not ev("db.ajustes['orden.pacientes']"), 'la tercera vez vuelve al orden por defecto')
    cab = page.locator('#listaPacientes .cab-lista')
    cab.get_by_role('button', name='Paciente').click(); page.wait_for_timeout(100)
    check(nombres() == ['López Pérez, Ana', 'Cruz, Marta', 'Beltrán, Luis'], 'en la columna por defecto, un clic la invierte')

    print('\n[2] Tablas con <th>: hitos (aria-sort)')
    ev("openPatient('p1'); irTab('hitos')"); page.wait_for_selector('#listaHitos table')
    notas = lambda: page.locator('#listaHitos tbody td.nota').all_inner_texts()
    th = page.locator('#listaHitos th', has_text='Fecha')
    check(notas() == ['Alfa', 'Bravo'] and th.get_attribute('aria-sort') == 'descending', 'por defecto, la más reciente primero (aria-sort descendente)')
    th.locator('button').click(); page.wait_for_timeout(100)
    check(notas() == ['Bravo', 'Alfa'] and page.locator('#listaHitos th', has_text='Fecha').get_attribute('aria-sort') == 'ascending', 'al pulsar «Fecha», ascendente')
    page.locator('#listaHitos th', has_text='Notas').locator('button').click(); page.wait_for_timeout(100)
    check(notas() == ['Alfa', 'Bravo'], 'por «Notas», alfabético')

    print('\n[3] Informes')
    ev("irTab('informes')"); page.wait_for_selector('#listaInformes .infItem')
    titulos = lambda: [t.split('\n')[0] for t in page.locator('#listaInformes .infItem strong').all_inner_texts()]
    check(titulos() == ['Alfa', 'Zeta'], 'por defecto, el generado más reciente primero')
    page.locator('#listaInformes .cab-lista').get_by_role('button', name='Informe').click(); page.wait_for_timeout(100)
    check(titulos() == ['Alfa', 'Zeta'], 'por nombre del informe, ascendente')
    page.locator('#listaInformes .cab-lista').get_by_role('button', name='Informe').click(); page.wait_for_timeout(100)
    check(titulos() == ['Zeta', 'Alfa'], 'y descendente')
    page.fill('#buscarInformes', 'a'); page.wait_for_timeout(100)
    check(page.evaluate("document.activeElement.id") == 'buscarInformes', 'la búsqueda sigue funcionando con la cabecera')

    print('\n[4] Sesiones del paciente')
    ev("irTab('citas'); filtroSes().ver = 'todas'; render()"); page.wait_for_selector('#listaSesiones .cita-fila')
    fechas = lambda: ev("[...document.querySelectorAll('#listaSesiones .cita-fila')].map(e => e.querySelector('button[onclick^=puntuarCita]').getAttribute('onclick').split(\"'\")[3])")
    f0 = fechas()
    check(f0 == sorted(f0), 'por defecto, por fecha ascendente')
    page.locator('#listaSesiones .cab-lista').get_by_role('button', name='Sesión').click(); page.wait_for_timeout(100)
    check(fechas() == sorted(f0, reverse=True), 'al pulsar «Sesión», descendente')
    ev("filtroSes().ver = 'pasadas'; render()"); page.wait_for_timeout(100)
    check(page.locator('#listaSesiones .orden-btn.on').inner_text().endswith('▼'), 'las pasadas tienen su propio orden (por defecto, la más reciente primero)')

    print('\n[5] Resumen: se ordena dentro de cada bloque')
    ev("irTab('calendario'); subCal('resumen')"); page.wait_for_selector('#sec-resumen thead')
    filas = lambda: page.locator('#sec-resumen table tbody tr').all_inner_texts()
    antes = filas()
    page.locator('#sec-resumen th', has_text='Ejercicio').locator('button').click(); page.wait_for_timeout(100)
    despues = filas()   # alfabético (Plancha antes que Puente, al revés que en el orden de ejecución)
    grupo = lambda xs: [x for x in xs if '\t' not in x]   # títulos de bloque (una sola celda)
    check(grupo(antes) == grupo(despues), 'los bloques siguen en su sitio')
    check(despues != antes and sorted(despues) == sorted(antes), 'y los ejercicios cambian de orden dentro de ellos')
    for _ in range(2): page.locator('#sec-resumen th', has_text='Ejercicio').locator('button').click(); page.wait_for_timeout(100)
    check(filas() == antes, 'tras descendente, vuelve al orden de ejecución')

    print('\n[6] Biblioteca')
    ev("go('bloques')"); page.wait_for_selector('#listaBloques .cab-lista')
    check([''.join(t.split()) for t in page.locator('#listaBloques .cab-lista .orden-btn').all_inner_texts()] == ['Bloque↕', 'Nivel▲', 'Ejercicios↕'], 'Bloques: cabecera Bloque / Nivel / Ejercicios, por nivel por defecto')
    ev("go('ejercicios')"); page.wait_for_selector('#listaEjercicios .cab-lista')
    e0 = page.locator('#listaEjercicios .ej-nom').all_inner_texts()
    page.locator('#listaEjercicios .cab-lista').get_by_role('button', name='Ejercicio').click(); page.wait_for_timeout(100)
    check(page.locator('#listaEjercicios .ej-nom').all_inner_texts() == e0[::-1], 'Ejercicios: un clic en «Ejercicio» invierte el orden alfabético')

    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
