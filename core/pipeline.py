"""
PIPELINE ORQUESTADOR - The goose Brand
Coordina todos los pasos: lectura Excel → búsqueda → extracción → escritura.
"""

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from core.actualizador_excel import (
    ActualizadorExcel,
    COL_ASIGNACION,
    COL_FECHA_DOC,
    COL_GUIA,
    COL_REFERENCIA,
    COL_VALOR_FACT,
    _es_vacio,
)
from core.buscador import buscar_factura, buscar_guia, determinar_epoca, limpiar_indice
from core.extractor_pdf import extraer_datos_guia, extraer_total_factura
from core.descargador_sap import descargar_reporte_sap
from core.consolidador import agregar_nuevos_registros
from utils.gestor_rutas import copiar_documentos_registro
from models.reporte import Reporte, ResultadoRegistro

logger = logging.getLogger(__name__)


def _generar_observacion(
    tiene_guia: bool,
    ok_guia: bool,
    tiene_factura: bool,
    ok_factura: bool,
) -> str:
    guia_ok       = tiene_guia and ok_guia
    guia_ilegible = tiene_guia and not ok_guia
    fact_ok       = tiene_factura and ok_factura
    fact_ilegible = tiene_factura and not ok_factura

    if guia_ok and fact_ok:
        return "Completo"
    if not tiene_guia and fact_ok:
        return "Falta Guia de Transporte"
    if guia_ok and not tiene_factura:
        return "Falta Factura comercial"
    if not tiene_guia and not tiene_factura:
        return "Faltan ambos documentos"
    if guia_ilegible and fact_ilegible:
        return "No se pudieron leer los documentos"
    if guia_ilegible and fact_ok:
        return "No se pudo leer la guia"
    if guia_ok and fact_ilegible:
        return "No se pudo leer la factura"
    if not tiene_guia and fact_ilegible:
        return "Falta guia y no se pudo leer la factura"
    if guia_ilegible and not tiene_factura:
        return "Falta factura y no se pudo leer la guia"
    return "Estado indeterminado"


def ejecutar_pipeline(
        ruta_excel: Path,
        ruta_busqueda: Path,
        ruta_destino: Path,
        callback_progreso: Optional[Callable[[int, int, str], None]] = None,
        callback_log: Optional[Callable[[str], None]] = None,
        fecha_desde: Optional[datetime] = None,
        fecha_hasta: Optional[datetime] = None,
        cancelar_flag: Optional[threading.Event] = None,
    ) -> Reporte:
    """
    Pipeline completo The goose Brand.

    Args:
        cancelar_flag: threading.Event que, si se activa, detiene el loop
                       limpiamente después del registro en curso y guarda el Excel.
    """

    def log(msg: str):
        logger.info(msg)
        if callback_log:
            callback_log(msg)

    reporte = Reporte()

    # Limpiar índice de PDFs de ejecuciones anteriores
    limpiar_indice()

    # ── 0. Descarga SAP y Consolidación ─────────────────────────────────────
    ruta_descarga_sap = ruta_excel.parent / "reporte_sap_temporal.xlsx"
    
    log("Iniciando automatización de SAP...")
    if descargar_reporte_sap(ruta_descarga_sap):
        log("Consolidando nuevos registros en el maestro...")
        agregar_nuevos_registros(ruta_excel, ruta_descarga_sap, columna_cruce="Referencia")
    else:
        log("⚠ Hubo un problema con SAP. Continuando con los datos existentes.")

    # ── 1. Cargar Excel ─────────────────────────────────────────────────────
    log("Cargando Excel maestro...")
    actualizador = ActualizadorExcel(ruta_excel)
    if not actualizador.cargar():
        log("❌ No se pudo cargar el Excel maestro. Abortando.")
        return reporte

    pendientes = actualizador.obtener_pendientes()

    # Aplicar filtro de fechas si se proporcionó
    if fecha_desde or fecha_hasta:
        import pandas as pd
        if fecha_desde:
            pendientes = pendientes[
                pendientes[COL_FECHA_DOC] >= pd.Timestamp(fecha_desde)
            ]
        if fecha_hasta:
            pendientes = pendientes[
                pendientes[COL_FECHA_DOC] <= pd.Timestamp(fecha_hasta)
            ]

    reporte.total_pendientes = len(pendientes)
    log(f"Registros pendientes a procesar: {reporte.total_pendientes}")

    if reporte.total_pendientes == 0:
        log("✔ No hay registros pendientes. Pipeline finalizado.")
        return reporte

    # ── 2. Procesar cada registro ───────────────────────────────────────────
    for numero, (idx, fila) in enumerate(pendientes.iterrows(), start=1):

        # Verificar cancelación al inicio de cada registro
        if cancelar_flag and cancelar_flag.is_set():
            log(f"⚠ Cancelado por el usuario en registro {numero}/{reporte.total_pendientes}.")
            break

        referencia = str(fila.get(COL_REFERENCIA, "")).strip()
        asignacion = str(fila.get(COL_ASIGNACION, "")).strip()
        fecha_doc  = fila.get(COL_FECHA_DOC)

        if fecha_doc is None or str(fecha_doc).lower() in ("nat", "nan", ""):
            log(f"[{numero}/{reporte.total_pendientes}] ⚠ Fecha inválida para ref={referencia}, omitido.")
            continue

        fecha = fecha_doc.date() if hasattr(fecha_doc, "date") else fecha_doc
        epoca = determinar_epoca(fecha)
        msg_base = f"[{numero}/{reporte.total_pendientes}] ref={referencia} época={epoca}"
        log(f"Procesando {msg_base}...")

        if callback_progreso:
            callback_progreso(numero, reporte.total_pendientes, msg_base)

        # ── 3. Determinar qué falta realmente ──────────────────────────────
        guia_ya_existe   = not _es_vacio(fila.get(COL_GUIA, ""))
        valor_ya_existe  = not _es_vacio(fila.get(COL_VALOR_FACT, ""))

        # Siempre buscamos la factura si el valor no existe o si falta la guía 
        # (ya que el nombre de la factura puede ayudar a encontrar la guía)
        necesita_factura_para_guia = not guia_ya_existe
        ruta_factura = (
            buscar_factura(referencia, fecha, ruta_busqueda)
            if not valor_ya_existe or necesita_factura_para_guia
            else None
        )
        ruta_guia    = buscar_guia(referencia, asignacion, fecha, ruta_busqueda, ruta_factura) if not guia_ya_existe else None

        tiene_factura = ruta_factura is not None or valor_ya_existe
        tiene_guia    = ruta_guia is not None or guia_ya_existe

        resultado = ResultadoRegistro(
            referencia=referencia,
            asignacion=asignacion,
            fecha=str(fecha),
        )

        if not tiene_factura and not tiene_guia:
            obs = _generar_observacion(False, False, False, False)
            resultado.observacion = obs
            actualizador.actualizar_fila(idx, None, None, None, obs)
            reporte.registrar(resultado)
            log(f"  ⚠ {obs}")
            continue

        # ── 4. Copiar archivos al destino ───────────────────────────────────
        fact_dest, guia_dest = copiar_documentos_registro(
            ruta_factura, ruta_guia, ruta_destino, fecha
        )

        # ── 5. Extraer datos de los PDFs ────────────────────────────────────
        waybill, fecha_guia, total_usd = None, None, None

        src_guia = guia_dest or ruta_guia
        if src_guia is not None:
            waybill, fecha_guia = extraer_datos_guia(src_guia)

        if tiene_factura:
            src_fact = fact_dest or ruta_factura
            if src_fact is not None:
                total_usd = extraer_total_factura(src_fact)

        # ── 6. Generar observación unificada ────────────────────────────────
        ok_guia    = waybill is not None or guia_ya_existe
        ok_factura = total_usd is not None or valor_ya_existe

        obs = _generar_observacion(
            tiene_guia, ok_guia,
            tiene_factura, ok_factura,
        )

        # ── 7. Actualizar Excel ─────────────────────────────────────────────
        actualizador.actualizar_fila(
            idx,
            waybill=waybill,
            fecha_guia=fecha_guia,
            valor_factura=total_usd,
            observacion=obs,
        )

        resultado.waybill       = waybill or ""
        resultado.valor_factura = str(total_usd) if total_usd else ""
        resultado.observacion   = obs
        reporte.registrar(resultado)

        estado = "✔" if obs == "Completo" else "⚠"
        log(f"USD={total_usd}  {obs}")

    # ── 8. Guardar Excel ────────────────────────────────────────────────────
    log("Guardando Excel maestro...")
    if actualizador.guardar():
        log("✔ Excel guardado exitosamente.")
    else:
        log("❌ Error al guardar el Excel.")

    log(reporte.resumen_texto())
    return reporte