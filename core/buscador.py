"""
BUSCADOR DE ARCHIVOS - The goose Brand
Localiza guías y facturas según la época del registro.

Estrategia de búsqueda:
  Se hace un glob recursivo desde {ruta_base} buscando candidatos por patrón
  de nombre, sin cargar a memoria una lista completa de todos los PDFs.
  Esto da más control sobre el consumo de RAM cuando el árbol contiene
  muchísimos archivos.

  Además, cada búsqueda se memoriza en un caché liviano por clave para evitar
  repetir escaneos idénticos dentro de la misma ejecución.
"""

import logging
import re
from datetime import date
from pathlib import Path
from typing import Callable, Optional

from core.extractor_pdf import extraer_dato_externo_nombre

logger = logging.getLogger(__name__)

CORTE_EPOCA_2 = date(2025, 1, 1)
CORTE_EPOCA_3 = date(2025, 11, 1)

# Caché liviano de resultados: {(tipo, ruta_base, clave): Path | None}
_cache_busquedas: dict[tuple[str, str, str], Optional[Path]] = {}


def determinar_epoca(fecha_documento: date) -> int:
    if fecha_documento < CORTE_EPOCA_2:
        return 1
    elif fecha_documento < CORTE_EPOCA_3:
        return 2
    else:
        return 3


def _es_guia(nombre: str) -> bool:
    n = nombre.lower().strip()
    return n.startswith("guia") or n.startswith("guía")


def _clave_cache(tipo: str, ruta_base: Path, clave: str) -> tuple[str, str, str]:
    return tipo, str(ruta_base).lower(), clave.upper()


def _buscar_en_arbol(
    ruta_base: Path,
    patron: str,
    *,
    solo_guias: Optional[bool],
    descripcion: str,
    matcher: Optional[Callable[[Path], bool]] = None,
) -> Optional[Path]:
    """
    Busca recursivamente PDFs por patrón sin materializar todo el árbol.

    Args:
        solo_guias:
            - True: solo acepta guías
            - False: solo acepta facturas
            - None: acepta cualquier PDF
    """
    if not ruta_base.exists():
        logger.warning(f"Carpeta raíz no encontrada: {ruta_base}")
        return None

    revisados = 0
    for pdf in ruta_base.rglob(patron):
        if not pdf.is_file():
            continue

        es_guia = _es_guia(pdf.name)
        if solo_guias is True and not es_guia:
            continue
        if solo_guias is False and es_guia:
            continue

        revisados += 1
        if matcher and not matcher(pdf):
            continue

        logger.info(
            f"{descripcion} encontrada: {pdf.name} en {pdf.parent.name} "
            f"(candidatos revisados={revisados})"
        )
        return pdf

    logger.warning(
        f"{descripcion} no encontrada con patrón '{patron}' "
        f"(candidatos revisados={revisados})"
    )
    return None


def _buscar_con_cache(
    tipo: str,
    ruta_base: Path,
    clave: str,
    finder: Callable[[], Optional[Path]],
) -> Optional[Path]:
    cache_key = _clave_cache(tipo, ruta_base, clave)
    if cache_key not in _cache_busquedas:
        _cache_busquedas[cache_key] = finder()
    return _cache_busquedas[cache_key]


def _buscar_factura_flexible(ruta_base: Path, referencia: str) -> Optional[Path]:
    """
    Busca facturas con todos los patrones conocidos sin depender de la época.

    Prioridad:
      1. Nombre que empieza con la referencia
      2. Nombre que termina con la referencia
      3. Nombre que contiene la referencia en cualquier parte
    """
    ref_upper = referencia.upper()
    mejor_inicio = None
    mejor_fin = None
    mejor_contiene = None
    revisados = 0

    if not ruta_base.exists():
        logger.warning(f"Carpeta raíz no encontrada: {ruta_base}")
        return None

    for pdf in ruta_base.rglob(f"*{referencia}*.pdf"):
        if not pdf.is_file() or _es_guia(pdf.name):
            continue

        revisados += 1
        nombre = pdf.stem.upper()

        if nombre.startswith(ref_upper):
            mejor_inicio = pdf
            break
        if mejor_fin is None and nombre.endswith(ref_upper):
            mejor_fin = pdf
        if mejor_contiene is None and ref_upper in nombre:
            mejor_contiene = pdf

    elegido = mejor_inicio or mejor_fin or mejor_contiene
    if elegido is not None:
        logger.info(
            f"Factura encontrada para ref={referencia}: {elegido.name} en "
            f"{elegido.parent.name} (candidatos revisados={revisados})"
        )
        return elegido

    logger.warning(
        f"Factura no encontrada para ref={referencia} "
        f"(candidatos revisados={revisados})"
    )
    return None


def limpiar_indice():
    """Limpia el caché de búsquedas entre ejecuciones del pipeline."""
    _cache_busquedas.clear()


def buscar_factura(
    referencia: str,
    fecha: date,
    ruta_base: Path,
) -> Optional[Path]:
    """
    Busca la factura en todo el árbol por nombre.
    """
    if not referencia or str(referencia).strip().lower() in ("nan", "none", ""):
        return None

    ref = str(referencia).strip()
    return _buscar_con_cache(
        "factura_flexible",
        ruta_base,
        ref,
        lambda: _buscar_factura_flexible(ruta_base, ref),
    )


def buscar_guia(
    referencia: str,
    asignacion: str,
    fecha: date,
    ruta_base: Path,
    ruta_factura: Optional[Path] = None,
) -> Optional[Path]:
    """
    Busca la guía en todo el árbol por nombre probando todos los métodos.
    Prioridad (según solicitud del usuario):
    1. Método Época 3 (Asignación) - Prioridad Máxima
    2. Método Época 3 (Referencia)
    3. Método Época 2 (Dato externo del nombre de la factura)
    """
    
    # --- 1. Método Época 3 (Asignación) ---
    asig = str(asignacion).strip()
    asig_num = re.sub(r"[^0-9]", "", asig) if asig.lower() not in ("nan", "none", "") else ""
    
    if asig_num:
        guia_por_asig = _buscar_con_cache(
            "guia_metodo_asig",
            ruta_base,
            asig_num,
            lambda: _buscar_en_arbol(
                ruta_base,
                patron=f"*{asig_num}*.pdf",
                solo_guias=True,
                descripcion=f"Guía (método asignación) clave={asig_num}",
                matcher=lambda pdf: asig_num in re.sub(r"[^0-9]", "", pdf.stem),
            ),
        )
        if guia_por_asig:
            return guia_por_asig

    # --- 2. Método Época 3 (Referencia) ---
    ref_limpia = str(referencia).strip()
    if ref_limpia and ref_limpia.lower() not in ("nan", "none", ""):
        ref_upper = ref_limpia.upper()
        guia_por_ref = _buscar_con_cache(
            "guia_metodo_ref",
            ruta_base,
            ref_upper,
            lambda: _buscar_en_arbol(
                ruta_base,
                patron=f"*{ref_upper}*.pdf",
                solo_guias=True,
                descripcion=f"Guía (método referencia) clave={ref_limpia}",
                matcher=lambda pdf: ref_upper in pdf.stem.upper(),
            ),
        )
        if guia_por_ref:
            return guia_por_ref

    # --- 3. Método Época 2 (Dato externo del nombre de la factura) ---
    if ruta_factura:
        dato_externo = extraer_dato_externo_nombre(ruta_factura.name)
        if dato_externo:
            clave = dato_externo.upper()
            guia_metodo_ext = _buscar_con_cache(
                "guia_metodo_externo",
                ruta_base,
                clave,
                lambda: _buscar_en_arbol(
                    ruta_base,
                    patron=f"*{dato_externo}*.pdf",
                    solo_guias=True,
                    descripcion=f"Guía (método dato externo) clave={dato_externo}",
                    matcher=lambda pdf: clave in pdf.stem.upper(),
                ),
            )
            if guia_metodo_ext:
                return guia_metodo_ext
            
    logger.warning(f"Guía no encontrada para ref={referencia} asignación={asignacion} por ningún método.")
    return None