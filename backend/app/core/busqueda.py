"""UX-03: coincidencias por palabras, sin interpretar comodines escritos por la persona."""

from sqlalchemy import and_, case, or_


def escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def palabras(texto: str) -> list[str]:
    partes = texto.strip().split()[:5]
    significativas = [p for p in partes if len(p) > 1]
    return significativas or partes


def por_palabras(texto: str, *columnas):
    return and_(
        *[
            or_(*[col.like(f"%{escapar_like(p)}%", escape="\\") for col in columnas])
            for p in palabras(texto)
        ]
    )


def relevancia(texto: str, *columnas):
    q = texto.strip()
    return case(
        (or_(*[c == q for c in columnas]), 0),
        (or_(*[c.like(f"{escapar_like(q)}%", escape="\\") for c in columnas]), 1),
        else_=2,
    )
