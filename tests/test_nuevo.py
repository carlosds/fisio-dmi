# Pruebas de: contador de pautas, cabecera fija, Personalizar (marca/tema/modos), Hitos y Plan en casa (+PDF).
# Uso: python3 mock_server.py PUERTO seed_nuevo.json &  ;  python3 test_nuevo.py PUERTO
import re, json, os, subprocess, sys, tempfile, urllib.request
from playwright.sync_api import sync_playwright
from PIL import Image
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
EXP = os.path.join(os.environ.get('EXPDIR', '/tmp/fisio_exports'), 'planes')   # exportaciones/planes
ok = True; dialogs = []
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def server_state(): return json.load(urllib.request.urlopen(BASE + '__state'))
tmp = tempfile.mkdtemp()
Image.new('RGBA', (300, 120), (200, 30, 30, 255)).save(f'{tmp}/logo.png')
Image.new('RGBA', (240, 80), (10, 10, 120, 255)).save(f'{tmp}/firma.png')
Image.new('RGB', (50, 50), (0, 128, 0)).save(f'{tmp}/firma.jpg')

with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 800})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.on('dialog', lambda d: (dialogs.append(d.message), d.accept()))
    page.goto(BASE); page.wait_for_selector('#main')

    print('\n[A] Cabecera sin marca y contador de pautas')
    check(page.locator('#marca').inner_text().strip() == '' and page.locator('#marca img').count() == 0, 'sin logo ni nombre, la barra no muestra nada')
    check('Ejercicios de fisioterapia' not in page.locator('header').inner_text(), 'ya no aparece «Ejercicios de fisioterapia»')
    page.locator('#listaPacientes .item a').first.click()
    page.wait_for_selector('#sec-pautas')
    check('(1 bloque / 3 ejercicios)' in page.locator('#sec-pautas h3').inner_text(), 'contador «Pautas (1 bloque / 3 ejercicios)»')

    print('\n[B] Barra superior fija')
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Calendario').click(); page.wait_for_timeout(200)
    page.evaluate('window.scrollTo(0, 600)'); page.wait_for_timeout(200)
    check(abs(page.evaluate("document.querySelector('header').getBoundingClientRect().top")) < 1, 'la barra sigue arriba tras desplazar')

    print('\n[C] Personalizar')
    page.get_by_role('button', name='Ajustes', exact=True).click(); page.wait_for_timeout(200)
    page.fill('#pClinica', 'Clínica Vigo'); page.fill('#pProf', 'Carlos Dabarca'); page.fill('#pCol', '1234')
    page.locator('#pCol').dispatch_event('change'); page.locator('#pClinica').dispatch_event('change'); page.locator('#pProf').dispatch_event('change')
    page.wait_for_timeout(200)
    check('Clínica Vigo' in page.locator('#marca').inner_text(), 'el nombre de la clínica aparece en la barra')
    page.set_input_files('#fileLogo', f'{tmp}/logo.png'); page.wait_for_timeout(500)
    check(page.locator('#marca img').count() == 1, 'el logo aparece en la barra junto al nombre')
    dialogs.clear(); page.set_input_files('#fileFirma', f'{tmp}/firma.jpg'); page.wait_for_timeout(300)
    check(any('PNG' in d for d in dialogs) and not page.evaluate("db.ajustes.profFirma"), 'la firma rechaza archivos que no son PNG')
    page.set_input_files('#fileFirma', f'{tmp}/firma.png'); page.wait_for_timeout(500)
    a = server_state()['ajustes']
    check(a.get('profFirma', '').startswith('data:image/png') and a.get('clinicaLogo', '').startswith('data:image/png') and a.get('profColegiado') == '1234' and a.get('profNombre') == 'Carlos Dabarca', 'logo, firma, profesional y colegiado se guardan')
    page.select_option('#pTema', 'oscuro'); page.wait_for_timeout(200)
    check(page.evaluate("document.documentElement.dataset.theme") == 'dark' and server_state()['ajustes'].get('tema') == 'oscuro', 'modo oscuro')
    fondo = page.evaluate("getComputedStyle(document.body).backgroundColor")
    check(fondo != 'rgb(255, 255, 255)', f'el fondo cambia en oscuro ({fondo})')
    page.screenshot(path=f'{tmp}/oscuro_ajustes.png')
    page.select_option('#pTema', 'claro'); page.wait_for_timeout(150)
    check(page.evaluate("document.documentElement.dataset.theme") == 'light', 'modo claro')

    print('\n[D] Hitos')
    page.get_by_role('button', name='Pacientes', exact=True).click(); page.locator('#listaPacientes .item a').first.click()
    page.wait_for_selector('.ptabs')
    page.get_by_role('tab', name='Progreso').click(); page.get_by_role('menuitem', name='Hitos').click(); page.wait_for_selector('#sec-hitos')
    check(page.locator('.ptabs [role=menuitem]', has_text='Hitos').count() == 1, 'hay una entrada «Hitos» en Progreso')
    (page.get_by_role('button', name='Nuevo hito…').click() if page.locator('#hNota').is_hidden() else None); page.fill('#hFecha', '2026-03-10'); page.fill('#hNota', 'Primera valoración, dolor lumbar'); page.get_by_role('button', name='Añadir hito').click()
    (page.get_by_role('button', name='Nuevo hito…').click() if page.locator('#hNota').is_hidden() else None); page.fill('#hFecha', '2026-05-02'); page.fill('#hNota', 'Alta de la fase aguda'); page.get_by_role('button', name='Añadir hito').click()
    (page.get_by_role('button', name='Nuevo hito…').click() if page.locator('#hNota').is_hidden() else None); page.fill('#hFecha', '2026-05-02'); page.fill('#hNota', 'Segundo hito mismo día'); page.get_by_role('button', name='Añadir hito').click()
    check(page.locator('#listaHitos tbody tr').count() == 3, 'los hitos aparecen en la tabla al añadirlos (varios el mismo día)')
    check('(3)' in page.locator('#hTitulo').inner_text(), 'el título cuenta los hitos')
    check('10 mar 2026' in page.locator('#listaHitos tbody tr').last.inner_text(), 'orden: más reciente primero')
    check(page.locator('#hNota').is_hidden() and page.get_by_role('button', name='Nuevo hito…').count() == 1, 'tras añadir, el formulario se pliega y queda «Nuevo hito…»')
    page.get_by_role('button', name='Nuevo hito…').click(); dialogs.clear(); page.get_by_role('button', name='Añadir hito').click()
    check(any('nota' in d for d in dialogs), 'no permite añadir un hito sin nota')
    page.wait_for_timeout(300); page.fill('#hBuscar', 'lumbar'); page.wait_for_timeout(300)
    check(page.locator('#listaHitos tbody tr').count() == 1 and 'Mostrando 1 de 3' in page.locator('#hCuenta').inner_text(), 'el buscador filtra por notas')
    page.fill('#hBuscar', 'AGUDA'); check(page.locator('#listaHitos tbody tr').count() == 1, 'búsqueda sin distinguir mayúsculas')
    page.fill('#hBuscar', 'zzz'); check('Ninguna nota' in page.locator('#listaHitos').inner_text(), 'sin coincidencias se avisa')
    page.fill('#hBuscar', '')
    page.locator('#listaHitos tr', has_text='Primera valoración').get_by_role('button', name='Editar').click()
    page.fill('#ehFecha', '2026-03-12'); page.fill('#ehNota', 'Valoración inicial corregida'); page.get_by_role('button', name='Guardar', exact=True).click(); page.wait_for_timeout(200)
    check('12 mar 2026' in page.locator('#listaHitos').inner_text() and 'corregida' in page.locator('#listaHitos').inner_text(), 'editar fecha y nota')
    page.locator('#listaHitos tr', has_text='Segundo hito').get_by_role('button', name='Eliminar').click(); page.wait_for_timeout(200)
    check(page.locator('#listaHitos tbody tr').count() == 2, 'eliminar un hito')
    check(len(server_state()['hitos']) == 2 and server_state()['hitos'][0]['patientId'], 'los hitos llegan al servidor')

    print('\n[E] Plan en casa')
    page.get_by_role('tab', name='Plan en casa').click(); page.wait_for_timeout(150)
    check(page.locator('.ptabs [role=tab]', has_text='Plan en casa').count() == 1, 'hay una pestaña «Plan en casa»')
    page.get_by_role('button', name='Nuevo plan').click(); page.wait_for_selector('#pcNombre')
    check(page.locator('#sec-casa button', has_text='Exportar a PDF').is_disabled(), 'sin ejercicios no se puede exportar')
    page.fill('#pcNombre', 'Fase 1'); page.locator('#pcNombre').dispatch_event('change'); page.wait_for_timeout(100)
    page.fill('#pcIni', '2026-06-01'); page.locator('#pcIni').dispatch_event('change'); page.wait_for_timeout(100)
    page.fill('#pcDurN', '3'); page.locator('#pcDurN').dispatch_event('change'); page.wait_for_timeout(200)
    check(page.locator('.pc-semana .pc-dia').count() == 21 and page.locator('.pc-semana .pc-dia').first.inner_text().lower().startswith('lun 1'), 'tres semanas, empezando el lunes 1 de junio')
    dia = lambda n: page.locator(f'.pc-dia[data-dia="{n}"]')
    planes = lambda: [x for x in server_state()['planes'] if x['patientId'] == 'p1']
    items = lambda: planes()[0]['items']
    # añadir un bloque y un ejercicio suelto, con notas, al lunes y al miércoles
    dia(1).get_by_role('button', name='+ Añadir').click(); page.wait_for_selector('#modal .lista-sel')
    check(page.locator('#modal .lista-sel.vertical').count() == 1 and page.locator('#modal .bItem').count() == 1 and page.locator('#modal .exItem').count() == 4, 'mismo selector de bloques y ejercicios')
    page.locator('#modal .bItem input').check()
    page.locator('#modal .exItem', has_text='Estiramiento isquios').locator('input').check()
    page.fill('#acNota', '3 series de 10')
    page.locator('.acDia[value="3"]').check()
    page.get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(300)
    its = items()
    lun = [x for x in its if x['dia'] == 1]; mie = [x for x in its if x['dia'] == 3]
    check(len(lun) == 3 and len(mie) == 3 and len(its) == 6, 'se añade a los dos días marcados (bloque de 2 + 1 suelto)')
    blq = [x for x in lun if x['bloqueId']]
    check(len(blq) == 2 and len({x['grupo'] for x in blq}) == 1 and blq[0]['grupo'] and all(x['notaGrupo'] == '3 series de 10' for x in blq), 'el bloque forma un grupo con su nota')
    suelto = [x for x in lun if not x['bloqueId']][0]
    check(suelto['nota'] == '3 series de 10' and suelto['grupo'] == '', 'el ejercicio suelto lleva su nota')
    check(len(server_state()['pautas']) == 3, 'las pautas de la clínica no se tocan')
    check(dia(1).locator('.pc-g').count() == 1 and dia(1).locator('.pc-suelto').count() == 1, 'el día muestra el bloque agrupado y el ejercicio suelto')
    check('3 series de 10' in dia(1).inner_text(), 'las notas se ven en el día')
    # el día ya no ofrece lo que contiene
    dia(1).get_by_role('button', name='+ Añadir').click(); page.wait_for_selector('#modal .lista-sel')
    check(page.locator('#modal .exItem').count() == 1 and page.locator('#modal .bItem').count() == 0, 'el selector oculta lo que ya está en ese día')
    page.locator('#modal button', has_text='Cancelar').click()
    # editar notas
    dia(1).locator('.pc-suelto button[aria-label="Editar notas"]').click()
    page.fill('#notaPl', 'Solo si no hay dolor'); page.get_by_role('button', name='Guardar', exact=True).click(); page.wait_for_timeout(200)
    check([x for x in items() if x['dia'] == 1 and not x['bloqueId']][0]['nota'] == 'Solo si no hay dolor', 'editar la nota de un ejercicio')
    dia(1).locator('button[aria-label="Editar notas del bloque"]').click()
    page.fill('#notaPl', 'Despacio'); page.get_by_role('button', name='Guardar', exact=True).click(); page.wait_for_timeout(200)
    check(all(x['notaGrupo'] == 'Despacio' for x in items() if x['dia'] == 1 and x['bloqueId']) and all(x['notaGrupo'] == '3 series de 10' for x in items() if x['dia'] == 3 and x['bloqueId']), 'editar la nota del bloque solo afecta a ese día')
    # quitar
    dia(3).locator('button[aria-label="Quitar bloque"]').click(); page.wait_for_timeout(200)
    check(len([x for x in items() if x['dia'] == 3]) == 1, 'quitar un bloque del día quita todos sus ejercicios')
    dia(1).locator('.pc-g button[aria-label="Quitar"]').first.click(); page.wait_for_timeout(200)
    check(len([x for x in items() if x['dia'] == 1]) == 2, 'quitar un ejercicio de un bloque')
    # editor de día: lo del día (ordenar, notas, quitar) y «+ Añadir…», que abre la ventana de añadir con el orden
    dia(1).get_by_role('button', name='Editar', exact=True).click()
    check(page.locator('#modal .dc-u').count() == 2 and page.locator('#modal').get_by_role('button', name='+ Añadir a este día…').count() == 1, 'el editor de día lista sus unidades y ofrece «+ Añadir…»')
    page.locator('#modal button', has_text='Cerrar').first.click()
    page.screenshot(path=f'{tmp}/paciente.png', full_page=True)

    print('\n[F] PDF del plan')
    for f in os.listdir(EXP) if os.path.isdir(EXP) else []: os.remove(os.path.join(EXP, f))   # solo ficheros de planes
    page.evaluate("docActual().items.push({id:uid(),dia:17,exerciseId:'e4',bloqueId:'',orden:1,nota:'Lento',grupo:'',notaGrupo:''}); render()")
    page.locator('#sec-casa').get_by_role('button', name='Exportar a PDF', exact=True).click()
    check(page.locator('#modal .card').count() == 0, 'exportar no abre ninguna ventana')
    page.wait_for_selector('#casaExpMsg:has-text("guardado")', timeout=20000)
    pdfs = [f for f in os.listdir(EXP) if f.endswith('.pdf')]
    check(len(pdfs) == 1 and pdfs[0].startswith('López_Pérez_Ana_Plan_en_casa_Fase_1_2026-06-01_2026-06-21') and '2026-06-01' in pdfs[0] and '2026-06-21' in pdfs[0], f'se guarda «{pdfs}» con el nombre y las fechas del plan')
    ruta = os.path.join(EXP, pdfs[0])
    txt = subprocess.run(['pdftotext', '-layout', ruta, '-'], capture_output=True, text=True).stdout
    check('Clínica Vigo' in txt and 'Carlos Dabarca' in txt and '1234' in txt, 'cabecera: clínica, profesional y colegiado')
    check('Plan de ejercicios en casa' in txt and 'Lunes, 1 de junio' in txt, 'título y primer día')
    check('3 series de 10' in txt and 'Solo si no hay dolor' in txt and 'Despacio' in txt, 'las notas de ejercicios y bloques aparecen en el PDF')
    check('Miércoles, 3 de junio' in txt and 'Estiramiento isquios' in txt, 'el miércoles conserva solo el ejercicio suelto')
    check('17 de junio' in txt and 'Respiración diafragmática' in txt, 'incluye también la tercera semana (17 de junio)')
    imgs = subprocess.run(['pdfimages', '-list', ruta], capture_output=True, text=True).stdout.strip().splitlines()
    check(len(imgs) - 2 >= 2, 'el PDF incluye logo y firma')
    subprocess.run(['pdftoppm', '-png', '-r', '60', '-f', '1', '-l', '1', ruta, f'{tmp}/plan'])
    # sin datos de personalización: no falla
    check(not errors, 'sin errores de consola: ' + '; '.join(errors[:3]))
    print('\ncapturas en', tmp)
    br.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLOS')
sys.exit(0 if ok else 1)
