// Fisioterapia: servidor local con SQLite.
// Cada carpeta de datos es un "set" independiente: contiene fisioterapia.db, fotos/ y copias/.
// La carpeta activa se guarda en config.json dentro de la carpeta de configuración del usuario
// (macOS: ~/Library/Application Support/Fisioterapia; Windows: %AppData%\Fisioterapia).
// Funciona en macOS y en Windows (ver build.sh).
// Solo escucha en 127.0.0.1, así que no es accesible desde otros equipos.
package main

import (
	"bytes"
	"context"
	"crypto/sha256"
	"database/sql"
	_ "embed"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"runtime"
	"sort"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
	"unicode"

	"fisioterapia/docs"
	_ "modernc.org/sqlite"
)

// version se fija al compilar con: go build -ldflags "-X main.version=1.2.3"
var version = "dev"

const addr = "127.0.0.1:8765"

//go:embed index.html
var indexHTML []byte

// Historial de cambios (docs/CHANGELOG.md) y manual de usuario (docs/AYUDA.md),
// ambos en español: se muestran en Ajustes > Novedades y en la sección «Ayuda». Se incrustan desde el
// paquete docs (docs/embed.go): go:embed solo alcanza ficheros de la carpeta del paquete o inferiores.
var (
	changelogMD = docs.Changelog
	ayudaMD     = docs.Ayuda
)

// pdf-lib (MIT, ver docs/pdf-lib.LICENSE.md): librería de PDF que se ejecuta en el navegador, incluida
// en el binario para que funcione sin internet. La interfaz la carga solo al exportar.
//
//go:embed pdf-lib.min.js
var pdfLibJS []byte

// revision identifica la versión de los datos que ven las ventanas del navegador. Cambia con cada
// guardado, restauración o cambio de carpeta; si una ventana intenta guardar con una revisión vieja
// (porque hay otra ventana abierta que ya guardó), se rechaza para no pisar datos más nuevos.
// Se protege con mu.
var revision = time.Now().UnixNano()

func nuevaRevision() { revision++ }

// mu protege la base de datos y las rutas de la carpeta activa.
// Cada handler que las usa toma el bloqueo; los helpers no lo toman.
var (
	mu        sync.Mutex
	db        *sql.DB
	dataDir   string
	fotosDir  string
	copiasDir string
)

type Exercise struct {
	ID     string `json:"id"`
	Nombre string `json:"nombre"`
	// Libre marca un ejercicio escrito como texto libre en el plan en casa: no aparece en la biblioteca.
	Libre bool `json:"libre,omitempty"`
}

type Patient struct {
	ID            string `json:"id"`
	Nombre        string `json:"nombre"`
	Apellidos     string `json:"apellidos"`
	FechaAlta     string `json:"fechaAlta"`
	Telefono      string `json:"telefono"`
	Email         string `json:"email"`
	Observaciones string `json:"observaciones"`
	Foto          string `json:"foto"`
	// Archivado: paciente que ya no viene (se oculta de la lista, pero conserva todo su historial).
	Archivado bool `json:"archivado,omitempty"`
	// ColorCita: color por defecto de sus citas en la agenda (colorId de Google Calendar, "1"…"11"; vacío = el de la aplicación).
	ColorCita string `json:"colorCita,omitempty"`
}

type Pauta struct {
	ID         string  `json:"id"`
	PatientID  string  `json:"patientId"`
	ExerciseID string  `json:"exerciseId"`
	Desde      string  `json:"desde"`
	Hasta      *string `json:"hasta"`
	Asignacion string  `json:"asignacion"`
	// Dias: días de la semana en que toca la pauta, como dígitos 1 (lunes) a 7 (domingo), por ejemplo "14"
	// para lunes y jueves. Vacío = todos los días.
	Dias     string `json:"dias,omitempty"`
	BloqueID string `json:"bloqueId"`
	Orden    int    `json:"orden"`
	// Sesion: en qué sesiones del día toca (desde la 0.0.5). Vacío = en todas (también los días sin cita);
	// "s:<raíz de la serie>" = solo en las citas de esa serie; "c:<cita>" = solo en esa cita; "-" = solo en la
	// sesión sin cita (lo que se añade a mano en un día que también tiene citas).
	Sesion string `json:"sesion,omitempty"`
}

// Bloque agrupa ejercicios que se asignan juntos. Las puntuaciones siguen siendo de cada ejercicio.
type Bloque struct {
	ID         string   `json:"id"`
	Nombre     string   `json:"nombre"`
	Nivel      string   `json:"nivel"`
	Ejercicios []string `json:"ejercicios"`
}

// PlanItem es un ejercicio del plan de trabajo en casa de un paciente en un día concreto
// (independiente de las pautas de la clínica y de sus puntuaciones).
type PlanItem struct {
	ID         string `json:"id"`
	PatientID  string `json:"patientId"`
	Fecha      string `json:"fecha"`
	ExerciseID string `json:"exerciseId"`
	BloqueID   string `json:"bloqueId"`
	Orden      int    `json:"orden"`
	Nota       string `json:"nota"`      // indicaciones del ejercicio (repeticiones, cosas a tener en cuenta…)
	Grupo      string `json:"grupo"`     // identifica cada vez que se añade un bloque a un día (vacío: ejercicio suelto)
	NotaGrupo  string `json:"notaGrupo"` // indicaciones del bloque (se repite en todos los ejercicios del grupo)
}

// Plantilla es una semana tipo del plan en casa (de lunes a domingo, sin fechas) que se puede
// aplicar a cualquier paciente. Dia va de 1 (lunes de la primera semana) a 7*Semanas (domingo de la última).
type PlantillaItem struct {
	ID         string `json:"id"`
	Dia        int    `json:"dia"`
	ExerciseID string `json:"exerciseId"`
	BloqueID   string `json:"bloqueId"`
	Orden      int    `json:"orden"`
	Nota       string `json:"nota"`
	Grupo      string `json:"grupo"`
	NotaGrupo  string `json:"notaGrupo"`
}

// PlantillaAplicacion registra que una plantilla se aplicó a un paciente (el plan del paciente es una copia
// independiente: editar la plantilla después no lo modifica).
type PlantillaAplicacion struct {
	ID        string `json:"id"`
	PatientID string `json:"patientId"`
	Desde     string `json:"desde"`
	Hasta     string `json:"hasta"`
	Fecha     string `json:"fecha"` // día en que se aplicó
}

type Plantilla struct {
	ID      string `json:"id"`
	Nombre  string `json:"nombre"`
	Semanas int    `json:"semanas"` // duración sugerida al aplicarla
	Creada  string `json:"creada"`
	Notas   string `json:"notas"` // observaciones que se copian al plan del paciente
	// Duración propuesta al usarla (en días, semanas o meses). Semanas es la de la cuadrícula de lunes a domingo.
	Duracion int    `json:"duracion"`
	Unidad   string `json:"unidad"`
	// Ciclo = 1: Semanas es la longitud real de la plantilla (Dia llega hasta 7*Semanas). 0: plantilla anterior,
	// de una sola semana repetida; el frontend la convierte al abrir la aplicación.
	Ciclo        int                   `json:"ciclo"`
	Items        []PlantillaItem       `json:"items"`
	Aplicaciones []PlantillaAplicacion `json:"aplicaciones"`
}

// PlanCasaDoc es un plan en casa de un paciente (desde la 0.0.5): nombre, fechas, duración en semanas, notas y
// ejercicios. Los Items usan el mismo formato que las plantillas: Dia cuenta desde el lunes de la semana en que
// empieza el plan (1 = ese lunes) y Dia = 0 son los ejercicios «a elegir», sin día fijo. Fin se calcula
// (Inicio + 7·Semanas − 1) salvo que se haya cambiado a mano (FinManual); cambiarlo no altera la duración.
type PlanCasaDoc struct {
	ID          string          `json:"id"`
	PatientID   string          `json:"patientId"`
	Nombre      string          `json:"nombre"`
	Inicio      string          `json:"inicio"`
	Fin         string          `json:"fin"`
	FinManual   bool            `json:"finManual,omitempty"`
	Semanas     int             `json:"semanas"` // semanas de lunes a domingo que ocupa (se deduce de la duración)
	Duracion    int             `json:"duracion"`
	Unidad      string          `json:"unidad"` // «dias», «semanas» o «meses»
	Notas       string          `json:"notas"`
	Creado      string          `json:"creado"`
	PlantillaID string          `json:"plantillaId"` // plantilla con la que se creó (si la hay)
	Items       []PlantillaItem `json:"items"`
}

// PlanGuardado es una copia con nombre del plan en casa de un paciente (con sus fechas). Formato anterior a la
// 0.0.5: la página lo convierte en PlanCasaDoc al abrir la aplicación (igual que PlanCasa).
type PlanGuardadoItem struct {
	ID         string `json:"id"`
	Fecha      string `json:"fecha"`
	ExerciseID string `json:"exerciseId"`
	BloqueID   string `json:"bloqueId"`
	Orden      int    `json:"orden"`
	Nota       string `json:"nota"`
	Grupo      string `json:"grupo"`
	NotaGrupo  string `json:"notaGrupo"`
}

type PlanGuardado struct {
	ID          string             `json:"id"`
	PatientID   string             `json:"patientId"`
	Descripcion string             `json:"descripcion"`
	Creada      string             `json:"creada"`
	Items       []PlanGuardadoItem `json:"items"`
}

// Cita es una cita de un paciente en la agenda (desde la 0.0.5). Las de una serie semanal llevan SerieID y
// FechaSerie (el día que les tocaba según la serie, aunque luego se hayan movido); Modificada indica que se cambió
// solo esa cita, de modo que cambiar la serie no la toca.
type Cita struct {
	ID         string `json:"id"`
	PatientID  string `json:"patientId"`
	Fecha      string `json:"fecha"`
	Hora       string `json:"hora"`     // HH:MM
	Duracion   int    `json:"duracion"` // minutos
	Nota       string `json:"nota"`
	SerieID    string `json:"serieId"`
	FechaSerie string `json:"fechaSerie"`
	Modificada bool   `json:"modificada,omitempty"`
	Color      string `json:"color,omitempty"` // colorId de Google Calendar ("1"…"11"); vacío = el de la aplicación
}

// SerieCitas es una cita que se repite cada semana (los días de Dias, como en las pautas: "24" = martes y jueves)
// desde Desde hasta Hasta (vacío: sin fecha de fin). La página crea las citas de la serie; Excluidas son los días
// en que se anuló una cita de la serie, para no volver a crearla.
type SerieCitas struct {
	ID        string   `json:"id"`
	PatientID string   `json:"patientId"`
	Dias      string   `json:"dias"`
	Hora      string   `json:"hora"`
	Duracion  int      `json:"duracion"`
	Desde     string   `json:"desde"`
	Hasta     string   `json:"hasta"`
	Nota      string   `json:"nota"`
	Excluidas []string `json:"excluidas"`
	Creada    string   `json:"creada"`
	Color     string   `json:"color,omitempty"`
	// Raiz: la serie original. Al cambiar una serie «desde un día» se parte en dos, y las pautas ligadas a la serie
	// (Pauta.Sesion = "s:<raíz>") siguen valiendo para las dos partes.
	Raiz string `json:"raiz,omitempty"`
}

// Hito es una anotación fechada en la ficha de un paciente.
type Hito struct {
	ID        string   `json:"id"`
	PatientID string   `json:"patientId"`
	Fecha     string   `json:"fecha"`
	Nota      string   `json:"nota"`
	Fotos     []string `json:"fotos"`
}

// Evaluacion es una evaluación fechada en la ficha de un paciente.
type Evaluacion struct {
	ID         string   `json:"id"`
	PatientID  string   `json:"patientId"`
	Fecha      string   `json:"fecha"`
	Evaluacion string   `json:"evaluacion"`
	Fotos      []string `json:"fotos"`
}

// Observacion es texto libre que se anota al puntuar. Es de un paciente, un día y una sesión (Sesion: id de la cita;
// vacío = sin sesión) y, si se indica, de un bloque, un ejercicio y una repetición. Con BloqueID y ExerciseID vacíos
// y Repeticion 0 es una observación de toda la sesión; así caben las de sesión, bloque, ejercicio y repetición.
type Observacion struct {
	PatientID  string `json:"patientId"`
	Fecha      string `json:"fecha"`
	Sesion     string `json:"sesion"`
	BloqueID   string `json:"bloqueId"`
	ExerciseID string `json:"exerciseId"`
	Repeticion int    `json:"repeticion"`
	Texto      string `json:"texto"`
}

type State struct {
	Exercises       []Exercise        `json:"exercises"`
	Patients        []Patient         `json:"patients"`
	Pautas          []Pauta           `json:"pautas"`
	Puntuaciones    map[string]*int   `json:"puntuaciones"`
	Ajustes         map[string]string `json:"ajustes"`
	Bloques         []Bloque          `json:"bloques"`
	PlanCasa        []PlanItem        `json:"planCasa"`
	Hitos           []Hito            `json:"hitos"`
	Evaluaciones    []Evaluacion      `json:"evaluaciones"`
	Plantillas      []Plantilla       `json:"plantillas"`
	PlanesGuardados []PlanGuardado    `json:"planesGuardados"`
	Planes          []PlanCasaDoc     `json:"planes"`
	Informes        []Informe         `json:"informes"`
	Citas           []Cita            `json:"citas"`
	SeriesCitas     []SerieCitas      `json:"seriesCitas"`
	Observaciones   []Observacion     `json:"observaciones"`
	// OrdenSesiones: orden de los ejercicios de una sesión, si se ha cambiado en ella.
	// Clave «paciente|fecha|sesión» (sesión vacía = sin cita); valor: ids de ejercicio en orden.
	OrdenSesiones map[string][]string `json:"ordenSesiones"`
}

// Informe registra un PDF generado para un paciente (informe o plan en casa) y dónde lo guardó el usuario.
// El archivo vive fuera de la carpeta de datos: si se mueve o se borra, el registro queda como «no encontrado».
type Informe struct {
	ID          string `json:"id"`
	PatientID   string `json:"patientId"`
	Tipo        string `json:"tipo"` // «informe» o «plan»
	Nombre      string `json:"nombre"`
	Ruta        string `json:"ruta"`
	Fecha       string `json:"fecha"` // cuándo se generó (ISO)
	Desde       string `json:"desde"`
	Hasta       string `json:"hasta"`
	Descripcion string `json:"descripcion"`
}

type copiaInfo struct {
	Nombre string    `json:"nombre"`
	Fecha  time.Time `json:"fecha"`
	Auto   bool      `json:"auto"`
}

type config struct {
	DataDir string `json:"dataDir"`
}

func main() {
	override := flag.String("dir", "", "carpeta de datos para esta ejecución (no cambia la configuración guardada)")
	verVersion := flag.Bool("version", false, "muestra la versión y termina (lo usan los lanzadores)")
	flag.Parse()
	if *verVersion {
		fmt.Println(version)
		return
	}

	dir := ""
	if *override != "" {
		abs, err := filepath.Abs(*override)
		if err != nil {
			log.Fatal(err)
		}
		dir = abs
	} else if saved := readConfig(); saved != "" {
		dir = saved
	} else {
		dir = defaultDataDir()
	}

	mu.Lock()
	err := openDataDir(dir)
	mu.Unlock()
	if err != nil {
		log.Fatal("No se puede abrir la carpeta de datos ", dir, ": ", err)
	}

	mux := http.NewServeMux()
	mux.HandleFunc("GET /{$}", handleIndex)
	mux.HandleFunc("/api/state", handleState)
	mux.HandleFunc("POST /api/copia", handleCopia)
	mux.HandleFunc("GET /api/copias", handleListCopias)
	mux.HandleFunc("GET /api/copias-auto", handleEstadoAuto)
	mux.HandleFunc("GET /api/copiando", handleCopiando)
	mux.HandleFunc("POST /api/restaurar", handleRestaurar)
	mux.HandleFunc("/api/ajustes", handleAjustes)
	mux.HandleFunc("GET /api/changelog", handleChangelog)
	mux.HandleFunc("GET /api/ayuda", handleAyuda)
	mux.HandleFunc("POST /api/elegir-carpeta", handleElegirCarpeta)
	mux.HandleFunc("GET /fotos/{name}", handleFoto)
	mux.HandleFunc("POST /api/foto", handleSubirFoto)
	mux.HandleFunc("GET /pdf-lib.min.js", handlePdfLib)
	mux.HandleFunc("POST /api/exportar", handleExportar)
	mux.HandleFunc("POST /api/informes/abrir", handleAbrirInforme)
	mux.HandleFunc("GET /api/informes/existen", handleInformesExisten)
	mux.HandleFunc("POST /api/salir", handleSalir)
	registrarCalendarios(mux)

	ln, err := net.Listen("tcp", addr)
	if err != nil {
		ln = puertoOcupado(err)
		if ln == nil {
			return
		}
	}

	iniciarCopiasAutomaticas()

	url := "http://" + addr + "/"
	fmt.Println("Fisioterapia en marcha en", url)
	fmt.Println("Versión", version)
	fmt.Println("Datos en", dir)
	fmt.Println("Para cerrar la aplicación, usa «Salir» en el menú o cierra esta ventana.")
	go func() {
		time.Sleep(400 * time.Millisecond)
		abrirEnSistema(url)
	}()
	srv := &http.Server{Handler: soloLocal(mux)}
	go func() {
		<-salir
		time.Sleep(300 * time.Millisecond) // deja que la respuesta llegue al navegador
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		srv.Shutdown(ctx)
	}()
	if err := srv.Serve(ln); err != nil && err != http.ErrServerClosed {
		log.Fatal(err)
	}
	mu.Lock()
	if db != nil {
		db.Close()
	}
	mu.Unlock()
	fmt.Println()
	fmt.Println("La aplicación se ha cerrado. Ya puedes cerrar esta ventana.")
}

// salir recibe la orden de cerrar la aplicación (botón «Salir» de la interfaz).
var salir = make(chan struct{}, 1)

func handleSalir(w http.ResponseWriter, r *http.Request) {
	if copiando.Load() > 0 {
		httpErr(w, fmt.Errorf("se está haciendo una copia de seguridad: espera unos segundos y vuelve a intentarlo"), http.StatusConflict)
		return
	}
	writeJSON(w, map[string]bool{"ok": true})
	select {
	case salir <- struct{}{}:
	default:
	}
}

// puertoOcupado decide qué hacer si el puerto de la aplicación ya está en uso:
//   - si es esta misma versión de la aplicación, solo abre el navegador;
//   - si es otra versión (por ejemplo, la anterior seguía abierta tras actualizar), le pide que se cierre
//     y vuelve a intentarlo;
//   - si es otro programa, avisa con un mensaje claro.
//
// Devuelve el puerto ya abierto para seguir arrancando, o nil si hay que terminar.
func puertoOcupado(errOrig error) net.Listener {
	url := "http://" + addr
	cli := http.Client{Timeout: 2 * time.Second}
	if resp, err := cli.Get(url + "/api/changelog"); err == nil {
		var v struct {
			Version string `json:"version"`
		}
		ok := resp.StatusCode == http.StatusOK && json.NewDecoder(resp.Body).Decode(&v) == nil && v.Version != ""
		resp.Body.Close()
		if ok && v.Version == version {
			fmt.Println("Fisioterapia ya estaba en marcha: se abre en el navegador.")
			abrirEnSistema(url + "/")
			return nil
		}
		if ok {
			fmt.Printf("Hay otra versión de Fisioterapia abierta (%s): se cierra para abrir la %s…\n", v.Version, version)
			if r2, err := cli.Post(url+"/api/salir", "application/json", nil); err == nil {
				r2.Body.Close()
				for i := 0; i < 20; i++ {
					time.Sleep(300 * time.Millisecond)
					if ln, err := net.Listen("tcp", addr); err == nil {
						return ln
					}
				}
			}
			avisoPuerto(fmt.Sprintf("Sigue abierta otra versión de Fisioterapia (%s).\n\nCierra su ventana negra (o reinicia el ordenador) y vuelve a abrir la aplicación.", v.Version), errOrig)
			return nil
		}
	}
	avisoPuerto("No se puede iniciar Fisioterapia: otro programa está usando el puerto 8765 de este ordenador.\n\nReinicia el ordenador y vuelve a abrir la aplicación. Si sigue pasando, avisa a quien te la instaló.", errOrig)
	return nil
}

// avisoPuerto muestra el problema en la ventana negra y en un aviso del sistema, para que se vea aunque
// la ventana quede detrás.
func avisoPuerto(msg string, err error) {
	fmt.Println(msg)
	fmt.Println("(Detalle técnico:", err, ")")
	switch runtime.GOOS {
	case "darwin":
		exec.Command("osascript", "-e", "on run argv", "-e", `display dialog (item 1 of argv) buttons {"OK"} default button 1 with icon caution with title "Fisioterapia"`, "-e", "end run", msg).Run()
	case "windows":
		cmd := exec.Command("powershell", "-NoProfile", "-Command",
			`Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.MessageBox]::Show($env:FISIO_MSG, 'Fisioterapia') | Out-Null`)
		cmd.Env = append(os.Environ(), "FISIO_MSG="+msg)
		cmd.Run()
	}
}

// abrirEnSistema abre una URL o una carpeta con el programa predeterminado del sistema
// (navegador o explorador de archivos).
// mostrarEnCarpeta abre la carpeta que contiene el archivo (en macOS, además, lo deja seleccionado).
func mostrarEnCarpeta(archivo string) {
	if runtime.GOOS == "darwin" {
		exec.Command("open", "-R", archivo).Start()
		return
	}
	abrirEnSistema(filepath.Dir(archivo))
}

func abrirEnSistema(destino string) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		cmd = exec.Command("open", destino)
	case "windows":
		// explorer abre tanto carpetas como direcciones web (y devuelve siempre un código de error, que se ignora).
		cmd = exec.Command("explorer", destino)
	default:
		cmd = exec.Command("xdg-open", destino)
	}
	cmd.Start()
}

// soloLocal rechaza las peticiones que no vienen de la propia aplicación. Sin esto, cualquier página
// web abierta en el navegador podría enviar peticiones a 127.0.0.1:8765 (por ejemplo restaurar una
// copia o cambiar la carpeta de datos), y un ataque de "DNS rebinding" podría leer los datos.
func soloLocal(next http.Handler) http.Handler {
	validos := map[string]bool{addr: true, "localhost:8765": true}
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if !validos[r.Host] {
			http.Error(w, "host no permitido", http.StatusForbidden)
			return
		}
		if o := r.Header.Get("Origin"); o != "" && !validos[strings.TrimPrefix(o, "http://")] {
			http.Error(w, "origen no permitido", http.StatusForbidden)
			return
		}
		next.ServeHTTP(w, r)
	})
}

// ---------- configuración y carpetas ----------

func configPath() string {
	dir, err := os.UserConfigDir()
	if err != nil {
		home, _ := os.UserHomeDir()
		dir = filepath.Join(home, ".config")
	}
	return filepath.Join(dir, "Fisioterapia", "config.json")
}

func readConfig() string {
	b, err := os.ReadFile(configPath())
	if err != nil {
		return ""
	}
	var c config
	if json.Unmarshal(b, &c) != nil {
		return ""
	}
	return c.DataDir
}

func writeConfig(dir string) error {
	p := configPath()
	if err := os.MkdirAll(filepath.Dir(p), 0o755); err != nil {
		return err
	}
	b, _ := json.MarshalIndent(config{DataDir: dir}, "", "  ")
	return os.WriteFile(p, b, 0o644)
}

func defaultDataDir() string {
	home, _ := os.UserHomeDir()
	if runtime.GOOS == "windows" {
		// Fuera de «Documentos»: en Windows suele estar sincronizada con OneDrive, y una base de datos
		// SQLite en una carpeta sincronizada puede corromperse.
		return filepath.Join(home, "Fisioterapia")
	}
	return filepath.Join(home, "Documents", "Fisioterapia")
}

// openDataDir pasa a usar la carpeta indicada: la crea si no existe y abre su base de datos.
// Debe llamarse con mu bloqueado.
func openDataDir(dir string) error {
	if !filepath.IsAbs(dir) {
		return fmt.Errorf("la ruta debe ser absoluta")
	}
	// Si la carpeta padre no existe (por ejemplo, un disco externo desconectado),
	// no la creamos: así no se escriben datos en otro sitio sin avisar.
	if _, err := os.Stat(filepath.Dir(dir)); err != nil {
		return fmt.Errorf("la carpeta padre no existe (¿está conectado el disco?)")
	}
	fotos := filepath.Join(dir, "fotos")
	copias := filepath.Join(dir, "copias")
	for _, d := range []string{dir, fotos, copias} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			return err
		}
	}
	nueva, err := sql.Open("sqlite", filepath.Join(dir, "fisioterapia.db")+"?_pragma=foreign_keys(1)&_pragma=busy_timeout(5000)")
	if err != nil {
		return err
	}
	nueva.SetMaxOpenConns(1)
	if err := prepararBaseDeDatos(nueva, copias, fotos); err != nil {
		nueva.Close()
		return err
	}
	if db != nil {
		db.Close()
	}
	db = nueva
	dataDir = dir
	fotosDir = fotos
	copiasDir = copias
	return nil
}

// schemaVersion es la versión del modelo de datos que entiende este ejecutable. Se guarda en la propia base de
// datos (PRAGMA user_version). Súbela en 1 en cada versión que cambie el modelo (tablas, columnas o datos) y,
// si el cambio no es solo añadir cosas, añade el paso correspondiente en pasosMigracion.
const schemaVersion = 8 // 2: tabla informes (PDF generados) · 3: pautas.dias y patients.archivado · 4: planes en casa (planes, plan_items) y plantillas.notas · 5: agenda (citas, citas_series) y Google Calendar (google_eventos, google_sync) · 6: sesiones (puntuaciones.sesion en la clave, pautas.sesion, citas_series.raiz) · 7: observaciones (texto libre por sesión, bloque, ejercicio o repetición) · 8: orden_sesiones (orden de los ejercicios en cada sesión)

// pasosMigracion[v] convierte los datos de la versión v a la v+1, dentro de una transacción, después de que
// migrateDB haya añadido las tablas y columnas nuevas. Solo hacen falta para cambios que no sean aditivos
// (renombrar, partir o recalcular datos). Los cambios que solo añaden tablas o columnas ya los cubre migrateDB.
var pasosMigracion = map[int]func(tx *sql.Tx) error{}

func tablaExiste(d *sql.DB, nombre string) bool {
	var n int
	if err := d.QueryRow(`SELECT COUNT(*) FROM sqlite_master WHERE type = 'table' AND name = ?`, nombre).Scan(&n); err != nil {
		return false
	}
	return n > 0
}

// prepararBaseDeDatos deja la base de datos lista para esta versión del programa:
//   - si los datos son de una versión más reciente, se niega a abrirlos (guardar con un programa antiguo
//     borraría lo que no conoce);
//   - si hay que actualizar datos existentes, hace antes una copia completa que no se borra sola;
//   - añade lo que falte, aplica los pasos de migración y anota la versión.
func prepararBaseDeDatos(d *sql.DB, copias, fotos string) error {
	var uv int
	if err := d.QueryRow(`PRAGMA user_version`).Scan(&uv); err != nil {
		return err
	}
	if uv > schemaVersion {
		return fmt.Errorf("estos datos pertenecen a una versión más reciente de la aplicación (modelo %d; esta versión entiende hasta el %d). "+
			"Usa la última versión de la aplicación: abrirlos con esta podría borrar información", uv, schemaVersion)
	}
	if uv < schemaVersion && tablaExiste(d, "patients") {
		if _, err := crearCopiaDe(d, copias, fotos, "copia-previa-actualizacion-", time.Now()); err != nil {
			return fmt.Errorf("no se ha podido hacer la copia de seguridad previa a la actualización (los datos no se han tocado): %w", err)
		}
	}
	if err := migrateDB(d); err != nil {
		return err
	}
	for v := uv; v < schemaVersion; v++ {
		tx, err := d.Begin()
		if err != nil {
			return err
		}
		if paso := pasosMigracion[v]; paso != nil {
			if err := paso(tx); err != nil {
				tx.Rollback()
				return fmt.Errorf("migración del modelo %d al %d: %w", v, v+1, err)
			}
		}
		if _, err := tx.Exec(fmt.Sprintf(`PRAGMA user_version = %d`, v+1)); err != nil {
			tx.Rollback()
			return err
		}
		if err := tx.Commit(); err != nil {
			return err
		}
	}
	return nil
}

func migrateDB(d *sql.DB) error {
	stmts := []string{
		`CREATE TABLE IF NOT EXISTS exercises (
			id TEXT PRIMARY KEY,
			nombre TEXT NOT NULL)`,
		`CREATE TABLE IF NOT EXISTS patients (
			id TEXT PRIMARY KEY,
			nombre TEXT NOT NULL,
			apellidos TEXT NOT NULL DEFAULT '',
			fecha_alta TEXT NOT NULL DEFAULT '',
			telefono TEXT NOT NULL DEFAULT '',
			email TEXT NOT NULL DEFAULT '',
			observaciones TEXT NOT NULL DEFAULT '',
			foto_archivo TEXT)`,
		`CREATE TABLE IF NOT EXISTS pautas (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			desde TEXT NOT NULL,
			hasta TEXT)`,
		// Esquema actual: una fila por sesión y repetición. Una base de datos antigua se migra más abajo.
		// sesion = '' es la sesión sin cita; si no, el id de la cita (sin clave foránea: las citas se reescriben en
		// cada guardado; la página pasa a «sin cita» las puntuaciones de una cita que ya no existe).
		`CREATE TABLE IF NOT EXISTS puntuaciones (
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			sesion TEXT NOT NULL DEFAULT '',
			repeticion INTEGER NOT NULL DEFAULT 1,
			valor INTEGER CHECK (valor IS NULL OR valor BETWEEN 0 AND 3),
			PRIMARY KEY (patient_id, fecha, exercise_id, sesion, repeticion))`,
		// Observaciones al puntuar (modelo 7). bloque_id / exercise_id vacíos y repeticion 0 = de toda la sesión.
		// Sin claves foráneas en sesion, bloque_id ni exercise_id: pueden ir vacíos (y las citas se reescriben en cada guardado).
		`CREATE TABLE IF NOT EXISTS observaciones (
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			sesion TEXT NOT NULL DEFAULT '',
			bloque_id TEXT NOT NULL DEFAULT '',
			exercise_id TEXT NOT NULL DEFAULT '',
			repeticion INTEGER NOT NULL DEFAULT 0,
			texto TEXT NOT NULL,
			PRIMARY KEY (patient_id, fecha, sesion, bloque_id, exercise_id, repeticion))`,
		// Orden de los ejercicios en una sesión (modelo 8), cuando se cambia en ella; si no, se usa el de las pautas.
		// sesion = '' es la sesión sin cita; sin clave foránea (las citas se reescriben en cada guardado).
		`CREATE TABLE IF NOT EXISTS orden_sesiones (
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			sesion TEXT NOT NULL DEFAULT '',
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			posicion INTEGER NOT NULL,
			PRIMARY KEY (patient_id, fecha, sesion, exercise_id))`,
		`CREATE TABLE IF NOT EXISTS ajustes (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)`,
		`CREATE TABLE IF NOT EXISTS bloques (id TEXT PRIMARY KEY, nombre TEXT NOT NULL)`,
		`CREATE TABLE IF NOT EXISTS bloque_ejercicios (
			bloque_id TEXT NOT NULL REFERENCES bloques(id) ON DELETE CASCADE,
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			posicion INTEGER NOT NULL DEFAULT 0,
			PRIMARY KEY (bloque_id, exercise_id))`,
		`CREATE TABLE IF NOT EXISTS plan_casa (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			bloque_id TEXT NOT NULL DEFAULT '',
			orden INTEGER NOT NULL DEFAULT 0,
			nota TEXT NOT NULL DEFAULT '',
			grupo TEXT NOT NULL DEFAULT '',
			nota_grupo TEXT NOT NULL DEFAULT '',
			UNIQUE (patient_id, fecha, exercise_id))`,
		`CREATE TABLE IF NOT EXISTS plantillas (
			id TEXT PRIMARY KEY,
			nombre TEXT NOT NULL,
			semanas INTEGER NOT NULL DEFAULT 1,
			creada TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS plantilla_items (
			id TEXT PRIMARY KEY,
			plantilla_id TEXT NOT NULL REFERENCES plantillas(id) ON DELETE CASCADE,
			dia INTEGER NOT NULL,
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			bloque_id TEXT NOT NULL DEFAULT '',
			orden INTEGER NOT NULL DEFAULT 0,
			nota TEXT NOT NULL DEFAULT '',
			grupo TEXT NOT NULL DEFAULT '',
			nota_grupo TEXT NOT NULL DEFAULT '',
			UNIQUE (plantilla_id, dia, exercise_id))`,
		`CREATE TABLE IF NOT EXISTS informes (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			tipo TEXT NOT NULL DEFAULT '',
			nombre TEXT NOT NULL DEFAULT '',
			ruta TEXT NOT NULL DEFAULT '',
			fecha TEXT NOT NULL DEFAULT '',
			desde TEXT NOT NULL DEFAULT '',
			hasta TEXT NOT NULL DEFAULT '',
			descripcion TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS plantilla_aplicaciones (
			id TEXT PRIMARY KEY,
			plantilla_id TEXT NOT NULL REFERENCES plantillas(id) ON DELETE CASCADE,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			desde TEXT NOT NULL DEFAULT '',
			hasta TEXT NOT NULL DEFAULT '',
			fecha TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS planes_guardados (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			descripcion TEXT NOT NULL DEFAULT '',
			creada TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS planes_guardados_items (
			id TEXT PRIMARY KEY,
			plan_id TEXT NOT NULL REFERENCES planes_guardados(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			bloque_id TEXT NOT NULL DEFAULT '',
			orden INTEGER NOT NULL DEFAULT 0,
			nota TEXT NOT NULL DEFAULT '',
			grupo TEXT NOT NULL DEFAULT '',
			nota_grupo TEXT NOT NULL DEFAULT '',
			UNIQUE (plan_id, fecha, exercise_id))`,
		`CREATE TABLE IF NOT EXISTS planes (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			nombre TEXT NOT NULL DEFAULT '',
			inicio TEXT NOT NULL DEFAULT '',
			fin TEXT NOT NULL DEFAULT '',
			fin_manual INTEGER NOT NULL DEFAULT 0,
			semanas INTEGER NOT NULL DEFAULT 1,
			notas TEXT NOT NULL DEFAULT '',
			creado TEXT NOT NULL DEFAULT '',
			plantilla_id TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS plan_items (
			id TEXT PRIMARY KEY,
			plan_id TEXT NOT NULL REFERENCES planes(id) ON DELETE CASCADE,
			dia INTEGER NOT NULL,
			exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
			bloque_id TEXT NOT NULL DEFAULT '',
			orden INTEGER NOT NULL DEFAULT 0,
			nota TEXT NOT NULL DEFAULT '',
			grupo TEXT NOT NULL DEFAULT '',
			nota_grupo TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS citas_series (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			dias TEXT NOT NULL DEFAULT '',
			hora TEXT NOT NULL DEFAULT '',
			duracion INTEGER NOT NULL DEFAULT 45,
			desde TEXT NOT NULL DEFAULT '',
			hasta TEXT NOT NULL DEFAULT '',
			nota TEXT NOT NULL DEFAULT '',
			excluidas TEXT NOT NULL DEFAULT '[]',
			creada TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS citas (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			hora TEXT NOT NULL,
			duracion INTEGER NOT NULL DEFAULT 45,
			nota TEXT NOT NULL DEFAULT '',
			serie_id TEXT NOT NULL DEFAULT '',
			fecha_serie TEXT NOT NULL DEFAULT '',
			modificada INTEGER NOT NULL DEFAULT 0)`,
		// Sincronización con Google Calendar: qué evento de Google corresponde a cada cita y cómo estaba la última vez
		// que se sincronizó. Sin claves foráneas: saveState borra y vuelve a escribir las citas en cada guardado.
		`CREATE TABLE IF NOT EXISTS google_eventos (
			cita_id TEXT PRIMARY KEY,
			event_id TEXT NOT NULL,
			firma TEXT NOT NULL DEFAULT '',
			remoto TEXT NOT NULL DEFAULT '')`,
		`CREATE TABLE IF NOT EXISTS google_sync (clave TEXT PRIMARY KEY, valor TEXT NOT NULL)`,
		`CREATE TABLE IF NOT EXISTS hitos (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			nota TEXT NOT NULL DEFAULT '',
			fotos TEXT NOT NULL DEFAULT '[]')`,
		`CREATE TABLE IF NOT EXISTS evaluaciones (
			id TEXT PRIMARY KEY,
			patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
			fecha TEXT NOT NULL,
			evaluacion TEXT NOT NULL DEFAULT '',
			fotos TEXT NOT NULL DEFAULT '[]')`,
	}
	for _, s := range stmts {
		if _, err := d.Exec(s); err != nil {
			return err
		}
	}

	// Columnas añadidas después de la primera versión. Solo se añaden si faltan,
	// y cualquier otro error se devuelve en lugar de ignorarse.
	columnas := []struct{ tabla, col, def string }{
		{"pautas", "asignacion", "TEXT NOT NULL DEFAULT ''"},
		{"pautas", "dias", "TEXT NOT NULL DEFAULT ''"},
		{"patients", "archivado", "INTEGER NOT NULL DEFAULT 0"},
		{"pautas", "bloque_id", "TEXT NOT NULL DEFAULT ''"},
		{"pautas", "orden", "INTEGER NOT NULL DEFAULT 0"},
		{"bloques", "nivel", "TEXT NOT NULL DEFAULT ''"},
		{"bloque_ejercicios", "posicion", "INTEGER NOT NULL DEFAULT 0"},
		{"plan_casa", "nota", "TEXT NOT NULL DEFAULT ''"},
		{"plan_casa", "grupo", "TEXT NOT NULL DEFAULT ''"},
		{"plan_casa", "nota_grupo", "TEXT NOT NULL DEFAULT ''"},
		{"hitos", "fotos", "TEXT NOT NULL DEFAULT '[]'"},
		{"evaluaciones", "fotos", "TEXT NOT NULL DEFAULT '[]'"},
		{"exercises", "libre", "INTEGER NOT NULL DEFAULT 0"},
		{"plantillas", "ciclo", "INTEGER NOT NULL DEFAULT 0"},
		{"plantillas", "notas", "TEXT NOT NULL DEFAULT ''"},
		{"plantillas", "duracion", "INTEGER NOT NULL DEFAULT 0"},
		{"plantillas", "unidad", "TEXT NOT NULL DEFAULT ''"},
		{"planes", "duracion", "INTEGER NOT NULL DEFAULT 0"},
		{"planes", "unidad", "TEXT NOT NULL DEFAULT ''"},
		{"patients", "color_cita", "TEXT NOT NULL DEFAULT ''"},
		{"citas", "color", "TEXT NOT NULL DEFAULT ''"},
		{"citas_series", "color", "TEXT NOT NULL DEFAULT ''"},
		{"pautas", "sesion", "TEXT NOT NULL DEFAULT ''"},
		{"citas_series", "raiz", "TEXT NOT NULL DEFAULT ''"},
	}
	for _, c := range columnas {
		if tieneColumna(d, c.tabla, c.col) {
			continue
		}
		if _, err := d.Exec("ALTER TABLE " + c.tabla + " ADD COLUMN " + c.col + " " + c.def); err != nil {
			return fmt.Errorf("migración de %s.%s: %w", c.tabla, c.col, err)
		}
	}

	// Las filas anteriores a la columna "posicion" conservan su orden de inserción.
	if _, err := d.Exec(`UPDATE bloque_ejercicios SET posicion = rowid WHERE posicion = 0`); err != nil {
		return fmt.Errorf("migración de bloque_ejercicios.posicion: %w", err)
	}

	// Puntuaciones por repetición: la tabla antigua tenía una sola puntuación por ejercicio y día.
	// Todo va en una transacción: si algo falla, la base de datos queda como estaba.
	if !tieneColumna(d, "puntuaciones", "repeticion") {
		tx, err := d.Begin()
		if err != nil {
			return err
		}
		defer tx.Rollback()
		for _, s := range []string{
			`ALTER TABLE puntuaciones RENAME TO puntuaciones_antigua`,
			`CREATE TABLE puntuaciones (
				patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
				fecha TEXT NOT NULL,
				exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
				repeticion INTEGER NOT NULL DEFAULT 1,
				valor INTEGER CHECK (valor IS NULL OR valor BETWEEN 0 AND 3),
				PRIMARY KEY (patient_id, fecha, exercise_id, repeticion))`,
			`INSERT INTO puntuaciones (patient_id, fecha, exercise_id, repeticion, valor)
				SELECT patient_id, fecha, exercise_id, 1, valor FROM puntuaciones_antigua`,
			`DROP TABLE puntuaciones_antigua`,
		} {
			if _, err := tx.Exec(s); err != nil {
				return fmt.Errorf("migración de puntuaciones: %w", err)
			}
		}
		if err := tx.Commit(); err != nil {
			return err
		}
	}

	// Puntuaciones por sesión (modelo 6): la sesión entra en la clave primaria, así que hay que rehacer la tabla.
	// Las puntuaciones que ya había quedan en la sesión sin cita ('').
	if !tieneColumna(d, "puntuaciones", "sesion") {
		tx, err := d.Begin()
		if err != nil {
			return err
		}
		defer tx.Rollback()
		pasos := []string{
			`ALTER TABLE puntuaciones RENAME TO puntuaciones_sin_sesion`,
			`CREATE TABLE puntuaciones (
				patient_id TEXT NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
				fecha TEXT NOT NULL,
				exercise_id TEXT NOT NULL REFERENCES exercises(id) ON DELETE CASCADE,
				sesion TEXT NOT NULL DEFAULT '',
				repeticion INTEGER NOT NULL DEFAULT 1,
				valor INTEGER CHECK (valor IS NULL OR valor BETWEEN 0 AND 3),
				PRIMARY KEY (patient_id, fecha, exercise_id, sesion, repeticion))`,
			`INSERT INTO puntuaciones (patient_id, fecha, exercise_id, sesion, repeticion, valor)
				SELECT patient_id, fecha, exercise_id, '', repeticion, valor FROM puntuaciones_sin_sesion`,
			`DROP TABLE puntuaciones_sin_sesion`,
		}
		for _, q := range pasos {
			if _, err := tx.Exec(q); err != nil {
				return fmt.Errorf("migración de puntuaciones por sesión: %w", err)
			}
		}
		if err := tx.Commit(); err != nil {
			return err
		}
	}
	return nil
}

// tieneColumna indica si una tabla tiene una columna (para las migraciones).
func tieneColumna(d *sql.DB, tabla, col string) bool {
	var n int
	err := d.QueryRow(`SELECT COUNT(*) FROM pragma_table_info(?) WHERE name = ?`, tabla, col).Scan(&n)
	return err == nil && n > 0
}

// ---------- handlers ----------

func handleIndex(w http.ResponseWriter, r *http.Request) {
	// Vuelta de Google tras dar permiso al calendario (la dirección de vuelta de OAuth es la raíz).
	if r.URL.Query().Has("state") {
		handleGoogleVuelta(w, r)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	// Sustituye el marcador de versión por la versión de compilación.
	w.Write(bytes.ReplaceAll(indexHTML, []byte("__APP_VERSION__"), []byte(version)))
}

func handleChangelog(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	json.NewEncoder(w).Encode(map[string]string{"version": version, "texto": string(changelogMD)})
}

func handleAyuda(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/markdown; charset=utf-8")
	w.Header().Set("Cache-Control", "no-store")
	w.Write(ayudaMD)
}

func handleFoto(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	dir := fotosDir
	mu.Unlock()
	http.ServeFile(w, r, filepath.Join(dir, filepath.Base(r.PathValue("name"))))
}

func handleState(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	defer mu.Unlock()
	switch r.Method {
	case http.MethodGet:
		st, err := loadState()
		if err != nil {
			httpErr(w, err, http.StatusInternalServerError)
			return
		}
		w.Header().Set("X-Revision", strconv.FormatInt(revision, 10))
		writeJSON(w, st)
	case http.MethodPut:
		if h := r.Header.Get("X-Revision"); h != "" && h != strconv.FormatInt(revision, 10) {
			httpErr(w, fmt.Errorf("los datos han cambiado desde otra ventana"), http.StatusConflict)
			return
		}
		r.Body = http.MaxBytesReader(w, r.Body, 200<<20)
		var st State
		if err := json.NewDecoder(r.Body).Decode(&st); err != nil {
			httpErr(w, err, http.StatusBadRequest)
			return
		}
		if err := saveState(st); err != nil {
			httpErr(w, err, http.StatusInternalServerError)
			return
		}
		nuevaRevision()
		w.Header().Set("X-Revision", strconv.FormatInt(revision, 10))
		writeJSON(w, map[string]bool{"ok": true})
	default:
		http.Error(w, "método no permitido", http.StatusMethodNotAllowed)
	}
}

func handleCopia(w http.ResponseWriter, r *http.Request) {
	copiando.Add(1)
	defer copiando.Add(-1)
	mu.Lock()
	defer mu.Unlock()
	dest, err := createCopia()
	if err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]string{"path": dest})
}

func handleListCopias(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	defer mu.Unlock()
	entries, _ := os.ReadDir(copiasDir)
	list := []copiaInfo{}
	for _, e := range entries {
		if !e.IsDir() || !strings.HasPrefix(e.Name(), "copia-") {
			continue
		}
		info, err := e.Info()
		if err != nil {
			continue
		}
		list = append(list, copiaInfo{Nombre: e.Name(), Fecha: info.ModTime(), Auto: strings.HasPrefix(e.Name(), prefijoAuto)})
	}
	sort.Slice(list, func(i, j int) bool { return list[i].Nombre > list[j].Nombre })
	writeJSON(w, list)
}

func handleRestaurar(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	defer mu.Unlock()
	var body struct {
		Nombre string `json:"nombre"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		httpErr(w, err, http.StatusBadRequest)
		return
	}
	if body.Nombre != filepath.Base(body.Nombre) || !strings.HasPrefix(body.Nombre, "copia-") {
		httpErr(w, fmt.Errorf("nombre de copia no válido"), http.StatusBadRequest)
		return
	}
	origen := filepath.Join(copiasDir, body.Nombre)
	dbOrigen := filepath.Join(origen, "fisioterapia.db")
	if _, err := os.Stat(dbOrigen); err != nil {
		httpErr(w, fmt.Errorf("la copia no existe"), http.StatusNotFound)
		return
	}
	// Copia previa de los datos actuales, por si la restauración no es la deseada.
	if _, err := createCopia(); err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	if err := restoreFrom(dbOrigen); err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	entries, _ := os.ReadDir(filepath.Join(origen, "fotos"))
	for _, e := range entries {
		dst := filepath.Join(fotosDir, e.Name())
		if _, err := os.Stat(dst); err == nil {
			continue
		}
		if err := copyFile(filepath.Join(origen, "fotos", e.Name()), dst); err != nil {
			httpErr(w, err, http.StatusInternalServerError)
			return
		}
	}
	refs, err := photoRefs()
	if err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	cleanFotos(refs)
	nuevaRevision()
	writeJSON(w, map[string]bool{"ok": true})
}

// handleAjustes devuelve la carpeta activa (GET) o cambia a otra carpeta de datos (POST).
func handleAjustes(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	defer mu.Unlock()
	switch r.Method {
	case http.MethodGet:
		writeJSON(w, map[string]string{"dataDir": dataDir, "defaultDir": defaultDataDir()})
	case http.MethodPost:
		var body struct {
			DataDir string `json:"dataDir"`
		}
		if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
			httpErr(w, err, http.StatusBadRequest)
			return
		}
		dir := filepath.Clean(strings.TrimSpace(body.DataDir))
		if err := openDataDir(dir); err != nil {
			httpErr(w, err, http.StatusBadRequest)
			return
		}
		nuevaRevision()
		if err := writeConfig(dir); err != nil {
			httpErr(w, err, http.StatusInternalServerError)
			return
		}
		writeJSON(w, map[string]string{"dataDir": dir})
	default:
		http.Error(w, "método no permitido", http.StatusMethodNotAllowed)
	}
}

// handleElegirCarpeta abre el selector de carpetas del sistema (macOS o Windows) y devuelve la ruta elegida.
// Parámetros opcionales: titulo (texto del diálogo) e inicio (carpeta en la que empieza).
func handleElegirCarpeta(w http.ResponseWriter, r *http.Request) {
	titulo := r.URL.Query().Get("titulo")
	if titulo == "" {
		titulo = "Elige la carpeta de datos de Fisioterapia"
	}
	ruta, err := dialogoSistema("carpeta", titulo, "", carpetaExistente(r.URL.Query().Get("inicio")))
	if err != nil {
		httpErr(w, err, http.StatusConflict)
		return
	}
	writeJSON(w, map[string]string{"path": ruta})
}

// carpetaExistente devuelve la ruta si es una carpeta que existe; si no, "".
func carpetaExistente(p string) string {
	if p == "" {
		return ""
	}
	if fi, err := os.Stat(p); err == nil && fi.IsDir() {
		return p
	}
	return ""
}

// dialogoSistema muestra el diálogo nativo «Elegir carpeta» (modo «carpeta») o «Guardar como» (modo «guardar»)
// y devuelve la ruta elegida. Los textos se pasan como argumentos o variables de entorno, nunca dentro del
// código del script, para que ningún nombre pueda romperlo. Si el usuario cancela devuelve un error «cancelado».
func dialogoSistema(modo, titulo, nombre, inicio string) (string, error) {
	var cmd *exec.Cmd
	switch runtime.GOOS {
	case "darwin":
		var script string
		if modo == "guardar" {
			script = `on run argv
	activate
	if item 3 of argv is "" then
		set f to choose file name with prompt (item 1 of argv) default name (item 2 of argv)
	else
		set f to choose file name with prompt (item 1 of argv) default name (item 2 of argv) default location ((POSIX file (item 3 of argv)) as alias)
	end if
	return POSIX path of f
end run`
		} else {
			script = `on run argv
	activate
	if item 3 of argv is "" then
		set f to choose folder with prompt (item 1 of argv)
	else
		set f to choose folder with prompt (item 1 of argv) default location ((POSIX file (item 3 of argv)) as alias)
	end if
	return POSIX path of f
end run`
		}
		cmd = exec.Command("osascript", "-e", script, titulo, nombre, inicio)
	case "windows":
		comun := `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Add-Type -AssemblyName System.Windows.Forms; ` +
			`$o = New-Object System.Windows.Forms.Form -Property @{TopMost = $true}; `
		var ps string
		if modo == "guardar" {
			ps = comun + `$f = New-Object System.Windows.Forms.SaveFileDialog; $f.Title = $env:FISIO_TITULO; ` +
				`if ($env:FISIO_NOMBRE -like '*.json') { $f.Filter = 'JSON (*.json)|*.json'; $f.DefaultExt = 'json' } else { $f.Filter = 'PDF (*.pdf)|*.pdf'; $f.DefaultExt = 'pdf' }; ` +
				`$f.AddExtension = $true; $f.OverwritePrompt = $true; ` +
				`$f.FileName = $env:FISIO_NOMBRE; if ($env:FISIO_INICIO) { $f.InitialDirectory = $env:FISIO_INICIO }; ` +
				`if ($f.ShowDialog($o) -eq 'OK') { [Console]::Out.Write($f.FileName) } else { exit 1 }`
		} else {
			ps = comun + `$f = New-Object System.Windows.Forms.FolderBrowserDialog; $f.Description = $env:FISIO_TITULO; ` +
				`$f.ShowNewFolderButton = $true; if ($env:FISIO_INICIO) { $f.SelectedPath = $env:FISIO_INICIO }; ` +
				`if ($f.ShowDialog($o) -eq 'OK') { [Console]::Out.Write($f.SelectedPath) } else { exit 1 }`
		}
		cmd = exec.Command("powershell", "-NoProfile", "-STA", "-Command", ps)
		cmd.Env = append(os.Environ(), "FISIO_TITULO="+titulo, "FISIO_NOMBRE="+nombre, "FISIO_INICIO="+inicio)
	default:
		return "", fmt.Errorf("los diálogos del sistema solo están disponibles en macOS y Windows")
	}
	out, err := cmd.Output()
	ruta := strings.TrimSpace(string(out))
	if err != nil || ruta == "" {
		// Normalmente, el usuario ha cancelado el diálogo.
		return "", fmt.Errorf("cancelado")
	}
	return ruta, nil
}

// ---------- base de datos ----------

func eachRow(q string, fn func(*sql.Rows) error) error {
	rows, err := db.Query(q)
	if err != nil {
		return err
	}
	defer rows.Close()
	for rows.Next() {
		if err := fn(rows); err != nil {
			return err
		}
	}
	return rows.Err()
}

func loadState() (State, error) {
	st := State{
		Exercises:       []Exercise{},
		Patients:        []Patient{},
		Pautas:          []Pauta{},
		Puntuaciones:    map[string]*int{},
		Ajustes:         map[string]string{},
		Bloques:         []Bloque{},
		PlanCasa:        []PlanItem{},
		Hitos:           []Hito{},
		Evaluaciones:    []Evaluacion{},
		Plantillas:      []Plantilla{},
		PlanesGuardados: []PlanGuardado{},
		Planes:          []PlanCasaDoc{},
		Informes:        []Informe{},
		Citas:           []Cita{},
		SeriesCitas:     []SerieCitas{},
		Observaciones:   []Observacion{},
		OrdenSesiones:   map[string][]string{},
	}
	err := eachRow(`SELECT id, nombre, libre FROM exercises ORDER BY nombre COLLATE NOCASE`, func(r *sql.Rows) error {
		var e Exercise
		var libre int
		if err := r.Scan(&e.ID, &e.Nombre, &libre); err != nil {
			return err
		}
		e.Libre = libre != 0
		st.Exercises = append(st.Exercises, e)
		return nil
	})
	if err != nil {
		return st, err
	}

	err = eachRow(`SELECT id, nombre, apellidos, fecha_alta, telefono, email, observaciones, foto_archivo, archivado, color_cita FROM patients ORDER BY apellidos COLLATE NOCASE`, func(r *sql.Rows) error {
		var p Patient
		var foto sql.NullString
		var archivado int
		if err := r.Scan(&p.ID, &p.Nombre, &p.Apellidos, &p.FechaAlta, &p.Telefono, &p.Email, &p.Observaciones, &foto, &archivado, &p.ColorCita); err != nil {
			return err
		}
		p.Archivado = archivado != 0
		if foto.Valid && foto.String != "" {
			p.Foto = "/fotos/" + foto.String
		}
		st.Patients = append(st.Patients, p)
		return nil
	})
	if err != nil {
		return st, err
	}

	err = eachRow(`SELECT id, patient_id, exercise_id, desde, hasta, asignacion, bloque_id, orden, dias, sesion FROM pautas`, func(r *sql.Rows) error {
		var x Pauta
		var hasta sql.NullString
		if err := r.Scan(&x.ID, &x.PatientID, &x.ExerciseID, &x.Desde, &hasta, &x.Asignacion, &x.BloqueID, &x.Orden, &x.Dias, &x.Sesion); err != nil {
			return err
		}
		if hasta.Valid {
			h := hasta.String
			x.Hasta = &h
		}
		st.Pautas = append(st.Pautas, x)
		return nil
	})
	if err != nil {
		return st, err
	}

	err = eachRow(`SELECT patient_id, fecha, exercise_id, repeticion, valor, sesion FROM puntuaciones`, func(r *sql.Rows) error {
		var pid, fecha, eid, sesion string
		var rep int
		var valor sql.NullInt64
		if err := r.Scan(&pid, &fecha, &eid, &rep, &valor, &sesion); err != nil {
			return err
		}
		// Clave «paciente|fecha|ejercicio|repetición», más «|sesión» si es de una cita.
		clave := fmt.Sprintf("%s|%s|%s|%d", pid, fecha, eid, rep)
		if sesion != "" {
			clave += "|" + sesion
		}
		if valor.Valid {
			v := int(valor.Int64)
			st.Puntuaciones[clave] = &v
		} else {
			st.Puntuaciones[clave] = nil
		}
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT patient_id, fecha, sesion, bloque_id, exercise_id, repeticion, texto FROM observaciones ORDER BY patient_id, fecha, sesion`, func(r *sql.Rows) error {
		var o Observacion
		if err := r.Scan(&o.PatientID, &o.Fecha, &o.Sesion, &o.BloqueID, &o.ExerciseID, &o.Repeticion, &o.Texto); err != nil {
			return err
		}
		st.Observaciones = append(st.Observaciones, o)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT patient_id, fecha, sesion, exercise_id FROM orden_sesiones ORDER BY patient_id, fecha, sesion, posicion`, func(r *sql.Rows) error {
		var pid, fecha, sesion, eid string
		if err := r.Scan(&pid, &fecha, &sesion, &eid); err != nil {
			return err
		}
		k := pid + "|" + fecha + "|" + sesion
		st.OrdenSesiones[k] = append(st.OrdenSesiones[k], eid)
		return nil
	})
	if err != nil {
		return st, err
	}
	indice := map[string]int{}
	err = eachRow(`SELECT id, nombre, nivel FROM bloques ORDER BY nombre COLLATE NOCASE`, func(r *sql.Rows) error {
		var b Bloque
		if err := r.Scan(&b.ID, &b.Nombre, &b.Nivel); err != nil {
			return err
		}
		b.Ejercicios = []string{}
		indice[b.ID] = len(st.Bloques)
		st.Bloques = append(st.Bloques, b)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT bloque_id, exercise_id FROM bloque_ejercicios ORDER BY bloque_id, posicion, rowid`, func(r *sql.Rows) error {
		var bid, eid string
		if err := r.Scan(&bid, &eid); err != nil {
			return err
		}
		if i, ok := indice[bid]; ok {
			st.Bloques[i].Ejercicios = append(st.Bloques[i].Ejercicios, eid)
		}
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, patient_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo FROM plan_casa ORDER BY patient_id, fecha, orden`, func(r *sql.Rows) error {
		var x PlanItem
		if err := r.Scan(&x.ID, &x.PatientID, &x.Fecha, &x.ExerciseID, &x.BloqueID, &x.Orden, &x.Nota, &x.Grupo, &x.NotaGrupo); err != nil {
			return err
		}
		st.PlanCasa = append(st.PlanCasa, x)
		return nil
	})
	if err != nil {
		return st, err
	}
	planesG := map[string]int{}
	err = eachRow(`SELECT id, patient_id, descripcion, creada FROM planes_guardados ORDER BY rowid`, func(r *sql.Rows) error {
		var p PlanGuardado
		if err := r.Scan(&p.ID, &p.PatientID, &p.Descripcion, &p.Creada); err != nil {
			return err
		}
		p.Items = []PlanGuardadoItem{}
		planesG[p.ID] = len(st.PlanesGuardados)
		st.PlanesGuardados = append(st.PlanesGuardados, p)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, plan_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo FROM planes_guardados_items ORDER BY plan_id, fecha, orden`, func(r *sql.Rows) error {
		var x PlanGuardadoItem
		var pid string
		if err := r.Scan(&x.ID, &pid, &x.Fecha, &x.ExerciseID, &x.BloqueID, &x.Orden, &x.Nota, &x.Grupo, &x.NotaGrupo); err != nil {
			return err
		}
		if i, ok := planesG[pid]; ok {
			st.PlanesGuardados[i].Items = append(st.PlanesGuardados[i].Items, x)
		}
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, patient_id, fecha, nota, fotos FROM hitos ORDER BY patient_id, fecha, rowid`, func(r *sql.Rows) error {
		var h Hito
		var fotos string
		if err := r.Scan(&h.ID, &h.PatientID, &h.Fecha, &h.Nota, &fotos); err != nil {
			return err
		}
		h.Fotos = urlsFotos(fotos)
		st.Hitos = append(st.Hitos, h)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, patient_id, fecha, evaluacion, fotos FROM evaluaciones ORDER BY patient_id, fecha, rowid`, func(r *sql.Rows) error {
		var e Evaluacion
		var fotos string
		if err := r.Scan(&e.ID, &e.PatientID, &e.Fecha, &e.Evaluacion, &fotos); err != nil {
			return err
		}
		e.Fotos = urlsFotos(fotos)
		st.Evaluaciones = append(st.Evaluaciones, e)
		return nil
	})
	if err != nil {
		return st, err
	}
	plantillas := map[string]int{}
	err = eachRow(`SELECT id, nombre, semanas, creada, ciclo, notas, duracion, unidad FROM plantillas ORDER BY rowid`, func(r *sql.Rows) error {
		var p Plantilla
		if err := r.Scan(&p.ID, &p.Nombre, &p.Semanas, &p.Creada, &p.Ciclo, &p.Notas, &p.Duracion, &p.Unidad); err != nil {
			return err
		}
		p.Items = []PlantillaItem{}
		p.Aplicaciones = []PlantillaAplicacion{}
		plantillas[p.ID] = len(st.Plantillas)
		st.Plantillas = append(st.Plantillas, p)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, plantilla_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo FROM plantilla_items ORDER BY plantilla_id, dia, orden`, func(r *sql.Rows) error {
		var x PlantillaItem
		var pid string
		if err := r.Scan(&x.ID, &pid, &x.Dia, &x.ExerciseID, &x.BloqueID, &x.Orden, &x.Nota, &x.Grupo, &x.NotaGrupo); err != nil {
			return err
		}
		if i, ok := plantillas[pid]; ok {
			st.Plantillas[i].Items = append(st.Plantillas[i].Items, x)
		}
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, plantilla_id, patient_id, desde, hasta, fecha FROM plantilla_aplicaciones ORDER BY rowid`, func(r *sql.Rows) error {
		var x PlantillaAplicacion
		var pid string
		if err := r.Scan(&x.ID, &pid, &x.PatientID, &x.Desde, &x.Hasta, &x.Fecha); err != nil {
			return err
		}
		if i, ok := plantillas[pid]; ok {
			st.Plantillas[i].Aplicaciones = append(st.Plantillas[i].Aplicaciones, x)
		}
		return nil
	})
	if err != nil {
		return st, err
	}
	planes := map[string]int{}
	err = eachRow(`SELECT id, patient_id, nombre, inicio, fin, fin_manual, semanas, duracion, unidad, notas, creado, plantilla_id FROM planes ORDER BY inicio, rowid`, func(r *sql.Rows) error {
		var p PlanCasaDoc
		var manual int
		if err := r.Scan(&p.ID, &p.PatientID, &p.Nombre, &p.Inicio, &p.Fin, &manual, &p.Semanas, &p.Duracion, &p.Unidad, &p.Notas, &p.Creado, &p.PlantillaID); err != nil {
			return err
		}
		p.FinManual = manual != 0
		p.Items = []PlantillaItem{}
		planes[p.ID] = len(st.Planes)
		st.Planes = append(st.Planes, p)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, plan_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo FROM plan_items ORDER BY plan_id, dia, orden`, func(r *sql.Rows) error {
		var x PlantillaItem
		var pid string
		if err := r.Scan(&x.ID, &pid, &x.Dia, &x.ExerciseID, &x.BloqueID, &x.Orden, &x.Nota, &x.Grupo, &x.NotaGrupo); err != nil {
			return err
		}
		if i, ok := planes[pid]; ok {
			st.Planes[i].Items = append(st.Planes[i].Items, x)
		}
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, patient_id, tipo, nombre, ruta, fecha, desde, hasta, descripcion FROM informes ORDER BY fecha, rowid`, func(r *sql.Rows) error {
		var x Informe
		if err := r.Scan(&x.ID, &x.PatientID, &x.Tipo, &x.Nombre, &x.Ruta, &x.Fecha, &x.Desde, &x.Hasta, &x.Descripcion); err != nil {
			return err
		}
		st.Informes = append(st.Informes, x)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, patient_id, dias, hora, duracion, desde, hasta, nota, excluidas, creada, color, raiz FROM citas_series ORDER BY desde, rowid`, func(r *sql.Rows) error {
		var x SerieCitas
		var excl string
		if err := r.Scan(&x.ID, &x.PatientID, &x.Dias, &x.Hora, &x.Duracion, &x.Desde, &x.Hasta, &x.Nota, &excl, &x.Creada, &x.Color, &x.Raiz); err != nil {
			return err
		}
		x.Excluidas = nombresDeJSON(excl)
		if x.Excluidas == nil {
			x.Excluidas = []string{}
		}
		st.SeriesCitas = append(st.SeriesCitas, x)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT id, patient_id, fecha, hora, duracion, nota, serie_id, fecha_serie, modificada, color FROM citas ORDER BY fecha, hora, rowid`, func(r *sql.Rows) error {
		var x Cita
		var mod int
		if err := r.Scan(&x.ID, &x.PatientID, &x.Fecha, &x.Hora, &x.Duracion, &x.Nota, &x.SerieID, &x.FechaSerie, &mod, &x.Color); err != nil {
			return err
		}
		x.Modificada = mod != 0
		st.Citas = append(st.Citas, x)
		return nil
	})
	if err != nil {
		return st, err
	}
	err = eachRow(`SELECT clave, valor FROM ajustes`, func(r *sql.Rows) error {
		var k, v string
		if err := r.Scan(&k, &v); err != nil {
			return err
		}
		st.Ajustes[k] = v
		return nil
	})
	return st, err
}

// saveState sustituye todo el contenido de la base de datos por el estado recibido.
// Las fotos en data URL se guardan como ficheros con nombre basado en su hash,
// así que reenviar la misma foto no duplica nada.
func saveState(st State) error {
	fotoArchivo := map[string]string{}
	for _, p := range st.Patients {
		switch {
		case strings.HasPrefix(p.Foto, "data:image/"):
			i := strings.Index(p.Foto, ",")
			if i < 0 {
				continue
			}
			raw, err := base64.StdEncoding.DecodeString(p.Foto[i+1:])
			if err != nil {
				return fmt.Errorf("la foto de %s %s no es válida", p.Nombre, p.Apellidos)
			}
			sum := sha256.Sum256(raw)
			name := hex.EncodeToString(sum[:8]) + ".jpg"
			path := filepath.Join(fotosDir, name)
			if _, err := os.Stat(path); err != nil {
				if err := os.WriteFile(path, raw, 0o644); err != nil {
					return err
				}
			}
			fotoArchivo[p.ID] = name
		case strings.HasPrefix(p.Foto, "/fotos/"):
			fotoArchivo[p.ID] = filepath.Base(p.Foto)
		}
	}

	// Fotos de hitos y evaluaciones: son ficheros en fotos/ y la base guarda sus nombres (JSON).
	fotosHito := map[string]string{}
	for _, h := range st.Hitos {
		j, err := nombresFotos(h.Fotos, fotoArchivo, "h:"+h.ID)
		if err != nil {
			return err
		}
		fotosHito[h.ID] = j
	}
	fotosEval := map[string]string{}
	for _, e := range st.Evaluaciones {
		j, err := nombresFotos(e.Fotos, fotoArchivo, "e:"+e.ID)
		if err != nil {
			return err
		}
		fotosEval[e.ID] = j
	}

	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	for _, q := range []string{"DELETE FROM citas", "DELETE FROM citas_series", "DELETE FROM observaciones", "DELETE FROM orden_sesiones", "DELETE FROM puntuaciones", "DELETE FROM pautas", "DELETE FROM plan_casa", "DELETE FROM hitos", "DELETE FROM evaluaciones", "DELETE FROM planes_guardados_items", "DELETE FROM planes_guardados", "DELETE FROM plan_items", "DELETE FROM planes", "DELETE FROM plantilla_aplicaciones", "DELETE FROM plantilla_items", "DELETE FROM plantillas", "DELETE FROM bloque_ejercicios", "DELETE FROM bloques", "DELETE FROM informes", "DELETE FROM patients", "DELETE FROM exercises", "DELETE FROM ajustes"} {
		if _, err := tx.Exec(q); err != nil {
			return err
		}
	}

	exIDs := map[string]bool{}
	for _, e := range st.Exercises {
		if e.ID == "" || strings.TrimSpace(e.Nombre) == "" {
			continue
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO exercises (id, nombre, libre) VALUES (?, ?, ?)`, e.ID, e.Nombre, boolInt(e.Libre)); err != nil {
			return err
		}
		exIDs[e.ID] = true
	}

	for _, b := range st.Bloques {
		if b.ID == "" || strings.TrimSpace(b.Nombre) == "" {
			continue
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO bloques (id, nombre, nivel) VALUES (?, ?, ?)`, b.ID, b.Nombre, strings.TrimSpace(b.Nivel)); err != nil {
			return err
		}
		pos := 0
		for _, eid := range b.Ejercicios {
			if !exIDs[eid] {
				continue
			}
			pos++
			if _, err := tx.Exec(`INSERT OR IGNORE INTO bloque_ejercicios (bloque_id, exercise_id, posicion) VALUES (?, ?, ?)`, b.ID, eid, pos); err != nil {
				return err
			}
		}
	}

	patIDs := map[string]bool{}
	for _, p := range st.Patients {
		if p.ID == "" || strings.TrimSpace(p.Nombre) == "" {
			continue
		}
		var foto any
		if f, ok := fotoArchivo[p.ID]; ok {
			foto = f
		}
		_, err := tx.Exec(`INSERT OR IGNORE INTO patients
			(id, nombre, apellidos, fecha_alta, telefono, email, observaciones, foto_archivo, archivado, color_cita)
			VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			p.ID, p.Nombre, p.Apellidos, p.FechaAlta, p.Telefono, p.Email, p.Observaciones, foto, boolInt(p.Archivado), colorValido(p.ColorCita))
		if err != nil {
			return err
		}
		patIDs[p.ID] = true
	}

	for _, x := range st.Pautas {
		if !patIDs[x.PatientID] || !exIDs[x.ExerciseID] || x.Desde == "" {
			continue
		}
		var hasta any
		if x.Hasta != nil && *x.Hasta != "" {
			hasta = *x.Hasta
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO pautas (id, patient_id, exercise_id, desde, hasta, asignacion, bloque_id, orden, dias, sesion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			x.ID, x.PatientID, x.ExerciseID, x.Desde, hasta, x.Asignacion, x.BloqueID, x.Orden, diasValidos(x.Dias), sesionValida(x.Sesion)); err != nil {
			return err
		}
	}

	for _, x := range st.PlanCasa {
		if x.ID == "" || x.Fecha == "" || !patIDs[x.PatientID] || !exIDs[x.ExerciseID] {
			continue
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO plan_casa (id, patient_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			x.ID, x.PatientID, x.Fecha, x.ExerciseID, x.BloqueID, x.Orden, x.Nota, x.Grupo, x.NotaGrupo); err != nil {
			return err
		}
	}

	for _, h := range st.Hitos {
		if h.ID == "" || h.Fecha == "" || !patIDs[h.PatientID] {
			continue
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO hitos (id, patient_id, fecha, nota, fotos) VALUES (?, ?, ?, ?, ?)`,
			h.ID, h.PatientID, h.Fecha, h.Nota, fotosHito[h.ID]); err != nil {
			return err
		}
	}

	for _, e := range st.Evaluaciones {
		if e.ID == "" || e.Fecha == "" || !patIDs[e.PatientID] {
			continue
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO evaluaciones (id, patient_id, fecha, evaluacion, fotos) VALUES (?, ?, ?, ?, ?)`,
			e.ID, e.PatientID, e.Fecha, e.Evaluacion, fotosEval[e.ID]); err != nil {
			return err
		}
	}

	for _, x := range st.Informes {
		if x.ID == "" || x.Ruta == "" || !patIDs[x.PatientID] {
			continue
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO informes (id, patient_id, tipo, nombre, ruta, fecha, desde, hasta, descripcion) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			x.ID, x.PatientID, x.Tipo, x.Nombre, x.Ruta, x.Fecha, x.Desde, x.Hasta, x.Descripcion); err != nil {
			return err
		}
	}

	for _, p := range st.PlanesGuardados {
		if p.ID == "" || !patIDs[p.PatientID] {
			continue
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO planes_guardados (id, patient_id, descripcion, creada) VALUES (?, ?, ?, ?)`,
			p.ID, p.PatientID, p.Descripcion, p.Creada); err != nil {
			return err
		}
		for _, x := range p.Items {
			if x.ID == "" || x.Fecha == "" || !exIDs[x.ExerciseID] {
				continue
			}
			if _, err := tx.Exec(`INSERT OR IGNORE INTO planes_guardados_items (id, plan_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
				x.ID, p.ID, x.Fecha, x.ExerciseID, x.BloqueID, x.Orden, x.Nota, x.Grupo, x.NotaGrupo); err != nil {
				return err
			}
		}
	}

	for _, p := range st.Planes {
		if p.ID == "" || !patIDs[p.PatientID] || !fechaValida(p.Inicio) {
			continue
		}
		semanas := p.Semanas
		if semanas < 1 {
			semanas = 1
		}
		if semanas > 120 {
			semanas = 120
		}
		duracion, unidad := duracionValida(p.Duracion, p.Unidad, semanas)
		fin := p.Fin
		if !fechaValida(fin) || fin < p.Inicio {
			fin = p.Inicio
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO planes (id, patient_id, nombre, inicio, fin, fin_manual, semanas, duracion, unidad, notas, creado, plantilla_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			p.ID, p.PatientID, p.Nombre, p.Inicio, fin, boolInt(p.FinManual), semanas, duracion, unidad, p.Notas, p.Creado, p.PlantillaID); err != nil {
			return err
		}
		for _, x := range p.Items {
			if x.ID == "" || x.Dia < 0 || x.Dia > 7*122 || !exIDs[x.ExerciseID] {
				continue
			}
			if _, err := tx.Exec(`INSERT OR IGNORE INTO plan_items (id, plan_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
				x.ID, p.ID, x.Dia, x.ExerciseID, x.BloqueID, x.Orden, x.Nota, x.Grupo, x.NotaGrupo); err != nil {
				return err
			}
		}
	}

	series := map[string]bool{}
	for _, x := range st.SeriesCitas {
		if x.ID == "" || !patIDs[x.PatientID] || !fechaValida(x.Desde) || !horaValida(x.Hora) || !strings.ContainsAny(x.Dias, "1234567") {
			continue
		}
		hasta := x.Hasta
		if !fechaValida(hasta) || hasta < x.Desde {
			hasta = ""
		}
		excl := []string{}
		for _, f := range x.Excluidas {
			if fechaValida(f) {
				excl = append(excl, f)
			}
		}
		ej, _ := json.Marshal(excl)
		if _, err := tx.Exec(`INSERT OR IGNORE INTO citas_series (id, patient_id, dias, hora, duracion, desde, hasta, nota, excluidas, creada, color, raiz) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			x.ID, x.PatientID, diasCita(x.Dias), x.Hora, duracionCita(x.Duracion), x.Desde, hasta, x.Nota, string(ej), x.Creada, colorValido(x.Color), x.Raiz); err != nil {
			return err
		}
		series[x.ID] = true
	}
	for _, x := range st.Citas {
		if x.ID == "" || !patIDs[x.PatientID] || !fechaValida(x.Fecha) || !horaValida(x.Hora) {
			continue
		}
		serie, fechaSerie := x.SerieID, x.FechaSerie
		if !series[serie] || !fechaValida(fechaSerie) {
			serie, fechaSerie = "", ""
		}
		if _, err := tx.Exec(`INSERT OR IGNORE INTO citas (id, patient_id, fecha, hora, duracion, nota, serie_id, fecha_serie, modificada, color) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
			x.ID, x.PatientID, x.Fecha, x.Hora, duracionCita(x.Duracion), x.Nota, serie, fechaSerie, boolInt(x.Modificada), colorValido(x.Color)); err != nil {
			return err
		}
	}

	for _, p := range st.Plantillas {
		if p.ID == "" || strings.TrimSpace(p.Nombre) == "" {
			continue
		}
		semanas := p.Semanas
		if semanas < 1 {
			semanas = 1
		}
		duracion, unidad := duracionValida(p.Duracion, p.Unidad, semanas)
		if _, err := tx.Exec(`INSERT OR IGNORE INTO plantillas (id, nombre, semanas, creada, ciclo, notas, duracion, unidad) VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
			p.ID, p.Nombre, semanas, p.Creada, p.Ciclo, p.Notas, duracion, unidad); err != nil {
			return err
		}
		for _, x := range p.Items {
			if x.ID == "" || x.Dia < 0 || x.Dia > 7*52 || !exIDs[x.ExerciseID] { // Dia 0: «a elegir»
				continue
			}
			if _, err := tx.Exec(`INSERT OR IGNORE INTO plantilla_items (id, plantilla_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
				x.ID, p.ID, x.Dia, x.ExerciseID, x.BloqueID, x.Orden, x.Nota, x.Grupo, x.NotaGrupo); err != nil {
				return err
			}
		}
		for _, x := range p.Aplicaciones {
			if x.ID == "" || !patIDs[x.PatientID] {
				continue
			}
			if _, err := tx.Exec(`INSERT OR IGNORE INTO plantilla_aplicaciones (id, plantilla_id, patient_id, desde, hasta, fecha) VALUES (?, ?, ?, ?, ?, ?)`,
				x.ID, p.ID, x.PatientID, x.Desde, x.Hasta, x.Fecha); err != nil {
				return err
			}
		}
	}

	for k, v := range st.Puntuaciones {
		parts := strings.Split(k, "|")
		if len(parts) != 4 && len(parts) != 5 || !patIDs[parts[0]] || !exIDs[parts[2]] {
			continue
		}
		sesion := ""
		if len(parts) == 5 {
			sesion = parts[4]
		}
		rep, err := strconv.Atoi(parts[3])
		if err != nil || rep < 1 {
			continue
		}
		var valor any // nil = fila de repetición sin puntuar
		if v != nil {
			if *v < 0 || *v > 3 {
				continue
			}
			valor = *v
		}
		if _, err := tx.Exec(`INSERT OR REPLACE INTO puntuaciones (patient_id, fecha, exercise_id, sesion, repeticion, valor) VALUES (?, ?, ?, ?, ?, ?)`,
			parts[0], parts[1], parts[2], sesion, rep, valor); err != nil {
			return err
		}
	}

	// Observaciones: se descartan las vacías, las de pacientes o ejercicios que ya no existen y las de repetición sin ejercicio.
	for _, o := range st.Observaciones {
		if o.Fecha == "" || !patIDs[o.PatientID] || strings.TrimSpace(o.Texto) == "" || o.Repeticion < 0 ||
			(o.ExerciseID != "" && !exIDs[o.ExerciseID]) || (o.Repeticion > 0 && o.ExerciseID == "") {
			continue
		}
		if _, err := tx.Exec(`INSERT OR REPLACE INTO observaciones (patient_id, fecha, sesion, bloque_id, exercise_id, repeticion, texto) VALUES (?, ?, ?, ?, ?, ?, ?)`,
			o.PatientID, o.Fecha, o.Sesion, o.BloqueID, o.ExerciseID, o.Repeticion, o.Texto); err != nil {
			return err
		}
	}

	// Orden de cada sesión: se descartan las claves mal formadas y los pacientes o ejercicios que ya no existen.
	for k, eids := range st.OrdenSesiones {
		parts := strings.Split(k, "|")
		if len(parts) != 3 || parts[1] == "" || !patIDs[parts[0]] {
			continue
		}
		pos := 0
		for _, eid := range eids {
			if !exIDs[eid] {
				continue
			}
			pos++
			if _, err := tx.Exec(`INSERT OR IGNORE INTO orden_sesiones (patient_id, fecha, sesion, exercise_id, posicion) VALUES (?, ?, ?, ?, ?)`,
				parts[0], parts[1], parts[2], eid, pos); err != nil {
				return err
			}
		}
	}

	for k, v := range st.Ajustes {
		if _, err := tx.Exec(`INSERT OR REPLACE INTO ajustes (clave, valor) VALUES (?, ?)`, k, v); err != nil {
			return err
		}
	}
	if err := tx.Commit(); err != nil {
		return err
	}
	// Los datos ya están guardados: un fallo al limpiar fotos sobrantes no debe darlos por perdidos.
	if err := cleanFotos(fotoArchivo); err != nil {
		log.Println("No se pudieron limpiar las fotos sobrantes:", err)
	}
	return nil
}

// Fotos que han dejado de usarse y desde cuándo (ruta completa → primera vez que se vio sin usar). Una foto
// solo se borra cuando lleva un rato sin usarse, para que «Deshacer» en la página (por ejemplo, tras eliminar
// un paciente o un hito) la encuentre todavía. Al reiniciar la app se empieza a contar de nuevo.
var (
	fotosSinUso   = map[string]time.Time{}
	fotosSinUsoMu sync.Mutex
)

// esperaFotoSinUso es cuánto tiempo se conserva una foto que ya no usa nadie antes de borrarla.
const esperaFotoSinUso = 10 * time.Minute

// cleanFotos borra las fotos que ya no están asignadas a nadie (paciente, hito o evaluación) desde hace un rato.
func cleanFotos(usadas map[string]string) error {
	keep := map[string]bool{}
	for _, f := range usadas {
		keep[f] = true
	}
	entries, err := os.ReadDir(fotosDir)
	if err != nil {
		return err
	}
	fotosSinUsoMu.Lock()
	defer fotosSinUsoMu.Unlock()
	ahora := time.Now()
	for _, e := range entries {
		ruta := filepath.Join(fotosDir, e.Name())
		if keep[e.Name()] || !strings.HasSuffix(e.Name(), ".jpg") {
			delete(fotosSinUso, ruta)
			continue
		}
		// Una foto subida hace poco puede estar a la espera de que se guarde su entrada.
		if info, err := e.Info(); err == nil && ahora.Sub(info.ModTime()) < time.Hour {
			continue
		}
		desde, visto := fotosSinUso[ruta]
		if !visto {
			fotosSinUso[ruta] = ahora
			continue
		}
		if ahora.Sub(desde) < esperaFotoSinUso {
			continue
		}
		os.Remove(ruta)
		delete(fotosSinUso, ruta)
	}
	return nil
}

// photoRefs devuelve las fotos que usan los pacientes actuales.
func photoRefs() (map[string]string, error) {
	refs := map[string]string{}
	err := eachRow(`SELECT id, foto_archivo FROM patients WHERE foto_archivo IS NOT NULL`, func(r *sql.Rows) error {
		var id, f string
		if err := r.Scan(&id, &f); err != nil {
			return err
		}
		refs[id] = f
		return nil
	})
	if err != nil {
		return refs, err
	}
	for _, t := range []struct{ tabla, pre string }{{"hitos", "h:"}, {"evaluaciones", "e:"}} {
		err = eachRow(`SELECT id, fotos FROM `+t.tabla, func(r *sql.Rows) error {
			var id, js string
			if err := r.Scan(&id, &js); err != nil {
				return err
			}
			for i, n := range nombresDeJSON(js) {
				refs[fmt.Sprintf("%s%s#%d", t.pre, id, i)] = n
			}
			return nil
		})
		if err != nil {
			return refs, err
		}
	}
	return refs, nil
}

// nombresDeJSON lee la lista de nombres de fichero guardada en la base de datos.
func nombresDeJSON(js string) []string {
	var n []string
	json.Unmarshal([]byte(js), &n)
	return n
}

// urlsFotos convierte la lista de nombres guardada en las URL que usa la página.
func urlsFotos(js string) []string {
	out := []string{}
	for _, n := range nombresDeJSON(js) {
		out = append(out, "/fotos/"+filepath.Base(n))
	}
	return out
}

// nombresFotos prepara las fotos de una entrada: acepta URL «/fotos/…» ya guardadas (o, por
// compatibilidad, imágenes en data URL), apunta cada una en usadas y devuelve el JSON a guardar.
func nombresFotos(fotos []string, usadas map[string]string, prefijo string) (string, error) {
	nombres := []string{}
	for _, f := range fotos {
		var name string
		switch {
		case strings.HasPrefix(f, "data:image/"):
			i := strings.Index(f, ",")
			if i < 0 {
				continue
			}
			raw, err := base64.StdEncoding.DecodeString(f[i+1:])
			if err != nil {
				return "", fmt.Errorf("una foto no es válida")
			}
			if name, err = escribirFoto(raw); err != nil {
				return "", err
			}
		case strings.HasPrefix(f, "/fotos/"):
			name = filepath.Base(f)
			if !strings.HasSuffix(name, ".jpg") {
				continue
			}
			if _, err := os.Stat(filepath.Join(fotosDir, name)); err != nil {
				continue // la foto ya no existe
			}
		default:
			continue
		}
		usadas[fmt.Sprintf("%s#%d", prefijo, len(nombres))] = name
		nombres = append(nombres, name)
	}
	b, _ := json.Marshal(nombres)
	return string(b), nil
}

// escribirFoto guarda una imagen JPEG en fotos/ con un nombre basado en su contenido
// (la misma foto no se duplica) y devuelve el nombre del fichero.
func escribirFoto(raw []byte) (string, error) {
	sum := sha256.Sum256(raw)
	name := hex.EncodeToString(sum[:8]) + ".jpg"
	path := filepath.Join(fotosDir, name)
	if _, err := os.Stat(path); err != nil {
		if err := os.WriteFile(path, raw, 0o644); err != nil {
			return "", err
		}
	}
	return name, nil
}

// handleSubirFoto recibe una foto (JPEG, ya reducida por la página), la guarda y devuelve su URL.
// La entrada que la use la enlazará al guardarse; mientras tanto no se borra en la primera hora.
func handleSubirFoto(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 30<<20)
	raw, err := io.ReadAll(r.Body)
	if err != nil {
		httpErr(w, err, http.StatusBadRequest)
		return
	}
	if len(raw) < 4 || raw[0] != 0xFF || raw[1] != 0xD8 || raw[2] != 0xFF {
		httpErr(w, fmt.Errorf("la imagen no es un JPEG"), http.StatusBadRequest)
		return
	}
	mu.Lock()
	defer mu.Unlock()
	name, err := escribirFoto(raw)
	if err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]string{"url": "/fotos/" + name})
}

// createCopia genera una carpeta con una copia consistente de la base de datos y de las fotos.
func createCopia() (string, error) {
	return createCopiaCon("copia-", time.Now())
}

func createCopiaCon(prefijo string, ahora time.Time) (ruta string, err error) {
	return crearCopiaDe(db, copiasDir, fotosDir, prefijo, ahora)
}

// crearCopiaDe copia la base de datos d (con VACUUM INTO) y las fotos de fotosOrigen en una carpeta nueva de copias.
func crearCopiaDe(d *sql.DB, copias, fotosOrigen, prefijo string, ahora time.Time) (ruta string, err error) {
	dest := filepath.Join(copias, prefijo+ahora.Format(formatoCopia))
	if _, err := os.Stat(dest); err == nil {
		return "", fmt.Errorf("ya hay una copia de este mismo segundo, espera un momento")
	}
	if err := os.MkdirAll(filepath.Join(dest, "fotos"), 0o755); err != nil {
		return "", err
	}
	// Una copia a medias no debe quedar en la lista ni contar como la última.
	defer func() {
		if err != nil {
			os.RemoveAll(dest)
		}
	}()
	q := "VACUUM INTO '" + strings.ReplaceAll(filepath.Join(dest, "fisioterapia.db"), "'", "''") + "'"
	if _, err := d.Exec(q); err != nil {
		return "", err
	}
	entries, _ := os.ReadDir(fotosOrigen)
	for _, e := range entries {
		if err := copyFile(filepath.Join(fotosOrigen, e.Name()), filepath.Join(dest, "fotos", e.Name())); err != nil {
			return "", err
		}
	}
	return dest, nil
}

// restoreFrom copia los datos de otra base de datos sobre la actual, en una sola transacción.
// Las copias antiguas pueden no tener algunas tablas o columnas: se copia lo que exista.
func restoreFrom(path string) error {
	if _, err := db.Exec("ATTACH DATABASE '" + strings.ReplaceAll(path, "'", "''") + "' AS src"); err != nil {
		return err
	}
	defer db.Exec("DETACH DATABASE src")
	var uvOrigen int
	if err := db.QueryRow("PRAGMA src.user_version").Scan(&uvOrigen); err == nil && uvOrigen > schemaVersion {
		return fmt.Errorf("esta copia es de una versión más reciente de la aplicación (modelo %d; esta versión entiende hasta el %d): usa la última versión para restaurarla", uvOrigen, schemaVersion)
	}
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	base := []string{
		"DELETE FROM citas",
		"DELETE FROM citas_series",
		"DELETE FROM observaciones",
		"DELETE FROM orden_sesiones",
		"DELETE FROM puntuaciones",
		"DELETE FROM pautas",
		"DELETE FROM plan_casa",
		"DELETE FROM hitos",
		"DELETE FROM evaluaciones",
		"DELETE FROM planes_guardados_items",
		"DELETE FROM planes_guardados",
		"DELETE FROM plan_items",
		"DELETE FROM planes",
		"DELETE FROM plantilla_aplicaciones",
		"DELETE FROM plantilla_items",
		"DELETE FROM plantillas",
		"DELETE FROM bloque_ejercicios",
		"DELETE FROM bloques",
		"DELETE FROM informes",
		"DELETE FROM patients",
		"DELETE FROM exercises",
		"INSERT INTO exercises (id, nombre) SELECT id, nombre FROM src.exercises",
		"INSERT INTO patients (id, nombre, apellidos, fecha_alta, telefono, email, observaciones, foto_archivo) SELECT id, nombre, apellidos, fecha_alta, telefono, email, observaciones, foto_archivo FROM src.patients",
	}
	for _, q := range base {
		if _, err := tx.Exec(q); err != nil {
			return err
		}
	}
	if srcColumna(tx, "exercises", "libre") {
		if _, err := tx.Exec(`UPDATE exercises SET libre = 1 WHERE id IN (SELECT id FROM src.exercises WHERE libre = 1)`); err != nil {
			return err
		}
	}
	if srcTabla(tx, "bloques") {
		nivel := "''"
		if srcColumna(tx, "bloques", "nivel") {
			nivel = "nivel"
		}
		if _, err := tx.Exec(fmt.Sprintf("INSERT INTO bloques (id, nombre, nivel) SELECT id, nombre, %s FROM src.bloques", nivel)); err != nil {
			return err
		}
	}
	if srcTabla(tx, "bloque_ejercicios") {
		posicion := "rowid"
		if srcColumna(tx, "bloque_ejercicios", "posicion") {
			posicion = "posicion"
		}
		if _, err := tx.Exec(fmt.Sprintf(`INSERT INTO bloque_ejercicios (bloque_id, exercise_id, posicion)
			SELECT bloque_id, exercise_id, %s FROM src.bloque_ejercicios
			WHERE bloque_id IN (SELECT id FROM bloques) AND exercise_id IN (SELECT id FROM exercises)`, posicion)); err != nil {
			return err
		}
	}
	if srcColumna(tx, "patients", "archivado") {
		if _, err := tx.Exec(`UPDATE patients SET archivado = (SELECT s.archivado FROM src.patients s WHERE s.id = patients.id)`); err != nil {
			return err
		}
	}
	if srcColumna(tx, "patients", "color_cita") {
		if _, err := tx.Exec(`UPDATE patients SET color_cita = (SELECT s.color_cita FROM src.patients s WHERE s.id = patients.id)`); err != nil {
			return err
		}
	}
	asignacion, bloque, orden, dias, sesionP := "''", "''", "0", "''", "''"
	if srcColumna(tx, "pautas", "dias") {
		dias = "dias"
	}
	if srcColumna(tx, "pautas", "sesion") {
		sesionP = "sesion"
	}
	if srcColumna(tx, "pautas", "asignacion") {
		asignacion = "asignacion"
	}
	if srcColumna(tx, "pautas", "bloque_id") {
		bloque = "bloque_id"
	}
	if srcColumna(tx, "pautas", "orden") {
		orden = "orden"
	}
	if _, err := tx.Exec(fmt.Sprintf(`INSERT INTO pautas (id, patient_id, exercise_id, desde, hasta, asignacion, bloque_id, orden, dias, sesion)
		SELECT id, patient_id, exercise_id, desde, hasta, %s, %s, %s, %s, %s FROM src.pautas
		WHERE patient_id IN (SELECT id FROM patients) AND exercise_id IN (SELECT id FROM exercises)`, asignacion, bloque, orden, dias, sesionP)); err != nil {
		return err
	}
	// Las copias anteriores al plan en casa y a los hitos no tienen estas tablas.
	if srcTabla(tx, "plan_casa") {
		nota, grupo, notaGrupo := "''", "''", "''"
		if srcColumna(tx, "plan_casa", "nota") {
			nota = "nota"
		}
		if srcColumna(tx, "plan_casa", "grupo") {
			grupo = "grupo"
		}
		if srcColumna(tx, "plan_casa", "nota_grupo") {
			notaGrupo = "nota_grupo"
		}
		if _, err := tx.Exec(fmt.Sprintf(`INSERT INTO plan_casa (id, patient_id, exercise_id, fecha, bloque_id, orden, nota, grupo, nota_grupo)
			SELECT id, patient_id, exercise_id, fecha, bloque_id, orden, %s, %s, %s FROM src.plan_casa
			WHERE patient_id IN (SELECT id FROM patients) AND exercise_id IN (SELECT id FROM exercises)`, nota, grupo, notaGrupo)); err != nil {
			return err
		}
	}
	if srcTabla(tx, "hitos") {
		fotos := "'[]'"
		if srcColumna(tx, "hitos", "fotos") {
			fotos = "fotos"
		}
		if _, err := tx.Exec(fmt.Sprintf(`INSERT INTO hitos (id, patient_id, fecha, nota, fotos)
			SELECT id, patient_id, fecha, nota, %s FROM src.hitos
			WHERE patient_id IN (SELECT id FROM patients)`, fotos)); err != nil {
			return err
		}
	}
	// Las copias anteriores a las evaluaciones no tienen esta tabla.
	if srcTabla(tx, "evaluaciones") {
		fotos := "'[]'"
		if srcColumna(tx, "evaluaciones", "fotos") {
			fotos = "fotos"
		}
		if _, err := tx.Exec(fmt.Sprintf(`INSERT INTO evaluaciones (id, patient_id, fecha, evaluacion, fotos)
			SELECT id, patient_id, fecha, evaluacion, %s FROM src.evaluaciones
			WHERE patient_id IN (SELECT id FROM patients)`, fotos)); err != nil {
			return err
		}
	}
	// Las copias anteriores a los planes guardados no tienen estas tablas.
	if srcTabla(tx, "planes_guardados") && srcTabla(tx, "planes_guardados_items") {
		if _, err := tx.Exec(`INSERT INTO planes_guardados (id, patient_id, descripcion, creada)
			SELECT id, patient_id, descripcion, creada FROM src.planes_guardados
			WHERE patient_id IN (SELECT id FROM patients)`); err != nil {
			return err
		}
		if _, err := tx.Exec(`INSERT INTO planes_guardados_items (id, plan_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo)
			SELECT id, plan_id, fecha, exercise_id, bloque_id, orden, nota, grupo, nota_grupo FROM src.planes_guardados_items
			WHERE plan_id IN (SELECT id FROM planes_guardados) AND exercise_id IN (SELECT id FROM exercises)`); err != nil {
			return err
		}
	}
	// Las copias anteriores a las plantillas no tienen estas tablas.
	if srcTabla(tx, "plantillas") && srcTabla(tx, "plantilla_items") {
		if _, err := tx.Exec(`INSERT INTO plantillas (id, nombre, semanas, creada) SELECT id, nombre, semanas, creada FROM src.plantillas`); err != nil {
			return err
		}
		if srcColumna(tx, "plantillas", "ciclo") {
			if _, err := tx.Exec(`UPDATE plantillas SET ciclo = (SELECT s.ciclo FROM src.plantillas s WHERE s.id = plantillas.id)`); err != nil {
				return err
			}
		}
		if srcColumna(tx, "plantillas", "notas") {
			if _, err := tx.Exec(`UPDATE plantillas SET notas = (SELECT s.notas FROM src.plantillas s WHERE s.id = plantillas.id)`); err != nil {
				return err
			}
		}
		if srcColumna(tx, "plantillas", "duracion") && srcColumna(tx, "plantillas", "unidad") {
			if _, err := tx.Exec(`UPDATE plantillas SET duracion = (SELECT s.duracion FROM src.plantillas s WHERE s.id = plantillas.id), unidad = (SELECT s.unidad FROM src.plantillas s WHERE s.id = plantillas.id)`); err != nil {
				return err
			}
		}
		if _, err := tx.Exec(`INSERT INTO plantilla_items (id, plantilla_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo)
			SELECT id, plantilla_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo FROM src.plantilla_items
			WHERE plantilla_id IN (SELECT id FROM plantillas) AND exercise_id IN (SELECT id FROM exercises)`); err != nil {
			return err
		}
	}
	// Planes en casa (modelo 4). Las copias anteriores tienen plan_casa y planes_guardados, que se restauran
	// arriba y la página convierte en planes al abrirse.
	if srcTabla(tx, "planes") && srcTabla(tx, "plan_items") {
		if _, err := tx.Exec(`INSERT INTO planes (id, patient_id, nombre, inicio, fin, fin_manual, semanas, notas, creado, plantilla_id)
			SELECT id, patient_id, nombre, inicio, fin, fin_manual, semanas, notas, creado, plantilla_id FROM src.planes
			WHERE patient_id IN (SELECT id FROM patients)`); err != nil {
			return err
		}
		if srcColumna(tx, "planes", "duracion") && srcColumna(tx, "planes", "unidad") {
			if _, err := tx.Exec(`UPDATE planes SET duracion = (SELECT s.duracion FROM src.planes s WHERE s.id = planes.id), unidad = (SELECT s.unidad FROM src.planes s WHERE s.id = planes.id)`); err != nil {
				return err
			}
		}
		if _, err := tx.Exec(`INSERT INTO plan_items (id, plan_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo)
			SELECT id, plan_id, dia, exercise_id, bloque_id, orden, nota, grupo, nota_grupo FROM src.plan_items
			WHERE plan_id IN (SELECT id FROM planes) AND exercise_id IN (SELECT id FROM exercises)`); err != nil {
			return err
		}
	}
	if srcTabla(tx, "informes") {
		if _, err := tx.Exec(`INSERT INTO informes (id, patient_id, tipo, nombre, ruta, fecha, desde, hasta, descripcion)
			SELECT id, patient_id, tipo, nombre, ruta, fecha, desde, hasta, descripcion FROM src.informes
			WHERE patient_id IN (SELECT id FROM patients)`); err != nil {
			return err
		}
	}
	if srcTabla(tx, "plantilla_aplicaciones") {
		if _, err := tx.Exec(`INSERT INTO plantilla_aplicaciones (id, plantilla_id, patient_id, desde, hasta, fecha)
			SELECT id, plantilla_id, patient_id, desde, hasta, fecha FROM src.plantilla_aplicaciones
			WHERE plantilla_id IN (SELECT id FROM plantillas) AND patient_id IN (SELECT id FROM patients)`); err != nil {
			return err
		}
	}
	// Agenda (modelo 5): las copias anteriores no tienen citas.
	if srcTabla(tx, "citas_series") {
		if _, err := tx.Exec(`INSERT INTO citas_series (id, patient_id, dias, hora, duracion, desde, hasta, nota, excluidas, creada)
			SELECT id, patient_id, dias, hora, duracion, desde, hasta, nota, excluidas, creada FROM src.citas_series
			WHERE patient_id IN (SELECT id FROM patients)`); err != nil {
			return err
		}
		if srcColumna(tx, "citas_series", "color") {
			if _, err := tx.Exec(`UPDATE citas_series SET color = (SELECT s.color FROM src.citas_series s WHERE s.id = citas_series.id)`); err != nil {
				return err
			}
		}
		if srcColumna(tx, "citas_series", "raiz") {
			if _, err := tx.Exec(`UPDATE citas_series SET raiz = (SELECT s.raiz FROM src.citas_series s WHERE s.id = citas_series.id)`); err != nil {
				return err
			}
		}
	}
	if srcTabla(tx, "citas") {
		if _, err := tx.Exec(`INSERT INTO citas (id, patient_id, fecha, hora, duracion, nota, serie_id, fecha_serie, modificada)
			SELECT id, patient_id, fecha, hora, duracion, nota, serie_id, fecha_serie, modificada FROM src.citas
			WHERE patient_id IN (SELECT id FROM patients)`); err != nil {
			return err
		}
		if srcColumna(tx, "citas", "color") {
			if _, err := tx.Exec(`UPDATE citas SET color = (SELECT s.color FROM src.citas s WHERE s.id = citas.id)`); err != nil {
				return err
			}
		}
	}
	rep, sesionPu := "1", "''"
	if srcColumna(tx, "puntuaciones", "repeticion") {
		rep = "repeticion"
	}
	if srcColumna(tx, "puntuaciones", "sesion") {
		sesionPu = "sesion"
	}
	if _, err := tx.Exec(fmt.Sprintf(`INSERT INTO puntuaciones (patient_id, fecha, exercise_id, sesion, repeticion, valor)
		SELECT patient_id, fecha, exercise_id, %s, %s, valor FROM src.puntuaciones
		WHERE patient_id IN (SELECT id FROM patients) AND exercise_id IN (SELECT id FROM exercises)`, sesionPu, rep)); err != nil {
		return err
	}
	// Las copias anteriores al modelo 8 no tienen orden por sesión.
	if srcTabla(tx, "orden_sesiones") {
		if _, err := tx.Exec(`INSERT INTO orden_sesiones (patient_id, fecha, sesion, exercise_id, posicion)
			SELECT patient_id, fecha, sesion, exercise_id, posicion FROM src.orden_sesiones
			WHERE patient_id IN (SELECT id FROM patients) AND exercise_id IN (SELECT id FROM exercises)`); err != nil {
			return err
		}
	}
	// Las copias anteriores al modelo 7 no tienen observaciones.
	if srcTabla(tx, "observaciones") {
		if _, err := tx.Exec(`INSERT INTO observaciones (patient_id, fecha, sesion, bloque_id, exercise_id, repeticion, texto)
			SELECT patient_id, fecha, sesion, bloque_id, exercise_id, repeticion, texto FROM src.observaciones
			WHERE patient_id IN (SELECT id FROM patients) AND (exercise_id = '' OR exercise_id IN (SELECT id FROM exercises))`); err != nil {
			return err
		}
	}
	if srcTabla(tx, "ajustes") {
		if _, err := tx.Exec("DELETE FROM ajustes"); err != nil {
			return err
		}
		if _, err := tx.Exec("INSERT INTO ajustes (clave, valor) SELECT clave, valor FROM src.ajustes"); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func srcTabla(tx *sql.Tx, tabla string) bool {
	var n int
	err := tx.QueryRow(`SELECT COUNT(*) FROM src.sqlite_master WHERE type = 'table' AND name = ?`, tabla).Scan(&n)
	return err == nil && n > 0
}

// diasValidos deja solo dígitos 1–7 sin repetir y en orden ("71" → "17"); "1234567" equivale a todos ("").
func diasValidos(s string) string {
	var b strings.Builder
	for _, d := range "1234567" {
		if strings.ContainsRune(s, d) {
			b.WriteRune(d)
		}
	}
	if b.Len() == 7 {
		return ""
	}
	return b.String()
}

func boolInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

func srcColumna(tx *sql.Tx, tabla, columna string) bool {
	var n int
	err := tx.QueryRow(`SELECT COUNT(*) FROM pragma_table_info(?, 'src') WHERE name = ?`, tabla, columna).Scan(&n)
	return err == nil && n > 0
}

// ---------- utilidades ----------

func copyFile(src, dst string) error {
	in, err := os.Open(src)
	if err != nil {
		return err
	}
	defer in.Close()
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()
	_, err = io.Copy(out, in)
	return err
}

func writeJSON(w http.ResponseWriter, v any) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(v)
}

func httpErr(w http.ResponseWriter, err error, code int) {
	http.Error(w, err.Error(), code)
}

// ---------- copias automáticas ----------

const (
	prefijoAuto  = "copia-auto-"
	formatoCopia = "2006-01-02_150405"
)

// copiando es true mientras se prepara o se hace una copia; la interfaz consulta
// /api/copiando (sin usar mu) para avisar al usuario y bloquear la pantalla.
var copiando atomic.Int32

func handleCopiando(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]bool{"copiando": copiando.Load() > 0})
}

// Estado de la última comprobación; se protege con mu.
var (
	autoError  string
	autoUltima time.Time
)

// ajusteGlobal lee un ajuste de la base de datos. Debe llamarse con mu bloqueado.
func ajusteGlobal(clave, def string) string {
	var v string
	if err := db.QueryRow(`SELECT valor FROM ajustes WHERE clave = ?`, clave).Scan(&v); err != nil {
		return def
	}
	return v
}

func ajusteEntero(clave string, def, min, max int) int {
	n, err := strconv.Atoi(strings.TrimSpace(ajusteGlobal(clave, "")))
	if err != nil {
		return def
	}
	if n < min {
		return min
	}
	if n > max {
		return max
	}
	return n
}

// copiasAuto devuelve los nombres de las copias automáticas, de la más antigua a la más reciente.
func copiasAuto() []string {
	entries, _ := os.ReadDir(copiasDir)
	var nombres []string
	for _, e := range entries {
		if e.IsDir() && strings.HasPrefix(e.Name(), prefijoAuto) {
			nombres = append(nombres, e.Name())
		}
	}
	sort.Strings(nombres)
	return nombres
}

// copiaDebida indica si está activada la copia automática y toca hacerla ya.
// Debe llamarse con mu bloqueado.
func copiaDebida(ahora time.Time) bool {
	if db == nil || ajusteGlobal("backupAuto", "1") != "1" {
		return false
	}
	var n int
	if err := db.QueryRow(`SELECT (SELECT COUNT(*) FROM patients) + (SELECT COUNT(*) FROM exercises)`).Scan(&n); err == nil && n == 0 {
		return false // no hay nada que guardar
	}
	cada := ajusteEntero("backupCadaDias", 1, 1, 30)
	if autos := copiasAuto(); len(autos) > 0 {
		if ult, err := time.ParseInLocation(formatoCopia, strings.TrimPrefix(autos[len(autos)-1], prefijoAuto), time.Local); err == nil {
			dia := func(t time.Time) time.Time { return time.Date(t.Year(), t.Month(), t.Day(), 12, 0, 0, 0, time.UTC) }
			if int(dia(ahora).Sub(dia(ult)).Hours()/24+0.5) < cada {
				return false
			}
		}
	}
	return true
}

// copiaAutomatica crea una copia si está activada y toca según la frecuencia elegida
// (por días naturales: con frecuencia diaria, una copia el primer momento de cada día en que la
// aplicación está abierta), y borra las automáticas más antiguas. Solo toca las copias
// "copia-auto-*": las manuales y las previas a una restauración nunca se borran.
// Debe llamarse con mu bloqueado.
func copiaAutomatica(ahora time.Time) {
	if !copiaDebida(ahora) {
		return
	}
	conservar := ajusteEntero("backupConservar", 14, 1, 365)
	dest, err := createCopiaCon(prefijoAuto, ahora)
	if err != nil {
		autoError = err.Error()
		log.Println("Copia automática fallida:", err)
		return
	}
	autoError = ""
	autoUltima = ahora
	fmt.Println("Copia automática creada:", dest)
	if autos := copiasAuto(); len(autos) > conservar {
		for _, viejo := range autos[:len(autos)-conservar] {
			if err := os.RemoveAll(filepath.Join(copiasDir, viejo)); err != nil {
				log.Println("No se pudo borrar la copia antigua", viejo, ":", err)
			}
		}
	}
}

// iniciarCopiasAutomaticas comprueba cada 15 minutos si toca hacer una copia
// (así también funciona si el Mac se suspende y se reactiva).
func iniciarCopiasAutomaticas() {
	go func() {
		time.Sleep(20 * time.Second)
		for {
			mu.Lock()
			toca := copiaDebida(time.Now())
			mu.Unlock()
			if toca {
				// Primero se avisa a la interfaz (que bloquea la pantalla) y se da tiempo a que
				// terminen de guardarse los últimos cambios; después se hace la copia.
				copiando.Add(1)
				time.Sleep(3 * time.Second)
				mu.Lock()
				copiaAutomatica(time.Now())
				mu.Unlock()
				copiando.Add(-1)
			}
			time.Sleep(15 * time.Minute)
		}
	}()
}

func handleEstadoAuto(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	defer mu.Unlock()
	out := map[string]any{"error": autoError, "ultima": nil}
	if autos := copiasAuto(); len(autos) > 0 {
		if t, err := time.ParseInLocation(formatoCopia, strings.TrimPrefix(autos[len(autos)-1], prefijoAuto), time.Local); err == nil {
			out["ultima"] = t
		}
	}
	writeJSON(w, out)
}

// ---------- exportación a PDF ----------
// Los PDF los genera el navegador; el servidor los guarda donde elija el usuario (diálogo del sistema) y la
// interfaz registra la ruta en la tabla «informes». Los PDF no se incluyen en las copias de seguridad.

func handlePdfLib(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/javascript; charset=utf-8")
	w.Header().Set("Cache-Control", "max-age=86400")
	w.Write(pdfLibJS)
}

// nombreSeguro deja un nombre de fichero sin separadores de ruta ni caracteres raros.
func nombreSeguro(s string) string {
	var b strings.Builder
	for _, r := range s {
		if unicode.IsLetter(r) || unicode.IsDigit(r) || r == ' ' || r == '-' || r == '_' {
			b.WriteRune(r)
		} else {
			b.WriteRune('_')
		}
	}
	out := strings.Trim(strings.TrimSpace(b.String()), "._ ")
	if r := []rune(out); len(r) > 120 {
		out = string(r[:120])
	}
	if out == "" {
		out = "paciente"
	}
	return out
}

// rutaLibre devuelve la ruta si no existe; si existe, añade « (2)», « (3)»… antes de la extensión.
func rutaLibre(p string) string {
	if _, err := os.Stat(p); os.IsNotExist(err) {
		return p
	}
	ext := filepath.Ext(p)
	base := strings.TrimSuffix(p, ext)
	for n := 2; ; n++ {
		q := fmt.Sprintf("%s (%d)%s", base, n, ext)
		if _, err := os.Stat(q); os.IsNotExist(err) {
			return q
		}
	}
}

// handleExportar guarda un PDF (o, con tipo=json, el archivo de ejercicios y bloques) generado por el navegador
// donde diga el usuario:
//   - con «carpeta» (exportación de varios pacientes): dentro de esa carpeta, sin pisar archivos existentes;
//   - sin ella: abre el diálogo «Guardar como» del sistema, empezando en «inicio» y con «nombre» propuesto.
//
// Devuelve la ruta final; el navegador la registra en el listado de informes del paciente.
func handleExportar(w http.ResponseWriter, r *http.Request) {
	r.Body = http.MaxBytesReader(w, r.Body, 100<<20)
	data, err := io.ReadAll(r.Body)
	if err != nil {
		httpErr(w, err, http.StatusBadRequest)
		return
	}
	q := r.URL.Query()
	// tipo=json: archivo de ejercicios y bloques (exportación de la biblioteca). Si no, un PDF.
	ext, titulo := ".pdf", "Guardar el PDF"
	if q.Get("tipo") == "json" {
		ext, titulo = ".json", "Guardar el archivo de ejercicios y bloques"
		if !json.Valid(data) {
			httpErr(w, fmt.Errorf("el archivo no es válido"), http.StatusBadRequest)
			return
		}
	} else if !bytes.HasPrefix(data, []byte("%PDF-")) {
		httpErr(w, fmt.Errorf("el archivo no es un PDF"), http.StatusBadRequest)
		return
	}
	nombre := nombreSeguro(q.Get("nombre")) + ext
	var dest string
	if c := q.Get("carpeta"); c != "" {
		if carpetaExistente(c) == "" {
			httpErr(w, fmt.Errorf("la carpeta %s no existe", c), http.StatusBadRequest)
			return
		}
		dest = rutaLibre(filepath.Join(c, nombre))
	} else {
		ruta, err := dialogoSistema("guardar", titulo, nombre, carpetaExistente(q.Get("inicio")))
		if err != nil {
			httpErr(w, err, http.StatusConflict)
			return
		}
		if !strings.EqualFold(filepath.Ext(ruta), ext) {
			ruta += ext
		}
		dest = ruta
	}
	// Se escribe en un temporal y se renombra: nunca queda un PDF a medias.
	tmp := dest + ".tmp"
	if err := os.WriteFile(tmp, data, 0o644); err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	if err := os.Rename(tmp, dest); err != nil {
		os.Remove(tmp)
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]string{"path": dest, "nombre": filepath.Base(dest), "carpeta": filepath.Dir(dest)})
}

// rutaInforme busca la ruta de un informe registrado. Solo se abren archivos que la propia aplicación
// registró: el navegador nunca puede pedir abrir una ruta cualquiera.
func rutaInforme(id string) (string, error) {
	mu.Lock()
	defer mu.Unlock()
	var ruta string
	if err := db.QueryRow(`SELECT ruta FROM informes WHERE id = ?`, id).Scan(&ruta); err != nil {
		return "", fmt.Errorf("informe no encontrado")
	}
	return ruta, nil
}

// handleAbrirInforme abre el PDF con el programa del sistema o, con modo=carpeta, muestra su carpeta.
func handleAbrirInforme(w http.ResponseWriter, r *http.Request) {
	ruta, err := rutaInforme(r.URL.Query().Get("id"))
	if err != nil {
		httpErr(w, err, http.StatusNotFound)
		return
	}
	if _, err := os.Stat(ruta); err != nil {
		httpErr(w, fmt.Errorf("no se encuentra el archivo %s: puede que se haya movido o borrado", ruta), http.StatusGone)
		return
	}
	if r.URL.Query().Get("modo") == "carpeta" {
		mostrarEnCarpeta(ruta)
	} else {
		abrirEnSistema(ruta)
	}
	writeJSON(w, map[string]string{"ruta": ruta})
}

// handleInformesExisten indica, para cada informe registrado, si su archivo sigue en su sitio.
func handleInformesExisten(w http.ResponseWriter, r *http.Request) {
	mu.Lock()
	rutas := map[string]string{}
	err := eachRow(`SELECT id, ruta FROM informes`, func(r *sql.Rows) error {
		var id, ruta string
		if err := r.Scan(&id, &ruta); err != nil {
			return err
		}
		rutas[id] = ruta
		return nil
	})
	mu.Unlock()
	if err != nil {
		httpErr(w, err, http.StatusInternalServerError)
		return
	}
	res := map[string]bool{}
	for id, ruta := range rutas {
		_, err := os.Stat(ruta)
		res[id] = err == nil
	}
	writeJSON(w, res)
}

// sesionValida deja solo los valores de Pauta.Sesion que entiende la página: "", "-", "c:<id>", "s:<id>" o
// "!c:<id>,s:<id>…" (en todas menos esas).
func sesionValida(s string) string {
	token := func(t string) bool { return (strings.HasPrefix(t, "c:") || strings.HasPrefix(t, "s:")) && len(t) > 2 }
	if s == "-" || token(s) {
		return s
	}
	// "!c:<cita>,s:<raíz>…": en todas las sesiones menos esas.
	if strings.HasPrefix(s, "!") && len(s) > 1 {
		for _, t := range strings.Split(s[1:], ",") {
			if !token(t) {
				return ""
			}
		}
		return s
	}
	return ""
}

// colorValido deja solo los colores de evento de Google Calendar ("1" a "11"); cualquier otro valor es "" (el color
// normal de la aplicación).
func colorValido(c string) string {
	if n, err := strconv.Atoi(c); err == nil && n >= 1 && n <= 11 && strconv.Itoa(n) == c {
		return c
	}
	return ""
}

// horaValida indica si s es una hora HH:MM (00:00 a 23:59).
func horaValida(s string) bool {
	t, err := time.Parse("15:04", s)
	return err == nil && t.Format("15:04") == s
}

// duracionCita deja la duración de una cita entre 5 minutos y 12 horas (45 si no es válida).
func duracionCita(n int) int {
	if n <= 0 {
		return 45
	}
	if n < 5 {
		return 5
	}
	if n > 720 {
		return 720
	}
	return n
}

// diasCita son los días de la semana de una serie de citas: como diasValidos, pero "todos" se guarda como "1234567"
// (una serie sin días no tiene sentido).
func diasCita(s string) string {
	if d := diasValidos(s); d != "" {
		return d
	}
	return "1234567"
}

// fechaValida indica si s es una fecha AAAA-MM-DD.
func fechaValida(s string) bool {
	_, err := time.Parse("2006-01-02", s)
	return err == nil
}

// duracionValida devuelve una duración guardable: unidad «dias», «semanas» o «meses» y un número dentro de sus
// límites. Sin unidad (datos anteriores), la duración son las semanas.
func duracionValida(n int, unidad string, semanas int) (int, string) {
	max := map[string]int{"dias": 730, "semanas": 104, "meses": 24}
	m, ok := max[unidad]
	if !ok {
		return semanas, "semanas"
	}
	if n < 1 {
		n = 1
	}
	if n > m {
		n = m
	}
	return n, unidad
}
