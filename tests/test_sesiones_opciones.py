# Sesiones (2): botonera del día, primera cita en un día con ejercicios sin sesión (sesión vacía, copiar o asignar),
# anular citas desde la lista del paciente (con aviso si tienen ejercicios o puntuaciones) y el panel «En qué sesión».
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_sesiones_opciones.py PUERTO
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
    H = page.evaluate('todayIso()'); d = lambda n: page.evaluate(f"addDays('{H}', {n})")
    m = page.locator('#modal')
    ev = page.evaluate
    def dar_cita(fecha, hora, resp):
        dialogos.clear(); respuestas[:] = [resp]
        ev(f"closeModal(); openCita(null, {{ patientId: 'p1', fecha: '{fecha}', hora: '{hora}' }})"); page.wait_for_selector('#ctHora')
        m.get_by_role('button', name='Dar cita').click(); page.wait_for_timeout(300)
        return ev(f"(db.citas.find(c => c.fecha === '{fecha}' && c.hora === '{hora}') || {{}}).id || null")
    nses = lambda f, ses: ev(f"exercisesSesion('p1', '{f}', '{ses}').length")
    sesiones = lambda f: ev(f"sesionesDia('p1', '{f}').map(x => x.id)")

    print('\n[1] Botonera del día')
    ev(f"openPatient('p1'); irTab('calendario'); openDay('{d(3)}')"); page.wait_for_selector('#modal .ej-dia')
    check(m.locator('.botonera-dia #quitarTodosDia').count() == 1, '«Quitar todos los ejercicios» está en la botonera de Puntuar / Añadir')
    m.get_by_role('tab', name='Añadir ejercicios').click(); page.wait_for_timeout(150)
    check(m.locator('.botonera-dia #quitarTodosDia').count() == 1, 'y sigue ahí en la pestaña Añadir')
    check(m.get_by_role('button', name='Añadir al día').count() == 1, 'sin citas el botón es «Añadir al día»')

    print('\n[2] Primera cita en un día con ejercicios: sesión vacía')
    ev(f"db.puntuaciones['p1|{H}|e1|1'] = 2; idxPunt = null; save()")
    c1 = dar_cita(H, '10:00', 'vacia')
    check(any('ya tiene 3 ejercicios sin sesión, con puntuaciones' in x for x in dialogos), f'pregunta qué hacer con los ejercicios sin sesión ({dialogos[-1][:80] if dialogos else ""})')
    check(c1 and nses(H, c1) == 0, 'la cita empieza sin ejercicios')
    check(sesiones(H) == [c1, ''] and nses(H, '') == 3, 'los ejercicios siguen en «Sin cita» ese día')
    check(f'p1|{H}|e1|1' in st()['puntuaciones'], 'con sus puntuaciones')
    check(ev("db.pautas.find(p => p.id === 'a1').sesion") == '!c:' + c1, 'la pauta toca en todas las sesiones menos en esa cita')
    check(nses(d(1), '') == 3, 'los demás días no cambian')
    ev(f"ui.patientId = 'p1'; openDay('{H}', 'anadir', '{c1}')"); page.wait_for_selector('#secAdd')
    check(m.get_by_role('button', name='Añadir a la sesión').count() == 1, 'en una cita, el botón es «Añadir a la sesión»')

    print('\n[3] Copiando ejercicios')
    c2 = dar_cita(d(1), '10:00', 'copiar')
    check(nses(d(1), c2) == 3 and nses(d(1), '') == 3 and sesiones(d(1)) == [c2, ''], 'la cita tiene una copia y «Sin cita» sigue con los suyos')
    copias = ev(f"db.pautas.filter(p => p.sesion === 'c:{c2}').map(p => [p.desde, p.hasta])")
    check(len(copias) == 3 and all(x == [d(1), d(1)] for x in copias), 'las copias son solo de ese día')
    check(nses(d(2), '') == 3 and sesiones(d(2)) == [''], 'el día siguiente no cambia')

    print('\n[4] Asignar los ejercicios existentes')
    ev(f"db.puntuaciones['p1|{d(2)}|e2|1'] = 3; idxPunt = null; save()")
    c3 = dar_cita(d(2), '10:00', 'asignar')
    check(sesiones(d(2)) == [c3] and nses(d(2), c3) == 3, 'solo queda la sesión de la cita, con los ejercicios')
    check(st()['puntuaciones'].get(f'p1|{d(2)}|e2|1|{c3}') == 3 and f'p1|{d(2)}|e2|1' not in st()['puntuaciones'], 'las puntuaciones pasan a la cita')

    print('\n[5] Cancelar no da la cita')
    check(dar_cita(d(3), '10:00', False) is None and page.locator('#ctHora').count() == 1, 'sin elegir, la cita no se da y la ventana sigue abierta')
    ev("closeModal()")

    print('\n[6] Serie nueva: una sola pregunta para todos sus días')
    dialogos.clear(); respuestas[:] = ['vacia']
    ev(f"openCita(null, {{ patientId: 'p1', fecha: '{d(7)}', hora: '17:00', repetir: true }})"); page.wait_for_selector('#ctHasta')
    page.fill('#ctHasta', d(21)); m.get_by_role('button', name='Dar cita').click(); page.wait_for_timeout(300)
    serie = ev(f"db.citas.filter(c => c.serieId).map(c => c.id)")
    check(len(serie) == 3 and sum('sin sesión' in x for x in dialogos) == 1 and any('3 días de la serie' in x for x in dialogos), 'pregunta una vez por los 3 días')
    check(all(nses(f, c) == 0 for f, c in zip([d(7), d(14), d(21)], serie)) and nses(d(7), '') == 3, 'sus citas empiezan vacías y los ejercicios siguen sin sesión')
    raiz = ev("raizSerie(db.seriesCitas[0])")
    check(ev("db.pautas.find(p => p.id === 'a3').sesion") == f'!c:{c1},c:{c2},s:{raiz}', 'la excepción se suma a las que ya había')

    print('\n[7] Anular desde la lista de citas del paciente')
    ev("closeModal(); openPatient('p1'); irTab('citas')"); page.wait_for_timeout(200)
    fila = lambda c: page.locator('.cita-fila').filter(has=page.locator(f'button[onclick="anularCita(\'{c}\')"]'))
    check(fila(c1).get_by_role('button', name='Anular').count() == 1, 'cada cita tiene su botón «Anular»')
    dialogos.clear(); respuestas[:] = [None]; fila(c1).get_by_role('button', name='Anular').click(); page.wait_for_timeout(300)
    check(not ev(f"!!getCita('{c1}')") and not any('ejercicio' in x for x in dialogos), 'una cita sin ejercicios se anula sin más avisos')
    dialogos.clear(); respuestas[:] = [None]; fila(c2).get_by_role('button', name='Anular').click(); page.wait_for_timeout(300)
    check(any('Esta cita tiene 3 ejercicios (sin puntuar)' in x for x in dialogos), 'con ejercicios sin puntuar, avisa')
    check(ev(f"db.pautas.filter(p => p.sesion === 'c:{c2}').length") == 0, 'las pautas que eran solo de esa cita se quitan')
    ev(f"db.pautas.push({{ id: 'solo', patientId: 'p1', exerciseId: 'e4', desde: '{d(2)}', hasta: '{d(2)}', asignacion: 'g9', bloqueId: '', orden: 9, sesion: 'c:{c3}' }}); db.puntuaciones['p1|{d(2)}|e4|1|{c3}'] = 1; idxPunt = null; render()")
    dialogos.clear(); respuestas[:] = [False]; fila(c3).get_by_role('button', name='Anular').click(); page.wait_for_timeout(300)
    check(any('⚠' in x and '2 ejercicios puntuados' in x and 'pasan a «Sin cita»' in x for x in dialogos), 'con puntuaciones, el aviso lo destaca')
    check(ev(f"!!getCita('{c3}')"), 'si se cancela, la cita sigue')
    respuestas[:] = [None]; fila(c3).get_by_role('button', name='Anular').click(); page.wait_for_timeout(300)
    p = st()['puntuaciones']
    check(p.get(f'p1|{d(2)}|e2|1') == 3 and p.get(f'p1|{d(2)}|e4|1') == 1, 'al anularla, las puntuaciones pasan a «Sin cita»')
    check(nses(d(2), '') == 4, 'y el ejercicio que era solo de la cita sigue ese día, sin sesión')
    check(page.locator('#deshacer.visible').count() == 1, 'se puede deshacer')

    print('\n[8] Asignar: panel «En qué sesión»')
    ev("openAssign(['p1'])"); page.wait_for_selector('#sesPanel')
    check(page.locator('.asig-cols #sesPanel').count() == 1, 'el panel está al lado de la lista de ejercicios')
    check(page.is_checked('#sesTodas') and page.locator('#sesLista .sesCheck:disabled').count() == page.locator('#sesLista .sesCheck').count() > 0, 'por defecto «Todas»')
    check(page.locator('#sesLista .sesCheck[value^="s:"]').count() == 1, 'la serie sale como una sola línea')
    m.get_by_role('button', name='Ninguna').click()
    check('quedan sin sesión' in page.inner_text('#sesResumen'), 'con «Ninguna» se explica que quedan sin sesión')
    m.locator('.exCheck[value="e4"]').check(); m.get_by_role('button', name='Asignar', exact=True).click(); page.wait_for_timeout(300)
    check(ev(f"db.pautas.filter(p => p.exerciseId === 'e4' && p.desde === '{H}').map(p => p.sesion)") == ['-'], 'ninguna = pauta sin sesión')
    nueva = dar_cita(d(4), '12:00', 'vacia'); ev("closeModal()")
    ev("openAssign(['p1'])"); page.wait_for_selector('#sesPanel')
    page.uncheck('#sesTodas')
    page.locator(f'#sesLista .sesCheck[value="c:{nueva}"]').check(); page.locator('#sesLista .sesCheck[value^="s:"]').check()
    check(page.inner_text('#sesResumen').startswith('Solo en las 2 sesiones'), 'se pueden marcar varias')
    m.locator('.exCheck[value="e4"]').check(); m.get_by_role('button', name='Asignar', exact=True).click(); page.wait_for_timeout(300)
    check(sorted(ev(f"db.pautas.filter(p => p.exerciseId === 'e4' && p.desde === '{H}' && p.sesion !== '-').map(p => p.sesion)")) == sorted([f'c:{nueva}', f's:{raiz}']), 'una pauta por cada sesión marcada')
    check(nses(d(4), nueva) == 1 and nses(d(7), serie[0]) == 1, 'el ejercicio sale en esas citas')
    ev("openAssign(['p1'])"); page.wait_for_selector('#sesPanel')
    page.select_option('#aTipo', 'dia'); page.fill('#aDesde', d(4)); page.dispatch_event('#aDesde', 'change')
    check(page.locator('#sesLista .sesCheck').count() == 1, 'la lista de citas sigue las fechas elegidas')
    ev("closeModal()")

    print('\n[9] Editar pauta: el mismo panel')
    k = ev(f"claveAsig(db.pautas.find(p => p.exerciseId === 'e4' && p.sesion === '-'))")
    ev(f"openEditarPauta('{k}')"); page.wait_for_selector('#sesPanel')
    check(not page.is_checked('#sesTodas') and page.locator('#sesLista .sesCheck:checked').count() == 0, 'una pauta sin sesión se abre con ninguna marcada')
    page.check('#sesTodas'); m.get_by_role('button', name='Guardar').click(); page.wait_for_timeout(300)
    check(ev(f"db.pautas.filter(p => claveAsig(p) === '{k}').every(p => !p.sesion)"), 'pasa a tocar en todas')
    s_ = st()
    check(all(x.get('sesion', '') == '' or x['sesion'] == '-' or x['sesion'][:2] in ('c:', 's:') or x['sesion'][0] == '!' for x in s_['pautas']), 'el servidor recibe valores de sesión válidos')
    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
