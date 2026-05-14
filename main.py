import os
# Forzar a Playwright a usar el navegador empaquetado localmente
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"

import logging
from interfaz import NewIndigoApp

if __name__ == "__main__":
    logging.basicConfig(    
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    app = NewIndigoApp()
    app.mainloop()