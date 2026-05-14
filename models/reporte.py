"""
REPORTE - The goose Brand
Acumula conteos durante el pipeline y genera el resumen final.
"""

from dataclasses import dataclass, field
from typing import List


MAX_DETALLE_OBSERVACIONES = 300


@dataclass
class ResultadoRegistro:
    referencia: str
    asignacion: str
    fecha: str
    observacion: str = ""
    waybill: str = ""
    valor_factura: str = ""


@dataclass
class Reporte:
    total_pendientes: int = 0
    actualizados: int = 0
    sin_factura: int = 0
    sin_guia: int = 0
    sin_ambos: int = 0
    errores_lectura: int = 0
    total_observaciones: int = 0
    observaciones: List[ResultadoRegistro] = field(default_factory=list)

    def registrar(self, resultado: ResultadoRegistro):
        obs = resultado.observacion.lower().strip()

        # Registro completo — solo sumar, no agregar a la tabla de observaciones
        if obs in ("completo", ""):
            self.actualizados += 1
            return

        # Registro con problema. Conservamos el total real, pero limitamos
        # el detalle que se guarda para no saturar la GUI al finalizar.
        self.total_observaciones += 1
        if len(self.observaciones) < MAX_DETALLE_OBSERVACIONES:
            self.observaciones.append(resultado)

        if "ambos" in obs:
            self.sin_ambos += 1
        elif "guia" in obs and "falta" in obs:
            self.sin_guia += 1
        elif "factura" in obs and "falta" in obs:
            self.sin_factura += 1
        elif "no se pudo leer" in obs or "no se pudieron leer" in obs:
            self.errores_lectura += 1
        else:
            # Casos mixtos (falta X y no se pudo leer Y) se cuentan
            # en la categoría más relevante; si no encajan, van a errores
            self.errores_lectura += 1

    def resumen_texto(self) -> str:
        lineas = [
            "═" * 52,
            "   RESUMEN PIPELINE The goose Brand",
            "═" * 52,
            f"  Registros procesados : {self.total_pendientes}",
            f"  ✔ Completados        : {self.actualizados}",
            f"  ✘ Sin ambos docs     : {self.sin_ambos}",
            f"  ⚠ Sin guía          : {self.sin_guia}",
            f"  ⚠ Sin factura       : {self.sin_factura}",
            f"  ⚠ Error de lectura  : {self.errores_lectura}",
            "═" * 52,
        ]
        return "\n".join(lineas)

    def filas_observaciones(self) -> list[tuple]:
        """Retorna lista de tuplas para mostrar en tabla GUI (solo registros con problema)."""
        return [
            (r.referencia, r.fecha, r.observacion)
            for r in self.observaciones
        ]