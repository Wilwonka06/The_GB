"""
GESTOR DE CONFIGURACIÓN - The goose Brand
Maneja la persistencia de rutas en config_indigo.ini
"""

import configparser
from pathlib import Path
from typing import Optional


class ConfiguradorNewIndigo:
    CONFIG_FILE = Path("config_indigo.ini")

    def __init__(self):
        self.config = configparser.ConfigParser()

    def cargar_config(self) -> bool:
        if not self.CONFIG_FILE.exists():
            return False
        self.config.read(self.CONFIG_FILE, encoding="utf-8")
        return "RUTAS" in self.config

    def obtener_rutas(self) -> Optional[dict]:
        if "RUTAS" not in self.config:
            return None
        r = self.config["RUTAS"]
        return {
            "ruta_maestro":    Path(r.get("ruta_maestro", "")),
            "ruta_busqueda":   Path(r.get("ruta_busqueda", "")),
            "ruta_destino":    Path(r.get("ruta_destino", "")),
        }

    def guardar_config(self, ruta_maestro: str, ruta_busqueda: str, ruta_destino: str) -> bool:
        try:
            self.config["RUTAS"] = {
                "ruta_maestro":  ruta_maestro,
                "ruta_busqueda": ruta_busqueda,
                "ruta_destino":  ruta_destino,
            }
            with open(self.CONFIG_FILE, "w", encoding="utf-8") as f:
                self.config.write(f)
            return True
        except Exception as e:
            print(f"[Config] Error al guardar: {e}")
            return False