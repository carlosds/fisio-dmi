package main

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"
)

// Las integraciones de calendario registran sus rutas y salen en GET /api/calendarios.
func TestIntegracionesCalendario(t *testing.T) {
	mux := http.NewServeMux()
	registrarCalendarios(mux)
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, httptest.NewRequest("GET", "/api/calendarios", nil))
	var lista []map[string]string
	if err := json.Unmarshal(rec.Body.Bytes(), &lista); err != nil || len(lista) != 1 || lista[0]["id"] != "google" || lista[0]["nombre"] != "Google Calendar" {
		t.Fatalf("lista de integraciones: %v %s", err, rec.Body.String())
	}
	if _, patron := mux.Handler(httptest.NewRequest("POST", "/api/google/sincronizar", nil)); patron == "" {
		t.Fatal("las rutas de Google no están registradas")
	}
}
