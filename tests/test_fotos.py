import re
# Fotos en hitos y evaluaciones: subida múltiple, columna con número, visor y edición.
import json, sys, tempfile, urllib.request
from playwright.sync_api import sync_playwright
from PIL import Image
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def st(): return json.load(urllib.request.urlopen(BASE + '__state'))
tmp = tempfile.mkdtemp(); fs = []
for i, col in enumerate([(200, 30, 30), (30, 200, 30), (30, 30, 200)]):
    p = f'{tmp}/f{i}.jpg'; Image.new('RGB', (2400 if i == 0 else 600, 1200), col).save(p); fs.append(p)
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1300, 'height': 900}); errors = []
    page.on('pageerror', lambda e: errors.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE); page.wait_for_selector('#main')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    for tab, clave, tid, lid, btn in [('Evaluación inicial', 'evaluaciones', 'evTexto', 'listaEvaluaciones', 'Añadir evaluación'), ('Hitos', 'hitos', 'hNota', 'listaHitos', 'Añadir hito')]:
        print('\n[' + tab + ']')
        page.get_by_role('tab', name='Progreso').click(); page.get_by_role('menuitem', name=tab).click(); page.wait_for_timeout(200)
        if page.locator('#' + tid).is_hidden(): page.locator('#sec-' + clave).get_by_role('button', name=re.compile('^Nuev')).click()
        page.fill('#' + tid, 'Con fotos')
        page.set_input_files(f'#fotosIn-{clave}', fs); page.wait_for_timeout(1200)
        check(page.locator(f'#fotosPrev-{clave} .th').count() == 3, 'se suben 3 fotos y salen las miniaturas')
        page.locator(f'#fotosPrev-{clave} .th button').nth(2).click()
        check(page.locator(f'#fotosPrev-{clave} .th').count() == 2, 'se puede quitar una antes de guardar')
        page.get_by_role('button', name=btn).click(); page.wait_for_timeout(400)
        e = st()[clave][-1]
        check(len(e['fotos']) == 2 and e['fotos'][0].startswith('/fotos/'), 'la entrada guarda 2 fotos (URL)')
        if page.locator('#' + tid).is_hidden(): page.locator('#sec-' + clave).get_by_role('button', name=re.compile('^Nuev')).click()
        page.fill('#' + tid, 'Sin fotos'); page.get_by_role('button', name=btn).click(); page.wait_for_timeout(300)
        filas = page.locator(f'#{lid} tbody tr')
        check(filas.count() == 2 and page.locator(f'#{lid} th', has_text='Fotos').count() == 1, 'columna «Fotos»')
        fila = page.locator(f'#{lid} tbody tr', has_text='Con fotos')
        check(fila.locator('.mini-fotos .mini').count() == 2 and fila.locator('.mini-fotos img').count() == 2, 'muestra las 2 fotos en miniatura')
        check(page.locator(f'#{lid} tbody tr', has_text='Sin fotos').locator('.mini-fotos').count() == 0, 'sin fotos no hay miniaturas')
        fila.get_by_role('button', name='Ver la foto 1 de 2').click(); page.wait_for_selector('#modal .visor img')
        check('Foto 1 de 2' in page.locator('#modal .visor').inner_text(), 'visor en la foto 1 de 2')
        check(page.evaluate("document.querySelector('#modal .visor-img img').naturalWidth") > 0, 'la imagen se carga')
        page.get_by_role('button', name='Foto siguiente').click()
        check('Foto 2 de 2' in page.locator('#modal .visor').inner_text(), 'siguiente')
        page.keyboard.press('ArrowRight')
        check('Foto 1 de 2' in page.locator('#modal .visor').inner_text(), 'flecha derecha da la vuelta')
        page.keyboard.press('ArrowLeft')
        check('Foto 2 de 2' in page.locator('#modal .visor').inner_text(), 'flecha izquierda')
        page.locator('#modal .visor-tiras img').first.click()
        check('Foto 1 de 2' in page.locator('#modal .visor').inner_text(), 'miniaturas del visor')
        page.locator('#modal button', has_text='Cerrar').click()
        # editar: quitar una y añadir otra
        fila.get_by_role('button', name='Editar').click(); page.wait_for_selector('#modal .fotos-prev .th')
        check(page.locator('#modal .fotos-prev .th').count() == 2, 'el editor muestra las fotos existentes')
        page.locator('#modal .fotos-prev .th button').first.click()
        page.set_input_files('#modal input[type=file]', [fs[2]]); page.wait_for_timeout(800)
        page.get_by_role('button', name='Guardar', exact=True).click(); page.wait_for_timeout(300)
        check(len([x for x in st()[clave] if x['nota' if clave == 'hitos' else 'evaluacion'] == 'Con fotos'][0]['fotos']) == 2, 'editar: quitar una y añadir otra deja 2')
    # el archivo servido es una imagen reducida
    url = st()['hitos'][-1]['fotos'][0] if st()['hitos'][-1]['fotos'] else st()['hitos'][0]['fotos'][0]
    data = urllib.request.urlopen(BASE.rstrip('/') + url).read()
    check(data[:3] == b'\xff\xd8\xff', 'la foto servida es JPEG')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
