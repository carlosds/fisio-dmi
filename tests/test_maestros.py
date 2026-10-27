# Exportar e importar la biblioteca (ejercicios y bloques).
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_maestros.py PUERTO
import json, os, sys, tempfile, urllib.request
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; BASE = f'http://127.0.0.1:{PORT}'
RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
get = lambda p: json.loads(urllib.request.urlopen(BASE + p).read())
TMP = tempfile.mkdtemp()
def archivo(nombre, datos):
    p = os.path.join(TMP, nombre); open(p, 'w', encoding='utf-8').write(datos if isinstance(datos, str) else json.dumps(datos)); return p

with sync_playwright() as pw:
    b = pw.chromium.launch(); page = b.new_page(viewport={'width': 1300, 'height': 900})
    errs = []; page.on('pageerror', lambda e: errs.append(str(e)))
    dialogos = []; page.on('dialog', lambda d: (dialogos.append(d.message), d.accept()))
    page.goto(BASE + '/'); page.wait_for_selector('#listaPacientes'); page.evaluate('descartarNovedades()')
    m = page.locator('#modal')

    print('\n[1] Exportar solo los bloques (con sus ejercicios)')
    page.evaluate("go('bloques')"); page.wait_for_timeout(150)
    page.get_by_role('button', name='Exportar…').click(); page.wait_for_selector('#expBl')
    check(page.is_checked('#expBl') and page.is_checked('#expEj'), 'por defecto se exportan bloques y ejercicios')
    check('1 bloque y 4 ejercicios' in m.inner_text(), 'el resumen dice cuánto se exporta')
    page.uncheck('#expEj'); page.wait_for_timeout(50)
    check('1 bloque y 2 ejercicios' in m.inner_text() and 'Solo los ejercicios que forman parte' in m.inner_text(), 'sin «Ejercicios», solo van los ejercicios de los bloques')
    page.uncheck('#expBl'); page.wait_for_timeout(50)
    check(page.locator('#btnExpMaestros').is_disabled(), 'sin marcar nada no se puede exportar')
    page.check('#expBl'); page.locator('#btnExpMaestros').click(); page.wait_for_timeout(500)
    ruta = get('/__exports')[-1]
    check(os.path.basename(ruta).startswith('Bloques_') and ruta.endswith('.json'), f'nombre propuesto «{os.path.basename(ruta)}»')
    j = json.load(open(ruta, encoding='utf-8'))
    check(j['formato'] == 'fisioterapia-maestros' and j['version'] == 1, 'formato propio con versión')
    check([x['nombre'] for x in j['bloques']] == ['Core básico'] and j['bloques'][0]['nivel'] == 'A' and j['bloques'][0]['ejercicios'] == ['e1', 'e2'], 'el bloque va con su nivel y sus ejercicios en orden')
    check(sorted(x['id'] for x in j['ejercicios']) == ['e1', 'e2'], 'solo los dos ejercicios del bloque')
    check('patients' not in j and 'pautas' not in j and 'Ana' not in json.dumps(j), 'no lleva ningún dato de pacientes')
    check(any('Se han exportado 1 bloque y 2 ejercicios' in d for d in dialogos), 'avisa de dónde se ha guardado')
    check(page.evaluate("db.ajustes.maestrosCarpeta") == os.path.dirname(ruta), 'recuerda la carpeta para la próxima vez')

    print('\n[2] Exportar todo desde Ejercicios')
    page.evaluate("go('ejercicios')"); page.wait_for_timeout(150)
    page.get_by_role('button', name='Exportar…').click(); page.wait_for_selector('#expBl'); page.locator('#btnExpMaestros').click(); page.wait_for_timeout(500)
    ruta_todo = get('/__exports')[-1]; jt = json.load(open(ruta_todo, encoding='utf-8'))
    check(os.path.basename(ruta_todo).startswith('Ejercicios_y_bloques_'), f'nombre «{os.path.basename(ruta_todo)}»')
    check(len(jt['ejercicios']) == 4 and len(jt['bloques']) == 1, 'los 4 ejercicios y el bloque')

    print('\n[3] Importar en una base de datos vacía')
    original = page.evaluate('instantanea()')
    page.evaluate("db = normalize({}); render(); go('bloques')"); page.wait_for_timeout(150)
    page.set_input_files('#fileBloquesB', ruta_todo); page.wait_for_selector('#modal h3:has-text("Importar ejercicios y bloques")')
    check(m.locator('.aviso-import').count() == 0, 'sin datos previos no hay aviso')
    t = m.inner_text()
    check('Bloques: 1 nuevo' in t and 'Ejercicios: 4 nuevos' in t, 'resumen: 1 bloque y 4 ejercicios nuevos')
    m.get_by_role('button', name='Importar', exact=True).click(); page.wait_for_timeout(300)
    s = get('/__state')
    check(sorted((e['id'], e['nombre']) for e in s['exercises']) == [('e1', 'Puente glúteo'), ('e2', 'Plancha lateral'), ('e3', 'Estiramiento isquios'), ('e4', 'Respiración diafragmática')], 'los ejercicios llegan con sus identificadores (también al servidor)')
    check(s['bloques'] == [{'id': 'b1', 'nombre': 'Core básico', 'nivel': 'A', 'ejercicios': ['e1', 'e2']}], 'el bloque llega igual')
    check(page.locator('#deshacer.visible').count() == 1 and 'Importados 1 bloque y 4 ejercicios' in page.locator('#deshacer').inner_text(), 'se puede deshacer la importación')
    page.set_input_files('#fileBloquesB', ruta_todo); page.wait_for_selector('#modal .aviso-import')
    check('No hay nada nuevo' in m.inner_text() and m.get_by_role('button', name='Combinar e importar').is_disabled(), 'importar dos veces lo mismo no añade nada')
    page.evaluate('closeModal()')

    print('\n[4] Importar en una base de datos con datos: aviso y combinar')
    page.evaluate(f"db = JSON.parse({json.dumps(original)}); db.exercises.find(e => e.id === 'e2').nombre = 'Plancha lateral corta'; db.exercises.push({{ id: 'x9', nombre: 'Equilibrio monopodal' }}); render()"); page.wait_for_timeout(200)
    otra = archivo('otra_clinica.json', {'formato': 'fisioterapia-maestros', 'version': 1, 'exportado': '2026-10-20', 'clinica': 'Otra clínica',
        'ejercicios': [{'id': 'k1', 'nombre': 'PUENTE GLUTEO'}, {'id': 'k2', 'nombre': 'equilibrio monopodal'}, {'id': 'k3', 'nombre': 'Gateo'}, {'id': 'e2', 'nombre': 'Plancha lateral'}, {'id': 'e4', 'nombre': 'Otro nombre'}],
        'bloques': [{'id': 'kb1', 'nombre': 'Equilibrio', 'nivel': 'B', 'ejercicios': ['k1', 'k2', 'k3', 'k3', 'nada']},
                    {'id': 'kb2', 'nombre': 'core BÁSICO', 'nivel': 'a', 'ejercicios': ['k1']},
                    {'id': 'kb3', 'nombre': 'Vacío', 'ejercicios': ['nada']},
                    {'id': 'kb4', 'nombre': 'Laterales', 'ejercicios': ['e2']}]})
    page.evaluate("go('ejercicios')"); page.wait_for_timeout(150)
    page.set_input_files('#fileEjercicios', otra); page.wait_for_selector('#modal .aviso-import')
    t = m.inner_text()
    check('Esta base de datos ya tiene 5 ejercicios y 1 bloque' in t and 'se combinará' in t, f'avisa de que ya hay datos y de que se combinan')
    check('Otra clínica' in t and 'exportado el 20 oct 2026' in t, 'dice de dónde viene el archivo')
    check('Bloques: 2 nuevos · 1 ya existe' in t and 'Ejercicios: 1 nuevo · 4 ya existen' in t, f'cuenta lo nuevo y lo que ya existe ({t.splitlines()[-4:]})')
    m.get_by_role('button', name='Combinar e importar').click(); page.wait_for_timeout(300)
    s = get('/__state')
    nombres = [e['nombre'] for e in s['exercises']]
    check(len(nombres) == 6 and nombres.count('Gateo') == 1, f'solo se añade «Gateo» (ejercicios: {sorted(nombres)})')
    check(page.evaluate("getE('e2').nombre") == 'Plancha lateral corta' and page.evaluate("getE('e4').nombre") == 'Respiración diafragmática', 'lo que ya existe no se cambia (ni siquiera el nombre)')
    eq = next(x for x in s['bloques'] if x['nombre'] == 'Equilibrio')
    gateo = next(e['id'] for e in s['exercises'] if e['nombre'] == 'Gateo')
    check(eq['ejercicios'] == ['e1', 'x9', gateo] and eq['nivel'] == 'B', 'el bloque nuevo usa los ejercicios que ya había (mismo nombre, sin tildes ni mayúsculas)')
    check(not any(x['id'] == 'kb2' for x in s['bloques']), 'un bloque con el mismo nombre y nivel no se duplica')
    check(next(x for x in s['bloques'] if x['nombre'] == 'Laterales')['ejercicios'] == ['e2'], 'un ejercicio con el mismo identificador es el mismo, aunque se haya renombrado')
    page.locator('#deshacer').get_by_role('button', name='Deshacer').click(); page.wait_for_timeout(300)
    check(len(get('/__state')['bloques']) == 1 and len(get('/__state')['exercises']) == 5, 'Deshacer quita todo lo importado')

    print('\n[5] Catálogo y archivos no válidos (desde Ajustes › Datos)')
    page.evaluate("ui.ajTab = 'datos'; go('ajustes')"); page.wait_for_timeout(150)
    check(page.get_by_role('button', name='Exportar…').count() == 1 and page.get_by_role('button', name='Importar…').count() == 1, 'Exportar e Importar también están en Ajustes › Datos')
    dialogos.clear()
    page.set_input_files('#fileBloques', archivo('malo.json', {'hola': 1})); page.wait_for_timeout(300)
    check(any('no es de ejercicios y bloques' in d for d in dialogos), 'un archivo que no es de la aplicación se rechaza con un aviso')
    page.set_input_files('#fileBloques', archivo('roto.json', '{no es json')); page.wait_for_timeout(300)
    check(sum('no es de ejercicios y bloques' in d for d in dialogos) == 2, 'un archivo roto también')
    page.evaluate("db = normalize({}); render()"); page.wait_for_timeout(150)
    page.set_input_files('#fileBloques', os.path.join(RAIZ, 'internal', 'bloques_dmi.json')); page.wait_for_selector('#modal h3:has-text("Importar ejercicios y bloques")')
    t = m.inner_text()
    check('Bloques: 95 nuevos' in t and 'Ejercicios: 215 nuevos' in t and 'Nivel A: 35' in t, 'el catálogo bloques_dmi.json se sigue importando (95 bloques, 215 ejercicios)')
    m.get_by_role('button', name='Importar', exact=True).click(); page.wait_for_timeout(300)
    check(page.evaluate('db.bloques.length') == 95 and page.evaluate('db.exercises.length') == 215, 'importado')
    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
