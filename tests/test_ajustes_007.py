# Cierre de la 0.0.7: observaciones de bloque y de ejercicio (visibles según Ajustes), valores por defecto de los
# filtros y qué incluye por defecto el informe de pautas (con la gráfica como opción nueva).
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_ajustes_007.py PUERTO
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
    hoy = ev('todayIso()')

    print('\n[1] Observaciones: por defecto, solo la de la sesión')
    ev("openPatient('p1'); openDay(todayIso(), 'puntuar')"); page.wait_for_selector('#modal .ej-dia')
    m = page.locator('#modal')
    check(m.locator('#obsSesion').count() == 1 and m.locator('.obs-btn').count() == 0, 'el cuadro de la sesión, sin ✎ en bloques ni ejercicios')
    ev('closeModal()')

    print('\n[2] Ajustes › Personalizar: activar bloque y ejercicio, quitar la de sesión')
    ev("ui.ajTab = 'personalizar'; go('ajustes')"); page.wait_for_selector('#obsNivel-bloque')
    check(page.is_checked('#obsNivel-sesion') and not page.is_checked('#obsNivel-bloque') and not page.is_checked('#obsNivel-ejercicio'), 'por defecto: sesión sí, bloque y ejercicio no')
    page.check('#obsNivel-bloque'); page.check('#obsNivel-ejercicio'); page.uncheck('#obsNivel-sesion'); page.wait_for_timeout(300)
    a = st()['ajustes']
    check(a.get('obs.bloque') == '1' and a.get('obs.ejercicio') == '1' and a.get('obs.sesion') == '0', 'se guarda en los ajustes')

    ev("openPatient('p1'); openDay(todayIso(), 'puntuar')"); page.wait_for_selector('#modal .ej-dia')
    check(m.locator('#obsSesion').count() == 0, 'sin el cuadro de la sesión')
    check(m.locator('.grp-titulo .obs-btn').count() == 1 and m.locator('.ej-dia .obs-btn').count() == m.locator('.ej-dia').count(), '✎ en el bloque y en cada ejercicio')
    check(m.locator('textarea.obs-mini').count() == 0, 'los cuadros empiezan cerrados')
    m.get_by_role('button', name='Observaciones de Core básico').click(); page.wait_for_timeout(150)
    ta = m.locator('textarea.obs-mini')
    check(ta.count() == 1 and ev('document.activeElement.classList.contains("obs-mini")'), 'el ✎ del bloque abre su cuadro con el cursor dentro')
    page.keyboard.type('Bloque cansado'); page.wait_for_timeout(1000)
    obs = st()['observaciones']
    check(any(o['bloqueId'] == 'b1' and not o['exerciseId'] and o['texto'] == 'Bloque cansado' and o['fecha'] == hoy for o in obs), 'se guarda como observación del bloque')
    nombre = m.locator('.ej-dia .ej-nom-dia').last.inner_text()
    eid = m.locator('.ej-dia').last.get_attribute('data-eid')
    m.locator('.ej-dia').last.locator('.obs-btn').click(); page.wait_for_timeout(150)
    page.keyboard.type('Le molesta la rodilla'); page.wait_for_timeout(1000)
    obs = st()['observaciones']
    check(any(o['exerciseId'] == eid and not o['bloqueId'] and o['texto'] == 'Le molesta la rodilla' for o in obs), f'y la del ejercicio ({nombre}) como observación del ejercicio')
    page.keyboard.press('2'); page.wait_for_timeout(200)
    check(page.input_value(f'#modal .ej-dia[data-eid="{eid}"] textarea').endswith('2') and ev(f"db.puntuaciones[scoreKey('p1', todayIso(), '{eid}', 1)]") is None, 'un número escrito en el cuadro no puntúa')
    ev('closeModal()'); ev("openDay(todayIso(), 'puntuar')"); page.wait_for_selector('#modal .ej-dia')
    check(m.locator('textarea.obs-mini').count() == 2 and m.locator('.obs-btn.on').count() == 2, 'al volver, los cuadros con texto se ven y su ✎ está marcado')
    ev('closeModal()')
    ev("irTab('calendario'); ui.vista = 'dia'; ui.fecha = new Date(); render()"); page.wait_for_timeout(200)
    check(page.locator('#sec-calendario textarea.obs-mini').count() == 2, 'también en la vista Día del calendario')

    print('\n[3] Informe: las observaciones de bloque y ejercicio, y las opciones por defecto')
    t = ev("obsPeriodoPdf('p1', todayIso(), todayIso()).map(x => x.texto).join('|')")
    check('Core básico: Bloque cansado' in t and 'Le molesta la rodilla' in t, f'el informe las incluye con el nombre del bloque o ejercicio ({t})')
    ev("ui.ajTab = 'personalizar'; go('ajustes')"); page.wait_for_selector('#infDef-grafica')
    check(all(page.is_checked(f'#infDef-{k}') for k in ('grafica', 'detalle', 'obs')), 'por defecto, todo marcado')
    page.uncheck('#infDef-grafica'); page.uncheck('#infDef-detalle'); page.wait_for_timeout(300)
    check(st()['ajustes'].get('informe.grafica') == '0' and st()['ajustes'].get('informe.detalle') == '0', 'se guarda')
    ev("openExportar(['p1'])"); page.wait_for_selector('#expGrafica')
    check(not page.is_checked('#expGrafica') and not page.is_checked('#expDetalle') and page.is_checked('#expObs'), 'la ventana del informe sale con esas casillas')
    page.check('#expGrafica')
    check(ev('ui.exp.grafica') is True, 'y en cada informe se puede cambiar')
    ev('closeModal()')
    ev("db.puntuaciones[scoreKey('p1', todayIso(), 'e1', 1)] = 2; db.puntuaciones[scoreKey('p1', addDays(todayIso(), -1), 'e1', 1)] = 3; idxPunt = null")
    con, sin = ev("""async () => { const p = getP('p1'), d = addDays(todayIso(), -6), h = todayIso();
      return [(await pdfPaciente(p, d, h, { grafica: true })).length, (await pdfPaciente(p, d, h, { grafica: false })).length]; }""")
    check(sin < con, f'sin la gráfica, el PDF es más corto ({sin} < {con})')

    print('\n[4] Filtros por defecto')
    ev("ui.ajTab = 'personalizar'; go('ajustes')"); page.wait_for_selector('#fDef-pautas')
    check(page.input_value('#fDef-pacientes') == 'activos' and page.input_value('#fDef-pautas') == 'vigentes' and page.input_value('#fDef-sesiones') == 'proximas' and page.input_value('#fDef-bloques') == '', 'los de siempre')
    page.select_option('#fDef-pautas', 'todas'); page.select_option('#fDef-sesiones', 'pasadas'); page.select_option('#fDef-pacientes', 'todos'); page.select_option('#fDef-bloques', 'A')
    page.locator('.filtros-def').get_by_role('button', name='Hoy').click(); page.wait_for_timeout(300)
    a = st()['ajustes']
    check([a.get('filtro.' + k) for k in ('pautas', 'sesiones', 'pacientes', 'bloques', 'pacSesiones')] == ['todas', 'pasadas', 'todos', 'A', 'hoy'], 'se guardan')
    check(page.locator('.filtros-def button[aria-pressed=true]').inner_text() == 'Hoy', 'el botón queda marcado')
    ev("go('pacientes')"); page.wait_for_timeout(200)
    check(page.input_value('#filtroPac') == 'todos' and page.locator('#filtroSesiones button.on').inner_text() == 'Hoy', 'pacientes: «Todos» y «Con sesiones: Hoy»')
    ev("openPatient('p1'); irTab('pautas')"); page.wait_for_selector('#verPautas')
    check(page.locator('#verPautas button.on').inner_text().startswith('Todas'), 'pautas: «Todas»')
    ev("irTab('citas')"); page.wait_for_selector('#verSesiones')
    check(page.locator('#verSesiones button.on').inner_text().startswith('Pasadas'), 'sesiones: «Pasadas»')
    page.locator('#verSesiones').get_by_role('button', name='Próximas', exact=False).click()
    ev("go('pacientes'); openPatient('p1'); irTab('citas')"); page.wait_for_selector('#verSesiones')
    check(page.locator('#verSesiones button.on').inner_text().startswith('Pasadas'), 'al abrir otra vez la ficha, vuelve al de por defecto')
    ev("go('bloques')"); page.wait_for_selector('#nivelBl')
    check(page.input_value('#nivelBl') == 'A', 'bloques: «Nivel A»')

    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
