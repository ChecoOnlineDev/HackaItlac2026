"""Sugerencia de categoria por la descripcion del articulo (I-14) y limpieza del nombre.

Es un reglamento de palabras, no un clasificador: el diccionario esta en el anexo de
`docs/features/FEAT-007-importacion-reposicion-y-categoria-sugerida.md` y cambiarlo es un cambio
de ese documento y de este archivo. Solo SUGIERE: nada se aplica sin que la persona lo vea.

Como se evalua: la descripcion se pasa a mayusculas y sin acentos; se recorren las reglas en orden
y la primera que coincide gana. `SERVICIO` no es un articulo: se excluye. Si ninguna coincide, la
fila queda "por revisar".
"""

import re
import unicodedata
from dataclasses import dataclass

EXCLUIR = "EXCLUIR"

EPP_BASICO = "EPP básico"
EPP_DOTACION = "EPP de dotación"
ALTURAS = "Equipo de alturas"
MANUAL = "Herramienta manual"
ELECTRICA = "Herramienta eléctrica"
ALTO_VALOR = "Equipo de alto valor"
CONSUMIBLES = "Consumibles de trabajo"

# Prefijo del codigo generado `PREFIJO-NNNN`. Una categoria creada por la empresa no tiene.
PREFIJOS = {
    EPP_BASICO: "EPB",
    EPP_DOTACION: "EPD",
    ALTURAS: "ALT",
    MANUAL: "HMA",
    ELECTRICA: "HEL",
    ALTO_VALOR: "EAV",
    CONSUMIBLES: "CON",
}

# (expresion sobre la descripcion normalizada, categoria o EXCLUIR), en el orden del anexo.
_REGLAS: tuple[tuple[str, str], ...] = (
    (r"\bSERVICIO\b", EXCLUIR),
    (r"CUERDA DE RAPEL|LINEA DE VIDA|\bARNES\b|BANDOLA|RETRACTIL|GANCHO DOBLE", ALTURAS),
    (r"GAS LENS|ANTORCHA TIG|\bTIG\b|BOQUILLA|SOLDADURA|MORDAZA|\bCERAMICA\b", CONSUMIBLES),
    (r"PORTA ?ELECTRODO|PINZA DE TIERRA", ELECTRICA),
    (r"REGULADOR|SOPLETE|MANOMETRO|DETECTOR DE GASES|\bRADIO\b", ALTO_VALOR),
    (r"RESPIRADOR|BARBOQUEJO|\bCASCO\b|\bPETO\b|POLAINAS", EPP_BASICO),
    (
        r"CRISTAL .*CARETA|\bFILTRO\b.*(VAP|PARTIC|GAS ACIDOS|OZONO|CART)|\bFILTRO/CART|\bLENTE\b"
        r"|ANTEOJO|CACHUCHA|\bGUANTE|TAPON AUDITIVO|OVEROL|CAMISOLA|\bBOTA|CALZADO|\bFAJA\b"
        r"|CHALECO",
        EPP_DOTACION,
    ),
    (
        r"HOJA DE LIJA|\bLIJA\b|\bDISCO\b|RUEDA FLAP|SEGUETA|\bBROCA\b|JUEGO DE BROCAS|REPUESTO",
        CONSUMIBLES,
    ),
    (
        r"TALADRO|TALABRO|ROTOMARTILLO|PULIDOR|ESMERIL|SIERRA|LLAVE DE IMPACTO"
        r"|BOMBA .*NEUMATICA|BOMBA ENGRAS|LINTERNA|\bLAMPARA(?! *BTICINO)|REFLECTOR",
        ELECTRICA,
    ),
    (
        r"ARANA|\bLLANA\b|CHAROLA|CEPILLO DE ALAMBRE|MULTICONTACTO|EXTENSION DE \d",
        MANUAL,
    ),
    (
        r"PORTA LAMPARA|CHALUPA|ARRANCADOR|\bFOCO\b|\bPILA\b|CINTA|FIBRA VERDE|PUNTA DE (3|CRUZ)"
        r"|JUEGO DE (\d+ )?PUNTAS|\bPUNTAS\b|\bCARBON\b|\bCARDA\b",
        CONSUMIBLES,
    ),
    (
        r"PINTURA|SILICON|SELLADOR|PEGAMENTO|ESPUMA|ACEITE|LUBRICANTE|AFLOJATODO|ACIDO"
        r"|LIQUIDO PARA|PLASTI|KOLA LOKA|NO MAS CLAVOS|\bYESO\b|CLORO|MARCADOR|ALAMBRE|\bLONA\b"
        r"|BOLSA|TRAPO|\bPIJA\b|TORNILLO|TUERCA|CLAVO|TAQUETE|ESPARRAGO|CINCHO|ABRAZADERA"
        r"|ARMELLA|CANDADO|CERRADURA|CHAPA|PASADOR|MENSULA|NIPLE|COPLE|MANGUERA|MEZCLADORA"
        r"|PLAGAFIN|RAFIA|BROCHA|RODILLO|SILIC|PENS|TEFLON",
        CONSUMIBLES,
    ),
    (r"ESCALERA|CARRETILLA|\bLLANTA\b|BOMBA PRETUL|INFLADOR|ATOMIZADOR|VANDEROLA", MANUAL),
    (
        r"\bLLAVE\b|\bDADO\b|NUDO|MATRACA|MARTILLO|\bPINZA|CUTTER|NIVEL|FLEXOMETRO|DESARMADOR"
        r"|BARRETA|\bPALA\b|AZADON|TALACHO|ZAPAPICO|\bHACHA\b|CAVADOR|CAVAHOYOS|\bLIMA\b"
        r"|ESCUADRA|\bESCOBA|RECOGEDOR|TRAPIADOR|DOBLADOR|MANERAL|ADAPTADOR|\bMARRO\b"
        r"|CABO PARA|MARTELINA|CUCHARA|RASPADOR|TIJERA|NAVAJA|CEPILLO|ENGRAPADORA|PISTOLA"
        r"|\bPUNTA\b",
        MANUAL,
    ),
)
REGLAS = tuple((re.compile(patron), categoria) for patron, categoria in _REGLAS)

# Regla 15: respaldo por prefijo de la clave UNSPSC, solo si el archivo la trae y ninguna regla
# anterior coincidio. Se prueba el prefijo mas largo primero.
_RESPALDO_UNSPSC: tuple[tuple[str, str], ...] = (
    ("46", EPP_DOTACION),
    ("2711", MANUAL),
    ("2713", MANUAL),
    ("2410", MANUAL),
    ("23101", ELECTRICA),
    ("2327", CONSUMIBLES),
    ("3119", CONSUMIBLES),
    ("3120", CONSUMIBLES),
    ("3126", CONSUMIBLES),
    ("3116", CONSUMIBLES),
    ("3912", CONSUMIBLES),
    ("4014", CONSUMIBLES),
    ("1110", CONSUMIBLES),
)


@dataclass(frozen=True)
class Sugerencia:
    """Lo que dice el diccionario. `categoria` es `EXCLUIR` si es un servicio."""

    categoria: str
    motivo: str

    @property
    def excluir(self) -> bool:
        return self.categoria == EXCLUIR


def normalizar(texto: str) -> str:
    """Mayusculas y sin acentos (NFD sin las marcas)."""
    descompuesto = unicodedata.normalize("NFD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).upper()


def _normalizar_con_posiciones(texto: str) -> tuple[str, list[int]]:
    """Como `normalizar`, pero dice de que posicion del original viene cada letra: sirve para
    mostrar en el motivo la palabra tal como esta escrita (con su acento)."""
    salida: list[str] = []
    posiciones: list[int] = []
    for i, caracter in enumerate(texto):
        for c in unicodedata.normalize("NFD", caracter):
            if not unicodedata.combining(c):
                for u in c.upper():
                    salida.append(u)
                    posiciones.append(i)
    return "".join(salida), posiciones


def sugerir(descripcion: str, clave_unspsc: str | None = None) -> Sugerencia | None:
    """La primera regla que coincide con la descripcion, o `None` si ninguna (por revisar)."""
    normalizada, posiciones = _normalizar_con_posiciones(descripcion)
    for patron, categoria in REGLAS:
        encontrada = patron.search(normalizada)
        if encontrada is None or encontrada.end() == encontrada.start():
            continue
        inicio = posiciones[encontrada.start()]
        fin = posiciones[encontrada.end() - 1] + 1
        palabra = " ".join(descripcion[inicio:fin].split()).lower()
        return Sugerencia(categoria, f"La descripción dice «{palabra}»")
    clave = "".join(c for c in (clave_unspsc or "") if c.isdigit())
    if clave.startswith("78"):
        return Sugerencia(EXCLUIR, "La clave de producto es la de un servicio")
    for prefijo, categoria in _RESPALDO_UNSPSC:
        if clave.startswith(prefijo):
            return Sugerencia(categoria, f"La clave de producto empieza con {prefijo}")
    return None


def es_servicio(descripcion: str) -> bool:
    """Una descripcion con la palabra SERVICIO no es un articulo (se excluye con aviso)."""
    return REGLAS[0][0].search(normalizar(descripcion)) is not None


# ------------------------------------------------------------------ limpieza del nombre

_PREFIJO_NOMBRE = re.compile(r"^\s*/(?:T|SP)/\s*", re.IGNORECASE)
_CLAVE_INTERNA = re.compile(r"\s*\(\s*[A-Za-z]{1,4}\s?\d{2,6}\s*\)")
_PUNTO_FINAL = re.compile(r"\s+\.$")


def limpiar_nombre(nombre: str) -> str:
    """Quita lo que no es parte del nombre: los prefijos `/T/` y `/SP/`, las claves internas entre
    parentesis como `(RF005)` y el sufijo ` .`; reduce los espacios multiples a uno."""
    limpio = _PREFIJO_NOMBRE.sub("", nombre)
    limpio = _CLAVE_INTERNA.sub("", limpio)
    limpio = " ".join(limpio.split())
    return _PUNTO_FINAL.sub("", limpio).strip()
