"""
Excepciones de negocio. Cada una lleva el código HTTP que le corresponde,
así la API responde el estado correcto y la app de administración muestra el mensaje.
"""


class ErrorNegocio(Exception):
    """Base de los errores de negocio."""

    status = 400

    def __init__(self, mensaje: str, errores: dict[str, str] | None = None):
        """Guarda el mensaje general y, opcionalmente, los errores por campo."""
        super().__init__(mensaje)
        self.mensaje = mensaje
        self.errores = errores or {}


class ErrorValidacion(ErrorNegocio):
    """Datos inválidos (400). `errores` es {campo: mensaje}."""

    status = 400

    def __init__(self, errores: dict[str, str], mensaje: str = "Revisá los datos ingresados."):
        """Crea el error con los mensajes por campo."""
        super().__init__(mensaje, errores)


class NoEncontrado(ErrorNegocio):
    """El recurso no existe (404)."""

    status = 404


class Prohibido(ErrorNegocio):
    """El usuario no puede operar sobre ese recurso (403)."""

    status = 403


class Conflicto(ErrorNegocio):
    """Choca con el estado actual de los datos (409): duplicados, ya autorizado, etc."""

    status = 409


# Nombre que usa el módulo de usuarios; se mantiene por compatibilidad.
OperacionNoPermitida = Conflicto
