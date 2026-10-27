# Sesiones: cada cita de un día es una sesión con sus ejercicios y puntuaciones; sin cita, la sesión «Sin sesión».
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_sesiones.py PUERTO
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
    respuestas = []; dialogos = []
    def on_dialog(d):
        dialogos.append(d.message); r = respuestas.pop(0) if respuestas else None
        if r is False: d.dismiss()
        elif r is None: d.accept()
        else: d.accept(r)
    page.on('dialog', on_dialog)
    page.goto(BASE + '/'); page.wait_for_selector('#listaPacientes'); page.evaluate('descartarNovedades()')
    page.evaluate("db.patients.push({ id: 'p2', nombre: 'Luis', apellidos: 'Otero', telefono: '', email: '', fechaAlta: '2026-01-01', foto: '' }); render()")
    hoy = page.evaluate('todayIso()')
    m = page.locator('#modal')
    claves = lambda: sorted(k for k in st()['puntuaciones'] if k.startswith(f'p1|{hoy}|'))
    def puntuar(eid, n, rep=1):
        m.locator(f'.rep-fila[data-eid="{eid}"][data-rep="{rep}"]').get_by_role('button', name=f'Puntuación {n}').click(); page.wait_for_timeout(250)

    print('\n[1] Día sin cita: se puntúa como siempre')
    page.evaluate("openPatient('p1'); irTab('calendario'); openDay(todayIso())"); page.wait_for_selector('#modal .ej-dia')
    check(m.locator('.sesiones-dia').count() == 0 and 'Sin sesión este día' in m.inner_text(), 'sin citas no hay botones de sesión, solo «Sin sesión este día»')
    puntuar('e1', 2)
    check(claves() == [f'p1|{hoy}|e1|1'], f'la puntuación se guarda sin sesión ({claves()})')

    print('\n[2] Apuntar la cita después de puntuar')
    m.get_by_role('button', name='+ Sesión').click(); page.wait_for_selector('#ctHora')
    check(page.input_value('#ctPac') == 'p1' and page.input_value('#ctFecha') == hoy, 'la cita se propone para ese paciente y ese día')
    page.fill('#ctHora', '10:00'); respuestas[:] = ['asignar']
    m.get_by_role('button', name='Programar sesión').click(); page.wait_for_selector('#modal .sesiones-dia')
    check(any('ejercicios sin sesión, con puntuaciones' in d for d in dialogos), 'pregunta qué hacer con lo que ya había sin cita')
    c1 = page.evaluate("db.citas[0].id")
    check(claves() == [f'p1|{hoy}|e1|1|{c1}'], f'al asignar los ejercicios existentes, la puntuación pasa a la cita ({claves()})')
    check(m.locator('.ses-btn').count() == 1 and 'Sesión 10:00–10:45' in m.locator('.ses-btn').inner_text() and '1 de 3 puntuados' in m.locator('.ses-btn').inner_text(), 'vuelve a la ventana del día, con la sesión de la cita')

    print('\n[3] Segunda visita el mismo día: otra sesión con sus propias puntuaciones')
    dialogos.clear()
    m.get_by_role('button', name='+ Sesión').click(); page.wait_for_selector('#ctHora')
    page.fill('#ctHora', '18:00'); m.get_by_role('button', name='Programar sesión').click(); page.wait_for_selector('#modal .sesiones-dia')
    check(not any('sin sesión' in d for d in dialogos), 'en la segunda cita del día ya no pregunta')
    c2 = page.evaluate("db.citas.find(c => c.hora === '18:00').id")
    check(m.locator('.ses-btn').count() == 2 and 'on' in m.locator('.ses-btn').nth(1).get_attribute('class'), 'dos sesiones; se abre la nueva')
    check(m.locator('.rep-fila .scores button.on').count() == 0, 'la sesión nueva empieza sin puntuar (aunque tenga los mismos ejercicios)')
    puntuar('e1', 3)
    check(claves() == sorted([f'p1|{hoy}|e1|1|{c1}', f'p1|{hoy}|e1|1|{c2}']), 'el mismo ejercicio queda puntuado en cada sesión')
    check(page.evaluate(f"resumenDia('p1', '{hoy}', 'e1').avg") == 2.5, 'la media del día junta las dos sesiones (2,5)')
    page.keyboard.press('ArrowDown'); page.keyboard.press('1'); page.wait_for_timeout(250)
    check(st()['puntuaciones'].get(f'p1|{hoy}|e2|1|{c2}') == 1, 'el teclado puntúa en la sesión abierta')
    m.locator('.ses-btn').first.click(); page.wait_for_timeout(150)
    check(m.locator('.rep-fila[data-eid="e1"] .scores button.on').inner_text() == '2', 'al cambiar de sesión se ven sus puntuaciones')
    page.evaluate('closeModal()'); page.wait_for_timeout(150)
    page.evaluate("go('pacientes')"); page.wait_for_timeout(150)
    check('Hoy: 3 de 6 puntuados' in page.locator('#listaPacientes .fila-pac', has_text='López').inner_text(), 'la lista de pacientes cuenta cada sesión (3 de 6)')

    print('\n[4] Pautas por sesión')
    page.evaluate("openPatient('p1'); irTab('pautas')"); page.wait_for_timeout(150)
    page.evaluate("openEditarPauta('g2')"); page.wait_for_selector('#sesPanel')
    ops = page.locator('#sesLista .ses-item').all_inner_texts()
    check(page.is_checked('#sesTodas') and any('18:00' in o for o in ops), f'«En qué sesión» ofrece todas o una cita ({ops})')
    page.uncheck('#sesTodas'); page.locator(f'#sesLista .sesCheck[value="c:{c2}"]').check(); m.get_by_role('button', name='Guardar').click(); page.wait_for_timeout(300)
    check(next(x for x in st()['pautas'] if x['id'] == 'a3').get('sesion') == f'c:{c2}', 'la pauta queda ligada a esa cita')
    n1 = page.evaluate(f"exercisesSesion('p1', '{hoy}', '{c1}').length"); n2 = page.evaluate(f"exercisesSesion('p1', '{hoy}', '{c2}').length")
    check((n1, n2) == (2, 3), f'la cita de las 10:00 ya no tiene ese ejercicio y la de las 18:00 sí ({n1}, {n2})')
    check('solo en la sesión del' in page.locator('#pautasLista').inner_text(), 'la lista de pautas dice en qué cita toca')
    page.evaluate("openAssign(['p1'])"); page.wait_for_selector('#modal .exItem')
    check(page.locator('#sesPanel').count() == 1, 'al asignar a un paciente con citas se puede elegir la sesión')
    page.evaluate("closeModal(); openAssign(['p2'])"); page.wait_for_selector('#modal .exItem')
    check(page.locator('#sesPanel').count() == 0, 'a un paciente sin citas no se le pregunta')
    page.evaluate("closeModal(); openAssign(['p1', 'p2'])"); page.wait_for_selector('#modal .exItem')
    check(page.locator('#sesPanel').count() == 0, 'ni al asignar a varios pacientes a la vez')
    page.evaluate('closeModal()')

    print('\n[5] Quitar y añadir en una sola sesión')
    page.evaluate(f"irTab('calendario'); openDay('{hoy}', 'puntuar', '{c1}')"); page.wait_for_selector('#modal .ej-dia')
    m.locator('.ej-dia[data-eid="e2"]').get_by_role('button', name='Quitar de esta sesión').click(); page.wait_for_timeout(300)
    f = lambda ses, d=hoy: page.evaluate(f"exercisesSesion('p1', '{d}', '{ses}').map(i => i.exercise.id).sort().join()")
    check(f(c1) == 'e1' and f(c2) == 'e1,e2,e3', f'«Quitar» lo quita solo de esa sesión ({f(c1)} | {f(c2)})')
    manana = page.evaluate("addDays(todayIso(), 1)")
    check(f('', manana) == 'e1,e2', f'los demás días no cambian ({f("", manana)})')
    m.locator('.ses-btn').nth(1).click(); page.wait_for_timeout(100)
    m.get_by_role('tab', name='Añadir ejercicios').click(); page.wait_for_selector('#secAdd')
    check('Se añaden solo a esta sesión' in m.inner_text(), 'al añadir, avisa de que es solo para esta sesión')
    m.locator('.exItem', has_text='Respiración diafragmática').locator('input').check()
    m.get_by_role('button', name='Añadir a la sesión').click(); page.wait_for_timeout(300)
    check(f(c2) == 'e1,e2,e3,e4' and f(c1) == 'e1', 'se añade solo a la sesión abierta')

    print('\n[6] Anular una cita con puntuaciones: no se pierden')
    respuestas[:] = [None]
    page.evaluate(f"closeModal(); anularCita('{c1}')"); page.wait_for_timeout(400)
    check(st()['puntuaciones'].get(f'p1|{hoy}|e1|1') == 2 and not any(k.endswith('|' + c1) for k in st()['puntuaciones']), 'sus puntuaciones pasan a «Sin sesión» en ese día')
    ses = page.evaluate(f"sesionesDia('p1', '{hoy}').map(x => x.cita ? x.cita.hora : 'sin')")
    check(ses == ['18:00', 'sin'], f'el día queda con la cita de las 18:00 y la sesión sin cita ({ses})')
    check(page.evaluate(f"resumenDia('p1', '{hoy}', 'e1').avg") == 2.5, 'y la media del día no cambia')

    print('\n[7] Una pauta ligada a una serie sigue valiendo si la serie se parte')
    L = page.evaluate("addDays(iso(inicioSemana(new Date())), 7)")
    page.evaluate(f"""const s = {{ id: 'sr1', patientId: 'p1', dias: '24', hora: '09:00', duracion: 45, desde: '{L}', hasta: addDays('{L}', 27), nota: '', excluidas: [], color: '' }};
      db.seriesCitas.push(s); generarSerie(db, s);
      db.pautas.push({{ id: 'ps1', patientId: 'p1', exerciseId: 'e4', desde: '{L}', hasta: null, asignacion: 'g9', bloqueId: '', orden: 9, sesion: 's:sr1' }}); render();""")
    martes = page.evaluate(f"addDays('{L}', 1)"); martes3 = page.evaluate(f"addDays('{L}', 15)")
    cm = page.evaluate(f"db.citas.find(c => c.serieId === 'sr1' && c.fecha === '{martes}').id")
    check('e4' in f(cm, martes) and 'e4' not in page.evaluate(f"exercisesSesion('p1', addDays('{L}', 2), '').map(i => i.exercise.id).join()"), 'el ejercicio sale en las citas de la serie y no en los días sin cita')
    page.evaluate(f"cambiarSerieDesde(getSerie('sr1'), addDays('{L}', 14), {{ hora: '11:00' }}); render()")
    cm3 = page.evaluate(f"db.citas.find(c => c.fecha === '{martes3}' && c.patientId === 'p1').id")
    check(page.evaluate("db.seriesCitas.filter(x => x.patientId === 'p1').length") == 2 and 'e4' in f(cm3, martes3), 'tras partir la serie (otra hora desde la tercera semana), sigue saliendo en sus citas')

    print('\n[8] Informe y resumen')
    d = page.evaluate(f"datosPdf(getP('p1'), '{hoy}', '{hoy}')")
    titulos = [x['titulo'] for x in d['dias'][0]['sesiones']]
    check(titulos == ['Sesión 18:00–18:45', 'Sin sesión'], f'el detalle del informe separa las sesiones ({titulos})')
    check(abs(d['puntos'][0]['media'] - page.evaluate(f"(resumenDia('p1','{hoy}','e1').avg + resumenDia('p1','{hoy}','e2').avg) / 2")) < 1e-9, 'la gráfica usa la media del día')
    r = page.evaluate(f"datosRango(getP('p1'), '{hoy}', '{hoy}').stats.e1")
    check(r['exp'] == 1 and sorted(r['scores']) == [2, 3], 'en el resumen el ejercicio cuenta una vez ese día, con las puntuaciones de las dos sesiones')

    print('\n[9] Al pasar a esta versión, lo puntuado un día con una sola cita pasa a esa cita')
    ayer = page.evaluate("addDays(todayIso(), -3)")
    page.evaluate(f"""db.citas.push({{ id: 'cv', patientId: 'p1', fecha: '{ayer}', hora: '12:00', duracion: 45, nota: '', serieId: '', fechaSerie: '', color: '' }});
      db.puntuaciones['p1|{ayer}|e1|1'] = 3; delete db.ajustes.sesionesMigradas; idxPunt = null; save();""")
    page.wait_for_timeout(400)
    check(f'p1|{ayer}|e1|1' in st()['puntuaciones'], '(puntuación antigua sin sesión)')
    page.reload(); page.wait_for_selector('#main'); page.wait_for_timeout(600)
    s = st()
    check(s['puntuaciones'].get(f'p1|{ayer}|e1|1|cv') == 3 and f'p1|{ayer}|e1|1' not in s['puntuaciones'], 'al abrir, pasa a la cita de ese día')
    check(s['puntuaciones'].get(f'p1|{hoy}|e1|1') == 2, 'un día con varias sesiones no se toca')
    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
