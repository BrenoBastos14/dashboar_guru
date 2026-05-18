from __future__ import annotations

from sqlalchemy import desc, func, select

from .config import DEFAULT_SYSTEM_PROMPT, HISTORY_LIMIT
from .database import Base, SessionLocal, engine
from .models import Instance, Message


def init_db() -> None:
    # Cria as tabelas se ainda não existem. Em produção, prefira `alembic upgrade head`.
    Base.metadata.create_all(bind=engine)


def _to_dict(inst: Instance) -> dict:
    return {
        "name": inst.name,
        "owner_user_id": inst.owner_user_id,
        "system_prompt": inst.system_prompt,
        "phone": inst.phone,
        "status": inst.status,
        "enabled": inst.enabled,
        "created_at": inst.created_at.isoformat() if inst.created_at else None,
    }


def upsert_instance(
    name: str,
    system_prompt: str | None = None,
    owner_user_id: int | None = None,
) -> None:
    with SessionLocal() as s:
        inst = s.get(Instance, name)
        if inst is None:
            inst = Instance(
                name=name,
                system_prompt=system_prompt or DEFAULT_SYSTEM_PROMPT,
                owner_user_id=owner_user_id,
            )
            s.add(inst)
        else:
            if system_prompt is not None:
                inst.system_prompt = system_prompt
            if owner_user_id is not None and inst.owner_user_id is None:
                inst.owner_user_id = owner_user_id
        s.commit()


def update_instance_status(name: str, status: str) -> None:
    with SessionLocal() as s:
        inst = s.get(Instance, name)
        if inst:
            inst.status = status
            s.commit()


def update_instance_prompt(name: str, prompt: str) -> None:
    with SessionLocal() as s:
        inst = s.get(Instance, name)
        if inst:
            inst.system_prompt = prompt
            s.commit()


def set_instance_enabled(name: str, enabled: bool) -> None:
    with SessionLocal() as s:
        inst = s.get(Instance, name)
        if inst:
            inst.enabled = enabled
            s.commit()


def delete_instance(name: str) -> None:
    with SessionLocal() as s:
        inst = s.get(Instance, name)
        if inst:
            s.delete(inst)
            s.commit()


def get_instance(name: str) -> dict | None:
    with SessionLocal() as s:
        inst = s.get(Instance, name)
        return _to_dict(inst) if inst else None


def list_instances(owner_user_id: int | None = None) -> list[dict]:
    with SessionLocal() as s:
        stmt = select(Instance).order_by(desc(Instance.created_at))
        if owner_user_id is not None:
            stmt = stmt.where(Instance.owner_user_id == owner_user_id)
        return [_to_dict(i) for i in s.execute(stmt).scalars()]


def add_message(instance_name: str, jid: str, role: str, content: str) -> None:
    with SessionLocal() as s:
        s.add(Message(instance_name=instance_name, jid=jid, role=role, content=content))
        s.commit()


def history(instance_name: str, jid: str, limit: int = HISTORY_LIMIT) -> list[dict]:
    with SessionLocal() as s:
        stmt = (
            select(Message)
            .where(Message.instance_name == instance_name, Message.jid == jid)
            .order_by(desc(Message.id))
            .limit(limit)
        )
        rows = list(s.execute(stmt).scalars())
        rows.reverse()
        return [{"role": r.role, "content": r.content} for r in rows]


def recent_conversations(instance_name: str, limit: int = 20) -> list[dict]:
    with SessionLocal() as s:
        stmt = (
            select(
                Message.jid,
                func.max(Message.created_at).label("last_at"),
                func.count().label("n_messages"),
            )
            .where(Message.instance_name == instance_name)
            .group_by(Message.jid)
            .order_by(desc("last_at"))
            .limit(limit)
        )
        return [
            {
                "jid": r.jid,
                "last_at": r.last_at.isoformat() if r.last_at else None,
                "n_messages": r.n_messages,
            }
            for r in s.execute(stmt)
        ]
