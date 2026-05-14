"""
GESTOR DE RUTAS DESTINO - The goose Brand
Crea y resuelve la ruta dinámica O:\...\{año}\{mes_es}\
y copia archivos fuente al destino.
"""

import logging
import shutil
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MESES_ES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


def ruta_de_soportes(ruta_base_destino: Path, fecha: date) -> Path:
    """
    Retorna la ruta completa de destino:
    {ruta_base_destino}/{año}/{MES_ES}/
    """
    mes_str = MESES_ES.get(fecha.month, str(fecha.month))
    return ruta_base_destino / str(fecha.year) / mes_str


def verificacion_carpetas(ruta: Path) -> bool:
    """Crea la carpeta si no existe. Retorna True si OK."""
    try:
        ruta.mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"No se pudo crear carpeta {ruta}: {e}")
        return False


def copiar_archivo(origen: Path, destino_dir: Path) -> Optional[Path]:
    """
    Copia un archivo al directorio destino.
    Si ya existe, no sobreescribe (skip silencioso).
    """
    if not origen or not origen.exists():
        return None
    try:
        verificacion_carpetas(destino_dir)
        ruta_destino = destino_dir / origen.name
        if ruta_destino.exists():
            logger.info(f"Ya existe, se omite copia: {origen.name}")
            return ruta_destino
        shutil.copy2(origen, ruta_destino)
        logger.info(f"Copiado: {origen.name} → {destino_dir}")
        return ruta_destino
    except Exception as e:
        logger.error(f"Error copiando {origen.name}: {e}")
        return None


def copiar_documentos_registro(
        ruta_factura: Optional[Path],
        ruta_guia: Optional[Path],
        ruta_base_destino: Path,
        fecha: date,
    ) -> tuple[Optional[Path], Optional[Path]]:
    """
    Copia factura y guía a la carpeta destino correspondiente.
    Retorna (ruta_factura_destino, ruta_guia_destino).
    """
    carpeta_destino = ruta_de_soportes(ruta_base_destino, fecha)
    verificacion_carpetas(carpeta_destino)

    fact_dest = copiar_archivo(ruta_factura, carpeta_destino) if ruta_factura else None
    guia_dest = copiar_archivo(ruta_guia, carpeta_destino) if ruta_guia else None

    return fact_dest, guia_dest