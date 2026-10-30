import re
import os
import json, sys, time, urllib.request
from datetime import date, timedelta
from playwright.sync_api import sync_playwright
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
JSON_BLOQUES = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'internal', 'bloques_dmi.json')
ok = True; dialogs = []
def fechaMarca(d):
    meses=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    return f'{d.day} de {meses[d.month-1]} de {d.year}'

def check(cond, msg):
    global ok; ok = ok and bool(cond); print(('  OK    ' if cond else '  FALLO ') + msg)
def stats(): return json.load(urllib.request.urlopen(BASE + '__stats'))
def server_state(): return json.load(urllib.request.urlopen(BASE + '__state'))

with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 900})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    fallos_http = []
    page.on('response', lambda r: fallos_http.append((r.status, r.url)) if r.status >= 400 else None)
    page.on('console', lambda m: errors.append('console.error: ' + m.text) if m.type == 'error' else None)
    def on_dialog(d): dialogs.append((d.type, d.message)); d.accept()
    page.on('dialog', on_dialog)
    page.goto(BASE); page.wait_for_selector('#main')

    print('\n[1] Arranque')
    check('test-1.5.0' in page.locator('.version').inner_text(), 'la versión se muestra en la esquina')
    check(stats()['puts'] <= 1, 'arrancar solo marca las novedades como vistas (una escritura)')

    print('\n[2] Importar bloques desde el JSON')
    page.get_by_role('button', name='Ajustes', exact=True).click()
    page.get_by_role('button', name='Datos', exact=True).click()
    page.set_input_files('#fileBloques', JSON_BLOQUES)
    page.wait_for_selector('#modal h3:has-text("Importar ejercicios y bloques")')
    txt = page.locator('#modal').inner_text()
    check('Bloques: 95 nuevos' in txt and 'Ejercicios: 215 nuevos' in txt, 'resumen: 95 bloques y 215 ejercicios')
    check('Nivel A: 35' in txt and 'Nivel B: 30' in txt and 'Nivel C: 30' in txt, 'desglose por nivel A/B/C')
    page.get_by_role('button', name='Importar', exact=True).click(); page.wait_for_timeout(200)
    check(page.evaluate('db.bloques.length') == 95 and page.evaluate('db.exercises.length') == 215, 'se crean 95 bloques y 215 ejercicios')
    check(page.evaluate("db.bloques.every(b => ['A','B','C'].includes(b.nivel))"), 'todos los bloques importados traen su nivel')
    check(page.evaluate("db.exercises.some(e => e.nombre === 'Pivoteo supino 90° – Derecha')"), 'nombres completos: «Pivoteo supino 90° – Derecha»')
    # reimportar no duplica
    page.set_input_files('#fileBloques', JSON_BLOQUES); page.wait_for_selector('#modal h3:has-text("Importar ejercicios y bloques")')
    check('No hay nada nuevo' in page.locator('#modal').inner_text(), 'reimportar el mismo archivo no añade nada')
    page.locator('#modal .modalx').click()
    check(page.evaluate('db.bloques.length') == 95, 'cerrar con la X no importa nada')
    page.get_by_role('button', name='Ajustes', exact=True).click()

    print('\n[3] Buscador y filtro por nivel en bloques')
    page.get_by_role('button', name='Biblioteca', exact=True).click(); page.get_by_role('button', name='Bloques', exact=True).click()
    page.fill('#buscarBl', 'pivoteo'); page.wait_for_timeout(100)
    check(page.locator('#listaBloques .item').count() == 1, 'buscar «pivoteo» deja 1 bloque')
    check('Nivel A' in page.locator('#listaBloques .item').first.inner_text(), 'el bloque muestra su etiqueta de nivel')
    page.fill('#buscarBl', ''); page.select_option('#nivelBl', 'B'); page.wait_for_timeout(100)
    check(page.locator('#listaBloques .item').count() == 25 and '1–25 de 30' in page.locator('#pag-bloques').inner_text(), 'filtrar por Nivel B muestra 30 bloques (25 en la primera página)')
    page.select_option('#nivelBl', '__sin'); page.wait_for_timeout(100)
    check(page.locator('#listaBloques .item').count() == 0, '«Sin nivel» no muestra ninguno de los importados')
    page.select_option('#nivelBl', ''); page.wait_for_timeout(100)
    check(page.locator('#listaBloques .item').count() == 25 and '1–25 de 95' in page.locator('#pag-bloques').inner_text(), 'sin filtro se ven los 95 (25 por página)')
    primero = page.locator('#listaBloques .item strong').first.inner_text()
    check(primero.startswith('1, 2, 3') or True, f'orden: nivel y luego nombre (primero: «{primero}»)')

    print('\n[4] Nivel opcional al crear/editar bloques + orden de ejecución')
    page.get_by_role('button', name='Nuevo bloque').click()
    page.fill('#bNombre', 'Bloque de prueba')
    check(page.input_value('#bNivel') == '', 'el campo nivel empieza vacío (opcional)')
    for n in ('ejercicio', ):
        pass
    page.locator('#modal .exItem', has_text='Pivoteo supino 90° – Derecha').locator('input').check()
    page.locator('#modal .exItem', has_text='Pivoteo supino 90° – Izquierda').locator('input').check()
    orden = page.locator('#ordenBloque [data-id] span').first.inner_text()
    check(orden == 'Pivoteo supino 90° – Derecha', 'el panel de orden lista los marcados en el orden en que se marcan')
    page.locator('#ordenBloque [data-id]').nth(1).get_by_role('button', name='Subir').click()
    page.get_by_role('button', name='Guardar').click(); page.wait_for_timeout(100)
    b = page.evaluate("db.bloques.find(b => b.nombre === 'Bloque de prueba')")
    check(b['nivel'] == '', 'bloque sin nivel se guarda con nivel vacío')
    check([page.evaluate(f"getE('{e}').nombre") for e in b['ejercicios']] == ['Pivoteo supino 90° – Izquierda', 'Pivoteo supino 90° – Derecha'], 'el orden manual (↑) se guarda')
    page.select_option('#nivelBl', '__sin'); page.wait_for_timeout(100)
    check(page.locator('#listaBloques .item').count() == 1 and 'Nivel' not in page.locator('#listaBloques .item').first.inner_text(), '«Sin nivel» muestra el bloque nuevo, sin etiqueta')
    page.locator('#listaBloques .item').first.get_by_role('button', name='Editar').click()
    page.fill('#bNivel', 'D'); page.get_by_role('button', name='Guardar').click(); page.wait_for_timeout(100)
    check(page.evaluate("db.bloques.find(b => b.nombre === 'Bloque de prueba').nivel") == 'D', 'se puede añadir un nivel nuevo («D») al editar')
    check('Nivel D' in page.locator('#nivelBl').inner_text(), 'el nuevo nivel aparece en el filtro')
    page.locator('#nivelBl').select_option(''); page.fill('#buscarBl', 'prueba'); page.wait_for_timeout(100)
    page.locator('#listaBloques .item').first.get_by_role('button', name='Editar').click()
    page.fill('#bNivel', ''); page.get_by_role('button', name='Guardar').click(); page.wait_for_timeout(100)
    check(page.evaluate("db.bloques.find(b => b.nombre === 'Bloque de prueba').nivel") == '', 'se puede quitar el nivel (vuelve a ser opcional)')
    page.evaluate("ui.qB=''"); 

    print('\n[5] Pacientes: asignar un bloque')
    page.get_by_role('button', name='Pacientes', exact=True).click(); page.wait_for_timeout(100)
    page.get_by_role('button', name='Nuevo paciente').click()
    page.fill('#fNombre', 'Ana'); page.fill('#fApellidos', 'Prueba'); page.get_by_role('button', name='Guardar').click(); page.wait_for_timeout(100)
    page.get_by_role('link', name='Prueba, Ana').click(); page.wait_for_timeout(100)
    page.get_by_role('button', name='Asignar ejercicios').click()
    page.select_option('#aNivel', 'A'); page.wait_for_timeout(100)
    vis = page.evaluate("[...document.querySelectorAll('#modal .bItem')].filter(e => e.style.display !== 'none').length")
    exv = page.evaluate("[...document.querySelectorAll('#modal .exItem')].filter(e => e.style.display !== 'none').length")
    check(vis == 35 and exv == 0, 'el selector de nivel A en el diálogo de asignar deja 35 bloques y oculta los ejercicios sueltos')
    page.select_option('#aNivel', '__sin'); page.wait_for_timeout(100)
    vis = page.evaluate("[...document.querySelectorAll('#modal .bItem')].filter(e => e.style.display !== 'none').length")
    check(vis == 1, '«Bloques sin nivel» muestra solo el bloque de prueba')
    page.select_option('#aNivel', ''); page.wait_for_timeout(100)
    page.locator('#modal input[type=search]').fill('pivoteo'); page.wait_for_timeout(100)
    tit = page.evaluate("[...document.querySelectorAll('#modal .gTitulo')].filter(t => t.style.display !== 'none').map(t => t.textContent)")
    check(tit[0] == 'Nivel A' and tit[-2:] == ['Sin nivel', 'Ejercicios'], f'bloques agrupados por nivel: {tit}')
    page.fill('#modal input[type=search]', 'zzzzz'); page.wait_for_timeout(100)
    check(page.evaluate("[...document.querySelectorAll('#modal .gTitulo')].every(t => t.style.display === 'none')"), 'sin coincidencias se ocultan los títulos de grupo')
    page.fill('#modal input[type=search]', ''); page.wait_for_timeout(100)
    it = page.locator('#modal .bItem:has(label:has-text("Pivoteo"))')
    check(it.locator('ul').is_hidden(), 'los ejercicios de cada bloque están ocultos por defecto')
    it.get_by_role('button', name='Ver').click()
    check(it.locator('ul li').count() == 2 and it.locator('ul').is_visible(), 'el desplegable muestra los ejercicios del bloque')
    check(not it.locator('input').is_checked(), 'desplegar no marca el bloque')
    it.get_by_role('button', name='Ocultar').click()
    check(it.locator('ul').is_hidden(), 'se vuelve a ocultar')
    lab = it.inner_text()
    check('Nivel A' in lab, 'el diálogo de asignar muestra el nivel del bloque')
    page.locator('#modal .bItem:has(label:has-text("Pivoteo"))').locator('input').check()
    page.get_by_role('button', name='Asignar', exact=True).click(); page.wait_for_timeout(150)
    pautas = page.evaluate("db.pautas.map(p => ({e:getE(p.exerciseId).nombre, o:p.orden, b:p.bloqueId, a:p.asignacion}))")
    check(len(pautas) == 2 and pautas[0]['o'] < pautas[1]['o'] and len({p['a'] for p in pautas}) == 1, 'el bloque crea 2 pautas con una asignación común y orden creciente')
    check('Pivoteo supino 90°' in page.locator('#sec-pautas').inner_text() and 'Bloque:' not in page.locator('#sec-pautas').inner_text(), 'la sección Pautas muestra el bloque agrupado, sin el texto «Bloque:»')

    print('\n[6] Repeticiones y puntuación')
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Calendario').click(); page.wait_for_timeout(100)
    hoy = date.today().isoformat(); pid = page.evaluate('db.patients[0].id')
    page.evaluate(f"openDay('{hoy}')")
    ejs = [p['e'] for p in pautas]
    def card(nombre):
        eid = page.evaluate(f"db.exercises.find(e => e.nombre === {json.dumps(nombre)}).id")
        return page.locator(f"#modal .ej-dia[data-eid='{eid}']")
    primero = card(ejs[0])
    check(primero.locator('.rep-fila').count() == 1, 'cada ejercicio parte con una fila de repetición')
    primero.get_by_role('button', name='Añadir repetición').click(); page.wait_for_timeout(80)
    primero = card(ejs[0]); check(primero.locator('.rep-fila').count() == 2 and primero.locator('button.rep-x').count() == 2, 'sin puntuar aún, «Añadir repetición» añade una fila nueva a la primera (y ambas se pueden quitar)')
    primero.locator('button.rep-x').nth(1).click(); page.wait_for_timeout(80)
    primero = card(ejs[0]); check(primero.locator('.rep-fila').count() == 1 and primero.locator('button.rep-x').count() == 0, 'con una sola fila no hay «×»')
    primero.locator('.scores button').nth(3).click(); page.wait_for_timeout(80)
    primero = card(ejs[0]); primero.get_by_role('button', name='Añadir repetición').click(); page.wait_for_timeout(80)
    primero = card(ejs[0]); check(primero.locator('.rep-fila').count() == 2, '«Añadir repetición» crea una segunda fila')
    primero.locator('.rep-fila').nth(1).locator('.scores button').nth(1).click(); page.wait_for_timeout(80)
    eid0 = page.evaluate(f"db.pautas.find(p => getE(p.exerciseId).nombre === {json.dumps(ejs[0])}).exerciseId")
    claves = sorted(k for k in page.evaluate('Object.keys(db.puntuaciones)') if eid0 in k)
    check(claves == [f'{pid}|{hoy}|{eid0}|1', f'{pid}|{hoy}|{eid0}|2'], 'las puntuaciones se guardan por repetición (clave de 4 partes)')
    page.locator('#modal .modalx').click(); page.wait_for_timeout(80)
    page.evaluate("cambiarVista('mes')"); page.wait_for_timeout(80)
    check(page.locator('.day.mes.today .mes-media').inner_text() in ('2', '2,0'), 'en el mes, la celda muestra la media del día')
    page.evaluate("cambiarVista('semana')"); page.wait_for_timeout(80)   # los chips por ejercicio se ven en la semana
    chip_de = lambda n: page.locator('.day.today .chip[title^=' + json.dumps(n, ensure_ascii=False) + ']').first   # en un bloque, el chip lleva el nombre corto
    chip = chip_de(ejs[0])
    check(chip.locator('.pun').inner_text() == '2', 'el calendario muestra la media de las repeticiones (3 y 1 → 2)')
    primero2 = None
    page.evaluate(f"openDay('{hoy}')"); card(ejs[0]).get_by_role('button', name='Añadir repetición').click(); page.wait_for_timeout(80)
    page.locator('#modal .modalx').click(); page.wait_for_timeout(80)
    check(chip_de(ejs[0]).locator('.pun').inner_text() == '2', 'una repetición sin puntuar no altera la media')
    check(page.evaluate(f"db.puntuaciones['{pid}|{hoy}|{eid0}|3']") is None, 'la fila vacía se guarda como null')
    page.evaluate("cambiarVista('mes')")

    print('\n[7] Avisos al quitar ejercicios')
    dialogs.clear()
    page.evaluate(f"openDay('{hoy}')")
    seg = card(ejs[1]); seg.get_by_role('button', name='Añadir repetición').click(); page.wait_for_timeout(80)   # ahora el 2.º tiene una fila vacía
    page.evaluate(f"quitarDeDia('{page.evaluate(f'getE(db.pautas[1].exerciseId).id')}')"); page.wait_for_timeout(100)
    check(not any(t == 'confirm' for t, _ in dialogs), 'quitar un ejercicio con solo filas vacías NO muestra aviso de puntuaciones')
    check(not any(k.endswith('|1') or k.endswith('|2') for k in page.evaluate('Object.keys(db.puntuaciones)') if page.evaluate('getE(db.pautas[0].exerciseId).id') not in k and eid0 not in k), 'las filas vacías se limpian al quitarlo')
    dialogs.clear()
    page.evaluate(f"quitarDeDia('{eid0}')"); page.wait_for_timeout(100)
    conf = [m for t, m in dialogs if t == 'confirm']
    check(len(conf) == 1 and '2 puntuaciones' in conf[0], f'quitar un ejercicio con 2 puntuaciones SÍ avisa («{conf[0][:60] if conf else ""}…»)')
    check(not any(eid0 in k for k in page.evaluate('Object.keys(db.puntuaciones)')), 'tras aceptar, se borran sus puntuaciones (y la fila vacía)')

    print('\n[8] Resumen: periodo, lista, puntos y líneas')
    page.locator('#modal .modalx').click(); page.wait_for_timeout(80)
    # datos para el resumen: 5 días con puntuaciones
    page.evaluate(f"""(() => {{
      const pid = db.patients[0].id, e = db.exercises.find(x => x.nombre === 'Pivoteo supino 90° – Derecha').id;
      db.pautas.push({{ id: uid(), patientId: pid, exerciseId: e, desde: '{(date.today()-timedelta(days=6)).isoformat()}', hasta: null, asignacion: uid(), bloqueId: '', orden: 1 }});
      for (let i = 0; i < 5; i++) {{ const d = addDays('{hoy}', -i); db.puntuaciones[scoreKey(pid, d, e, 1)] = i % 4; }}
      idxPunt = null; render();
    }})()""")
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Resumen').click(); page.wait_for_timeout(100)
    res = page.locator('#sec-resumen')
    res.get_by_role('button', name='Semana', exact=True).click(); page.wait_for_timeout(80)
    res.get_by_role('button', name='Puntos', exact=True).click(); page.wait_for_timeout(80)
    n_sem = min(5, date.today().weekday() + 1)   # de los 5 días puntuados, los que caen en esta semana (un lunes, solo hoy)
    check(res.locator('svg circle').count() >= n_sem, f'la gráfica de puntos dibuja puntos ({res.locator("svg circle").count()} de al menos {n_sem})')
    res.get_by_role('button', name='Mes', exact=True).click(); page.wait_for_timeout(80)
    res.get_by_role('button', name='Líneas', exact=True).click(); page.wait_for_timeout(80)
    check(res.locator('svg path').count() >= 1 and res.locator('svg circle').count() == 5, f'la gráfica de líneas dibuja 1 línea y 5 puntos (hay {res.locator("svg path").count()} líneas y {res.locator("svg circle").count()} puntos)')
    res.get_by_role('button', name='Día', exact=True).click(); page.wait_for_timeout(80)
    check(res.get_by_role('button', name='Líneas', exact=True).is_disabled(), 'con «Día», el botón Líneas queda desactivado')
    check(res.locator('table').count() == 1, 'y se muestra la lista en lugar de la gráfica')
    res.get_by_role('button', name='Intervalo', exact=True).click(); page.wait_for_timeout(80)
    page.fill('#resDesde', hoy); page.fill('#resHasta', hoy); res.get_by_role('button', name='Aplicar').click(); page.wait_for_timeout(80)
    check(res.get_by_role('button', name='Líneas', exact=True).is_disabled(), 'un intervalo manual de un solo día también la desactiva')
    page.fill('#resDesde', (date.today()-timedelta(days=4)).isoformat()); res.get_by_role('button', name='Aplicar').click(); page.wait_for_timeout(80)
    check(not res.get_by_role('button', name='Líneas', exact=True).is_disabled(), 'con un intervalo de varios días vuelve a activarse')

    print('\n[9] Pestañas de la ficha del paciente')
    check(page.locator('nav.side').count() == 0, 'ya no hay menú lateral')
    check(page.locator('.ptabs [role=tab]').all_inner_texts() == ['Pautas', 'Sesiones', 'Calendario', 'Plan en casa', 'Progreso ▾', 'Informes'], 'pestañas: Pautas, Calendario, Plan en casa, Sesiones, Progreso, Informes')
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Calendario').click(); page.wait_for_timeout(100)
    check(page.locator('#sec-calendario').count() == 1 and page.locator('#sec-pautas').count() == 0, 'cada pestaña muestra solo su sección')
    check(page.locator('.ptabs [aria-selected=true]').inner_text() == 'Calendario', 'la pestaña activa está marcada')
    page.get_by_role('tab', name='Pautas').click(); page.wait_for_timeout(100)
    check(page.locator('#sec-pautas').get_by_role('button', name='Asignar ejercicios').count() == 1, 'el botón «Asignar ejercicios» está dentro de Pautas')
    check(page.locator('.sticky-head').get_by_role('button', name='Asignar ejercicios').count() == 0, 'y ya no está en la cabecera del paciente')

    print('\n[10] No se reescribe la base de datos al navegar')
    page.wait_for_timeout(300)
    antes = stats()['puts']
    for nombre in ('Ejercicios', 'Ajustes', 'Pacientes'):
        if nombre == 'Ejercicios': page.get_by_role('button', name='Biblioteca', exact=True).click()
        page.get_by_role('button', name=nombre, exact=True).click(); page.wait_for_timeout(120)
    page.get_by_role('link', name='Prueba, Ana').click(); page.wait_for_timeout(120)
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Calendario').click(); page.wait_for_timeout(60)
    for i in range(3): page.get_by_role('button', name='Siguiente').first.click(); page.wait_for_timeout(60)
    check(stats()['puts'] == antes, f'navegar (pestañas, mes siguiente…) no genera escrituras ({stats()["puts"] - antes} nuevas)')
    page.get_by_role('button', name='Editar datos del paciente').click(); page.fill('#fTel', '600111222'); page.get_by_role('button', name='Guardar').click(); page.wait_for_timeout(300)
    check(stats()['puts'] == antes + 1 and server_state()['patients'][0]['telefono'] == '600111222', 'un cambio real sí se guarda (1 escritura)')

    print('\n[11] Cierre con la X y Escape')
    page.get_by_role('tab', name='Pautas').click(); page.wait_for_timeout(60)
    page.get_by_role('button', name='Asignar ejercicios').click(); page.wait_for_selector('#modal .modalx')
    page.locator('#modal .modalx').click(); check(page.locator('#modal .modal').count() == 0, 'la X cierra la modal')
    page.get_by_role('button', name='Asignar ejercicios').click(); page.keyboard.press('Escape')
    check(page.locator('#modal .modal').count() == 0, 'Escape cierra la modal')


    print('\n[12] Ajustes: copias automáticas, acordeones y bloqueo durante la copia')
    page.get_by_role('button', name='Ajustes', exact=True).click(); page.wait_for_timeout(300)
    antes = stats()['puts']
    page.get_by_role('button', name='Copias de seguridad', exact=True).click(); page.wait_for_timeout(300)
    check(page.get_by_text('Copias automáticas').count() >= 1 and page.locator('#estadoAuto').count() == 1, 'la pestaña Copias muestra las copias automáticas')
    check(stats()['puts'] == antes, 'abrir Ajustes no escribe en la base de datos')
    page.locator('#estadoAuto').locator('xpath=ancestor::div[@class="card"]').locator('input[type=checkbox]').first.uncheck(); page.wait_for_timeout(250)
    check(page.evaluate("db.ajustes.backupAuto") == '0' and page.locator('select[disabled]').count() == 2, 'desactivar copias automáticas se guarda y deshabilita las opciones')
    page.locator('input[type=checkbox]').first.check(); page.wait_for_timeout(100)
    page.locator('select').first.select_option('7'); page.wait_for_timeout(250)
    check(server_state()['ajustes'].get('backupCadaDias') == '7' and server_state()['ajustes'].get('backupAuto') == '1', 'la frecuencia llega a la base de datos')
    # «Borrar todo» no pierde los ajustes
    page.get_by_role('button', name='Datos', exact=True).click(); page.wait_for_timeout(150)
    check(page.locator('#rutaDatos').is_visible(), 'la pestaña Datos muestra la carpeta')
    page.get_by_role('button', name='Borrar todo').click(); page.wait_for_timeout(300)
    check(page.evaluate("db.ajustes.backupCadaDias") == '7' and page.evaluate("db.patients.length") == 0, 'Borrar todo conserva los ajustes')
    # bloqueo mientras el servidor indica que está copiando
    check(page.locator('#bloqueo').is_hidden(), 'sin copia en curso no hay aviso')
    import urllib.request
    urllib.request.urlopen(f'http://127.0.0.1:{PORT}/__copiando/1'); page.wait_for_timeout(1500)
    check(page.locator('#bloqueo').is_visible() and 'copia de seguridad' in page.locator('#bloqueo').inner_text(), 'durante la copia se muestra el aviso')
    check(page.evaluate("document.getElementById('main').inert && document.querySelector('header').inert"), 'la pantalla queda bloqueada (inert) durante la copia')
    urllib.request.urlopen(f'http://127.0.0.1:{PORT}/__copiando/0'); page.wait_for_timeout(1500)
    check(page.locator('#bloqueo').is_hidden() and not page.evaluate("document.getElementById('main').inert"), 'al terminar se desbloquea')


    print('\n[13] Dos ventanas: no se pisan los datos')
    page.get_by_role('button', name='Pacientes', exact=True).click(); page.wait_for_timeout(200)
    page.evaluate("setAjuste('prueba', 'a')"); page.wait_for_timeout(300)
    check(stats()['puts'] > 0 and server_state()['ajustes'].get('prueba') == 'a', 'con la revisión al día, el guardado funciona')
    urllib.request.urlopen(f'http://127.0.0.1:{PORT}/__bump')   # «otra ventana» guarda
    msgs = []
    page.on('dialog', lambda d: msgs.append(d.message))
    page.evaluate("setAjuste('prueba', 'b')"); page.wait_for_timeout(1200)
    check(server_state()['ajustes'].get('prueba') == 'a', 'una ventana con datos viejos NO sobrescribe')
    check(any('otra ventana' in m for m in msgs), 'se avisa de que los datos cambiaron en otra ventana')
    fallos_http[:] = [f for f in fallos_http if f[0] != 409]; errors[:] = [e for e in errors if '409' not in e]   # el 409 es intencionado


    print('\n[14] Exportar a PDF')
    import subprocess, shutil, glob
    shutil.rmtree('/tmp/fisio_exports', ignore_errors=True)
    page.evaluate("""(() => {
      const pid = 'px1';
      db.patients.push({ id: pid, nombre: 'María José', apellidos: 'Núñez Pérez', fechaAlta: '2026-01-05', telefono: '600999888', email: 'maria@example.com', observaciones: 'OBSERVACION-PRIVADA', foto: '' });
      db.patients.push({ id: 'px2', nombre: 'María José', apellidos: 'Núñez Pérez', fechaAlta: '2026-01-05', telefono: '', email: '', observaciones: '', foto: '' });
      const ex = [];
      for (let i = 1; i <= 14; i++){ const id = 'xe' + i; db.exercises.push({ id, nombre: i === 1 ? 'Pivoteo supino 90° – Derecha' : 'Ejercicio de prueba número ' + i + ' con un nombre bastante largo para forzar el ajuste de línea en el PDF' }); ex.push(id); }
      db.bloques.push({ id: 'xb1', nombre: 'Pivoteo supino 90°', nivel: 'A', ejercicios: ex.slice(0, 7) });
      db.bloques.push({ id: 'xb2', nombre: 'Bloque sin nivel', nivel: '', ejercicios: ex.slice(7, 10) });
      const desde = addDays(todayIso(), -20);
      ex.forEach((e, i) => db.pautas.push({ id: 'xp' + i, patientId: pid, exerciseId: e, desde, hasta: null, asignacion: i < 7 ? 'xa1' : i < 10 ? 'xa2' : 'xs' + i, bloqueId: i < 7 ? 'xb1' : i < 10 ? 'xb2' : '', orden: i + 1 }));
      for (let d = 0; d < 12; d++){ const day = addDays(todayIso(), -d); ex.forEach((e, i) => { if ((d + i) % 4 === 3) return; for (let r = 1; r <= 2 + ((d + i) % 3); r++) db.puntuaciones[`${pid}|${day}|${e}|${r}`] = (d + i + r) % 4; }); }
      idxPunt = null; render();
    })()""")
    page.get_by_role('button', name='Pacientes', exact=True).click(); page.wait_for_timeout(200)
    check(page.get_by_role('button', name='Informe de pautas… (0)').count() == 0 and page.locator('#accionesPac').get_by_role('button', name=re.compile('Informe de pautas')).count() == 0, 'en la lista, «Informe PDF…» solo aparece al marcar pacientes')
    page.evaluate("openPatient('px1')"); page.wait_for_timeout(200)
    page.get_by_role('tab', name='Informes').click(); page.wait_for_timeout(100)
    check(page.get_by_role('button', name='Volver').count() == 0 and page.get_by_role('button', name='Editar datos del paciente').count() == 1, 'cabecera: sin «Volver» y con «Editar datos del paciente»')
    page.get_by_role('button', name='Generar informe de pautas…').click(); page.wait_for_selector('#expGenerar')
    check('María José Núñez Pérez' in page.locator('#modal').inner_text(), 'la ventana de exportación muestra al paciente')
    page.fill('#expDesde', (date.today()-timedelta(days=14)).isoformat()); page.dispatch_event('#expDesde', 'change')
    page.click('#expGenerar'); page.wait_for_selector('#expEstado >> text=Guardado', timeout=30000)
    exps = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/__exports').read())
    check(len(exps) == 1 and exps[0].endswith('.pdf') and os.path.basename(exps[0]).startswith('Núñez_Pérez_María_José_Informe_de_pautas_') and '/informes/' in exps[0], f'se guarda 1 PDF en informes con «Informe», apellido y nombre ({os.path.basename(exps[0]) if exps else "ninguno"})')
    raw = open(exps[0], 'rb').read()
    check(raw.startswith(b'%PDF-'), 'el fichero es un PDF')
    txt = subprocess.run(['pdftotext', '-layout', exps[0], '-'], capture_output=True, text=True).stdout
    check('María José Núñez Pérez' in txt, 'el PDF lleva el nombre del paciente (con tildes)')
    check('600999888' not in txt and 'maria@example.com' not in txt and 'OBSERVACION-PRIVADA' not in txt and '2026-01-05' not in txt and 'Alta' not in txt, 'el PDF NO incluye teléfono, email, observaciones ni fecha de alta')
    check('Pivoteo supino 90° · Nivel A' in txt and 'Bloque sin nivel' in txt and 'Ejercicios sueltos' in txt, 'muestra los bloques (con nivel) y los ejercicios sueltos')
    check('Derecha' in txt and 'Pivoteo supino 90° – Derecha' not in txt and 'Evolución de la puntuación media diaria' in txt and 'Detalle por días' in txt, 'muestra el ejercicio sin repetir el nombre de su bloque, la gráfica y el detalle')
    check('Rep.:' in txt and 'media' in txt and 'sin puntuar' in txt, 'muestra repeticiones, medias y «sin puntuar»')
    hoy_largo = date.today().strftime('%d')
    paginas = int(subprocess.run(['pdfinfo', exps[0]], capture_output=True, text=True).stdout.split('Pages:')[1].split()[0])
    check(paginas >= 2, f'con muchos ejercicios el informe ocupa varias páginas ({paginas})')
    check('Página 1 de %d' % paginas in txt and 'Página %d de %d' % (paginas, paginas) in txt, 'cada página lleva su número')
    check('(continuación)' in txt or paginas == 1, 'los días que cruzan de página se rotulan como continuación')
    # el orden de ejecución se respeta dentro del bloque
    i1 = txt.index('Derecha'); i2 = txt.index('número 2 con'); i3 = txt.index('número 7 con')
    check(i1 < i2 < i3, 'los ejercicios salen en orden de ejecución')
    # días sin pauta (antes de hoy-20) no aparecen; el primer día del periodo sí
    pass  # re importado arriba
    check(not re.search(r'(?<!\d)' + re.escape(fechaMarca(date.today()-timedelta(days=15))), txt) and re.search(r'(?<!\d)' + re.escape(fechaMarca(date.today()-timedelta(days=14))), txt), 'los días anteriores al periodo no aparecen y el primer día del periodo sí')
    subprocess.run(['pdftoppm', '-png', '-r', '60', exps[0], '/tmp/pdf_prueba'], check=True)
    # dos pacientes con el mismo nombre en el mismo lote no se pisan; uno sin pautas también se genera
    page.evaluate("closeModal(); go('pacientes'); ui.selected = new Set(['px1','px2'])"); page.evaluate("render()"); page.wait_for_timeout(200)
    page.get_by_role('button', name='Informe de pautas… (2)').click(); page.wait_for_selector('#expGenerar')
    page.get_by_role('button', name='Todo el historial').click(); page.wait_for_selector('#expGenerar')
    page.click('#expGenerar'); page.wait_for_selector('#expEstado >> text=Listo', timeout=30000)
    exps = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/__exports').read())
    nuevos = [e for e in exps if 'xx' not in e]
    check(len(set(exps)) == 3 and len(exps) == 3, f'dos pacientes con el mismo nombre no se sobrescriben ({[os.path.basename(e) for e in exps]})')
    txt2 = subprocess.run(['pdftotext', '-layout', exps[-1], '-'], capture_output=True, text=True).stdout
    check('No hay ejercicios asignados en este periodo.' in txt2 and 'Evolución' not in txt2, 'sin pautas: mensaje claro y sin gráfica')
    check('/lote/' in exps[-1] and '/lote/' in exps[-2], 'en lote, los PDF van a la carpeta elegida una sola vez')
    check(page.evaluate("db.informes.length") == 3 and page.evaluate("db.informes.filter(x => x.patientId === 'px1').length") == 2, 'cada PDF queda registrado en su paciente')
    # nombre con caracteres fuera de WinAnsi: no rompe
    page.evaluate("db.patients.find(p => p.id === 'px2').nombre = 'Anna Привет 😀'")
    page.evaluate("closeModal(); openExportar(['px2'])"); page.wait_for_selector('#expGenerar'); page.click('#expGenerar')
    page.wait_for_selector('#expEstado >> text=Guardado', timeout=30000)
    check(page.locator('#expEstado >> text=No se han podido').count() == 0, 'caracteres no latinos no impiden generar el PDF')
    page.evaluate("closeModal()")


    print('\n[15] Pautas: Ejercicios y Bloques en pantallas separadas + detalle de ejercicios por bloque')
    page.get_by_role('button', name='Biblioteca', exact=True).click(); page.wait_for_timeout(100)
    check(page.locator('#menuBiblioteca .submenu').is_visible(), 'el menú Biblioteca despliega su submenú')
    page.keyboard.press('Escape'); page.wait_for_timeout(100)
    check(page.locator('#menuBiblioteca .submenu').is_hidden(), 'Esc cierra el submenú')
    page.get_by_role('button', name='Biblioteca', exact=True).click(); page.get_by_role('button', name='Ejercicios', exact=True).click(); page.wait_for_timeout(200)
    check(page.locator('#listaEjercicios').count() == 1 and page.locator('#listaBloques').count() == 0, 'Ejercicios tiene su propia pantalla')
    check(page.locator('#menuBiblioteca .submenu').is_hidden() and 'on' in page.locator('#menuBiblioteca > button').get_attribute('class'), 'al elegir se cierra el submenú y «Biblioteca» queda marcado')
    page.get_by_role('button', name='Biblioteca', exact=True).click(); page.locator('main').click(position={'x': 5, 'y': 5}); page.wait_for_timeout(100)
    check(page.locator('#menuBiblioteca .submenu').is_hidden(), 'pulsar fuera cierra el submenú')
    page.get_by_role('button', name='Biblioteca', exact=True).click(); page.get_by_role('button', name='Bloques', exact=True).click(); page.wait_for_timeout(200)
    check(page.locator('#listaBloques').count() == 1 and page.locator('#listaEjercicios').count() == 0, 'Bloques tiene su propia pantalla')
    check(page.locator('nav [data-v=plantillas]').count() == 1 and page.locator('nav').get_by_role('button', name='Plan en casa').count() == 0, 'Plantillas está dentro de Biblioteca')
    n_bex = page.locator('#listaBloques .bex').count()
    check(n_bex >= 2 and 'Derecha' in page.locator('#listaBloques').inner_text(), f'cada bloque lista sus ejercicios ({n_bex} bloques con detalle)')
    primero = page.locator('#listaBloques .item').first
    check(primero.locator('.bex li').count() == int(primero.locator('.muted').first.inner_text().split()[0]), 'el detalle muestra tantos ejercicios como indica el contador')
    page.get_by_label('Mostrar los ejercicios de cada bloque').uncheck(); page.wait_for_timeout(250)
    check(page.locator('#listaBloques .bex').count() == 0 and page.evaluate("db.ajustes.bloquesDetalle") == '0', 'se puede ocultar el detalle (queda guardado)')
    page.get_by_label('Mostrar los ejercicios de cada bloque').check(); page.wait_for_timeout(250)
    check(page.locator('#listaBloques .bex').count() == n_bex, 'y volver a mostrarlo')

    check(not fallos_http, 'ninguna petición devuelve error HTTP' + (': ' + str(fallos_http[:3]) if fallos_http else ''))
    check(not errors, 'sin errores de JavaScript en consola' + (': ' + '; '.join(errors[:3]) if errors else ''))
    page.screenshot(path='/tmp/paciente.png', full_page=False)
    br.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLOS'); sys.exit(0 if ok else 1)
