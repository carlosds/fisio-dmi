# Pruebas de plantillas del plan en casa. Uso: python3 mock_server.py PUERTO seed_nuevo.json & ; python3 test_plantillas.py PUERTO
import json, sys, urllib.request
from playwright.sync_api import sync_playwright
from ayuda_planes import PLAN_PRUEBA
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True; dialogs = []
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def st(): return json.load(urllib.request.urlopen(BASE + '__state'))
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('dialog', lambda d: (dialogs.append(d.message), d.accept()))
    page.goto(BASE); page.wait_for_selector('#main')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    page.get_by_role('tab', name='Plan en casa').click(); page.wait_for_timeout(200)
    # un plan de una semana: lunes bloque b1 con nota, miércoles e3 con nota
    page.evaluate(PLAN_PRUEBA)
    page.evaluate("""() => { const g = uid(); planPrueba(ui.patientId, iso(inicioSemana(new Date())), 1,
      [{dia:1,e:'e1',b:'b1',g,ng:'3x10'},{dia:1,e:'e2',b:'b1',g,ng:'3x10'},{dia:3,e:'e3',nota:'30 s'}]); }""")
    page.get_by_role('button', name='Guardar como plantilla…').click(); page.wait_for_selector('#plNombre'); page.wait_for_timeout(150)
    page.fill('#plNombre', 'Lumbalgia fase 1')
    page.get_by_role('button', name='Guardar plantilla').click(); page.wait_for_timeout(500)
    page.locator('#modal button.btn').click(); page.wait_for_timeout(500)
    t = st()['plantillas']
    check(len(t) == 1 and t[0]['nombre'] == 'Lumbalgia fase 1' and t[0]['semanas'] == 1 and len(t[0]['items']) == 3, 'plantilla guardada en servidor (1 semana, 3 entradas)')
    check(sorted({i['dia'] for i in t[0]['items']}) == [1, 3], 'días 1 (lunes) y 3 (miércoles)')
    check(any(i['nota'] == '30 s' for i in t[0]['items']) and any(i['notaGrupo'] == '3x10' for i in t[0]['items']), 'conserva notas')

    # usarla en un plan nuevo de 2 semanas
    page.get_by_role('button', name='← Planes en casa').click(); page.wait_for_selector('#listaPlanes')
    page.get_by_role('button', name='Usar una plantilla…').click(); page.locator('#modal').get_by_role('button', name='Elegir').first.click(); page.wait_for_selector('#apIni')
    check('Lumbalgia' in page.locator('#apPrev').inner_text() and 'Lunes' in page.locator('#apPrev').inner_text(), 'vista previa con días')
    page.fill('#apIni', '2030-01-07'); page.fill('#apDurN', '2')
    page.get_by_role('button', name='Crear plan', exact=True).click(); page.wait_for_timeout(500)
    pl = [x for x in st()['planes'] if x['inicio'] == '2030-01-07']
    its = pl[0]['items'] if pl else []
    check(len(pl) == 1 and len(its) == 6 and sorted({i['dia'] for i in its}) == [1, 3, 8, 10], '2 semanas: la plantilla se repite (6 entradas, lunes y miércoles)')
    check(len({x['grupo'] for x in its if x['grupo']}) == 2, 'un grupo nuevo por día de bloque')
    check(page.input_value('#pcNombre') == 'Lumbalgia fase 1', 'abre el plan creado')

    # vista Plantillas
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.wait_for_timeout(200)
    check('Lumbalgia fase 1' in page.locator('#main').inner_text(), 'aparece en la pantalla Plantillas')
    page.get_by_role('button', name='Editar', exact=True).click(); page.wait_for_selector('#plNombre'); page.wait_for_timeout(300)
    check(page.locator('.pc-semana .pc-dia').count() == 7 and page.locator('#plDurN').count() == 1 and page.locator('.pc-libre').count() == 1, 'una sola pantalla de edición: nombre, duración, «a elegir» y 7 días')
    page.fill('#plNombre', 'Lumbalgia A'); page.fill('#plDurN', '3'); page.locator('#plDurN').blur(); page.wait_for_timeout(400)
    check(st()['plantillas'][0]['nombre'] == 'Lumbalgia A' and st()['plantillas'][0]['semanas'] == 3, 'renombrar y cambiar duración desde la misma pantalla')
    page.get_by_role('button', name='← Volver a las plantillas').click(); page.wait_for_selector('#plBuscar')
    page.get_by_role('button', name='Usar con pacientes…').click(); page.wait_for_selector('#apIni')
    check(page.locator('#modal #apTpl').count() == 0, 'ya no hay selector de plantilla')
    check(page.locator('.apPac:checked').count() == 0, 'sin paciente marcado al venir de Plantillas')
    page.get_by_role('button', name='Crear plan', exact=True).click(); page.wait_for_timeout(200)
    check(page.locator('#apIni').count() == 1, 'sin pacientes no deja crear el plan')
    page.fill('#apBuscarP', 'zzzz'); check(page.locator('.apPacItem:visible').count() == 0, 'el buscador de pacientes filtra')
    page.fill('#apBuscarP', ''); page.locator('.apPac').first.check(); page.fill('#apIni', '2031-02-03'); page.fill('#apDurN', '1')
    page.get_by_role('button', name='Crear plan', exact=True).click(); page.wait_for_timeout(300)
    check(len([x for x in st()['planes'] if x['inicio'] == '2031-02-03' and len(x['items']) == 3]) == 1, 'aplicar desde Plantillas a un paciente')
    # varios pacientes a la vez
    page.evaluate("() => { db.patients.push({id:'p2', nombre:'Ana', apellidos:'Zubiri', fechaAlta:'2026-01-01', telefono:'', email:'', observaciones:''}); save(); }"); page.wait_for_timeout(300)
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.wait_for_selector('#plBuscar')
    page.get_by_role('button', name='Usar con pacientes…').click(); page.wait_for_selector('#apIni')
    page.get_by_role('button', name='Marcar visibles', exact=True).click()
    npac = page.locator('.apPac:checked').count()
    check(npac >= 2 and 'seleccionados' in page.locator('#apContador').inner_text(), 'marcar visibles selecciona a varios pacientes')
    page.fill('#apIni', '2032-03-01'); page.fill('#apDurN', '1')
    page.get_by_role('button', name='Crear plan', exact=True).click(); page.wait_for_timeout(400)
    check(len({x['patientId'] for x in st()['planes'] if x['inicio'] == '2032-03-01'}) == npac, 'el plan se crea para todos los pacientes marcados')
    # buscador de plantillas: por nombre, bloque y ejercicio
    pl = st()['plantillas'][0]
    ej = next(e['nombre'] for e in st()['exercises'] if e['id'] == pl['items'][0]['exerciseId'])
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.wait_for_selector('#plBuscar')
    page.fill('#plBuscar', ej.split()[0]); check(page.locator('.plItem:visible').count() == 1, 'buscar por ejercicio encuentra la plantilla')
    page.fill('#plBuscar', 'Lumbalgia'); check(page.locator('.plItem:visible').count() == 1, 'buscar por nombre')
    page.fill('#plBuscar', 'qqqqq'); check(page.locator('.plItem:visible').count() == 0 and page.locator('#plNada').is_visible(), 'sin coincidencias, avisa')
    # pacientes con la plantilla
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.wait_for_selector('#plBuscar')
    check(len([x for x in st()['planes'] if x['plantillaId'] == st()['plantillas'][0]['id']]) >= 3, 'cada plan recuerda con qué plantilla se creó')
    page.get_by_role('button', name='Pacientes (').click(); page.wait_for_selector('#plaBuscar')
    check(page.locator('.plaItem').count() >= 1, 'lista de pacientes con la plantilla')
    page.fill('#plaBuscar', 'qqqq'); check(page.locator('.plaItem:visible').count() == 0 and page.locator('#plaNada').is_visible(), 'buscador de pacientes de la plantilla')
    page.fill('#plaBuscar', page.locator('.plaItem strong').first.inner_text().split(',')[0]); check(page.locator('.plaItem:visible').count() >= 1, 'buscar por nombre encuentra al paciente')
    page.locator('#modal button.ghost', has_text='Cerrar').click()
    # editar el contenido no cambia los planes ya creados
    n_plan = json.dumps(st()['planes']); n_it = len(st()['plantillas'][0]['items'])
    page.get_by_role('button', name='Editar', exact=True).click(); page.wait_for_selector('#plNombre')
    page.locator('.pc-semana .pc-dia').nth(1).get_by_role('button', name='+ Añadir').click(); page.wait_for_selector('#acLibre')
    check('Martes' in page.locator('#modal h3').inner_text(), 'Añadir en el martes')
    page.locator('#modal .exCheck').first.check(); page.fill('#acLibre', 'Paseo suave'); page.fill('#acNota', '10 min')
    page.locator('#modal').get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(400)
    check(len(st()['plantillas'][0]['items']) == n_it + 2 and any(i['dia'] == 2 and i['nota'] == '10 min' for i in st()['plantillas'][0]['items']), 'añadir ejercicio y texto libre a un día de la plantilla')
    page.locator('.pc-semana .pc-dia').nth(1).get_by_role('button', name='Editar', exact=True).click(); page.wait_for_selector('#modal .dc-u')
    check(page.locator('#modal .dc-u').count() == 2 and page.locator('#modal input[type=search]').count() == 1, 'Editar un día abre la misma ventana que en el plan en casa (2 unidades)')
    page.locator('#modal .dc-u').nth(0).get_by_role('button', name='Bajar').click(); page.wait_for_timeout(300)
    page.locator('#modal .dc-u').nth(0).get_by_role('button', name='Quitar').click(); page.wait_for_timeout(300)
    check(len(st()['plantillas'][0]['items']) == n_it + 1 and page.locator('#modal').count() == 1, 'quitar de la plantilla sin cerrar la ventana')
    page.locator('#modal button.ghost', has_text='Cerrar').click()
    page.locator('.pc-semana .pc-dia').nth(1).get_by_role('button', name='Vaciar').click(); page.wait_for_timeout(300)
    check(len(st()['plantillas'][0]['items']) == n_it, 'Vaciar un día de la plantilla')
    check(json.dumps(st()['planes']) == n_plan, 'los planes de los pacientes no cambian')
    page.get_by_role('button', name='← Volver a las plantillas').click()
    # borrar ejercicio limpia plantillas
    page.evaluate("delEj('e3')"); page.wait_for_timeout(300)
    check(all(i['exerciseId'] != 'e3' for i in st()['plantillas'][0]['items']), 'borrar ejercicio lo quita de las plantillas')
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.get_by_role('button', name='Eliminar').click(); page.wait_for_timeout(300)
    check(st()['plantillas'] == [], 'eliminar plantilla')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
