#!/bin/bash
# Doble clic para arrancar Fisioterapia. Déjalo en la misma carpeta que el programa "fisioterapia".
cd "$(dirname "$0")" || exit 1

URL="http://127.0.0.1:8765/"

if [ ! -f ./fisioterapia ]; then
  osascript -e 'display dialog "No encuentro el programa «fisioterapia» junto a este archivo." buttons {"OK"} with icon stop' >/dev/null
  exit 1
fi

# Quita la marca de «descargado de internet» y asegura que es ejecutable.
xattr -d com.apple.quarantine ./fisioterapia 2>/dev/null
chmod +x ./fisioterapia

# Si ya está en marcha ESTA misma versión, solo abre el navegador. Si es otra versión (por ejemplo, la
# anterior seguía abierta tras actualizar), el programa se encarga de cerrarla y abrir la nueva.
ACTUAL=$(curl -s --max-time 1 "${URL}api/changelog" | sed -n 's/.*"version":"\([^"]*\)".*/\1/p')
if [ -n "$ACTUAL" ] && [ "$ACTUAL" = "$(./fisioterapia -version 2>/dev/null)" ]; then
  open "$URL"
  exit 0
fi

clear
echo "Fisioterapia se está iniciando… (se abrirá en el navegador)"
echo "NO CIERRES esta ventana mientras uses la aplicación."
echo
./fisioterapia
