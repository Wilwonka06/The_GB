import re
from time import sleep

from playwright.sync_api import Playwright, sync_playwright, expect


def run(playwright: Playwright) -> None:
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://saps4h.gco.com.co/sap/bc/gui/sap/its/webgui/?sap-client=300&sap-language=ES#")
    page.get_by_role("textbox", name="Usuario Obligatorio").press("CapsLock")
    page.get_by_role("textbox", name="Usuario Obligatorio").fill("AUXCONMEPA1")
    page.get_by_role("textbox", name="Clave de acceso Obligatorio").click()
    page.get_by_role("textbox", name="Clave de acceso Obligatorio").fill("A")
    page.get_by_role("textbox", name="Clave de acceso Obligatorio").press("CapsLock")
    page.get_by_role("textbox", name="Clave de acceso Obligatorio").fill("AuxiliarMP01*")
    page.get_by_role("button", name="Acceder al sistema Resaltado").click()
    page.get_by_role("combobox", name="Indicar código de transacción").fill("FBL5n")
    page.get_by_role("combobox", name="Indicar código de transacción").press("ArrowDown")
    page.get_by_role("combobox", name="Indicar código de transacción").press("Enter")
    page.get_by_role("textbox", name="Cuenta de deudor").fill("3000000674")
    page.get_by_role("textbox", name="Cuenta de deudor").press("ArrowDown")
    page.get_by_role("textbox", name="Cuenta de deudor").press("Enter")
    page.get_by_role("textbox", name="Sociedad").click()
    page.get_by_role("textbox", name="Sociedad").fill("1000")
    page.get_by_role("textbox", name="Sociedad").press("ArrowDown")
    page.get_by_role("textbox", name="Sociedad").press("Enter")
    page.get_by_role("checkbox", name="Operaciones CME").click()
    page.get_by_role("checkbox", name="Apuntes estadísticos").click()
    page.get_by_role("button", name="Ejecutar  Resaltado").click()
    sleep(5)
    page.locator("#userarealist0").press("Shift+F4")
    page.get_by_role("textbox", name="Nom.arch.").fill("soporte_the_goose_brand")
    page.get_by_role("button", name="Exportar a...").click()
    with page.expect_download() as download_info:
        with page.expect_popup() as page1_info:
            page.get_by_role("button", name="OK").click()
        page1 = page1_info.value
    download = download_info.value
    page1.close()

    # ---------------------
    context.close()
    browser.close()


with sync_playwright() as playwright:
    run(playwright)
