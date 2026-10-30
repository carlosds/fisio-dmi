# Manual de la aplicación {#inicio}

Esta aplicación sirve para llevar el seguimiento de los ejercicios de cada paciente: qué ejercicios tiene asignados, cómo los hace cada día (puntuación de 0 a 3), qué tiene que hacer en casa y cómo evoluciona.

Todo se guarda solo, en tu ordenador. No hace falta pulsar «Guardar» salvo en las ventanas que lo piden expresamente. Cada vez que se guarda algo sale un momento «✓ Guardado» abajo a la izquierda.

**Si borras algo por error**, abajo sale durante unos segundos un aviso con el botón **Deshacer** (también vale **Cmd+Z** en Mac o **Ctrl+Z** en Windows). Funciona al eliminar o quitar pacientes, pautas, ejercicios, bloques, plantillas, hitos, evaluaciones, sesiones y cosas del plan en casa, y también al importar ejercicios y bloques.

**Listas largas.** Las listas (pacientes, ejercicios, bloques, plantillas, pautas, planes en casa, sesiones, hitos, evaluaciones, informes y copias de seguridad) se ven por páginas cuando tienen más de 10 elementos. Debajo de cada lista eliges cuántos ver a la vez (**10**, **25**, **50**, **100** o **Todos**) y pasas de página con **‹ Anterior** y **Siguiente ›**. Cada lista recuerda lo que elijas. Al buscar o filtrar se vuelve a la primera página.

**Los botones Atrás y Adelante** del navegador (o deslizar dos dedos en el trackpad) te llevan a la pantalla anterior o siguiente. Si hay una ventana abierta, Atrás primero la cierra.

El menú de arriba tiene estos apartados:

- **Pacientes**: la lista de pacientes y la ficha de cada uno. Es donde pasarás la mayor parte del tiempo.
- **Agenda**: las sesiones de todos los pacientes, por semanas o por días.
- **Biblioteca ▾**: los **Ejercicios**, los **Bloques** y las **Plantillas casa** (plantillas del plan en casa), que luego usas con los pacientes.
- **Ajustes**: datos de la clínica, horario de la agenda y Google Calendar, copias de seguridad, carpeta de datos y novedades.
- **Ayuda**: este manual.
- **Salir**: cierra la aplicación del todo.

A la derecha de la barra están el botón de **modo claro/oscuro** (la luna o el sol: un clic cambia el aspecto de toda la aplicación) y el número de la versión instalada.

> **Consejo:** en muchas pantallas verás un icono **?**. Púlsalo para ver una explicación corta y un enlace a la parte de este manual que habla de ello.

## Abrir y cerrar la aplicación {#primeros-pasos}

**Para abrirla**, haz doble clic en **Fisioterapia.command** (Mac) o **Fisioterapia.bat** (Windows). Se abre una ventana negra (Terminal en Mac, ventana de comandos en Windows) y, enseguida, la aplicación en el navegador.

- **No cierres la ventana negra** mientras uses la aplicación: es el programa que guarda tus datos.
- Si la aplicación ya estaba abierta, el doble clic solo abre otra vez la página en el navegador.
- Si estaba abierta una versión anterior (por ejemplo, justo después de actualizar), se cierra sola y se abre la nueva.
- Puedes cerrar la pestaña del navegador cuando quieras; para volver, haz doble clic otra vez en el mismo archivo.

**Para cerrarla del todo**, pulsa **Salir** en el menú de arriba. La aplicación termina de guardar, se apaga y te lo indica en la página. Después ya puedes cerrar la pestaña y la ventana negra.

> **Importante:** si al abrirla el navegador dice que no puede conectar, comprueba que la ventana negra sigue abierta. Si no estás segura de si está abierta o no, reinicia el ordenador y vuelve a abrirla.

## Conceptos básicos {#conceptos}

Merece la pena tener claras estas palabras, porque se repiten en toda la aplicación:

- **Ejercicio**: una actividad concreta, por ejemplo «Pivoteo supino 90° – Derecha».
- **Bloque**: un grupo de ejercicios que se asignan juntos y en un orden, por ejemplo «Pivoteo supino 90°» con su lado derecho e izquierdo. Puede tener un **nivel** (A, B, C…).
- **Pauta**: un bloque o ejercicio asignado a un paciente para trabajarlo en la clínica, desde una fecha y, si quieres, hasta otra. Puede ser para todos los días o solo para algunos días de la semana.
- **Puntuación**: cómo ha hecho el paciente un ejercicio un día concreto, de **0** (no lo consigue) a **3** (lo consigue bien).
- **Repetición**: si un día haces el mismo ejercicio varias veces, cada repetición tiene su propia puntuación. La aplicación calcula la media.
- **Plan en casa**: los ejercicios que el paciente (o su familia) tiene que hacer en casa durante un periodo: tiene nombre, fecha de inicio, duración (en días, semanas o meses), fecha de fin y notas. Cada ejercicio va en un día o en **A elegir** (cuando el paciente quiera). Un paciente puede tener varios planes. Es independiente de las pautas y no se puntúa.
- **Plantilla**: un plan en casa sin fechas (de lunes a domingo, con su duración en días, semanas o meses) que puedes usar con cualquier paciente.
- **Evaluación inicial** e **hitos**: notas con fecha y fotos sobre el estado y los logros del paciente.
- **Informe de pautas**: un PDF con los ejercicios de las pautas y sus puntuaciones en un periodo. (El otro tipo de PDF es el del **plan en casa**.)
- **Sesión**: un día y una hora reservados para un paciente en la **Agenda**, con sus propios ejercicios y puntuaciones. Una sesión puede **repetirse cada semana** (por ejemplo, martes y jueves a las 17:00): es una **serie** de sesiones.
- **Paciente archivado**: un paciente que ya no viene. Deja de salir en la lista, pero no se borra nada de lo suyo.

## Ordenar listas y tablas {#ordenar}

Todas las listas (pacientes, ejercicios, bloques, plantillas, sesiones, planes en casa, hitos, evaluaciones, informes, copias de seguridad y el resumen) tienen una **cabecera** con el nombre de sus columnas. Pulsa una columna para ordenar por ella:

- La primera vez, de menor a mayor (**▲**: A→Z, de la fecha más antigua a la más reciente, de menos a más).
- La segunda vez, al revés (**▼**).
- La tercera vez, vuelve al orden de siempre de esa lista.

La columna por la que está ordenada la lista lleva la flecha en color; las demás, **↕**. Cada lista recuerda su orden. Lo que no tiene dato (por ejemplo, un paciente sin próxima sesión) va siempre al final. En el **resumen**, los ejercicios se ordenan dentro de cada bloque. Los ejercicios de una sesión y de los planes en casa no se ordenan así: se colocan con ↑ ↓ (ver [Puntuar un día](#puntuar) y [Planes en casa](#plan-en-casa)).

## Acciones que borran y filtros por fecha {#menus}

**Menú ⋯.** Lo que borra o quita (eliminar una pauta, un bloque, una plantilla, un plan, un hito o una evaluación; anular una sesión; quitar un ejercicio de una sesión; quitar un informe de la lista…) no está a la vista: está en el botón **⋯** de su fila o de su apartado, en rojo. Así es más difícil pulsarlo sin querer. Si te equivocas, pulsa **Deshacer**.

**Filtrar por fecha.** En Pautas, Sesiones, Planes en casa e Informes, los filtros **entre dos fechas**, **mes** y **año** están plegados: pulsa **Filtrar por fecha** para verlos. Si hay alguno puesto, salen abiertos y el botón dice **· activo**.

**Buscar un paciente desde cualquier pantalla.** Escribe en **Buscar paciente**, en la barra de arriba (o pulsa **⌘K** en Mac, **Ctrl+K** en Windows). Con las flechas **↑ ↓** eliges y con **Intro** abres su ficha.

## Pacientes {#pacientes}

La pantalla **Pacientes** muestra la lista de pacientes, uno por fila. Debajo del nombre ves cuántos ejercicios tiene **hoy** y cuántos están puntuados, hasta cuándo tiene **plan en casa** y su teléfono; en sus columnas, la fecha de su **última sesión** puntuada y su **próxima sesión**. La casilla de la cabecera marca a todos los de la lista.

- **Nueva sesión**: programa una sesión para ese paciente sin salir de la lista (ver [Agenda y sesiones](#agenda)).
- **Puntuar hoy**: abre la ventana de puntuación de hoy de ese paciente sin salir de la lista, así puedes ir puntuando a un paciente tras otro (ver [Puntuar un día](#puntuar)). Si quieres ir a su calendario, pulsa **Ver su calendario** en esa ventana. Si ya está todo puntuado, el botón dice **Ver hoy**.
- **Buscar**: escribe en la caja de búsqueda parte del nombre, del teléfono o del email. Para abrir un paciente desde otra pantalla, usa **Buscar paciente** en la barra de arriba.
- **Última sesión** y **Próxima sesión**: púlsalas para ir a la sesión. La última abre sus puntuaciones; la próxima, la ventana de la sesión (para cambiarla o anularla).
- **Ordenar**: pulsa **Paciente**, **Última sesión** o **Próxima sesión** en la cabecera de la lista (ver [Ordenar listas y tablas](#ordenar)).
- **Activos / Archivados / Todos**: qué pacientes se ven. Por defecto, solo los activos.
- **Abrir la ficha**: pulsa el nombre del paciente.
- **Ver la foto en grande**: pulsa la foto. Para cerrarla, pulsa en cualquier sitio o la tecla Esc.
- **Nuevo paciente**: botón **Nuevo paciente**. Solo el nombre es obligatorio. La **primera visita** es el día en que empieza a venir a la clínica.

**Acciones con varios pacientes a la vez.** Marca la casilla de cada paciente (o la de arriba, para marcar todos los de la lista). Al marcar alguno aparecen los botones:

- **Asignar ejercicios (N)**: asigna los mismos bloques o ejercicios a todos (ver [Pautas](#pautas)).
- **Informe de pautas… (N)**: genera un informe de pautas para cada uno (ver [Informes](#informes)).
- **Archivar (N)**: los quita de la lista sin borrar nada. Con el filtro **Archivados**, el botón es **Recuperar (N)**.
- **Eliminar (N)**: borra a esos pacientes y todo lo suyo.

**Editar, archivar o eliminar un paciente.** En su ficha, pulsa **Editar datos del paciente**. Ahí puedes cambiar sus datos y su foto, y abajo están **Archivar paciente** y **Eliminar paciente**.

> **Consejo:** cuando un paciente deja de venir, mejor **archivarlo** que eliminarlo: la lista queda limpia y, si vuelve, lo recuperas con todo su historial.

> **Importante:** eliminar un paciente borra también sus pautas, puntuaciones, plan en casa, evaluaciones, hitos y sesiones. Justo después puedes pulsar **Deshacer**; pasados unos segundos, solo se recupera restaurando una copia de seguridad (ver [Copias de seguridad](#copias)).

## La ficha del paciente {#ficha}

Arriba de la ficha están siempre la foto, el nombre, su **próxima sesión** (púlsala para verla), la fecha de la primera visita, el teléfono y las observaciones, y los botones **Puntuar hoy** y **Editar datos del paciente**. Al bajar por la página, esta cabecera se hace más pequeña para dejar sitio.

Si el paciente está archivado, lo indica debajo del nombre, con el botón **Recuperar paciente**.

Debajo hay seis pestañas (este es su orden por defecto; puedes cambiarlo en **Ajustes → Personalizar**, y la ficha se abre en la primera):

- **Pautas**: qué ejercicios tiene asignados para la clínica. Ver [Pautas del paciente](#pautas).
- **Sesiones**: sus próximas sesiones, las que se repiten cada semana y las pasadas. Ver [Agenda y sesiones](#agenda).
- **Calendario**: el día a día, para puntuar, y el **Resumen** de la evolución. Ver [Calendario](#calendario) y [Resumen](#resumen).
- **Plan en casa**: los ejercicios para casa. Ver [Plan en casa](#plan-en-casa).
- **Progreso ▾**: despliega **Evaluación inicial** e **Hitos**. Ver [Progreso](#progreso).
- **Informes**: los PDF generados de este paciente (informes de pautas y planes en casa). Ver [Informes](#informes).

## Pautas del paciente {#pautas}

En la pestaña **Pautas** ves los bloques y ejercicios que el paciente tiene asignados, en el **orden en que se hacen**. Ese orden es el que se usa luego en el calendario, al puntuar y en los informes. Debajo de cada pauta pone desde cuándo y hasta cuándo es, y qué días de la semana si no es para todos.

**Asignar ejercicios.** Pulsa **Asignar ejercicios** y:

1. Busca y marca los bloques o ejercicios sueltos. Puedes filtrar por nivel y, con **▸ Ver**, ver qué ejercicios tiene cada bloque.
2. Elige **Desde** qué fecha.
3. Elige la **Duración**: **Continua** (hasta que la termines), **Hasta una fecha** o **Solo ese día**.
4. Elige los **días de la semana**. Por defecto están todos; **Lunes a viernes** marca solo los laborables.
5. Si el paciente tiene sesiones, a la derecha de la lista sale **En qué sesión**: **Todas** (lo normal), una o varias de sus sesiones o series de sesiones, o **Ninguna** (los ejercicios quedan sin sesión). Ver [Sesiones](#sesiones).
6. Pulsa **Asignar**.

**Orden.** Las pautas no se ordenan aquí: el orden de los ejercicios se elige en cada sesión (ver [Puntuar un día](#puntuar)). Si no lo cambias, salen en el orden en que los asignaste.

**Cambiar fechas o días.** Pulsa **Editar** en la pauta. En la ventana puedes cambiar:

- **Inicio**: desde qué día.
- **Fin**: **Continua (sin fecha de fin)** o **Hasta una fecha**.
- **Días**: qué días de la semana toca. Si desmarcas un día, el ejercicio deja de salir ese día en el calendario.
- **En qué sesión** (si el paciente tiene sesiones): todas, unas sesiones concretas o ninguna. Ver [Sesiones](#sesiones).

Pulsa **Guardar** para aplicar los cambios.

**Vigentes, terminadas o todas.** Con los botones **Vigentes** (las que están en curso o empiezan más adelante), **Terminadas** y **Todas** eliges qué pautas ver; en **Todas**, las terminadas van al final. Además del buscador de bloque o ejercicio, puedes buscar las pautas que había **entre dos fechas**, en un **mes** o en un **año** (**Quitar filtros** vuelve a verlas todas).

**Quitar pautas.** En el menú **⋯** de cada pauta, **Eliminar pauta…** la quita; en el **⋯** de arriba, junto a **Asignar ejercicios**, **Quitar todas las pautas…** las quita todas.

> **Importante:** si un ejercicio ya tiene puntuaciones en los días que vas a quitar (por cambiar fechas, días o eliminarlo), la aplicación te avisa antes, porque esas puntuaciones se borrarían.

> **Consejo:** para quitar un ejercicio solo de un día concreto, no hace falta tocar las pautas: hazlo desde el calendario (ver [Puntuar un día](#puntuar)).

## Calendario {#calendario}

La pestaña **Calendario** tiene dos vistas, que se cambian con los botones de arriba: **Calendario** y **Resumen**.

- **Día / Semana / Mes**: cambia cuánto tiempo ves a la vez. **Anterior**, **Hoy** y **Siguiente** mueven las fechas.
- **Días con sesión**: tienen todo el borde del color de la sesión (al poner el ratón encima, la hora). Así se ve de un vistazo qué días vino o viene el paciente. Las sesiones se programan en la [Agenda](#agenda).
- **Buscar**: escribe el nombre de un bloque o ejercicio para ver solo esos.
- Al bajar por el calendario, la barra de arriba (**Anterior**, **Hoy**, **Siguiente**, el mes o la semana que ves, **Día / Semana / Mes**, el buscador y la leyenda) se queda fija debajo de la cabecera del paciente.

**Vista Semana.** Cada día muestra sus ejercicios, agrupados bajo el nombre de su bloque:

- **Colores**: cada ejercicio sale del color de su puntuación (0 rojo, 1 naranja, 2 verde claro, 3 verde oscuro). Con borde de puntos, aún no está puntuado.
- **Repeticiones**: si un día un ejercicio tiene varias, sale su número entre paréntesis antes de la media, por ejemplo «(3) 2,3».
- **«N sin puntuar»**: en la esquina de cada día, cuántos ejercicios faltan por puntuar.

**Vista Mes.** Cada día muestra un resumen: la **media** del día (en el color de la puntuación) y **cuántos ejercicios están puntuados** de los previstos. Si faltan por puntuar, sale resaltado. Pasa el ratón por encima para ver el detalle.

**Vista Día.** Los ejercicios del día, para puntuarlos directamente sin abrir ninguna ventana.

Pulsa un día para añadir, quitar o puntuar ejercicios de ese día.

**Generar informe de pautas…** (arriba a la derecha) crea un informe de pautas del periodo que estás viendo: el día, la semana o el mes. Ver [Informes](#informes).

## Puntuar un día {#puntuar}

Al pulsar un día del calendario (o **Puntuar hoy**) se abre su ventana, con dos pestañas. Si ese día el paciente tiene sesión, arriba salen sus **sesiones** (con cuántos ejercicios lleva puntuados cada una): pulsa la que quieras puntuar. Ver [Sesiones](#sesiones).

**Puntuar ejercicios** (se abre esta si el día tiene ejercicios). Cada ejercicio ocupa una fila:

- Pulsa **0**, **1**, **2** o **3**. Pulsa el mismo número otra vez para borrar la puntuación.
- **+ Rep.** añade otra repetición para puntuar ese ejercicio otra vez el mismo día. La **×** quita una repetición.
- En el **⋯** de cada ejercicio, **Quitar de esta sesión** (o **de este día**) lo quita solo de ahí; el resto sigue igual.
- En el **⋯** de arriba, junto a las pestañas, **Quitar todos los ejercicios…** vacía ese día (o esa sesión).
- **↑ ↓** cambian el orden: en el título de cada bloque (se mueve el bloque entero) y en cada ejercicio suelto. El orden vale solo para esa sesión de ese día; los demás días siguen igual. También se puede ordenar desde la vista **Día** del calendario.

**Con el teclado** es más rápido (lo recuerda el **?** de la ventana): la fila marcada (con un borde de color) es la siguiente por puntuar.

- Pulsa **0**, **1**, **2** o **3** en el teclado para puntuarla. Se pasa sola a la fila siguiente.
- Las flechas **↑** y **↓** cambian de fila.
- La tecla **+** añade una repetición al ejercicio marcado.

**Añadir ejercicios** (se abre esta si el día está vacío): marca los bloques o ejercicios y pulsa **Añadir al día** (o **Añadir a la sesión**, si hay sesiones). Se añaden solo a ese día (y solo a la sesión abierta, si hay sesiones). Antes de añadirlos, en **Orden** (a la derecha de la lista; debajo, en pantallas estrechas) ves lo que ya tiene la sesión y, al final, lo que has marcado (como «Nuevo»): colócalo con ↑ ↓ donde quieras. Después se vuelve sola a la pestaña de puntuar.

**Observaciones.** Arriba, antes de las pestañas y de la lista de ejercicios, hay un cuadro para escribir **observaciones** de la sesión (cómo ha ido, incidencias, qué cambiar la próxima vez). Si el día no tiene sesión, son **observaciones del día**. Se guardan solas mientras escribes; para quitarlas, borra el texto. Se ven:

- en el **calendario**: en la vista de semana, el principio del texto debajo de los ejercicios; en la de mes, un ✎ (pon el ratón encima para leerlas); en la de día, completas, con un botón **Observaciones…** para cambiarlas;
- en la pestaña **Sesiones**, debajo de cada sesión;
- en el **informe de pautas**, en el apartado **Observaciones de las sesiones**.

Si anulas una sesión con observaciones, no se pierden: pasan a «Sin sesión» de ese día, como sus puntuaciones.

## Sesiones: ejercicios y puntuaciones de cada sesión {#sesiones}

Cada **sesión** tiene sus propios ejercicios y sus propias puntuaciones. Si un día el paciente no tiene sesión programada, sus ejercicios se puntúan igual, en **Sin sesión**. Así, si un paciente viene dos veces el mismo día, cada visita tiene su puntuación, aunque haga los mismos bloques.

**Qué ejercicios tiene cada sesión.** Los de sus pautas. Una pauta puede ser para:

- **Todas** las sesiones (lo normal): sale en cada sesión y también los días sin sesión.
- **Unas sesiones concretas**: una o varias sesiones, o las sesiones de una serie (por ejemplo, «los martes y jueves a las 10:00»: sale solo en esas, aunque luego cambies la serie a partir de un día).
- **Ninguna**: el ejercicio queda **sin sesión**: se puntúa aparte de las sesiones, en **Sin sesión**.

Se elige en **En qué sesión** al asignar o al editar la pauta: es la lista de la derecha, con las sesiones de las fechas de la pauta. Marca **Todas**, o desmárcala y marca las que quieras (o pulsa **Ninguna**). Por ejemplo: a las 10:00 trabaja el bloque A y a las 17:00 el bloque B; asigna el A «solo en sus sesiones de las 10:00» y el B «solo en sus sesiones de las 17:00». Lo que añadas o quites desde la ventana de un día vale solo para esa sesión de ese día.

**En la ventana del día**, arriba salen sus sesiones: **Sesión 10:00–10:45** («3 de 9 puntuados»), **Sesión 17:00–17:45**… Pulsa una para puntuarla. **+ Sesión** programa otra sesión ese día y vuelve a la ventana con ella abierta. Desde la pestaña **Sesiones** de la ficha, **Puntuar** abre directamente la puntuación de esa sesión.

**Programar la primera sesión de un día que ya tiene ejercicios.** La aplicación pregunta qué hacer con los ejercicios sin sesión de ese día:

- **Crear sesión vacía**: la sesión empieza sin ejercicios; los que había siguen en **Sin sesión**, con sus puntuaciones.
- **Crear sesión copiando ejercicios**: la sesión tiene los mismos ejercicios, para puntuarlos aparte; los de **Sin sesión** siguen como estaban.
- **Crear sesión y asignar ejercicios existentes**: los ejercicios (y sus puntuaciones) pasan a la sesión.

Con **No programar la sesión** no se programa. Si es una sesión que se repite cada semana, se pregunta una sola vez para todos sus días.

**Anular una sesión con ejercicios.** Antes de anularla se avisa de cuántos ejercicios tiene y, sobre todo, si tiene puntuaciones. Las puntuaciones no se pierden: pasan a **Sin sesión** de ese día, con sus ejercicios. Si la mueves a otro día, también pasan a **Sin sesión** en el día en que se hicieron.

**En el calendario, el resumen y los informes**, la puntuación de un ejercicio en un día es la **media de todas sus sesiones** (y repeticiones). En el calendario, «N sin puntuar» cuenta cada sesión. En el detalle por días del informe de pautas, cada sesión sale por separado.

Las puntuaciones se guardan al momento. Cierra la ventana con **Cerrar**, la **×** o la tecla Esc.

## Resumen {#resumen}

En la pestaña **Calendario**, pulsa **Resumen** para ver la evolución del paciente en un periodo.

- **Día / Semana / Mes / Intervalo**: el periodo. Con **Intervalo** eliges las fechas y pulsas **Aplicar**.
- **Buscar**: para ver solo algunos bloques o ejercicios.

Hay tres formas de verlo:

- **Lista**: una fila por ejercicio, agrupados por bloque, con los días previstos, los días puntuados y la media. Si hay ejercicios con varias repeticiones, marca **Ver cada repetición** para ver una fila por repetición.
- **Puntos**: una fila por ejercicio y una columna por día, con un punto del color de la puntuación. Los ejercicios con varias repeticiones tienen subfilas «Rep. 1», «Rep. 2»…
- **Líneas**: la media de cada día en una gráfica. Puedes verla **Por ejercicio** (una línea por ejercicio), **Por bloque** (una línea por bloque) o **Media del día** (una sola línea). Pulsa un nombre de la leyenda para ocultar o mostrar su línea. Necesita un periodo de más de un día.

> **Consejo:** pasa el ratón por encima de un punto para ver el ejercicio, la fecha y la puntuación exacta.

## Planes en casa del paciente {#plan-en-casa}

La pestaña **Plan en casa** tiene la lista de **planes en casa** del paciente: los ejercicios que tiene que hacer en casa, con sus fechas. No tiene que ver con las pautas ni con las puntuaciones de la clínica.

**La lista de planes** muestra, para cada plan, su nombre, si está **en curso**, es **próximo** o ya ha **terminado**, cuándo empieza y termina, cuánto dura y qué contiene. Para encontrar uno:

- **Buscar por nombre del plan**: escribe parte del nombre.
- **Entre … y …**: los planes que tocan ese intervalo de fechas.
- **Mes** y **año**: los planes que pasan por ese mes o ese año (o por ese mes de ese año, si eliges los dos).
- **Quitar filtros** vuelve a mostrarlos todos.

En cada fila: **Editar plan**, **Exportar a PDF** y, en el **⋯**, **Eliminar plan…**.

**Crear un plan.** Pulsa **Nuevo plan** (vacío) o **Usar una plantilla…** (con los ejercicios de una plantilla; ver [Plantillas](#plantillas)).

**Dentro de un plan** ves arriba su **nombre** y sus **notas u observaciones** (indicaciones generales para el paciente o la familia, que salen en el PDF). Justo encima de los ejercicios están sus fechas:

- **Empieza**: el primer día del plan.
- **Duración**: cuánto dura, en **días**, **semanas** o **meses** (elige la unidad en el desplegable). Al cambiar de unidad, el número se ajusta para que dure parecido (2 semanas pasan a 14 días).
- **Termina**: se calcula sola con la duración. Puedes cambiarla a mano (por ejemplo, para alargarlo por unas vacaciones) sin que cambie la duración ni los ejercicios; **Recalcular** vuelve a la fecha calculada. Su **?** lo explica.

Todo se guarda solo. Debajo están los ejercicios:

- **A elegir**: ejercicios sin día fijo, que el paciente hace cuando quiera durante el plan.
- **Las semanas**, de lunes a domingo, con la fecha de cada día. Si el plan empieza o termina a mitad de semana, los días que quedan fuera salen en gris («Fuera del plan»).

**Añadir ejercicios.** Pulsa **+ Añadir** en un día (o en «A elegir»):

1. Marca bloques o ejercicios de la biblioteca, o escribe un **ejercicio a mano** si no está en la biblioteca.
2. En **Orden**, a la derecha, ves lo que ya tiene ese día (o «A elegir») y, al final, lo que has marcado: colócalo con ↑ ↓ donde quieras. (Lo escrito a mano se añade al final.)
3. Escribe **notas** si quieres (repeticiones, cómo hacerlo, material…).
4. Si quieres, marca otros días del plan para añadirlo a la vez (en esos días, lo nuevo va al final).
5. Pulsa **Añadir**.

En las **plantillas** se añade igual.

**Cambiar un día.** Dentro de cada día:

- **✎** cambia las notas de un ejercicio o de un bloque.
- **×** quita ese ejercicio o bloque.
- **Editar** abre el día entero para reordenar (↑ ↓), cambiar notas, quitar, añadir (**+ Añadir…**) o vaciarlo (**Vaciar el día…**).

**Botones de arriba:**

- **← Planes en casa**: vuelve a la lista (también vale el botón **Atrás**).
- **Exportar a PDF**: crea el PDF para la familia, con las notas, los ejercicios «a elegir» y cada día con su fecha y una casilla por ejercicio. Ver [Informes](#informes).
- **Guardar como plantilla…**: copia el plan, sin fechas, para usarlo con otros pacientes.
- **Duplicar**: crea otro plan igual que empieza justo cuando termina este (por ejemplo, para repetir el mismo plan el mes siguiente). Después puedes cambiarle el nombre y las fechas.
- En el **⋯**: **Vaciar el plan…** quita todos los ejercicios, pero conserva el plan; **Eliminar el plan…** lo borra (los PDF que ya hayas sacado no se borran).

> **Consejo:** si cambias la fecha de inicio a otra semana, los ejercicios se mueven con el plan (mismo día de la semana). Si algún ejercicio queda fuera de las nuevas fechas, la aplicación te avisa antes de quitarlo.

## Plantillas {#plantillas}

Una **plantilla** es un plan en casa sin fechas: de lunes a domingo, con una duración en días, semanas o meses. Sirve para no repetir el mismo plan a mano en cada paciente. Las encuentras en **Biblioteca ▾ → Plantillas casa**.

En una plantilla los días se ven por semanas de lunes a domingo: una de **10 días** se ve en 2 semanas y una de **1 mes**, en 4 semanas (cada mes cuenta como 4 semanas).

**Crear una plantilla.** Hay dos formas:

- Desde cero: **Nueva plantilla**. Escribe el nombre y añade los ejercicios de cada día.
- Desde un paciente: abre uno de sus planes en casa y pulsa **Guardar como plantilla…**. Se guardan los ejercicios de cada día, los «a elegir» y las notas.

**Usar una plantilla.** Hay dos formas:

- Desde la plantilla: **Usar con pacientes…**, para uno o varios pacientes a la vez.
- Desde el paciente: **Usar una plantilla…** en su lista de planes en casa.

En los dos casos se crea un **plan nuevo** para cada paciente: eliges su **nombre**, cuándo **empieza** y cuánto **dura** (en días, semanas o meses; propone la de la plantilla y te dice cuándo termina). Si dura más que la plantilla, la plantilla se repite. Las notas y los ejercicios «a elegir» de la plantilla pasan al plan.

**Editar una plantilla.** Pulsa **Editar**: puedes cambiar el nombre, la duración, las notas, los ejercicios «a elegir» y el contenido de cada día, igual que en un plan en casa. Los cambios se guardan al momento.

> **Importante:** cambiar una plantilla **no** cambia los planes de los pacientes que ya la usan: cada paciente tiene su propia copia.

**Pacientes (N)** muestra qué pacientes tienen un plan en curso o próximo creado con esta plantilla, y te deja abrirlo directamente.

## Progreso: evaluación inicial e hitos {#progreso}

En la pestaña **Progreso ▾** de la ficha hay dos apartados que funcionan igual:

- **Evaluación inicial**: cómo estaba el paciente al empezar, y las evaluaciones que hagas después.
- **Hitos**: logros o momentos importantes, con su fecha.

Arriba ves la lista, con la más reciente primero. Para añadir una, pulsa **Nueva evaluación…** o **Nuevo hito…**, elige la **fecha**, escribe el texto, añade **fotos** si quieres y pulsa **Añadir evaluación** o **Añadir hito**. (Si todavía no hay ninguna, el formulario ya sale abierto.)

- **Buscar** filtra por el texto.
- **Editar** está en cada fila, y **Eliminar** en su **⋯**.
- Las fotos salen en miniatura en su fila. Pulsa una para verla en grande; con las flechas pasas de una a otra.

## Informes y PDF {#informes}

La aplicación crea dos tipos de PDF:

- **Informe de pautas**: los ejercicios de las pautas y sus puntuaciones en un periodo. Lleva arriba los datos de tu clínica, un **resumen por ejercicio** (días previstos, puntuados y media), una gráfica de la evolución y, si marcas **Incluir el detalle de cada día**, una tabla día a día. Si marcas **Incluir las observaciones de las sesiones** (marcado de entrada), lleva también las observaciones que escribiste al puntuar en ese periodo. No incluye teléfono, email ni las observaciones de la ficha del paciente.
- **Plan en casa**: el plan para la familia, con la cabecera de tu clínica, el nombre y las fechas del plan, sus notas, los ejercicios «a elegir», cada día con una casilla por ejercicio y tu firma.

**Dónde se crean:**

- Pestaña **Informes** → **Generar informe de pautas…**.
- **Calendario** o **Resumen** → **Generar informe de pautas…**, con el periodo que estás viendo ya puesto.
- **Pacientes** → marca varios y pulsa **Informe de pautas… (N)**, para hacer uno de cada paciente.
- **Plan en casa** → **Exportar a PDF**, en la lista de planes o dentro de un plan.

> **Consejo:** sin el detalle de cada día, el informe de pautas suele caber en una sola página: es lo más cómodo para entregar a la familia o a otro profesional.

**Buscar informes.** En la pestaña **Informes** del paciente puedes buscar por el nombre del informe, el nombre del archivo o la fecha, y ver solo los generados **entre dos fechas**, en un **mes** o en un **año**.

**Dónde se guardan.** Al generar un PDF se abre la ventana **Guardar como** del ordenador para que elijas carpeta y nombre. La próxima vez empieza en la misma carpeta. Si haces informes de varios pacientes a la vez, eliges la carpeta una sola vez.

> **Consejo:** la ventana de «Guardar como» a veces aparece detrás del navegador. Si no la ves, busca en la barra de tareas o en el Dock.

**La pestaña Informes** lista todos los PDF del paciente, con un filtro **Todos / Informes de pautas / Planes en casa**:

- **Abrir**: lo abre con el programa de PDF del ordenador.
- **Mostrar en la carpeta**: abre la carpeta donde está.
- **Quitar de la lista** (en el **⋯**): lo quita de la lista, pero **no borra el archivo**.

Si mueves, renombras o borras un PDF fuera de la aplicación, en la lista sale «No se encuentra el archivo».

> **Importante:** los PDF contienen datos de salud. Guárdalos en un sitio seguro y compártelos con cuidado.

## Agenda y sesiones {#agenda}

En **Agenda** (menú de arriba) están las sesiones de todos los pacientes en una cuadrícula con las horas del día.

- **Día**, **Semana** o **Mes**: cómo se ve. Pulsa el nombre (o, en el mes, el número) de un día para ver solo ese día. En el mes, cada día muestra sus primeras sesiones (con **+N más** si hay más); pulsar un día programa una sesión ese día.
- **Anterior**, **Hoy** y **Siguiente**, o el calendario pequeño, para ir a otra fecha.
- **Programar una sesión**: pulsa un hueco libre de la cuadrícula (la sesión empieza a esa hora) o el botón **Nueva sesión**. Elige el paciente, el día, la hora y la duración, y pulsa **Programar sesión**.
- **Cambiar o anular una sesión**: púlsala. En su ventana también está **Ver ficha**.
- Las sesiones que se solapan se ven una al lado de la otra. La línea roja marca la hora actual.

**Colores.** Cada sesión puede tener un color (los mismos que Google Calendar, así se ven igual allí). En los datos del paciente (**Editar datos del paciente**) eliges el **color de sus sesiones**: es el que llevan por defecto las sesiones nuevas de ese paciente. Al cambiarlo, la aplicación pregunta si cambiar también sus próximas sesiones o solo las nuevas. En la ventana de cada sesión (y de cada serie) se puede poner otro color.

**Huecos ocupados.** Al elegir día y hora, la ventana avisa si ese hueco ya está ocupado por otra sesión (o por algo de tu Google Calendar, si está conectado, ver [Google Calendar](#google-calendar)). Puedes programarla igualmente: la aplicación te lo pregunta antes.

**Sesiones que se repiten cada semana.** En una sesión nueva, marca **Se repite cada semana**, elige los días de la semana y hasta qué fecha (o **Sin fecha de fin**). La aplicación programa de una vez todas esas sesiones y te dice cuántas son y si alguna se solapa. Las sesiones sin fecha de fin se crean para los próximos 6 meses y se van añadiendo solas.

Al **cambiar** o **anular** una sesión que se repite, la aplicación pregunta:

- **Solo esta sesión**: por ejemplo, para moverla a otra hora. Las demás no cambian.
- **Esta y las siguientes**: por ejemplo, porque a partir de esa semana viene a otra hora o en otro día. Si la mueves a otro día de la semana (de jueves a viernes), las siguientes también pasan a ese día. Las sesiones anteriores no cambian.

**En la ficha del paciente**, la pestaña **Sesiones** muestra:

- **Próximas**, **Pasadas** o **Todas**: con estos botones eliges qué sesiones ver. Se pueden buscar **entre dos fechas**, por **mes** y por **año** (**Quitar filtros** vuelve a verlas todas).
- Cada sesión dice si **no tiene ejercicios**, cuántos tiene **sin puntuar** o **cuántos están puntuados** (en verde, si están todos).
- **Puntuar** abre directamente la puntuación de esa sesión, sin pasar por el calendario. Si todavía no tiene ejercicios, se abre en **Añadir ejercicios** para ponérselos ahí mismo. **Cambiar…** abre la sesión.
- **↻ Se repiten (N)**: si tiene sesiones que se repiten cada semana, este botón muestra sus series, una por línea. **Cambiar…** cambia días, hora, duración o fecha de fin a partir del día que elijas. **Terminar la serie…** (en el **⋯**) anula las sesiones de la serie desde mañana (las anteriores se quedan). Sus sesiones salen también en **Próximas**, marcadas con ↻.
- **Nueva sesión** (ya con el paciente elegido) y **Ver en la agenda**.

**Horario de la agenda.** En **Ajustes → Agenda** eliges desde qué hora y hasta qué hora se ve la cuadrícula, qué días de la semana salen (un día sin marcar sale igualmente si tiene alguna sesión) y cuánto duran las sesiones nuevas.

> **Consejo:** si anulas o cambias sesiones por error, pulsa **Deshacer** en el aviso de abajo.

## Google Calendar {#google-calendar}

La agenda se puede sincronizar con tu **Google Calendar**, en los dos sentidos:

- **De la aplicación a Google**: las sesiones se copian en un calendario nuevo de tu cuenta llamado **Fisioterapia · sesiones** (lo crea la aplicación). Cada sesión que programes, cambies o anules aquí cambia allí al poco tiempo, con su color. Así las ves también en el móvil.
- **De Google a la aplicación**: si en Google Calendar mueves o borras una de esas sesiones, también cambia en la aplicación (sale un aviso con **Deshacer**). Si la misma sesión se ha cambiado en los dos sitios a la vez, se queda la versión de la aplicación.
- **Tus otros calendarios** (por ejemplo, el personal): de ellos solo se trae qué horas están **ocupadas**, sin el título de los eventos. En la agenda salen como zonas rayadas («Ocupado») y la ventana de la sesión avisa si la programas encima. En **Ajustes → Agenda → Elegir calendarios…** decides cuáles se usan (al principio, tu calendario principal).

La aplicación sincroniza sola al abrirla, cada pocos minutos mientras está abierta y poco después de cada cambio en las sesiones. Arriba de la agenda ves cómo va («al día», «sincronizando…» o un error) y el botón **⟳** para sincronizar en ese momento. Hace falta conexión a internet; sin ella, la agenda funciona igual y se pone al día cuando vuelva la conexión.

**Qué se ve en Google.** En **Ajustes → Agenda → Qué se ve en Google** eliges el título de los eventos: el **nombre y apellidos** del paciente (y la nota de la sesión), **solo las iniciales** o **solo «Sesión»**. Los datos de los pacientes son datos de salud: si prefieres que su nombre no salga de tu ordenador, usa las iniciales o «Sesión».

**Configurarlo (solo la primera vez).** Google pide que cada aplicación tenga su propio «ID de cliente». Se crea gratis con tu cuenta de Google, en unos 10 minutos. En **Ajustes → Agenda** están los pasos:

1. Entra en **console.cloud.google.com** con tu cuenta de Google y crea un proyecto (por ejemplo, «Fisioterapia»).
2. Busca **Google Calendar API**, ábrela y pulsa **Habilitar**.
3. En **Pantalla de consentimiento de OAuth** (o «Google Auth Platform»), pulsa **Comenzar**: nombre «Fisioterapia», tu correo y público **Externo**.
4. En **Público**, pulsa **Publicar aplicación** para que quede «En producción». Si se queda «En prueba», Google la desconecta cada 7 días.
5. En **Clientes** (o «Credenciales»), crea un cliente de tipo **App de escritorio**.
6. Copia el **ID de cliente** y el **secreto del cliente** en Ajustes → Agenda (o carga el archivo JSON que te deja descargar Google) y pulsa **Guardar**.
7. Pulsa **Conectar con Google…**: se abre una pestaña de Google donde eliges tu cuenta y das permiso para ver y editar tus calendarios. Si Google avisa de que **no ha verificado la aplicación**, pulsa **Configuración avanzada** y después **Ir a Fisioterapia**: es la aplicación que acabas de crear tú. Al terminar, cierra esa pestaña y vuelve a la aplicación.

El ID de cliente y el permiso se guardan solo en tu ordenador, fuera de la carpeta de datos (no van en las copias de seguridad). Cada carpeta de datos tiene su propio calendario en Google; la casilla **Sincronizar la agenda de esta carpeta de datos** la activa o la desactiva.

**Desconectar.** **Desconectar de Google** retira el permiso. Lo que ya está en Google Calendar se queda allí; si no lo quieres, borra el calendario «Fisioterapia · sesiones» desde Google Calendar.

> **Importante:** si borras el calendario «Fisioterapia · sesiones» en Google, la aplicación crea otro y vuelve a copiar en él las sesiones desde hace un mes.

## Ejercicios {#ejercicios}

En **Biblioteca ▾ → Ejercicios** está la biblioteca de todos los ejercicios.

- **Nuevo ejercicio…**: escribe el nombre y pulsa **Añadir** (o Intro). No deja repetir un nombre que ya existe.
- **Buscar ejercicio**: filtra la lista.

El botón **⋯** de cada ejercicio tiene estas opciones:

- **Renombrar…**: cambia el nombre en toda la aplicación (pautas, planes, plantillas e informes de pautas).
- **Duplicar**: crea una copia con el mismo nombre y un número, por ejemplo para hacer una variante.
- **Eliminar…**: lo borra de la biblioteca y de todas las pautas y puntuaciones.

La etiqueta **En N bloques** indica que el ejercicio forma parte de algún bloque. Si lo renombras o eliminas, la aplicación te avisa de los bloques y plantillas afectados.

**Exportar…** e **Importar…** guardan la biblioteca en un archivo o la cargan desde uno. Ver [Exportar e importar ejercicios y bloques](#exportar-importar).

## Bloques {#bloques}

En **Biblioteca ▾ → Bloques** están los grupos de ejercicios.

- **Nuevo bloque**: ponle nombre y, si quieres, un **nivel** (A, B, C…). Marca sus ejercicios y ordénalos con las flechas en «Orden de ejecución».
- Si falta un ejercicio, escríbelo en **¿Falta alguno?** y pulsa **Crear y añadir**: se crea en la biblioteca y queda marcado en el bloque.
- **Buscar** y el filtro de **nivel** ayudan a encontrar un bloque.
- **Mostrar los ejercicios de cada bloque** enseña u oculta la lista de cada uno.
- **Editar** está en cada bloque, y **Eliminar bloque…** en su **⋯**. Con **Mostrar los ejercicios de cada bloque**, sus ejercicios salen en columnas debajo.
- **Exportar…** e **Importar…**: guardan los ejercicios y bloques en un archivo, o los cargan desde uno (por ejemplo, el catálogo **bloques_dmi.json**). Ver [Exportar e importar ejercicios y bloques](#exportar-importar).

## Exportar e importar ejercicios y bloques {#exportar-importar}

La biblioteca (ejercicios y bloques) se puede guardar en un archivo y cargar en otra carpeta de datos o en otro ordenador. Los botones **Exportar…** e **Importar…** están en **Biblioteca ▾ → Ejercicios**, en **Biblioteca ▾ → Bloques** y en **Ajustes → Datos**.

**Exportar.** Marca qué quieres guardar: **Bloques**, **Ejercicios** o los dos. Los bloques llevan siempre sus ejercicios; si marcas también **Ejercicios**, van además los que no están en ningún bloque. Pulsa **Exportar…** y elige dónde guardar el archivo (por ejemplo, `Ejercicios_y_bloques_2026-10-27.json`). El archivo no lleva nada de los pacientes.

**Importar.** Elige un archivo exportado (o un catálogo de bloques, como **bloques_dmi.json**). Antes de importar sale un resumen con cuántos bloques y ejercicios son nuevos y cuántos ya existen. Pulsa **Importar** para añadirlos; justo después puedes pulsar **Deshacer**.

Si la carpeta de datos **ya tiene ejercicios o bloques**, el resumen lo avisa y el botón dice **Combinar e importar**. Al combinar:

- No se borra ni se cambia nada de lo que ya tienes.
- Un ejercicio que ya existe (el mismo, o con el mismo nombre aunque cambien mayúsculas o tildes) no se duplica: los bloques nuevos usan el que ya tienes.
- Un bloque que ya existe (el mismo, o con el mismo nombre y nivel) no se duplica.

**Empezar una base de datos nueva solo con la biblioteca.** Por ejemplo, para otra clínica o para hacer pruebas:

1. En la carpeta de datos actual, pulsa **Exportar…** con **Bloques** y **Ejercicios** marcados.
2. En **Ajustes → Datos**, pulsa **Elegir otra carpeta…** y elige una carpeta nueva y vacía.
3. Pulsa **Importar…** y elige el archivo del paso 1.

## Ajustes {#ajustes}

**Ajustes** tiene cinco pestañas: **Personalizar**, **Agenda** (horario de la agenda y Google Calendar, ver [Agenda](#agenda) y [Google Calendar](#google-calendar)), **Copias de seguridad**, **Datos** y **Novedades**.

En **Personalizar**:

- **Nombre de la clínica**, **profesional responsable** y **nº de colegiado**: salen en la barra de arriba y en la cabecera de los PDF (informes de pautas y planes en casa).
- **Logo**: sale en la cabecera de los PDF. La **firma** (en PNG; mejor con fondo transparente) sale en los PDF del plan en casa.
- **Pestañas de la ficha del paciente**: ordénalas con ↑ ↓. La ficha de cada paciente se abre en la primera. **Volver al orden de siempre** deja Pautas · Sesiones · Calendario · Plan en casa · Progreso · Informes.
- **Modo de visualización**: claro u oscuro. También se cambia con el botón de la luna o el sol de la barra de arriba.

## Copias de seguridad {#copias}

Los datos tienen información de salud: las copias de seguridad son importantes. En **Ajustes → Copias de seguridad**:

- **Hacer copias automáticas**: con esto activado, la aplicación hace una copia sola mientras está abierta: la primera vez que la abres cada día (o con la frecuencia que elijas) y después cada 15 minutos comprueba si toca.
- **Frecuencia** y **Conservar las últimas N**: cada cuánto se hacen y cuántas automáticas se guardan. Las más antiguas se borran solas.
- **Crear copia ahora**: hace una copia en ese momento. Estas copias manuales no se borran nunca solas.
- **Copias guardadas**: la lista de copias. **Restaurar** sustituye los datos actuales por los de esa copia; antes, la aplicación guarda una copia de los datos actuales por si acaso.

Mientras se hace una copia sale un aviso «Haciendo copia de seguridad…»: espera unos segundos y no cierres la aplicación.

> **Importante:** las copias se guardan en la misma carpeta de datos, en el mismo disco. De vez en cuando, copia la carpeta **copias** a un USB o a iCloud por si falla el disco.

## Datos {#datos}

En **Ajustes → Datos**:

- **Carpeta de datos**: dónde están la base de datos, las fotos y las copias. Con **Elegir otra carpeta…** puedes usar otra; cada carpeta es un juego de datos independiente.
- **Ejercicios y bloques**: **Exportar…** e **Importar…** la biblioteca. Ver [Exportar e importar ejercicios y bloques](#exportar-importar).
- **Borrar todo**: elimina pacientes, ejercicios, pautas, puntuaciones, planes y sesiones. Los ajustes se conservan. Para confirmarlo hay que escribir la palabra **BORRAR**.

> **Importante:** después de **Borrar todo** solo tienes unos segundos para pulsar **Deshacer**; luego, solo se recupera restaurando una copia de seguridad.

## Novedades y actualizaciones {#novedades}

Cuando instalas una versión nueva, la primera vez que abres la aplicación sale arriba un aviso con **Ver novedades** y **Entendido**. Todas las novedades están en **Ajustes → Novedades**.

El número de la versión instalada aparece en la barra de arriba, a la derecha de todo.

Al actualizar, la aplicación hace sola una copia de seguridad de tus datos si la versión nueva necesita cambiarlos. Esa copia empieza por **copia-previa-actualizacion** y no se borra sola.

## Si algo no va bien {#problemas}

**El navegador dice que no puede conectar.** La aplicación está cerrada (o la ventana negra se cerró). Haz doble clic en Fisioterapia.command o Fisioterapia.bat.

**Sale un aviso de que sigue abierta otra versión de Fisioterapia.** Cierra esa versión: pulsa **Salir** en ella, o cierra su ventana negra. Si no la encuentras, reinicia el ordenador. Después vuelve a abrir la aplicación.

**Sale un aviso de que otro programa está usando el puerto.** Reinicia el ordenador y vuelve a abrir la aplicación. Si sigue pasando, avisa a quien te la instaló.

**No veo la ventana de «Guardar como» o «Elegir carpeta».** Suele estar detrás del navegador. Búscala en el Dock o en la barra de tareas.

**No encuentro a un paciente.** Puede estar archivado: en **Pacientes**, cambia el filtro a **Archivados** o **Todos**.

**He borrado algo por error.** Si todavía ves el aviso de abajo, pulsa **Deshacer** (o Cmd+Z / Ctrl+Z). Si ya no está, no hagas más cambios. Ve a **Ajustes → Copias de seguridad** y restaura la copia más reciente anterior al error. Antes de restaurar, la aplicación guarda una copia de lo que hay ahora.

**La ventana negra dice que los datos son de una versión más reciente.** Estás abriendo una versión antigua de la aplicación. Usa la última que te hayan enviado; la aplicación no abre esos datos para no estropearlos.

**Sale «Los datos se han modificado desde otra ventana».** Tenías la aplicación abierta en dos pestañas y cambiaste algo en las dos. La pestaña se recarga sola para no pisar los datos; el último cambio que hiciste en ella no se ha guardado, así que repítelo. Mejor usar una sola pestaña.

**Google Calendar dice «no se ha podido sincronizar».** Pulsa el aviso para ir a Ajustes → Agenda y ver el motivo. Si no hay internet, se pondrá al día sola al volver la conexión. Si dice que Google ha cerrado la conexión, pulsa **Conectar con Google…** otra vez (pasa si se retiró el permiso o si la aplicación de Google Cloud se quedó «En prueba», ver [Google Calendar](#google-calendar)).

**Una sesión cambiada en Google Calendar no cambia en la aplicación.** Solo se sincronizan las sesiones del calendario «Fisioterapia · sesiones». Lo que crees directamente en Google no pasa a la aplicación como sesión: si está en uno de los calendarios elegidos, sale como «Ocupado». No crees eventos tuyos en «Fisioterapia · sesiones»: ese calendario es solo para las sesiones de la aplicación.
