// Sincronización de la agenda con Google Calendar (desde la 0.0.5).
//
// Conexión: OAuth 2.0 para aplicaciones de escritorio. El usuario crea una vez un «ID de cliente» (tipo «App de
// escritorio») en Google Cloud y lo pega en Ajustes › Agenda; después pulsa «Conectar con Google», inicia sesión en
// su navegador y Google vuelve a http://127.0.0.1:8765/ con un código que se cambia por un «refresh token». El ID de
// cliente y el token se guardan en google.json, junto a config.json (no en la carpeta de datos ni en las copias).
//
// Qué se sincroniza (en los dos sentidos):
//   - Las citas de la aplicación se copian como eventos en un calendario propio («Fisioterapia · citas») que la
//     aplicación crea en la cuenta: altas, cambios y anulaciones. Cada carpeta de datos tiene su calendario.
//   - Si en Google se mueve o se borra uno de esos eventos, la cita cambia también en la aplicación (si no se había
//     cambiado a la vez en la aplicación; en ese caso gana la aplicación).
//   - De los demás calendarios elegidos (por defecto, el principal) se traen solo los huecos ocupados, sin títulos,
//     para no dar citas encima.
//
// La página pide la sincronización (POST /api/google/sincronizar) al abrirse, cada pocos minutos y tras cambiar
// citas. El servidor no cambia las citas por su cuenta: devuelve los cambios hechos en Google y la página los aplica
// y los guarda como cualquier otro cambio (así no hay conflictos con la ventana abierta).
package main

import (
	"bytes"
	"crypto/rand"
	"crypto/sha256"
	"database/sql"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"html"
	"io"
	"log"
	"net/http"
	"net/url"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"
	"sync"
	"time"
)

// Direcciones de Google (variables para poder probar con un servidor falso).
var (
	googleAuthURL    = "https://accounts.google.com/o/oauth2/v2/auth"
	googleTokenURL   = "https://oauth2.googleapis.com/token"
	googleRevokeURL  = "https://oauth2.googleapis.com/revoke"
	googleAPI        = "https://www.googleapis.com/calendar/v3"
	googleHTTP       = &http.Client{Timeout: 30 * time.Second}
	googleRedirect   = "http://" + addr + "/"
	googleConfigPath = func() string { return filepath.Join(filepath.Dir(configPath()), "google.json") }
)

const (
	googleScope     = "openid email https://www.googleapis.com/auth/calendar"
	googleNombreCal = "Fisioterapia · sesiones"
	googleDescCal   = "Sesiones de la aplicación Fisioterapia. Se actualiza solo."
	// googleNombreViejo es el nombre que tenía el calendario hasta la 0.0.5, cuando las sesiones se llamaban citas.
	googleNombreViejo = "Fisioterapia · citas"
	googleMaxCambios  = 120 // altas, cambios y bajas por llamada (si hay más, la página vuelve a llamar)
	googleDiasAtras   = 30  // las citas más antiguas que esto no se suben (sí se actualizan las ya subidas)
	googleOcupadoDias = 90  // hasta cuándo se traen los huecos ocupados de los otros calendarios
)

type googleConfig struct {
	ClientID     string `json:"clientId"`
	ClientSecret string `json:"clientSecret"`
	RefreshToken string `json:"refreshToken,omitempty"`
	Cuenta       string `json:"cuenta,omitempty"`
}

// Hueco ocupado en otro calendario de Google, en hora local («2026-10-27T17:00»).
type ocupado struct {
	Inicio string `json:"inicio"`
	Fin    string `json:"fin"`
}

// Cambio hecho en Google que la página tiene que aplicar a una cita.
type cambioGoogle struct {
	CitaID   string `json:"citaId"`
	Accion   string `json:"accion"` // «mover» o «anular»
	Fecha    string `json:"fecha,omitempty"`
	Hora     string `json:"hora,omitempty"`
	Duracion int    `json:"duracion,omitempty"`
}

type resultadoSync struct {
	Cambios    []cambioGoogle `json:"cambios"`
	Ocupados   []ocupado      `json:"ocupados"`
	Subidas    int            `json:"subidas"`
	Borradas   int            `json:"borradas"`
	Pendientes int            `json:"pendientes"`
	Hora       time.Time      `json:"hora"`
}

type ultimoSync struct {
	Hora     time.Time
	Error    string
	Ocupados []ocupado
}

type oauthPendiente struct {
	verificador string
	caduca      time.Time
}

var (
	gMu      sync.Mutex // protege google.json, los estados OAuth pendientes y gUltimo
	gEstados = map[string]oauthPendiente{}
	gUltimo  = map[string]*ultimoSync{} // por carpeta de datos

	tokMu   sync.Mutex // token de acceso en memoria
	gAcceso string
	gCaduca time.Time

	gSyncMu sync.Mutex // una sola sincronización a la vez

	errNoConectado = errors.New("la aplicación no está conectada con Google")
	errCaducada    = errors.New("Google ha cerrado la conexión (se ha retirado el permiso o ha caducado): vuelve a conectar en Ajustes › Agenda")
)

// ---------- configuración (google.json) ----------

func leerGoogleConfig() googleConfig {
	var c googleConfig
	if b, err := os.ReadFile(googleConfigPath()); err == nil {
		json.Unmarshal(b, &c)
	}
	return c
}

func guardarGoogleConfig(c googleConfig) error {
	p := googleConfigPath()
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	b, _ := json.MarshalIndent(c, "", "  ")
	return os.WriteFile(p, b, 0o600)
}

func olvidarAcceso() {
	tokMu.Lock()
	gAcceso, gCaduca = "", time.Time{}
	tokMu.Unlock()
}

// googleKV lee un valor de la tabla google_sync de la carpeta activa. Debe llamarse con mu bloqueado.
func googleKV(clave string) string {
	var v string
	if db == nil || db.QueryRow(`SELECT valor FROM google_sync WHERE clave = ?`, clave).Scan(&v) != nil {
		return ""
	}
	return v
}

// setGoogleKV guarda un valor en google_sync. Debe llamarse con mu bloqueado.
func setGoogleKV(clave, valor string) error {
	_, err := db.Exec(`INSERT OR REPLACE INTO google_sync (clave, valor) VALUES (?, ?)`, clave, valor)
	return err
}

func ultimoDe(dir string) *ultimoSync {
	gMu.Lock()
	defer gMu.Unlock()
	u := gUltimo[dir]
	if u == nil {
		u = &ultimoSync{}
		gUltimo[dir] = u
	}
	return u
}

// ---------- OAuth ----------

func aleatorio(n int) string {
	b := make([]byte, n)
	rand.Read(b)
	return base64.RawURLEncoding.EncodeToString(b)
}

type respuestaToken struct {
	AccessToken  string `json:"access_token"`
	ExpiresIn    int    `json:"expires_in"`
	RefreshToken string `json:"refresh_token"`
	IDToken      string `json:"id_token"`
	Scope        string `json:"scope"`
	Error        string `json:"error"`
	Descripcion  string `json:"error_description"`
}

func pedirToken(form url.Values) (respuestaToken, error) {
	var t respuestaToken
	resp, err := googleHTTP.PostForm(googleTokenURL, form)
	if err != nil {
		return t, fmt.Errorf("no se puede contactar con Google (¿hay conexión a internet?): %w", err)
	}
	defer resp.Body.Close()
	b, _ := io.ReadAll(io.LimitReader(resp.Body, 1<<20))
	json.Unmarshal(b, &t)
	if resp.StatusCode != http.StatusOK || t.AccessToken == "" {
		if t.Error == "invalid_grant" {
			return t, errCaducada
		}
		if t.Error == "invalid_client" || t.Error == "unauthorized_client" {
			return t, fmt.Errorf("Google no reconoce el ID de cliente o el secreto: revísalos en Ajustes › Agenda")
		}
		return t, fmt.Errorf("Google ha rechazado la conexión (%s %s)", t.Error, t.Descripcion)
	}
	return t, nil
}

// tokenAcceso devuelve un token de acceso válido, renovándolo con el refresh token si hace falta.
func tokenAcceso() (string, error) {
	tokMu.Lock()
	defer tokMu.Unlock()
	if gAcceso != "" && time.Until(gCaduca) > time.Minute {
		return gAcceso, nil
	}
	gMu.Lock()
	c := leerGoogleConfig()
	gMu.Unlock()
	if c.RefreshToken == "" || c.ClientID == "" {
		return "", errNoConectado
	}
	t, err := pedirToken(url.Values{
		"client_id": {c.ClientID}, "client_secret": {c.ClientSecret},
		"refresh_token": {c.RefreshToken}, "grant_type": {"refresh_token"},
	})
	if err != nil {
		if err == errCaducada {
			gMu.Lock()
			c := leerGoogleConfig()
			c.RefreshToken = ""
			guardarGoogleConfig(c)
			gMu.Unlock()
		}
		return "", err
	}
	gAcceso, gCaduca = t.AccessToken, time.Now().Add(time.Duration(t.ExpiresIn)*time.Second)
	return gAcceso, nil
}

// correoDeIDToken saca el correo de la cuenta del id_token (llega directamente de Google por HTTPS).
func correoDeIDToken(tok string) string {
	partes := strings.Split(tok, ".")
	if len(partes) < 2 {
		return ""
	}
	b, err := base64.RawURLEncoding.DecodeString(strings.TrimRight(partes[1], "="))
	if err != nil {
		return ""
	}
	var c struct {
		Email string `json:"email"`
	}
	json.Unmarshal(b, &c)
	return c.Email
}

// handleGoogleConectar lleva al navegador a la página de Google para dar permiso.
func handleGoogleConectar(w http.ResponseWriter, r *http.Request) {
	gMu.Lock()
	c := leerGoogleConfig()
	if c.ClientID == "" || c.ClientSecret == "" {
		gMu.Unlock()
		paginaGoogle(w, false, "Falta el ID de cliente", "Antes de conectar, pega el ID de cliente y el secreto de Google en Ajustes › Agenda.")
		return
	}
	estado, verif := aleatorio(24), aleatorio(48)
	for k, v := range gEstados {
		if time.Now().After(v.caduca) {
			delete(gEstados, k)
		}
	}
	gEstados[estado] = oauthPendiente{verificador: verif, caduca: time.Now().Add(15 * time.Minute)}
	gMu.Unlock()
	reto := sha256.Sum256([]byte(verif))
	q := url.Values{
		"client_id": {c.ClientID}, "redirect_uri": {googleRedirect}, "response_type": {"code"},
		"scope": {googleScope}, "access_type": {"offline"}, "prompt": {"consent"}, "state": {estado},
		"code_challenge": {base64.RawURLEncoding.EncodeToString(reto[:])}, "code_challenge_method": {"S256"},
		"include_granted_scopes": {"true"},
	}
	http.Redirect(w, r, googleAuthURL+"?"+q.Encode(), http.StatusFound)
}

// handleGoogleVuelta recibe la vuelta de Google (http://127.0.0.1:8765/?state=…&code=…) y guarda el permiso.
func handleGoogleVuelta(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	gMu.Lock()
	p, ok := gEstados[q.Get("state")]
	delete(gEstados, q.Get("state"))
	c := leerGoogleConfig()
	gMu.Unlock()
	if !ok || time.Now().After(p.caduca) {
		paginaGoogle(w, false, "La conexión ha caducado", "Vuelve a la aplicación y pulsa otra vez «Conectar con Google».")
		return
	}
	if e := q.Get("error"); e != "" {
		paginaGoogle(w, false, "No se ha conectado", "No se ha dado permiso en Google ("+e+"). Si quieres conectar, vuelve a la aplicación y pulsa otra vez «Conectar con Google».")
		return
	}
	t, err := pedirToken(url.Values{
		"client_id": {c.ClientID}, "client_secret": {c.ClientSecret}, "code": {q.Get("code")},
		"code_verifier": {p.verificador}, "redirect_uri": {googleRedirect}, "grant_type": {"authorization_code"},
	})
	if err != nil {
		paginaGoogle(w, false, "No se ha podido conectar", err.Error())
		return
	}
	if !strings.Contains(t.Scope, "auth/calendar") {
		paginaGoogle(w, false, "Falta el permiso del calendario", "En la pantalla de Google hay que marcar la casilla que permite ver y editar los calendarios. Vuelve a la aplicación y pulsa otra vez «Conectar con Google».")
		return
	}
	if t.RefreshToken == "" {
		paginaGoogle(w, false, "No se ha podido conectar", "Google no ha dado un permiso duradero. Vuelve a la aplicación y pulsa otra vez «Conectar con Google».")
		return
	}
	gMu.Lock()
	c = leerGoogleConfig()
	c.RefreshToken, c.Cuenta = t.RefreshToken, correoDeIDToken(t.IDToken)
	err = guardarGoogleConfig(c)
	gMu.Unlock()
	if err != nil {
		paginaGoogle(w, false, "No se ha podido guardar la conexión", err.Error())
		return
	}
	tokMu.Lock()
	gAcceso, gCaduca = t.AccessToken, time.Now().Add(time.Duration(t.ExpiresIn)*time.Second)
	tokMu.Unlock()
	// Al conectar, la agenda de la carpeta de datos abierta empieza a sincronizarse.
	mu.Lock()
	setGoogleKV("activo", "1")
	mu.Unlock()
	cuenta := ""
	if c.Cuenta != "" {
		cuenta = " como " + c.Cuenta
	}
	paginaGoogle(w, true, "Conectado con Google", "La aplicación ya está conectada con Google Calendar"+cuenta+". Ya puedes cerrar esta pestaña y volver a la aplicación.")
}

// paginaGoogle muestra una página sencilla con el resultado de la conexión.
func paginaGoogle(w http.ResponseWriter, ok bool, titulo, texto string) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	color := "#B5533C"
	if ok {
		color = "#2E6F5E"
	}
	fmt.Fprintf(w, `<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s</title></head>
<body style="font:17px/1.5 system-ui,sans-serif;max-width:560px;margin:12vh auto;padding:0 20px;color:#222;background:#fff">
<h1 style="font:600 26px Georgia,serif;color:%s">%s</h1><p>%s</p>
<p><a href="/#/ajustes" style="color:#2E6F5E;font-weight:600">Volver a la aplicación</a></p></body></html>`,
		html.EscapeString(titulo), color, html.EscapeString(titulo), html.EscapeString(texto))
}

// ---------- endpoints de configuración ----------

func handleGoogleEstado(w http.ResponseWriter, r *http.Request) {
	gMu.Lock()
	c := leerGoogleConfig()
	gMu.Unlock()
	mu.Lock()
	activo, cal, dir := googleKV("activo") == "1", googleKV("calendario"), dataDir
	mu.Unlock()
	u := ultimoDe(dir)
	gMu.Lock()
	out := map[string]any{
		"configurado": c.ClientID != "" && c.ClientSecret != "",
		"clientId":    c.ClientID,
		"conectado":   c.RefreshToken != "",
		"cuenta":      c.Cuenta,
		"activo":      activo,
		"calendario":  cal != "",
		"ultima":      nil,
		"error":       u.Error,
		"ocupados":    u.Ocupados,
	}
	if !u.Hora.IsZero() {
		out["ultima"] = u.Hora
	}
	if u.Ocupados == nil {
		out["ocupados"] = []ocupado{}
	}
	gMu.Unlock()
	writeJSON(w, out)
}

// handleGoogleCredenciales guarda el ID de cliente y el secreto (pegados o leídos del JSON que descarga Google).
func handleGoogleCredenciales(w http.ResponseWriter, r *http.Request) {
	var body struct {
		ClientID     string `json:"clientId"`
		ClientSecret string `json:"clientSecret"`
	}
	if err := json.NewDecoder(io.LimitReader(r.Body, 1<<16)).Decode(&body); err != nil {
		httpErr(w, err, http.StatusBadRequest)
		return
	}
	id, secreto := strings.TrimSpace(body.ClientID), strings.TrimSpace(body.ClientSecret)
	if !strings.HasSuffix(id, ".apps.googleusercontent.com") || strings.ContainsAny(id, " /") {
		httpErr(w, fmt.Errorf("el ID de cliente no parece correcto: termina en «.apps.googleusercontent.com»"), http.StatusBadRequest)
		return
	}
	if secreto == "" || strings.ContainsAny(secreto, " /") {
		httpErr(w, fmt.Errorf("falta el secreto del cliente"), http.StatusBadRequest)
		return
	}
	gMu.Lock()
	c := leerGoogleConfig()
	if c.ClientID != id || c.ClientSecret != secreto {
		c = googleConfig{ClientID: id, ClientSecret: secreto} // otro cliente: hay que volver a conectar
		olvidarAcceso()
	}
	err := guardarGoogleConfig(c)
	gMu.Unlock()
	if err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]bool{"ok": true})
}

func handleGoogleActivar(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Activo bool `json:"activo"`
	}
	if err := json.NewDecoder(io.LimitReader(r.Body, 1<<12)).Decode(&body); err != nil {
		httpErr(w, err, http.StatusBadRequest)
		return
	}
	mu.Lock()
	err := setGoogleKV("activo", map[bool]string{true: "1", false: "0"}[body.Activo])
	mu.Unlock()
	if err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]bool{"ok": true})
}

// handleGoogleDesconectar retira el permiso en Google (si se puede) y lo olvida. Los eventos ya creados se quedan.
func handleGoogleDesconectar(w http.ResponseWriter, r *http.Request) {
	gMu.Lock()
	c := leerGoogleConfig()
	token := c.RefreshToken
	c.RefreshToken, c.Cuenta = "", ""
	err := guardarGoogleConfig(c)
	gMu.Unlock()
	olvidarAcceso()
	if token != "" {
		if resp, e := googleHTTP.PostForm(googleRevokeURL, url.Values{"token": {token}}); e == nil {
			resp.Body.Close()
		}
	}
	mu.Lock()
	setGoogleKV("activo", "0")
	mu.Unlock()
	if err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]bool{"ok": true})
}

// ---------- API de Google Calendar ----------

type errorGoogle struct {
	Estado  int
	Mensaje string
}

func (e *errorGoogle) Error() string {
	return fmt.Sprintf("Google Calendar ha respondido con un error (%d): %s", e.Estado, e.Mensaje)
}

func estadoGoogle(err error) int {
	var e *errorGoogle
	if errors.As(err, &e) {
		return e.Estado
	}
	return 0
}

// llamarGoogle hace una petición a la API de Calendar con el token de acceso (y lo renueva una vez si caduca).
func llamarGoogle(metodo, ruta string, cuerpo, salida any) error {
	for intento := 0; intento < 2; intento++ {
		tok, err := tokenAcceso()
		if err != nil {
			return err
		}
		var rd io.Reader
		if cuerpo != nil {
			b, _ := json.Marshal(cuerpo)
			rd = bytes.NewReader(b)
		}
		req, err := http.NewRequest(metodo, googleAPI+ruta, rd)
		if err != nil {
			return err
		}
		req.Header.Set("Authorization", "Bearer "+tok)
		if cuerpo != nil {
			req.Header.Set("Content-Type", "application/json")
		}
		resp, err := googleHTTP.Do(req)
		if err != nil {
			return fmt.Errorf("no se puede contactar con Google (¿hay conexión a internet?): %w", err)
		}
		b, _ := io.ReadAll(io.LimitReader(resp.Body, 20<<20))
		resp.Body.Close()
		if resp.StatusCode == http.StatusUnauthorized && intento == 0 {
			olvidarAcceso()
			continue
		}
		if resp.StatusCode >= 300 {
			var e struct {
				Error struct {
					Message string `json:"message"`
				} `json:"error"`
			}
			json.Unmarshal(b, &e)
			return &errorGoogle{resp.StatusCode, e.Error.Message}
		}
		if salida != nil && len(b) > 0 {
			return json.Unmarshal(b, salida)
		}
		return nil
	}
	return errCaducada
}

type horaEvento struct {
	DateTime string `json:"dateTime,omitempty"`
	Date     string `json:"date,omitempty"`
	TimeZone string `json:"timeZone,omitempty"`
}

type eventoGoogle struct {
	ID          string     `json:"id,omitempty"`
	Status      string     `json:"status,omitempty"`
	Summary     string     `json:"summary"`
	ColorID     *string    `json:"colorId"` // null = color del calendario (en un PATCH, quita el color que tuviera)
	Description string     `json:"description"`
	Start       horaEvento `json:"start"`
	End         horaEvento `json:"end"`
	Extended    *struct {
		Private map[string]string `json:"private"`
	} `json:"extendedProperties,omitempty"`
}

func (e eventoGoogle) citaID() string {
	if e.Extended == nil {
		return ""
	}
	return e.Extended.Private["citaId"]
}

// remotoDe resume la hora de un evento como «2026-10-27T17:00|45» (inicio en hora local y minutos).
func remotoDe(e eventoGoogle) (fecha, hora string, dur int, ok bool) {
	ini, err1 := time.Parse(time.RFC3339, e.Start.DateTime)
	fin, err2 := time.Parse(time.RFC3339, e.End.DateTime)
	if err1 != nil || err2 != nil || !fin.After(ini) {
		return "", "", 0, false
	}
	ini = ini.In(time.Local)
	return ini.Format("2006-01-02"), ini.Format("15:04"), int(fin.Sub(ini).Minutes()), true
}

func claveRemota(fecha, hora string, dur int) string {
	return fecha + "T" + hora + "|" + strconv.Itoa(dur)
}

// ---------- sincronización ----------

type mapeoGoogle struct {
	EventID, Firma, Remoto string
}

type datosSync struct {
	dir        string
	citas      map[string]Cita
	orden      []string // ids de las citas por fecha y hora
	nombres    map[string][2]string
	titulo     string
	calendario string
	ultimoPull string
	ocupadosEn []string
	mapa       map[string]mapeoGoogle
}

func leerDatosSync() (*datosSync, error) {
	d := &datosSync{dir: dataDir, citas: map[string]Cita{}, nombres: map[string][2]string{}, mapa: map[string]mapeoGoogle{}}
	if googleKV("activo") != "1" {
		return nil, fmt.Errorf("la sincronización con Google no está activada en esta carpeta de datos")
	}
	err := eachRow(`SELECT id, patient_id, fecha, hora, duracion, nota, color FROM citas ORDER BY fecha, hora`, func(r *sql.Rows) error {
		var c Cita
		if err := r.Scan(&c.ID, &c.PatientID, &c.Fecha, &c.Hora, &c.Duracion, &c.Nota, &c.Color); err != nil {
			return err
		}
		d.citas[c.ID] = c
		d.orden = append(d.orden, c.ID)
		return nil
	})
	if err != nil {
		return nil, err
	}
	err = eachRow(`SELECT id, nombre, apellidos FROM patients`, func(r *sql.Rows) error {
		var id, n, a string
		if err := r.Scan(&id, &n, &a); err != nil {
			return err
		}
		d.nombres[id] = [2]string{n, a}
		return nil
	})
	if err != nil {
		return nil, err
	}
	err = eachRow(`SELECT cita_id, event_id, firma, remoto FROM google_eventos`, func(r *sql.Rows) error {
		var id string
		var m mapeoGoogle
		if err := r.Scan(&id, &m.EventID, &m.Firma, &m.Remoto); err != nil {
			return err
		}
		d.mapa[id] = m
		return nil
	})
	if err != nil {
		return nil, err
	}
	d.titulo = ajusteGlobal("googleTitulo", "nombre")
	d.calendario = googleKV("calendario")
	d.ultimoPull = googleKV("ultimoPull")
	json.Unmarshal([]byte(googleKV("ocupadosCalendarios")), &d.ocupadosEn)
	if d.ocupadosEn == nil {
		d.ocupadosEn = []string{"primary"}
	}
	return d, nil
}

// eventoDe prepara el evento de Google de una cita. Lo que se ve en Google depende del ajuste googleTitulo:
// «nombre» (nombre y apellidos, y la nota), «iniciales» o «cita» (solo «Sesión»).
func (d *datosSync) eventoDe(c Cita) eventoGoogle {
	n := d.nombres[c.PatientID]
	titulo, desc := "Sesión", ""
	switch d.titulo {
	case "iniciales":
		ini := ""
		for _, s := range []string{n[0], n[1]} {
			if r := []rune(strings.TrimSpace(s)); len(r) > 0 {
				ini += strings.ToUpper(string(r[0])) + ". "
			}
		}
		if ini != "" {
			titulo = "Sesión " + strings.TrimSpace(ini)
		}
	case "cita":
	default:
		titulo = strings.TrimSpace(n[0] + " " + n[1])
		desc = strings.TrimSpace(c.Nota)
	}
	if desc != "" {
		desc += "\n\n"
	}
	desc += "Sesión de la aplicación Fisioterapia. Si la cambias aquí de día u hora, o la borras, también cambia en la aplicación."
	ini, _ := time.ParseInLocation("2006-01-02 15:04", c.Fecha+" "+c.Hora, time.Local)
	fin := ini.Add(time.Duration(duracionCita(c.Duracion)) * time.Minute)
	var color *string
	if col := colorValido(c.Color); col != "" {
		color = &col
	}
	e := eventoGoogle{Summary: titulo, Description: desc, ColorID: color,
		Start: horaEvento{DateTime: ini.Format(time.RFC3339)}, End: horaEvento{DateTime: fin.Format(time.RFC3339)}}
	e.Extended = &struct {
		Private map[string]string `json:"private"`
	}{map[string]string{"citaId": c.ID, "app": "fisioterapia"}}
	return e
}

// firma resume lo que se ve de una cita en Google: si cambia, hay que actualizar el evento.
func (d *datosSync) firma(c Cita) string {
	e := d.eventoDe(c)
	texto := strings.Join([]string{e.Summary, e.Description, e.Start.DateTime, e.End.DateTime}, "\x00")
	if e.ColorID != nil {
		texto += "\x00color:" + *e.ColorID // sin color, la firma es la misma que antes de existir los colores
	}
	h := sha256.Sum256([]byte(texto))
	return hex.EncodeToString(h[:8])
}

// sincronizarGoogle hace una pasada completa (ver el comentario del principio del archivo).
func sincronizarGoogle() (*resultadoSync, error) {
	mu.Lock()
	d, err := leerDatosSync()
	mu.Unlock()
	if err != nil {
		return nil, err
	}
	res := &resultadoSync{Cambios: []cambioGoogle{}, Ocupados: []ocupado{}, Hora: time.Now()}
	inicio := time.Now()
	errSync := d.pasada(res)
	// Lo hecho se guarda aunque la pasada se haya quedado a medias (para no duplicar eventos la próxima vez).
	mu.Lock()
	if dataDir == d.dir {
		if e := d.guardar(errSync == nil, inicio); e != nil && errSync == nil {
			errSync = e
		}
	} else if errSync == nil {
		errSync = fmt.Errorf("se ha cambiado de carpeta de datos durante la sincronización")
	}
	mu.Unlock()
	u := ultimoDe(d.dir)
	gMu.Lock()
	if errSync != nil {
		u.Error = errSync.Error()
	} else {
		u.Error, u.Hora, u.Ocupados = "", res.Hora, res.Ocupados
	}
	gMu.Unlock()
	if errSync != nil {
		return nil, errSync
	}
	return res, nil
}

// guardar escribe el mapa de eventos y el estado. Debe llamarse con mu bloqueado.
func (d *datosSync) guardar(completa bool, inicio time.Time) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if _, err := tx.Exec(`DELETE FROM google_eventos`); err != nil {
		return err
	}
	for id, m := range d.mapa {
		if _, err := tx.Exec(`INSERT INTO google_eventos (cita_id, event_id, firma, remoto) VALUES (?, ?, ?, ?)`, id, m.EventID, m.Firma, m.Remoto); err != nil {
			return err
		}
	}
	kv := map[string]string{"calendario": d.calendario}
	if completa {
		// La próxima vez se piden los cambios desde un poco antes de empezar esta pasada.
		kv["ultimoPull"] = inicio.Add(-2 * time.Minute).UTC().Format(time.RFC3339)
	}
	for k, v := range kv {
		if _, err := tx.Exec(`INSERT OR REPLACE INTO google_sync (clave, valor) VALUES (?, ?)`, k, v); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func (d *datosSync) pasada(res *resultadoSync) error {
	// 1. El calendario de la aplicación: se crea la primera vez (o si se ha borrado en Google).
	if d.calendario != "" {
		var cal struct {
			Summary string `json:"summary"`
		}
		if err := llamarGoogle("GET", "/calendars/"+url.PathEscape(d.calendario), nil, &cal); err != nil {
			if s := estadoGoogle(err); s == http.StatusNotFound || s == http.StatusGone {
				d.calendario, d.ultimoPull, d.mapa = "", "", map[string]mapeoGoogle{}
			} else {
				return err
			}
		} else if cal.Summary == googleNombreViejo {
			// Las citas pasaron a llamarse sesiones: el calendario creado antes se renombra (si falla, en la próxima).
			if err := llamarGoogle("PATCH", "/calendars/"+url.PathEscape(d.calendario), map[string]string{"summary": googleNombreCal, "description": googleDescCal}, nil); err != nil {
				log.Println("Google Calendar: no se pudo renombrar el calendario:", err)
			}
		}
	}
	if d.calendario == "" {
		var prim struct {
			TimeZone string `json:"timeZone"`
		}
		if err := llamarGoogle("GET", "/calendars/primary", nil, &prim); err != nil {
			return err
		}
		var nuevo struct {
			ID string `json:"id"`
		}
		cuerpo := map[string]string{"summary": googleNombreCal, "description": googleDescCal, "timeZone": prim.TimeZone}
		if err := llamarGoogle("POST", "/calendars", cuerpo, &nuevo); err != nil {
			return err
		}
		d.calendario, d.ultimoPull, d.mapa = nuevo.ID, "", map[string]mapeoGoogle{}
	}
	base := "/calendars/" + url.PathEscape(d.calendario) + "/events"

	// 2. Cambios hechos en Google desde la última vez en los eventos de las citas.
	saltar := map[string]bool{}
	if d.ultimoPull != "" {
		token := ""
		for {
			q := url.Values{"showDeleted": {"true"}, "singleEvents": {"true"}, "maxResults": {"2500"},
				"updatedMin": {d.ultimoPull}, "privateExtendedProperty": {"app=fisioterapia"}}
			if token != "" {
				q.Set("pageToken", token)
			}
			var lista struct {
				Items         []eventoGoogle `json:"items"`
				NextPageToken string         `json:"nextPageToken"`
			}
			if err := llamarGoogle("GET", base+"?"+q.Encode(), nil, &lista); err != nil {
				return err
			}
			for _, e := range lista.Items {
				d.cambioRemoto(e, res, saltar)
			}
			if token = lista.NextPageToken; token == "" {
				break
			}
		}
	}

	// 3. Citas nuevas o cambiadas en la aplicación → Google.
	desde := time.Now().AddDate(0, 0, -googleDiasAtras).Format("2006-01-02")
	hechos := 0
	for _, id := range d.orden {
		c := d.citas[id]
		if saltar[id] {
			continue
		}
		m, tiene := d.mapa[id]
		f := d.firma(c)
		if tiene && m.Firma == f || !tiene && c.Fecha < desde {
			continue
		}
		if hechos >= googleMaxCambios {
			res.Pendientes++
			continue
		}
		hechos++
		ev := d.eventoDe(c)
		var resp eventoGoogle
		err := errNoConectado
		if tiene {
			err = llamarGoogle("PATCH", base+"/"+url.PathEscape(m.EventID), ev, &resp)
			if s := estadoGoogle(err); s == http.StatusNotFound || s == http.StatusGone {
				tiene = false
			}
		}
		if !tiene {
			err = llamarGoogle("POST", base, ev, &resp)
		}
		if err != nil {
			return err
		}
		fe, ho, du, _ := remotoDe(resp)
		d.mapa[id] = mapeoGoogle{EventID: resp.ID, Firma: f, Remoto: claveRemota(fe, ho, du)}
		res.Subidas++
	}
	// Citas borradas en la aplicación → se borran sus eventos.
	borrar := []string{}
	for id := range d.mapa {
		if _, existe := d.citas[id]; !existe {
			borrar = append(borrar, id)
		}
	}
	sort.Strings(borrar)
	for _, id := range borrar {
		if hechos >= googleMaxCambios {
			res.Pendientes++
			continue
		}
		hechos++
		err := llamarGoogle("DELETE", base+"/"+url.PathEscape(d.mapa[id].EventID), nil, nil)
		if s := estadoGoogle(err); err != nil && s != http.StatusNotFound && s != http.StatusGone {
			return err
		}
		delete(d.mapa, id)
		res.Borradas++
	}

	// 4. Huecos ocupados en los otros calendarios elegidos.
	cals := []map[string]string{}
	for _, c := range d.ocupadosEn {
		if c != "" && c != d.calendario {
			cals = append(cals, map[string]string{"id": c})
		}
	}
	if len(cals) > 0 {
		hoy := time.Now()
		ini := time.Date(hoy.Year(), hoy.Month(), hoy.Day(), 0, 0, 0, 0, time.Local).AddDate(0, 0, -7)
		fin := ini.AddDate(0, 0, 7+googleOcupadoDias)
		vistos := map[ocupado]bool{}
		// Por tramos de 30 días: así nunca se pasa del intervalo máximo que admite Google en una consulta.
		for t := ini; t.Before(fin); t = t.AddDate(0, 0, 30) {
			hasta := t.AddDate(0, 0, 30)
			if hasta.After(fin) {
				hasta = fin
			}
			var fb struct {
				Calendars map[string]struct {
					Busy []struct {
						Start string `json:"start"`
						End   string `json:"end"`
					} `json:"busy"`
				} `json:"calendars"`
			}
			cuerpo := map[string]any{"timeMin": t.Format(time.RFC3339), "timeMax": hasta.Format(time.RFC3339), "items": cals}
			if err := llamarGoogle("POST", "/freeBusy", cuerpo, &fb); err != nil {
				return err
			}
			for _, c := range fb.Calendars {
				for _, b := range c.Busy {
					t1, e1 := time.Parse(time.RFC3339, b.Start)
					t2, e2 := time.Parse(time.RFC3339, b.End)
					if e1 != nil || e2 != nil {
						continue
					}
					o := ocupado{t1.In(time.Local).Format("2006-01-02T15:04"), t2.In(time.Local).Format("2006-01-02T15:04")}
					if !vistos[o] {
						vistos[o] = true
						res.Ocupados = append(res.Ocupados, o)
					}
				}
			}
		}
		sort.Slice(res.Ocupados, func(i, j int) bool { return res.Ocupados[i].Inicio < res.Ocupados[j].Inicio })
	}
	return nil
}

// cambioRemoto procesa un evento de la aplicación que ha cambiado en Google.
func (d *datosSync) cambioRemoto(e eventoGoogle, res *resultadoSync, saltar map[string]bool) {
	id := e.citaID()
	m, ok := d.mapa[id]
	if !ok || m.EventID != e.ID {
		return
	}
	c, existe := d.citas[id]
	if !existe {
		return // se ha borrado en la aplicación: se borrará en Google
	}
	cambiadaAqui := d.firma(c) != m.Firma
	if e.Status == "cancelled" {
		delete(d.mapa, id)
		if !cambiadaAqui {
			res.Cambios = append(res.Cambios, cambioGoogle{CitaID: id, Accion: "anular"})
			saltar[id] = true
		}
		return // si se había cambiado aquí, se vuelve a crear
	}
	fe, ho, du, valido := remotoDe(e)
	if !valido || claveRemota(fe, ho, du) == m.Remoto || cambiadaAqui {
		return // sin cambios de hora, o gana la aplicación (se sube su versión)
	}
	c.Fecha, c.Hora, c.Duracion = fe, ho, du
	d.citas[id] = c
	d.mapa[id] = mapeoGoogle{EventID: m.EventID, Firma: d.firma(c), Remoto: claveRemota(fe, ho, du)}
	res.Cambios = append(res.Cambios, cambioGoogle{CitaID: id, Accion: "mover", Fecha: fe, Hora: ho, Duracion: du})
	saltar[id] = true
}

func handleGoogleSincronizar(w http.ResponseWriter, r *http.Request) {
	if !gSyncMu.TryLock() {
		httpErr(w, fmt.Errorf("ya se está sincronizando"), http.StatusConflict)
		return
	}
	defer gSyncMu.Unlock()
	res, err := sincronizarGoogle()
	if err != nil {
		httpErr(w, err, http.StatusBadGateway)
		return
	}
	writeJSON(w, res)
}

// handleGoogleCalendarios lista los calendarios de la cuenta (GET) para elegir de cuáles se traen los huecos
// ocupados, o guarda la elección (POST {"ids": [...]}).
func handleGoogleCalendarios(w http.ResponseWriter, r *http.Request) {
	if r.Method == http.MethodPost {
		var body struct {
			IDs []string `json:"ids"`
		}
		if err := json.NewDecoder(io.LimitReader(r.Body, 1<<16)).Decode(&body); err != nil {
			httpErr(w, err, http.StatusBadRequest)
			return
		}
		if body.IDs == nil {
			body.IDs = []string{}
		}
		b, _ := json.Marshal(body.IDs)
		mu.Lock()
		err := setGoogleKV("ocupadosCalendarios", string(b))
		mu.Unlock()
		if err != nil {
			httpErr(w, err, http.StatusInternalServerError)
			return
		}
		writeJSON(w, map[string]bool{"ok": true})
		return
	}
	mu.Lock()
	propio, elegidosJS := googleKV("calendario"), googleKV("ocupadosCalendarios")
	mu.Unlock()
	var elegidos []string
	if json.Unmarshal([]byte(elegidosJS), &elegidos) != nil {
		elegidos = []string{"primary"}
	}
	var lista struct {
		Items []struct {
			ID      string `json:"id"`
			Summary string `json:"summary"`
			Primary bool   `json:"primary"`
		} `json:"items"`
	}
	if err := llamarGoogle("GET", "/users/me/calendarList?maxResults=250", nil, &lista); err != nil {
		httpErr(w, err, http.StatusBadGateway)
		return
	}
	marcado := map[string]bool{}
	for _, id := range elegidos {
		marcado[id] = true
	}
	out := []map[string]any{}
	for _, c := range lista.Items {
		if c.ID == propio {
			continue
		}
		out = append(out, map[string]any{"id": c.ID, "nombre": c.Summary, "principal": c.Primary,
			"marcado": marcado[c.ID] || c.Primary && marcado["primary"]})
	}
	writeJSON(w, out)
}
