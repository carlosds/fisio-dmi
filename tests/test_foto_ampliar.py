import sys
from playwright.sync_api import sync_playwright
PORT=sys.argv[1]; fails=[]
def check(c,m):
    print(('  ok  ' if c else '  FALLA ')+m)
    if not c: fails.append(m)
IMG="data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><rect width='20' height='20' fill='red'/></svg>"
with sync_playwright() as p:
    b=p.chromium.launch(); page=b.new_page(); page.goto(f'http://127.0.0.1:{PORT}/'); page.wait_for_timeout(400)
    page.evaluate("img => { db.patients[0].foto = img; render() }", IMG); page.wait_for_timeout(200)
    page.locator('#listaPacientes .avatar.zoom').first.click(); page.wait_for_timeout(200)
    check(page.locator('#fotoAmpliada').count()==1 and page.evaluate("ui.view")=='pacientes', 'clic en la foto del listado la amplía sin abrir la ficha')
    page.keyboard.press('Escape'); check(page.locator('#fotoAmpliada').count()==0, 'Esc la cierra')
    page.locator('#listaPacientes .avatar.zoom').first.click(); page.locator('#fotoAmpliada').click(); check(page.locator('#fotoAmpliada').count()==0, 'clic la cierra')
    page.evaluate("openPatient(db.patients[0].id)"); page.wait_for_timeout(200)
    page.locator('.avatar.zoom').first.click(); check(page.locator('#fotoAmpliada figcaption').inner_text().strip()!='', 'ficha: se amplía con el nombre'); page.keyboard.press('Escape')
    page.evaluate("openEditPaciente ? 0 : 0") if False else None
    b.close()
sys.exit(1 if fails else 0)
