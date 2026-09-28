"""
Revisión de pedidos por el Servicio de Alimentación.

La autorización es nominada: cada solicitud (persona + comida) queda autorizada o no.
Lo pedido nunca se sobrescribe: la solicitud conserva sus datos y la decisión se guarda
en columnas propias (autorizada, autorizada_por, autorizada_at).
"""
import logging
from src.core.database import db
from src.core.fechas import ahora
from src.core.errores import Conflicto, ErrorValidacion
from src.core.models.pedidos import ESTADO_AUTORIZADO, ESTADO_CONFIRMADO, ESTADO_RECHAZADO
from src.core.validators.pedidos import validar_autorizacion

log = logging.getLogger("alimentacion")


def _pendiente(pedido) -> None:
    """Solo se revisa un pedido confirmado (pendiente)."""
    if pedido.estado != ESTADO_CONFIRMADO:
        raise Conflicto(f"El pedido ya está {pedido.estado}.")


def autorizar_pedido(usuario, pedido, data):
    """Registra la decisión por solicitud y deja el pedido en estado autorizado."""
    _pendiente(pedido)
    d, errores = validar_autorizacion(data)
    if errores:
        raise ErrorValidacion(errores)

    ids_del_pedido = {s.id for s in pedido.solicitudes}
    ajenas = set(d["decisiones"]) - ids_del_pedido
    if ajenas:
        raise ErrorValidacion(
            {"solicitudes": f"Las solicitudes {sorted(ajenas)} no pertenecen a este pedido."}
        )

    momento = ahora()
    for solicitud in pedido.solicitudes:
        solicitud.autorizada = True if d["todas"] else d["decisiones"].get(solicitud.id, False)
        solicitud.autorizada_por_id = usuario.id
        solicitud.autorizada_at = momento

    pedido.estado = ESTADO_AUTORIZADO
    pedido.revisado_por_id = usuario.id
    pedido.revisado_at = momento
    db.session.commit()
    autorizadas = sum(1 for s in pedido.solicitudes if s.autorizada)
    log.info("Pedido %s autorizado por %s: %s de %s solicitudes",
             pedido.id, usuario.email, autorizadas, len(pedido.solicitudes))
    return pedido


def rechazar_pedido(usuario, pedido, motivo: str | None):
    """Rechaza el pedido completo. Queda en el historial pero no disponible para entrega."""
    _pendiente(pedido)
    motivo = (motivo or "").strip()
    if len(motivo) > 255:
        raise ErrorValidacion({"motivo": "El motivo no puede superar los 255 caracteres."})
    momento = ahora()
    for solicitud in pedido.solicitudes:
        solicitud.autorizada = False
        solicitud.autorizada_por_id = usuario.id
        solicitud.autorizada_at = momento
    pedido.estado = ESTADO_RECHAZADO
    pedido.motivo_rechazo = motivo or None
    pedido.revisado_por_id = usuario.id
    pedido.revisado_at = momento
    db.session.commit()
    log.info("Pedido %s rechazado por %s", pedido.id, usuario.email)
    return pedido
