# Fisioterapia

Aplicación local (sin internet obligatorio) para gestionar pacientes, pautas de ejercicios, puntuaciones, sesiones (agenda) e informes de fisioterapia pediátrica. Un único ejecutable en Go con la interfaz embebida; los datos van en SQLite en la carpeta que elija la usuaria.

## Estructura

| Carpeta | Contenido |
|---|---|
| `code/` | La aplicación: `main.go`, `google.go`, `index.html`, `pdf-lib.min.js` y las pruebas Go |
| `docs/` | `CHANGELOG.md`, `AYUDA.md` (manual de la usuaria), `DOCUMENTACION.md` (técnica), `ACTUALIZAR.txt` y `embed.go` |
| `internal/` | Catálogo de bloques `bloques_dmi.json` |
| `scripts/` | `build.sh` y los lanzadores de doble clic (`Fisioterapia.command`, `Fisioterapia.bat`) |
| `tests/` | Pruebas Python/Playwright y servidor simulado |
| `dist/` | Lo que se entrega (ejecutables y `.zip`). **No se sube a git** |

`docs/embed.go` incrusta `CHANGELOG.md` y `AYUDA.md` en el ejecutable (`go:embed` solo alcanza ficheros de la carpeta del paquete); `go.mod` y `go.sum` están en la raíz para que el módulo incluya `docs/` y `code/`.

## Compilar

```bash
scripts/build.sh 0.0.5 todo      # ejecutables en dist/bin/ y los .zip en dist/
go run ./code                    # desarrollo
go test ./code                   # pruebas Go
python3 tests/test_sql.py        # pruebas de migraciones SQL
```

Cada versión necesita su entrada `## X.Y.Z · fecha` en `docs/CHANGELOG.md`. Detalles en `docs/DOCUMENTACION.md`.
