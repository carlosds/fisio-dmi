# Pestaña Sesiones de la ficha: botonera Próximas / Pasadas / Todas, búsqueda por fechas, mes y año, estado de cada
# sesión (ejercicios y puntuaciones), «Puntuar» en todas, color en los datos del paciente y borde en el calendario.
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_sesiones_lista.py PUERTO
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
    page.goto(BASE); page.wait_for_selector('#main')
    f = page.evaluate("""() => {
      const hoy = todayIso(), d = n => addDays(hoy, n);
      const cita = (id, n) => ({ id, patientId: 'p1', fecha: d(n), hora: '10:00', duracion: 45, nota: '', color: '' });
      db.pautas = db.pautas.filter(x => x.patientId !== 'p1');   // así solo tienen ejercicios las sesiones que se dicen aquí
      db.citas = [cita('cA', -40), cita('cB', -10), cita('cC', 3), cita('cD', 40)];
      db.pautas.push({ id: 'pz1', patientId: 'p1', exerciseId: 'e1', desde: d(-10), hasta: d(-10), asignacion: '', dias: '', bloqueId: '', orden: 9 });
      db.pautas.push({ id: 'pz2', patientId: 'p1', exerciseId: 'e1', desde: d(3), hasta: d(3), asignacion: '', dias: '', bloqueId: '', orden: 9 });
      db.puntuaciones[scoreKey('p1', d(-10), 'e1', 1, 'cB')] = 3; idxPunt = null;
      openPatient('p1'); irTab('citas');
      return { a: d(-40), b: d(-10), c: d(3), d: d(40) };
    }""")
    page.wait_for_selector('#sec-citas #verSesiones')
    sec = page.locator('#sec-citas')
    filas = lambda: sec.locator('#listaSesiones .cita-fila')
    fechas = lambda: page.evaluate("[...document.querySelectorAll('#listaSesiones .cita-fila')].map(e => e.querySelector('button[onclick^=puntuarCita]').getAttribute('onclick').split(\"'\")[3])")

    print('\n[1] Botonera Próximas / Pasadas / Todas')
    check(sec.locator('#verSesiones button.on').inner_text().startswith('Próximas') and fechas() == [f['c'], f['d']], f'por defecto, las próximas en orden {fechas()}')
    check(sec.locator('details:not(.filtro-fechas)').count() == 0, 'las pasadas ya no van en un plegable')
    sec.get_by_role('button', name='Pasadas (2)').click(); page.wait_for_timeout(100)
    check(fechas() == [f['b'], f['a']], f'Pasadas: de la más reciente a la más antigua {fechas()}')
    sec.get_by_role('button', name='Todas (4)').click(); page.wait_for_timeout(100)
    check(fechas() == [f['a'], f['b'], f['c'], f['d']], 'Todas: en orden de fecha')

    print('\n[2] Buscar por fechas, mes y año')
    check(not page.locator('#fsDesde').is_visible(), 'los filtros de fecha empiezan plegados')
    page.locator('#fsFechas > summary').click()
    page.fill('#fsDesde', f['b']); page.dispatch_event('#fsDesde', 'change'); page.fill('#fsHasta', f['c']); page.dispatch_event('#fsHasta', 'change'); page.wait_for_timeout(100)
    check(fechas() == [f['b'], f['c']], 'entre dos fechas')
    check(sec.locator('#fsQuitar').is_visible(), 'aparece «Quitar filtros»')
    sec.locator('#fsQuitar').click(); page.wait_for_timeout(100)
    check(len(fechas()) == 4 and page.evaluate('filtroSes().ver') == 'todas', '«Quitar filtros» vuelve a todas sin cambiar la botonera')
    page.select_option('#fsMes', f['d'][5:7]); page.wait_for_timeout(100)
    check(f['d'] in fechas() and all(x[5:7] == f['d'][5:7] for x in fechas()), 'por mes')
    page.select_option('#fsMes', ''); page.select_option('#fsAnio', f['a'][:4]); page.wait_for_timeout(100)
    check(fechas() and all(x.startswith(f['a'][:4]) for x in fechas()), 'por año')
    page.select_option('#fsAnio', ''); page.wait_for_timeout(100)
    page.select_option('#fsMes', '02' if f['a'][5:7] != '02' and f['b'][5:7] != '02' and f['c'][5:7] != '02' and f['d'][5:7] != '02' else '08'); page.wait_for_timeout(100)
    check('Ninguna sesión coincide' in sec.locator('#listaSesiones').inner_text(), 'sin coincidencias, avisa')
    page.select_option('#fsMes', ''); page.wait_for_timeout(100)

    print('\n[3] Estado de cada sesión y «Puntuar» en todas')
    estado = lambda fe: page.evaluate(f"[...document.querySelectorAll('#listaSesiones .cita-fila')].find(e => e.innerHTML.includes(\"'{fe}'\")).querySelector('.ses-estado').className")
    check('vacia' in estado(f['a']) and 'vacia' in estado(f['d']), 'las sesiones sin ejercicios lo dicen')
    check('hecha' in estado(f['b']), 'la sesión puntuada del todo sale como puntuada')
    check('prevista' in estado(f['c']), 'la sesión futura con ejercicios sale con sus ejercicios, sin puntuar todavía')
    check(filas().count() == sec.get_by_role('button', name='Puntuar').count() == 4, 'todas las sesiones tienen «Puntuar»')
    page.evaluate(f"puntuarCita('p1', '{f['d']}', 'cD')"); page.wait_for_selector('#modal #tabsDia')
    check(page.evaluate('ui.diaTab') == 'anadir' and page.evaluate('ui.selSes') == 'cD', 'sin ejercicios, «Puntuar» abre esa sesión en «Añadir ejercicios»')
    page.evaluate('closeModal()'); page.wait_for_timeout(100)
    page.evaluate(f"puntuarCita('p1', '{f['c']}', 'cC')"); page.wait_for_selector('#modal #tabsDia')
    check(page.evaluate('ui.diaTab') == 'puntuar', 'con ejercicios, se abre en «Puntuar ejercicios»')
    page.evaluate('closeModal()'); page.wait_for_timeout(100)

    print('\n[4] Color de sus sesiones en los datos del paciente')
    check(sec.locator('#pacColor').count() == 0, 'la pestaña Sesiones ya no tiene el selector de color')
    sec.get_by_role('button', name='Cambiarlo en sus datos').click(); page.wait_for_selector('#modal #pacColor')
    page.locator('#pacColor button[data-color="11"]').click()
    page.locator('#modal').get_by_role('button', name='Guardar').click(); page.wait_for_timeout(300)
    check(page.evaluate("getP('p1').colorCita") == '11', 'el color se guarda al guardar los datos del paciente')
    check(page.evaluate("db.citas.filter(c => c.fecha >= todayIso()).every(c => c.color === '11')"), 'al aceptar, se aplica también a sus próximas sesiones')
    check(page.evaluate("db.citas.filter(c => c.fecha < todayIso()).every(c => !c.color)"), 'las pasadas no cambian')
    page.evaluate("openCita(null, { patientId: 'p1' })"); page.wait_for_selector('#ctColor')
    check(page.evaluate("leerColor('ctColor')") == '11', 'una sesión nueva sale con su color y se puede cambiar en la ventana')
    page.evaluate('closeModal()'); page.wait_for_timeout(100)

    print('\n[5] Borde de los días con sesión en el calendario')
    page.evaluate(f"irTab('calendario'); ui.vista = 'semana'; ui.fecha = fromIso('{f['c']}'); render()"); page.wait_for_timeout(150)
    dia = page.locator('#calCuerpo .day.con-sesion')
    check(dia.count() == 1 and '--cc:#D50000' in (dia.first.get_attribute('style') or ''), 'el día con sesión lleva el borde del color de la sesión')
    check(f['c'][8:].lstrip('0') in dia.first.inner_text() and '10:00' in (dia.first.get_attribute('title') or ''), 'y dice la hora al pasar el ratón')
    check(page.evaluate("getComputedStyle(document.querySelector('#calCuerpo .day.con-sesion')).borderTopWidth") == '2px', 'el borde es más grueso que el de los demás días')
    page.evaluate("ui.vista = 'mes'; render()"); page.wait_for_timeout(150)
    check(page.locator('#calCuerpo .day.mes.con-sesion').count() >= 1, 'también en la vista de mes')

    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
