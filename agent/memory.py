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
from sqlalchemy import String, Text, DateTime, select, Integer, Boolean
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
    notificado: Mapped[bool] = mapped_column(Boolean, default=False)
    cerrado: Mapped[bool] = mapped_column(Boolean, default=False)
    descartado: Mapped[bool] = mapped_column(Boolean, default=False)
    # Datos extraídos de la conversación
    nombre: Mapped[str] = mapped_column(String(100), default="No indicó")
    rubro: Mapped[str] = mapped_column(String(100), default="No indicó")
    presupuesto: Mapped[str] = mapped_column(String(100), default="No indicó")
    interes: Mapped[str] = mapped_column(Text, default="No indicó")
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


async def inicializar_db():
    """Crea las tablas si no existen. Se llama al arrancar el servidor."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


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


async def registrar_lead(telefono: str) -> bool:
    """
    Registra un lead calificado. Si ya existe, no hace nada.

    Returns:
        True si fue registrado por primera vez (nuevo lead)
        False si ya existía (ya fue notificado antes)
    """
    async with async_session() as session:
        query = select(Lead).where(Lead.telefono == telefono)
        result = await session.execute(query)
        existente = result.scalar_one_or_none()

        if existente:
            return False  # Ya registrado

        lead = Lead(telefono=telefono, notificado=True, cerrado=False, descartado=False)
        session.add(lead)
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


async def obtener_leads(solo_abiertos: bool = False) -> list[dict]:
    """Retorna todos los leads registrados para el dashboard."""
    async with async_session() as session:
        query = select(Lead).order_by(Lead.timestamp.desc())
        if solo_abiertos:
            query = query.where(Lead.cerrado == False)
        result = await session.execute(query)
        leads = result.scalars().all()
        return [
            {
                "id": l.id,
                "telefono": l.telefono,
                "notificado": l.notificado,
                "cerrado": l.cerrado,
                "descartado": l.descartado,
                "nombre": l.nombre,
                "rubro": l.rubro,
                "presupuesto": l.presupuesto,
                "interes": l.interes,
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
