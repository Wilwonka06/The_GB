"""
ACTUALIZADOR EXCEL MAESTRO - The goose Brand
Lee el archivo NEW_INDIGO.xlsx y escribe los campos:
  - Guia
  - Fecha de creacion guia
  - Valor factura
  - Observaciones
Solo procesa registros donde Guia y Valor factura estén vacíos.

Estrategia de escritura:
  NO se reescribe el DataFrame completo. Se abre el archivo con openpyxl
  y se escriben ÚNICAMENTE las celdas que el pipeline calculó, celda por
  celda. Esto garantiza que cualquier columna extra, dato ingresado
  manualmente, formato o fecha en cualquier otra columna quede intacto.
"""

import logging
from pathlib import Path
from typing import Optional

import pandas as pd
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

logger = logging.getLogger(__name__)

HOJA = "Data"

COL_ASIGNACION  = "Asignación"
COL_REFERENCIA  = "Referencia"
COL_FECHA_DOC   = "Fecha de documento"
COL_GUIA        = "Guia"
COL_FECHA_GUIA  = "Fecha de creacion guia"
COL_VALOR_FACT  = "Valor factura"
COL_OBS         = "Observaciones"
COL_VALOR_REG   = "Importe en moneda doc."
COL_DIFERENCIA  = "Diferencia"

# Únicas columnas que el pipeline tiene permitido escribir
COLUMNAS_ESCRITURA = {COL_GUIA, COL_FECHA_GUIA, COL_VALOR_FACT, COL_OBS, COL_DIFERENCIA}


def _es_vacio(val) -> bool:
    """True si el valor es NaN, None, cadena vacía o 'nan'."""
    if val is None:
        return True
    if pd.isna(val):
        return True
    s = str(val).strip().lower()
    return s in ("nan", "none", "nat", "", "<na>")


class ActualizadorExcel:
    def __init__(self, ruta_excel: Path):
        self.ruta = ruta_excel
        self.df: Optional[pd.DataFrame] = None

        self._cambios: dict[int, dict[str, object]] = {}

        # Mapa nombre_columna → número de columna Excel (1-based)
        self._col_idx: dict[str, int] = {}

        # Mapa pandas_idx → número de fila Excel (1-based, fila 1 = encabezado)
        self._fila_excel: dict[int, int] = {}

    def cargar(self) -> bool:
        """Carga el Excel en memoria. Retorna True si OK."""
        try:
            # 0. Asegurar que las columnas obligatorias de escritura existan en el archivo
            wb_temp = load_workbook(self.ruta)
            ws_temp = wb_temp[HOJA]
            encabezados_temp = {str(c.value).strip(): c.column for c in ws_temp[1] if c.value is not None}
            
            faltantes = COLUMNAS_ESCRITURA - set(encabezados_temp.keys())
            if faltantes:
                logger.info(f"Creando columnas faltantes en el maestro: {faltantes}")
                max_col = ws_temp.max_column
                for col_name in faltantes:
                    max_col += 1
                    ws_temp.cell(row=1, column=max_col, value=col_name)
                wb_temp.save(self.ruta)
            wb_temp.close()

            # 1. Ahora sí leer el DataFrame con Pandas
            self.df = pd.read_excel(
                self.ruta,
                sheet_name=HOJA,
                engine="openpyxl",
            )

            self.df.columns = self.df.columns.str.strip()

            # Convertir columnas de escritura a tipo flexible para evitar colisiones de tipo float/str
            for col in COLUMNAS_ESCRITURA:
                if col in self.df.columns:
                    self.df[col] = self.df[col].astype(object)

            # Leer encabezados reales del archivo para construir el mapa de columnas
            wb = load_workbook(self.ruta, read_only=True, data_only=True)
            ws = wb[HOJA]
            for cell in ws[1]:  # fila 1 = encabezados
                if cell.value is not None:
                    self._col_idx[str(cell.value).strip()] = cell.column
            wb.close()

            # pandas_idx 0 → fila Excel 2 (fila 1 es el encabezado)
            for pandas_idx in self.df.index:
                self._fila_excel[pandas_idx] = pandas_idx + 2

            # Convertir a datetime solo para filtros internos
            self.df[COL_FECHA_DOC] = pd.to_datetime(
                self.df[COL_FECHA_DOC], errors="coerce", dayfirst=True
            )

            logger.info(f"Excel cargado: {len(self.df)} registros")
            logger.info(f"Columnas detectadas: {list(self._col_idx.keys())}")
            return True

        except Exception as e:
            logger.error(f"Error cargando Excel: {e}")
            return False

    def obtener_pendientes(self) -> pd.DataFrame:
        """
        Retorna filas que realmente necesitan procesamiento:
        - Sin Guia Y sin Valor factura  → nunca procesados
        - Con Guia pero sin Valor factura → solo falta valor
        - Sin Guia pero con Valor factura → solo falta guía
        """
        if self.df is None:
            return pd.DataFrame()

        sin_guia  = self.df[COL_GUIA].apply(_es_vacio)
        sin_valor = self.df[COL_VALOR_FACT].apply(_es_vacio)
        
        if COL_DIFERENCIA in self.df.columns:
            sin_dif = self.df[COL_DIFERENCIA].apply(_es_vacio)
        else:
            sin_dif = pd.Series(True, index=self.df.index)

        mask = sin_guia | sin_valor | sin_dif
        pendientes = self.df[mask].copy()
        logger.info(f"Registros pendientes: {len(pendientes)} "
                    f"(sin guia={sin_guia.sum()}, sin valor={sin_valor.sum()}, sin diferencia={sin_dif.sum()})")
        return pendientes

    def actualizar_fila(
        self,
        idx: int,
        waybill: Optional[str],
        fecha_guia: Optional[str],
        valor_factura: Optional[float],
        observacion: str = "",
    ) -> None:
        """
        Acumula los valores calculados para esta fila.
        NUNCA sobreescribe un campo que ya tiene valor (excepto Observaciones).
        No escribe al archivo todavía — solo registra los cambios en memoria.
        """
        if self.df is None:
            return

        cambios_fila: dict[str, object] = {}

        if waybill and _es_vacio(self.df.at[idx, COL_GUIA]):
            cambios_fila[COL_GUIA] = str(waybill)
            self.df.at[idx, COL_GUIA] = str(waybill)

        if fecha_guia and _es_vacio(self.df.at[idx, COL_FECHA_GUIA]):
            cambios_fila[COL_FECHA_GUIA] = fecha_guia
            self.df.at[idx, COL_FECHA_GUIA] = fecha_guia

        if valor_factura is not None and _es_vacio(self.df.at[idx, COL_VALOR_FACT]):
            cambios_fila[COL_VALOR_FACT] = float(valor_factura)
            self.df.at[idx, COL_VALOR_FACT] = float(valor_factura)

        # Se incluye la fórmula de diferencia si se actualizó algún dato
        cambios_fila[COL_DIFERENCIA] = "FORMULA_DIFERENCIA"

        # Observaciones siempre se actualiza — refleja el estado actual
        cambios_fila[COL_OBS] = observacion
        self.df.at[idx, COL_OBS] = observacion

        if cambios_fila:
            self._cambios[idx] = cambios_fila

    def guardar(self) -> bool:
        """
        Escribe SOLO las celdas calculadas por el pipeline usando openpyxl.
        """
        if not self._cambios:
            logger.info("Sin cambios que guardar.")
            return True

        # Verificar que las columnas a escribir existen en el archivo
        columnas_faltantes = COLUMNAS_ESCRITURA - set(self._col_idx.keys())
        if columnas_faltantes:
            logger.error(
                f"Columnas no encontradas en el Excel: {columnas_faltantes}. "
                f"Columnas disponibles: {list(self._col_idx.keys())}"
            )
            return False

        try:
            wb = load_workbook(self.ruta)
            ws = wb[HOJA]

            col_valor_reg_letra = get_column_letter(self._col_idx.get(COL_VALOR_REG, 5))
            col_valor_fact_letra = get_column_letter(self._col_idx.get(COL_VALOR_FACT, 10))

            celdas_escritas = 0
            for pandas_idx, campos in self._cambios.items():
                fila_excel = self._fila_excel.get(pandas_idx)
                if fila_excel is None:
                    logger.warning(f"No se encontró fila Excel para idx={pandas_idx}")
                    continue

                for col_nombre, valor in campos.items():
                    col_excel = self._col_idx.get(col_nombre)
                    if col_excel is None:
                        logger.warning(f"Columna '{col_nombre}' no encontrada, omitida")
                        continue

                    if col_nombre == COL_DIFERENCIA and valor == "FORMULA_DIFERENCIA":
                        valor = f"=SUM({col_valor_reg_letra}{fila_excel}-{col_valor_fact_letra}{fila_excel})"

                    ws.cell(row=fila_excel, column=col_excel, value=valor)
                    celdas_escritas += 1

            wb.save(self.ruta)
            wb.close()

            logger.info(
                f"Excel guardado: {celdas_escritas} celdas en "
                f"{len(self._cambios)} filas → {self.ruta}"
            )
            return True

        except Exception as e:
            logger.error(f"Error guardando Excel: {e}")
            return False

    def obtener_valor(self, idx: int, columna: str) -> str:
        """Retorna el valor de una celda específica como string."""
        if self.df is None:
            return ""
        val = self.df.at[idx, columna]
        return "" if _es_vacio(val) else str(val).strip()