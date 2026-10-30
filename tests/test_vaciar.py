# Quitar todos los ejercicios de un día, días por semana, quitar todas las pautas y vaciar un día del plan en casa.
import json, sys, urllib.request
from playwright.sync_api import sync_playwright
from ayuda_planes import PLAN_PRUEBA
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True; dialogs = []
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def st(): return json.load(urllib.request.urlopen(BASE + '__state'))
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = br.new_page(viewport={'width': 1300, 'height': 900}); errors = []
    page.on('pageerror', lambda e: errors.append(str(e))); page.on('dialog', lambda d: (dialogs.append(d.message), d.accept()))
    page.goto(BASE); page.wait_for_selector('#main')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')

    print('\n[Días por semana]')
    # la semana en curso: pautas solo lunes, miércoles y viernes (una pauta de un día cada una)
    page.evaluate("""() => { const l = iso(inicioSemana(new Date())); db.pautas = db.pautas.filter(x => x.patientId !== ui.patientId);
      [0, 2, 4].forEach((i, k) => db.pautas.push({id: 'dd' + k, patientId: ui.patientId, exerciseId: 'e' + (k + 1), desde: addDays(l, i), hasta: addDays(l, i), asignacion: 'dd' + k, bloqueId: '', orden: k}));
      render(); }""")
    check(page.locator('#diasSemana').count() == 0 and 'por semana' not in page.locator('.sticky-head').inner_text(), 'la cabecera ya no dice los días por semana')

    print('\n[Quitar todas las pautas]')
    dialogs.clear()
    check(page.get_by_role('button', name='Quitar todas las pautas').count() == 0, 'no está a la vista: va en el menú «⋯»')
    page.locator('#sec-pautas .menu-mas').first.click(); page.get_by_role('button', name='Quitar todas las pautas').click(); page.wait_for_timeout(300)
    check(any('todas las pautas' in d for d in dialogs), 'pide confirmación')
    check(len([x for x in st()['pautas'] if x['patientId'] == 'p1']) == 0, 'se eliminan todas las pautas del paciente')
    check(page.get_by_role('button', name='Quitar todas las pautas', include_hidden=True).is_disabled(), 'sin pautas, la opción queda desactivada')

    print('\n[Quitar todos los ejercicios de un día]')
    page.evaluate("""() => { db.pautas = [
      {id:'a1',patientId:ui.patientId,exerciseId:'e1',desde:'2026-06-01',hasta:'',asignacion:'g1',bloqueId:'b1',orden:1},
      {id:'a2',patientId:ui.patientId,exerciseId:'e2',desde:'2026-06-01',hasta:'',asignacion:'g1',bloqueId:'b1',orden:2},
      {id:'a3',patientId:ui.patientId,exerciseId:'e3',desde:'2026-06-01',hasta:'',asignacion:'g3',bloqueId:'',orden:3}];
      ui.selDay = '2026-06-10'; render(); renderDayModal(); }""")
    page.wait_for_selector('#modal .ej-dia')
    page.evaluate("db.puntuaciones[ui.patientId + '|2026-06-10|e1|1'] = 3; render(); refrescarModalDia()")
    dialogs.clear()
    page.locator('#modal .botonera-dia .menu-mas').click(); page.get_by_role('button', name='Quitar todos los ejercicios').click(); page.wait_for_timeout(300)
    check(any('puntuaciones' in d for d in dialogs), 'si hay puntuaciones, avisa de que se borrarán')
    check('No hay ejercicios asignados para este día' in page.locator('#modal').inner_text(), 'el día queda vacío (bloques y sueltos)')
    check(page.get_by_role('button', name='Quitar todos los ejercicios', include_hidden=True).count() == 0, 'con el día vacío la opción desaparece')
    ps = [x for x in st()['pautas'] if x['patientId'] == 'p1']
    cubre = lambda d, e: any(x['exerciseId'] == e and x['desde'] <= d and (not x['hasta'] or d <= x['hasta']) for x in ps)
    check(not any(cubre('2026-06-10', e) for e in ['e1', 'e2', 'e3']), 'ningún ejercicio cubre ese día')
    check(all(cubre('2026-06-09', e) and cubre('2026-06-11', e) for e in ['e1', 'e2', 'e3']), 'los días anterior y posterior siguen intactos')
    page.get_by_role('button', name='Cerrar').last.click()

    print('\n[Vaciar un día del plan en casa]')
    page.get_by_role('tab', name='Plan en casa').click()
    page.evaluate(PLAN_PRUEBA)
    page.evaluate("""() => planPrueba(ui.patientId, iso(inicioSemana(new Date())), 1, [{dia:1,e:'e1'},{dia:1,e:'e2'},{dia:2,e:'e3'}])""")
    check(page.locator('.pc-dia').get_by_role('button', name='Vaciar').count() == 0, '«Vaciar» ya no está en las tarjetas de los días')
    dialogs.clear()
    page.locator('.pc-dia[data-dia="1"]').get_by_role('button', name='Editar', exact=True).click(); page.wait_for_selector('#modal .dc-lista')
    page.locator('#modal').get_by_role('button', name='Vaciar el día…').click(); page.wait_for_timeout(300)
    check(any('Vaciar' in d for d in dialogs), 'pide confirmación')
    pc = [i for x in st()['planes'] if x['patientId'] == 'p1' for i in x['items']]
    check(len(pc) == 1 and pc[0]['exerciseId'] == 'e3', 'solo se vacía ese día; el martes se conserva')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
