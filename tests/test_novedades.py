import sys, json, os, re, urllib.request
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; URL = f'http://127.0.0.1:{PORT}/'
fails = []
# versión actual = la primera del CHANGELOG (la que anuncia el mock); la anterior, la segunda
VERS = re.findall(r'^## (\S+)', open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'docs', 'CHANGELOG.md'), encoding='utf-8').read(), re.M)
V, ANT = VERS[0], VERS[1]
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(); page.on('dialog', lambda d: d.accept())
    page.goto(URL); page.wait_for_timeout(500)
    # datos existentes + sin novedadesVista -> aviso
    check(page.locator('#avisoNovedades .aviso-nov').count() == 0, 'instalación vacía: sin aviso')
    check(page.evaluate("db.ajustes.novedadesVista") == V, 'instalación vacía: se marca como vista en silencio')
    page.evaluate("db.ajustes.novedadesVista = '" + ANT + "'; db.patients.push({id:'zz',nombre:'A',apellidos:'B'}); avisoNovedades()"); page.wait_for_timeout(300)
    check(page.locator('#avisoNovedades .aviso-nov').count() == 1 and V in page.locator('#avisoNovedades').inner_text(), 'tras actualizar aparece el aviso')
    page.get_by_role('button', name='Ver novedades').click(); page.wait_for_timeout(400)
    check(page.locator('#avisoNovedades .aviso-nov').count() == 0 and page.evaluate("db.ajustes.novedadesVista") == V, 'Ver novedades descarta el aviso')
    check(page.locator('#tabsAjustes button.on').inner_text() == 'Novedades', 'abre la pestaña Novedades')
    check(page.locator('#novedades details').count() == len(VERS), f'están las {len(VERS)} versiones')
    check(page.locator('#novedades details').nth(0).get_attribute('open') is not None and page.locator('#novedades details').nth(1).get_attribute('open') is None, 'la actual abierta y la anterior plegada')
    check('Instalada' in page.locator('#novedades details').nth(0).inner_text(), 'la versión instalada está marcada')
    check(page.locator('#novedades strong').count() > 3, 'la negrita se interpreta')
    for t, sel in (('Personalizar', None), ('Copias de seguridad', '#listaCopias'), ('Datos', '#rutaDatos')):
        page.get_by_role('button', name=t, exact=True).click(); page.wait_for_timeout(200)
        check(page.locator('#tabsAjustes button.on').inner_text() == t and (sel is None or page.locator(sel).count() == 1), f'pestaña {t}')
    # Entendido
    page.evaluate("db.ajustes.novedadesVista = '" + ANT + "'; avisoNovedades()"); page.wait_for_timeout(300)
    page.get_by_role('button', name='Entendido').click(); page.wait_for_timeout(300)
    check(page.locator('#avisoNovedades .aviso-nov').count() == 0 and page.evaluate("db.ajustes.novedadesVista") == V, 'Entendido descarta y recuerda')
    b.close()
sys.exit(1 if fails else 0)
