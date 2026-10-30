# Novedades de la aplicación

## 0.0.7 · 30 oct 2026

### Novedades
- **Observaciones de cada sesión**: al puntuar, arriba de la lista de ejercicios hay un cuadro para escribir cómo ha ido la sesión (o el día, si no tiene sesión). Se guardan solas y se ven en el calendario (en la semana, el principio del texto; en el mes, un ✎; en el día, completas), en la lista de sesiones del paciente y en el informe de pautas, en un apartado propio que se puede quitar al generarlo.
- **Ordenar los ejercicios de cada sesión**: en la ventana del día y en la vista **Día** del calendario, ↑ ↓ en cada bloque y en cada ejercicio suelto. El orden vale solo para esa sesión; los demás días no cambian. Al **añadir** ejercicios (a una sesión, a un día del plan en casa, a «A elegir» o a una plantilla), el panel **Orden**, a la derecha de la lista, muestra lo que ya hay y lo nuevo, para colocarlo antes de añadirlo.
- **Ordenar las listas pulsando la cabecera** de cada columna (pacientes, ejercicios, bloques, plantillas, sesiones, planes en casa, hitos, evaluaciones, informes, copias y el resumen): una vez de menor a mayor, otra al revés y otra vuelve al orden de siempre. Cada lista recuerda su orden. Sustituye a los desplegables «Ordenar por».
- **Buscar un paciente desde cualquier pantalla**, en la barra de arriba (o con ⌘K en Mac, Ctrl+K en Windows).
- **Lista de pacientes**: una fila por paciente, con columnas para la **última** y la **próxima sesión** (púlsalas para ir a la sesión), filtro **Con sesiones: Pasadas / Hoy / Futuras** y orden por **Próxima sesión**. La última sesión no sale si es el mismo día que la próxima.
- **Agenda**: buscador de pacientes.
- **Sesiones del paciente**: botones **Próximas / Pasadas / Todas** (y **↻ Se repiten**, con las sesiones que se repiten cada semana), búsqueda por fechas, mes y año, y el estado de cada sesión (sin ejercicios, sin puntuar, cuántos puntuados). **Puntuar** está en todas: si la sesión aún no tiene ejercicios, se abre para añadirlos.
- **Pautas**: botones **Vigentes / Terminadas / Todas** y búsqueda por fechas, mes y año, además de por bloque o ejercicio.
- **Ordenar las pestañas de la ficha del paciente** en **Ajustes → Personalizar** (↑ ↓). La ficha se abre en la primera. El orden por defecto pasa a ser **Pautas · Sesiones · Calendario · Plan en casa · Progreso · Informes**.
- **Observaciones de cada bloque y de cada ejercicio** al puntuar (un ✎ en cada uno), además de las de la sesión. Qué observaciones se ven se elige en **Ajustes → Personalizar**; las de bloques y ejercicios salen también en el informe de pautas.
- **Filtros por defecto** en **Ajustes → Personalizar**: cómo salen al abrirse las listas de pacientes (activos, archivados o todos, y con qué sesiones), las pautas y las sesiones del paciente y los bloques (por nivel).
- **Informe de pautas**: la gráfica de la evolución pasa a ser opcional (**Incluir la gráfica**) y lo que sale marcado al generarlo (gráfica, detalle de cada día, observaciones) se elige en **Ajustes → Personalizar**.
- **Calendario de otra aplicación**, en **Ajustes → Agenda**: eliges con qué calendario se sincroniza la agenda (**Ninguno** o **Google Calendar**), preparado para añadir otras aplicaciones más adelante. Con **Ninguno**, la agenda no muestra nada de Google.
- **Informes de pautas con nombre**: al generarlo puedes ponerle un nombre, que sale en la lista y en el nombre del archivo. La lista de informes se puede buscar por nombre, archivo y fecha, y filtrar por fecha de generación.

### Mejoras
- En el calendario del paciente, los **días con sesión** llevan todo el borde del color de la sesión, y la barra de arriba (navegación, buscador y leyenda) se queda **fija** al bajar.
- El **color de las sesiones** de cada paciente se elige en sus datos (**Editar datos del paciente**); en cada sesión se puede seguir cambiando.
- **Ver calendario** (antes «Ver ficha»), en la ventana de una sesión, abre el calendario del paciente en la semana de esa sesión.
- Lo que **borra o quita** (eliminar, anular, vaciar, quitar de la lista…) pasa al menú **⋯** de cada fila o apartado, para no pulsarlo sin querer. «Vaciar» un día del plan está ahora dentro de **Editar** el día.
- Los **filtros por fecha** salen plegados tras **Filtrar por fecha** (abiertos si hay alguno puesto).
- La cabecera del paciente ya no muestra los días por semana, y los atajos de teclado de la ventana del día están en su **?**.
- **Ejercicios** y **bloques** se ven en una sola columna; los ejercicios de cada bloque, en columnas debajo.
- Las pautas ya no se ordenan en su pestaña: el orden se elige en cada sesión.
- **Editar** un día del plan en casa o de una plantilla añade con **+ Añadir…**, la misma ventana con el panel de orden.

### Correcciones
- Al programar la primera sesión de un día que ya tenía ejercicios ordenados, la sesión conserva ese orden (al copiarlos o asignarlos). Al anular una sesión, su orden y sus observaciones pasan a «Sin sesión» de ese día.

### Al actualizar
- Esta versión añade a tus datos las observaciones y el orden de las sesiones. Al abrirla por primera vez se hace sola una copia de seguridad de tus datos antes de actualizarlos.

## 0.0.6 · 27 oct 2026

### Novedades
- **Listas por páginas**: las listas largas (pacientes, ejercicios, bloques, plantillas, pautas, planes en casa, sesiones, hitos, evaluaciones, informes y copias de seguridad) se ven por páginas. Debajo de cada lista eliges cuántos ver a la vez: **10**, **25**, **50**, **100** o **Todos**, y pasas de página con **‹ Anterior** y **Siguiente ›**. Cada lista recuerda lo que elijas. Al buscar o filtrar se vuelve a la primera página.

### Mejoras
- Las **citas pasan a llamarse sesiones** en toda la aplicación: la agenda, la pestaña **Sesiones** de la ficha del paciente, **Nueva sesión**, **Programar sesión**, **Sin sesión**… Una cita y una sesión eran lo mismo; ahora solo hay un nombre. No cambia nada de tus datos.
- En Google Calendar, el calendario de la aplicación pasa a llamarse **«Fisioterapia · sesiones»** (se cambia solo en la próxima sincronización) y los eventos dicen «Sesión» en lugar de «Cita».
- En la pantalla **Plantillas casa**, la búsqueda se conserva al volver a la pantalla, como en Ejercicios y Bloques.

## 0.0.5 · 27 oct 2026

### Novedades
- **Sesiones**: cada sesión tiene sus propios ejercicios y puntuaciones. Si un paciente viene dos veces el mismo día, cada visita se puntúa por separado (aunque haga los mismos bloques). Los días sin sesión se puntúan como siempre («Sin sesión»). Al asignar o editar una pauta se elige **en qué sesión** toca, en una lista junto a los ejercicios: todas, una o varias sesiones o series (por ejemplo, las de las 10:00) o ninguna (sin sesión). Al programar la primera sesión de un día que ya tiene ejercicios se elige si la sesión empieza vacía, con una copia de los ejercicios o con los que ya había (y sus puntuaciones). Las sesiones se pueden **anular desde la lista** del paciente; si tienen ejercicios o puntuaciones, se avisa antes. La ventana del día muestra sus sesiones; la media del día junta todas y el informe de pautas detalla cada sesión.
- **Agenda de sesiones**: nuevo apartado **Agenda** en el menú, con las sesiones de todos los pacientes por semanas o por días. Pulsa un hueco libre para programar una sesión a esa hora o una sesión para cambiarla o anularla. Avisa si el hueco ya está ocupado. También hay **vista de mes**.
- **Color de las sesiones**: en la ficha del paciente (pestaña Sesiones) eliges el color de sus sesiones, que es el que llevan por defecto las nuevas; en cada sesión se puede cambiar. Son los colores de Google Calendar, así que allí se ven igual.
- **Sesiones que se repiten cada semana** (por ejemplo, martes y jueves a las 17:00, hasta una fecha o sin fecha de fin). Al cambiar o anular una, eliges si es **solo esa** o **esa y las siguientes**.
- **Sesiones en la ficha del paciente**: nueva pestaña **Sesiones** con sus próximas sesiones, las que se repiten y las pasadas. Cada sesión tiene **Puntuar**, si ese día tiene ejercicios. La próxima sesión sale también en la cabecera de la ficha y en la lista de pacientes, donde además hay un botón **Nueva sesión** para programar una sesión sin entrar en la ficha.
- **Los días con sesión se marcan en el calendario** de ejercicios del paciente, con un punto del color de la sesión.
- **Sincronización con Google Calendar** en los dos sentidos: las sesiones se copian en un calendario «Fisioterapia · sesiones» de tu cuenta de Google, lo que muevas o borres allí cambia también aquí, y tus otros calendarios marcan en la agenda las horas que tienes ocupadas. Se configura una vez en **Ajustes › Agenda** (los pasos están allí y en el manual). Puedes elegir si en Google sale el nombre del paciente, sus iniciales o solo «Sesión».
- **Exportar e importar ejercicios y bloques**: guarda la biblioteca en un archivo (solo bloques, solo ejercicios o las dos cosas) y cárgala en otra carpeta de datos u otro ordenador, por ejemplo para empezar una base de datos nueva solo con los ejercicios y los bloques. Si la carpeta ya tiene ejercicios o bloques, se avisa y se **combinan** sin borrar ni duplicar nada. Los catálogos como bloques_dmi.json se siguen importando igual.
- **Planes en casa nuevos**: cada paciente tiene ahora una **lista de planes en casa**. Cada plan tiene **nombre**, fecha en que **empieza**, **duración** (en **días, semanas o meses**), fecha en que **termina** (se calcula sola, pero se puede cambiar a mano, por ejemplo por vacaciones, sin cambiar la duración) y **notas u observaciones**. Se edita igual que una plantilla: todas sus semanas a la vez, de lunes a domingo y con la fecha de cada día; los días fuera del plan salen en gris.
- **Ejercicios «a elegir»**: en cada plan (y en cada plantilla) se pueden poner ejercicios sin día fijo, para que el paciente los haga cuando quiera durante el plan.
- **PDF del plan en casa** con el nombre del plan, sus fechas y duración, las notas, los ejercicios «a elegir» y cada día con su fecha.
- **Buscar planes** en la lista por nombre, por intervalo de fechas, por mes y por año. La lista muestra el inicio, el fin, la duración y si el plan está en curso, es próximo o ha terminado.
- **Duplicar un plan**: crea otro igual que empieza cuando termina el anterior.
- **Puntuar hoy**: botón en cada paciente de la lista y en la cabecera de su ficha que abre directamente la puntuación de hoy, sin salir de la pantalla: se puede ir puntuando a un paciente tras otro desde la lista. «Ver su calendario» lleva a su ficha si se quiere.
- **Modo claro/oscuro con un clic**: botón de la luna o el sol en la barra de arriba, en todas las pantallas.
- El número de versión está ahora en la barra de arriba, a la derecha.
- **Puntuar con el teclado**: en la ventana del día, las teclas **0**, **1**, **2** y **3** puntúan la fila marcada y pasan a la siguiente; las flechas **↑ ↓** cambian de fila y **+** añade una repetición.
- **Días de la semana en las pautas**: al asignar ejercicios (o al editar una pauta) puedes elegir qué días toca, por ejemplo lunes y jueves. Los demás días el ejercicio no sale en el calendario ni cuenta como pendiente.
- **Editar una pauta** en una sola ventana: inicio, fin (continua o hasta una fecha) y días de la semana. Sustituye a los campos de fecha y los botones «Establecer» de cada pauta.
- **Archivar pacientes**: un paciente que ya no viene se puede archivar (desde la lista o desde «Editar datos del paciente»). Deja de salir en la lista sin borrar nada, y se recupera cuando quieras. La lista tiene un filtro **Activos / Archivados / Todos**.
- **Lista de pacientes más informativa**: cuántos ejercicios tiene hoy y cuántos están puntuados, la fecha de la última sesión y hasta cuándo tiene plan en casa. Se puede **ordenar por última sesión**.
- **Botón «Salir»** en el menú, para cerrar la aplicación del todo sin tener que buscar la ventana negra. Al abrir una versión nueva, la anterior se cierra sola.
- **Nueva plantilla** desde cero, en Biblioteca › Plantillas casa, sin tener que montarla antes en un paciente. Las plantillas también tienen notas.
- **Crear un ejercicio desde la ventana de un bloque** («¿Falta alguno?» → «Crear y añadir»): queda en la biblioteca y marcado en el bloque.
- **Informe PDF renovado**: lleva arriba los datos de la clínica (logo, nombre y profesional), un **resumen por ejercicio** con días previstos, puntuados y media, y la gráfica. El **detalle de cada día** es opcional: sin él, el informe suele caber en una página.
- **Gráfica de líneas**: se puede ver **por ejercicio**, **por bloque** o la **media del día**, y pulsando la leyenda se oculta o se muestra cada línea. Aprovecha todo el ancho de la pantalla.
- **«✓ Guardado»**: un aviso discreto abajo a la izquierda cada vez que se guardan cambios.
- **Deshacer**: al eliminar o quitar algo (un paciente, una pauta, un ejercicio de un día, un hito, una plantilla, el plan en casa…) sale abajo durante unos segundos un aviso con el botón **Deshacer**. También funciona **Cmd+Z** (Mac) o **Ctrl+Z** (Windows).
- **Botones Atrás y Adelante del navegador**: ahora llevan a la pantalla anterior o siguiente de la aplicación (y Atrás cierra la ventana que esté abierta). Al recargar la página se vuelve a la misma pantalla.
- **Avisos y confirmaciones propios de la aplicación**, en lugar de las ventanas del navegador («127.0.0.1:8765 dice…»). Los botones dicen lo que hacen («Eliminar paciente», «Vaciar plan»…) y los que borran van en rojo.
- **Borrar todo** pide escribir la palabra **BORRAR** para confirmar.

### Mejoras
- Menú principal: **Biblioteca ▾** agrupa **Ejercicios**, **Bloques** y **Plantillas casa** (antes «Pautas ▾» y «Plan en casa»), para no confundirlos con las pestañas del paciente que se llaman igual.
- Ventana del día más compacta: una fila por ejercicio con sus puntuaciones, **+ Rep.** y **Quitar**. «Quitar todos los ejercicios» está ahora en la pestaña «Puntuar ejercicios» y solo aparece si el día tiene ejercicios.
- Calendario: en la vista **Mes**, cada día muestra un resumen (media del día y cuántos ejercicios están puntuados); en la vista **Semana** caben todos los ejercicios, agrupados bajo su bloque con el nombre corto (Derecha, Izquierda…). Los días futuros ya no salen como «sin puntuar».
- Resumen: la lista va en orden de ejecución y agrupada por bloque, como la gráfica de puntos. Las filas de cada repetición se muestran con **Ver cada repetición**. Los días previstos solo cuentan hasta hoy y solo los días de la semana que tocan.
- Pautas del paciente: cada pauta muestra sus fechas y días en texto, con un botón **Editar**. Las pautas terminadas van aparte, plegadas, al final.
- Usar una plantilla crea siempre un **plan nuevo** para cada paciente (con nombre, inicio y semanas), en lugar de mezclarse con lo que ya hubiera. En la pantalla Plantillas, el botón es **Usar con pacientes…**, y «Pacientes (N)» cuenta a los que tienen un plan en curso o próximo creado con ella.
- Los planes en casa que ya existían se convierten solos: el plan de cada paciente pasa a ser un plan llamado «Plan en casa» con sus fechas, y cada plan guardado, un plan con su nombre. Desaparecen «Guardar plan…» y la lista de «Planes guardados», que ya no hacen falta.
- Los botones de cada plan de la lista ya no se descolocan en dos líneas.
- Ejercicios: «Nuevo ejercicio…» abre su propia ventana y las acciones de cada ejercicio van en un menú **⋯** (Renombrar…, Duplicar, Eliminar…). «Clonar» pasa a llamarse **Duplicar**.
- **Exportar…** e **Importar…** ejercicios y bloques desde las pantallas Ejercicios y Bloques, y desde Ajustes › Datos.
- Evaluación inicial e Hitos: primero se ve el historial; el formulario se abre con **Nueva evaluación…** / **Nuevo hito…**. Las fotos salen en miniatura en cada fila.
- La cabecera del paciente se hace más pequeña al bajar por la página, para dejar más sitio.
- «Fecha de alta» pasa a llamarse **Primera visita**.
- En la lista de pacientes, los botones para varios pacientes solo aparecen al marcar alguno.
- El informe de puntuaciones pasa a llamarse **Informe de pautas** en todas partes (botones, ventana, lista de PDF, nombre del archivo y el propio PDF), para no confundirlo con el PDF del plan en casa.
- Si la aplicación no puede arrancar porque sigue abierta otra versión o porque otro programa usa el puerto, sale una ventana con un mensaje claro de qué hacer.
- En «Nuevo paciente» ya no sale «Quitar foto» si no hay foto, y el nombre está marcado como obligatorio.
- Manual de Ayuda y ayudas «?» actualizados con todo lo anterior.

## 0.0.4 · 25 oct 2026

### Novedades
- **Eliminar pacientes**: desde la ficha del paciente y también desde el listado, donde puedes marcar varios y eliminarlos a la vez.
- **Plantillas de varias semanas**: ahora se editan igual que un plan en casa, con una tarjeta por cada día de todas las semanas. Nombre, duración y contenido se editan con un solo botón.
- **Aplicar una plantilla a varios pacientes** a la vez, con lista de pacientes y buscador.
- **Pacientes con una plantilla**: botón para ver qué pacientes la tienen asignada, con buscador.
- **Ejercicio en texto libre** en el plan de casa, para pautas puntuales que no están en la biblioteca.
- **Vaciar el plan de casa** de un paciente con un solo botón.
- **Buscadores** de bloques y ejercicios en las pestañas Pautas, Calendario y Plan de casa del paciente, y buscador en el listado de plantillas (por nombre, bloques o ejercicios).
- **Ayuda**: nuevo apartado en el menú con el manual de la aplicación, con índice y buscador. En las pantallas más complejas hay un icono **?** con una explicación corta y un enlace a la parte del manual que habla de ello.
- **Pestaña «Novedades»** en Ajustes (esta pantalla) y aviso al abrir la aplicación después de actualizar.
- **Elegir dónde guardar los PDF**: al exportar un informe o un plan en casa se abre la ventana «Guardar como» del sistema (empieza en la última carpeta usada). Si exportas varios pacientes a la vez, eliges la carpeta una sola vez.
- **PDF generados en la pestaña «Informes»** del paciente: lista de informes y planes en casa exportados, con botones para abrirlos, mostrarlos en su carpeta o quitarlos de la lista (el archivo no se borra). Si un PDF se ha movido o borrado, se avisa.
- **Ampliar la foto del paciente** haciendo clic sobre ella (listado, ficha y listas de pacientes).
- **Generar informe PDF desde Calendario y Resumen**, con el periodo que estás viendo (día, semana, mes o intervalo) ya puesto.
- **Buscador de bloques y ejercicios en el Resumen.**
- **Repeticiones a la vista**: en el calendario, los ejercicios con varias repeticiones muestran cuántas entre paréntesis antes de la media; en el Resumen, la lista y la gráfica de puntos tienen una subfila por repetición, y la gráfica de líneas indica las repeticiones en la leyenda y en cada punto. En la gráfica de puntos, la media de cada día se muestra con decimales (por ejemplo 0,5), sin redondear.
- **Funciona también en Windows.**

### Mejoras
- El listado de pacientes ahora es una lista, no una cuadrícula.
- Menú principal reorganizado: **Pautas** despliega «Ejercicios» y «Bloques», cada uno en su propia pantalla, y «Plantillas» pasa a llamarse **Plan en casa**.
- La ventana de un día del calendario tiene ahora dos pestañas, **Puntuar ejercicios** y **Añadir ejercicios**, en lugar de secciones plegables. Se abre en «Puntuar» (o en «Añadir» si el día está vacío) y, al añadir ejercicios, pasa sola a «Puntuar».
- Ajustes se ha reorganizado en pestañas.
- Texto de ayuda del calendario: «Pulsa un día para añadir, quitar o puntuar ejercicios de ese día».
- Todos los botones que borran o quitan algo (eliminar, quitar, vaciar, restaurar una copia…) están ahora en rojo.
- Botones más claros: «Exportar plan a PDF» y, en los planes guardados, «Exportar a PDF».
- Pestañas del paciente reorganizadas: **Pautas · Calendario · Plan en casa · Progreso · Informes**. «Progreso» despliega **Evaluación inicial** (antes «Evaluaciones») e **Hitos**.
- El **Resumen** de ejercicios y puntuaciones está dentro de **Calendario**, con un botón para alternar entre «Calendario» y «Resumen». «Informes» queda para generar los PDF y ver los ya generados.
- El botón «Guardar plan» ahora es «Guardar plan…» porque abre una ventana para poner el nombre.
- Las listas largas de pacientes tienen scroll y se pueden usar aunque haya muchos.
- Al actualizar a una versión que cambia la forma de guardar los datos, la aplicación hace antes una copia de seguridad automática («copia-previa-actualizacion») que no se borra sola.

### Correcciones
- En Ajustes › Copias de seguridad, la casilla y los desplegables de las copias automáticas salían descolocados.
- En la puntuación de un día, «Añadir repetición» en un ejercicio sin puntuar añadía solo una «×» en vez de una fila nueva. Además, la «×» ya no aparece cuando solo hay una repetición.
- Una plantilla seguía mostrando a un paciente aunque se le hubieran borrado todas sus pautas y planes.

## 0.0.3

### Novedades
- Primera versión entregada.
