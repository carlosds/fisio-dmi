# Observaciones al puntuar: se escriben en la ventana del día (por sesión, o del día si no tiene sesión), se guardan,
# salen en el calendario (semana, mes y día), en la lista de sesiones y en el informe de pautas, y siguen a sus
# puntuaciones si la sesión se anula.
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_observaciones.py PUERTO
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
    dialogos = []
    page.on('dialog', lambda d: (dialogos.append(d.message), d.accept()))
    page.goto(BASE + '/'); page.wait_for_selector('#listaPacientes')
    ev = page.evaluate
    hoy = ev('todayIso()'); manana = ev("addDays(todayIso(), 1)")
    ev(f"""db.citas.push({{ id: 'c1', patientId: 'p1', fecha: '{manana}', hora: '10:00', duracion: 45, nota: '', color: '', serieId: '', fechaSerie: '' }});
        openPatient('p1'); irTab('citas')""")
    page.wait_for_selector('#sec-citas .cita-fila')

    print('\n[1] Escribir observaciones de una sesión')
    page.locator('#sec-citas .cita-fila').first.get_by_role('button', name='Puntuar').click(); page.wait_for_selector('#obsSesion')
    check('de esta sesión' in page.locator('label[for=obsSesion]').inner_text(), 'la ventana del día tiene «Observaciones de esta sesión»')
    page.fill('#obsSesion', 'Ha venido cansada.\nRepetir el puente la próxima vez.')
    page.wait_for_timeout(1200)   # se guarda sola al poco de escribir
    o = [x for x in st().get('observaciones', []) if x['patientId'] == 'p1']
    check(len(o) == 1 and o[0]['sesion'] == 'c1' and o[0]['fecha'] == manana and o[0]['texto'].startswith('Ha venido cansada.\nRepetir'),
          'se guarda en el servidor como observación de esa sesión, con sus saltos de línea')
    check(o and o[0]['exerciseId'] == '' and o[0]['bloqueId'] == '' and o[0]['repeticion'] == 0, 'con el ámbito de sesión (sin bloque, ejercicio ni repetición)')
    page.locator('#modal').get_by_text('Cerrar', exact=True).click(); page.wait_for_timeout(200)

    print('\n[2] Lista de sesiones')
    fila = page.locator('#sec-citas .cita-fila').first
    check('Ha venido cansada' in fila.locator('.obs-fila').inner_text(), 'la fila de la sesión muestra sus observaciones')

    print('\n[3] Calendario')
    ev(f"irTab('calendario'); ui.vista = 'semana'; ui.fecha = fromIso('{manana}'); render()"); page.wait_for_timeout(150)
    dia = page.locator('#calCuerpo .day', has=page.locator('.obs-dia'))
    check(dia.count() == 1 and 'Ha venido cansada' in dia.locator('.obs-dia').inner_text(), 'en la semana, el día lleva el texto de las observaciones')
    ev("ui.vista = 'mes'; render()"); page.wait_for_timeout(150)
    marca = page.locator('#calCuerpo .day.mes .obs-marca')
    check(marca.count() == 1 and 'Ha venido cansada' in marca.get_attribute('title'), 'en el mes, un icono con el texto al pasar el ratón')
    ev("ui.vista = 'dia'; render()"); page.wait_for_timeout(150)
    check('Ha venido cansada' in page.locator('#calCuerpo .obs-texto').inner_text(), 'en la vista de un día, el texto completo')

    print('\n[4] Observaciones sin sesión')
    ev(f"ui.patientId = 'p1'; openDay('{hoy}', 'puntuar')"); page.wait_for_selector('#obsSesion')
    check('del día' in page.locator('label[for=obsSesion]').inner_text(), 'un día sin sesión tiene «Observaciones del día»')
    page.fill('#obsSesion', 'Ejercicios en casa con su madre'); page.wait_for_timeout(100)
    check(ev(f"textoObs('p1', '{hoy}', '')") == 'Ejercicios en casa con su madre', 'se guardan en la sesión sin cita')
    page.fill('#obsSesion', '   '); page.wait_for_timeout(100)
    check(ev(f"db.observaciones.filter(o => o.fecha === '{hoy}').length") == 0, 'al vaciarlas, se quitan')
    ev('closeModal()')

    print('\n[5] Informe de pautas')
    check(ev(f"obsPeriodoPdf('p1', '{hoy}', '{manana}')") == [{'fecha': manana, 'titulo': 'Sesión 10:00–10:45', 'texto': 'Ha venido cansada.\nRepetir el puente la próxima vez.'}],
          'el informe recoge las observaciones del periodo con su sesión')
    tam = ev(f"""(async () => [(await pdfPaciente(getP('p1'), '{hoy}', '{manana}', {{ detalle: false }})).length,
                               (await pdfPaciente(getP('p1'), '{hoy}', '{manana}', {{ detalle: false, observaciones: false }})).length])()""")
    check(tam[0] > tam[1], f'el PDF incluye la sección de observaciones, y se puede quitar ({tam[0]} > {tam[1]} bytes)')
    ev("openExportar(['p1'])"); page.wait_for_selector('#expObs')
    check(page.is_checked('#expObs'), 'el diálogo del informe tiene «Incluir las observaciones», marcado')
    ev('closeModal()')

    print('\n[6] Al anular la sesión, las observaciones pasan a «Sin sesión»')
    dialogos.clear()
    ev("irTab('citas')"); page.wait_for_selector('#sec-citas .cita-fila')
    page.locator('#sec-citas .cita-fila').first.locator('.menu-mas').click(); page.locator('#sec-citas .cita-fila').first.get_by_role('button', name='Anular sesión…').click(); page.wait_for_timeout(400)
    check(any('observaciones pasan' in x for x in dialogos), f'el aviso lo dice ({dialogos[-1:] })')
    o = [x for x in ev('db.observaciones') if x['patientId'] == 'p1']
    check(len(o) == 1 and o[0]['sesion'] == '' and o[0]['fecha'] == manana, 'la observación sigue, en la sesión sin cita de ese día')
    check(ev(f"sesionesDia('p1', '{manana}').map(x => x.id)") == [''], 'y ese día tiene su «Sin sesión» para verla')

    check(not errs, f'sin errores JS {errs}')
    b.close()
print('\nRESULTADO:', 'TODO OK' if not fails else f'{len(fails)} FALLOS')
sys.exit(1 if fails else 0)
