# Fisioterapia — documentación técnica y funcional

Aplicación local para que un fisioterapeuta registre ejercicios, los asigne a pacientes y puntúe cada
ejercicio (0–3) por repetición y día. Interfaz en español. Pensada para un Mac de un usuario no técnico, sin
herramientas de compilación: el desarrollador compila el binario y el usuario hace doble clic.

> **Para otro agente / futuras iteraciones:** lee primero las secciones 1, 2, 9 (reglas de trabajo) y 10
> (riesgos y estado de las pruebas). Mantén el estilo: un solo `main.go`, un solo `index.html`, sin
> frameworks ni paso de build para el frontend.

---

## 1. Resumen funcional

| Área | Qué hace |
|---|---|
| **Pacientes** | Alta/edición con nombre, apellidos, foto, fecha de alta, teléfono, email y observaciones. Buscador. |
| **Ejercicios** | Lista con buscador; crear, editar, **clonar** (mismo nombre + sufijo numérico) y eliminar. |
| **Bloques** | (Las secciones Ejercicios y Bloques son plegables y recuerdan su estado; cada bloque lista sus ejercicios en orden de ejecución, con opción para ocultar ese detalle: ajuste `bloquesDetalle`.) Agrupan ejercicios que se asignan juntos. Tienen **nivel opcional** (A/B/C u otro texto) y un **orden manual** de ejecución. Buscador y filtro por nivel. Importables desde JSON. |
| **Pautas** | Un paciente tiene ejercicios sueltos o bloques asignados, desde/hasta una fecha. Se asigna a uno o varios pacientes a la vez. Varios ejercicios por día. |
| **Calendario** | En la ficha del paciente: vista mes / semana / día. Cada celda muestra la media de las repeticiones puntuadas, con leyenda de colores y marca de «sin puntuar». |
| **Puntuación** | Por ejercicio y día hay N filas (una por repetición), cada una 0–3 o vacía. Se pueden añadir/quitar repeticiones. |
| **Resumen** | Por día/semana/mes o rango manual. Vistas: lista, gráfica de puntos, gráfica de líneas (desactivada si el rango es un solo día). |
| **Exportar PDF** | Un PDF por paciente (uno o varios a la vez) para un intervalo de fechas: nombre del paciente, gráfica de la puntuación media diaria y detalle de cada día (bloques con su nivel y ejercicios en orden de ejecución, con la puntuación de cada repetición y su media). Sin foto, teléfono, email, observaciones ni fecha de alta. Nombre propuesto `Informe_Apellidos_Nombre_desde_hasta.pdf`; se guarda donde elija el usuario (ver apartado 21) y queda en la pestaña «Informes» del paciente. |
| **Ajustes** | Copias automáticas (frecuencia, cuántas conservar), crear copia manual, lista de copias y restauración, carpeta de datos, borrar todo. |
| **Persistencia de UI** | El estado de los acordeones (pautas, secciones de Ajustes, secciones de la ventana del día) se guarda en la BD. |
| **Versión** | Se muestra discretamente abajo a la derecha (`vX.Y.Z`) para depurar con el usuario. |

Reglas de negocio relevantes:

- **Lo único puntuable son los ejercicios**, nunca los bloques. Un bloque solo agrupa y ordena.
- Un ejercicio asignado dentro de un bloque comparte `asignacion` con el resto del bloque; los sueltos tienen su propia `asignacion`.
- La media del calendario usa solo repeticiones con valor (las filas vacías `null` no cuentan).
- Cambiar una pauta de modo que un día deje de estar cubierto **avisa** si hay puntuaciones reales que se perderían (las filas vacías se limpian sin avisar). Si se acepta, se borran.
- Eliminar un ejercicio de un día concreto parte la pauta (ver `changePautas`).
- Los niveles son opcionales: un bloque puede no tener nivel («Sin nivel» es un filtro).
- Aún **no se muestra el nivel en la sección del paciente** (pendiente por decisión del usuario).

---

## 2. Arquitectura

```
Navegador (index.html, JS vanilla)  <—HTTP JSON—>  Servidor Go (main.go, 127.0.0.1:8765)  <—>  SQLite (fisioterapia.db)
                                                          └─ fotos/  copias/  (en la carpeta de datos)
```

- **Un binario**: `main.go` embebe `index.html` con `//go:embed`. Al servirlo sustituye `__APP_VERSION__` por la versión de compilación.
- **Solo escucha en `127.0.0.1:8765`** y rechaza peticiones con `Host`/`Origin` ajenos (`soloLocal`).
- **Sincronización por estado completo**: `GET /api/state` devuelve todo; `PUT /api/state` **sustituye todo** en una transacción. El cliente solo hace PUT si el JSON cambió (`ultimoGuardado`).
- **Control de revisión** (anti «dos ventanas»): el servidor mantiene `revision` en memoria, la devuelve en la cabecera `X-Revision` y el cliente la reenvía en cada PUT. Si no coincide → `409` y la ventana se recarga sin pisar datos.
- **Concurrencia**: un `sync.Mutex` global `mu` protege `db`, `dataDir`, `fotosDir`, `copiasDir` y `revision`. Cada handler lo toma; los helpers no. `db.SetMaxOpenConns(1)`.
- **Arranque**: abre la carpeta de datos (por defecto `~/Documents/Fisioterapia`, o la guardada en `~/Library/Application Support/Fisioterapia/config.json`, o `-dir`), migra el esquema, lanza el planificador de copias y en macOS ejecuta `open http://127.0.0.1:8765/`.
- **Cierre**: se cierra la ventana de Terminal. No hay servicio en segundo plano.

### Ficheros del proyecto

```
.
├── go.mod / go.sum     Módulo Go «fisioterapia» (en la raíz, para que el módulo incluya code/ y docs/)
├── code/               La aplicación (package main)
│   ├── main.go         Todo el backend salvo Google Calendar
│   ├── google.go       Sincronización con Google Calendar (OAuth y API), desde la 0.0.5 (ver 26)
│   ├── index.html      Todo el frontend (HTML+CSS+JS)
│   ├── pdf-lib.min.js  pdf-lib 1.17.1 (MIT), embebida con go:embed (debe estar junto a main.go)
│   └── *_test.go       Pruebas Go (ver 8)
├── docs/               CHANGELOG.md y AYUDA.md (embebidos en el binario por docs/embed.go, paquete «docs»;
│                       go:embed solo alcanza ficheros de su carpeta), DOCUMENTACION.md (este documento),
│                       ACTUALIZAR.txt (va dentro de cada zip), pdf-lib.LICENSE.md
├── internal/           bloques_dmi.json: catálogo importable de 95 bloques / 215 ejercicios (generado con tests/gen_bloques.py)
├── scripts/            build.sh, Fisioterapia.command (Mac), Fisioterapia.bat (Windows)
├── tests/              Batería de pruebas Python/Playwright y servidor simulado (ver 8)
└── dist/               Ejecutables y .zip que se entregan a la usuaria. NO se sube a git (.gitignore)
```


---

## 3. Compilar y ejecutar

Requisitos: Go ≥ 1.22 (usa `net/http` con patrones de método, `atomic.Int32`).

```bash
go mod init fisioterapia          # solo la primera vez, en la RAÍZ del repositorio
go get modernc.org/sqlite         # driver SQLite en Go puro (sin CGO)
scripts/build.sh 1.6.0            # compila dist/bin/fisioterapia con la versión visible en la app
dist/bin/fisioterapia             # o: dist/bin/fisioterapia -dir /ruta/de/datos
go run ./code                     # alternativa rápida para desarrollar (versión «dev»)
```

- `build.sh` se puede lanzar desde cualquier carpeta; siempre trabaja desde la raíz y deja **todo en `dist/`**.
- Otra arquitectura de Mac: `MAC_ARCH=amd64 scripts/build.sh X mac` (Intel; por defecto Apple Silicon).
- Flag `-dir`: usa esa carpeta de datos **solo en esa ejecución** (no cambia la configuración guardada).
- Cada carpeta de datos es un juego independiente: `fisioterapia.db`, `fotos/`, `copias/`.

---

## 4. Modelo de datos (SQLite)

```sql
exercises(id PK, nombre)
patients(id PK, nombre, apellidos, fecha_alta, telefono, email, observaciones, foto_archivo)
pautas(id PK, patient_id FK, exercise_id FK, desde, hasta NULL,
       asignacion, bloque_id, orden)                 -- asignacion: agrupa filas de un mismo bloque/ejercicio suelto
puntuaciones(patient_id, fecha, exercise_id, repeticion, valor NULL CHECK 0..3,
             PK(patient_id, fecha, exercise_id, repeticion))   -- valor NULL = fila de repetición sin puntuar
ajustes(clave PK, valor)                             -- ajustes globales (ver 4.1)
bloques(id PK, nombre, nivel)                        -- nivel '' = sin nivel
bloque_ejercicios(bloque_id FK, exercise_id FK, posicion,   -- posicion = orden manual de ejecución
                  PK(bloque_id, exercise_id))
```

Todas las FK son `ON DELETE CASCADE` y `foreign_keys` está activado. Fechas en `YYYY-MM-DD` (texto).

**Claves en el cliente.** `db.puntuaciones` es un objeto `{"pid|fecha|eid|rep": 0..3 | null}`. Al guardar se parte por `|` (los ids no deben contener `|`; se generan con `uid()`).

### 4.1 Ajustes globales (`ajustes`)

| Clave | Valores | Uso |
|---|---|---|
| `backupAuto` | `'1'` (por defecto) / `'0'` | Activa las copias automáticas. |
| `backupCadaDias` | `1,2,7,15,30` (por defecto 1) | Frecuencia, en días naturales. |
| `backupConservar` | `7,14,30,60,90` (por defecto 14) | Cuántas copias *automáticas* se conservan. |
| `acc.<id>` | `'1'` abierto / `'0'` cerrado | Estado de acordeones: `pautas`, `ejercicios`, `bloques`, `ajAuto`, `ajCopias`, `ajCarpeta`, `ajBorrar`, `secAdd`, `secPun`. |
| `bloquesDetalle` | `'1'` (por defecto) / `'0'` | Mostrar los ejercicios dentro de cada bloque en la lista de bloques. |
| `pautasColapsadas` | `'1'` | Clave antigua; solo se lee como valor por defecto de `acc.pautas`. |

### 4.2 Migraciones (`migrateDB`)

- Las tablas se crean directamente con el esquema actual (`CREATE TABLE IF NOT EXISTS`).
- Las columnas añadidas después (`pautas.asignacion/bloque_id/orden`, `bloques.nivel`, `bloque_ejercicios.posicion`) se añaden con `ALTER TABLE` **solo si faltan** (`tieneColumna`), y cualquier error se devuelve (no se ignora).
- `puntuaciones` antigua (sin `repeticion`) se migra en **una transacción** (RENAME → CREATE → INSERT con `repeticion=1` → DROP).
- Las filas de `bloque_ejercicios` previas a `posicion` toman `posicion = rowid`.
- **Regla:** toda columna/tabla nueva debe (1) crearse en `CREATE TABLE`, (2) añadirse a la lista `columnas` si es una columna, (3) tratarse en `loadState`, `saveState` **y** `restoreFrom` (que debe tolerar copias antiguas sin esa columna).

---

## 5. API HTTP

Todas bajo `127.0.0.1:8765`. Cuerpos y respuestas JSON.

| Método y ruta | Descripción |
|---|---|
| `GET /` | `index.html` con la versión inyectada (`Cache-Control: no-store`). |
| `GET /api/state` | Estado completo + cabecera `X-Revision`. |
| `PUT /api/state` | Sustituye todo (transacción). Cabecera `X-Revision`; `409` si está desfasada; devuelve la nueva. Límite 200 MB. Las fotos llegan como `data:image/...;base64` y se guardan como `fotos/<hash>.jpg`; las ya guardadas llegan como `/fotos/<archivo>`. Se descartan filas huérfanas (pautas/puntuaciones de ids inexistentes, valores fuera de 0–3). |
| `GET /fotos/{name}` | Sirve una foto de la carpeta activa. |
| `GET /pdf-lib.min.js` | La librería de PDF (se carga solo al exportar). |
| `POST /api/foto` | Cuerpo: un JPEG (la página lo reduce a 1600 px). Lo guarda en `fotos/<hash>.jpg` y devuelve `{"url":"/fotos/…"}`. La entrada que lo use lo enlaza al guardarse; `cleanFotos` no borra ficheros de menos de 1 h (fotos subidas a la espera de guardar) y sí los no referenciados por pacientes, hitos ni evaluaciones. |
| `POST /api/exportar?nombre=…[&carpeta=…\|&inicio=…]` | Cuerpo: un PDF (`%PDF-`). Con `carpeta` lo guarda dentro sin pisar nada; sin ella abre «Guardar como» (409 si se cancela). Temporal + renombrado. `nombreSeguro` elimina separadores de ruta y caracteres raros. Ver apartado 21. |
| `POST /api/informes/abrir?id=…[&modo=carpeta]` · `GET /api/informes/existen` | Abre un PDF registrado o su carpeta; qué PDF registrados siguen existiendo. Ver apartado 21. |
| `POST /api/copia` | Crea una copia manual `copias/copia-AAAA-MM-DD_HHMMSS/`. |
| `GET /api/copias` | Lista de copias (`nombre`, `fecha`, `auto`). |
| `POST /api/restaurar` `{nombre}` | Hace antes una copia de seguridad del estado actual y restaura (una transacción). Tolera copias antiguas. |
| `GET /api/copias-auto` | `{ultima, error}` de las copias automáticas. |
| `GET /api/copiando` | `{copiando: bool}`. **No toma `mu`**, para poder consultarse mientras se copia. |
| `GET/POST /api/ajustes` | GET: `{dataDir, defaultDir}`. POST `{dataDir}`: cambia de carpeta de datos y lo guarda en `config.json`. |
| `POST /api/elegir-carpeta` | Abre el selector de carpetas de macOS (`osascript`). |
| `POST /api/salir` | Botón «Salir»: espera a que no haya copia en curso (409 si `copiando`), responde y apaga el servidor (`http.Server.Shutdown` + `db.Close()`); el proceso termina y la ventana negra queda libre. Ver apartado 23. |
| `GET /api/changelog` · `GET /api/ayuda` | Novedades (`{version, texto}`) y manual (`AYUDA.md`). Ver apartados 20 y 22. |

Todas pasan por `soloLocal` (Host ∈ {`127.0.0.1:8765`, `localhost:8765`}; si hay `Origin`, igual).

---

## 6. Frontend (`index.html`)

JS vanilla, estado en memoria en `db` (misma forma que `/api/state`) y UI en `ui`. `render()` repinta la vista activa entera con `innerHTML`.

**Vistas** (`ui.view`): `pacientes`, `paciente` (ficha), `ejercicios` (ejercicios + gestión de bloques), `ajustes`.

Funciones clave:

| Función | Papel |
|---|---|
| `load()` / `save()` | Sincronización; `save()` compara con `ultimoGuardado`, envía `X-Revision`, gestiona el `409`. |
| `setAjuste(clave, valor)` | Ajuste global + `save()`. |
| `acordeon(id, titulo, cuerpo, defecto)`, `accAbierto`, `accGuardar` | Acordeones con estado persistente. `accGuardar` ignora el aviso inicial del navegador. |
| `repsDe(pid, dia, eid)` | Repeticiones de un ejercicio/día. **Usa un índice perezoso `idxPunt`**: tras cualquier cambio directo de `db.puntuaciones` hay que poner `idxPunt = null`. |
| `resumenDia`, `fmtPunt`, `filasDia`, `setScore`, `addRep`, `quitarRep` | Puntuación por repetición. |
| `activePautas`, `exercisesOn`, `coveredBy` | Qué ejercicios tiene un paciente un día. |
| `changePautas(mutate, confirmarSiempre)` | Único punto por el que cambiar pautas: calcula qué puntuaciones se pierden, avisa y las borra. |
| `openAssign` / `saveAssign` | Asignar bloques y ejercicios (con buscador, selector de nivel, marcar/desmarcar visibles). |
| `openBloque` / `saveBloque` | Editar bloque, nivel (opcional, con sugerencias) y orden (↑/↓, `sincronizarOrden`). |
| `leerImportBloques` / `aplicarImportBloques` | Asistente de importación del JSON. |
| `datosRango`, `listadoResumen`, `graficoPuntos`, `graficoLineas`, `resumenHTML` | Pestaña Resumen (SVG a mano, sin librerías). |
| `viewAjustes`, `loadCopias`, `crearCopia`, `restaurarCopia`, `consultarBloqueo` | Ajustes y copias. |

**Anchos y formularios:** `main` llega a 1760 px; las ventanas (`showModal(html, ancho)`) miden hasta 980 px (1500 px con `ancho = true`: asignar, bloque y día). Los formularios usan rejillas que se adaptan (`.gridf` auto-fit, `.split` dos paneles, `.dia-grid`), las listas de selección usan columnas CSS (`.lista-sel`) y las listas de pacientes/ejercicios/bloques también (`column-width`, orden alfabético de arriba abajo en cada columna). Comprobado sin desbordes entre 480 y 2200 px.

Interfaz: texto siempre escapado con `esc()` al ir a `innerHTML`. Menú lateral de secciones en la ficha. Todas las ventanas modales tienen una **X** y se cierran con Escape.

### 6.1 Formato de importación de bloques

> Desde la 0.0.5 hay además un formato propio de exportación (ver 26.1). El importador acepta los dos.

```json
{ "formato": "fisioterapia-bloques", "version": 2,
  "bloques": [ { "id": "A1", "nombre": "Pivoteo supino 90°", "nivel": "A", "numero": 1,
                 "ejercicios": ["Pivoteo supino 90° – Derecha", "Pivoteo supino 90° – Izquierda"] } ] }
```

- `nivel` es opcional. El importador crea los ejercicios con id `<bloque>-<n>`, **omite bloques cuyo id ya existe** y no borra nada. Muestra un desglose por nivel antes de aplicar.
- Los nombres de ejercicio son **completos** («Bloque – Variante»); en bloques de un único ejercicio, el ejercicio se llama como el bloque.
- `internal/bloques_dmi.json` se genera con `tests/gen_bloques.py internal/bloques_dmi.json` (A:35, B:30, C:30 bloques; 215 ejercicios). Las decisiones interpretativas del PDF original están anotadas en la sección 10.

---

### 6.2 Exportación a PDF

- **Dónde se genera:** en el navegador, con pdf-lib (fuentes estándar Helvetica, codificación WinAnsi: cubre tildes, ñ, °, –, ·; cualquier otro carácter se sustituye por `?`). El servidor solo recibe los bytes y los guarda.
- **Funciones:** `datosPdf(p, desde, hasta)` (qué se muestra: por día, `exercisesOn` → grupos por `bloqueId` o «Ejercicios sueltos» → ejercicios con repeticiones y media), `pdfPaciente(p, desde, hasta)` (maquetación A4: cabecera, leyenda, gráfica vectorial, detalle con saltos de página y «(continuación)», pie «Nombre · Página n de N»), `openExportar(ids)` / `renderExportar` / `expPreset` / `generarExportacion` (ventana, presets «Este mes», «Últimas 4 semanas», «Todo el historial», progreso y resultado).
- **Nombre del fichero:** `Apellidos_Nombre_desde_hasta.pdf`; si dos pacientes del mismo lote dan el mismo nombre se añade `_2`, `_3`…
- **Reglas:** intervalo máximo 2 años; un paciente sin pautas en el periodo genera un PDF con «No hay ejercicios asignados en este periodo.» y sin gráfica.
- **Privacidad:** el PDF incluye solo el nombre del paciente (decisión del usuario). los PDF **no** forman parte de las copias de seguridad (están donde los guardó el usuario); su registro sí.
- **Para cambiar el contenido del PDF:** editar `datosPdf` (datos) y `pdfPaciente` (diseño). Las coordenadas están en puntos (A4 = 595×842); `y` es el cursor vertical (baja al avanzar).

## 7. Copias de seguridad

- **Formato:** carpeta `copias/<prefijo>AAAA-MM-DD_HHMMSS/` con `fisioterapia.db` (`VACUUM INTO`, consistente) y `fotos/`.
- **Tipos y prefijos:** manual y previa-a-restaurar → `copia-…`; automática → `copia-auto-…`. **Solo se borran solas las `copia-auto-*`** (las más antiguas, hasta quedarse con `backupConservar`).
- **Planificador:** goroutine que espera 20 s tras arrancar y después comprueba cada 15 min (`copiaDebida`). Con frecuencia diaria hace una copia el primer momento de cada día natural con la app abierta; si no se abre la app, no hay copia (no hay servicio en segundo plano). Si no hay pacientes ni ejercicios, no copia. Si una copia falla se borra lo parcial y el error aparece en Ajustes.
- **Bloqueo de pantalla:** el contador `copiando` está activo durante la copia (en la automática, 3 s antes para dar tiempo a que se guarden los últimos cambios). La UI consulta `/api/copiando` cada segundo y muestra un aviso a pantalla completa, poniendo `inert` en cabecera, contenido y modales.
- **Restaurar:** hace antes una copia `copia-…` del estado actual (nunca se borra sola), copia los datos con `ATTACH` en una transacción, copia las fotos que falten y borra las no referenciadas.
- Las copias están en la misma carpeta de datos: **no protegen frente a un fallo de disco** (ver sugerencias).

### `Fisioterapia.command`

Script para doble clic: entra en su carpeta; si la app ya responde en `:8765` **con la misma versión** (compara `GET /api/changelog` con `./fisioterapia -version`) solo abre el navegador; si no responde o es otra versión, quita la cuarentena de macOS al binario (`xattr -d com.apple.quarantine`), le da permiso de ejecución y lo lanza (si había otra versión abierta, el propio binario la cierra: ver apartado 23). La ventana de Terminal debe quedar abierta mientras se usa la app; para cerrar, botón «Salir».

---

## 8. Pruebas (carpeta `tests/`)

El entorno de desarrollo del agente **no pudo descargar `modernc.org/sqlite`** (proxy de Go bloqueado), por lo que el Go se verificó de otra forma:

| Prueba | Cómo se ejecuta | Qué cubre |
|---|---|---|
| `test_sql.py` | `python3 tests/test_sql.py` | Extrae las sentencias SQL de `code/main.go` y las ejecuta con el `sqlite3` de Python: migraciones desde esquemas v1/v2, idempotencia, atomicidad, restauración desde copias antiguas/nuevas, `VACUUM INTO`. Resultado esperado: `TODO OK`. |
| `test_ui.py` + `mock_server.py` | `python3 tests/mock_server.py 8800 &` y `python3 tests/test_ui.py 8800` (Playwright + Chromium; `PLAYWRIGHT_BROWSERS_PATH`/ruta de Chromium a ajustar) | Flujos de UI contra un servidor simulado en memoria (incluida la exportación a PDF real: se genera el PDF en Chromium y se verifica con `pdftotext`/`pdfinfo`/`pdftoppm`, que deben estar instalados; importación de 95 bloques, búsqueda, niveles, orden, asignación, repeticiones y medias, avisos, resumen/gráficas, menú lateral, Ajustes, bloqueo durante copia, conflicto de dos ventanas, ausencia de escrituras al navegar, sin errores JS/HTTP). Hay que usar un `mock_server` **recién arrancado** para cada ejecución (guarda estado). |
| `code/soloLocal_test.go`, `code/exportar_test.go`, `code/google_test.go` | `go test ./code` (`google_test` usa un servidor falso de Google: ver 26.3) | Filtro Host/Origin; `nombreSeguro`, `handleExportar` (con `carpeta` guarda dentro, no pisa archivos, rechaza carpetas inexistentes y lo que no es PDF) y que la librería embebida está presente. |

**Lo que NO se ha probado nunca:** compilar y ejecutar `main.go` con el driver SQLite real; la persistencia del orden de bloques en SQLite real (solo en SQL de Python); el selector de carpetas (`osascript`) y permisos de `Documents` en macOS; `Fisioterapia.command` en un Mac real; el planificador de copias con reloj real. La primera compilación en el Mac es la prueba final.

Rendimiento medido en navegador con 34.560 puntuaciones (8 pacientes × 12 ejercicios × 120 días × 3 reps): ficha ≈ 13 ms, resumen de 120 días ≈ 150 ms.

---

## 9. Reglas para modificar el proyecto

1. **Idioma:** toda la interfaz y los mensajes en español; el código y los comentarios, también.
2. **Sin dependencias nuevas** salvo `modernc.org/sqlite`; sin frameworks de frontend ni paso de build. El usuario final no tiene herramientas de compilación.
3. **Formato Go:** `gofmt` limpio; `go vet` sin avisos.
4. **Concurrencia:** toda ruta nueva que toque `db`/carpetas debe tomar `mu`. Las que deban poder responder mientras se copia (como `/api/copiando`) no.
5. **Esquema:** seguir la regla de la sección 4.2 (crear, migrar, `loadState`, `saveState`, `restoreFrom`).
6. **Cambios de `db.puntuaciones`:** invalidar `idxPunt` (`idxPunt = null`).
7. **Cambios de pautas:** pasar por `changePautas`.
8. **Textos de usuario a `innerHTML`:** siempre con `esc()`.
9. **Nuevos ajustes globales:** `setAjuste(clave, valor)` (se persisten con el estado) y leerlos en Go con `ajusteGlobal`/`ajusteEntero` si el servidor los necesita.
10. **Acordeones:** usar `acordeon()`; no guardar estado de UI en `localStorage`.
11. **Datos de salud:** no añadir telemetría, servicios externos ni escuchar fuera de `127.0.0.1`.
12. Tras cambiar `main.go`/`index.html`, pasar `test_sql.py` y `test_ui.py` y, siempre que se pueda, compilar con el driver real.
13. **Nomenclatura:** en los textos que ve el usuario se dice siempre **sesión** (nunca «cita»; «dar una cita» es «programar una sesión»). En el código y la base de datos se conserva `cita` (ver sección 28).
14. **Listas:** toda lista nueva de una pantalla o pestaña se pinta con `paginar()` (sección 28).

---

## 10. Estado, decisiones y correcciones

### Decisiones interpretativas al transcribir el PDF (conviene revisar con el original)

- A22 «De pie» y A28 «Caminar con los muslos»: la primera variante «Por los muslos» se dedujo de la fila de título.
- A17: «Bien» se trató como «Derecha».
- A10 se llama «…de espalda a mi» (nombre algo extraño); B23 («Manos entrelazadas y manos juntas») tiene título inventado y la errata «estrelazadas» se corrigió.
- «Pivoteo supino 90°» omite la palabra «grados», como en el ejemplo del usuario.
- Se normalizaron variantes entre niveles («Por combinación», «Por los muslos»…) y se fusionaron los subapartados a/b en B6, B22, B26, B23, B21 y A13.

### Correcciones realizadas en la revisión

| Problema | Corrección |
|---|---|
| El JSON de bloques se escribió sin leer el PDF | Releído entero (26 págs.) y corregidos nombres/variantes. |
| Migración de `puntuaciones` no atómica | Ahora transaccional; las columnas se añaden solo si faltan y los errores no se ignoran. |
| Aviso al cambiar pauta por filas de repetición vacías | Solo cuentan puntuaciones reales. |
| La app reescribía la BD en cada pantalla | `save()` solo envía si hay cambios. |
| Orden de ejercicios en un bloque no garantizado en SQLite | Columna `posicion` + `ORDER BY bloque_id, posicion, rowid`. |
| Render lento con mucho histórico (≈5 s) | Índice `idxPunt` (≈13 ms). |
| «Borrar todo» borraba también los ajustes | Los conserva. |
| Dos ventanas abiertas podían pisarse los datos | Control de `X-Revision` (409 + recarga). |
| Cualquier web podía lanzar peticiones a `127.0.0.1:8765` | Filtro `soloLocal` por Host/Origin. |
| Indicador «copiando» podía apagarse antes con copias solapadas | Contador atómico. |
| Fallo al limpiar fotos devolvía error con los datos ya guardados | Solo se registra en el log. |
| Una copia fallida dejaba una carpeta parcial | Se borra al fallar. |
| (nuevo) Exportación a PDF por paciente | pdf-lib embebida; ver 6.2. |
| `/favicon.ico` daba 404 | `<link rel="icon" href="data:,">`. |

### Limitaciones conocidas

- **Se guarda el estado completo** en cada cambio: con histórico muy grande (decenas de miles de filas) cada PUT reescribe toda la BD. Funciona hoy, pero no escala indefinidamente.
- Si dos personas usaran la app a la vez desde dos equipos distintos sobre una carpeta compartida (p. ej. iCloud/Dropbox), SQLite **no es seguro** y la revisión es solo en memoria. Fuera de alcance.
- Las copias automáticas solo se hacen con la app abierta.
- Los PDF usan fuentes estándar (WinAnsi): caracteres fuera del alfabeto latino occidental salen como `?`.
- La foto se guarda siempre como `.jpg` aunque el origen sea PNG (el contenido no se transcodifica en servidor).
- El nivel de un bloque aún no se muestra en la sección del paciente.
- No hay deshacer; el único respaldo son las copias.

---

## 12. Personalización, Plan en casa y Hitos (última ampliación)

**Modelo de datos nuevo** (`migrateDB`, `CREATE TABLE IF NOT EXISTS`, las copias antiguas se restauran sin estas tablas):
- `plan_casa(id, patient_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo)`, única por (paciente, fecha, ejercicio). `grupo` identifica cada vez que se añade un bloque a un día (vacío = ejercicio suelto); `nota` son las indicaciones del ejercicio y `nota_grupo` las del bloque (repetida en todas las filas del grupo). Independiente de `pautas` y `puntuaciones`. Estado JSON: `planCasa`.
- `hitos(id, patient_id, fecha, nota, fotos)`. Varios por día permitidos. Estado JSON: `hitos`. `fotos` es un JSON con los nombres de fichero (en `fotos/`); en el estado JSON viajan como URL `/fotos/<hash>.jpg`.
- `evaluaciones(id, patient_id, fecha, evaluacion, fotos)`. Misma mecánica que los hitos, con el campo «Evaluación» en lugar de «Notas». Estado JSON: `evaluaciones`; se incluye en copias y restauración (las copias antiguas sin esta tabla se restauran igual).
- Ambas se borran en cascada con el paciente (y `plan_casa` con el ejercicio).

**Ajustes nuevos** (tabla `ajustes`): `clinicaNombre`, `clinicaLogo` (PNG en data URL, máx. 480×200), `profNombre`, `profColegiado`, `profFirma` (PNG, máx. 600×240; solo se admite PNG), `tema` (`claro`/`oscuro`), `accModo.<id>` (`recordar` por defecto / `abierta` / `cerrada`) para cada colapsable listado en `ACORDEONES` (index.html).

**Interfaz**
- Barra superior fija (`position:sticky`); `ajustarCabecera()` guarda su altura en `--hh`, que usan la cabecera del paciente y el menú lateral. Muestra logo y/o nombre de la clínica; si no hay ninguno, queda vacía.
- Ajustes › Personalizar: datos de clínica/profesional, logo, firma, modo claro/oscuro (variables CSS bajo `:root[data-theme="dark"]`) y comportamiento por defecto de cada colapsable.
- «Importar bloques (JSON)» está ahora en Ajustes › Carpeta de datos e importación.
- Pautas: título «Pautas (N bloques / M ejercicios)»; los bloques se muestran en negrita sin «Bloque:».
- Ficha del paciente con **pestañas** (`TABS_PAC`, estado `ui.tabP`): Pautas, Plan en casa, Hitos, Calendario, Resumen. Ya no hay menú lateral ni colapsables para esas secciones. El botón «Asignar ejercicios» está dentro de Pautas.
  - Pautas: lista en orden de ejecución (↑/↓ → `moverPauta`, renumera `orden`), «Establecer fecha fin» (`fijarFin`, también para pautas ya cerradas) y «Hacer continua». El orden se respeta en calendarios y puntuaciones.
  - Puntuación del día: una columna, ejercicios agrupados bajo su bloque (`filasDia`); no pierde la posición al puntuar (`refrescarModalDia` conserva el scroll de `.mwrap > .card`).
  - Añadir al día usa el mismo selector que Asignar (`selectorEjerciciosHTML`, `crearPautas`), ocultando lo que ya está en ese día.
  - Selector: lista vertical agrupada por nivel, desplegable de ejercicios por bloque, filtro «Solo ejercicios / bloques por nivel». Ejercicios: badge «En N bloques»; buscador de bloques también por ejercicios.
  - (obsoleto) Plan en casa: «Crear plan…» (intervalo, días de la semana, bloques/ejercicios con el mismo selector que Asignar, añadir o sustituir lo existente), lista de días con Editar (ordenar, quitar, añadir) y Eliminar, y «Exportar plan».
  - Hitos: fecha + nota, tabla (más reciente primero) con Editar/Eliminar y buscador de notas (sin distinguir mayúsculas ni tildes).
  - Fotos (hitos y evaluaciones): N fotos por entrada (`fotosFormHTML`, `subirFotos`), columna «Fotos» con el número y un botón 📷 que abre el visor (`verFotos`: anterior/siguiente, flechas del teclado, miniaturas). Se pueden quitar/añadir al editar. Las copias de seguridad ya incluyen la carpeta `fotos/`. Pruebas: `tests/test_fotos.py`.
  - Evaluaciones (primera pestaña): idéntica a Hitos pero con el campo «Evaluación» (`evaluacionesSeccionHTML`, `refrescarEvaluaciones`, `addEvaluacion`/`openEvaluacion`/`saveEvaluacion`/`delEvaluacion`). Pruebas: `tests/test_evaluaciones.py`.

**PDF del plan** (`pdfPlanCasa`): cabecera con logo, clínica, profesional y nº de colegiado en todas las páginas; título, paciente, periodo; por día, casillas vacías para marcar; firma, nombre y colegiado al final; pie con paginación. El botón «Exportar plan» (`exportarPlan`) genera directamente el PDF con todo el plan del paciente (de su primer a su último día, sin ventana ni intervalo de fechas), abre «Guardar como» con el nombre `Plan en casa_Apellidos_Nombre_desde_hasta.pdf` propuesto, muestra el resultado bajo los botones y lo registra en la pestaña «Informes». Bajo el título de un bloque se omite el prefijo del nombre del bloque en sus ejercicios (`nombreEnBloque`). El PDF del historial no cambia (solo lleva el nombre del paciente).

**Pruebas**: `tests/test_lote.py` y `tests/test_aviso_bloques.py` (con `seed_nuevo.json`), `tests/test_nuevo.py` (usa `tests/seed_nuevo.json`: `python3 tests/mock_server.py PUERTO tests/seed_nuevo.json &` y `python3 tests/test_nuevo.py PUERTO`), `test_ui.py` y `test_sql.py` actualizados (9 sentencias CREATE; restauración de plan/hitos).

### Plan en casa (rehecho)
Calendario semanal (`ui.casaSemana` = lunes ISO; `casaNav`). Cada día es una tarjeta con «+ Añadir» (`openAddCasa`/`saveAddCasa`: mismo selector que Asignar, notas opcionales y posibilidad de repetir en otros días de la semana), notas editables por bloque y por ejercicio (`editarNotaCasa`) y «Quitar» (`quitarCasa`). «Editar» abre `openDiaCasa`: el mismo formulario que «+ Añadir» (selector, notas) con, arriba, lo que ya hay en el día: cada bloque (nombre en negrita y ejercicios debajo, sin repetir su prefijo) o ejercicio suelto es una unidad que se puede subir/bajar, quitar y anotar. El PDF muestra nota de bloque y de ejercicio.

### Nombres bajo un bloque y negritas
Convención de la interfaz: solo el **bloque** va en negrita; sus ejercicios, en texto normal y **sin repetir el nombre del bloque** (`nombreEnBloque`: «Caminar con los muslos – Por los tobillos» bajo «Caminar con los muslos» se ve como «Por los tobillos»). Se aplica en la ventana de puntuación y vista de día, Plan en casa (tarjetas, editor de día, PDF y plantillas), Pautas, lista de Bloques, selector de ejercicios, gráfica de puntos y PDF del informe. Si un ejercicio se llama exactamente como su bloque: en las listas conserva su nombre; en la ventana de puntuación y en las tarjetas de Plan en casa no se repite. Los ejercicios sueltos van en texto normal (también en Pautas). Los tooltips conservan el nombre completo. Pruebas: `tests/test_negrita.py`, `tests/test_prefijo.py`.

### Acciones de vaciado y días por semana
- **Cabecera del paciente**: bajo el nombre se muestra «N días por semana (Lun, Mié…)» (`diasPorSemanaHTML`), calculado con los días de la semana en curso (lunes a domingo) que tienen algún ejercicio planificado en las pautas; sin ninguno, «Sin días planificados esta semana».
- **Pautas › «Quitar todas las pautas»** (`quitarTodasPautas`): elimina todas las pautas del paciente con confirmación (si hay puntuaciones afectadas, el aviso de `changePautas` las menciona).
- **Ventana de un día › «Quitar todos los ejercicios»** (`quitarTodosDeDia`): quita de ese día todos los ejercicios (bloques y sueltos) dividiendo las pautas como «Quitar de este día», sin tocar el resto de días.
- **Plan en casa › «Vaciar»** en cada día con ejercicios (`delDiaCasa`, con confirmación). Pruebas: `tests/test_vaciar.py`.

### Planes guardados del paciente
Copia con nombre del plan en casa de un paciente (con sus fechas). Tablas `planes_guardados(id, patient_id, descripcion, creada)` y `planes_guardados_items(plan_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo)`; estado JSON `planesGuardados` (cada plan con sus `items`); entran en copias y restauración. En la pestaña Plan en casa:
- **Guardar plan**: copia todo el plan actual; la descripción es obligatoria (sirve para identificarlo) y se guarda la fecha de creación.
- **Lista «Planes guardados»** (más reciente primero): descripción, fecha, contenido (días y ejercicios) y, en cada fila, **Exportar** (PDF del plan guardado, con su descripción; nombre `Plan en casa_Apellidos_Nombre_descripción_desde_hasta.pdf`, se guarda donde elija el usuario), **Editar** y **Eliminar**.
- **Editar** carga el plan guardado como plan de trabajo del paciente (sustituye el actual; avisa solo si el actual no coincide con ningún plan guardado). Aparece un banner «Editando el plan guardado…» con **Guardar cambios** (actualiza ese plan y permite cambiar su descripción, conserva la fecha de creación) y **Dejar de editar**. «Guardar plan» siempre crea uno nuevo.
- Borrar un ejercicio lo quita de los planes guardados; borrar un bloque deja sus ejercicios sueltos. Borrar un paciente borra sus planes guardados (cascada). Pruebas: `tests/test_planes.py`.

### Plantillas del plan en casa
Una plantilla es una semana tipo de lunes a domingo, sin fechas, con duración sugerida en semanas. Tablas `plantillas` y `plantilla_items` (dia 1=lunes…7=domingo; ejercicio, bloque, orden, nota, grupo, nota_grupo); se sincronizan en `/api/state` (`plantillas`) y se incluyen en copias y restauración.
- **Guardar**: botón «Guardar semana como plantilla…» en Plan en casa (semana visible). Siempre crea una plantilla nueva; no sobrescribe (para variar una, aplícala, ajusta y guarda de nuevo).
- **Aplicar**: «Aplicar a pacientes…» (pantalla Plantillas) o «Crear plan desde plantilla…» (en el paciente: primero se elige la plantilla en una lista con buscador y luego se abre la misma ventana con ese paciente marcado). La ventana ya no tiene selector de plantilla: se aplica la elegida, a uno o varios pacientes (lista con buscador y «Marcar visibles»). La pantalla Plantillas y el selector tienen buscador por nombre de plantilla, bloque o ejercicio. Elige fecha de inicio, duración (N semanas o hasta una fecha, máx. 1 año) y modo «añadir» (no duplica ejercicios ya presentes ese día) o «sustituir» (borra el plan del periodo, con confirmación).
- **Pantalla Plantillas** (menú superior): lista, contenido por día, editar nombre/duración, eliminar. Borrar un ejercicio lo quita de las plantillas; borrar un bloque deja sus ejercicios como sueltos.


## 11. Sugerencias y mejoras potenciales

Ordenadas por valor/esfuerzo aproximado.

**Seguridad y fiabilidad de los datos**
1. **Copia a una segunda ubicación** (USB/iCloud/NAS) elegida en Ajustes, además de la local. Es la mejora de más valor: hoy un fallo de disco pierde datos y copias a la vez.
2. **Verificar las copias** tras crearlas (abrir la BD copiada y comprobar `PRAGMA integrity_check` y recuentos) y mostrar el resultado.
3. **Guardado incremental** (endpoints por entidad o diff) en lugar de PUT del estado completo; reduce riesgo y coste y permite fusionar cambios de varias ventanas.
4. **Cifrado en reposo** de la carpeta de datos (o aviso para activar FileVault) y contraseña/PIN al abrir, dado que son datos de salud (RGPD): considerar consentimiento, registro de accesos y derecho al borrado de un paciente (borrar paciente + fotos + puntuaciones).
5. **Exportar/importar** pacientes y su historial (CSV/JSON/PDF) para portabilidad entre sets de datos.

**Experiencia de uso**
6. **Mostrar el nivel en la sección del paciente** (etiqueta en pautas agrupadas por bloque y filtro por nivel en el calendario).
7. **Plantillas de pauta** («programa» = bloques + frecuencia) y asignación por días de la semana (p. ej. L-X-V).
8. **Informe imprimible/PDF por paciente** (evolución, medias por ejercicio y gráfica) para dar al paciente.
9. Atajos de teclado para puntuar (0–3) y avanzar de fila durante la sesión.
10. Notas por sesión/ejercicio, y marcar un ejercicio como «no realizado» distinto de «sin puntuar».
11. Modo «sesión»: pantalla a pantalla completa con el orden de ejecución del día y grandes botones de puntuación.
12. Ajustes: tamaño de letra y tema oscuro/alto contraste.
13. Deshacer último cambio (o papelera de pacientes/ejercicios eliminados).

**Distribución y operación**
14. **Empaquetar como `.app`** firmada y notarizada (evita avisos de Gatekeeper) y con icono; arranque sin ventana de Terminal usando un `LaunchAgent` o una app de barra de menús con opción «Salir».
15. **Actualizador**: comprobar versión y avisar; mostrar changelog.
16. **Puerto configurable / selección automática** si el 8765 está ocupado (hoy aborta).
17. **Binarios universales** (`arm64` + `amd64` con `lipo`) para cualquier Mac.
18. Registro (`log`) a fichero rotado en la carpeta de datos para depurar sin Terminal.

**Calidad de código**
19. **Tests Go reales** (`go test`) con SQLite en memoria en CI: migraciones, `saveState`/`loadState` ida y vuelta, `restoreFrom`, `copiaDebida` (con reloj inyectable) y poda de copias.
20. Partir `main.go` en varios ficheros (`db.go`, `backup.go`, `handlers.go`) sin cambiar la arquitectura; y `index.html` en módulos ES mediante `go:embed` de un directorio.
21. Pruebas de UI en CI con el binario real (en lugar del servidor simulado).
22. Validar en servidor longitudes y formatos (email, fechas, tamaño de foto) y reducir la foto en cliente antes de enviarla.
23. Sustituir el escaneo lineal de `changePautas` por índices si crece el número de pautas.
24. Accesibilidad: roles ARIA, foco en modales (el bloqueo ya usa `inert`), contraste de la leyenda de colores.

## 13. Windows

La aplicación funciona en macOS y Windows (Go puro, sin CGO, así que se compila para Windows desde el Mac).

- **Compilar:** `scripts/build.sh 1.5.0 windows` genera `fisioterapia.exe`; `scripts/build.sh 1.5.0 todo` genera las dos versiones.
- **Qué entregar en Windows:** `fisioterapia.exe` + `Fisioterapia.bat` en la misma carpeta. Se usa `Fisioterapia.bat` (doble clic): abre una ventana negra que NO se debe cerrar mientras se usa la app; si ya está en marcha, solo abre el navegador.
- **Datos:** por defecto en `C:\Users\<usuario>\Fisioterapia` (no en Documentos, porque OneDrive suele sincronizarlo y SQLite puede corromperse en carpetas sincronizadas). La configuración (`config.json`) está en `%AppData%\Fisioterapia`. Desde Ajustes se puede cambiar la carpeta con el selector de Windows (PowerShell + FolderBrowserDialog).
- **Navegador y carpetas:** se abren con `explorer` (carpeta de un PDF y URL de la app); los PDF se abren con su programa por defecto.
- **Avisos esperables (exe sin firmar):** SmartScreen ("Windows protegió su PC" → Más información → Ejecutar de todas formas), posible aviso del cortafuegos la primera vez (permitir acceso privado) y antivirus que a veces ponen en cuarentena exes de Go sin firmar. El `.bat` ejecuta `Unblock-File` para quitar la marca de descarga. Si llega por correo, enviarlo comprimido en `.zip`.
- **Pendiente de probar en un Windows real:** todo lo de este apartado se ha compilado y revisado (`go vet` para windows/amd64), pero no se ha ejecutado en Windows. Comprobar: arranque, apertura automática del navegador, selector de carpeta, «Guardar como» de los PDF, abrir un PDF y su carpeta, copia de seguridad (`VACUUM INTO`), fotos y rutas con espacios o tildes.

## 14. Ejercicio escrito a mano en el plan en casa

En «Añadir» y «Editar» de un día hay un cuadro «Ejercicio escrito a mano» (uno por línea). Cada línea se guarda como un ejercicio con `libre = true` (columna `exercises.libre`, se añade sola al abrir una base de datos antigua) y una entrada normal de `plan_casa`; así funciona igual en PDF, plantillas y planes guardados. No aparece en la biblioteca de ejercicios (`biblioteca()` en `index.html` filtra los libres) ni en los selectores. Al guardar, `limpiarLibres()` borra los libres que ya no usa ningún plan, plantilla o plan guardado. Prueba: `tests/test_libre.py`.

## 15. Plantillas: editar contenido y pacientes asignados

- Aplicar una plantilla **copia** sus ejercicios al plan del paciente (`plan_casa`); editar la plantilla después no modifica esos planes.
- «Editar» (pantalla Plantillas) abre una única pantalla con el nombre, la duración sugerida y la semana tipo en tarjetas de lunes a domingo, igual que el plan en casa: «+ Añadir» (con opción de añadir también a otros días), «Editar» un día (ordenar, notas, quitar, añadir), notas y quitar por elemento y «Vaciar» por día. Todo se guarda al momento.
- Cada aplicación se registra en la tabla `plantilla_aplicaciones` (plantilla, paciente, desde, hasta, día de aplicación; en el estado, `plantilla.aplicaciones`). «Pacientes (N)» abre la lista de pacientes con buscador y acceso a su plan. Las aplicaciones anteriores a esta versión no constan.
- La lista de pacientes al aplicar una plantilla tiene scroll propio (`test_scroll_pacientes.py`).

### Plantillas de varias semanas

- Una plantilla tiene `semanas` (1–52) y sus entradas usan `dia` de 1 a 7·semanas (lunes de la semana 1 = 1, domingo de la semana 2 = 14…). El editor muestra una tarjeta por día, agrupadas por semana; «Duración (semanas)» añade semanas vacías o, al reducir, pide confirmación y quita lo que sobra.
- Al aplicarla, la semana del periodo que corresponde se calcula desde la semana de la fecha de inicio (`diaPlantillaDe`); si el periodo es más largo que la plantilla, el ciclo se repite. «Guardar semana como plantilla…» con N semanas repite esa semana N veces (luego se puede editar cada una).
- Compatibilidad: columna `plantillas.ciclo` (0 = antigua, 1 = nueva). Al abrir la aplicación, una plantilla antigua de N semanas (una semana repetida) se convierte en N semanas iguales (`migrarPlantilla`) y se guarda sola; el resultado al aplicarla es el mismo que antes. Las copias de seguridad antiguas se convierten igual. Prueba: `tests/test_plantilla_semanas.py`.

## 16. Buscador de bloques y ejercicios en la ficha del paciente

Las pestañas Pautas, Calendario y Plan en casa tienen un cuadro «Buscar bloque o ejercicio» (varias palabras: deben aparecer todas; sin tildes ni mayúsculas). Se filtra sin repintar la pantalla, con una búsqueda independiente por pestaña (`ui.qPautas`, `ui.qCal`, `ui.qCasa`; se vacían al abrir otro paciente).
- **Pautas:** solo las pautas (bloque o ejercicio suelto) cuyo nombre, o el de alguno de sus ejercicios, coincide; conservan su número de orden.
- **Calendario:** en mes y semana, cada día muestra solo los ejercicios que coinciden (por nombre del ejercicio o de su bloque); en la vista Día, «X de Y ejercicios».
- **Plan en casa:** si coincide el nombre del bloque se ve entero; si solo coincide algún ejercicio, el bloque muestra solo esos. Los días sin coincidencias ponen «Sin coincidencias» y conservan «Editar» y «Vaciar». El PDF y los planes guardados no se ven afectados. Prueba: `tests/test_buscador_pac.py`.

### Pacientes con una plantilla: vigencia

Una aplicación de plantilla solo cuenta (y solo se muestra en «Pacientes (N)») mientras el paciente conserve algún ejercicio del plan en casa dentro de su periodo; si se vacía el plan, deja de figurar y el registro se limpia al guardar (`limpiarAplicaciones`). Cuando un plan se quita ejercicio a ejercicio, la aplicación desaparece al quedar el periodo sin ejercicios.

## 17. Eliminar un paciente

«Editar datos del paciente» → «Eliminar paciente» (abajo a la izquierda). Pide confirmación indicando cuántas pautas, puntuaciones, días de plan en casa, planes guardados, hitos y evaluaciones se borrarán con él. Elimina todo lo del paciente (`delPaciente` en `index.html`; el servidor, al guardar, borra también sus fotos que ya no usa nadie) y lo quita de los registros de plantillas. No se puede deshacer salvo restaurando una copia de seguridad. Prueba: `tests/test_eliminar_paciente.py`.

## 18. Versiones, migraciones y distribución

**Dónde están los datos:** fuera del ejecutable (carpeta de datos). Actualizar = sustituir el ejecutable y el lanzador. `index.html` va incrustado en el ejecutable: cualquier cambio de `index.html` o de `main.go` exige recompilar.

**Versión del modelo (`schemaVersion` en `main.go`, guardada en `PRAGMA user_version`):** súbela en 1 en cada versión que cambie el modelo de datos (tablas, columnas o datos). Al abrir una carpeta de datos (`prepararBaseDeDatos`):
1. Si los datos son de un modelo MÁS NUEVO que el del ejecutable, no se abren (la app no arranca y explica que hay que usar la última versión): guardar con un programa antiguo borraría lo que no conoce. Restaurar una copia de un modelo más nuevo se rechaza igual.
2. Si hay datos de un modelo anterior, antes de tocar nada se hace una copia completa `copia-previa-actualizacion-<fecha>` (en copias/; las automáticas no la borran). Si la copia falla, los datos no se tocan.
3. `migrateDB` añade tablas y columnas que falten; luego se ejecutan los `pasosMigracion[v]` pendientes (v → v+1), cada uno en una transacción junto con la anotación de la versión.

**Cómo añadir un cambio de modelo:** (a) si solo añades tablas/columnas, ponlas en `migrateDB` (y en la restauración, `restoreFrom`) y sube `schemaVersion`; (b) si renombras, partes o recalculas datos, añade además `pasosMigracion[versiónAnterior]`; (c) actualiza `tests/test_sql.py`; (d) prueba con una copia de la carpeta de datos real de la usuaria.

**Entrega:** `scripts/build.sh X.Y.Z todo` compila Mac y Windows y, si hay `zip`, deja en `dist/` los ejecutables y `Fisioterapia-X.Y.Z-mac.zip` / `-windows.zip` con el lanzador (`scripts/`) y `docs/ACTUALIZAR.txt` (instrucciones para la usuaria). Las bases de datos existentes son versión 0; la primera apertura con este ejecutable hace la copia previa y las marca como versión 1.

## 19. Compilar desde Linux o WSL

`scripts/build.sh` compila siempre para el sistema pedido (`GOOS`/`GOARCH` explícitos, sin CGO), así que sirve igual en macOS, Linux y WSL. El Mac se compila para Apple Silicon (`arm64`) salvo que se ejecute en un Mac Intel o se indique `MAC_ARCH=amd64 scripts/build.sh X.Y.Z mac`. Preparación en WSL (Ubuntu): instalar Go desde go.dev (no con `apt`), `sudo apt install zip`, trabajar en `~/` (no en `/mnt/c`) y `go mod tidy` la primera vez. Si `./build.sh` da «permiso denegado» (al copiar los archivos se pierde el bit de ejecución), usar `chmod +x scripts/build.sh scripts/Fisioterapia.command` o `bash scripts/build.sh …`.

### Eliminar varios pacientes y listado en lista
En el listado de pacientes, «Eliminar seleccionados (N)» (junto a «Exportar PDF») borra a los pacientes marcados con la misma confirmación (nombres y datos que se pierden) y el mismo borrado en cascada (`delPacientes`). La casilla de la primera fila selecciona (o quita) todos los de la lista o de la búsqueda. El listado ya no se reparte en columnas: es una lista de una sola columna. Prueba: `tests/test_eliminar_paciente.py`.

## 20. Novedades (changelog) y Ajustes en pestañas

- **Ajustes** tiene cuatro pestañas: Personalizar, Copias de seguridad (automáticas + guardadas), Datos (carpeta, importar bloques, borrar todo) y Novedades. La pestaña activa es `ui.ajTab`. Los antiguos acordeones de Ajustes desaparecen (ya no aparecen en Personalizar).
- **`docs/CHANGELOG.md`** va embebido en el binario (`go:embed`) y se sirve en `GET /api/changelog` (`{version, texto}`). Está escrito en español para la usuaria final, la versión más reciente primero. Formato:
  ```
  ## 0.0.5 · 12 nov 2026
  ### Novedades   (también «Mejoras» y «Correcciones»)
  - Texto con **negrita**.
  ```
- La pestaña Novedades muestra las versiones plegables; la instalada se abre y lleva la etiqueta «Instalada».
- **Aviso descartable** (`#avisoNovedades`): la primera vez que se abre la aplicación con una versión distinta a la guardada en el ajuste `novedadesVista`, aparece «La aplicación se ha actualizado…» con «Ver novedades» y «Entendido». En una instalación nueva (sin pacientes ni ejercicios) se marca como vista sin avisar; en la versión `dev` no se muestra.
- **`build.sh` se niega a compilar** si `docs/CHANGELOG.md` no tiene una línea `## X.Y.Z` para esa versión. Flujo de cada release: añadir la entrada en CHANGELOG.md, `scripts/build.sh X.Y.Z todo`.
- Tests: `tests/test_novedades.py`.

### Ampliar la foto del paciente
`avatar()` hace clic-para-ampliar (`ampliarFoto(id)`): superposición propia `#fotoAmpliada` (no cierra la ventana que haya debajo); se cierra con clic o Esc. Test: `tests/test_foto_ampliar.py`.

## 21. PDF: dónde se guardan y listado en «Informes»

- Ya no hay carpeta `exportaciones/` en los datos. `POST /api/exportar?nombre=…` recibe el PDF y:
  - sin `carpeta`: el servidor abre el diálogo nativo «Guardar como» (`dialogoSistema("guardar", …)`: `osascript choose file name` en macOS, `SaveFileDialog` de PowerShell en Windows) empezando en `inicio`; si se cancela responde 409;
  - con `carpeta` (exportación de varios pacientes): guarda dentro sin pisar nada (`rutaLibre` añade « (2)»…). La carpeta se elige antes con `POST /api/elegir-carpeta?titulo=…&inicio=…`.
  - Los textos van al script como argumentos (macOS) o variables de entorno (Windows), nunca concatenados, para que ningún nombre pueda romperlo. Los diálogos se muestran en primer plano (`activate` / formulario `TopMost`), aunque pueden quedar detrás del navegador: la interfaz lo avisa.
- La interfaz registra cada PDF en `db.informes` (tabla `informes`: id, patient_id, tipo `informe|plan`, nombre, ruta, fecha, desde, hasta, descripcion; borrado en cascada con el paciente) y guarda la última carpeta en el ajuste `pdfCarpeta`.
- **Modelo de datos 2** (`schemaVersion = 2`): solo añade la tabla, así que no hay paso de migración; al abrir datos del modelo 1 o 0 se hace la copia `copia-previa-actualizacion`. La restauración copia `informes` si la copia la tiene.
- Pestaña «Informes» del paciente: sección «PDF generados» con filtro (Todos / Informes / Planes en casa), y por cada uno *Abrir* (programa del sistema), *Mostrar en la carpeta* (`open -R` en Mac; en Windows abre la carpeta) y *Quitar de la lista* (no borra el archivo).
- `POST /api/informes/abrir?id=…[&modo=carpeta]` solo abre rutas registradas en la tabla `informes` (el navegador no puede pedir abrir una ruta cualquiera); 410 si el archivo ya no existe. `GET /api/informes/existen` devuelve `{id: bool}` para marcar los que faltan.
- Los PDF no se incluyen en las copias de seguridad (el registro sí).
- Tests: `tests/test_informes.py` (el mock simula el diálogo; `/__dialogo/cancelar` y `/__dialogo/ok`).

### Pestañas «Resumen» e «Informes» del paciente
El resumen de ejercicios (`resumenHTML`, `#sec-resumen`, clave de pestaña `resumen`) tiene su propia pestaña «Resumen». La pestaña «Informes» (clave `informes`, `#sec-informes`) contiene el botón «Generar informe PDF...» y la lista de PDF generados.

### Menú principal: Pautas (Ejercicios / Bloques) y Plan en casa
- Menú: Pacientes · **Pautas ▾** (submenú `#menuPautas` con Ejercicios y Bloques) · **Plan en casa** (antes «Plantillas»; la vista sigue siendo `plantillas`) · Ajustes.
- `ui.view` `ejercicios` (solo `viewEjercicios`) y `bloques` (solo `bloquesHTML`). Ya no son secciones plegables: se quitaron de `ACORDEONES` y de Personalizar.
- El submenú se abre al pulsar (`toggleSubmenu`) y se cierra al elegir, al pulsar fuera o con Esc (`cerrarSubmenu`; `go()` lo cierra siempre). «Pautas» queda marcado mientras se está en Ejercicios o Bloques.

### Convención: acciones destructivas en rojo
Todo botón que borra, quita, vacía o sustituye datos usa `class="danger"` (con texto) o, si es un icono «×», `class="ghost … quitar"` (texto en `--danger`). Incluye eliminar hitos, evaluaciones y planes guardados, quitar logo/firma/foto, quitar de la lista de informes y restaurar una copia.

### Ventana del día: pestañas en vez de plegables
- `renderDayModal` muestra `#tabsDia` con «Puntuar ejercicios (n)» (`#secPun`, primera) y «Añadir ejercicios» (`#secAdd`). Estado en `ui.diaTab` (`puntuar` | `anadir`); `openDay(s, tab)` abre en `tab`, o en «Puntuar» si el día tiene ejercicios y en «Añadir» si está vacío. `addDayEx` vuelve a «Puntuar».
- Ya no queda ninguna sección plegable con estado guardado: se eliminaron `acordeon()`, `ACORDEONES`, `accModo/accAbierto/accGuardar`, `setModoAcordeon` y el bloque «Secciones plegables» de Ajustes › Personalizar. Los ajustes antiguos `acc.*` y `accModo.*` que haya en la base de datos se ignoran.
- Test: `tests/test_dia_pestanas.py`.

### Pestañas del paciente: Progreso (submenú) y Calendario/Resumen
- `TABS_PAC` (orden por defecto desde la 0.0.7; configurable, ver §33): Pautas · Sesiones · Calendario · Plan en casa · **Progreso** (submenú: `evaluaciones` «Evaluación inicial», `hitos` «Hitos») · Informes. Un elemento con tercer campo es un submenú (`tabsPacHTML`); usa el mismo `.menu-sub` / `toggleSubmenu` / `cerrarSubmenu` que «Pautas» del menú principal (Esc, clic fuera y elegir lo cierran). `ui.tabP` sigue guardando la sección concreta (`evaluaciones` o `hitos`); «Progreso» se marca si la sección activa es una de las suyas.
- Resumen: subpestaña de Calendario (`#subCal`, `ui.calVista` = `calendario` | `resumen`, se recuerda al cambiar de pestaña y se reinicia al abrir otro paciente). `irTab('resumen')` sigue funcionando y lleva ahí.
- `.ptabs` ya no tiene `overflow-x:auto` (recortaba el submenú): en pantallas estrechas las pestañas pasan a otra línea.
- Test: `tests/test_pestanas_paciente.py`.

### Calendario/Resumen: informe del periodo, buscador y repeticiones
- `subCalHTML` incluye «Generar informe PDF...» (`#btnInformeCal` → `informePeriodoActual()`): abre `openExportar([pid], desde, hasta)` con `rangoCalendario()` (día/semana/mes de `ui.vista`) o `rangoResumen()`. `openExportar` acepta ahora fechas opcionales.
- Resumen: buscador `#qRes` (`ui.qRes`, se vacía al abrir otro paciente). Solo se repinta `#resCuerpo` (`resCuerpoHTML` / `refrescarResumen`) para no perder el foco; `filtrarDatos` filtra por nombre del ejercicio o de su bloque.
- `datosRango` devuelve también `porRep[eid][día]` (filas de repetición; un día previsto sin filas cuenta como «Rep. 1» sin puntuar) y, por ejercicio, `minRep`, `maxRep` y `reps[k]` (`exp`, `puntuados`, `scores`). `textoReps(st)` → «3 reps», «1 rep» o «1–3 reps».
- Calendario: el chip muestra `(n)` (`.nrep`) antes de la media si ese día hay 2 o más repeticiones; el `title` lo explica.
- Lista: si el ejercicio tiene más de una repetición en el periodo, su nombre lleva «(… reps)» y debajo van subfilas `tr.rep-sub` «Rep. k» (días con esa repetición, puntuadas y media).
- Puntos: subfilas «Rep. k» sangradas con puntos más pequeños (solo los días en que hubo esa repetición). La fila del ejercicio sigue mostrando la media del día.
- Líneas: siguen siendo la media; la leyenda añade «(… reps)» y el `title` de cada punto, «(n reps) · fecha · media x».
- Test: `tests/test_reps_resumen.py`.

## 22. Ayuda: manual de usuario e iconos «?»

- **`docs/AYUDA.md`** (embebido con `go:embed` desde `docs/embed.go`, igual que `docs/CHANGELOG.md`; hace falta para compilar) es el manual para la usuaria, en español sencillo. Se sirve en `GET /api/ayuda` (texto Markdown) y se muestra en el menú **Ayuda** (`ui.view = 'ayuda'`, `viewAyuda` / `loadAyuda`): índice lateral con las secciones `##`, buscador (`ui.qAyuda`, `filtrarAyuda`: oculta las secciones que no contienen todas las palabras) y el texto.
- **Formato que entiende el intérprete** (`mdManual`, sin librerías): `#`/`##`/`###` con ancla opcional `{#id}` (el `id` del HTML es `ay-<id>`), párrafos, listas `-` y `1.`, notas `> …` (las que empiezan por `**Importante` salen en rojo), `**negrita**` y enlaces internos `[texto](#id)`. Cada `##` es una sección del índice y del buscador. **Las anclas son estables**: los iconos de ayuda dependen de ellas.
- **Iconos «?»**: `ayudaIco('<clave>')` dentro del título de la pantalla; `AYUDA_CORTA[clave] = { t, txt, ancla }` tiene el texto corto y la sección del manual. Al pulsar se abre `#ayudaPop` (junto al icono, encima de las ventanas) con «Ver en el manual →» (`irAyuda(ancla)`, que cierra la ventana abierta y salta a la sección). Se cierra con Esc (sin cerrar la ventana de debajo), clic fuera, scroll o pulsando otra vez el icono.
- Iconos actuales: Pacientes, Pautas (pestaña y ventana de asignar), Calendario/Resumen, ventana del día, Plan en casa, Planes guardados, Plantillas (lista, editor y ventana de aplicar), Evaluación inicial, Hitos, Informes, ventana de exportar PDF, Ejercicios, Bloques, Ajustes › Copias automáticas y Carpeta de datos.
- Al cambiar una pantalla, revisa su sección de `AYUDA.md` y su texto en `AYUDA_CORTA`. Test: `tests/test_ayuda.py` (comprueba también que todos los enlaces y anclas existen).

## 23. Versión 0.0.5: propuestas de la evaluación de usabilidad

Implementa las 12 mejoras del informe de evaluación (y varias observaciones menores). La lista para la usuaria está en `docs/CHANGELOG.md`; aquí, lo técnico.

### Modelo de datos 3 (`schemaVersion = 3`)
- `pautas.dias TEXT NOT NULL DEFAULT ''`: días de la semana en que toca la pauta, dígitos `1` (lunes) … `7` (domingo) ordenados, p. ej. `135`. Vacío = todos. El servidor normaliza con `diasValidos` (solo 1–7, sin repetir, ordenados; los 7 → vacío) al guardar.
- `patients.archivado INTEGER NOT NULL DEFAULT 0` (JSON `archivado`, omitido si es falso).
- Las dos se añaden con `ALTER TABLE` vía la lista `columnas` (no hay paso de migración); al abrir datos del modelo 2 o anterior se hace antes la copia `copia-previa-actualizacion-…`. `restoreFrom` copia ambas si la copia las tiene (`srcColumna`) y deja los valores por defecto si no. Tests: `test_sql.py` (columnas, guardado y restauración) y `TestDiasValidos` en `exportar_test.go.txt`.

### Días de la semana en la UI
- `tocaDia(p, día)` (con `digitoDia`) se añade a `coveredBy`, `exercisesOn` y al cálculo de pautas que cubren un día: todo lo que cuenta «previstos» (calendario, Resumen, informe, cabecera «N días por semana», lista de pacientes) respeta los días.
- Selector `selectorDiasHTML(id, dias)` (casillas L M X J V S D + «Lunes a viernes» / «Todos»), `leerDias(id)` → `''` (todos), `'135'` o `null` (ninguno: no se guarda y se avisa). Está en «Asignar ejercicios» (`#aDias`; oculto con «Solo ese día») y en «Editar pauta» (`#epDias`). `textoDias` → «de lunes a viernes», «los fines de semana», «los lunes, miércoles y viernes».

### Pautas: ventana «Editar»
- Cada pauta (asignación: `claveAsig`) se muestra con su periodo en texto (`periodoPauta` → `{ini, fin, abierta, huecos}`, `textoPeriodo`; los días quitados a mano con «Quitar de este día» salen como «sin el …» / «sin N días sueltos») y un botón **Editar** → `openEditarPauta(k)` / `guardarEditarPauta(k)`: inicio (`#epIni`), fin (`#epTipo` continua/fecha + `#epFin`) y días. Cambia el inicio del primer tramo de cada ejercicio y el fin del último, pasando por `changePautas` (avisa si se pierden puntuaciones). Desaparecen los campos `ini_`/`fin_` y los botones «Establecer fecha …»/«Hacer continua».
- Las pautas terminadas (`pautaTerminada`) van en `<details class="pautas-terminadas">` al final; las flechas de orden solo cuentan las activas.

### Puntuar
- `puntuarHoy(pid)` (lista de pacientes y cabecera de la ficha): abre la ficha en Calendario y `openDay(hoy, 'puntuar')`.
- Ventana del día compacta (`filaEjercicioDia`): una fila por ejercicio (`.ej-dia`), con sus repeticiones (`.rep-fila`, `data-fila/eid/rep`), «+ Rep.» y «Quitar». «Quitar todos los ejercicios» solo en la pestaña Puntuar y si hay ejercicios.
- Teclado (listener global, solo con `#secPun .rep-fila` visible y sin foco en un campo): `0`–`3` puntúa la fila `ui.diaFoco` y avanza; `↑ ↓` mueven; `+` añade repetición (`addRep` deja marcada la nueva). `marcarFocoDia` elige al abrir la primera fila sin puntuar.
- `mostrarGuardado()` muestra «✓ Guardado» tras cada `PUT` correcto.

### Pacientes
- `refrescarPacientes`: filas con «Hoy: x de y puntuados» (`resumenDia`), «Última sesión» (`ultimasSesiones()`: último día ≤ hoy con alguna puntuación) y «Plan en casa hasta…» (`finPlanesCasa()`); botón «Puntuar hoy»/«Ver hoy». Orden `ui.ordenPac` (`nombre` | `sesion`) y filtro `ui.filtroPac` (`activos` por defecto | `archivados` | `todos`, `pacientesVisibles()`).
- Las acciones en lote (`#accionesPac`) solo se pintan con algún paciente marcado: «Asignar ejercicios (n)», «Informe PDF… (n)», «Archivar (n)»/«Recuperar (n)», «Eliminar (n)».
- `archivarPacientes(ids, archivar)`: confirma, marca/desmarca `archivado` y `render()` (que guarda). También desde «Editar datos del paciente» y el aviso de la ficha de un archivado. Los archivados no salen al aplicar plantillas.
- «Fecha de alta» → «Primera visita» (solo el texto; el campo sigue siendo `fechaAlta`). El nombre se marca como obligatorio y «Quitar foto» solo sale si hay foto.
- Cabecera de la ficha (`.sticky-head`): clase `compacta` con `scrollY > 180` (se quita con `< 40`), oculta los `.det` y reduce foto y título.

### Calendario y Resumen
- Mes: `celdaMes` (media del día redondeada a 1 decimal en color `.mes-media.sN` y «x de y puntuados», `.pend` si faltan; días futuros solo «N ejercicios»). Semana: `celdaDia` con todos los ejercicios (máx. 40), agrupados por bloque (`.chip-grupo`) con `nombreEnBloque`; los días futuros no llevan «sin puntuar».
- Resumen lista: `idsOrdenResumen` (orden de ejecución, como los puntos) con filas de grupo `tr.grp`; las subfilas `tr.rep-sub` solo con `ui.resReps` («Ver cada repetición»). Los «previstos» solo cuentan días ≤ hoy.
- Líneas: `seriesLineas(datos, modo)` con `ui.lineas` = `ejercicio` | `bloque` | `media` (por defecto `bloque` si hay más de 6 ejercicios), leyenda con botones (`alternarLinea`, `ui.lineasOcultas`) y ancho según `#main`.

### Biblioteca
- Menú principal `#menuBiblioteca` (Ejercicios, Bloques, Plantillas) con `data-v="biblioteca"` marcado si la vista es una de las tres. Ya no hay menú «Plan en casa» ni «Pautas».
- Ejercicios: «Nuevo ejercicio…» (`openNuevoEj` → `addEj` → `crearEjercicio(nombre)`, que rechaza nombres repetidos) y menú «⋯» por fila (`.menu-sub.menu-claro.menu-fila`): Renombrar…, Duplicar (antes Clonar), Eliminar… (`.peligro`).
- Bloques: «Importar bloques…» (`#fileBloquesB`, mismo flujo que Ajustes) y, en la ventana del bloque, `#bNuevoEj` + «Crear y añadir» (`crearEnBloque`: crea en la biblioteca y lo deja marcado al principio de la lista).
- Plantillas: «Nueva plantilla» (`nuevaPlantilla`: crea «Plantilla nueva» vacía y abre el editor con el nombre seleccionado). «Usar con pacientes…» (antes «Aplicar a pacientes…»). `openElegirPlantilla` solo ofrece plantillas con ejercicios.
- Plan en casa del paciente: menú `#menuPlantillasCasa` («Usar una plantilla…», «Guardar como plantilla…»). `openGuardarPlantilla` ofrece «Solo la semana que estás viendo» (con «Repetir la semana») o «Todo el plan» (`semanasPlanCasa(pid)`: todas las semanas con algo; los días se numeran 1…7·N).

### Progreso
- `formProgresoAbierto(clave, n)` / `formProgreso(clave, abierto)`: con entradas, el formulario va plegado (`hidden`) y se abre con «Nueva evaluación…»/«Nuevo hito…»; se pliega tras añadir. Columna «Fotos» con miniaturas (`fotosCeldaHTML`, hasta 3 + «+N»).

### Informe PDF
- Cabecera con la clínica (logo `clinicaLogo`, `clinicaNombre`, profesional y colegiado) como el PDF del plan en casa, solo en la primera página.
- «Resumen por ejercicio» (agrupado por bloque, días previstos ≤ fecha del informe, puntuados y media con su bolita de color) tras la gráfica.
- «Detalle por días» opcional: casilla `#expDetalle` (`ui.exp.detalle`, marcada por defecto). Sin detalle, un informe normal ocupa una página.

### Salir y puerto ocupado (`main.go`, lanzadores)
- `POST /api/salir` → `handleSalir`: si hay copia en curso responde 409 con un texto para la usuaria; si no, responde y cierra el canal `salir`; `main` hace `srv.Shutdown` (5 s) y `db.Close()`. La UI (`salirApp`) confirma, espera a `saveChain`, llama y sustituye la página por «La aplicación se ha cerrado».
- `-version` imprime la versión y sale (lo usan los lanzadores).
- Si `:8765` está ocupado (`puertoOcupado`): si responde la misma versión, abre el navegador y sale; si es otra versión de Fisioterapia, le hace `POST /api/salir` y reintenta escuchar durante 6 s; si no, `avisoPuerto(msg)` muestra una ventana (macOS: `osascript` `display dialog`, mensaje por argumento; Windows: PowerShell `MessageBox`, mensaje por variable de entorno `FISIO_MSG`) además de escribirlo en la consola. Las versiones ≤ 0.0.4 no tienen `/api/salir`: al actualizar desde ellas hay que cerrar antes la vieja (lo dice `ACTUALIZAR.txt`).
- `Fisioterapia.command` / `.bat` comparan la versión que responde en `:8765` con `fisioterapia -version` y solo abren el navegador si coinciden; si no, lanzan el binario.

### Ayuda
- `AYUDA.md` y `AYUDA_CORTA` actualizados (mismas anclas).

### Pruebas
- Nuevo `tests/test_005.py` (menú, lista de pacientes, Puntuar hoy, teclado, archivar/ordenar, días de la semana en editar y asignar, mes, líneas y leyenda, informe con cabecera/resumen/detalle, cabecera compacta, nuevo ejercicio, crear desde bloque, nueva plantilla, guardar todo el plan como plantilla, Salir).
- Actualizados los tests existentes a la nueva interfaz (Biblioteca, ventana «Editar» pauta, acciones en lote ocultas, formularios de Progreso plegados, menús ⋯ y Plantillas ▾, chips del calendario en la vista Semana).
- Ejecución: cada test con su propio `mock_server.py` recién arrancado en un puerto distinto; con `seed_nuevo.json` salvo `test_ui.py` y `test_novedades.py`, que parten de datos vacíos.

## 24. Ventanas propias, Deshacer, historial del navegador e «Informe de pautas» (0.0.5)

### Ventanas propias (`avisar`, `preguntar`, `pedirTexto`)
- Sustituyen a `alert`, `confirm` y `prompt` (ya no queda ninguno en `index.html`). Devuelven promesas: `await avisar(msg)`, `if (!await preguntar(msg, op)) return;`, `const t = await pedirTexto(msg, valor)` (null si se cancela). Por eso las funciones que confirman son `async`. **Regla:** en código nuevo, nunca `alert/confirm/prompt`.
- Opciones `op`: `titulo`, `boton` (texto del botón principal), `cancelar`, `peligro` (botón rojo y el foco empieza en «Cancelar») y `palabra` (hay que escribirla para confirmar; se compara con `norm`, sin mayúsculas ni tildes). Ejemplo: `borrarTodo` pide «BORRAR».
- Se pintan en `#dialogo` (z-index 9000: encima de las ventanas de la app, debajo del aviso de copia en curso y de la foto ampliada) y se encolan si llegan varias. Mientras hay una abierta, `header`, `#main`, `#modal`, `#avisoNovedades` y `#deshacer` quedan `inert`, y un `keydown` en fase de captura en `window` se queda con el teclado: Esc cancela (o cierra el aviso), Intro en el campo acepta, Tab circula por sus botones y el resto de teclas no llegan a la app (no se puntúa con 0–3 por debajo). El foco se pone a los 30 ms para que el Intro que abrió la ventana no pulse ya su botón.
- `changePautas(mutate, confirmarSiempre, textoDeshacer)` es `async`, pero si no hace falta confirmar aplica el cambio de forma síncrona (lo necesita `moverPauta` para conservar el scroll).
- **Pruebas:** si existe `window.__dialogoAuto(tipo, msg, valor, op)`, las ventanas no se pintan y se usa lo que devuelva. `tests/mock_server.py` lo define para que pasen por `alert/confirm/prompt` del navegador y las pruebas antiguas sigan contestando con `page.on('dialog')`. Con `MOCK_DIALOGOS=propios` no lo define y se prueban las ventanas de verdad (`tests/test_dialogos.py`).

### Deshacer
- Patrón: `const antes = instantanea();` al principio (una copia `JSON.stringify(db)`), el cambio, y `ofrecerDeshacer(antes, 'texto')`. Si los datos no han cambiado (por ejemplo, se canceló) no sale nada. El aviso `#deshacer` dura 15 s y solo guarda el último cambio; `deshacer()` restaura `db` con esa copia y repinta (y guarda). Cmd/Ctrl+Z hace lo mismo fuera de los campos de texto.
- Está en: eliminar pacientes, archivar/recuperar, eliminar o quitar pautas (incluido «Quitar de este día» / «Quitar todos los ejercicios»), cualquier cambio de pautas que borre puntuaciones, eliminar ejercicio y bloque, quitar un PDF de la lista, eliminar hito y evaluación, cargar o eliminar un plan guardado, quitar/vaciar en el plan en casa, aplicar una plantilla, reducir semanas, quitar/vaciar en una plantilla, eliminar plantilla y «Borrar todo».
- No cubre lo que hace el servidor (restaurar una copia de seguridad, cambiar de carpeta de datos), que ya tiene su propia copia previa.
- **Fotos:** como deshacer puede volver a usar una foto, el servidor ya no borra en el acto las fotos sin uso: `cleanFotos` anota cuándo vio cada una sin uso (`fotosSinUso`) y solo la borra si sigue así pasados 10 min (`esperaFotoSinUso`) en un guardado posterior. Si vuelve a usarse, sale de la lista. Test: `TestCleanFotosEspera`.

### Historial del navegador
- `render()` llama a `registrarNav()`, que pone en la dirección la pantalla actual (`estadoNav()`: `#/pacientes`, `#/paciente/<id>/<pestaña>[/resumen]`, `#/plantilla/<id>`, `#/ejercicios`…) con `pushState` (o `replaceState` la primera vez). Solo cambia de entrada si cambia la pantalla, no con cada repintado.
- `popstate` → `irANav(k)`: reconstruye `ui` (con `prepararPaciente(id)`, la parte de `openPatient` que no repinta) y repinta con `aplicandoHistorial`. Al cargar la página, si hay dirección se va a esa pantalla (recargar no devuelve a Pacientes).
- `showModal` añade un paso al historial (`modalEnHistorial`) y `closeModal` lo quita con `history.back()` (marcando `ignorarPop`); así «Atrás» con una ventana abierta solo la cierra. Si mientras tanto se cambia de pantalla, `registrarNav` espera a que llegue ese `popstate` (`navPendiente`). «Atrás» también cancela una ventana propia abierta.

### «Informe de pautas»
- Textos: «Generar informe de pautas…», «Informe de pautas… (n)», título de la ventana, filtro «Informes de pautas», tipo `informe` → «Informe de pautas», nombre del archivo `<Apellidos>_<Nombre>_Informe_de_pautas_<desde>_<hasta>.pdf` y primera línea del PDF «Informe de pautas · seguimiento de ejercicios». La pestaña sigue llamándose **Informes** porque lista también los PDF del plan en casa. Los datos (`tipo: 'informe'`) no cambian.

### Pruebas
- Nuevo `tests/test_dialogos.py` (servidor con `MOCK_DIALOGOS=propios`): confirmación propia con foco en Cancelar y pantalla bloqueada, Esc, Deshacer (también en el servidor, con hitos), Ctrl+Z, avisos sobre una ventana abierta, pedir texto, «escribe BORRAR», Atrás/Adelante, Atrás con una ventana abierta, recargar en la misma pantalla, teclado bloqueado con una ventana abierta y Deshacer en la ventana del día.

## 25. Planes en casa como lista de planes (0.0.5, modelo de datos 4)

Sustituye al calendario continuo por fechas (`planCasa`) y a las copias guardadas (`planesGuardados`): cada paciente tiene una lista de planes, y un plan se edita con el mismo editor que las plantillas.

### Modelo (`schemaVersion = 4`)
- Tablas nuevas `planes` (`id`, `patient_id`, `nombre`, `inicio`, `fin`, `fin_manual`, `semanas`, `notas`, `creado`, `plantilla_id`) y `plan_items` (mismo formato que `plantilla_items`, sin `UNIQUE`). Columna nueva `plantillas.notas`. JSON: `db.planes = [{ id, patientId, nombre, inicio, fin, finManual, semanas, notas, creado, plantillaId, items }]`, `PlanCasaDoc` en Go.
- `items[].dia` cuenta desde el **lunes de la semana de `inicio`** (1 = ese lunes, 8 = el siguiente…), igual que en las plantillas; **`dia = 0` son los ejercicios «a elegir»** (también en plantillas). Días válidos de un plan: `primerDiaPlan` (= día de la semana de `inicio`) … `ultimoDiaPlan` (= primero + 7·semanas − 1). Fecha de un día: `fechaDiaPlan(pl, dia)`.
- `fin` = `inicio + 7·semanas − 1` (`finAutoPlan`) salvo que se cambie a mano (`finManual`); es informativa (lista, PDF, «Plan en casa hasta» de la lista de pacientes, estado en curso/terminado) y no cambia los días del plan.
- El servidor guarda y restaura las tablas nuevas (y sigue leyendo `plan_casa` y `planes_guardados`, que quedan vacías tras la conversión). Tests: `test_sql.py`.

### Conversión de los datos antiguos (en la página)
- `normalize()` llama a `migrarPlanesCasa()`: el calendario de cada paciente pasa a un plan «Plan en casa» (inicio = primer día con ejercicios, semanas = las necesarias para llegar al último), salvo que coincida exactamente con uno de sus planes guardados; cada plan guardado pasa a un plan con su descripción como nombre. Si una aplicación de plantilla (`plantillas[].aplicaciones`) toca esas fechas, se anota en `plantillaId`. Después `planCasa` y `planesGuardados` quedan vacíos y `planesMigrados` fuerza el primer guardado. Como antes de convertir el servidor hace la copia `copia-previa-actualizacion` (cambio de modelo), se puede volver atrás.
- Las `aplicaciones` de las plantillas ya no se usan (se conservan en la base de datos): «Pacientes (N)» cuenta los planes con `plantillaId` cuyo `fin` es hoy o después (`planesVigentesDePlantilla`).

### Interfaz
- Pestaña «Plan en casa»: `planCasaSeccionHTML` → lista (`planesListaHTML`, `tablaPlanesHTML`, filtros en `ui.fPlanes` con `filtrarPlanes`: nombre, intervalo `desde`–`hasta`, `mes`, `anio`; solo se repinta `#listaPlanes`) o editor (`planEditorHTML`) si `ui.planCasaId`. La dirección es `#/paciente/<id>/casa/<planId>`, así que «Atrás» vuelve a la lista.
- Editor común de planes y plantillas: `docActual()` devuelve el plan abierto o la plantilla; `cuerpoDocHTML` pinta «A elegir» (`diaDocHTML(t, 0)`) y las semanas (en un plan, `semanasCalendario` semanas de lunes a domingo, con fechas y los días fuera del plan como `.pc-fuera`). `openAddPl`, `anadirPl`, `openDiaPl`, `quitarPl`, `vaciarDiaPl`, `editarNotaPl`, `moverPl` trabajan sobre `docActual()`. En un plan, el buscador `#qCasa` filtra los días.
- Cabecera del plan: `guardarCabeceraPlan` (nombre, inicio, semanas, fin, notas). Si el inicio pasa a otra semana, los ejercicios se mueven con él (su `dia` no cambia); los que quedan fuera del nuevo rango se quitan tras confirmar (con «Deshacer»). Lleva un cerrojo (`guardandoCabecera`) porque al repintar se quita el campo con el foco y el navegador puede lanzar otro `change` a mitad (pasaba con las flechas del campo numérico); lo mismo en `guardarCabeceraPl` (plantillas).
- Acciones: `nuevoPlanCasa`, `abrirPlanCasa`, `cerrarPlanCasa`, `duplicarPlanCasa` (empieza `7·semanas` días después, mismo día de la semana), `vaciarPlanCasa`, `delPlanCasa`, `openGuardarPlantilla`/`saveGuardarPlantilla` (copia días, «a elegir» y notas; semanas = `semanasCalendario`), `openAplicarPlantilla`/`saveAplicarPlantilla` → `planDesdePlantilla` (un plan nuevo por paciente; la plantilla se repite con `diaPlantillaDe`).
- PDF: `exportarPlan(pid, planId)` → `pdfPlanCasa(p, pl)`: cabecera de la clínica, nombre del plan, «Del … al … (N semanas)», «Observaciones» (respeta los saltos de línea), «A elegir» y cada día con su fecha. Nombre del archivo `<Apellidos>_<Nombre>_Plan_en_casa_<Nombre_del_plan>_<inicio>_<fin>.pdf` (sin repetir si el plan se llama «Plan en casa») (`nombrePdf`: espacios → guiones bajos); se registra en «Informes» con tipo `plan`.

### Pruebas
- `tests/test_planes.py` (reescrito): conversión de datos antiguos, plan nuevo, días fuera del plan, añadir por día y «a elegir», notas, fin manual y «Recalcular», mover el inicio, lista y búsqueda (nombre, mes, año, intervalo), botones en una línea, PDF, duplicar, guardar como plantilla, usar plantilla, Atrás/Adelante, vaciar, eliminar y deshacer.
- `tests/ayuda_planes.py`: `PLAN_PRUEBA` define en la página `planPrueba(pid, inicio, semanas, items)` para que las demás pruebas creen planes.

- Ajuste posterior: en el editor, nombre y notas van arriba (`.plan-cab`) y las fechas (Empieza, Duración, Termina) en una fila justo encima del calendario (`.plan-fechas`, con el buscador a la derecha). La explicación de «Termina» está en el «?» (`AYUDA_CORTA['plan-fin']`); en el texto bajo las fechas solo se indica si la fecha de fin está cambiada a mano, con «Recalcular». En la lista, el botón de cada plan es «Editar plan».

### Barra de arriba y «Puntuar hoy» (ajuste)
- La versión está en la barra (`nav .version`, tras el botón de modo). `#btnTema` → `alternarTema()` cambia `ajustes.tema` (igual que Ajustes › Personalizar, cuyo `#pTema` se actualiza); `aplicarTema()` pone el icono (luna en claro, sol en oscuro) y su `aria-label`.
- `puntuarHoy(pid)` ya no cambia de pantalla: pone `ui.patientId` (en la lista no se abre la ficha) y abre la ventana del día. La ventana muestra «Ver su calendario» (`irCalendarioDia`) salvo que ya se esté en el calendario de ese paciente (`viendoCalendario()`). Todo lo de la ventana del día (puntuar, teclado, quitar, añadir) usa `ui.patientId`, así que funciona desde la lista, que se repinta al puntuar.

### Duración en días, semanas o meses (ajuste)
- Planes y plantillas tienen `duracion` (número) y `unidad` (`dias` | `semanas` | `meses`); columnas nuevas en `planes` y `plantillas` (añadidas con `columnas`, sin subir el modelo: la 0.0.5 aún no se había entregado). Sin unidad (datos anteriores) se toma `semanas` y `duracion = semanas`. Límites: 730 días, 104 semanas, 24 meses (`MAX_DUR`; en Go, `duracionValida`, con test `TestDuracionValida`).
- Plan: `finAutoPlan = finDuracion(inicio, duracion, unidad)` (meses de calendario con `sumarMeses`: 31 de enero + 1 mes → 28 de febrero, y el plan termina el día anterior). `ultimoDiaPlan` sale de esa fecha, así que las semanas de la cuadrícula y los días fuera del plan se deducen de la duración. `semanas` se sigue guardando (semanas de lunes a domingo que ocupa).
- Plantilla: la cuadrícula sigue siendo de semanas; `semanasDeDuracion` (días → ⌈n/7⌉, meses → 4·n). Solo se recalcula si cambia la duración. Al usarla, propone su duración y la repite hasta cubrir el plan.
- Campo común `duracionHTML(id, n, u, cambio)` / `leerDuracion(id)` (`#pcDur`, `#apDur`, `#plDur` + `N`/`U`). Al cambiar la unidad, `convertirDuracion` ajusta el número para conservar más o menos los días (2 semanas → 14 días), así no se quitan ejercicios sin querer.
- Duplicar empieza el día siguiente al fin calculado y mantiene cada ejercicio a la misma distancia del inicio.
- El menú «Biblioteca › Plantillas» pasa a llamarse «Plantillas casa» (y el título de la pantalla).

## 26. Exportar/importar la biblioteca, agenda de citas y Google Calendar (0.0.5, modelo de datos 5)

### 26.1 Exportar e importar ejercicios y bloques
- Formato de exportación: `{ "formato": "fisioterapia-maestros", "version": 1, "exportado": "AAAA-MM-DD", "clinica": "…", "ejercicios": [{ "id", "nombre" }], "bloques": [{ "id", "nombre", "nivel", "ejercicios": [ids] }] }`. Los bloques referencian ejercicios por **id**. Nunca lleva datos de pacientes.
- `openExportarMaestros()` (casillas Bloques / Ejercicios) → `datosExpMaestros(conBl, conEj)` (los bloques llevan siempre sus ejercicios; con «Ejercicios», toda la biblioteca sin los textos libres) → `exportarMaestros()`: `POST /api/exportar?tipo=json&nombre=…&inicio=…` (el mismo endpoint que los PDF; con `tipo=json` valida que sea JSON y guarda `.json`; en Windows el filtro del diálogo cambia según la extensión). La carpeta elegida se recuerda en `ajustes.maestrosCarpeta`.
- Importación (`leerImportBloques`, los tres `<input type=file>`: `#fileBloques` en Ajustes › Datos, `#fileBloquesB` en Bloques, `#fileEjercicios` en Ejercicios): `interpretarImport(j)` acepta `fisioterapia-maestros` y el catálogo `fisioterapia-bloques` (ejercicios por nombre, id `<bloque>-<n>`; de un catálogo solo se traen los ejercicios de los bloques que se añaden: `soloDeBloques`). `planImport(d)` decide sin tocar nada: bloque existente = mismo id o mismo nombre+nivel (normalizados con `norm`); ejercicio existente = mismo id (que no sea texto libre) o mismo nombre normalizado → los bloques nuevos apuntan al existente; un id ocupado por otra cosa recibe un `uid()` nuevo. El resumen avisa (`.aviso-import`) si la biblioteca ya tiene datos y el botón pasa a «Combinar e importar». `aplicarImportBloques()` añade y ofrece «Deshacer».
- Botones comunes: `botonesMaestrosHTML(idFile)`. Ayuda corta `maestros`, sección del manual `exportar-importar`.
- Pruebas: `tests/test_maestros.py`.

### 26.2 Agenda de citas
- Modelo 5 (`schemaVersion = 5`): tablas `citas` (`id`, `patient_id` con cascada, `fecha`, `hora` HH:MM, `duracion` en minutos, `nota`, `serie_id`, `fecha_serie`, `modificada`) y `citas_series` (`id`, `patient_id`, `dias` como en las pautas pero «todos» = `1234567`, `hora`, `duracion`, `desde`, `hasta` ('' = sin fin), `nota`, `excluidas` JSON, `creada`). JSON: `db.citas`, `db.seriesCitas`; Go: `Cita`, `SerieCitas` (validación con `horaValida`, `duracionCita` 5–720, `diasCita`). Guardar/restaurar como el resto (restaurar copias antiguas deja la agenda vacía).
- **Las series se materializan**: la página crea una cita por ocurrencia (`generarSerie(d, s)`, idempotente: no crea una fecha que ya tenga cita con ese `serieId`+`fechaSerie` ni una de `excluidas`). Sin `hasta`, hasta hoy + 26 semanas; `normalize()` → `ampliarSeries()` añade las que van entrando al abrir la app (`seriesAmpliadas` fuerza el guardado). Así cada cita es un evento independiente (también en Google, sin RRULE ni excepciones).
- Cambiar una ocurrencia: «Solo esta» → `modificada = true` (la serie no la vuelve a tocar; `fechaSerie` conserva el hueco original). «Esta y las siguientes» → `cambiarSerieDesde(s, corte, datos, editando)`: si `corte` > `s.desde` parte la serie (la vieja termina el día anterior; la nueva hereda las `excluidas` ≥ corte y las citas cambiadas aparte), borra las no modificadas desde `corte` y regenera. Mover a otro día de la semana sustituye ese dígito en `dias` (y si es a un día posterior de la misma semana, alarga `hasta` lo mismo, para no perder la última). Anular: `quitarCita` (añade a `excluidas`) o `terminarSerie(s, desde)`.
- Pantalla `viewAgenda()` (vista `agenda`, dirección `#/agenda`, nav «Agenda»): cuadrícula `agendaCuerpoHTML()` con columnas por día (`diasAgenda`: semana según `ajustes.agendaDias`, más los días con citas; o un día, `ui.agVista`), horas de `ajustes.agendaInicio`–`agendaFin` ampliadas si alguna cita cae fuera (`rangoHorasAgenda`), `PX_MIN` px por minuto, solapes en columnas (`columnasSolape`), horas ocupadas de Google (`ocupadosDia`, `.ag-ocupado`, sin eventos de ratón) y línea de «ahora». La cuadrícula tiene su propio scroll (`.ag-scroll`, cabecera de días fija); la posición se guarda en `ui.agScroll` (`situarAgenda`). Clic en un hueco → `clicAgenda` → `openCita(null, { fecha, hora })` redondeado a 15 min.
- Ventana de cita `openCita(id, pre)`: paciente, día, hora, duración (`opcionesDuracion`, por defecto `ajustes.citaDuracion`), «Se repite cada semana» (días, hasta / sin fin), nota; `revisarSolapes()` avisa en vivo (`solapes()` contra citas y horas ocupadas; en una serie, cuenta los días con conflicto) y `guardarCita()` vuelve a preguntar antes de guardar encima. Botones «Anular cita…», «Ver ficha» (pestaña Citas), «Puntuar» (si ese día tiene ejercicios).
- Diálogo nuevo `elegir(msg, [[valor, texto]…], op)` (tipo `choice` en el módulo de ventanas propias; devuelve el valor o `null`). En las pruebas con el servidor simulado pasa por `prompt` (aceptar = primera opción, o el texto que se pase).
- «Puntuar» (→ `puntuarCita`, abre la ventana del día) va en cada fila de la lista de citas del paciente cuando ese día tiene ejercicios (`exercisesOn`), no en la ventana de la cita (allí quedaba desfasado: se calculaba al abrirla y solo valía para días pasados). «Nueva cita» (`openCita(null, { patientId })`) también en cada fila de la lista de pacientes, salvo archivados.
- Días con cita en el calendario de ejercicios: `citasDia(pid, s)` y `marcaCitasDia` (un punto por cita, `.marca-cita`, con el color de la cita y la hora en el `title`) en `celdaDia` y `celdaMes`; `textoCitasDia` añade «· Cita 17:00–17:45» en la vista de un día y en la ventana del día.
- Ficha: pestaña `citas` (`citasSeccionHTML`: series con «Cambiar…» → `openSerie`/`guardarSerie` a partir de una fecha, «Terminar…» → `anularSerie` desde mañana; próximas; pasadas plegadas). «Próxima cita» en la cabecera (`proximaCita`) y en la lista de pacientes. Eliminar pacientes borra sus citas y series.
- Ajustes › Agenda (`agendaAjustesHTML`): horario, días visibles (`#agDias`, se guarda al cambiar), duración por defecto, Google Calendar y título de los eventos (`ajustes.googleTitulo`: `nombre` | `iniciales` | `cita`).
- Vista de mes (`ui.agVista = 'mes'`): `agendaMesHTML()` (columnas = días visibles + los que tengan citas ese mes; `MAX_CITAS_MES` por casilla y «+N más»; horas ocupadas resumidas); clic en la casilla → cita nueva ese día, en el número → vista de día. `navAgenda` avanza meses.
- Colores: `color` en citas y series y `colorCita` en el paciente (columnas `citas.color`, `citas_series.color`, `patients.color_cita`, añadidas con `columnas`, sin subir el modelo). Valores = `colorId` de los eventos de Google Calendar (`"1"`…`"11"`, `colorValido` en Go; `''` = color de la app). `COLORES_CITA`, `estiloColorCita` (variables `--cc`/`--ct`, texto oscuro en colores claros), `selectorColorHTML`/`marcarColor`/`leerColor`. Una cita nueva toma el color del paciente salvo que se elija otro (`citaEd.colorTocado`); las series lo pasan a sus citas (`generarSerie`). `cambiarColorPaciente` ofrece aplicarlo a las próximas citas y series que tenían el color anterior. En Google, `colorId` del evento (`null` si no tiene, para quitarlo con PATCH); la firma solo cambia si hay color, así actualizar no vuelve a subir todas las citas.
- Pruebas: `tests/test_agenda.py` (citas, clic en hueco, solapes, series, solo esta / las siguientes, mover de día, anular, sin fin y ampliación al abrir, ficha, cambiar y terminar series, ajustes, eliminar paciente) y la sección 7 de `test_dialogos.py` (ventana de tres botones).

### 26.3 Google Calendar (`google.go`)
- **Conexión (OAuth 2.0, app de escritorio con PKCE).** El usuario crea en Google Cloud un ID de cliente de tipo «App de escritorio» (pasos en Ajustes › Agenda y en el manual; hay que **publicar** la app para que el refresh token no caduque a los 7 días) y lo guarda: `POST /api/google/credenciales`. `GET /api/google/conectar` redirige a Google con `state` y `code_challenge`; la vuelta es `http://127.0.0.1:8765/?state=…&code=…` (la raíz: `handleIndex` lo detecta y llama a `handleGoogleVuelta`, que cambia el código por tokens, comprueba que se concedió el permiso del calendario y activa la sincronización de la carpeta abierta). Ámbitos: `openid email https://www.googleapis.com/auth/calendar`. ID, secreto, refresh token y correo se guardan en **`google.json`** junto a `config.json` (permisos 0600), no en la carpeta de datos ni en las copias. El token de acceso vive en memoria (`tokenAcceso`; si Google responde `invalid_grant` se olvida el refresh token y se pide reconectar).
- **Por carpeta de datos** (tabla `google_sync`, clave/valor): `activo`, `calendario` (id del calendario «Fisioterapia · citas» que crea la app con la zona horaria del principal), `ultimoPull`, `ocupadosCalendarios` (JSON; por defecto `["primary"]`). Tabla `google_eventos` (`cita_id` → `event_id`, `firma` = hash de lo subido, `remoto` = «fecha T hora | minutos» de Google la última vez). Ninguna de las dos la toca `saveState` ni `restoreFrom`: tras restaurar una copia, la siguiente pasada pone Google al día.
- **Pasada** (`POST /api/google/sincronizar` → `sincronizarGoogle()` → `datosSync.pasada`), una a la vez (`gSyncMu`), sin tener `mu` durante las llamadas a Google: (1) comprueba o crea el calendario (si se borró en Google, se crea otro y se vuelve a subir todo); (2) pide a Google los eventos de la app cambiados desde `ultimoPull` (`privateExtendedProperty=app=fisioterapia`, `showDeleted`): si un evento se movió o se borró allí y la cita **no** cambió aquí (firma igual a la guardada), lo devuelve como cambio (`mover` / `anular`) y actualiza la firma como si ya estuviera aplicado; si cambió en los dos lados, gana la aplicación; (3) sube citas nuevas o cambiadas (POST/PATCH; un PATCH a un evento que ya no existe se convierte en POST) y borra los eventos de citas que ya no existen; las citas de hace más de 30 días no se suben; máximo 120 operaciones por pasada (`pendientes` > 0 y la página vuelve a llamar); (4) `freeBusy` de los calendarios elegidos (sin títulos), de 7 días atrás a 90 adelante en tramos de 30 días. Lo hecho se guarda aunque la pasada falle a medias (para no duplicar eventos) y el `ultimoPull` solo avanza si termina bien.
- Eventos: título según `googleTitulo` (nombre y apellidos + nota en la descripción, iniciales o «Cita»), `extendedProperties.private = { citaId, app: "fisioterapia" }`, hora local con desfase RFC 3339.
- **La página** (`gSync`): `cargarEstadoGoogle()` (`GET /api/google/estado`: configurado, conectado, cuenta, activo, último resultado y horas ocupadas en memoria del servidor) en `postCarga()`; sincroniza al abrir, cada 5 minutos con la pestaña visible, al volver a la pestaña y 3 s después de guardar cambios que afectan a lo subido (`trasGuardar`, comparando `firmaCitasGoogle()`). `aplicarCambiosGoogle()` aplica los cambios devueltos (mover → `modificada` si es de una serie; anular → `quitarCita`, que la excluye de la serie) y ofrece «Deshacer». Estado en la agenda (`#estadoGoogle`, botón ⟳) y en Ajustes (`pintarGoogleAjustes`: guía + campos o archivo JSON, conectar con espera activa, casilla de activar, elegir calendarios `GET/POST /api/google/calendarios`, desconectar `POST /api/google/desconectar` que revoca el token).
- Pruebas: `code/google_test.go` (servidor falso de Google: crear calendario, subir, PATCH, cambios en Google, conflicto, borrado en los dos lados, calendario borrado, límite por pasada, títulos, permiso retirado, parámetros de la autorización, correo del id_token) y `tests/test_google.py` (la página contra `/api/google/*` simulado en `mock_server.py`, que se controla con `POST /__google`).
- **No probado**: la conexión real con Google (el entorno de desarrollo no tiene acceso a sus servidores). La primera conexión en el Mac del usuario es la prueba final; si falla, el mensaje de error de Google sale en Ajustes › Agenda.

## 27. Sesiones: puntuaciones por cita (0.0.5, modelo de datos 6)

Cada cita de un paciente es una **sesión** con sus propios ejercicios y puntuaciones. Un día sin cita tiene una sola sesión, «sin cita» (`''`), que se comporta como antes.

### Modelo (`schemaVersion = 6`)
- `puntuaciones.sesion` (TEXT, `''` = sin cita, si no el id de la cita) entra en la **clave primaria** `(patient_id, fecha, exercise_id, sesion, repeticion)`. `migrateDB` rehace la tabla si falta la columna (en una transacción, como la migración de `repeticion`); lo anterior queda en `''`. Sin clave foránea a `citas` (se reescriben en cada guardado).
- Clave en el JSON: `pid|fecha|ejercicio|rep` (sin cita) o `pid|fecha|ejercicio|rep|cita`. `loadState` y `saveState` aceptan las dos (4 o 5 partes).
- `pautas.sesion`: `''` (todas, también sin cita), `s:<raíz de serie>`, `c:<cita>`, `-` (sin sesión: solo la sesión sin cita) o `!c:<cita>,s:<raíz>…` (todas menos esas; lo crea «Crear sesión vacía»: así no hay que partir la pauta por días). Varias sesiones concretas = una pauta por sesión. Go: `sesionValida` (`code/sesion_test.go`).
- `citas_series.raiz`: al partir una serie (`cambiarSerieDesde`), la parte nueva hereda la raíz (`raizSerie(s) = s.raiz || s.id`), así las pautas `s:` siguen valiendo.
- Restaurar copias anteriores: `sesion`/`raiz` vacíos. Tests: `test_sql.py`.

### Página
- Índices: `asegurarIndice()` construye `idxPunt` («pid|día|ejercicio|sesión» → repeticiones) e `idxSesDia` («pid|día» → sesiones con filas). `repsDe(pid, día, eid, ses)` es por sesión; `repsDia` junta todas; `resumenDia` (media del día) usa todas. `scoreKey(pid, día, eid, rep, ses)`, `partesClave(k)`.
- `sesionesDia(pid, día)`: una por cita (por hora) + la sin cita si no hay citas, si hay puntuaciones sin cita o si alguna pauta con `sesion` toca sin cita pero en ninguna cita de ese día (`-`, o `!…` que excluye todas las citas del día). `exceptuarSesion(p, token)` añade una excepción. `pautaEnSesion(p, ses)`, `exercisesSesion(pid, día, ses)`; `exercisesOn(pid, día)` = unión de sus sesiones (calendario, resumen, cabeceras). `cuentaDia(pid, día, q)` cuenta sesión × ejercicio (lista de pacientes, «N sin puntuar», «x de y puntuados»).
- Puntuaciones huérfanas (cita anulada, movida de día o de otro paciente): `normalizarSesiones()` al principio de cada `render()` las pasa a la sesión sin cita de ese día (`moverPuntSesion`, añadiendo repeticiones detrás). `resolverSinSesion(citas, serie)`: al dar la primera cita de un día con ejercicios (o puntuaciones) sin sesión pregunta (`elegir`, botones en columna) y `aplicarSinSesion` hace: `vacia` → `exceptuarSesion` en las pautas que tocaban sin cita; `copiar` → lo mismo + una copia de cada pauta con `c:<cita>` (ese día) o `s:<raíz>` (rango de la pauta, días de la serie); `asignar` → las `''`/`!…` ya tocan en la cita; las `-` se parten por esos días con una pauta de un día para la cita; las puntuaciones sin cita pasan a la cita. Una serie nueva se pregunta una vez. Cancelar = no se da la cita. Al anular (`quitarCita`, `terminarSerie`), `conservarSesionCita(c)`: si la cita tenía puntuaciones, sus ejercicios propios puntuados quedan ese día como pauta `-` de un día; las pautas `c:<cita>` se borran. `textoEjerciciosCitas` arma el aviso (con ⚠ si hay puntuaciones) de `anularCita` y `anularSerie`. `migrarSesiones(d)` (una vez, `ajustes.sesionesMigradas`): los días que tenían una sola cita y aún ninguna sesión pasan sus puntuaciones a esa cita.
- Ventana del día: «Quitar todos los ejercicios» va en la botonera de las pestañas (`.botonera-dia`, `#quitarTodosDia`); con citas, «Añadir a la sesión». `openDay(día, pestaña, ses)`, `ui.selSes`, `sesionPorDefecto` (hoy, la cita en curso o la siguiente; si no, la primera con algo sin puntuar), `sesionesDiaHTML` (botones `.ses-btn` con «x de y puntuados» y «+ Cita» → `otraCitaDia` → `openCita({ volverDia })`, que al guardar vuelve al día con la cita nueva abierta). Filas con `data-ses`; `setScore`, `addRep`, `quitarRep` y el teclado llevan la sesión. `addDayEx` crea pautas de ese día con `sesion` `c:<cita>` (o `-`/`''` sin cita). `quitarEjerciciosDeDia(eids, confirmar, ses)` parte la pauta y añade, para ese día, una pauta solo para cada una de las otras sesiones en que tocaba. `changePautas` avisa por sesión (`coveredBy(..., ses)`).
- Vista Día del calendario: una sección por sesión (`.ses-vista`).
- Asignar / Editar pauta: panel «En qué sesión» (`panelSesionesHTML`, estado en `sesPanel`; en Asignar va a la derecha de la lista, `.asig-cols`; solo con un paciente que tenga citas). Casilla «Todas» + lista de series (una línea por raíz) y citas sueltas del periodo de la pauta (máx. 60; `rangoAsignarCambiado` la rehace al cambiar fechas); botones Todas / Ninguna. `leerSesionesPanel()` → `['']` (o la excepción `!…` que tenía), `['-']` si no hay ninguna marcada, o un valor por sesión marcada (una pauta por cada una; al editar, las copias van en un grupo nuevo). `textoSesionPauta` en la lista de pautas.
- Resumen (`datosRango`): cada ejercicio cuenta una vez al día, con las repeticiones de todas las sesiones. Informe (`datosPdf`): `dias[].sesiones[] = { titulo, grupos }`; el detalle pone un título por sesión si hay varias (con una sola cita, en la cabecera del día); la gráfica usa la media del día.
- Lista de citas del paciente: «Puntuar» abre la sesión de esa cita (`puntuarCita(pid, fecha, cita)`); «Anular» → `anularCita`.
- Pruebas: `tests/test_sesiones.py`, `tests/test_sesiones_opciones.py`. En `mock_server.py`, aceptar una ventana de elegir sin texto es la primera opción.

## 28. «Sesión» en lugar de «cita» y listas por páginas (0.0.6)

### Nomenclatura
- En la interfaz, el manual (`AYUDA.md`), las ayudas «?», los avisos y el changelog, las **citas** se llaman **sesiones**: «Nueva sesión», «Programar sesión», «Anular sesión…», «+ Sesión», «Sin sesión», pestaña **Sesiones** de la ficha, «Agenda y sesiones» en el manual… La entrada 0.0.6 del changelog explica el cambio.
- **En el código y los datos sigue llamándose `cita`**, para no migrar la base de datos ni las copias: tablas `citas`, `citas_series`, `google_eventos.cita_id`, columna `patients.color_cita`; estado JSON `db.citas` / `db.seriesCitas`; Go `Cita`, `SerieCitas`; funciones `openCita`, `anularCita`, `citasDia`…; el valor `cita` del ajuste `googleTitulo`; las claves de ayuda `cita` y `citas` y la pestaña `citas` (dirección `#/paciente/<id>/citas`). Glosario: en el código, una **cita** es una sesión con fecha y hora (de la agenda) y `sesion` (en pautas y puntuaciones) dice a qué sesión pertenece algo: `''` es la de los días sin sesión programada, que en pantalla se llama **«Sin sesión»**.
- Los comentarios del código siguen usando «cita» en ese sentido técnico.
- Google Calendar (`google.go`): el calendario nuevo se llama `googleNombreCal` = «Fisioterapia · sesiones». Si el que ya existe se llama `googleNombreViejo` («Fisioterapia · citas»), la pasada lo renombra con un PATCH (si falla, lo intenta en la siguiente). Los eventos se titulan «Sesión» / «Sesión A. L.»; como el título entra en la firma, la primera pasada tras actualizar vuelve a subir los eventos (120 por pasada, como siempre). Prueba: `TestGoogleRenombraCalendarioViejo`.

### Listas por páginas
- `paginar(clave, items, repintar = 'render()', firma = '')` → `{ items, html }`: los elementos de la página actual y la botonera (`.paginacion`, `#pag-<clave>`), que se pone **dentro del contenedor de la lista, al final**. Con 10 elementos o menos no hay botonera. `repintar` es la llamada que vuelve a pintar la lista (por ejemplo `refrescarPacientes()`); `firma` resume los filtros (búsqueda, paciente, filtro de tipo…): si cambia, se vuelve a la página 1.
- Tamaño de página: `porPagina(clave)` lee `ajustes['pagina.<clave>']` (`10`, `25`, `50`, `100` o `todos`; por defecto 25) con `setAjuste`, así se recuerda por lista y por carpeta de datos. La página actual vive solo en memoria (`ui.pag[clave] = { p, firma }`). `cambiarPorPagina` deja a la vista la página que contiene el primer elemento que se veía; `irPagina` y `subirALista` (sube al principio de la lista si ha quedado fuera de la vista, también dentro de `.pautas-scroll`).
- Listas paginadas (clave): pacientes (`pacientes`; «Seleccionar los N» sigue marcando toda la lista filtrada, no solo la página), ejercicios (`ejercicios`), bloques (`bloques`), plantillas (`plantillas`), pautas en curso y terminadas (`pautas`, `pautasTerminadas`; el plegable de terminadas recuerda si está abierto en `ui.verTerminadas`), planes en casa (`planes`), sesiones de la ficha (`sesionesProximas`, `sesionesPasadas`, `sesionesSeries`; sustituye a los límites fijos de 12 próximas y 100 pasadas; `ui.verPasadas`), hitos (`hitos`), evaluaciones (`evaluaciones`), informes (`informes`) y copias de seguridad (`copias`).
- No se paginan las listas de elegir dentro de una ventana (Asignar, «Usar una plantilla…», pacientes de «Usar con pacientes…», «Pacientes con la plantilla», exportar varios pacientes), que filtran ocultando filas y tienen «Marcar visibles»; ni el Resumen, la agenda, el manual o las Novedades.
- La pantalla Plantillas filtra ahora sobre los datos (`ui.qPl`, `refrescarPlantillas()`, llamada desde `render()`), no ocultando filas; la búsqueda se conserva al volver. `filtrarPlantillas` / `buscadorPlantillasHTML` quedan para la ventana de elegir plantilla.
- Pruebas: `tests/test_paginacion.py`; `test_ui.py` (bloques) y `test_plantillas.py` adaptadas.

## 29. Observaciones al puntuar (modelo 7)

### Modelo
- Tabla nueva `observaciones(patient_id FK, fecha, sesion, bloque_id, exercise_id, repeticion, texto, PK(patient_id, fecha, sesion, bloque_id, exercise_id, repeticion))`. `schemaVersion = 7` (solo añade una tabla: no hay paso de migración; al abrir datos del modelo 6 se hace antes la copia `copia-previa-actualizacion-…`).
- El **ámbito** lo dan las columnas: `sesion` = id de la cita (`''` = sin sesión); con `bloque_id = ''`, `exercise_id = ''` y `repeticion = 0` es de **toda la sesión**; con `bloque_id`, de un bloque; con `exercise_id`, de un ejercicio (y `bloque_id`, si se quiere distinguir el mismo ejercicio en dos bloques); con `repeticion > 0` (y `exercise_id`), de una repetición. Así caben las de sesión, bloque, ejercicio y repetición sin cambiar el esquema. **De momento la interfaz solo usa las de sesión.**
- `saveState` descarta las vacías (solo espacios), las de pacientes o ejercicios que no existen y las de repetición sin ejercicio. `restoreFrom` las copia si la copia tiene la tabla. Sin clave foránea en `sesion`, `bloque_id` ni `exercise_id` (pueden ir vacíos; las citas se reescriben en cada guardado).
- Estado JSON: `observaciones: [{ patientId, fecha, sesion, bloqueId, exerciseId, repeticion, texto }]`. El texto se guarda tal cual (con saltos de línea).

### Cliente
- `buscarObs(pid, dia, ses, ambito)`, `textoObs(...)`, `ponerObs(pid, dia, ses, texto, ambito)` (vacío = quitar). `ambito` es `{ bloqueId, exerciseId, repeticion }`; por defecto `AMBITO_SESION`. `obsSesionesDia(pid, dia)`: las de sesión de un día, por hora.
- Siguen a las puntuaciones: `moverPuntSesion` llama a `moverObsSesion` (si en la sesión de destino ya hay una del mismo ámbito, se juntan los textos). `normalizarSesiones` también mueve a «sin sesión» las observaciones de citas que ya no existen o que cambiaron de día. `sesionesDia` muestra la sesión «sin cita» si tiene observaciones. Al eliminar un paciente se borran las suyas. El aviso de anular una sesión lo menciona (`textoEjerciciosCitas`).
- Ventana del día: `#obsSesion` encima de las pestañas (tras los botones de sesión) (de la sesión elegida, o «del día»); `escribirObsSesion` guarda en el modelo en cada tecla y llama a `save()` 800 ms después; al salir del campo, `save(); render()`.
- Dónde se ven: semana (`obsDiaHTML`, texto recortado a 2 líneas), mes (icono ✎ con el texto en el `title`), vista de día (`.obs-texto` y botón «Observaciones…»), lista de sesiones (`filaSesionHTML`, `.obs-fila`) e informe de pautas (apartado «Observaciones de las sesiones» tras el resumen, con `obsPeriodoPdf`; casilla `#expObs` / `opciones.observaciones`).
- Pruebas: `code/observaciones_test.go` (guardar, cargar, descartes y restaurar una copia), `tests/test_observaciones.py`; `tests/test_sql.py` cuenta 23 tablas.

## 30. Ordenar por cabecera

- Sustituye a los desplegables «Ordenar por» (pacientes e informes). `ORDEN_DEFECTO[clave] = [columna, 'asc'|'desc']`; `ordenDe(clave)` lee `ajustes['orden.<clave>']` (`'col:dir'`, vacío = por defecto); `cambiarOrden(clave, col)`: otra columna → asc; asc → desc; desc → por defecto (si el por defecto es desc, de él se pasa a asc). `ordenarLista(clave, lista, cols, desempate)`: `cols[col](x)` da el valor (número, texto o fecha ISO; texto con `localeCompare('es', { numeric: true })`); vacíos siempre al final; `desempate` siempre ascendente (si la columna no tiene valor, como `orden` del resumen, solo se usa el desempate).
- Cabeceras: `thOrden(clave, col, texto, repintar, attrs)` en tablas (`aria-sort`) y `cabListaHTML(clave, cols, repintar)` (`.cab-lista`) en listas de filas (la primera columna a la izquierda y las demás a la derecha). Cada botón es `.orden-btn` con `data-orden="clave:col"`.
- `paginar` añade el orden a la firma, así al cambiarlo se vuelve a la primera página.
- Listas: `pacientes` (nombre, ultima, proxima), `ejercicios` (nombre, bloques), `bloques` (nombre, nivel, ejercicios; por defecto nivel y nombre), `plantillas` (nombre, duracion —en días, `diasPlantilla`—, creada, pacientes), `planes` (nombre, inicio, fin, duracion), `hitos` y `evaluaciones` (fecha, texto), `informes` (titulo, tipo, periodo, generado), `copias` (fecha, tipo), `sesiones` y `sesionesPasadas` (fecha, estado = puntuados/total), `resumen` (nombre, exp, puntuados, media; por defecto orden de ejecución; siempre agrupado por bloque, ordenando dentro de cada uno).
- No se ordenan: las pautas (orden de ejecución manual), las series de sesiones y las listas de elegir dentro de ventanas.
- Pruebas: `tests/test_orden_cabeceras.py`; `test_005.py` adaptada.

## 31. Calendario fijo, filtros de fecha comunes y series en su pestaña

- **Barra del calendario fija** (`.cal-fija`): navegación, título, vistas, buscador y leyenda en dos filas, `position: sticky` con `top: calc(var(--hh) + var(--ph))`. `--ph` es la altura de la cabecera del paciente (`.sticky-head`, que cambia al compactarse): la mide `observarCabeceraPac()` con un `ResizeObserver`, llamada desde `render()` en la ficha. Por debajo de 1000 px se oculta el texto explicativo de la leyenda.
- **Filtros de fecha comunes**: `filtroFechasHTML(id, f, cambiar, anios, quitar)` pinta «Entre / y / mes / año / Quitar filtros» (ids `<id>Desde`, `<id>Hasta`, `<id>Mes`, `<id>Anio`, `<id>Quitar`); `coincideFechas(ini, fin, f)` dice si un intervalo (fin vacío = sin fin) toca esas fechas; `hayFiltroFechas(f)`. Los usan pautas (`ui.fPautas`, prefijo `fpa`), informes (`ui.fInf`, prefijo `fin`, sobre el día de generación, `fechaGenerado`) y sesiones (`ui.fSes`, prefijo `fs`). Los planes en casa conservan su propio filtro (`filtrarPlanes`).
- **Pautas**: botonera `#verPautas` Vigentes / Terminadas / Todas (`filtroPautas().ver`) en lugar del plegable «Pautas terminadas»; en «Todas» las terminadas van detrás con su título y sin flechas. El periodo de cada pauta sale de `periodoPauta(xs)`.
- **Sesiones**: las series vigentes (`seriesVigentes`) pasan a la pestaña «↻ Se repiten (N)» de la botonera (`filtroSes().ver = 'series'`, `seriesPacHTML`); si no quedan series se vuelve a «Próximas». Sin filtros de fecha en esa pestaña.
- **Lista de pacientes**: «Última sesión» abre su puntuación (`puntuarCita`, con la última cita de ese día si la hubo) y «Próxima sesión» la ventana de la sesión (`openCita`). «Puntuar hoy» va antes que «Nueva sesión».
- Pruebas: `tests/test_ficha_filtros.py`; `test_agenda.py` adaptada.

## 32. Orden por sesión (modelo 8) y ordenar al añadir

- **Pautas**: ya no se ordenan en su pestaña (sin flechas ni numeración; `moverPauta` sigue en el código sin usarse). El `orden` de las pautas es el orden por defecto de cada sesión.
- **Modelo 8**: tabla `orden_sesiones(patient_id FK, fecha, sesion, exercise_id FK, posicion, PK(patient_id, fecha, sesion, exercise_id))`. Estado JSON `ordenSesiones: { 'pid|fecha|sesión': [ids de ejercicio] }` (sesión vacía = sin cita). `saveState` descarta claves mal formadas y pacientes o ejercicios que no existen; `restoreFrom` la copia si existe. Solo añade una tabla: sin paso de migración.
- **Cliente**: `exercisesSesion` = `aplicarOrdenSesion(exercisesSesionBase(...))`; los ejercicios que no están en la lista (añadidos después) van detrás, en el orden de las pautas. `exercisesOn` aplica el orden si el día tiene una sola sesión (calendario de semana). `normalizarSesiones` olvida el orden de citas que ya no existen o cambiaron de día; eliminar un paciente borra el suyo.
- **Unidades**: se mueve un bloque entero o un ejercicio suelto (`unidadesSesion`, `moverUnidadSesion(dia, ses, eid, dir)`). En `filasDia` (ventana del día y vista Día del calendario), ↑ ↓ en el título de cada bloque y en cada ejercicio suelto; no se muestran mientras se busca.
- **Panel «Orden» al añadir** (`panelOrdenAddHTML(existentes)`, `#ordenAdd`): lo que ya hay (claves `x:N`) y lo marcado en `selectorEjerciciosHTML` (`b:bloque`, `e:ejercicio`; se sincroniza con un `change` delegado y en `marcarVisibles`), movible con ↑ ↓ en el propio DOM; `leerOrdenAdd()` devuelve las claves. Lo usan la pestaña «Añadir ejercicios» del día (`addDayEx` → `guardarOrdenTrasAnadir`, que no guarda nada si queda igual que el de las pautas) y `openAddPl` del plan en casa y las plantillas, también para «A elegir» (`anadirPl` renumera el `orden` del día abierto según el panel; lo escrito a mano y lo añadido a otros días va al final). «Editar» un día del plan añade con `openAddPl(dia, true)` y vuelve a la edición.
- Pruebas: `tests/test_orden_sesion.py`; `test_lote.py` adaptada; `observaciones_test.go` cubre también `ordenSesiones`; `test_sql.py` cuenta 24 tablas.
- **Correcciones (después)**: al dar la primera cita de un día con ejercicios sin sesión, «copiar» y «asignar» pasan a la cita el orden de «sin sesión» (`aplicarSinSesion`; con «asignar» se quita el de «sin sesión»). Al anular o mover una cita, `normalizarSesiones` pasa su orden a «sin sesión» si esta no tenía uno propio. Las ventanas de añadir ponen el panel «Orden» en una columna a la derecha de la lista (`colsAddHTML`, `.add-cols`; debajo por debajo de 820 px).

## 33. Versión 0.0.7: propuestas del análisis de usabilidad (ver `ANALISIS_UX.md`)

- **Filtros de fecha plegados**: `filtroFechasHTML` devuelve un `<details class="filtro-fechas" id="<id>Fechas">` («Filtrar por fecha»), abierto si hay filtro o si se abrió antes en esa lista (`ui.fechasAbiertas[id]`); `estadoFiltroFechas(id, f)` actualiza «Quitar filtros» y la marca «· activo». Lo usan pautas (`fpa`), sesiones (`fs`), informes (`fin`) y ahora también planes en casa (`fp`, con `cambiarFiltroPlanes`; el buscador por nombre sigue a la vista).
- **Menú «⋯»**: `menuAccionesHTML(de, [[texto, js, peligro, desactivado, id]])` (botón `.menu-mas`, `aria-label` «Más acciones de …»; reutiliza `.menu-sub.menu-claro.menu-fila` y `toggleSubmenu`). Usado en pautas (cabecera y filas), ventana del día (cada ejercicio y «Quitar todos…», `#quitarTodosDia`), sesiones y series, informes, hitos, evaluaciones, planes (fila y cabecera del plan), bloques y plantillas. «Vaciar el día…» está en `openDiaPl` (y `vaciarDiaPl` cierra esa ventana). Quedan como botones los borrados que ya están dentro de su propia ventana (datos del paciente, sesión, «Editar» un día) y los de Ajustes.
- **Cabecera de la ficha** sin `#diasSemana` (`diasPorSemanaHTML` sigue en el código). Atajos de teclado de la ventana del día: solo en la ayuda «puntuar».
- **Ejercicios y bloques en una columna** (sin `column-width`); `.bex` de cada bloque en columnas.
- **Buscador de pacientes en la barra** (`#buscaPac`, `#buscaPacInput`, `#buscaPacRes`): `resultadosBuscaPac` (hasta 8, activos primero), ↑ ↓ / Intro / Esc (`teclaBuscaPac`), ⌘K o Ctrl+K lo enfoca, `abrirDesdeBusca` cierra la ventana abierta y abre la ficha.
- **Lista de pacientes en columnas**: `.item.fila-pac` y `.cab-pac` comparten `grid-template-columns` (casilla, foto, paciente, última sesión, próxima sesión, acciones). La cabecera lleva la casilla de marcar todos (con `aria-label` «Seleccionar los N…») y los `botonOrden`; el filtro «Con sesiones» sube a la fila del buscador. Por debajo de 760 px las columnas se apilan bajo el nombre y muestran su etiqueta (`data-etq`). Los enlaces de sesión llevan `aria-label` «Última sesión: …» / «Próxima sesión: …».
- **Orden de las pestañas de la ficha**: `TABS_PAC` lleva el orden por defecto (Pautas · Sesiones · Calendario · Plan en casa · Progreso · Informes). `db.ajustes.ordenPestanas` guarda las claves de primer nivel separadas por comas (vacío = por defecto); `tabsPacOrdenadas()` lo aplica ignorando claves desconocidas y añadiendo al final las que falten (pestañas nuevas en versiones futuras). `primeraTabPac()` es la pestaña de entrada (`prepararPaciente`, ruta `#/paciente/<id>` sin pestaña y la reserva de `viewPaciente`). Se edita en Ajustes › Personalizar (`ordenPestanasHTML`, `moverPestana`, `#ordenPestanas`, botones «Subir X» / «Bajar X»).
- Pruebas adaptadas a los menús y los filtros plegados (`test_vaciar`, `test_planes`, `test_sesiones_opciones`, `test_agenda`, `test_sesiones`, `test_informes`, `test_evaluaciones`, `test_nuevo`, `test_libre`, `test_plantillas`, `test_dialogos`, `test_observaciones`, `test_sesiones_lista`, `test_ficha_filtros`); nueva `tests/test_v007.py`.
