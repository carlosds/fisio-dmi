# Planes en casa del paciente (0.0.5): lista de planes con fechas, duración, notas y ejercicios «a elegir»;
# editor por semanas igual que las plantillas; búsqueda; PDF; duplicar; plantillas; y conversión de los datos antiguos.
# Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_planes.py PUERTO
import json, os, re, subprocess, sys, urllib.request
from playwright.sync_api import sync_playwright
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
EXP = os.path.join(os.environ.get('EXPDIR', '/tmp/fisio_exports'), 'planes')
ok = True; dialogs = []
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def st(): return json.load(urllib.request.urlopen(BASE + '__state'))
planes = lambda: [x for x in st().get('planes', []) if x['patientId'] == 'p1']

with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 900}); errors = []
    page.on('pageerror', lambda e: errors.append(str(e))); page.on('dialog', lambda d: (dialogs.append(d.message), d.accept()))
    page.goto(BASE); page.wait_for_selector('#main'); page.evaluate('descartarNovedades()')

    print('\n[1] Conversión de los planes antiguos (calendario + planes guardados)')
    r = page.evaluate("""() => { planesMigrados = false; const n = normalize({ patients: [{id:'p1'}], plantillas: [{ id:'tz', nombre:'T', semanas:1, ciclo:1, items:[], aplicaciones:[{ id:'a', patientId:'p1', desde:'2026-06-01', hasta:'2026-06-14', fecha:'2026-05-30' }] }],
        planCasa: [ {id:'c1',patientId:'p1',fecha:'2026-06-03',exerciseId:'e1',bloqueId:'b1',orden:1,nota:'',grupo:'g',notaGrupo:'3x10'},
                    {id:'c2',patientId:'p1',fecha:'2026-06-12',exerciseId:'e3',bloqueId:'',orden:1,nota:'30 s',grupo:'',notaGrupo:''},
                    {id:'c3',patientId:'p2',fecha:'2026-07-01',exerciseId:'e3',bloqueId:'',orden:1,nota:'',grupo:'',notaGrupo:''} ],
        planesGuardados: [ { id:'g1', patientId:'p2', descripcion:'Copia', creada:'2026-06-20', items:[{id:'i',fecha:'2026-07-01',exerciseId:'e3',bloqueId:'',orden:1,nota:'',grupo:'',notaGrupo:''}] },
                           { id:'g2', patientId:'p1', descripcion:'Antiguo', creada:'2026-05-01', items:[{id:'j',fecha:'2026-05-04',exerciseId:'e2',bloqueId:'',orden:1,nota:'',grupo:'',notaGrupo:''}] } ] });
      return { migrado: planesMigrados, viejos: n.planCasa.length + n.planesGuardados.length,
        planes: n.planes.map(p => ({ pid: p.patientId, nombre: p.nombre, inicio: p.inicio, fin: p.fin, semanas: p.semanas, tpl: p.plantillaId, dias: p.items.map(i => i.dia).sort((a, b) => a - b) })) }; }""")
    pl = r['planes']
    check(r['migrado'] and r['viejos'] == 0, 'se convierten y los datos antiguos quedan vacíos (se guardará el nuevo formato)')
    p1 = [x for x in pl if x['pid'] == 'p1' and x['nombre'] == 'Plan en casa']
    check(len(p1) == 1 and p1[0]['inicio'] == '2026-06-03' and p1[0]['semanas'] == 2 and p1[0]['fin'] == '2026-06-16', f'el calendario pasa a un plan de 2 semanas desde el primer día ({p1})')
    check(p1 and p1[0]['dias'] == [3, 12] and p1[0]['tpl'] == 'tz', 'los días se cuentan desde el lunes de la primera semana y se recuerda la plantilla aplicada')
    check(sum(1 for x in pl if x['pid'] == 'p2') == 1 and any(x['nombre'] == 'Copia' for x in pl), 'un calendario igual que un plan guardado no se duplica: queda el plan con su nombre')
    check(any(x['nombre'] == 'Antiguo' and x['inicio'] == '2026-05-04' for x in pl), 'cada plan guardado es un plan con su nombre')

    print('\n[2] Lista vacía y plan nuevo')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    page.get_by_role('tab', name='Plan en casa').click(); page.wait_for_timeout(200)
    check('todavía no tiene planes en casa' in page.locator('#sec-casa').inner_text(), 'lista vacía con mensaje')
    page.get_by_role('button', name='Nuevo plan').click(); page.wait_for_selector('#pcNombre'); page.wait_for_timeout(100)
    check(page.evaluate('document.activeElement.id') == 'pcNombre', 'el editor se abre con el nombre listo para escribir')
    check(re.search(r'#/paciente/p1/casa/\w+', page.evaluate('location.hash')), 'el plan abierto tiene su dirección')
    page.fill('#pcNombre', 'Lumbalgia fase 1'); page.locator('#pcNombre').dispatch_event('change'); page.wait_for_timeout(100)
    page.fill('#pcIni', '2026-06-03'); page.locator('#pcIni').dispatch_event('change'); page.wait_for_timeout(150)
    page.fill('#pcDurN', '2'); page.locator('#pcDurN').dispatch_event('change'); page.wait_for_timeout(300)
    p = planes()
    check(len(p) == 1 and p[0]['nombre'] == 'Lumbalgia fase 1' and p[0]['inicio'] == '2026-06-03' and p[0]['duracion'] == 2 and p[0]['unidad'] == 'semanas' and p[0]['fin'] == '2026-06-16' and not p[0].get('finManual'),
          f'nombre, inicio y 2 semanas: termina sola el 16 de junio ({p and (p[0]["inicio"], p[0]["fin"])})')
    check(page.input_value('#pcFin') == '2026-06-16', 'el campo «Termina» muestra la fecha calculada')
    check(page.locator('.semana-t').count() == 3 and page.locator('.pc-semana .pc-dia').count() == 21, 'empieza un miércoles: 3 semanas de lunes a domingo')
    fuera = page.locator('.pc-dia.pc-fuera')
    check(fuera.count() == 7 and 'lun 1 jun' in fuera.first.inner_text().lower(), 'los días antes del inicio y después del fin salen «Fuera del plan»')
    check('del 3 jun al 7 jun' in page.locator('.semana-t').first.inner_text(), 'el título de la semana lleva sus fechas')
    fe = page.locator('.plan-fechas').bounding_box(); ca = page.locator('.pc-elegir').bounding_box(); no = page.locator('#pcNotas').bounding_box()
    check(no['y'] < fe['y'] < ca['y'] and ca['y'] - (fe['y'] + fe['height']) < 80, 'inicio, duración y fin quedan justo encima del calendario del plan')
    check(page.locator('.ayuda-campo').count() == 0 and 'Se calcula' not in page.locator('#sec-casa').inner_text(), 'la explicación de «Termina» no ocupa el formulario')
    page.locator('.plan-fechas .ayuda-ico').click(); page.wait_for_selector('#ayudaPop')
    check('Fecha de fin' in page.locator('#ayudaPop').inner_text() and 'vacaciones' in page.locator('#ayudaPop').inner_text(), 'el «?» de «Termina» explica la fecha de fin en una ventanita')
    page.keyboard.press('Escape')

    print('\n[3] Ejercicios por día y «a elegir»')
    page.locator('.pc-dia[data-dia="3"]').get_by_role('button', name='+ Añadir').click(); page.wait_for_selector('#modal .exCheck')
    check(page.locator('#modal .acDia').count() == 14 and page.locator('#modal .acDiaFuera').count() == 7, 'al añadir, solo se pueden marcar los 14 días del plan')
    page.locator('#modal .exCheck[value="e3"]').check(); page.locator('#modal .acDia[value="5"]').check(); page.fill('#acNota', '30 s')
    page.locator('#modal').get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(300)
    p = planes()[0]
    check(sorted(i['dia'] for i in p['items']) == [3, 5] and all(i['nota'] == '30 s' for i in p['items']), 'el ejercicio queda el miércoles 3 y el viernes 5, con su nota')
    page.locator('.pc-dia.pc-libre').get_by_role('button', name='+ Añadir').click(); page.wait_for_selector('#modal .exCheck')
    check(page.locator('#modal .acDia').count() == 0 and 'A elegir' in page.locator('#modal h3').inner_text(), '«A elegir» no pide días')
    page.locator('#modal .bCheck[value="b1"]').check(); page.fill('#acNota', 'Cuando quiera, 2 veces por semana')
    page.locator('#modal').get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(300)
    p = planes()[0]
    libres = [i for i in p['items'] if i['dia'] == 0]
    check(len(libres) == 2 and all(i['notaGrupo'].startswith('Cuando quiera') for i in libres), 'el bloque queda en «a elegir» (día 0) con su nota')
    check('Core básico' in page.locator('.pc-libre').inner_text(), 'se ve en la sección «A elegir»')

    print('\n[4] Notas del plan y fecha de fin a mano')
    page.fill('#pcNotas', 'Hacerlo después de la merienda.\nUsar la colchoneta azul.'); page.locator('#pcNotas').dispatch_event('change'); page.wait_for_timeout(300)
    check(planes()[0]['notas'].startswith('Hacerlo después') and 'colchoneta' in planes()[0]['notas'], 'las notas se guardan')
    page.fill('#pcFin', '2026-06-23'); page.locator('#pcFin').dispatch_event('change'); page.wait_for_timeout(300)
    p = planes()[0]
    check(p['fin'] == '2026-06-23' and p.get('finManual') and p['duracion'] == 2, 'la fecha de fin se puede cambiar a mano sin cambiar la duración')
    check('Fecha de fin cambiada a mano' in page.locator('#sec-casa').inner_text() and page.locator('.pc-semana .pc-dia').count() == 21, 'se indica que es manual y los días del plan no cambian')
    page.get_by_role('button', name='Recalcular').click(); page.wait_for_timeout(300)
    check(planes()[0]['fin'] == '2026-06-16' and not planes()[0].get('finManual'), '«Recalcular» vuelve a la fecha calculada')
    page.fill('#pcFin', '2026-06-01'); page.locator('#pcFin').dispatch_event('change'); page.wait_for_timeout(200)
    check(planes()[0]['fin'] == '2026-06-16' and any('anterior' in d for d in dialogs), 'una fecha de fin anterior al inicio no se admite')

    print('\n[5] Cambiar el inicio: los ejercicios van con su semana')
    page.fill('#pcIni', '2026-06-10'); page.locator('#pcIni').dispatch_event('change'); page.wait_for_timeout(300)
    p = planes()[0]
    check(p['inicio'] == '2026-06-10' and p['fin'] == '2026-06-23' and sorted(i['dia'] for i in p['items'] if i['dia']) == [3, 5], 'una semana después: mismos días de la semana, fechas una semana más tarde')
    check(page.locator('.pc-dia[data-dia="3"]').inner_text().lower().startswith('mié 10 jun'), 'el miércoles 10 tiene el ejercicio')
    dialogs.clear()
    page.fill('#pcIni', '2026-06-12'); page.locator('#pcIni').dispatch_event('change'); page.wait_for_timeout(300)
    check(any('fuera del plan' in d for d in dialogs) and sorted(i['dia'] for i in planes()[0]['items'] if i['dia']) == [5], 'si un ejercicio queda fuera, avisa y lo quita')
    page.locator('#deshacer').get_by_role('button', name='Deshacer').click(); page.wait_for_timeout(300)
    check(planes()[0]['inicio'] == '2026-06-10' and sorted(i['dia'] for i in planes()[0]['items'] if i['dia']) == [3, 5], 'y se puede deshacer')
    page.fill('#pcIni', '2026-06-03'); page.locator('#pcIni').dispatch_event('change'); page.wait_for_timeout(300)

    print('\n[5b] Duración en días o meses')
    page.select_option('#pcDurU', 'dias'); page.wait_for_timeout(300)
    check(planes()[0]['duracion'] == 14 and planes()[0]['unidad'] == 'dias' and planes()[0]['fin'] == '2026-06-16' and len(planes()[0]['items']) == 4, 'cambiar de semanas a días convierte el número (2 semanas → 14 días) y no quita nada')
    page.fill('#pcDurN', '10'); page.locator('#pcDurN').dispatch_event('change'); page.wait_for_timeout(300)
    p = planes()[0]
    check(p['duracion'] == 10 and p['unidad'] == 'dias' and p['fin'] == '2026-06-12', f'10 días desde el 3 de junio: termina el 12 ({p["duracion"]}, {p["unidad"]}, {p["fin"]})')
    check(page.locator('.pc-dia.pc-fuera').count() == 4 and '10 días' in page.locator('#sec-casa').inner_text(), 'los días que sobran de la última semana salen fuera del plan')
    page.select_option('#pcDurU', 'meses'); page.wait_for_timeout(200); page.fill('#pcDurN', '1'); page.locator('#pcDurN').dispatch_event('change'); page.wait_for_timeout(300)
    p = planes()[0]
    check(p['unidad'] == 'meses' and p['duracion'] == 1 and p['fin'] == '2026-07-02', f'1 mes desde el 3 de junio: termina el 2 de julio ({p["fin"]})')
    check(page.evaluate("finDuracion('2026-01-31', 1, 'meses')") == '2026-02-27' and page.evaluate("finDuracion('2026-03-31', 1, 'meses')") == '2026-04-29', 'meses con días distintos (31 de enero + 1 mes termina el 27 de febrero)')
    page.select_option('#pcDurU', 'semanas'); page.wait_for_timeout(200); page.fill('#pcDurN', '2'); page.locator('#pcDurN').dispatch_event('change'); page.wait_for_timeout(300)
    check(planes()[0]['fin'] == '2026-06-16' and planes()[0]['unidad'] == 'semanas', 'y de vuelta a 2 semanas')

    print('\n[6] Lista de planes: fechas, duración y búsqueda')
    page.evaluate("""() => { const mk = (nombre, inicio, semanas) => { const pl = { id: uid(), patientId: 'p1', nombre, inicio, semanas, fin: '', finManual: false, notas: '', creado: todayIso(), plantillaId: '', items: [{ id: uid(), dia: diaSemana(inicio), exerciseId: 'e1', bloqueId: '', orden: 1, nota: '', grupo: '', notaGrupo: '' }] }; pl.fin = finAutoPlan(pl); db.planes.push(pl); };
      mk('Verano', '2026-08-03', 4); mk('Invierno', '2027-01-11', 1); render(); }""")
    page.get_by_role('button', name='← Planes en casa').click(); page.wait_for_selector('#listaPlanes')
    filas = page.locator('.tabla-planes tbody tr')
    check(filas.count() == 3 and filas.first.inner_text().startswith('Invierno'), 'lista con los 3 planes, el más reciente primero')
    f1 = page.locator('.fila-plan', has_text='Lumbalgia fase 1').inner_text()
    check('3 jun 2026' in f1 and '16 jun 2026' in f1 and '2 semanas' in f1 and '2 a elegir' in f1, f'la fila muestra inicio, fin, duración y contenido ({f1!r})')
    check('4 semanas' in page.locator('.fila-plan', has_text='Verano').inner_text(), 'duración del otro plan')
    acc = page.locator('.fila-plan').first.locator('.acc-plan button')
    ys = [acc.nth(i).bounding_box()['y'] for i in range(acc.count())]
    check(acc.count() == 3 and max(ys) - min(ys) < 2, 'los botones de la fila quedan en una sola línea')
    check(acc.all_inner_texts() == ['Editar plan', 'Exportar a PDF', 'Eliminar'], 'botones: Editar plan, Exportar a PDF y Eliminar')
    n = lambda: page.locator('.tabla-planes tbody tr').count()
    page.fill('#fpQ', 'lumbal'); page.wait_for_timeout(100)
    check(n() == 1 and page.evaluate("document.activeElement.id") == 'fpQ', 'buscar por nombre (y el foco se queda en la caja)')
    page.fill('#fpQ', ''); page.select_option('#fpMes', '08'); page.wait_for_timeout(100)
    check(n() == 1 and 'Verano' in page.locator('#listaPlanes').inner_text(), 'buscar por mes')
    page.select_option('#fpMes', ''); page.select_option('#fpAnio', '2027'); page.wait_for_timeout(100)
    check(n() == 1 and 'Invierno' in page.locator('#listaPlanes').inner_text(), 'buscar por año')
    page.select_option('#fpAnio', '2026'); page.select_option('#fpMes', '06'); page.wait_for_timeout(100)
    check(n() == 1 and 'Lumbalgia' in page.locator('#listaPlanes').inner_text(), 'mes y año juntos')
    page.select_option('#fpMes', ''); page.select_option('#fpAnio', ''); page.fill('#fpDesde', '2026-06-10'); page.locator('#fpDesde').dispatch_event('change')
    page.fill('#fpHasta', '2026-08-05'); page.locator('#fpHasta').dispatch_event('change'); page.wait_for_timeout(100)
    check(n() == 2 and 'Invierno' not in page.locator('#listaPlanes').inner_text(), 'intervalo de fechas: los planes que lo tocan')
    page.fill('#fpQ', 'zzz'); page.wait_for_timeout(100)
    check('Ningún plan coincide' in page.locator('#listaPlanes').inner_text(), 'sin coincidencias, avisa')
    page.get_by_role('button', name='Quitar filtros').click(); page.wait_for_timeout(100)
    check(n() == 3, '«Quitar filtros» vuelve a mostrar todos')

    print('\n[7] PDF del plan')
    for f in os.listdir(EXP) if os.path.isdir(EXP) else []: os.remove(os.path.join(EXP, f))
    page.locator('.fila-plan', has_text='Lumbalgia').get_by_role('button', name='Exportar a PDF').click(); page.wait_for_selector('#casaExpMsg:has-text("guardado")', timeout=20000)
    pdfs = os.listdir(EXP)
    check(len(pdfs) == 1 and pdfs[0] == 'López_Pérez_Ana_Plan_en_casa_Lumbalgia_fase_1_2026-06-03_2026-06-16.pdf' and '2026-06-03' in pdfs[0] and '2026-06-16' in pdfs[0], f'nombre del PDF con el plan y sus fechas: {pdfs}')
    txt = subprocess.run(['pdftotext', '-layout', os.path.join(EXP, pdfs[0]), '-'], capture_output=True, text=True).stdout
    check('Lumbalgia fase 1' in txt and 'Del 3 de junio de 2026 al 16 de junio de 2026 (2 semanas)' in txt, 'el PDF lleva el nombre, las fechas y la duración')
    check('Observaciones' in txt and 'Hacerlo después de la merienda.' in txt and 'Usar la colchoneta azul.' in txt, 'el PDF lleva las notas (respetando los saltos de línea)')
    check('A elegir' in txt and 'Core básico' in txt and 'Miércoles, 3 de junio de 2026' in txt and 'Viernes, 5 de junio de 2026' in txt, 'el PDF lleva «a elegir» y los días con su fecha')
    check(page.evaluate("nombrePdf(['Dabarca', 'Carlos', 'Plan en casa', norm('Plan en casa') === 'plan en casa' ? '' : 'x', '2026-10-26', '2026-11-01'])") == 'Dabarca_Carlos_Plan_en_casa_2026-10-26_2026-11-01', 'un plan llamado «Plan en casa» no repite el tipo')
    check(page.evaluate("db.informes.at(-1).tipo") == 'plan' and 'Lumbalgia' in page.evaluate("db.informes.at(-1).descripcion"), 'queda registrado en «Informes»')

    print('\n[8] Duplicar, guardar como plantilla y usar una plantilla')
    page.locator('.fila-plan', has_text='Lumbalgia').get_by_role('button', name='Editar plan').click(); page.wait_for_selector('#pcNombre')
    page.get_by_role('button', name='Duplicar').click(); page.wait_for_timeout(300)
    c = [x for x in planes() if x['nombre'] == 'Lumbalgia fase 1 (copia)']
    check(len(c) == 1 and c[0]['inicio'] == '2026-06-17' and c[0]['fin'] == '2026-06-30' and len(c[0]['items']) == 4, 'Duplicar: copia que empieza justo después, mismo día de la semana y mismos ejercicios')
    check(page.input_value('#pcNombre') == 'Lumbalgia fase 1 (copia)', 'y se abre la copia')
    page.get_by_role('button', name='Guardar como plantilla…').click(); page.fill('#plNombre', 'Lumbalgia tipo')
    page.get_by_role('button', name='Guardar plantilla').click(); page.wait_for_timeout(300); page.evaluate('closeModal()')
    t = [x for x in st()['plantillas'] if x['nombre'] == 'Lumbalgia tipo']
    check(len(t) == 1 and t[0]['semanas'] == 3 and sorted(i['dia'] for i in t[0]['items']) == [0, 0, 3, 5] and t[0]['notas'].startswith('Hacerlo'), 'la plantilla guarda días, «a elegir» y notas')
    page.evaluate("openElegirPlantilla('p1')")
    page.locator('#modal .plItem', has_text='Lumbalgia tipo').get_by_role('button', name='Elegir').click(); page.wait_for_selector('#apIni')
    check(page.input_value('#apNombre') == 'Lumbalgia tipo' and page.input_value('#apDurN') == '2' and page.input_value('#apDurU') == 'semanas', 'propone el nombre y la duración de la plantilla')
    page.fill('#apNombre', 'Desde plantilla'); page.fill('#apIni', '2027-11-01'); page.fill('#apDurN', '4'); page.locator('#apDurN').dispatch_event('input')
    check('Termina el domingo, 28 de noviembre de 2027' in page.locator('#apFinTxt').inner_text(), 'muestra cuándo termina')
    page.get_by_role('button', name='Crear plan', exact=True).click(); page.wait_for_timeout(400)
    d = [x for x in planes() if x['nombre'] == 'Desde plantilla']
    check(len(d) == 1 and d[0]['semanas'] == 4 and d[0]['fin'] == '2027-11-28' and d[0]['plantillaId'] == t[0]['id'] and d[0]['notas'].startswith('Hacerlo'), 'crea un plan nuevo con nombre, fechas, notas y la plantilla de origen')
    check(sorted(i['dia'] for i in d[0]['items']) == [0, 0, 3, 5, 24, 26], 'la plantilla de 3 semanas se repite: la semana 4 es otra vez la 1 (y «a elegir» va una vez)')
    check(page.input_value('#pcNombre') == 'Desde plantilla', 'se abre el plan creado')
    page.evaluate("go('plantillas')"); page.wait_for_timeout(150)
    check('Pacientes (1)' in page.locator('.plItem', has_text='Lumbalgia tipo').inner_text(), 'la plantilla cuenta al paciente con un plan en curso')

    print('\n[9] Atrás, vaciar, eliminar y deshacer')
    page.evaluate("openPatient('p1'); irTab('casa')"); page.wait_for_selector('#listaPlanes')
    page.locator('.fila-plan', has_text='Verano').get_by_role('button', name='Editar plan').click(); page.wait_for_selector('#pcNombre')
    page.go_back(); page.wait_for_timeout(300)
    check(page.locator('#listaPlanes').count() == 1, 'Atrás vuelve de un plan a la lista')
    page.go_forward(); page.wait_for_timeout(300)
    check(page.locator('#pcNombre').count() == 1 and page.input_value('#pcNombre') == 'Verano', 'Adelante vuelve a abrirlo')
    page.get_by_title('Quita todos los ejercicios del plan').click(); page.wait_for_timeout(300)
    check([x for x in planes() if x['nombre'] == 'Verano'][0]['items'] == [], 'Vaciar quita los ejercicios y conserva el plan')
    page.locator('#deshacer').get_by_role('button', name='Deshacer').click(); page.wait_for_timeout(300)
    check(len([x for x in planes() if x['nombre'] == 'Verano'][0]['items']) == 1, 'y se puede deshacer')
    nplanes = len(planes())
    page.get_by_role('button', name='Eliminar plan').click(); page.wait_for_timeout(400)
    check(len(planes()) == nplanes - 1 and page.locator('#listaPlanes').count() == 1, 'Eliminar plan vuelve a la lista')
    page.evaluate("delEj('e3')"); page.wait_for_timeout(300)
    check(all(i['exerciseId'] != 'e3' for x in planes() for i in x['items']), 'borrar un ejercicio lo quita de los planes')
    check(page.evaluate("finPlanesCasa().p1") == max(x['fin'] for x in planes() if x['items']), 'en la lista de pacientes, «plan en casa hasta» es el fin más tardío')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
