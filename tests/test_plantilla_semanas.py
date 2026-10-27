# Plantillas de varias semanas: edición, aplicación y conversión de las antiguas.
import json, sys, urllib.request
from playwright.sync_api import sync_playwright
PORT = int(sys.argv[1]); BASE = f'http://127.0.0.1:{PORT}/'
ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
def st(): return json.load(urllib.request.urlopen(BASE + '__state'))
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(viewport={'width': 1400, 'height': 900}); errors = []
    page.on('pageerror', lambda e: errors.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE); page.wait_for_selector('#main')
    # conversión de una plantilla antigua (1 semana repetida 2 veces)
    r = page.evaluate("""() => { const q = normalize({ plantillas: [{ id:'old', nombre:'Antigua', semanas:2, creada:'2026-01-01', items:[{id:'a',dia:1,exerciseId:'e1',bloqueId:'',orden:1,nota:'',grupo:'',notaGrupo:''},{id:'b',dia:3,exerciseId:'e2',bloqueId:'',orden:1,nota:'',grupo:'',notaGrupo:''}] }] }).plantillas[0]; return [q.ciclo, q.items.map(i => i.dia).sort((a,b)=>a-b)]; }""")
    check(r[0] == 1 and r[1] == [1, 3, 8, 10], f'plantilla antigua de 2 semanas -> 4 entradas en las semanas 1 y 2 {r}')
    # nueva plantilla de 1 semana
    page.evaluate("""() => { db.plantillas.push({ id:'t1', nombre:'Nueva', semanas:1, ciclo:1, creada:'2026-10-01', aplicaciones:[], items:[{id:'i1',dia:1,exerciseId:'e1',bloqueId:'',orden:1,nota:'',grupo:'',notaGrupo:''}] }); verPlantilla('t1'); }""")
    page.wait_for_selector('#plNombre')
    check(page.locator('.pc-semana .pc-dia').count() == 7, '1 semana = 7 tarjetas')
    page.fill('#plDurN', '2'); page.locator('#plDurN').blur(); page.wait_for_timeout(300)
    check(page.locator('.pc-semana .pc-dia').count() == 14 and page.get_by_role('heading', name='Semana 2').count() == 1, '2 semanas = 14 tarjetas con título de semana')
    page.locator('.pc-semana .pc-dia').nth(7).get_by_role('button', name='+ Añadir').click(); page.wait_for_selector('#acLibre')
    check('Semana 2 · Lunes' in page.locator('#modal h3').inner_text() and page.locator('#modal .acDia').count() == 14, 'añadir en la semana 2 (14 días elegibles)')
    page.locator('#modal .exCheck').nth(1).check(); page.locator('#modal').get_by_role('button', name='Añadir', exact=True).click(); page.wait_for_timeout(300)
    it = st()['plantillas'][-1]['items']
    check(sorted(i['dia'] for i in it) == [1, 8], 'el ejercicio queda en el día 8 (lunes de la semana 2)')
    # aplicar 3 semanas: la 1.ª con el contenido de la semana 1, la 2.ª con el de la 2.ª, la 3.ª repite la 1.ª
    page.evaluate("openAplicarPlantilla('" + page.evaluate("db.patients[0].id") + "', 't1')"); page.wait_for_selector('#apIni')
    page.fill('#apIni', '2033-01-03'); page.fill('#apDurN', '3')
    page.get_by_role('button', name='Crear plan', exact=True).click(); page.wait_for_timeout(500)
    pc = {(i['dia'], i['exerciseId']) for x in st()['planes'] if x['inicio'] == '2033-01-03' for i in x['items']}
    e2 = [i['exerciseId'] for i in it if i['dia'] == 8][0]
    check(pc == {(1, 'e1'), (8, e2), (15, 'e1')}, f'ciclo de 2 semanas repetido en 3 {sorted(pc)}')
    # eliminar el plan del paciente: deja de figurar con la plantilla
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.wait_for_selector('#plBuscar')
    check('Pacientes (1)' in page.locator('#main').inner_text(), 'el paciente figura con la plantilla')
    page.evaluate("delPlanCasa(db.planes.find(x => x.inicio === '2033-01-03').id)"); page.wait_for_timeout(400)
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.wait_for_selector('#plBuscar'); page.wait_for_timeout(200)
    check('Pacientes (0)' in page.locator('#main').inner_text(), 'tras eliminar su plan, ya no figura')
    # reducir con contenido en la semana 2 pide confirmación y la quita
    page.locator('#menuBiblioteca > button').click(); page.locator('header [data-v="plantillas"]').click(); page.wait_for_selector('#plBuscar')
    page.get_by_role('button', name='Editar', exact=True).last.click(); page.wait_for_selector('#plNombre')
    page.fill('#plDurN', '1'); page.locator('#plDurN').blur(); page.wait_for_timeout(300)
    check(sorted(i['dia'] for i in st()['plantillas'][-1]['items']) == [1] and page.locator('.pc-semana .pc-dia').count() == 7, 'reducir a 1 semana quita lo de la semana 2')
    # duración en meses o días
    page.select_option('#plDurU', 'meses'); page.wait_for_timeout(300)
    t = st()['plantillas'][-1]
    check(t['unidad'] == 'meses' and t['duracion'] == 1 and t['semanas'] == 4 and page.locator('.pc-semana .pc-dia').count() == 28, 'plantilla de 1 mes: 4 semanas de lunes a domingo')
    check('1 mes' in page.locator('#sec-plantilla').inner_text() and '4 semanas' in page.locator('#sec-plantilla').inner_text(), 'lo explica en la pantalla')
    page.select_option('#plDurU', 'dias'); page.wait_for_timeout(300)
    t = st()['plantillas'][-1]
    check(t['unidad'] == 'dias' and t['duracion'] == 30 and t['semanas'] == 5, '1 mes → 30 días: 5 semanas')
    page.evaluate("openAplicarPlantilla(db.patients[0].id, '" + t['id'] + "')"); page.wait_for_selector('#apDurN')
    check(page.input_value('#apDurN') == '30' and page.input_value('#apDurU') == 'dias', 'al usarla propone su duración (30 días)')
    page.fill('#apIni', '2034-01-02'); page.locator('#apDurN').dispatch_event('input')
    check('31 de enero de 2034' in page.locator('#apFinTxt').inner_text(), 'y calcula cuándo termina')
    page.evaluate('closeModal()')
    check(not errors, 'sin errores JS ' + str(errors))
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
