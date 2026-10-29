import re, sqlite3, os, shutil, sys
SRC = open(__import__('os').path.join(__import__('os').path.dirname(__import__('os').path.abspath(__file__)), '..', 'code', 'main.go'), encoding='utf-8').read()
print("SQLite", sqlite3.sqlite_version)

def func_body(name):
    i = SRC.index(f'func {name}(')
    j = SRC.index('\nfunc ', i + 5)
    return SRC[i:j]

mig = func_body('migrateDB')
stmts_block = mig[mig.index('stmts := []string{'):mig.index('for _, s := range stmts')]
STMTS = re.findall(r'`([^`]*)`', stmts_block)
cols_block = mig[mig.index('columnas := '):mig.index('for _, c := range columnas')]
COLS = re.findall(r'\{"(\w+)", "(\w+)", "([^"]+)"\}', cols_block)
tx_block = mig[mig.index('`ALTER TABLE puntuaciones RENAME'):mig.index('} {\n\t\t\tif _, err := tx.Exec(s)')]
MIGR = [m.strip() for m in re.findall(r'`([^`]*)`', tx_block)]
ses_block = mig[mig.index('`ALTER TABLE puntuaciones RENAME TO puntuaciones_sin_sesion'):mig.index('for _, q := range pasos')]
MIGR_SES = [m.strip() for m in re.findall(r'`([^`]*)`', ses_block)]
assert len(MIGR_SES) == 4, len(MIGR_SES)
print(f"extraídas: {len(STMTS)} CREATE, {len(COLS)} columnas, {len(MIGR)} pasos de migración")
assert len(STMTS) == 24 and len(COLS) == 24 and len(MIGR) == 4, (len(STMTS), len(COLS), len(MIGR))

def tiene_col(c, t, col):
    return c.execute("SELECT COUNT(*) FROM pragma_table_info(?) WHERE name = ?", (t, col)).fetchone()[0] > 0

def migrate(c):
    for s in STMTS: c.execute(s)
    for t, col, d in COLS:
        if not tiene_col(c, t, col): c.execute(f"ALTER TABLE {t} ADD COLUMN {col} {d}")
    if not tiene_col(c, 'puntuaciones', 'repeticion'):
        c.execute('BEGIN')
        try:
            for s in MIGR: c.execute(s)
            c.execute('COMMIT')
        except Exception:
            c.execute('ROLLBACK'); raise
    if not tiene_col(c, 'puntuaciones', 'sesion'):
        c.execute('BEGIN')
        try:
            for s in MIGR_SES: c.execute(s)
            c.execute('COMMIT')
        except Exception:
            c.execute('ROLLBACK'); raise

def conn(path):
    c = sqlite3.connect(path, isolation_level=None)
    c.execute('PRAGMA foreign_keys=ON')
    return c

def schema_v1(c):   # primera versión: sin ajustes, bloques ni columnas nuevas
    c.executescript("""
    CREATE TABLE exercises (id TEXT PRIMARY KEY, nombre TEXT NOT NULL);
    CREATE TABLE patients (id TEXT PRIMARY KEY, nombre TEXT NOT NULL, apellidos TEXT NOT NULL DEFAULT '', fecha_alta TEXT NOT NULL DEFAULT '', telefono TEXT NOT NULL DEFAULT '', email TEXT NOT NULL DEFAULT '', observaciones TEXT NOT NULL DEFAULT '', foto_archivo TEXT);
    CREATE TABLE pautas (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE, exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE, desde TEXT NOT NULL, hasta TEXT);
    CREATE TABLE puntuaciones (patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE, fecha TEXT NOT NULL, exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE, valor INTEGER NOT NULL CHECK (valor BETWEEN 0 AND 3), PRIMARY KEY (patient_id, fecha, exercise_id));
    """)
def schema_v2(c):   # versión con bloques, asignación y ajustes, pero puntuación única
    schema_v1(c)
    c.executescript("""
    CREATE TABLE ajustes (clave TEXT PRIMARY KEY, valor TEXT NOT NULL);
    CREATE TABLE bloques (id TEXT PRIMARY KEY, nombre TEXT NOT NULL);
    CREATE TABLE bloque_ejercicios (bloque_id TEXT NOT NULL REFERENCES bloques(id) ON DELETE CASCADE, exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE, PRIMARY KEY (bloque_id, exercise_id));
    ALTER TABLE pautas ADD COLUMN asignacion TEXT NOT NULL DEFAULT '';
    ALTER TABLE pautas ADD COLUMN bloque_id TEXT NOT NULL DEFAULT '';
    """)
def seed(c, v2):
    c.executescript("""
    INSERT INTO exercises (id,nombre) VALUES ('e1','Ejercicio 1'),('e2','Ejercicio 2');
    INSERT INTO patients (id,nombre) VALUES ('p1','Ana');
    INSERT INTO pautas (id,patient_id,exercise_id,desde,hasta) VALUES ('x1','p1','e1','2026-10-01',NULL),('x2','p1','e2','2026-10-01','2026-10-05');
    INSERT INTO puntuaciones VALUES ('p1','2026-10-02','e1',3),('p1','2026-10-03','e1',0),('p1','2026-10-03','e2',2);
    """)
    if v2:
        c.executescript("""
        INSERT INTO ajustes VALUES ('pautasColapsadas','1');
        INSERT INTO bloques VALUES ('b1','Bloque viejo');
        INSERT INTO bloque_ejercicios VALUES ('b1','e1'),('b1','e2');
        """)

W = '/tmp/sqltest_work'; shutil.rmtree(W, ignore_errors=True); os.makedirs(W)
ok = True
def check(cond, msg):
    global ok
    print(('  OK   ' if cond else '  FALLO') + ' ' + msg)
    ok = ok and cond

print("\n[1] Base de datos nueva")
c = conn(f'{W}/nueva.db'); migrate(c); migrate(c)   # dos veces: debe ser idempotente
check(tiene_col(c,'puntuaciones','repeticion') and tiene_col(c,'bloques','nivel') and tiene_col(c,'pautas','orden'), "esquema actual completo e idempotente")

for nombre, v2 in (('v1', False), ('v2', True)):
    print(f"\n[2] Migración de esquema {nombre}")
    path = f'{W}/{nombre}.db'; c = conn(path)
    (schema_v2 if v2 else schema_v1)(c); seed(c, v2); c.close()
    c = conn(path); migrate(c)
    n = c.execute("SELECT COUNT(*), MIN(repeticion), MAX(repeticion) FROM puntuaciones").fetchone()
    check(n == (3, 1, 1), f"3 puntuaciones antiguas pasan a repetición 1 {n}")
    check(c.execute("SELECT valor FROM puntuaciones WHERE fecha='2026-10-03' AND exercise_id='e1'").fetchone()[0] == 0, "la puntuación 0 se conserva (no se confunde con vacío)")
    check(c.execute("SELECT COUNT(*) FROM pautas WHERE orden=0 AND asignacion='' AND bloque_id=''").fetchone()[0] == 2, "pautas antiguas con valores por defecto")
    check(tiene_col(c,'bloques','nivel'), "bloques tiene la columna nivel")
    check(c.execute("SELECT COUNT(*) FROM sqlite_master WHERE name IN ('puntuaciones_antigua', 'puntuaciones_sin_sesion')").fetchone()[0] == 0, "no quedan tablas temporales")
    check(tiene_col(c, 'puntuaciones', 'sesion') and c.execute("SELECT COUNT(*) FROM puntuaciones WHERE sesion = ''").fetchone()[0] == 3, "las puntuaciones antiguas pasan a la sesión sin cita")
    migrate(c)
    check(c.execute("SELECT COUNT(*) FROM puntuaciones").fetchone()[0] == 3, "segunda migración no duplica nada")
    c.execute("INSERT INTO puntuaciones (patient_id, fecha, exercise_id, repeticion, valor) VALUES ('p1','2026-10-02','e1',2,NULL)")
    c.execute("INSERT INTO puntuaciones (patient_id, fecha, exercise_id, sesion, repeticion, valor) VALUES ('p1','2026-10-02','e1','cita1',1,3)")
    check(c.execute("SELECT COUNT(*) FROM puntuaciones WHERE fecha='2026-10-02' AND exercise_id='e1' AND repeticion=1").fetchone()[0] == 2, "el mismo ejercicio, día y repetición puede puntuarse en otra sesión")
    check(True, "se admite una fila de repetición sin puntuar (valor NULL)")
    try:
        c.execute("INSERT INTO puntuaciones (patient_id, fecha, exercise_id, repeticion, valor) VALUES ('p1','2026-10-02','e1',3,9)"); check(False, "debería rechazar valor 9")
    except sqlite3.IntegrityError: check(True, "rechaza una puntuación fuera de 0 a 3")

print("\n[3] La migración es atómica (si falla, no deja la base a medias)")
path = f'{W}/roto.db'; c = conn(path); schema_v1(c); seed(c, False)
c.execute("CREATE TABLE puntuaciones_antigua (x)")      # fuerza un fallo en el RENAME
try: migrate(c); check(False, "debía fallar")
except sqlite3.OperationalError: pass
check(c.execute("SELECT COUNT(*) FROM puntuaciones").fetchone()[0] == 3 and not tiene_col(c,'puntuaciones','repeticion'),
      "tras el fallo la tabla original sigue intacta y sin migrar")

print("\n[4] Restauración desde copias de distintas versiones")
res = func_body('restoreFrom')
base = re.findall(r'"((?:DELETE|INSERT)[^"]*)"', res[res.index('base := '):res.index('for _, q := range base')])
def sprintf_sql(marker):
    i = res.index(marker)
    return res[res.rindex('`', 0, i) + 1:res.index('`', i)]
SQL_BLOQ_ND = re.search(r'"(INSERT INTO bloques \(id, nombre, nivel\)[^"]*)"', res).group(1)
SQL_BE   = sprintf_sql('INSERT INTO bloque_ejercicios')
SQL_PAU  = sprintf_sql('INSERT INTO pautas')
SQL_PUN  = sprintf_sql('INSERT INTO puntuaciones')
SQL_PC   = sprintf_sql('INSERT INTO plan_casa')
SQL_HI   = sprintf_sql('INSERT INTO hitos')
SQL_EV   = sprintf_sql('INSERT INTO evaluaciones')
SQL_PG1  = re.search(r'`(INSERT INTO planes_guardados \(id[^`]*)`', res).group(1)
SQL_PG2  = re.search(r'`(INSERT INTO planes_guardados_items[^`]*)`', res).group(1)
SQL_PL1  = re.search(r'`(INSERT INTO plantillas \(id[^`]*)`', res).group(1)
SQL_PL2  = re.search(r'`(INSERT INTO plantilla_items[^`]*)`', res).group(1)
SQL_PA   = re.search(r'`(INSERT INTO plantilla_aplicaciones[^`]*)`', res).group(1)
SQL_INF  = re.search(r'`(INSERT INTO informes[^`]*)`', res).group(1)
SQL_PLN1 = re.search(r'`(INSERT INTO planes \(id[^`]*)`', res).group(1)
SQL_PLN2 = re.search(r'`(INSERT INTO plan_items[^`]*)`', res).group(1)
SQL_PLDUR = re.search(r'`(UPDATE plantillas SET duracion[^`]*)`', res).group(1)
SQL_PNDUR = re.search(r'`(UPDATE planes SET duracion[^`]*)`', res).group(1)
SQL_PLNOT = re.search(r'`(UPDATE plantillas SET notas[^`]*)`', res).group(1)
SQL_CS = re.search(r'`(INSERT INTO citas_series[^`]*)`', res).group(1)
SQL_CI = re.search(r'`(INSERT INTO citas \(id[^`]*)`', res).group(1)
SQL_CSCOL = re.search(r'`(UPDATE citas_series SET color[^`]*)`', res).group(1)
SQL_CSRAIZ = re.search(r'`(UPDATE citas_series SET raiz[^`]*)`', res).group(1)
SQL_CICOL = re.search(r'`(UPDATE citas SET color[^`]*)`', res).group(1)
SQL_PCOL = re.search(r'`(UPDATE patients SET color_cita[^`]*)`', res).group(1)
SQL_ARCH = re.search(r'`(UPDATE patients SET archivado[^`]*)`', res).group(1)
def src_tabla(c, t): return c.execute("SELECT COUNT(*) FROM src.sqlite_master WHERE type='table' AND name=?", (t,)).fetchone()[0] > 0
def src_col(c, t, col): return c.execute("SELECT COUNT(*) FROM pragma_table_info(?, 'src') WHERE name=?", (t, col)).fetchone()[0] > 0
def restore(c, srcpath):
    c.execute(f"ATTACH DATABASE '{srcpath}' AS src")
    try:
        c.execute('BEGIN')
        for q in base: c.execute(q)
        if src_tabla(c, 'bloques'):
            c.execute(SQL_BLOQ_ND % ('nivel' if src_col(c,'bloques','nivel') else "''"))
        if src_tabla(c, 'bloque_ejercicios'): c.execute(SQL_BE % ('posicion' if src_col(c,'bloque_ejercicios','posicion') else 'rowid'))
        if src_col(c, 'patients', 'archivado'): c.execute(SQL_ARCH)
        a = 'asignacion' if src_col(c,'pautas','asignacion') else "''"
        b = 'bloque_id'  if src_col(c,'pautas','bloque_id')  else "''"
        o = 'orden'      if src_col(c,'pautas','orden')      else "0"
        d = 'dias'       if src_col(c,'pautas','dias')       else "''"
        ss = 'sesion'    if src_col(c,'pautas','sesion')     else "''"
        c.execute(SQL_PAU % (a, b, o, d, ss))
        if src_tabla(c, 'plan_casa'):
            n = 'nota' if src_col(c,'plan_casa','nota') else "''"; g = 'grupo' if src_col(c,'plan_casa','grupo') else "''"; ng = 'nota_grupo' if src_col(c,'plan_casa','nota_grupo') else "''"
            c.execute(SQL_PC % (n, g, ng))
        if src_tabla(c, 'hitos'): c.execute(SQL_HI % ('fotos' if src_col(c,'hitos','fotos') else "'[]'"))
        if src_tabla(c, 'evaluaciones'): c.execute(SQL_EV % ('fotos' if src_col(c,'evaluaciones','fotos') else "'[]'"))
        if src_tabla(c, 'planes_guardados') and src_tabla(c, 'planes_guardados_items'): c.execute(SQL_PG1); c.execute(SQL_PG2)
        if src_tabla(c, 'plantillas') and src_tabla(c, 'plantilla_items'):
            c.execute(SQL_PL1)
            if src_col(c, 'plantillas', 'notas'): c.execute(SQL_PLNOT)
            if src_col(c, 'plantillas', 'duracion') and src_col(c, 'plantillas', 'unidad'): c.execute(SQL_PLDUR)
            c.execute(SQL_PL2)
        if src_tabla(c, 'planes') and src_tabla(c, 'plan_items'):
            c.execute(SQL_PLN1)
            if src_col(c, 'planes', 'duracion') and src_col(c, 'planes', 'unidad'): c.execute(SQL_PNDUR)
            c.execute(SQL_PLN2)
        if src_tabla(c, 'informes'): c.execute(SQL_INF)
        if src_tabla(c, 'plantilla_aplicaciones'): c.execute(SQL_PA)
        if src_col(c, 'patients', 'color_cita'): c.execute(SQL_PCOL)
        if src_tabla(c, 'citas_series'):
            c.execute(SQL_CS)
            if src_col(c, 'citas_series', 'color'): c.execute(SQL_CSCOL)
            if src_col(c, 'citas_series', 'raiz'): c.execute(SQL_CSRAIZ)
        if src_tabla(c, 'citas'):
            c.execute(SQL_CI)
            if src_col(c, 'citas', 'color'): c.execute(SQL_CICOL)
        c.execute(SQL_PUN % ('sesion' if src_col(c,'puntuaciones','sesion') else "''", 'repeticion' if src_col(c,'puntuaciones','repeticion') else '1'))
        if src_tabla(c, 'ajustes'):
            c.execute("DELETE FROM ajustes"); c.execute("INSERT INTO ajustes (clave, valor) SELECT clave, valor FROM src.ajustes")
        c.execute('COMMIT')
    finally:
        c.execute('DETACH DATABASE src')

# destino con datos distintos, que deben desaparecer al restaurar
def destino(name):
    p = f'{W}/{name}.db'; c = conn(p); migrate(c)
    c.executescript("INSERT INTO exercises (id,nombre) VALUES ('zz','Otro'); INSERT INTO patients (id,nombre) VALUES ('pz','Zoe'); INSERT INTO bloques (id,nombre,nivel) VALUES ('bz','Otro bloque','C');")
    return c
for nombre in ('v1', 'v2'):
    c = destino('dest_' + nombre); restore(c, f'{W}/{nombre}.db')
    check(c.execute("SELECT COUNT(*) FROM patients WHERE id='pz'").fetchone()[0] == 0, f"[{nombre}] los datos actuales se sustituyen")
    check(c.execute("SELECT COUNT(*), COUNT(valor), MIN(repeticion) FROM puntuaciones").fetchone() == (5, 4, 1), f"[{nombre}] 5 filas (3 de antes, 1 vacía y 1 de otra sesión) restauradas, repetición mínima 1")
    check(c.execute("SELECT COUNT(*) FROM pautas").fetchone()[0] == 2, f"[{nombre}] pautas restauradas")
    if nombre == 'v2':
        check(c.execute("SELECT nombre, nivel FROM bloques").fetchall() == [('Bloque viejo', '')], "[v2] bloque restaurado con nivel vacío")
        check(c.execute("SELECT valor FROM ajustes WHERE clave='pautasColapsadas'").fetchone()[0] == '1', "[v2] ajustes restaurados")
# copia de la versión actual con nivel
cur = conn(f'{W}/actual.db'); migrate(cur)
cur.executescript("INSERT INTO exercises (id,nombre) VALUES ('a','A'),('b','B'); INSERT INTO bloques VALUES ('bk1','Pivoteo','A'); INSERT INTO bloque_ejercicios (bloque_id, exercise_id, posicion) VALUES ('bk1','a',1),('bk1','b',2); INSERT INTO patients (id,nombre) VALUES ('p','P'); INSERT INTO puntuaciones (patient_id, fecha, exercise_id, sesion, repeticion, valor) VALUES ('p','2026-10-02','a','',1,2),('p','2026-10-02','a','',2,NULL),('p','2026-10-02','a','c1',1,3);")
cur.executescript("INSERT INTO plan_casa (id,patient_id,fecha,exercise_id,bloque_id,orden,nota,grupo,nota_grupo) VALUES ('pc1','p','2026-06-01','a','bk1',1,'3 series de 10','g1','Despacio'),('pc2','p','2026-06-01','b','',2,'','',''); INSERT INTO hitos VALUES ('h1','p','2026-03-10','Primera valoración','[a.jpg]'); INSERT INTO evaluaciones VALUES ('ev1','p','2026-03-10','Flexión 40','[]'); INSERT INTO planes_guardados VALUES ('g1','p','Plan A','2026-10-22'); INSERT INTO planes_guardados_items (id,plan_id,fecha,exercise_id,bloque_id,orden,nota,grupo,nota_grupo) VALUES ('gi1','g1','2026-06-01','a','',1,'x','','');  INSERT INTO plantillas (id,nombre,semanas,creada) VALUES ('t1','Semana A',2,'2026-10-22'); INSERT INTO plantilla_items (id,plantilla_id,dia,exercise_id,bloque_id,orden,nota,grupo,nota_grupo) VALUES ('i1','t1',1,'a','bk1',1,'10 reps','g','Lento'),('i2','t1',3,'b','',1,'','',''); INSERT INTO plantilla_aplicaciones VALUES ('a1','t1','p','2026-10-19','2026-10-25','2026-10-23'); INSERT INTO informes VALUES ('if1','p','informe','Informe.pdf','/Users/x/Informe.pdf','2026-10-25T10:00:00Z','2026-10-01','2026-10-25','');")
cur.executescript("UPDATE plantillas SET notas = 'Beber agua' WHERE id = 't1'; INSERT INTO planes (id,patient_id,nombre,inicio,fin,fin_manual,semanas,notas,creado,plantilla_id,duracion,unidad) VALUES ('pl1','p','Fase 1','2026-10-28','2026-11-12',1,2,'Sin dolor','2026-10-26','t1',10,'dias'); UPDATE plantillas SET duracion = 1, unidad = 'meses' WHERE id = 't1'; INSERT INTO plan_items VALUES ('pi1','pl1',3,'a','bk1',1,'10 reps','g','Lento'),('pi2','pl1',0,'b','',1,'cuando quiera','','');")
cur.executescript("UPDATE patients SET archivado = 1 WHERE id = 'p'; INSERT INTO pautas (id,patient_id,exercise_id,desde,hasta,asignacion,bloque_id,orden,dias,sesion) VALUES ('pd1','p','a','2026-10-01',NULL,'g9','',1,'14','c:x');")
cur.executescript("INSERT INTO citas_series VALUES ('s1','p','24','17:00',45,'2026-10-27','','Traer informe','[\"2026-11-03\"]','2026-10-27','7','r1'); INSERT INTO citas VALUES ('c1','p','2026-10-27','17:00',45,'','s1','2026-10-27',0,'7'),('c2','p','2026-10-30','18:15',30,'','s1','2026-10-29',1,'11'),('c3','p','2026-11-02','09:00',60,'Primera','','',0,''); UPDATE patients SET color_cita = '7' WHERE id = 'p';")
cur.execute("VACUUM INTO ?", (f'{W}/copia_actual.db',))
check(os.path.exists(f'{W}/copia_actual.db'), "VACUUM INTO crea la copia")
c = destino('dest_actual'); c.execute("INSERT INTO google_eventos VALUES ('c1','ev1','f','r')"); c.execute("INSERT INTO google_sync VALUES ('calendario','cal@group')")
restore(c, f'{W}/copia_actual.db')
check(c.execute("SELECT color FROM citas ORDER BY id").fetchall() == [('7',), ('11',), ('',)] and c.execute("SELECT color FROM citas_series").fetchone()[0] == '7' and c.execute("SELECT color_cita FROM patients WHERE id='p'").fetchone()[0] == '7', "[actual] los colores de citas, series y pacientes se restauran")
check(c.execute("SELECT dias, hora, duracion, desde, hasta, nota, excluidas FROM citas_series").fetchall() == [('24', '17:00', 45, '2026-10-27', '', 'Traer informe', '["2026-11-03"]')], "[actual] las series de citas se restauran")
check(c.execute("SELECT id, fecha, hora, duracion, serie_id, fecha_serie, modificada FROM citas ORDER BY id").fetchall() == [('c1', '2026-10-27', '17:00', 45, 's1', '2026-10-27', 0), ('c2', '2026-10-30', '18:15', 30, 's1', '2026-10-29', 1), ('c3', '2026-11-02', '09:00', 60, '', '', 0)], "[actual] las citas se restauran (con su serie y si se cambiaron aparte)")
check(c.execute("SELECT COUNT(*) FROM google_eventos").fetchone()[0] == 1 and c.execute("SELECT valor FROM google_sync").fetchone()[0] == 'cal@group', "[actual] restaurar no toca la relación con Google (la siguiente sincronización pone Google al día)")
check(c.execute("SELECT nombre, nivel FROM bloques").fetchall() == [('Pivoteo', 'A')], "[actual] el nivel del bloque se restaura")
check(c.execute("SELECT sesion, repeticion, valor FROM puntuaciones ORDER BY sesion, repeticion").fetchall() == [('', 1, 2), ('', 2, None), ('c1', 1, 3)], "[actual] repeticiones, fila vacía y sesiones se restauran")
check(c.execute("SELECT sesion FROM pautas WHERE id='pd1'").fetchone()[0] == 'c:x' and c.execute("SELECT raiz FROM citas_series").fetchone()[0] == 'r1', "[actual] la sesión de las pautas y la raíz de las series se restauran")
check(c.execute("SELECT nota, grupo, nota_grupo FROM plan_casa WHERE id='pc1'").fetchone() == ('3 series de 10', 'g1', 'Despacio'), "[actual] las notas del plan en casa se restauran")
check(c.execute("SELECT nombre, semanas FROM plantillas").fetchall() == [('Semana A', 2)] and c.execute("SELECT COUNT(*) FROM plantilla_items").fetchone()[0] == 2, "[actual] las plantillas y sus ejercicios se restauran")
check(c.execute("SELECT patient_id, desde FROM plantilla_aplicaciones").fetchall() == [('p', '2026-10-19')], "[actual] las aplicaciones de plantilla se restauran")
check(c.execute("SELECT patient_id, ruta FROM informes").fetchall() == [('p', '/Users/x/Informe.pdf')], "[actual] el registro de PDF generados se restaura")
check(c.execute("SELECT archivado FROM patients WHERE id='p'").fetchone()[0] == 1, "[actual] el paciente archivado sigue archivado")
check(c.execute("SELECT dias FROM pautas WHERE id='pd1'").fetchone()[0] == '14', "[actual] los días de la semana de una pauta se restauran")
check(c.execute("SELECT nombre, inicio, fin, fin_manual, semanas, notas, plantilla_id FROM planes").fetchall() == [('Fase 1', '2026-10-28', '2026-11-12', 1, 2, 'Sin dolor', 't1')], "[actual] los planes en casa se restauran con fechas, semanas y notas")
check(sorted(c.execute("SELECT dia, nota FROM plan_items").fetchall()) == [(0, 'cuando quiera'), (3, '10 reps')], "[actual] sus ejercicios (también los «a elegir», día 0) se restauran")
check(c.execute("SELECT notas FROM plantillas").fetchone()[0] == 'Beber agua', "[actual] las notas de las plantillas se restauran")
check(c.execute("SELECT duracion, unidad FROM planes").fetchone() == (10, 'dias') and c.execute("SELECT duracion, unidad FROM plantillas").fetchone() == (1, 'meses'), "[actual] la duración (número y unidad) de planes y plantillas se restaura")
check(c.execute("SELECT COUNT(*) FROM plan_casa").fetchone()[0] == 2 and c.execute("SELECT nota FROM hitos").fetchone()[0] == 'Primera valoración' and c.execute("SELECT evaluacion FROM evaluaciones").fetchone()[0] == 'Flexión 40', "[actual] plan en casa, hitos y evaluaciones se restauran")
check(c.execute("SELECT descripcion FROM planes_guardados").fetchone()[0] == 'Plan A' and c.execute("SELECT COUNT(*) FROM planes_guardados_items").fetchone()[0] == 1, "[actual] planes guardados se restauran")
# borrar un ejercicio o paciente en cascada
c.execute("PRAGMA foreign_keys=ON"); c.execute("DELETE FROM exercises WHERE id='b'")
check(c.execute("SELECT COUNT(*) FROM plan_casa").fetchone()[0] == 1 and c.execute("SELECT COUNT(*) FROM plantilla_items").fetchone()[0] == 1, "borrar un ejercicio quita sus entradas del plan en casa y de las plantillas")
c.execute("DELETE FROM plantillas WHERE id='t1'")
check(c.execute("SELECT COUNT(*) FROM plantilla_items").fetchone()[0] == 0, "borrar una plantilla borra sus ejercicios")
c.execute("DELETE FROM patients WHERE id='p'")
check(c.execute("SELECT COUNT(*) FROM citas").fetchone()[0] == 0 and c.execute("SELECT COUNT(*) FROM citas_series").fetchone()[0] == 0, "borrar un paciente borra sus citas y series")
check(c.execute("SELECT COUNT(*) FROM google_eventos").fetchone()[0] == 1, "la tabla de eventos de Google no depende de las citas (se guardan de nuevo en cada cambio)")
check(c.execute("SELECT COUNT(*) FROM plan_casa").fetchone()[0] == 0 and c.execute("SELECT COUNT(*) FROM hitos").fetchone()[0] == 0, "borrar un paciente quita su plan y sus hitos")
# las copias antiguas (v1, v2) no traen estas tablas: restaurar no falla y las deja vacías
c2 = destino('dest_v1b'); restore(c2, f'{W}/v1.db')
check(c2.execute("SELECT COUNT(*) FROM plantillas").fetchone()[0] == 0, "copia antigua sin plantillas: se restaura sin errores")
check(c2.execute("SELECT COUNT(*) FROM plan_casa").fetchone()[0] == 0 and c2.execute("SELECT COUNT(*) FROM hitos").fetchone()[0] == 0, "copia antigua sin plan/hitos: se restaura sin errores")
# copia de la versión anterior del plan en casa (sin columnas de notas)
old = conn(f'{W}/plan_viejo.db')
migrate(old)
old.executescript("DROP TABLE plan_casa; CREATE TABLE plan_casa (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL, fecha TEXT NOT NULL, exercise_id TEXT NOT NULL, bloque_id TEXT NOT NULL DEFAULT '', orden INTEGER NOT NULL DEFAULT 0); INSERT INTO exercises (id,nombre) VALUES ('a','A'); INSERT INTO patients (id,nombre) VALUES ('p','P'); INSERT INTO plan_casa VALUES ('x','p','2026-06-01','a','',1);")
old.commit(); old.close()
c3 = destino('dest_planviejo'); restore(c3, f'{W}/plan_viejo.db')
check(c3.execute("SELECT nota, grupo, nota_grupo FROM plan_casa").fetchall() == [('', '', '')], "plan en casa sin notas (copia anterior): se restaura con notas vacías")

# --- consultas de guardar y de la sincronización con Google ---
print('\n[citas y Google: consultas]')
SAVE = func_body('saveState')
GO = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'code', 'google.go'), encoding='utf-8').read()
c = conn(f'{W}/citas.db'); migrate(c)
c.execute("INSERT INTO patients (id,nombre,apellidos) VALUES ('p','Ana','López')")
q_serie = re.search(r'`(INSERT OR IGNORE INTO citas_series[^`]*)`', SAVE).group(1)
q_cita = re.search(r'`(INSERT OR IGNORE INTO citas \(id[^`]*)`', SAVE).group(1)
c.execute(q_serie, ('s1', 'p', '24', '17:00', 45, '2026-10-27', '', '', '[]', '2026-10-27', '7', 's1'))
c.execute(q_cita, ('c1', 'p', '2026-10-27', '17:00', 45, '', 's1', '2026-10-27', 0, '7'))
check(c.execute("SELECT COUNT(*) FROM citas").fetchone()[0] == 1, "guardar una serie y una cita")
for q in re.findall(r'`((?:SELECT|INSERT|DELETE)[^`]*google_[^`]*)`', GO) + [re.search(r'`(SELECT id, patient_id, fecha, hora, duracion, nota, color FROM citas[^`]*)`', GO).group(1)]:
    n = q.count('?'); c.execute(q, tuple(['x'] * n)); 
check(True, f"las consultas de google.go son válidas")
c.execute("INSERT OR REPLACE INTO google_sync (clave, valor) VALUES ('activo','1')"); c.execute("INSERT OR REPLACE INTO google_sync (clave, valor) VALUES ('activo','0')")
check(c.execute("SELECT valor FROM google_sync WHERE clave='activo'").fetchone()[0] == '0', "google_sync guarda un valor por clave")

# --- versión del modelo (PRAGMA user_version) ---
print('\n[versión del modelo]')
W2 = f'{W}/uv'; os.makedirs(W2, exist_ok=True)
for f_ in ('a.db', 'a_copia.db'):
    if os.path.exists(f'{W2}/{f_}'): os.remove(f'{W2}/{f_}')
c = sqlite3.connect(f'{W2}/a.db', isolation_level=None)
check(c.execute('PRAGMA user_version').fetchone()[0] == 0, 'una base de datos existente (anterior) tiene versión 0')
c.execute('CREATE TABLE patients (id TEXT)')
check(c.execute("SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?", ('patients',)).fetchone()[0] == 1, 'se detecta que ya hay datos (tabla patients)')
c.execute('BEGIN'); c.execute('PRAGMA user_version = 1'); c.execute('ROLLBACK')
check(c.execute('PRAGMA user_version').fetchone()[0] == 0, 'un paso fallido (ROLLBACK) no cambia la versión')
c.execute('BEGIN'); c.execute('PRAGMA user_version = 1'); c.execute('COMMIT')
check(c.execute('PRAGMA user_version').fetchone()[0] == 1, 'la versión se anota al confirmar el paso')
c.execute(f"VACUUM INTO '{W2}/a_copia.db'")
c.execute(f"ATTACH DATABASE '{W2}/a_copia.db' AS src")
check(c.execute('PRAGMA src.user_version').fetchone()[0] == 1, 'la copia conserva la versión y se puede leer desde la restauración')
print("\nRESULTADO:", "TODO OK" if ok else "HAY FALLOS"); sys.exit(0 if ok else 1)
