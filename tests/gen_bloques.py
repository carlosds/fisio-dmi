import json, sys
LR = ["Derecha", "Izquierda"]
C5 = ["Por combinación", "Por los muslos", "Por debajo de las rodillas", "Por los tobillos", "Por 1 muslo / tobillo"]
C4 = ["Por combinación", "Por los muslos", "Por debajo de las rodillas", "Por los tobillos"]
def lr(prefijos): return [f"{p} – {d}" for p in prefijos for d in LR]
S = None  # bloque de un solo ejercicio

A = [
 ("Pivoteo supino 90°", LR), ("Flexión de cuello, con envoltura de tronco/brazos", S),
 ("180° por el tronco: flexión lateral del cuello", LR), ("Vibraciones contra la gravedad", ["Prono", "Supino", "Derecha", "Izquierda"]),
 ("Horizontal 180°", LR), ("Posición alta de rodillas tomando por el mentón o por pecho", S),
 ("Rolado por los tobillos: de decúbito supino a decúbito prono", LR),
 ("Decúbito supino a sentado a la altura del tronco medio/pelvis", LR),
 ("Decúbito supino a sentado con un brazo/45°", LR),
 ("Decúbito supino a sentado por pelvis de espalda a mi", LR),
 ("Extensión del tronco por abdomen bajo", S), ("Posición supina con las piernas alrededor del tronco 90°/180°", LR),
 ("Sentado sobre el antebrazo", ["Con apoyo intermitente", "Libre"]),
 ("Posición de cuatro puntos (balanceo) por los codos", S), ("Extensión rítmica de brazos en cuatro puntos", LR),
 ("Prono a cuatro puntos a sentado por pelvis", S), ("180° en posición vertical", LR),
 ("Supino a de pie el occipucio y los tobillos", S),
 ("Supino de pie por antebrazos y tobillos (envoltura del tronco antideslizante)", S),
 ("Posición alta de rodilla a de pie por antebrazos", LR),
 ("Prono a cuatro puntos, cuclillas a de pie por muslos / muslo y tobillo opuesto", S),
 ("De pie", ["Por los muslos", "Por debajo de las rodillas", "Por los tobillos"]),
 ("De pie, 20 toques aleatorios", S), ("Prono a de pie por abdomen y tobillos", S),
 ("De pie contra el tronco: tres movimientos", S), ("De pie sobre los muslos: tres movimientos", S),
 ("De pie entre las piernas", S),
 ("Caminar con los muslos", ["Por los muslos", "Por debajo de las rodillas", "Por los tobillos", "Por combinación", "Por 1 muslo / tobillo"]),
 ("Reacción de paso al halar hacia atrás", LR),
 ('Subir caja de 15 cm (6") como escalones para subir y bajar', LR),
 ("Pasos sobre panel de equilibrio", C5), ("Pasos a lo largo de la barra de equilibrio", C5),
 ('Entrar y salir en caja de 15 cm (6")', ["Por combinación", "Por los muslos", "Por debajo de las rodillas", "Por 1 muslo / tobillo"]),
 ("Subir rampa", C5), ("Pasos descendentes en rampa sobre el regazo", C5),
]
B = [
 ("Suaves pulsos horizontales de cabeza 45°", LR), ("Control de la cabeza mediante el mentón y el occipucio", S),
 ('Curvas en forma de "S"', S), ("Carga vertical inversa sobre la pelvis", S),
 ("Sentadillas en el aire por el tronco superior", S),
 ("Giro por la cabeza", lr(["Decúbito prono a supino", "De decúbito supino a decúbito prono"])),
 ("Inclinación suspendida 45° y 90°", ["Extensión", "Flexión", "Flexión lateral derecha", "Flexión lateral izquierda"]),
 ("Inclinación sobre el regazo por la pelvis", ["Extensión", "Flexión", "Flexión lateral derecha", "Flexión lateral izquierda"]),
 ("Rodillas contra el pecho: manteniendo una postura recta", S), ("Supino a sentado con el tronco en control", LR),
 ("Supino a sentado con el brazo y la pierna contraria", LR), ("Prono a 4 puntos para sentarse por los hombros", LR),
 ("Postura de 4 puntos sentado estabilizando los codos", LR),
 ("Supino a sentado a mitad del tronco con una pierna flexionada", S), ("Equilibrio sostenido sujeto a los tobillos", S),
 ("Gateo con el brazo y la pierna opuesta", S), ("Silla en el aire", S),
 ("Equilibrio sentado libre en un cuadrado pequeño y una pelota", S), ("Sentadilla isométrica contenida", S),
 ("De cuclillas a de pie por la mitad del tronco y los tobillos", S),
 ("Cuatro puntos a de pie", ["Por debajo de las rodillas", "Por los tobillos"]),
 ("De prono a posición alta de rodillas", lr(["De rodillas a de pie", "Bajar desde la posición de pie"])),
 ("Manos entrelazadas y manos juntas", ["De pie con manos entrelazadas", "Caminando con manos juntas"]),
 ("De pie/caminando con lazos antideslizantes alrededor de los muslos", S),
 ('Subir y bajar escaleras de 15 cm (6")', C5),
 ("Pasos con una pierna sostenida", lr(["Pierna de apoyo", "Pierna oscilante"])),
 ('Subir y pasar dos cajas cerradas de 15 cm (6")', C5), ("Tablero de ajedrez", C5), ("Los X Games", C5),
 ("Pasos en barras paralelas estrechas dobles", C4),
]
C = [
 ("Sincronización", LR), ("Oscilaciones suaves de la cabeza por el tronco en decúbito lateral", LR),
 ("Oscilaciones suaves del tronco por acción de la cabeza al sentarse", ["Izquierda + derecha", "Adelante + atrás"]),
 ("Al borde del acantilado", S), ("Comando arrastrándose con los brazos", S),
 ("Arrastre de cuatro puntos con los brazos en pendiente", S),
 ("Comando arrastrándose por las piernas - dejar de apoyar", LR),
 ("Cuatro puntos con una mano sobre el medio del tronco", LR), ("Sentadillas en el aire - por la pelvis", S),
 ("Sentado libremente en la viga mirando hacia adelante", S),
 ("De rodillas altas a rodillas bajas a la altura de los muslos o la pelvis baja", S), ("Arrodillarse a distancia", S),
 ("Extensión de tronco desde el abdomen bajo hasta la postura de Superman sobre los muslos", S),
 ("Propenso a ponerse de pie en cuatro puntos utilizando un antideslizante largo", S),
 ("Postura boca abajo en cuatro puntos para pararse con 2 manos sobre 1 pierna", LR),
 ("Independiente sobre una barra", S), ("Flotar en las manos desde posición boca abajo sobre una mesa", S),
 ("Flotación en manos desde extensión de tronco por abdomen bajo", S),
 ("Doble zig zag en barras estrechas por combinación", S),
 ('1, 2, 3, sube del cubo a dos cajas de 15 cm (6")', C5), ("Hongo", C5), ("Robot", C5), ("Diamante", C5), ("Cajas de mosaico", C5),
 ("Barras baldosas por tobillos", S), ("Bajar escalera alta frente a ti", C5),
 ("Subir dobles barras estrechas arriba abajo", C4),
 ('Pasos laterales para subir y bajar cajas 15 cm (6")', C5),
 ("Pasos con antideslizante en la muñeca y el tobillo opuesto", S),
 ("Pasos con rotación externa de hombro y con carga", S),
]
bloques = []
for nivel, datos in (("A", A), ("B", B), ("C", C)):
    for n, (nombre, variantes) in enumerate(datos, 1):
        ejercicios = [nombre] if variantes is None else [f"{nombre} – {v}" for v in variantes]
        bloques.append({"id": f"dmi-{nivel.lower()}-{n:02d}", "nombre": nombre, "nivel": nivel, "numero": n, "ejercicios": ejercicios})

# validaciones
ids = [b["id"] for b in bloques]; assert len(ids) == len(set(ids)), "ids repetidos"
nombres = [e for b in bloques for e in b["ejercicios"]]
dup = sorted({x for x in nombres if nombres.count(x) > 1})
assert not dup, f"nombres de ejercicio repetidos: {dup}"
assert all(b["ejercicios"] for b in bloques)
cuenta = {k: sum(1 for b in bloques if b["nivel"] == k) for k in "ABC"}
assert cuenta == {"A": 35, "B": 30, "C": 30}, cuenta

cab = '{\n  "formato": "fisioterapia-bloques",\n  "version": 2,\n  "origen": "Ejercicios DMI Nivel A, B y C",\n  "bloques": [\n'
cuerpo = ",\n".join("    " + json.dumps(b, ensure_ascii=False) for b in bloques)
out = sys.argv[1]
open(out, "w", encoding="utf-8").write(cab + cuerpo + "\n  ]\n}\n")
json.load(open(out, encoding="utf-8"))  # debe ser JSON válido
print(f"OK: {len(bloques)} bloques {cuenta}, {len(nombres)} ejercicios, sin nombres repetidos")
