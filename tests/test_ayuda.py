# Sección «Ayuda» (manual AYUDA.md) e iconos «?» con ayuda corta y enlace al manual.
import sys
from playwright.sync_api import sync_playwright
PORT = sys.argv[1]; fails = []
def check(c, m):
    print(('  ok  ' if c else '  FALLA ') + m)
    if not c: fails.append(m)
with sync_playwright() as p:
    b = p.chromium.launch(); page = b.new_page(viewport={'width': 1300, 'height': 850}); errs = []; page.on('pageerror', lambda e: errs.append(str(e)))
    page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_timeout(400)
    page.evaluate("descartarNovedades()")
    page.get_by_role('button', name='Ayuda', exact=True).click(); page.wait_for_selector('#manual section')
    n = page.locator('#manual section').count()
    check(n >= 18 and page.locator('#ayudaIndice a').count() == n, f'el manual se muestra con su índice ({n} secciones)')
    check('on' in (page.locator('nav [data-v=ayuda]').get_attribute('class') or ''), 'el menú marca «Ayuda»')
    # todos los enlaces internos y todas las anclas de la ayuda corta existen
    rotos = page.evaluate("[...document.querySelectorAll('#manual a[href^=\"#\"]')].map(a => a.getAttribute('href').slice(1)).filter(id => !document.getElementById('ay-' + id))")
    check(rotos == [], f'los enlaces del manual llevan a secciones que existen {rotos}')
    sin = page.evaluate("Object.entries(AYUDA_CORTA).filter(([k, a]) => !document.getElementById('ay-' + a.ancla)).map(([k]) => k)")
    check(sin == [], f'cada ayuda corta apunta a una sección del manual {sin}')
    # índice: salta a la sección
    page.locator('#ayudaIndice a', has_text='Copias de seguridad').click(); page.wait_for_timeout(700)
    top = page.evaluate("document.getElementById('ay-copias').getBoundingClientRect().top")
    check(0 <= top < 200, f'el índice lleva a la sección ({top:.0f}px)')
    # buscador
    page.fill('#ayudaBuscar', 'repetición'); page.wait_for_timeout(150)
    vis = page.locator('#manual section:not(.oculto)').count()
    check(0 < vis < n, f'el buscador deja solo las secciones que contienen la palabra ({vis})')
    page.fill('#ayudaBuscar', 'zzzzqq'); page.wait_for_timeout(150)
    check(page.locator('#ayudaNada').count() == 1, 'sin coincidencias, lo dice')
    page.fill('#ayudaBuscar', ''); page.wait_for_timeout(150)
    check(page.locator('#manual section.oculto').count() == 0, 'al vaciar el buscador vuelve todo')
    # icono en la ficha → ayuda corta → manual
    page.evaluate("openPatient('p1')"); page.wait_for_timeout(200)
    page.locator('#sec-pautas .ayuda-ico').click(); page.wait_for_timeout(150)
    check(page.locator('#ayudaPop').is_visible() and 'Pautas' in page.locator('#ayudaPop h4').inner_text(), 'el «?» de Pautas abre su ayuda corta')
    page.keyboard.press('Escape'); page.wait_for_timeout(100)
    check(page.locator('#ayudaPop').count() == 0, 'Esc la cierra')
    page.locator('#sec-pautas .ayuda-ico').click(); page.wait_for_timeout(100)
    page.locator('#sec-pautas .ayuda-ico').click(); page.wait_for_timeout(100)
    check(page.locator('#ayudaPop').count() == 0, 'pulsar otra vez el «?» la cierra')
    page.locator('#sec-pautas .ayuda-ico').click(); page.mouse.click(5, 880); page.wait_for_timeout(100)
    check(page.locator('#ayudaPop').count() == 0, 'pulsar fuera la cierra')
    page.locator('#sec-pautas .ayuda-ico').click(); page.get_by_role('link', name='Ver en el manual →').click(); page.wait_for_timeout(700)
    check(page.evaluate('ui.view') == 'ayuda' and 0 <= page.evaluate("document.getElementById('ay-pautas').getBoundingClientRect().top") < 200, '«Ver en el manual» abre la sección correspondiente')
    # dentro de una ventana: Esc cierra la ayuda pero no la ventana
    page.evaluate("openPatient('p1'); ui.tabP='calendario'; render(); openDay(todayIso())"); page.wait_for_timeout(200)
    page.locator('#modal .ayuda-ico').click(); page.wait_for_timeout(150)
    check(page.locator('#ayudaPop').is_visible(), 'el «?» funciona dentro de la ventana del día')
    page.keyboard.press('Escape'); page.wait_for_timeout(100)
    check(page.locator('#ayudaPop').count() == 0 and page.locator('#modal .modalx').count() == 1, 'Esc cierra la ayuda y deja la ventana abierta')
    page.locator('#modal .ayuda-ico').click(); page.get_by_role('link', name='Ver en el manual →').click(); page.wait_for_timeout(600)
    check(page.evaluate("document.getElementById('modal').innerHTML.trim()") == '' and page.evaluate('ui.view') == 'ayuda', 'desde una ventana, el enlace la cierra y abre el manual')
    # hay iconos en las pantallas principales
    cuenta = {}
    for v, js in [('pacientes', "go('pacientes')"), ('ejercicios', "go('ejercicios')"), ('bloques', "go('bloques')"), ('plantillas', "go('plantillas')"), ('ajustes-copias', "ui.ajTab='copias'; go('ajustes')"), ('casa', "openPatient('p1'); ui.tabP='casa'; render()"), ('informes', "openPatient('p1'); ui.tabP='informes'; render()"), ('hitos', "openPatient('p1'); ui.tabP='hitos'; render()"), ('resumen', "openPatient('p1'); ui.tabP='calendario'; ui.calVista='resumen'; render()")]:
        page.evaluate(js); page.wait_for_timeout(150); cuenta[v] = page.locator('#main .ayuda-ico').count()
    check(all(c >= 1 for c in cuenta.values()), f'iconos de ayuda en las pantallas principales {cuenta}')
    check(not errs, f'sin errores JS {errs}')
    b.close()
sys.exit(1 if fails else 0)
