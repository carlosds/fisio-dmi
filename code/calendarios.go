// Integraciones de la agenda con el calendario de otra aplicación (desde la 0.0.7).
//
// Cada integración se registra en integracionesCalendario con su id (el mismo que usa la página en el ajuste
// «calendarioExterno» y en INTEGRACIONES_CAL), su nombre y sus rutas, todas bajo /api/<id>/. La página espera de
// todas lo mismo:
//   - GET  /api/<id>/estado: si está configurada, conectada y activa, la hora y el error de la última
//     sincronización y los huecos ocupados (ver handleGoogleEstado).
//   - POST /api/<id>/sincronizar: sube las sesiones y devuelve un resultadoSync con los cambios hechos allí a las
//     sesiones, los huecos ocupados de los demás calendarios y si quedan cambios pendientes (la página vuelve a
//     llamar). El servidor no cambia las sesiones: los cambios los aplica la página, con «Deshacer».
//
// Hoy solo está Google Calendar (google.go). Para añadir otra: un archivo con sus rutas y su sincronización que
// devuelva estos tipos, una entrada aquí y otra en INTEGRACIONES_CAL de la página.
package main

import (
	"net/http"
	"time"
)

type integracionCalendario struct {
	ID     string
	Nombre string
	Rutas  func(mux *http.ServeMux)
}

var integracionesCalendario = []integracionCalendario{
	{ID: "google", Nombre: "Google Calendar", Rutas: rutasGoogle},
}

// Hueco ocupado en otro calendario, en hora local («2026-10-27T17:00»).
type ocupado struct {
	Inicio string `json:"inicio"`
	Fin    string `json:"fin"`
}

// Cambio hecho en el otro calendario que la página tiene que aplicar a una sesión.
type cambioCalendario struct {
	CitaID   string `json:"citaId"`
	Accion   string `json:"accion"` // «mover» o «anular»
	Fecha    string `json:"fecha,omitempty"`
	Hora     string `json:"hora,omitempty"`
	Duracion int    `json:"duracion,omitempty"`
}

// Resultado de una sincronización, igual para todas las integraciones.
type resultadoSync struct {
	Cambios    []cambioCalendario `json:"cambios"`
	Ocupados   []ocupado          `json:"ocupados"`
	Subidas    int                `json:"subidas"`
	Borradas   int                `json:"borradas"`
	Pendientes int                `json:"pendientes"`
	Hora       time.Time          `json:"hora"`
}

// registrarCalendarios añade las rutas de cada integración y GET /api/calendarios, la lista de las disponibles.
func registrarCalendarios(mux *http.ServeMux) {
	for _, ic := range integracionesCalendario {
		ic.Rutas(mux)
	}
	mux.HandleFunc("GET /api/calendarios", handleCalendarios)
}

func handleCalendarios(w http.ResponseWriter, r *http.Request) {
	out := []map[string]string{}
	for _, ic := range integracionesCalendario {
		out = append(out, map[string]string{"id": ic.ID, "nombre": ic.Nombre})
	}
	writeJSON(w, out)
}
