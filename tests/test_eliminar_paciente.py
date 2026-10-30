# Eliminar un paciente y todos sus datos.
import json, re, sys, urllib.request
from playwright.sync_api import sync_playwright
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def st(): return json.load(urllib.request.urlopen(BASE + '__state'))
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 900}); errors = []; dialogs = []; resp = [False]
    page.on('pageerror', lambda e: errors.append(str(e)))
    def on_dialog(d): dialogs.append(d.message); d.accept() if resp[0] else d.dismiss()
    page.on('dialog', on_dialog)
    page.goto(BASE); page.wait_for_selector('#main')
    page.evaluate("""() => { db.patients.push({id:'p2', nombre:'Luis', apellidos:'Otro', fechaAlta:'2026-01-01', telefono:'', email:'', observaciones:''});
      const l = todayIso(); db.pautas.push({id:'ax', patientId:'p2', exerciseId:'e1', desde:'2026-01-01', hasta:null, asignacion:'gx', bloqueId:'', orden:9});
      db.puntuaciones['p2|' + l + '|e1|1'] = 2; db.puntuaciones['p1|' + l + '|e1|1'] = 1;
      db.planCasa.push({id:'pc2', patientId:'p2', fecha:l, exerciseId:'e1', bloqueId:'', orden:1, nota:'', grupo:'', notaGrupo:''});
      db.hitos.push({id:'h2', patientId:'p2', fecha:l, nota:'x', fotos:[]}); db.evaluaciones.push({id:'v2', patientId:'p2', fecha:l, evaluacion:'y', fotos:[]});
      db.planesGuardados.push({id:'g2', patientId:'p2', descripcion:'Plan', creada:l, items:[]});
      db.plantillas.push({id:'t1', nombre:'T', semanas:1, ciclo:1, creada:l, items:[], aplicaciones:[{id:'ap1', patientId:'p2', desde:l, hasta:l, fecha:l}]});
      openPatient('p2'); }""")
    page.wait_for_selector('#sec-pautas')
    page.get_by_role('button', name='Editar datos del paciente').click(); page.wait_for_selector('#fNombre')
    page.get_by_role('button', name='Eliminar paciente').click(); page.wait_for_timeout(300)
    check(dialogs and 'Luis Otro' in dialogs[-1] and 'Se borrarán también' in dialogs[-1], 'pide confirmación con el nombre')
    check(page.locator('#fNombre').count() == 1, 'si se cancela, el paciente sigue y el formulario abierto')
    resp[0] = True
    page.get_by_role('button', name='Eliminar paciente').click(); page.wait_for_timeout(600)
    s = st()
    check(all(p['id'] != 'p2' for p in s['patients']) and any(p['id'] == 'p1' for p in s['patients']), 'el paciente desaparece y el otro se conserva')
    check(not [x for x in s['pautas'] if x['patientId'] == 'p2'] and any(x['patientId'] == 'p1' for x in s['pautas']), 'se borran sus pautas, no las de otros')
    check(not [k for k in s['puntuaciones'] if k.startswith('p2|')] and any(k.startswith('p1|') for k in s['puntuaciones']), 'se borran sus puntuaciones, no las de otros')
    check(not [x for x in s['planCasa'] if x['patientId'] == 'p2'] and not s['hitos'] and not s['evaluaciones'] and not s['planesGuardados'], 'se borran plan en casa, hitos, evaluaciones y planes guardados')
    check(s['plantillas'][0]['aplicaciones'] == [], 'se quita de las aplicaciones de plantilla')
    check(page.locator('#listaPacientes').count() == 1 and 'Luis' not in page.locator('#listaPacientes').inner_text(), 'vuelve a la lista de pacientes sin él')
    # --- desde el listado: lista (no cuadrícula) y eliminar varios a la vez ---
    page.evaluate("""() => { ['p3','p4','p5'].forEach((id, i) => db.patients.push({id, nombre:'Nombre'+i, apellidos:'Zeta'+i, fechaAlta:'2026-01-01', telefono:'', email:'', observaciones:''}));
      db.pautas.push({id:'ay', patientId:'p3', exerciseId:'e1', desde:'2026-01-01', hasta:null, asignacion:'gy', bloqueId:'', orden:9}); render(); go('pacientes'); }""")
    page.wait_for_selector('#listaPacientes .item')
    col = page.evaluate("getComputedStyle(document.querySelector('#listaPacientes')).columnCount + '|' + getComputedStyle(document.querySelector('#listaPacientes')).columnWidth")
    check(col.startswith('auto'), f'el listado de pacientes es una lista, no columnas ({col})')
    check(page.locator('#accionesPac').get_by_role('button', name=re.compile('^Eliminar')).count() == 0, 'sin selección, «Eliminar» no aparece')
    nb = len(st()['patients'])
    page.fill('#buscarPac', 'Zeta'); page.wait_for_timeout(200)
    page.locator('#listaPacientes .cab-pac input[type=checkbox]').check(); page.wait_for_timeout(200)
    check(page.get_by_role('button', name='Eliminar (3)').count() == 1, 'la casilla de arriba selecciona los 3 pacientes de la búsqueda')
    resp[0] = False
    page.get_by_role('button', name=re.compile(r'^Eliminar \(')).click(); page.wait_for_timeout(300)
    check('estos' in dialogs[-1] and 'Zeta' in dialogs[-1], 'pide confirmación con los nombres de los varios pacientes')
    check(len(st()['patients']) == nb, 'si se cancela no se borra a nadie')
    resp[0] = True
    page.get_by_role('button', name=re.compile(r'^Eliminar \(')).click(); page.wait_for_timeout(600)
    ids = {p['id'] for p in st()['patients']}
    check(not ({'p3', 'p4', 'p5'} & ids), 'se eliminan los varios seleccionados')
    check(not [x for x in st()['pautas'] if x['patientId'] == 'p3'], 'y sus datos')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
