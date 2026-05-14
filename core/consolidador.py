import logging
import pandas as pd
from pathlib import Path
from openpyxl import load_workbook
from openpyxl.utils.dataframe import dataframe_to_rows

logger = logging.getLogger(__name__)

def agregar_nuevos_registros(ruta_maestro: Path, ruta_sap: Path, columna_cruce: str = "Referencia"):
    """
    Lee el reporte descargado de SAP y agrega al maestro únicamente 
    los registros que no existan previamente.
    """
    logger.info("Cruzando datos de SAP con el Excel maestro...")
    try:
        # 1. Leer ambos archivos
        df_maestro = pd.read_excel(ruta_maestro, sheet_name="Data")
        df_sap = pd.read_excel(ruta_sap)
        
        df_maestro.columns = df_maestro.columns.str.strip()
        df_sap.columns = df_sap.columns.str.strip()

        # Limpieza robusta de ".0" para columnas clave en SAP
        for col_texto in ["Nº documento", "Referencia", "Asignación"]:
            if col_texto in df_sap.columns:
                df_sap[col_texto] = df_sap[col_texto].apply(
                    lambda x: None if pd.isna(x) else str(x).strip()[:-2] if str(x).strip().endswith(".0") else str(x).strip()
                )

        # 2. Filtrar los que NO están en el maestro
        if columna_cruce in df_maestro.columns:
            registros_existentes = df_maestro[columna_cruce].dropna().astype(str).str.strip()
            registros_existentes = registros_existentes.apply(lambda x: x[:-2] if x.endswith(".0") else x).tolist()
        else:
            registros_existentes = []

        mask = ~df_sap[columna_cruce].dropna().astype(str).str.strip().isin(registros_existentes)
        df_nuevos = df_sap.loc[df_sap[columna_cruce].notna() & mask].copy()
        
        if df_nuevos.empty:
            logger.info("No hay registros nuevos para agregar al maestro.")
            return
            
        # Alinear columnas al maestro
        for col in df_maestro.columns:
            if col not in df_nuevos.columns:
                df_nuevos[col] = None
                
        df_nuevos = df_nuevos[df_maestro.columns]

        # Forzar que la fecha no guarde la hora y tenga formato con slash (DD/MM/YYYY)
        if "Fecha de documento" in df_nuevos.columns:
            df_nuevos["Fecha de documento"] = pd.to_datetime(df_nuevos["Fecha de documento"], errors='coerce').dt.strftime('%d/%m/%Y')

        # 3. Escribir los nuevos registros al final del archivo maestro usando openpyxl
        logger.info(f"Agregando {len(df_nuevos)} registros nuevos al maestro.")
        wb = load_workbook(ruta_maestro)
        ws = wb["Data"]
        
        for row in df_nuevos.itertuples(index=False, name=None):
            row_cleaned = [None if pd.isna(x) or str(x).strip().lower() in ("nan", "<na>", "nat") else x for x in row]
            ws.append(row_cleaned)
            
        wb.save(ruta_maestro)
    except Exception as e:
        logger.error(f"Error consolidando registros: {e}")