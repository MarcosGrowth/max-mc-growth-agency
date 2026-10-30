# agent/memory.py — Memoria de conversaciones con SQLite
# Generado por AgentKit para MC Growth Agency

"""
Sistema de memoria del agente Max. Guarda el historial de conversaciones
por número de teléfono usando SQLite (local) o PostgreSQL (producción en Railway).
"""

import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, DateTime, select, Integer, Boolean, inspect, text
from dotenv import load_dotenv

load_dotenv()

# Configuración de base de datos desde .env
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./agentkit.db")

# Si es PostgreSQL en Railway, ajustar el esquema de URL
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Mensaje(Base):
    """Modelo de mensaje almacenado en la base de datos."""
    __tablename__ = "mensajes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), index=True)
    role: Mapped[str] = mapped_column(String(20))       # "user" o "assistant"
    content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Lead(Base):
    """Lead calificado por Max — para el dashboard y seguimiento."""
    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telefono: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    calificado: Mapped[bool] = mapped_column(Boolean, default=False)
    notificado: Mapped[bool] = mapped_column(Boolean, default=False)
    cerrado: Mapped[bool] = mapped_column(Boolean, default=False)
    descartado: Mapped[bool] = mapped_column(Boolean, default=False)
    # Datos extraídos de la conversación (solo se completan si califica)
    nombre: Mapped[str] = mapped_column(String(100), default="No indicó")
    rubro: Mapped[str] = mapped_column(String(100), default="No indicó")
    presupuesto: Mapped[str] = mapped_column(String(100), default="No indicó")
    interes: Mapped[str] = mapped_column(Text, default="No indicó")
    # Actividad — para identificar rápido quién respondió
    ultimo_mensaje: Mapped[str] = mapped_column(Text, default="")
    ultima_actividad: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def inicializar_db():
    """Crea las tablas si no existen y migra columnas nuevas en tablas viejas.
    Se llama al arrancar el servidor. NUNCA borra filas existentes."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_migrar_columnas_nuevas)


def _migrar_columnas_nuevas(conn):
    """
    Agrega a la tabla 'leads' las columnas que no existían en versiones
    anteriores (calificado, ultimo_mensaje, ultima_actividad) sin tocar
    ninguna fila ya guardada. Los leads que ya estaban en la tabla quedan
    marcados como calificados, porque antes de este cambio solo se
    guardaban ahí los leads que ya habían calificado.
    """
    inspector = inspect(conn)
    if "leads" not in inspector.get_table_names():
        return  # Tabla nueva — create_all ya la creó con todas las columnas
    columnas_existentes = {c["name"] for c in inspector.get_columns("leads")}

    if "calificado" not in columnas_existentes:
        conn.execute(text("ALTER TABLE leads ADD COLUMN calificado BOOLEAN DEFAULT FALSE"))
        conn.execute(text("UPDATE leads SET calificado = TRUE"))

    if "ultimo_mensaje" not in columnas_existentes:
        conn.execute(text("ALTER TABLE leads ADD COLUMN ultimo_mensaje TEXT DEFAULT ''"))

    if "ultima_actividad" not in columnas_existentes:
        conn.execute(text("ALTER TABLE leads ADD COLUMN ultima_actividad TIMESTAMP"))
        conn.execute(text("UPDATE leads SET ultima_actividad = timestamp WHERE ultima_actividad IS NULL"))


async def guardar_mensaje(telefono: str, role: str, content: str):
    """
    Guarda un mensaje en el historial de conversación.

    Args:
        telefono: Número de teléfono del prospecto
        role: "user" (prospecto) o "assistant" (Max)
        content: Texto del mensaje
    """
    async with async_session() as session:
        mensaje = Mensaje(
            telefono=telefono,
            role=role,
            content=content,
            timestamp=datetime.utcnow()
        )
        session.add(mensaje)
        await session.commit()


async def obtener_historial(telefono: str, limite: int = 20) -> list[dict]:
    """
    Recupera los últimos N mensajes de una conversación.

    Args:
        telefono: Número de teléfono del prospecto
        limite: Máximo de mensajes a recuperar (default: 20 = ~10 intercambios)

    Returns:
        Lista de dicts con role y content, en orden cronológico
    """
    async with async_session() as session:
        query = (
            select(Mensaje)
            .where(Mensaje.telefono == telefono)
            .order_by(Mensaje.timestamp.desc())
            .limit(limite)
        )
        result = await session.execute(query)
        mensajes = result.scalars().all()

        # Invertir para orden cronológico (los más recientes estaban primero)
        mensajes.reverse()

        return [
            {"role": msg.role, "content": msg.content}
            for msg in mensajes
        ]


async def registrar_contacto(telefono: str) -> bool:
    """
    Registra a CUALQUIER persona que le escribe a Max, calificada o no.
    Si ya existe, no hace nada (no pisa sus datos).

    Returns:
        True si es la primera vez que este número escribe
    """
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        existente = result.scalar_one_or_none()

        if existente:
            return False  # Ya estaba registrado

        contacto = Lead(telefono=telefono, calificado=False, notificado=False, cerrado=False, descartado=False)
        session.add(contacto)
        await session.commit()
        return True


async def actualizar_actividad(telefono: str, ultimo_mensaje: str):
    """Guarda el último mensaje y marca el momento, para ver rápido quién acaba de responder."""
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        contacto = result.scalar_one_or_none()
        if contacto:
            contacto.ultimo_mensaje = ultimo_mensaje
            contacto.ultima_actividad = datetime.utcnow()
            await session.commit()


async def registrar_lead(telefono: str) -> bool:
    """
    Marca un contacto como lead CALIFICADO (ya venía registrado por registrar_contacto).
    Si ya estaba calificado, no hace nada.

    Returns:
        True si acaba de calificar por primera vez (hay que notificar)
        False si ya estaba calificado antes
    """
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        contacto = result.scalar_one_or_none()

        if contacto is None:
            # No debería pasar (registrar_contacto corre antes), pero por si acaso
            contacto = Lead(telefono=telefono, calificado=True, notificado=True, cerrado=False, descartado=False)
            session.add(contacto)
            await session.commit()
            return True

        if contacto.calificado:
            return False  # Ya calificaba — no renotificar

        contacto.calificado = True
        contacto.notificado = True
        await session.commit()
        return True


async def actualizar_info_lead(telefono: str, nombre: str, rubro: str, presupuesto: str, interes: str):
    """Guarda los datos extraídos de la conversación en el lead."""
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        lead = result.scalar_one_or_none()
        if lead:
            lead.nombre = nombre
            lead.rubro = rubro
            lead.presupuesto = presupuesto
            lead.interes = interes
            await session.commit()


async def marcar_lead_cerrado(telefono: str) -> bool:
    """Marca un lead como cerrado (cliente ganado)."""
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        lead = result.scalar_one_or_none()
        if lead:
            lead.cerrado = True
            lead.descartado = False
            await session.commit()
            return True
        return False


async def marcar_lead_descartado(telefono: str) -> bool:
    """Marca un lead como descartado (no avanzó)."""
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        lead = result.scalar_one_or_none()
        if lead:
            lead.descartado = True
            lead.cerrado = False
            await session.commit()
            return True
        return False


async def eliminar_lead(telefono: str) -> bool:
    """Borra un contacto/lead del dashboard de forma manual y permanente. No toca su historial de mensajes."""
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        lead = result.scalar_one_or_none()
        if lead:
            await session.delete(lead)
            await session.commit()
            return True
        return False


async def obtener_leads(solo_abiertos: bool = False) -> list[dict]:
    """Retorna todos los contactos registrados (calificados o no) para el dashboard.
    Ordenados por actividad reciente — el que acaba de responder aparece primero."""
    async with async_session() as session:
        query = select(Lead).order_by(Lead.ultima_actividad.desc())
        if solo_abiertos:
            query = query.where(Lead.cerrado == False)
        result = await session.execute(query)
        leads = result.scalars().all()
        return [
            {
                "id": l.id,
                "telefono": l.telefono,
                "calificado": l.calificado,
                "notificado": l.notificado,
                "cerrado": l.cerrado,
                "descartado": l.descartado,
                "nombre": l.nombre,
                "rubro": l.rubro,
                "presupuesto": l.presupuesto,
                "interes": l.interes,
                "ultimo_mensaje": l.ultimo_mensaje,
                "ultima_actividad": l.ultima_actividad.isoformat(),
                "timestamp": l.timestamp.isoformat(),
            }
            for l in leads
        ]


async def limpiar_historial(telefono: str):
    """Borra todo el historial de conversación de un número. Útil para testing."""
    async with async_session() as session:
        query = select(Mensaje).where(Mensaje.telefono == telefono)
        result = await session.execute(query)
        mensajes = result.scalars().all()
        for msg in mensajes:
            await session.delete(msg)
        await session.commit()
