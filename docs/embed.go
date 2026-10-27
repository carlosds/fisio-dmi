// Package docs incrusta en el ejecutable los textos de esta carpeta (go:embed solo alcanza ficheros de la
// carpeta del paquete o inferiores, por eso el paquete vive aquí y no en code/).
package docs

import _ "embed"

// Changelog es CHANGELOG.md: se muestra en Ajustes > Novedades y build.sh exige una entrada por versión.
//
//go:embed CHANGELOG.md
var Changelog []byte

// Ayuda es AYUDA.md: el manual de la usuaria (sección «Ayuda» de la interfaz).
//
//go:embed AYUDA.md
var Ayuda []byte
