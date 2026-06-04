import logging
from pathlib import Path
from time import sleep
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

def descargar_reporte_sap(ruta_destino: Path) -> bool:
    max_intentos = 2
    for intento in range(1, max_intentos + 1):
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                
                logger.info(f"Iniciando sesión en SAP (Intento {intento}/{max_intentos})...")
                page.goto("https://saps4h.gco.com.co/sap/bc/gui/sap/its/webgui/?sap-client=300&sap-language=ES#")
                page.get_by_role("textbox", name="Usuario Obligatorio").fill("AUXCONMEPA1")
                page.get_by_role("textbox", name="Clave de acceso Obligatorio").fill("AuxiliarMP01*")
                page.get_by_role("button", name="Acceder al sistema Resaltado").click()
                
                logger.info("Navegando a FBL5n y generando reporte...")
                page.get_by_role("combobox", name="Indicar código de transacción").fill("FBL5n")
                page.get_by_role("combobox", name="Indicar código de transacción").press("ArrowDown")
                page.get_by_role("combobox", name="Indicar código de transacción").press("Enter")
                
                sleep(1)
                page.get_by_role("textbox", name="Cuenta de deudor").fill("3000000674")
                page.get_by_role("textbox", name="Cuenta de deudor").press("ArrowDown")
                page.get_by_role("textbox", name="Cuenta de deudor").press("Enter")

                sleep(1)
                page.get_by_role("textbox", name="Sociedad").click()
                page.get_by_role("textbox", name="Sociedad").fill("1000")
                page.get_by_role("textbox", name="Sociedad").press("ArrowDown")
                page.get_by_role("textbox", name="Sociedad").press("Enter")
                
                sleep(1)
                page.get_by_role("checkbox", name="Operaciones CME").click()
                page.get_by_role("checkbox", name="Apuntes estadísticos").click()
                page.get_by_role("button", name="Ejecutar Resaltado").click()
                
                sleep(4)
                logger.info("Exportando archivo...")
                page.locator("#userarealist0").press("Shift+F4")

                page.get_by_role("textbox", name="Nom.arch.").fill("soporte_the_goose_brand")
                page.get_by_role("button", name="Exportar a...").click()
                with page.expect_download() as download_info:
                    with page.expect_popup() as page1_info:
                        page.get_by_role("button", name="OK").click()
                    page1 = page1_info.value
                download = download_info.value

                download.save_as(ruta_destino)
                logger.info(f"Reporte descargado a {ruta_destino}")

                page1.close()
                context.close()
                browser.close()

                return True
        except Exception as e:
            logger.warning(f"Error en intento {intento} de SAP: {e}")
            if intento == max_intentos:
                logger.error("Se agotaron los reintentos para descargar el reporte de SAP.")
                return False
            sleep(3) # Esperar un poco antes de reabrir el navegador
    return False