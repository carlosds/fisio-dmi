# Análisis de usabilidad y UI/UX

Revisión hecha el 29 de octubre de 2026 sobre la versión en desarrollo de la 0.0.7, con datos realistas (los 95 bloques del catálogo DMI, 6 pacientes, sesiones de la semana, puntuaciones, un plan en casa e informes), a 1440 px (escritorio) y a 820 px (tablet), recorriendo las tareas del día a día.

**Estado:** ✅ hecho en la 0.0.7 · ⏳ pendiente (siguiente paquete).

## Conclusión

La aplicación cubre bien el trabajo diario y tiene muy buenos detalles: «Puntuar hoy» desde la lista, puntuar con el teclado, «Deshacer», el aviso «✓ Guardado», el botón Atrás que funciona y la ayuda «?» en cada pantalla. Los problemas están en cuatro sitios: **llegar a puntuar desde la agenda**, el **ruido de «sin puntuar»** en días sin sesión, **demasiados conceptos y caminos** para lo mismo y **pantallas cargadas** de filtros y botones rojos.

## Problemas encontrados y propuestas

### 1. Desde la agenda no se puede puntuar ⏳
Al pulsar una sesión en la agenda se abre la ventana de cambiar hora, duración y color, sin el estado de sus ejercicios ni sus observaciones. Para puntuar hay que ir a «Ver calendario» y pulsar el día: 3 clics y 2 cambios de pantalla.
- ⏳ La ventana de la sesión con su estado («4 ejercicios, 2 puntuados»), sus observaciones y un botón **Puntuar**; o una pantalla **Hoy** con las sesiones del día.

### 2. Ruido de «sin puntuar» en días sin sesión ⏳
Al asignar, los días vienen todos marcados: una pauta normal toca los 7 días aunque el paciente venga uno o dos. Por eso salen badges de «sin puntuar» en todos los días de la semana, «0 de N puntuados» en casi todas las casillas del mes y «Puntuar hoy» destacado en todos los pacientes. Lo pendiente de verdad queda escondido.
- ⏳ Una opción de días **«En sus sesiones»** (por defecto si el paciente tiene sesiones) y «sin puntuar» solo en días con sesión.
- ✅ Quitar de la cabecera de la ficha «7 días por semana (Lun…Dom)».

### 3. Demasiados conceptos y caminos para lo mismo ⏳
- Tres ventanas distintas para añadir ejercicios: Asignar (con fechas, duración, días y «En qué sesión», y sin panel de orden), Añadir a la sesión y Añadir al plan.
- El concepto «sin sesión» y el diálogo de 3 opciones al crear la primera sesión de un día con ejercicios.
- Las sesiones se ven en tres sitios (Agenda, pestaña Sesiones, bordes del Calendario).
- El Resumen vive dentro de Calendario con su propia navegación de periodo.
- ⏳ Un único componente de «añadir ejercicios» (lista a la izquierda, orden a la derecha) en los tres sitios.
- ⏳ Al crear la sesión, asignarle por defecto los ejercicios sin sesión, con «Deshacer», en vez de preguntar.
- ⏳ Que Resumen y Calendario compartan el periodo.

### 4. Navegación entre pacientes y dentro de la ficha
- ✅ Buscador de pacientes en la barra superior, desde cualquier pantalla (⌘K / Ctrl+K).
- ⏳ Una pestaña de entrada **«Resumen del paciente»** (próxima y última sesión con sus observaciones, pautas vigentes, plan en casa en curso, último hito), en vez de abrir en «Pautas».
- ✅ Reordenar las pestañas: el orden se elige en Ajustes › Personalizar y la ficha se abre en la primera. Por defecto: Pautas · Sesiones · Calendario · Plan en casa · Progreso · Informes.
- ⏳ Sacar «Evaluación inicial» e «Hitos» del desplegable.

### 5. Densidad visual y acciones peligrosas a la vista
- ✅ **Filtros de fecha plegados** tras «Filtrar por fecha» en Pautas, Sesiones, Planes en casa e Informes (abiertos si hay alguno puesto, y se recuerda si los abriste).
- ✅ **Acciones destructivas en el menú «⋯»**: quitar todas las pautas, eliminar pauta, quitar un ejercicio de la sesión y quitar todos, anular sesión, terminar serie, vaciar y eliminar plan, eliminar bloque, plantilla, hito y evaluación, quitar un informe de la lista. «Vaciar» un día del plan pasa a «Editar» el día.
- ✅ **Lista de pacientes más densa**: una fila por paciente en columnas alineadas con la cabecera (paciente, última sesión, próxima sesión, acciones), la casilla de marcar todos en la cabecera y el filtro «Con sesiones» en la fila del buscador. De 4 líneas por paciente a 2.
- ✅ Los atajos de teclado de la ventana del día pasan al «?».
- ⏳ Destacar o filtrar los pacientes **con sesión hoy**.

### 6. Inconsistencias
- ✅ **Bloques** (y ejercicios) en una sola columna: la cabecera de orden se lee de arriba abajo. Los ejercicios de cada bloque, en columnas debajo.
- ✅ Acciones de cada fila más homogéneas (acción principal visible y lo demás en «⋯»).
- ⏳ «Última sesión» sale del último día con puntuaciones y «Próxima sesión» de la agenda: unificar en sesiones.
- ⏳ El modo claro/oscuro está en la barra y otra vez en Ajustes.

### 7. Tablet (820 px) ⏳
La barra superior se parte en dos filas, la cabecera del paciente ocupa casi media pantalla y la vista Semana del calendario corta los nombres de los ejercicios.
- ⏳ Vista Día por defecto en pantallas estrechas, menú compacto y cabecera reducida.

## Tareas clave: ahora y con las propuestas

| Tarea | Antes | Con las propuestas |
|---|---|---|
| Puntuar la sesión de un paciente desde la agenda | 3 clics y 2 pantallas | 2 clics (sesión → Puntuar) ⏳ |
| Ver qué queda pendiente de puntuar | Mezclado con días sin sesión | Solo días con sesión ⏳ |
| Asignar un bloque para sus sesiones | 4 clics y 4 decisiones | 2 decisiones ⏳ |
| Crear la primera sesión de un día con ejercicios | Diálogo con 3 opciones | Sin pregunta, con «Deshacer» ⏳ |
| Cambiar de paciente estando en una ficha | Volver a la lista y buscar | Buscador en la barra ✅ |

## Siguiente paquete (por orden de impacto)

1. Ventana de la sesión con estado, observaciones y **Puntuar** (o pantalla **Hoy**).
2. Días **«En sus sesiones»** y «sin puntuar» solo en días con sesión.
3. Pestaña **«Resumen del paciente»** y reorganización de pestañas.
4. Filtro o realce de **pacientes con sesión hoy**.
5. Un solo componente de **añadir ejercicios**; simplificar «sin sesión».
6. **Modo tablet** para puntuar.
