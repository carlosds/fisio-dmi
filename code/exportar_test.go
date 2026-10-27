package main

import (
	"encoding/json"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func TestNombreSeguro(t *testing.T) {
	casos := map[string]string{
		"García Pérez_Ana_2026-10-01_2026-10-22": "García Pérez_Ana_2026-10-01_2026-10-22",
		"../../etc/passwd":                       "etc_passwd",
		"a/b\\c":                                 "a_b_c",
		"":                                       "paciente",
		"...":                                    "paciente",
		"x.pdf":                                  "x_pdf",
	}
	for in, want := range casos {
		if got := nombreSeguro(in); got != want {
			t.Errorf("nombreSeguro(%q) = %q, esperaba %q", in, got, want)
		}
	}
	if n := len([]rune(nombreSeguro(strings.Repeat("ñ", 500)))); n != 120 {
		t.Errorf("longitud %d", n)
	}
}

func TestExportar(t *testing.T) {
	dir := t.TempDir()
	pdf := "%PDF-1.7\nfake"
	q := "/api/exportar?carpeta=" + url.QueryEscape(dir) + "&nombre="
	// Con carpeta: guarda dentro, con el nombre saneado (no sale de la carpeta)
	w := httptest.NewRecorder()
	handleExportar(w, httptest.NewRequest("POST", q+url.QueryEscape("../../mal/Ana P"), strings.NewReader(pdf)))
	if w.Code != 200 {
		t.Fatalf("código %d: %s", w.Code, w.Body.String())
	}
	b, err := os.ReadFile(filepath.Join(dir, "mal_Ana P.pdf"))
	if err != nil || string(b) != pdf {
		t.Fatalf("no se guardó donde debía: %v", err)
	}
	var res map[string]string
	json.Unmarshal(w.Body.Bytes(), &res)
	if res["carpeta"] != dir || res["path"] != filepath.Join(dir, "mal_Ana P.pdf") {
		t.Errorf("respuesta inesperada: %v", res)
	}
	if m, _ := filepath.Glob(filepath.Join(dir, "*.tmp")); len(m) != 0 {
		t.Errorf("quedó un temporal: %v", m)
	}
	// El mismo nombre otra vez no pisa el anterior
	w = httptest.NewRecorder()
	handleExportar(w, httptest.NewRequest("POST", q+"T", strings.NewReader(pdf)))
	w = httptest.NewRecorder()
	handleExportar(w, httptest.NewRequest("POST", q+"T", strings.NewReader(pdf)))
	if _, err := os.Stat(filepath.Join(dir, "T (2).pdf")); w.Code != 200 || err != nil {
		t.Errorf("el segundo PDF con el mismo nombre debía ser «T (2).pdf» (%v)", err)
	}
	// Carpeta inexistente
	w = httptest.NewRecorder()
	handleExportar(w, httptest.NewRequest("POST", "/api/exportar?carpeta=/no/existe&nombre=x", strings.NewReader(pdf)))
	if w.Code != 400 {
		t.Errorf("carpeta inexistente debía dar 400, dio %d", w.Code)
	}
	// Lo que no es un PDF se rechaza
	w = httptest.NewRecorder()
	handleExportar(w, httptest.NewRequest("POST", q+"x", strings.NewReader("<html>")))
	if w.Code != 400 {
		t.Errorf("un no-PDF debía dar 400, dio %d", w.Code)
	}
	if _, err := os.Stat(filepath.Join(dir, "..", "mal")); err == nil {
		t.Errorf("escribió fuera de la carpeta")
	}
}

func TestPdfLibEmbebida(t *testing.T) {
	w := httptest.NewRecorder()
	handlePdfLib(w, httptest.NewRequest("GET", "/pdf-lib.min.js", nil))
	if w.Code != 200 || w.Body.Len() < 100000 || !strings.Contains(w.Body.String(), "PDFLib") {
		t.Errorf("la librería embebida no es la esperada (%d bytes)", w.Body.Len())
	}
}

func TestSubirFoto(t *testing.T) {
	fotosDir = t.TempDir()
	jpg := "\xff\xd8\xff\xe0fakejpeg"
	w := httptest.NewRecorder()
	handleSubirFoto(w, httptest.NewRequest("POST", "/api/foto", strings.NewReader(jpg)))
	if w.Code != 200 || !strings.Contains(w.Body.String(), "/fotos/") {
		t.Fatalf("subida: %d %s", w.Code, w.Body.String())
	}
	var r map[string]string
	json.Unmarshal(w.Body.Bytes(), &r)
	if b, err := os.ReadFile(filepath.Join(fotosDir, filepath.Base(r["url"]))); err != nil || string(b) != jpg {
		t.Fatalf("la foto no se guardó: %v", err)
	}
	w = httptest.NewRecorder()
	handleSubirFoto(w, httptest.NewRequest("POST", "/api/foto", strings.NewReader("<html>")))
	if w.Code != 400 {
		t.Errorf("un no-JPEG debía dar 400, dio %d", w.Code)
	}
	// nombresFotos: acepta URL existentes, descarta inexistentes y registra las usadas
	usadas := map[string]string{}
	j, err := nombresFotos([]string{r["url"], "/fotos/noexiste.jpg", "http://x/y.jpg"}, usadas, "h:1")
	if err != nil || strings.Count(j, ".jpg") != 1 || len(usadas) != 1 {
		t.Errorf("nombresFotos: %q %v %v", j, usadas, err)
	}
}

func TestDiasValidos(t *testing.T) {
	casos := map[string]string{"": "", "14": "14", "41": "14", "1234567": "", "7x1": "17", "8": "", "1111": "1"}
	for in, want := range casos {
		if got := diasValidos(in); got != want {
			t.Errorf("diasValidos(%q) = %q, esperaba %q", in, got, want)
		}
	}
}

// Una foto que deja de usarse no se borra enseguida: «Deshacer» en la página puede volver a necesitarla.
func TestCleanFotosEspera(t *testing.T) {
	dir := t.TempDir()
	viejo := fotosDir
	fotosDir = dir
	defer func() { fotosDir = viejo }()
	hace2h := time.Now().Add(-2 * time.Hour)
	for _, n := range []string{"usada.jpg", "suelta.jpg", "nueva.jpg"} {
		p := filepath.Join(dir, n)
		os.WriteFile(p, []byte("x"), 0o644)
		if n != "nueva.jpg" {
			os.Chtimes(p, hace2h, hace2h)
		}
	}
	existe := func(n string) bool { _, err := os.Stat(filepath.Join(dir, n)); return err == nil }
	usadas := map[string]string{"p1": "usada.jpg"}
	cleanFotos(usadas)
	if !existe("suelta.jpg") || !existe("usada.jpg") || !existe("nueva.jpg") {
		t.Fatal("la primera limpieza no debe borrar nada: la foto suelta acaba de quedarse sin uso")
	}
	// vuelve a usarse (como al deshacer): deja de contar
	cleanFotos(map[string]string{"p1": "usada.jpg", "p2": "suelta.jpg"})
	fotosSinUsoMu.Lock()
	_, sigue := fotosSinUso[filepath.Join(dir, "suelta.jpg")]
	fotosSinUsoMu.Unlock()
	if sigue {
		t.Fatal("una foto que vuelve a usarse debe salir de la lista de sin uso")
	}
	cleanFotos(usadas)
	fotosSinUsoMu.Lock()
	fotosSinUso[filepath.Join(dir, "suelta.jpg")] = time.Now().Add(-esperaFotoSinUso - time.Minute)
	fotosSinUsoMu.Unlock()
	cleanFotos(usadas)
	if existe("suelta.jpg") {
		t.Fatal("pasado el tiempo de espera, la foto sin uso se borra")
	}
	if !existe("usada.jpg") || !existe("nueva.jpg") {
		t.Fatal("no se borran las fotos usadas ni las recién subidas")
	}
}

func TestDuracionValida(t *testing.T) {
	casos := []struct {
		n   int
		u   string
		sem int
		wn  int
		wu  string
	}{{10, "dias", 2, 10, "dias"}, {0, "meses", 5, 1, "meses"}, {99, "meses", 5, 24, "meses"}, {3, "", 3, 3, "semanas"}, {5, "años", 2, 2, "semanas"}}
	for _, c := range casos {
		if n, u := duracionValida(c.n, c.u, c.sem); n != c.wn || u != c.wu {
			t.Errorf("duracionValida(%d, %q, %d) = %d, %q; quería %d, %q", c.n, c.u, c.sem, n, u, c.wn, c.wu)
		}
	}
}
