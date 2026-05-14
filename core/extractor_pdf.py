"""
EXTRACTOR DE PDF - The goose Brand
Extrae: WAYBILL, fecha de guía, total USD de factura
"""

import re
import logging
from pathlib import Path
from typing import Optional, Tuple

import pdfplumber

logger = logging.getLogger(__name__)

MESES_ES = {
    1: "ENERO", 2: "FEBRERO", 3: "MARZO", 4: "ABRIL",
    5: "MAYO", 6: "JUNIO", 7: "JULIO", 8: "AGOSTO",
    9: "SEPTIEMBRE", 10: "OCTUBRE", 11: "NOVIEMBRE", 12: "DICIEMBRE",
}


def extraer_texto_pdf(ruta: Path) -> str:
    """Extrae todo el texto de un PDF página por página."""
    if ruta is None:
        logger.warning("extraer_texto_pdf: ruta es None, retornando vacío.")
        return ""
    try:
        with pdfplumber.open(ruta) as pdf:
            return "\n".join(
                page.extract_text() or "" for page in pdf.pages
            )
    except Exception as e:
        logger.warning(f"No se pudo leer {ruta.name}: {e}")
        return ""


# ─── GUÍA ────────────────────────────────────────────────────────────────────

def extraer_datos_guia(ruta: Path) -> Tuple[Optional[str], Optional[str]]:
    """
    Retorna (waybill_limpio, fecha_iso) desde una guía DHL.
    """
    if ruta is None:
        logger.warning("extraer_datos_guia: ruta es None.")
        return None, None

    try:
        with pdfplumber.open(ruta) as pdf:
            page = pdf.pages[0]
            texto = page.extract_text() or ""

        lineas = [l.strip() for l in texto.splitlines() if l.strip()]

        # ── Fecha ────────────────────────────────────────────────────────────
        fecha = None
        for linea in lineas[:6]:
            m = re.match(r"(\d{4}-\d{2}-\d{2})", linea)
            if m:
                fecha = m.group(1)
                break

        # ── WAYBILL ──────────────────────────────────────────────────────────
        waybill = None
        for linea in lineas:
            if "WAYBILL" in linea.upper():
                numeros = re.findall(r"\d+", linea.upper().split("WAYBILL", 1)[1])
                if numeros:
                    waybill = "".join(numeros)
                break

        logger.info(f"Guía {ruta.name} → WAYBILL={waybill}  fecha={fecha}")
        return waybill, fecha

    except Exception as e:
        logger.error(f"Error extrayendo guía {ruta.name}: {e}")
        return None, None


# ─── FACTURA ─────────────────────────────────────────────────────────────────

def extraer_total_factura(ruta: Path) -> Optional[float]:
    """
    Extrae el TOTAL DOLARES de una factura Comodín.
    """
    if ruta is None:
        logger.warning("extraer_total_factura: ruta es None.")
        return None

    try:
        texto = extraer_texto_pdf(ruta)
        lineas = texto.splitlines()

        patron_fecha = re.compile(
            r"\b(\d{4}[-/]\d{2}[-/]\d{2}|\d{2}[/-]\d{2}[/-]\d{4})\b"
        )
        patron_valor = re.compile(
            r"\b(\d{1,3}(?:\.\d{3})*,\d{2}|\d+,\d{2})\b"
        )

        for linea in lineas:
            if "USD" not in linea.upper():
                continue
            m_fecha = patron_fecha.search(linea)
            if not m_fecha:
                continue

            resto = linea[m_fecha.end():]
            valores = patron_valor.findall(resto)
            if valores:
                val_str = valores[0].replace(".", "").replace(",", ".")
                total = float(val_str)
                logger.info(f"Factura {ruta.name} → TOTAL USD={total}")
                return total

        logger.warning(f"No se encontró total USD en {ruta.name}")
        return None

    except Exception as e:
        logger.error(f"Error extrayendo factura {ruta.name}: {e}")
        return None


# ─── DATO EXTERNO desde nombre de archivo ────────────────────────────────────

def extraer_dato_externo_nombre(nombre_archivo: str) -> Optional[str]:
    """
    Para facturas de época 2: extrae el dato externo (ej. CH5258) del nombre.

    Soporta dos formatos de separador:
      - Guión bajo:  OSAP148079_CH5258_1_.pdf  → partes[1] = "CH5258"
      - Espacio:     OSAP148079 CH5258.pdf     → partes[1] = "CH5258"

    Estrategia: reemplazar espacios por guiones bajos antes de splitear,
    así ambos formatos quedan normalizados.
    """
    sin_ext = Path(nombre_archivo).stem
    # Normalizar: tratar espacios igual que guiones bajos
    normalizado = sin_ext.replace(" ", "_")
    partes = normalizado.split("_")
    if len(partes) >= 2:
        return partes[1]
    return None