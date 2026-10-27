# PDF guardados donde elige el usuario y listado en la pestaña «Informes» del paciente.
import sys, os, json, urllib.request
from playwright.sync_api import sync_playwright
from ayuda_planes import PLAN_PRUEBA
PORT = sys.argv[1]; BASE = f'http://127.0.0.1:{PORT}'
fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
get = lambda p: json.loads(urllib.request.urlopen(BASE + p).read())
stats = lambda: get('/__stats'); st = lambda: get('/__state')
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page()
    errs = []; page.on('pageerror', lambda e: errs.append(str(e))); page.on('dialog', lambda d: d.accept())
    page.goto(BASE + '/'); page.wait_for_timeout(500)
    page.evaluate("openPatient('p1')"); page.get_by_role('tab', name='Informes').click(); page.wait_for_timeout(200)
    check('Todavía no se ha generado ningún PDF' in page.locator('#secInformes').inner_text(), 'sin PDF: mensaje vacío')
    # cancelar el diálogo
    get('/__dialogo/cancelar')
    page.get_by_role('button', name='Generar informe de pautas…').click(); page.click('#expGenerar')
    page.wait_for_selector('#expEstado >> text=No se ha guardado nada', timeout=30000)
    check(page.evaluate('db.informes.length') == 0, 'cancelar el diálogo no registra nada')
    get('/__dialogo/ok')
    page.click('#expGenerar'); page.wait_for_selector('#expEstado >> text=Guardado', timeout=30000)
    inf = page.evaluate('db.informes[0]')
    check(inf['tipo'] == 'informe' and inf['patientId'] == 'p1' and inf['ruta'].endswith('.pdf') and os.path.exists(inf['ruta']), 'se registra el informe con su ruta')
    check(page.evaluate('db.ajustes.pdfCarpeta') == os.path.dirname(inf['ruta']), 'se recuerda la carpeta elegida')
    page.locator('#expEstado').get_by_role('button', name='Abrir PDF').click(); page.wait_for_timeout(400)
    check(stats().get('abiertos', [])[-1:] == [[inf['id'], '']], 'Abrir PDF pide al servidor abrir ese informe')
    page.locator('#expEstado').get_by_role('button', name='Generar PDF') if False else None
    page.click('#expGenerar'); page.wait_for_selector('#expEstado >> text=Guardado', timeout=30000); page.wait_for_timeout(200)
    check(stats()['inicios'][-1] == os.path.dirname(inf['ruta']), 'el siguiente diálogo empieza en la última carpeta')
    page.evaluate('closeModal()'); page.wait_for_timeout(300)
    check(len(st().get('informes', [])) == 2, 'los informes llegan a la base de datos')
    check(page.locator('.infItem').count() == 2 and inf['ruta'] in page.locator('#secInformes').inner_text(), 'la pestaña Informes lista los PDF con su ruta')
    page.locator(f'.infItem[data-id="{inf["id"]}"]').get_by_role('button', name='Mostrar en la carpeta').click(); page.wait_for_timeout(300)
    check(stats()['abiertos'][-1] == [inf['id'], 'carpeta'], 'Mostrar en la carpeta')
    # filtro por tipo
    page.evaluate("db.informes.push({id:'pl1',patientId:'p1',tipo:'plan',nombre:'Plan.pdf',ruta:'/no/existe/Plan.pdf',fecha:new Date().toISOString(),desde:'2026-06-01',hasta:'2026-06-07',descripcion:'Plan en casa'}); render()"); page.wait_for_timeout(400)
    page.locator('#secInformes').get_by_role('button', name='Planes en casa (1)').click(); page.wait_for_timeout(300)
    check(page.locator('.infItem').count() == 1 and 'Plan en casa' in page.locator('.infItem').inner_text(), 'filtro «Planes en casa»')
    check(page.locator('.infItem .infFalta').is_visible() and page.locator('.infItem').get_by_role('button', name='Abrir').is_disabled(), 'archivo que no existe: aviso y Abrir desactivado')
    page.locator('#secInformes').get_by_role('button', name='Todos (3)').click(); page.wait_for_timeout(300)
    # archivo borrado después de listar: al abrir avisa
    os.remove(inf['ruta'])
    page.locator(f'.infItem[data-id="{inf["id"]}"]').get_by_role('button', name='Abrir').click(); page.wait_for_timeout(500)
    check(page.locator(f'.infItem[data-id="{inf["id"]}"] .infFalta').is_visible(), 'si el archivo desapareció, al abrir se marca como no encontrado')
    # quitar de la lista
    page.locator(f'.infItem[data-id="{inf["id"]}"]').get_by_role('button', name='Quitar de la lista').click(); page.wait_for_timeout(400)
    check(page.evaluate('db.informes.length') == 2 and page.locator('.infItem').count() == 2, 'Quitar de la lista')
    # lote: carpeta una vez; cancelar no genera nada
    page.evaluate("db.patients.push({id:'p2',nombre:'Ana',apellidos:'Lote',fechaAlta:'2026-01-01',telefono:'',email:'',observaciones:'',foto:''}); save()")
    get('/__dialogo/cancelar')
    page.evaluate("openExportar(['p1','p2'])"); page.click('#expGenerar'); page.wait_for_selector('#expEstado >> text=No se ha guardado nada', timeout=30000)
    check(page.evaluate('db.informes.length') == 2, 'lote: cancelar la carpeta no genera nada')
    get('/__dialogo/ok')
    page.click('#expGenerar'); page.wait_for_selector('#expEstado >> text=Listo', timeout=30000)
    lote = page.evaluate("db.informes.slice(-2)")
    check(len({os.path.dirname(x['ruta']) for x in lote}) == 1 and '/lote' in lote[0]['ruta'] and {x['patientId'] for x in lote} == {'p1', 'p2'}, 'lote: un PDF por paciente en la carpeta elegida')
    # el plan en casa también se registra
    page.evaluate("closeModal(); openPatient('p1')"); page.evaluate(PLAN_PRUEBA); page.evaluate("planPrueba('p1', '2026-06-01', 1, [{dia:3,e:'e1'}])")
    page.locator('#sec-casa').get_by_role('button', name='Exportar a PDF', exact=True).click()
    page.wait_for_selector('#casaExpMsg:has-text("PDF guardado")', timeout=20000)
    check(page.evaluate("db.informes.filter(x => x.tipo === 'plan' && x.patientId === 'p1' && x.id !== 'pl1').length") == 1, 'el PDF del plan en casa queda en la lista')
    # eliminar paciente quita sus registros
    page.evaluate("delPacientes(['p2'])"); page.wait_for_timeout(300)
    check(page.evaluate("db.informes.some(x => x.patientId === 'p2')") is False, 'eliminar un paciente quita sus PDF de la lista')
    check(not errs, f'sin errores JS {errs}')
    b.close()
sys.exit(1 if fails else 0)
