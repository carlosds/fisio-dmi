# Barra del calendario fija al desplazarse, sesiones enlazadas en la lista de pacientes, filtros de pautas
# (vigentes / terminadas / todas y fechas), filtro por fecha de los informes y series en su pestaña de Sesiones.
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_ficha_filtros.py PUERTO
import sys
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; BASE = f'http://127.0.0.1:{PORT}/'
fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)

with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_page(viewport={'width': 820, 'height': 700})
    errs = []; page.on('pageerror', lambda e: errs.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE); page.wait_for_selector('#listaPacientes')
    ev = page.evaluate
    f = ev("""() => { const hoy = todayIso(), d = n => addDays(hoy, n);
      const cita = (id, n, h) => ({ id, patientId: 'p1', fecha: d(n), hora: h, duracion: 45, nota: '', color: '', serieId: '', fechaSerie: '' });
      db.citas.push(cita('c1', -2, '10:00'), cita('c2', 3, '12:30'));
      db.puntuaciones[scoreKey('p1', d(-2), 'e1', 1, 'c1')] = 2; idxPunt = null;
      // una pauta terminada (enero) y las de la semilla (continuas)
      db.pautas.push({ id: 'pt1', patientId: 'p1', exerciseId: 'e4', desde: '2026-01-05', hasta: '2026-01-20', asignacion: 'gt', dias: '', bloqueId: '', orden: 9 });
      db.informes.push({ id: 'i1', patientId: 'p1', tipo: 'informe', nombre: 'a.pdf', ruta: '/x/a.pdf', fecha: '2026-03-15T10:00:00', desde: '2026-03-01', hasta: '2026-03-15', descripcion: 'Marzo' },
                       { id: 'i2', patientId: 'p1', tipo: 'informe', nombre: 'b.pdf', ruta: '/x/b.pdf', fecha: '2026-09-15T10:00:00', desde: '2026-09-01', hasta: '2026-09-15', descripcion: 'Septiembre' });
      db.seriesCitas.push({ id: 's1', patientId: 'p1', dias: '3', hora: '14:00', duracion: 45, desde: hoy, hasta: d(60), nota: '', excluidas: [], creada: hoy, color: '' });
      go('pacientes'); return { hoy, ant: d(-2), sig: d(3) }; }""")
    page.wait_for_timeout(200)

    print('\n[1] Lista de pacientes')
    fila = page.locator('#listaPacientes .fila-pac').first
    check(fila.locator('button.small').all_inner_texts()[:2] == ['Puntuar hoy', 'Nueva sesión'], f'«Puntuar hoy» va a la izquierda de «Nueva sesión» {fila.locator("button.small").all_inner_texts()}')
    fila.get_by_role('button', name='Próxima sesión').click(); page.wait_for_selector('#ctHora')
    check(page.evaluate("citaEd.id") == 'c2', 'pulsar «Próxima sesión» abre esa sesión')
    ev('closeModal()')
    fila.get_by_role('button', name='Última sesión').click(); page.wait_for_selector('#modal #tabsDia')
    check(ev('[ui.selDay, ui.selSes]') == [f['ant'], 'c1'], 'pulsar «Última sesión» abre la puntuación de esa sesión')
    check(ev('ui.view') == 'pacientes', 'sin salir de la lista')
    ev('closeModal()')

    print('\n[2] Barra del calendario fija')
    ev("openPatient('p1'); irTab('calendario'); ui.vista = 'mes'; render()"); page.wait_for_selector('.cal-fija')
    page.mouse.wheel(0, 900); page.wait_for_timeout(500)
    pos = ev("(() => { const f = document.querySelector('.cal-fija').getBoundingClientRect(), h = document.querySelector('.sticky-head').getBoundingClientRect(); return [f.top, h.bottom, scrollY]; })()")
    check(pos[2] > 100 and abs(pos[0] - pos[1]) < 2, f'al bajar, la barra se queda justo debajo de la cabecera del paciente {pos}')
    check(page.locator('.cal-fija').get_by_role('button', name='Siguiente').is_visible() and page.locator('.cal-fija #qCal').is_visible(), 'con la navegación y el buscador a la vista')
    ev('window.scrollTo(0, 0)')

    print('\n[3] Pautas: vigentes, terminadas, todas y fechas')
    ev("irTab('pautas')"); page.wait_for_selector('#verPautas')
    n = lambda: page.locator('#pautasLista > .item').count()
    check(page.locator('#verPautas button.on').inner_text().startswith('Vigentes') and n() == 2, f'por defecto, las vigentes ({n()})')
    check(page.locator('#sec-pautas details:not(.filtro-fechas)').count() == 0, 'las terminadas ya no van en un plegable')
    page.locator('#verPautas').get_by_role('button', name='Terminadas (1)').click(); page.wait_for_timeout(100)
    check(n() == 1 and 'Respiración' in page.locator('#pautasLista').inner_text(), 'Terminadas: solo la de enero')
    page.locator('#verPautas').get_by_role('button', name='Todas (3)').click(); page.wait_for_timeout(100)
    check(n() == 3 and 'Terminadas (1)' in page.locator('#pautasLista').inner_text(), 'Todas: las vigentes y, debajo, las terminadas')
    page.locator('#fpaFechas > summary').click()
    page.select_option('#fpaMes', '01'); page.select_option('#fpaAnio', '2026'); page.wait_for_timeout(100)
    check(n() == 3, 'en enero de 2026 estaban las tres (las continuas también)')
    page.fill('#fpaDesde', '2026-02-01'); page.dispatch_event('#fpaDesde', 'change'); page.select_option('#fpaMes', ''); page.select_option('#fpaAnio', ''); page.wait_for_timeout(100)
    check(n() == 2 and 'Respiración' not in page.locator('#pautasLista').inner_text(), 'desde febrero ya no sale la que terminó en enero')
    page.fill('#qPautas', 'core'); page.wait_for_timeout(100)
    check(n() == 1, 'y se combina con el buscador de bloque o ejercicio')
    page.fill('#qPautas', ''); page.locator('#fpaQuitar').click(); page.wait_for_timeout(100)
    check(n() == 3 and ev("filtroPautas().ver") == 'todas', '«Quitar filtros» deja la botonera como estaba')

    print('\n[4] Informes: buscar por fecha')
    ev("irTab('informes')"); page.wait_for_selector('#finFechas'); page.locator('#finFechas > summary').click()
    tit = lambda: [t.strip() for t in page.locator('#listaInformes .infItem strong').all_inner_texts()]
    page.select_option('#finMes', '03'); page.wait_for_timeout(100)
    check(tit() == ['Marzo'], 'por mes de generación')
    page.select_option('#finMes', ''); page.fill('#finDesde', '2026-06-01'); page.dispatch_event('#finDesde', 'change'); page.wait_for_timeout(100)
    check(tit() == ['Septiembre'], 'desde una fecha')
    page.fill('#finHasta', '2026-06-30'); page.dispatch_event('#finHasta', 'change'); page.wait_for_timeout(100)
    check('Ningún PDF coincide' in page.locator('#listaInformes').inner_text(), 'sin coincidencias, avisa')
    page.locator('#finQuitar').click(); page.wait_for_timeout(100)
    check(len(tit()) == 2, '«Quitar filtros» las vuelve a mostrar')

    print('\n[5] Sesiones: las series en su pestaña')
    ev("irTab('citas')"); page.wait_for_selector('#verSesiones')
    sec = page.locator('#sec-citas')
    check(sec.get_by_role('button', name='Terminar…').count() == 0 and 'Se repiten cada semana' not in sec.inner_text(), 'las series no ocupan sitio encima de la lista')
    sec.locator('#verSesiones').get_by_role('button', name='↻ Se repiten (1)').click(); page.wait_for_timeout(100)
    check(sec.locator('.serie-fila').count() == 1 and 'a las 14:00' in sec.locator('.serie-fila').inner_text(), 'la pestaña «Se repiten» las muestra, una por línea')
    check(page.locator('#fsDesde').count() == 0, 'sin los filtros de fechas (no aplican a las series)')
    ev("db.seriesCitas = []; render()"); page.wait_for_timeout(100)
    check(ev("filtroSes().ver") == 'proximas' and 'Se repiten' not in page.locator('#verSesiones').inner_text(), 'sin series, la pestaña desaparece y se vuelve a Próximas')

    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
