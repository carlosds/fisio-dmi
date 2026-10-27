import re
# Aviso de bloques al renombrar/eliminar un ejercicio. Uso: mock_server.py PUERTO seed_nuevo.json & ; python3 test_aviso_bloques.py PUERTO
import sys
from playwright.sync_api import sync_playwright
ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
dialogs = []
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium', headless=True)
    page = br.new_page(); page.goto(f'http://127.0.0.1:{sys.argv[1]}/'); page.wait_for_selector('#main')
    def on(d):
        dialogs.append((d.type, d.message))
        (d.accept('Puente de glúteo') if len(dialogs) == 2 else d.dismiss()) if d.type == 'prompt' else d.accept()
    page.on('dialog', on)
    page.get_by_role('button', name='Biblioteca', exact=True).click(); page.get_by_role('button', name='Ejercicios', exact=True).click(); page.wait_for_timeout(200)
    page.locator('#listaEjercicios .item', has_text='Puente glúteo').get_by_role('button', name=re.compile('^Acciones de')).click(); page.locator('#listaEjercicios .item', has_text='Puente glúteo').get_by_role('button', name='Renombrar…').click(); page.wait_for_timeout(200)
    check(dialogs[0][0] == 'confirm' and 'Core básico' in dialogs[0][1] and 'pertenece al bloque' in dialogs[0][1], 'renombrar avisa del bloque')
    check(page.evaluate("db.exercises.some(e => e.nombre === 'Puente de glúteo')"), 'tras aceptar, se renombra')
    dialogs.clear()
    page.locator('#listaEjercicios .item', has_text='Estiramiento isquios').get_by_role('button', name=re.compile('^Acciones de')).click(); page.locator('#listaEjercicios .item', has_text='Estiramiento isquios').get_by_role('button', name='Renombrar…').click(); page.wait_for_timeout(200)
    check(dialogs and dialogs[0][0] == 'prompt', 'sin bloque, renombrar va directo sin aviso')
    dialogs.clear()
    page.locator('#listaEjercicios .item', has_text='Plancha lateral').get_by_role('button', name=re.compile('^Acciones de')).click(); page.locator('#listaEjercicios .item', has_text='Plancha lateral').get_by_role('button', name='Eliminar…').click(); page.wait_for_timeout(200)
    check('Core básico' in dialogs[0][1] and 'pertenece al bloque' in dialogs[0][1], 'eliminar avisa del bloque')
    check(page.evaluate("db.bloques[0].ejercicios.length") == 1, 'se quita también del bloque')
    dialogs.clear()
    page.locator('#listaEjercicios .item', has_text='Estiramiento isquios').get_by_role('button', name=re.compile('^Acciones de')).click(); page.locator('#listaEjercicios .item', has_text='Estiramiento isquios').get_by_role('button', name='Eliminar…').click(); page.wait_for_timeout(200)
    check('pertenece' not in dialogs[0][1], 'eliminar un ejercicio sin bloque no muestra el aviso')
    br.close()
print('\nRESULTADO:', 'TODO OK' if ok else 'HAY FALLOS'); sys.exit(0 if ok else 1)
