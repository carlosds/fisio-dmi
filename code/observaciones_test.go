package main

import (
	"database/sql"
	"os"
	"path/filepath"
	"testing"
	"time"
)

// abrirBasePrueba deja en db una base de datos nueva (modelo actual) en una carpeta temporal.
func abrirBasePrueba(t *testing.T, dir string) *sql.DB {
	t.Helper()
	d, err := sql.Open("sqlite", filepath.Join(dir, "fisioterapia.db")+"?_pragma=foreign_keys(1)")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { d.Close() })
	if err := prepararBaseDeDatos(d, filepath.Join(dir, "copias"), filepath.Join(dir, "fotos")); err != nil {
		t.Fatal(err)
	}
	return d
}

func TestObservaciones(t *testing.T) {
	viejaDB, viejasFotos := db, fotosDir
	t.Cleanup(func() { db, fotosDir = viejaDB, viejasFotos })
	dir := t.TempDir()
	db, fotosDir = abrirBasePrueba(t, dir), filepath.Join(dir, "fotos")
	if err := os.MkdirAll(fotosDir, 0o755); err != nil {
		t.Fatal(err)
	}

	st := State{
		Exercises: []Exercise{{ID: "e1", Nombre: "Puente"}},
		Patients:  []Patient{{ID: "p1", Nombre: "Ana"}},
		Observaciones: []Observacion{
			{PatientID: "p1", Fecha: "2026-10-28", Sesion: "c1", Texto: "Ha venido cansada.\nRepetir la semana que viene"}, // de la sesión
			{PatientID: "p1", Fecha: "2026-10-28", Texto: "Sin sesión"},
			{PatientID: "p1", Fecha: "2026-10-28", Sesion: "c1", BloqueID: "b1", Texto: "Bloque"},
			{PatientID: "p1", Fecha: "2026-10-28", Sesion: "c1", ExerciseID: "e1", Texto: "Ejercicio"},
			{PatientID: "p1", Fecha: "2026-10-28", Sesion: "c1", ExerciseID: "e1", Repeticion: 2, Texto: "Repetición"},
			{PatientID: "p1", Fecha: "2026-10-29", Texto: "   "},                                 // vacía: no se guarda
			{PatientID: "p9", Fecha: "2026-10-29", Texto: "otro"},                                // paciente que no existe
			{PatientID: "p1", Fecha: "2026-10-29", ExerciseID: "e9", Texto: "ejercicio borrado"}, // ejercicio que no existe
			{PatientID: "p1", Fecha: "2026-10-29", Repeticion: 1, Texto: "repetición sin ejercicio"},
		},
	}
	if err := saveState(st); err != nil {
		t.Fatal(err)
	}
	cargado, err := loadState()
	if err != nil {
		t.Fatal(err)
	}
	if len(cargado.Observaciones) != 5 {
		t.Fatalf("se esperaban 5 observaciones válidas, hay %d: %+v", len(cargado.Observaciones), cargado.Observaciones)
	}
	porTexto := map[string]Observacion{}
	for _, o := range cargado.Observaciones {
		porTexto[o.Texto] = o
	}
	if o := porTexto["Repetición"]; o.ExerciseID != "e1" || o.Repeticion != 2 || o.Sesion != "c1" {
		t.Errorf("la observación de una repetición no conserva su ámbito: %+v", o)
	}
	if _, ok := porTexto["Ha venido cansada.\nRepetir la semana que viene"]; !ok {
		t.Error("los saltos de línea del texto deben conservarse")
	}

	// Una copia de seguridad se restaura con sus observaciones.
	copia, err := crearCopiaDe(db, filepath.Join(dir, "copias"), fotosDir, "prueba-", time.Now())
	if err != nil {
		t.Fatal(err)
	}
	if err := saveState(State{Exercises: st.Exercises, Patients: st.Patients}); err != nil {
		t.Fatal(err)
	}
	if err := restoreFrom(filepath.Join(copia, "fisioterapia.db")); err != nil {
		t.Fatal(err)
	}
	if cargado, err = loadState(); err != nil || len(cargado.Observaciones) != 5 {
		t.Fatalf("al restaurar la copia deben volver las 5 observaciones: %d (%v)", len(cargado.Observaciones), err)
	}
}
