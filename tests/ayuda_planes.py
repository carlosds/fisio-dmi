# Ayuda para las pruebas: crea un plan en casa (formato 0.0.5) desde la página.
# page.evaluate(PLAN_PRUEBA) define window.planPrueba(pid, inicio, semanas, items, abrir);
# items: [{dia, e, b, g, nota, ng, orden}] (dia 1 = lunes de la semana de inicio; dia 0 = «a elegir»).
PLAN_PRUEBA = """() => { window.planPrueba = (pid, inicio, semanas, items, abrir = true, nombre = 'Plan de prueba') => {
  const pl = { id: uid(), patientId: pid, nombre, inicio, semanas, fin: '', finManual: false, notas: '', creado: todayIso(), plantillaId: '',
    items: items.map((x, k) => ({ id: uid(), dia: x.dia, exerciseId: x.e, bloqueId: x.b || '', orden: x.orden || k + 1, nota: x.nota || '', grupo: x.g || '', notaGrupo: x.ng || '' })) };
  pl.fin = finAutoPlan(pl); db.planes.push(pl);
  if (abrir){ if (ui.patientId !== pid || ui.view !== 'paciente') prepararPaciente(pid); ui.view = 'paciente'; ui.tabP = 'casa'; ui.planCasaId = pl.id; }
  render(); return pl.id; }; }"""
