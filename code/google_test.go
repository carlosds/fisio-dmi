package main

// Pruebas de la sincronización con Google Calendar contra un servidor falso de Google.
// Para ejecutarlas: copia este archivo como google_test.go junto a main.go y google.go y ejecuta «go test».

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"net/url"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

type googleFalso struct {
	mu         sync.Mutex
	eventos    map[string]*eventoGoogle
	cambiados  []string // eventos que devolverá el próximo listado (cambios «hechos en Google»)
	calendario string
	borrado    bool // el calendario de la aplicación se ha borrado en Google
	peticiones []string
	n          int
	tokenMalo  bool
}

func (g *googleFalso) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.peticiones = append(g.peticiones, r.Method+" "+r.URL.Path)
	p := r.URL.Path
	writeJSON := func(v any) { w.Header().Set("Content-Type", "application/json"); json.NewEncoder(w).Encode(v) }
	switch {
	case p == "/token":
		r.ParseForm()
		if g.tokenMalo {
			w.WriteHeader(400)
			writeJSON(map[string]string{"error": "invalid_grant"})
			return
		}
		writeJSON(map[string]any{"access_token": "acc", "expires_in": 3600})
		return
	}
	if r.Header.Get("Authorization") != "Bearer acc" {
		w.WriteHeader(401)
		return
	}
	switch {
	case p == "/calendars/primary" && r.Method == "GET":
		writeJSON(map[string]string{"timeZone": "Europe/Madrid"})
	case p == "/calendars" && r.Method == "POST":
		g.n++
		g.calendario = fmt.Sprintf("cal%d@group", g.n)
		g.borrado = false
		g.eventos = map[string]*eventoGoogle{}
		writeJSON(map[string]string{"id": g.calendario})
	case strings.HasPrefix(p, "/calendars/") && strings.Count(p, "/") == 2 && r.Method == "GET":
		if g.borrado || strings.TrimPrefix(p, "/calendars/") != g.calendario {
			w.WriteHeader(404)
			writeJSON(map[string]any{"error": map[string]string{"message": "Not Found"}})
			return
		}
		writeJSON(map[string]string{"id": g.calendario})
	case p == "/freeBusy":
		var body struct {
			Items []struct {
				ID string `json:"id"`
			} `json:"items"`
		}
		json.NewDecoder(r.Body).Decode(&body)
		cals := map[string]any{}
		for _, it := range body.Items {
			cals[it.ID] = map[string]any{"busy": []map[string]string{{"start": "2026-11-02T08:00:00Z", "end": "2026-11-02T09:30:00Z"}}}
		}
		writeJSON(map[string]any{"calendars": cals})
	case strings.HasPrefix(p, "/calendars/"+g.calendario+"/events"):
		resto := strings.TrimPrefix(p, "/calendars/"+g.calendario+"/events")
		id := strings.TrimPrefix(resto, "/")
		switch r.Method {
		case "GET":
			if r.URL.Query().Get("privateExtendedProperty") != "app=fisioterapia" || r.URL.Query().Get("updatedMin") == "" {
				w.WriteHeader(400)
				return
			}
			items := []*eventoGoogle{}
			for _, k := range g.cambiados {
				items = append(items, g.eventos[k])
			}
			g.cambiados = nil
			writeJSON(map[string]any{"items": items})
		case "POST":
			var e eventoGoogle
			json.NewDecoder(r.Body).Decode(&e)
			g.n++
			e.ID = fmt.Sprintf("ev%d", g.n)
			g.eventos[e.ID] = &e
			writeJSON(e)
		case "PATCH":
			e, ok := g.eventos[id]
			if !ok || e.Status == "cancelled" {
				w.WriteHeader(404)
				writeJSON(map[string]any{"error": map[string]string{"message": "Not Found"}})
				return
			}
			var n eventoGoogle
			json.NewDecoder(r.Body).Decode(&n)
			n.ID = id
			g.eventos[id] = &n
			writeJSON(n)
		case "DELETE":
			if _, ok := g.eventos[id]; !ok {
				w.WriteHeader(410)
				return
			}
			delete(g.eventos, id)
			w.WriteHeader(204)
		}
	default:
		w.WriteHeader(404)
	}
}

func (g *googleFalso) contar(prefijo string) int {
	g.mu.Lock()
	defer g.mu.Unlock()
	n := 0
	for _, p := range g.peticiones {
		if strings.HasPrefix(p, prefijo) {
			n++
		}
	}
	g.peticiones = nil
	return n
}

// moverEnGoogle simula que el usuario mueve un evento en Google Calendar.
func (g *googleFalso) moverEnGoogle(id, inicio string, minutos int) {
	g.mu.Lock()
	defer g.mu.Unlock()
	t, _ := time.ParseInLocation("2006-01-02 15:04", inicio, time.Local)
	e := g.eventos[id]
	e.Start.DateTime = t.Format(time.RFC3339)
	e.End.DateTime = t.Add(time.Duration(minutos) * time.Minute).Format(time.RFC3339)
	g.cambiados = append(g.cambiados, id)
}

func (g *googleFalso) borrarEnGoogle(id string) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.eventos[id].Status = "cancelled"
	g.cambiados = append(g.cambiados, id)
}

func prepararGoogleFalso(t *testing.T) (*googleFalso, string) {
	t.Helper()
	g := &googleFalso{eventos: map[string]*eventoGoogle{}}
	srv := httptest.NewServer(g)
	t.Cleanup(srv.Close)
	dir := t.TempDir()
	viejos := []string{googleTokenURL, googleAPI}
	viejaRuta := googleConfigPath
	googleTokenURL, googleAPI = srv.URL+"/token", srv.URL
	googleConfigPath = func() string { return filepath.Join(dir, "google.json") }
	t.Cleanup(func() { googleTokenURL, googleAPI, googleConfigPath = viejos[0], viejos[1], viejaRuta; olvidarAcceso() })
	olvidarAcceso()
	if err := guardarGoogleConfig(googleConfig{ClientID: "x.apps.googleusercontent.com", ClientSecret: "s", RefreshToken: "r", Cuenta: "ana@gmail.com"}); err != nil {
		t.Fatal(err)
	}
	return g, dir
}

func nuevosDatos(citas ...Cita) *datosSync {
	d := &datosSync{citas: map[string]Cita{}, nombres: map[string][2]string{"p1": {"Ana", "López Pérez"}, "p2": {"Luis", "Otero"}},
		titulo: "nombre", mapa: map[string]mapeoGoogle{}, ocupadosEn: []string{"primary"}}
	for _, c := range citas {
		d.citas[c.ID] = c
		d.orden = append(d.orden, c.ID)
	}
	return d
}

func pasar(t *testing.T, d *datosSync) *resultadoSync {
	t.Helper()
	res := &resultadoSync{Cambios: []cambioGoogle{}, Ocupados: []ocupado{}}
	if err := d.pasada(res); err != nil {
		t.Fatal(err)
	}
	d.ultimoPull = "2026-01-01T00:00:00Z" // a partir de la primera pasada se piden los cambios de Google
	return res
}

func TestGoogleSincronizacion(t *testing.T) {
	g, _ := prepararGoogleFalso(t)
	manana := time.Now().AddDate(0, 0, 1).Format("2006-01-02")
	pasado := time.Now().AddDate(0, 0, 2).Format("2006-01-02")
	viejo := time.Now().AddDate(0, 0, -60).Format("2006-01-02")
	d := nuevosDatos(
		Cita{ID: "c1", PatientID: "p1", Fecha: manana, Hora: "17:00", Duracion: 45, Nota: "traer informe"},
		Cita{ID: "c2", PatientID: "p2", Fecha: pasado, Hora: "10:00", Duracion: 30},
		Cita{ID: "c0", PatientID: "p2", Fecha: viejo, Hora: "10:00", Duracion: 30}, // demasiado antigua: no se sube
	)

	// 1. Primera vez: crea el calendario y sube las dos citas.
	res := pasar(t, d)
	if d.calendario == "" || res.Subidas != 2 || len(d.mapa) != 2 {
		t.Fatalf("primera pasada: calendario %q, subidas %d, mapa %v", d.calendario, res.Subidas, d.mapa)
	}
	if _, ok := d.mapa["c0"]; ok {
		t.Fatal("la cita antigua no debería subirse")
	}
	e1 := g.eventos[d.mapa["c1"].EventID]
	if e1.Summary != "Ana López Pérez" || !strings.Contains(e1.Description, "traer informe") || e1.citaID() != "c1" || e1.Extended.Private["app"] != "fisioterapia" {
		t.Fatalf("evento mal formado: %+v", e1)
	}
	if f, h, du, _ := remotoDe(*e1); f != manana || h != "17:00" || du != 45 {
		t.Fatalf("hora del evento: %s %s %d", f, h, du)
	}
	if len(res.Ocupados) != 1 || !strings.HasPrefix(res.Ocupados[0].Inicio, "2026-11-02T") {
		t.Fatalf("huecos ocupados: %+v", res.Ocupados)
	}
	g.contar("")

	// 2. Sin cambios: no se sube nada.
	if res = pasar(t, d); res.Subidas != 0 || g.contar("POST /calendars/"+d.calendario+"/events")+g.contar("PATCH") != 0 {
		t.Fatalf("sin cambios no debería subir nada (subidas %d)", res.Subidas)
	}

	// 3. Cambio en la aplicación → PATCH.
	c := d.citas["c1"]
	c.Hora = "18:00"
	d.citas["c1"] = c
	res = pasar(t, d)
	if res.Subidas != 1 || g.contar("PATCH") != 1 {
		t.Fatalf("cambio local: subidas %d", res.Subidas)
	}
	if _, h, _, _ := remotoDe(*g.eventos[d.mapa["c1"].EventID]); h != "18:00" {
		t.Fatalf("el evento no se ha movido a las 18:00 (%s)", h)
	}

	// 4. Cambio en Google → se devuelve para aplicarlo en la aplicación, sin volver a subirlo.
	g.moverEnGoogle(d.mapa["c2"].EventID, pasado+" 12:30", 60)
	res = pasar(t, d)
	if len(res.Cambios) != 1 || res.Cambios[0] != (cambioGoogle{CitaID: "c2", Accion: "mover", Fecha: pasado, Hora: "12:30", Duracion: 60}) {
		t.Fatalf("cambio remoto: %+v", res.Cambios)
	}
	if res.Subidas != 0 {
		t.Fatal("no debería volver a subir la cita movida en Google")
	}
	// La página aplica el cambio: en la siguiente pasada la firma coincide y no se sube nada.
	c = d.citas["c2"]
	c.Hora, c.Duracion = "12:30", 60
	d.citas["c2"] = c
	if res = pasar(t, d); res.Subidas != 0 || len(res.Cambios) != 0 {
		t.Fatalf("tras aplicar el cambio remoto no debería haber nada que hacer: %+v", res)
	}

	// 5. Cambio a la vez en los dos lados: gana la aplicación.
	g.moverEnGoogle(d.mapa["c2"].EventID, pasado+" 13:00", 60)
	c = d.citas["c2"]
	c.Hora = "09:00"
	d.citas["c2"] = c
	res = pasar(t, d)
	if len(res.Cambios) != 0 || res.Subidas != 1 {
		t.Fatalf("conflicto: cambios %+v, subidas %d", res.Cambios, res.Subidas)
	}
	if _, h, _, _ := remotoDe(*g.eventos[d.mapa["c2"].EventID]); h != "09:00" {
		t.Fatalf("en un conflicto debería quedar la hora de la aplicación (%s)", h)
	}

	// 6. Borrada en Google → se anula en la aplicación.
	ev1 := d.mapa["c1"].EventID
	g.borrarEnGoogle(ev1)
	res = pasar(t, d)
	if len(res.Cambios) != 1 || res.Cambios[0].Accion != "anular" || res.Cambios[0].CitaID != "c1" {
		t.Fatalf("borrado remoto: %+v", res.Cambios)
	}
	if _, ok := d.mapa["c1"]; ok || res.Subidas != 0 {
		t.Fatal("la cita borrada en Google no debería seguir en el mapa ni volver a subirse")
	}
	delete(d.citas, "c1") // la página la anula
	d.orden = []string{"c2", "c0"}

	// 7. Borrada en la aplicación → DELETE en Google.
	delete(d.citas, "c2")
	d.orden = []string{"c0"}
	ev2 := d.mapa["c2"].EventID
	res = pasar(t, d)
	if res.Borradas != 1 || len(d.mapa) != 0 || g.eventos[ev2] != nil {
		t.Fatalf("borrado local: borradas %d, mapa %v", res.Borradas, d.mapa)
	}

	// 8. Si el calendario se borra en Google, se crea otro y se vuelve a subir todo.
	d.citas["c3"] = Cita{ID: "c3", PatientID: "p1", Fecha: manana, Hora: "11:00", Duracion: 45}
	d.orden = append(d.orden, "c3")
	pasar(t, d)
	viejoCal := d.calendario
	g.borrado = true
	res = pasar(t, d)
	if d.calendario == viejoCal || res.Subidas != 1 || len(d.mapa) != 1 {
		t.Fatalf("calendario borrado: %q → %q, subidas %d", viejoCal, d.calendario, res.Subidas)
	}
}

func TestGoogleTitulosYLimite(t *testing.T) {
	g, _ := prepararGoogleFalso(t)
	manana := time.Now().AddDate(0, 0, 1).Format("2006-01-02")
	var citas []Cita
	for i := 0; i < googleMaxCambios+5; i++ {
		citas = append(citas, Cita{ID: fmt.Sprintf("c%03d", i), PatientID: "p1", Fecha: manana, Hora: "09:00", Duracion: 30, Nota: "privada"})
	}
	d := nuevosDatos(citas...)
	d.titulo = "iniciales"
	res := pasar(t, d)
	if res.Subidas != googleMaxCambios || res.Pendientes != 5 {
		t.Fatalf("límite por pasada: subidas %d, pendientes %d", res.Subidas, res.Pendientes)
	}
	if res = pasar(t, d); res.Subidas != 5 || res.Pendientes != 0 {
		t.Fatalf("segunda pasada: subidas %d, pendientes %d", res.Subidas, res.Pendientes)
	}
	e := g.eventos[d.mapa["c000"].EventID]
	if e.Summary != "Cita A. L." || strings.Contains(e.Description, "privada") {
		t.Fatalf("con iniciales no debe salir el nombre ni la nota: %q / %q", e.Summary, e.Description)
	}
	// Cambiar lo que se ve en Google vuelve a subir las citas.
	d.titulo = "cita"
	if res = pasar(t, d); res.Subidas != googleMaxCambios || g.eventos[d.mapa["c000"].EventID].Summary != "Cita" {
		t.Fatalf("cambio de título: subidas %d", res.Subidas)
	}
}

func TestGooglePermisoRetirado(t *testing.T) {
	g, dir := prepararGoogleFalso(t)
	g.tokenMalo = true
	d := nuevosDatos(Cita{ID: "c1", PatientID: "p1", Fecha: time.Now().Format("2006-01-02"), Hora: "09:00", Duracion: 30})
	err := d.pasada(&resultadoSync{})
	if err != errCaducada {
		t.Fatalf("esperaba errCaducada, ha dado %v", err)
	}
	b, _ := os.ReadFile(filepath.Join(dir, "google.json"))
	var c googleConfig
	json.Unmarshal(b, &c)
	if c.RefreshToken != "" || c.ClientID == "" {
		t.Fatalf("con el permiso retirado se olvida el token pero no el ID de cliente: %+v", c)
	}
}

func TestGoogleConectarYVuelta(t *testing.T) {
	g, dir := prepararGoogleFalso(t)
	_ = g
	guardarGoogleConfig(googleConfig{ClientID: "x.apps.googleusercontent.com", ClientSecret: "s"})
	// La página de Google: la petición lleva PKCE, acceso offline y la dirección de vuelta a la raíz.
	rec := httptest.NewRecorder()
	handleGoogleConectar(rec, httptest.NewRequest("GET", "/api/google/conectar", nil))
	if rec.Code != http.StatusFound {
		t.Fatalf("conectar: %d", rec.Code)
	}
	u, _ := url.Parse(rec.Header().Get("Location"))
	q := u.Query()
	if q.Get("code_challenge_method") != "S256" || q.Get("access_type") != "offline" || q.Get("redirect_uri") != "http://127.0.0.1:8765/" || !strings.Contains(q.Get("scope"), "auth/calendar") {
		t.Fatalf("parámetros de la autorización: %v", q)
	}
	// Un estado desconocido no sirve.
	rec = httptest.NewRecorder()
	handleGoogleVuelta(rec, httptest.NewRequest("GET", "/?state=otro&code=x", nil))
	if b, _ := io.ReadAll(rec.Body); !strings.Contains(string(b), "caducado") {
		t.Fatal("un estado desconocido debería rechazarse")
	}
	_ = dir
}

func TestCorreoDeIDToken(t *testing.T) {
	// cabecera.{"email":"ana@gmail.com"}.firma
	tok := "eyJhbGciOiJSUzI1NiJ9.eyJlbWFpbCI6ImFuYUBnbWFpbC5jb20ifQ.x"
	if c := correoDeIDToken(tok); c != "ana@gmail.com" {
		t.Fatalf("correo: %q", c)
	}
	if correoDeIDToken("basura") != "" {
		t.Fatal("un token mal formado no da correo")
	}
}

func TestHoraYDuracionCita(t *testing.T) {
	for s, ok := range map[string]bool{"09:00": true, "23:59": true, "9:00": false, "24:00": false, "12:60": false, "": false} {
		if horaValida(s) != ok {
			t.Errorf("horaValida(%q) = %v", s, !ok)
		}
	}
	for n, esp := range map[int]int{0: 45, -3: 45, 3: 5, 50: 50, 999: 720} {
		if duracionCita(n) != esp {
			t.Errorf("duracionCita(%d) = %d", n, duracionCita(n))
		}
	}
	if diasCita("") != "1234567" || diasCita("42") != "24" {
		t.Error("diasCita")
	}
}

func TestGoogleColor(t *testing.T) {
	g, _ := prepararGoogleFalso(t)
	manana := time.Now().AddDate(0, 0, 1).Format("2006-01-02")
	d := nuevosDatos(Cita{ID: "c1", PatientID: "p1", Fecha: manana, Hora: "09:00", Duracion: 30, Color: "11"})
	sinColor := d.firma(Cita{ID: "c1", PatientID: "p1", Fecha: manana, Hora: "09:00", Duracion: 30})
	pasar(t, d)
	if e := g.eventos[d.mapa["c1"].EventID]; e.ColorID == nil || *e.ColorID != "11" {
		t.Fatalf("el evento debería llevar el color 11: %+v", e.ColorID)
	}
	c := d.citas["c1"]
	c.Color = ""
	d.citas["c1"] = c
	if d.firma(c) != sinColor {
		t.Fatal("sin color, la firma no debe cambiar respecto a la de antes de existir los colores")
	}
	if res := pasar(t, d); res.Subidas != 1 || g.eventos[d.mapa["c1"].EventID].ColorID != nil {
		t.Fatalf("quitar el color debe actualizar el evento y dejarlo sin color")
	}
	b, _ := json.Marshal(d.eventoDe(c))
	if !strings.Contains(string(b), `"colorId":null`) {
		t.Fatalf("sin color se envía colorId null (para quitar el que tuviera en Google): %s", b)
	}
	if colorValido("12") != "" || colorValido("05") != "" || colorValido("7") != "7" {
		t.Fatal("colorValido")
	}
}
