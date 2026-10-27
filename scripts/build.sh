#!/bin/bash
# Uso (desde cualquier carpeta): scripts/build.sh 1.4.0 [mac|windows|todo]
#   mac      (por defecto) compila "fisioterapia" para macOS
#   windows  compila "fisioterapia.exe" para Windows 64 bits
#   todo     compila ambas
# Todo lo que se entrega a la usuaria queda en dist/: los .zip y, en dist/bin/, los ejecutables sueltos (separados
# para que al descomprimir un zip en dist/ no choque «fisioterapia» con la carpeta «Fisioterapia» en macOS). dist/ no se sube a git.
# Se puede ejecutar desde macOS, Linux o WSL: siempre se compila para el sistema pedido (sin CGO).
# Arquitectura del Mac: la del propio Mac si se ejecuta en un Mac; si no (Linux/WSL), Apple Silicon (arm64).
# Para un Mac con procesador Intel:  MAC_ARCH=amd64 scripts/build.sh 1.4.0
# Si está el comando zip, deja además los paquetes listos para enviar en dist/ (con ACTUALIZAR.txt).
set -e
cd "$(dirname "$0")/.."   # raíz del repositorio
VERSION="${1:?Indica la versión, por ejemplo: scripts/build.sh 1.4.0 [mac|windows|todo]}"
OBJETIVO="${2:-mac}"
# Cada versión debe tener su entrada en docs/CHANGELOG.md (se muestra al usuario en Ajustes > Novedades).
if ! grep -qE "^## ${VERSION//./\\.}( |$)" docs/CHANGELOG.md; then
  echo "Falta la entrada «## $VERSION · fecha» en docs/CHANGELOG.md. Añádela antes de compilar." >&2
  exit 1
fi
mkdir -p dist/bin
LD="-X main.version=$VERSION"
if [ -z "$MAC_ARCH" ]; then
  if [ "$(uname -s)" = "Darwin" ] && [ "$(uname -m)" != "arm64" ]; then MAC_ARCH=amd64; else MAC_ARCH=arm64; fi
fi
if [ "$OBJETIVO" = "mac" ] || [ "$OBJETIVO" = "todo" ]; then
  GOOS=darwin GOARCH="$MAC_ARCH" CGO_ENABLED=0 go build -ldflags "$LD" -o dist/bin/fisioterapia ./code
  echo "Compilado dist/bin/fisioterapia (macOS $MAC_ARCH) versión $VERSION"
fi
if [ "$OBJETIVO" = "windows" ] || [ "$OBJETIVO" = "todo" ]; then
  GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -ldflags "$LD" -o dist/bin/fisioterapia.exe ./code
  echo "Compilado dist/bin/fisioterapia.exe (Windows) versión $VERSION"
fi

paquete() {   # paquete <nombre del zip> <archivos...>   (los ejecutables se cogen de dist/bin/, el resto de scripts/)
  command -v zip >/dev/null 2>&1 || return 0
  local nombre="$1"; shift
  local tmp; tmp="$(mktemp -d)"
  mkdir -p "$tmp/Fisioterapia"
  cp "$@" docs/ACTUALIZAR.txt "$tmp/Fisioterapia/"
  rm -f "dist/$nombre"
  (cd "$tmp" && zip -qr "$OLDPWD/dist/$nombre" Fisioterapia)
  rm -rf "$tmp"
  echo "Paquete dist/$nombre"
}
if [ "$OBJETIVO" = "mac" ] || [ "$OBJETIVO" = "todo" ]; then paquete "Fisioterapia-$VERSION-mac.zip" dist/bin/fisioterapia scripts/Fisioterapia.command; fi
if [ "$OBJETIVO" = "windows" ] || [ "$OBJETIVO" = "todo" ]; then paquete "Fisioterapia-$VERSION-windows.zip" dist/bin/fisioterapia.exe scripts/Fisioterapia.bat; fi
