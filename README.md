# The goose Brand V2.0.0

Sistema de automatización avanzado para la conciliación de facturas y guías de transporte.

---

## 1. Información General
*   **Proyecto:** The goose Brand
*   **Objetivo:** Automatizar completamente el proceso de conciliación de facturas comerciales y guías de transporte DHL, integrando datos descargados automáticamente desde SAP con archivos físicos (PDFs), extrayendo información crítica mediante técnicas de procesamiento de texto y OCR, y actualizando de forma segura un archivo maestro de Excel preservando formatos y fórmulas existentes. El sistema elimina duplicados, maneja búsquedas inteligentes por múltiples criterios, y proporciona una interfaz gráfica intuitiva para monitoreo y control en tiempo real.
*   **Autor:** GCO Corporativo, Wilson Rojas
*   **Fecha:** 2026/05/14
*   **Versión:** 2.0.0

---

## 2. Funcionalidades Principales
1.  **Automatización SAP:** Descarga automática y programática de reportes de cuentas por cobrar mediante Playwright, simulando navegación web en la transacción FBL5n de SAP S/4HANA, con sistema de reintento automático en caso de fallos de conexión o interfaz.
2.  **Cruce de Datos Inteligente:** Consolidación automática de nuevos registros SAP en el archivo maestro Excel, comparando referencias para evitar duplicados y manteniendo la integridad histórica de los datos.
3.  **Búsqueda Multimétodo de PDFs:** Algoritmo de localización avanzado que busca archivos PDF en estructuras de directorios complejas probando múltiples criterios en orden de prioridad: **Asignación** (prioridad máxima para época 3), **Referencia**, y **Dato Externo** (extraído del nombre de la factura), con caché de búsquedas para optimización de rendimiento.
4.  **Extracción de Datos OCR y Texto:** Procesamiento automático de PDFs para extraer Waybills de guías DHL, fechas de emisión, y montos totales en USD de facturas comerciales, utilizando técnicas de reconocimiento de patrones y OCR cuando es necesario.
5.  **Actualización Segura del Excel:** Escritura incremental celda por celda en el maestro Excel usando openpyxl, preservando completamente formatos, colores, bordes, fórmulas y estilos existentes sin corromper el archivo.
6.  **Interfaz Gráfica Moderna:** Aplicación GUI construida con CustomTkinter que ofrece control completo del pipeline, monitoreo en tiempo real con barras de progreso, logs detallados, filtros por rango de fechas, capacidad de cancelación segura, y visualización de resultados con estadísticas y observaciones.

---

## 3. Estructura del Proyecto
El proyecto sigue una arquitectura modular y escalable para facilitar el mantenimiento, testing y extensiones futuras:

```text
C:\Proyectos Comodin\The_goose_brand\
├── core/                       # Lógica central del sistema (Pipeline)
│   ├── actualizador_excel.py   # Gestión segura de actualización del Excel maestro
│   ├── buscador.py             # Motor inteligente de búsqueda de PDFs con estrategias múltiples
│   ├── consolidador.py         # Lógica de cruce y consolidación de datos SAP
│   ├── descargador_sap.py      # Automatización completa de descarga desde SAP WebGUI
│   ├── extractor_pdf.py        # Procesamiento y extracción de datos desde PDFs
│   └── pipeline.py             # Orquestador principal que coordina todo el flujo
├── models/                     # Definiciones de estructuras de datos
│   └── reporte.py              # Clases para reporte de ejecución y resultados
├── utils/                      # Utilidades transversales
│   ├── config_manager.py       # Gestión persistente de configuración y rutas
│   └── gestor_rutas.py         # Manejo de copias físicas y organización de archivos
├── main.py                     # Punto de entrada principal de la aplicación
├── interfaz.py                 # Interfaz gráfica de usuario completa
├── requirements.txt            # Lista de dependencias Python
└── compilar.bat                # Script de compilación a ejecutable standalone
```

---

## 3.1 Funciones Detalladas de Módulos

### Core Modules
- **`pipeline.py`**: Es el corazón del sistema. Coordina la ejecución secuencial de todas las fases: descarga SAP, consolidación, búsqueda de PDFs, extracción de datos, actualización Excel y generación de reportes. Implementa callbacks para progreso y logging, manejo de cancelaciones seguras, y filtros por fechas.
- **`descargador_sap.py`**: Maneja la automatización completa de SAP usando Playwright. Navega a la WebGUI de SAP S/4HANA, autentica con credenciales específicas, ejecuta la transacción FBL5n con parámetros predefinidos (cuenta deudor 3000000674, sociedad 1000), filtra por operaciones CME y apuntes estadísticos, y descarga el reporte en formato Excel. Incluye reintentos automáticos con reinicio del navegador.
- **`buscador.py`**: Implementa un motor de búsqueda inteligente para localizar PDFs en estructuras de directorios profundas. Utiliza estrategias por épocas (1, 2, 3) con prioridades específicas: asignación numérica (época 3), referencia exacta, y dato externo extraído del nombre de factura. Emplea caché liviano para evitar búsquedas redundantes y glob recursivo eficiente para minimizar uso de memoria.
- **`consolidador.py`**: Realiza el cruce inteligente entre datos SAP descargados y el maestro Excel existente, agregando solo registros nuevos basados en referencias únicas para evitar duplicados.
- **`actualizador_excel.py`**: Gestiona la actualización segura del archivo Excel maestro. Utiliza escritura celda por celda con openpyxl para preservar formatos, fórmulas y estilos. Identifica columnas por nombre y actualiza selectivamente campos como Waybill, fecha guía, valor factura y observaciones.
- **`extractor_pdf.py`**: Procesa PDFs de guías DHL y facturas comerciales. Extrae Waybills mediante patrones de texto, fechas de emisión, y montos totales en USD usando expresiones regulares y procesamiento de texto plano.

### Models
- **`reporte.py`**: Define estructuras de datos para el reporte de ejecución, incluyendo estadísticas de procesamiento, observaciones por registro, y resumen textual. La clase `Reporte` acumula resultados y la clase `ResultadoRegistro` representa cada registro procesado con sus metadatos.

### Utils
- **`config_manager.py`**: Maneja la persistencia de configuración del usuario (rutas de Excel, búsqueda y destino) usando archivos JSON en el directorio de usuario. Proporciona validación y carga/guardado seguro.
- **`gestor_rutas.py`**: Gestiona operaciones de sistema de archivos: copia física de documentos encontrados a rutas organizadas por año/mes, creación de directorios si no existen, y manejo de rutas relativas/absolutas.

### Interface
- **`interfaz.py`**: Implementa una aplicación GUI completa con CustomTkinter. Incluye tres estados principales (IDLE, RUNNING, COMPLETED), configuración modal, filtros de fecha, monitoreo en tiempo real con barras de progreso, logs scrollables, estadísticas visuales, y capacidad de cancelación del pipeline.
- **`main.py`**: Punto de entrada simple que inicializa y lanza la interfaz gráfica.

---

## 4. Metodología y Flujo de Trabajo
The goose Brand opera bajo una metodología secuencial y robusta, con manejo de errores, logging detallado y capacidad de cancelación segura. El proceso está diseñado para ser idempotente y resistente a fallos parciales.

### 4.1 Paso a Paso Detallado del Pipeline

1.  **Inicialización y Configuración**:
    - Carga de rutas configuradas (Excel maestro, directorio de búsqueda PDFs, ruta destino).
    - Limpieza del caché de búsquedas de ejecuciones anteriores.
    - Aplicación de filtros opcionales por rango de fechas (desde/hasta).

2.  **Descarga Automática desde SAP**:
    - Lanzamiento de navegador Chromium headless con Playwright.
    - Navegación a WebGUI de SAP S/4HANA (URL específica de GCO).
    - Autenticación automática con credenciales predefinidas (usuario: AUXCONMEPA1, sociedad: 1000).
    - Ejecución de transacción FBL5n con filtros específicos:
        - Cuenta deudor: 3000000674
        - Sociedad: 1000
        - Operaciones CME: activado
        - Apuntes estadísticos: activado
    - Exportación del reporte como archivo Excel temporal.
    - Sistema de reintento: hasta 2 intentos con reinicio completo del navegador en caso de fallo.

3.  **Consolidación de Datos SAP**:
    - Carga del reporte SAP descargado.
    - Comparación con registros existentes en el maestro Excel por columna "Referencia".
    - Adición exclusiva de registros nuevos para evitar duplicados.
    - Actualización del maestro con nuevos datos SAP.

4.  **Identificación de Registros Pendientes**:
    - Análisis del maestro Excel para identificar registros sin Guía de Transporte o sin Valor de Factura.
    - Determinación de la "época" del registro basada en fecha (época 1: <2025-01-01, época 2: 2025-01-01 a 2025-10-31, época 3: >=2025-11-01).
    - Preparación de lista de registros a procesar con filtros de fecha aplicados.

5.  **Búsqueda Inteligente de PDFs**:
    - Para cada registro pendiente, búsqueda en el árbol de directorios configurado.
    - Estrategia multimétodo por prioridades:
        - **Método 1 (Asignación - Época 3)**: Búsqueda por número de asignación extraído y limpiado (solo dígitos).
        - **Método 2 (Referencia)**: Búsqueda exacta por referencia del registro.
        - **Método 3 (Dato Externo - Época 2)**: Extracción de dato externo del nombre de la factura encontrada, usado como clave para buscar guía.
    - Uso de caché liviano para evitar búsquedas redundantes en la misma ejecución.
    - Retorno del primer PDF encontrado que coincida con criterios (guías vs facturas).

6.  **Procesamiento y Extracción de Datos**:
    - Copia física de archivos encontrados a ruta destino organizada por `Año/Mes`.
    - Para guías DHL: extracción de Waybill mediante patrones de texto y OCR si necesario.
    - Para facturas comerciales: extracción de total USD usando expresiones regulares en texto plano.
    - Generación de observaciones unificadas basadas en disponibilidad de documentos y éxito de extracción.

7.  **Actualización Segura del Excel Maestro**:
    - Escritura celda por celda usando openpyxl para preservar formatos, colores, bordes y fórmulas.
    - Actualización selectiva de columnas: Waybill, Fecha Guía, Valor Factura, Observación.
    - Guardado del archivo con validación de integridad.

8.  **Generación de Reporte y Finalización**:
    - Compilación de estadísticas: total procesados, completados, errores, etc.
    - Creación de lista de observaciones por registro.
    - Logging completo del proceso para auditoría.
    - Limpieza de archivos temporales.

### 4.2 Características Técnicas de la Metodología
- **Idempotencia**: El proceso puede re-ejecutarse múltiples veces sin efectos secundarios.
- **Resiliencia**: Manejo de errores parciales, continuando con registros válidos.
- **Cancelación Segura**: Interrupción limpia en cualquier punto, guardando progreso.
- **Eficiencia**: Caché de búsquedas, procesamiento por lotes, minimización de I/O.
- **Auditoría**: Logging detallado en tiempo real con niveles de severidad.

---

## 5. Instalación y Configuración

### 5.1 Instalación Paso a Paso

1.  **Clonación/Descarga del Proyecto**:
    ```bash
    # Navegar al directorio deseado
    cd "C:\Proyectos Comodin"
    # El proyecto ya está ubicado en: C:\Proyectos Comodin\The_goose_brand
    ```

2.  **Creación de Entorno Virtual**:
    ```bash
    # Crear entorno virtual
    python -m venv venv_thegoose

    # Activar entorno virtual
    venv_thegoose\Scripts\activate
    ```

3.  **Instalación de Dependencias**:
    ```bash
    # Instalar paquetes Python
    pip install -r requirements.txt

    # Instalar navegador Chromium para Playwright
    playwright install chromium
    ```

4.  **Verificación de Instalación**:
    ```bash
    # Verificar versiones
    python --version
    pip list | findstr "pandas playwright"

    # Probar importación básica
    python -c "import pandas, playwright, customtkinter; print('Instalación exitosa')"
    ```

### 5.2 Configuración Inicial

1.  **Ejecución por Primera Vez**:
    - Ejecutar `main.py` directamente.
    - La aplicación se abrirá en modo interfaz gráfica.

2.  **Configuración de Rutas** (Obligatorio):
    - Hacer clic en "⚙ Configuración" en la interfaz.
    - Configurar las tres rutas principales:
        - **Excel Historial (NEW_INDIGO)**: Ruta al archivo maestro Excel (ej: `O:\Finanzas\Info Bancos\Pagos Internacionales\The Goose Brand\NEW_INDIGO.xlsx`)
        - **Ruta de búsqueda (PDFs fuente)**: Directorio raíz donde buscar PDFs (ej: `O:\Finanzas\...`)
        - **Ruta destino (O:\Finanzas\...)**: Carpeta para copiar archivos procesados organizados por año/mes.
    - Las rutas se guardan automáticamente en el perfil del usuario.

3.  **Verificación de Configuración**:
    - Intentar ejecutar un pipeline de prueba pequeño.
    - Verificar logs para errores de rutas o permisos.

### 5.3 Paquetes y Dependencias Detalladas
*   `pandas>=2.0.0`: Manipulación y análisis de datos tabulares, cruces de información.
*   `playwright>=1.40.0`: Automatización de navegadores para interacción con SAP WebGUI.
*   `pdfplumber>=0.10.0`: Extracción de texto y datos de archivos PDF.
*   `openpyxl>=3.1.0`: Lectura y escritura de archivos Excel (.xlsx) preservando formatos.
*   `customtkinter>=5.2.0`: Framework moderno para interfaces gráficas en Tkinter.
*   `pathlib` (estándar): Manejo de rutas del sistema de archivos.
*   `datetime` (estándar): Gestión de fechas y filtros temporales.

### 5.4 Compilación a Ejecutable (Opcional)
Para distribuir la aplicación como ejecutable standalone sin requerir Python instalado:

```bash
# Ejecutar el script de compilación
compilar.bat
```

Esto genera una carpeta `dist\The goose Brand` con el ejecutable portable, incluyendo todas las dependencias y Chromium embebido.

---

## 6. Ubicaciones y Archivos Importantes
*   **Directorio del Proyecto:** `C:\Proyectos Comodin\The_goose_brand`
*   **Archivo Maestro Excel:** `NEW_INDIGO.xlsx` (ubicación configurable, típicamente en red compartida `O:\Finanzas\Info Bancos\Pagos Internacionales\The Goose Brand\`)
*   **Directorio de Búsqueda PDFs:** Estructura de carpetas raíz donde se buscan facturas y guías (ej: `O:\Finanzas\...`)
*   **Ruta de Destino:** Carpeta organizada por año/mes para archivos procesados (ej: `O:\Finanzas\Info Bancos\Pagos Internacionales\The Goose Brand\2026\05\`)
*   **Archivo de Configuración:** `config.json` guardado en `%APPDATA%\kilo\config\the_goose_brand.json`
*   **Logs de Ejecución:** Mostrados en tiempo real en la interfaz, con límite de 400 líneas para rendimiento.

---

## 7. Soporte y Mantenimiento

### 7.1 Contacto para Soporte
Para soporte técnico, reportes de bugs, solicitudes de nuevas funcionalidades o actualizaciones, contactar a:
- **GCO Corporativo - Wilson Rojas**
- Fecha de última actualización: 2026/05/14
- Versión actual: 2.0.0

### 7.2 Notas Técnicas Importantes
*   **Cambios en SAP:** Si la interfaz web de SAP S/4HANA cambia (selectores CSS, flujo de navegación), actualizar los scripts en `core/descargador_sap.py`. Los selectores actuales están basados en SAP GUI for HTML.
*   **Actualización de Credenciales:** Las credenciales SAP están hardcodeadas por seguridad operativa. Para cambios, modificar `descargador_sap.py` con aprobación de seguridad.
*   **Rendimiento:** Para grandes volúmenes (>1000 registros), considerar aumentar límites de memoria y optimizar rutas de búsqueda.
*   **Compatibilidad PDF:** El sistema funciona mejor con PDFs de texto plano. PDFs escaneados requieren OCR, que puede ser menos preciso.

### 7.3 Compilación y Distribución
*   **Compilación Standalone:** Usar `compilar.bat` para generar ejecutable portable con PyInstaller. Incluye Chromium embebido para evitar instalación adicional.
*   **Distribución:** El ejecutable generado es autocontenido y puede copiarse a cualquier máquina Windows sin instalación de Python.
*   **Dependencias Externas:** Requiere acceso a rutas de red configuradas y conectividad a SAP WebGUI.

### 7.4 Troubleshooting Común
*   **Error de SAP:** Verificar conectividad de red y credenciales. Los logs mostrarán detalles del fallo.
*   **PDFs no encontrados:** Revisar configuración de rutas de búsqueda y estructura de directorios.
*   **Excel corrupto:** El sistema preserva formatos, pero respaldos regulares son recomendados.
*   **Memoria insuficiente:** Para volúmenes grandes, procesar en lotes más pequeños usando filtros de fecha.

### 7.5 Registro de Cambios (Changelog)
*   **v2.0.0 (2026/05/14)**: Interfaz gráfica completa, sistema de cancelación, filtros por fecha, búsqueda multimétodo optimizada, reportes detallados.
*   **v1.x**: Versiones anteriores con funcionalidad básica.