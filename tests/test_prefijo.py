# Bajo el nombre de un bloque, sus ejercicios no repiten ese nombre (puntuación, día, pautas, bloques, selector, gráfica).
import sys
from playwright.sync_api import sync_playwright
PORT = int(sys.argv[1]); ok = True
def check(c, m):
    global ok; ok = ok and bool(c); print(('  OK    ' if c else '  FALLO ') + m)
with sync_playwright() as pw:
    br = pw.chromium.launch(executable_path='/opt/pw-browsers/chromium')
    page = br.new_page(viewport={'width': 1300, 'height': 900}); page.on('dialog', lambda d: d.accept())
    page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_selector('#main')
    page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    page.evaluate("""() => {
      db.exercises.push({id:'q1',nombre:'Caminar con los muslos – Por los muslos',descripcion:'',fotos:[]}, {id:'q2',nombre:'Caminar con los muslos – Por los tobillos',descripcion:'',fotos:[]}, {id:'q3',nombre:'Caminar con los muslos',descripcion:'',fotos:[]});
      db.bloques.push({id:'bq',nombre:'Caminar con los muslos',nivel:'A',ejercicios:['q1','q2','q3']});
      ['q1','q2','q3'].forEach((e,i) => db.pautas.push({id:'pq'+i,patientId:ui.patientId,exerciseId:e,desde:'2026-06-01',hasta:'',asignacion:'gq',bloqueId:'bq',orden:50+i}));
      ui.selDay = '2026-06-10'; render(); renderDayModal(); }""")
    page.wait_for_selector('#modal .ej-dia')
    m = page.locator('#modal').inner_text()
    check(m.count('Caminar con los muslos') == 1, 'Puntuación: el nombre del bloque aparece una sola vez')
    check('Por los tobillos' in m and 'Caminar con los muslos – Por' not in m, 'Puntuación: los ejercicios sin el prefijo')
    page.get_by_role('button', name='Cerrar').last.click()
    # pautas
    t = page.locator('#sec-pautas .item', has_text='Caminar con los muslos').first.inner_text()
    check(t.count('Caminar con los muslos') == 2 and 'Por los tobillos' in t and 'Caminar con los muslos – Por' not in t, 'Pautas: lista del bloque sin repetir el prefijo (título + el ejercicio que se llama igual)')
    # bloques
    page.get_by_role('button', name='Biblioteca', exact=True).click(); page.get_by_role('button', name='Bloques', exact=True).click(); page.wait_for_timeout(300)
    b = page.locator('#listaBloques .item', has_text='Caminar con los muslos').inner_text()
    check(b.count('Caminar con los muslos') == 2 and 'Por los muslos' in b and 'Caminar con los muslos – Por' not in b, 'Bloques: lista sin repetir el prefijo')
    # selector (ver los ejercicios del bloque)
    page.evaluate("renderDayModal()") if False else None
    page.locator('header').get_by_role('button', name='Pacientes').click(); page.locator('#listaPacientes .item a').first.click(); page.wait_for_selector('#sec-pautas')
    page.get_by_role('button', name='Asignar ejercicios').click(); page.wait_for_selector('#modal .bItem')
    fila = page.locator('#modal .bItem', has_text='Caminar con los muslos').first
    fila.get_by_role('button', name='Ver').click()
    lis = fila.locator('li').all_inner_texts()
    check('Por los muslos' in lis and 'Por los tobillos' in lis, f'Selector: ejercicios del bloque sin prefijo {lis}')
    check('Caminar con los muslos' in lis, 'un ejercicio que se llama igual que el bloque conserva su nombre en las listas')
    page.get_by_role('button', name='Cancelar').click() if page.get_by_role('button', name='Cancelar').count() else page.keyboard.press('Escape')
    # gráfica
    page.evaluate("db.puntuaciones[scoreKey('p1', todayIso(), 'q1', 1)] = 3; idxPunt = null; render()")
    page.get_by_role('tab', name='Calendario').click(); page.locator('#subCal').get_by_role('button', name='Resumen').click(); page.wait_for_timeout(100)
    page.get_by_role('button', name='Semana', exact=True).last.click(); page.get_by_role('button', name='Puntos', exact=True).click(); page.wait_for_timeout(200)
    textos = page.locator('#sec-resumen svg text').evaluate_all("els => els.map(e => [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join(''))")
    check('Por los tobillos' in textos and not any(t.startswith('Caminar con los muslos –') for t in textos), f'Gráfica: filas sin el prefijo del bloque {[t for t in textos if "muslos" in t or "tobillos" in t]}')
print('\nTODO OK' if ok else '\nHAY FALLOS'); sys.exit(0 if ok else 1)
