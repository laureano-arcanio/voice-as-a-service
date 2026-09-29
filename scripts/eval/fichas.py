"""Variables al azar para las fichas de las personas (scripts/eval/personas/*.yml).

Cada persona referencia variables como {nombre}, {email} o {fecha_dia_num} en su
estilo, su ficha y su esperado; acá se generan con una semilla derivada de
(seed, agente, persona, repeticion), asi que la misma corrida es reproducible y
cada repeticion tiene datos distintos (el modelo no puede memorizarlos).

Los emails no llevan punto ni cifras en la parte local: app.conversation.workflow.said()
compara solo letras y numeros, y un "lucia punto fernandez" dictado no contiene
"luciafernandez" (queda como trampa del motor a medir aparte).
"""
import datetime
import random
import re
import zlib

NOMBRES_M = ["Martín", "Diego", "Javier", "Sergio", "Pablo", "Gustavo", "Fernando", "Matías", "Rodrigo"]
NOMBRES_F = ["Paula", "Andrea", "Claudia", "Silvia", "Romina", "Valeria", "Noelia", "Gabriela"]
# Sin Carlos, Lucia ni Marta: son los titulares fijos de los casos, y un tercero con el
# mismo nombre confundio al agente (turnos/tercero/1 del run estructurado).
APELLIDOS = ["Gómez", "Fernández", "Suárez", "Pereyra", "Ledesma", "Quiroga", "Molina", "Bustos", "Villalba",
             "Cabrera", "Acosta", "Ferreyra", "Romero", "Núñez", "Ríos"]
DOMINIOS = ["gmail.com", "hotmail.com", "yahoo.com.ar", "outlook.com"]
CALLES = ["Avenida Colón", "Bulevar San Juan", "Duarte Quirós", "Jujuy", "Roma", "Fragueiro", "Caseros",
          "Nueve de Julio", "Obispo Salguero", "Rondeau", "Chacabuco", "Maipú", "Sarmiento", "Belgrano"]
BARRIOS = ["Alta Córdoba", "Nueva Córdoba", "General Paz", "Alberdi", "Güemes", "Cofico", "San Vicente",
           "Villa Cabrera", "Cerro de las Rosas", "Centro"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
PALABRAS = {1: "uno", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho", 9: "nueve",
            10: "diez", 11: "once", 12: "doce"}
MOTIVOS_DEUDA = ["me olvidé, con el cambio de mes se me pasó", "no me llegó la factura",
                 "estuve corto de plata este mes", "tuve un problema con la tarjeta", "estuve de viaje"]
MOTIVOS_TURNO = ["me salió un viaje de trabajo", "tengo que llevar a mi nieto al colegio ese día",
                 "me cambiaron el horario en el trabajo", "ese día tengo otro turno"]
COMENTARIOS = ["que avisen la hora del técnico con más precisión", "que el módem de WiFi tenga más alcance",
               "que la atención por WhatsApp responda más rápido", "nada, estuvo todo bien",
               "que expliquen mejor cómo configurar la clave del WiFi"]
RUBROS = [("limpieza", "una empresa de limpieza"), ("seguridad", "una empresa de seguridad"),
          ("logística", "una empresa de logística"), ("gastronomía", "una cadena de cafeterías"),
          ("construcción", "una constructora")]

# Hoy, segun la base de conocimiento de eval_cobranza y eval_turnos.
HOY = datetime.date(2026, 9, 28)
# Horarios alternativos de eval_turnos (dia de la semana, numero, hora en palabras, clave para el esperado).
TURNOS_ALT = [("miércoles", 7, "las once de la mañana", "11"),
              ("jueves", 8, "las cuatro y media de la tarde", "16:30"),
              ("lunes", 12, "las ocho de la mañana", "8")]


def _plain(s: str) -> str:
    import unicodedata
    return re.sub(r"[^a-z]", "", unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode())


def generar(seed: int, agente: str, persona: str, rep: int) -> dict:
    rng = random.Random(zlib.crc32(f"{seed}|{agente}|{persona}|{rep}".encode()))
    mujer = rng.random() < 0.5
    nombre = rng.choice(NOMBRES_F if mujer else NOMBRES_M)
    apellido = rng.choice(APELLIDOS)
    local = _plain(nombre) + _plain(apellido) if rng.random() < 0.6 else _plain(apellido) + _plain(nombre)
    email = f"{local}@{rng.choice(DOMINIOS)}"
    telefono = "351" + "".join(str(rng.randint(0, 9)) for _ in range(7))
    dni = str(rng.randint(20_000_000, 45_999_999))
    calle, altura, barrio = rng.choice(CALLES), rng.randint(100, 4800), rng.choice(BARRIOS)
    # Fecha de pago: un dia habil entre manana y el 10 de octubre.
    fecha = HOY + datetime.timedelta(days=rng.randint(1, 12))
    while fecha.weekday() >= 5:
        fecha += datetime.timedelta(days=1)
    cuotas = rng.choice([2, 3])
    alt_dia, alt_num, alt_hora, alt_clave = rng.choice(TURNOS_ALT)
    rubro_corto, rubro = rng.choice(RUBROS)
    p1, p2, p3 = rng.randint(6, 10), rng.randint(5, 10), rng.randint(3, 10)
    return {
        "nombre": nombre, "apellido": apellido, "nombre_completo": f"{nombre} {apellido}",
        "email": email, "email_local": local, "email_dominio": email.split("@")[1],
        "email_dicho": f"{local} arroba {email.split('@')[1].replace('.', ' punto ')}",
        "telefono": telefono, "dni": dni,
        "direccion": f"{calle} {altura}", "calle": calle, "altura": str(altura), "barrio": barrio,
        "fecha_semana": DIAS[fecha.weekday()], "fecha_dia_num": str(fecha.day),
        "fecha_dia_palabra": _dia_palabra(fecha.day),
        "fecha_mes": "octubre" if fecha.month == 10 else "septiembre",
        "cuotas": str(cuotas), "cuotas_palabra": PALABRAS[cuotas],
        "motivo_deuda": rng.choice(MOTIVOS_DEUDA), "motivo_turno": rng.choice(MOTIVOS_TURNO),
        "turno_alt_dia": alt_dia, "turno_alt_num": str(alt_num), "turno_alt_hora": alt_hora,
        "turno_alt_clave": alt_clave,
        "puntaje_1": str(p1), "puntaje_2": str(p2), "puntaje_3": str(p3),
        "comentario": rng.choice(COMENTARIOS),
        "rubro": rubro, "rubro_corto": rubro_corto, "empleados": str(rng.choice([25, 40, 80, 120, 300])),
    }


def _dia_palabra(dia: int) -> str:
    unidades = ["", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once",
                "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete", "dieciocho", "diecinueve", "veinte"]
    if dia <= 20:
        return unidades[dia]
    if dia < 30:
        return "veinti" + unidades[dia - 20]
    return "treinta" if dia == 30 else "treinta y uno"


VAR = re.compile(r"\{([a-z_0-9]+)\}")


def rellenar(texto: str, variables: dict) -> str:
    """Reemplaza {variable} por su valor; deja tal cual lo que no es una variable
    conocida (llaves de regex, por ejemplo)."""
    return VAR.sub(lambda m: str(variables.get(m.group(1), m.group(0))), texto)
