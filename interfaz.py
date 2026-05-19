"""
INTERFAZ GUI - The goose Brand
Construida con customtkinter.
Pantallas: IDLE → RUNNING → COMPLETED  +  CONFIG (modal)
"""

import logging
import queue
import threading

import os
import shutil
import pandas as pd

from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from utils.config_manager import ConfiguradorNewIndigo
from core.pipeline import ejecutar_pipeline
from models.reporte import Reporte

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

FONT_TITLE  = ("Segoe UI", 22, "bold")
FONT_LABEL  = ("Segoe UI", 14)
FONT_SMALL  = ("Segoe UI", 12)
FONT_MONO   = ("Consolas", 11)
COLOR_OK    = "#27ae60"
COLOR_WARN  = "#e67e22"
COLOR_ERR   = "#c0392b"
COLOR_BG    = "#f4f6f9"
COLOR_CARD  = "#ffffff"
COLOR_ACCENT= "#586AE8"

MAX_LOG_LINES = 400   # Límite de líneas en el log para no saturar la GUI

logger = logging.getLogger(__name__)


class NewIndigoApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("The goose Brand — Pipeline de Facturación")
        self.geometry("900x640")
        self.minsize(800, 580)
        self.configure(fg_color=COLOR_BG)

        # Establecer el icono de la ventana
        try:
            ruta_icono = Path(__file__).parent / "icono.ico"
            if ruta_icono.exists():
                self.iconbitmap(str(ruta_icono))
        except Exception as e:
            logger.warning(f"No se pudo cargar el icono de la ventana: {e}")

        self.config_manager = ConfiguradorNewIndigo()
        self.config_manager.cargar_config()

        self._queue: queue.Queue = queue.Queue()
        self._pipeline_thread: threading.Thread | None = None
        self._cancelar_flag = threading.Event()
        self._log_lines = 0

        # Guardamos los valores de los filtros para restaurarlos al volver
        self._ultimo_desde = ""
        self._ultimo_hasta = ""

        self._build_header()
        self._build_body()
        self._mostrar_idle()
        self.after(100, self._procesar_cola)

    # ── HEADER ────────────────────────────────────────────────────────────────
    def _build_header(self):
        header = ctk.CTkFrame(self, fg_color=COLOR_ACCENT, corner_radius=0, height=60)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="⬡  The goose Brand", font=FONT_TITLE, text_color="white"
        ).pack(side="left", padx=20, pady=10)

        ctk.CTkButton(
            header, text="⚙  Configuración", width=140, height=34,
            fg_color="transparent", border_width=1, border_color="white",
            text_color="white", hover_color="#4255c8",
            command=self._abrir_config
        ).pack(side="right", padx=15, pady=12)

    # ── BODY ──────────────────────────────────────────────────────────────────
    def _build_body(self):
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=30, pady=20)

    def _limpiar_body(self):
        for w in self.body.winfo_children():
            w.destroy()

    # ════════════════════════════════════════════════════════════════════════════
    # PANTALLA IDLE
    # ════════════════════════════════════════════════════════════════════════════
    def _mostrar_idle(self, desde: str = "", hasta: str = ""):
        self._limpiar_body()

        card = ctk.CTkFrame(self.body, fg_color=COLOR_CARD, corner_radius=16, border_width=1, border_color="#e0e0e0")
        card.pack(expand=True, fill="both")

        ctk.CTkLabel(
            card, text="Proceso Listo para ejecutar",
            font=FONT_LABEL, text_color="#333333"
        ).pack(pady=(40, 6))

        ctk.CTkLabel(
            card,
            text="Procesa facturas y guías DHL, extrae datos\n"
                 "y actualiza el maestro The goose Brand.xlsx",
            font=FONT_SMALL, text_color="#666666", justify="center"
        ).pack(pady=(0, 30))

        # ── Filtro de fechas ──────────────────────────────────────────────────
        frame_fechas = ctk.CTkFrame(card, fg_color="transparent")
        frame_fechas.pack(pady=(0, 20))

        ctk.CTkLabel(frame_fechas, text="Desde:", font=FONT_SMALL, text_color="#333333").grid(
            row=0, column=0, padx=8)
        self.entry_desde = ctk.CTkEntry(
            frame_fechas, placeholder_text="YYYY-MM-DD  (opcional)", width=160, fg_color="#f8f9fa", border_color="#ced4da", text_color="#333333")
        self.entry_desde.grid(row=0, column=1, padx=8)
        if desde:
            self.entry_desde.insert(0, desde)

        ctk.CTkLabel(frame_fechas, text="Hasta:", font=FONT_SMALL, text_color="#333333").grid(
            row=0, column=2, padx=8)
        self.entry_hasta = ctk.CTkEntry(
            frame_fechas, placeholder_text="YYYY-MM-DD  (opcional)", width=160, fg_color="#f8f9fa", border_color="#ced4da", text_color="#333333")
        self.entry_hasta.grid(row=0, column=3, padx=8)
        if hasta:
            self.entry_hasta.insert(0, hasta)

        # ── Botón ejecutar ────────────────────────────────────────────────────
        ctk.CTkButton(
            card, text="▶  Ejecutar Pipeline",
            width=220, height=48, font=("Segoe UI", 14, "bold"),
            fg_color=COLOR_ACCENT, hover_color="#4255c8", text_color="white",
            command=self._iniciar_pipeline
        ).pack(pady=10)

    # ════════════════════════════════════════════════════════════════════════════
    # PANTALLA RUNNING
    # ════════════════════════════════════════════════════════════════════════════
    def _mostrar_running(self):
        self._limpiar_body()
        self._log_lines = 0

        card = ctk.CTkFrame(self.body, fg_color=COLOR_CARD, corner_radius=16, border_width=1, border_color="#e0e0e0")
        card.pack(expand=True, fill="both")

        ctk.CTkLabel(card, text="⏳  Ejecutando pipeline…",
                     font=FONT_LABEL, text_color="#333333").pack(pady=(30, 10))

        self.lbl_progreso = ctk.CTkLabel(
            card, text="Inicializando…", font=FONT_SMALL, text_color="#666666")
        self.lbl_progreso.pack()

        self.barra = ctk.CTkProgressBar(card, width=600, height=18,
                                         progress_color=COLOR_ACCENT)
        self.barra.pack(pady=12)
        self.barra.set(0)

        self.txt_log = ctk.CTkTextbox(
            card, width=820, height=300, font=FONT_MONO,
            fg_color="#f8f9fa", text_color="#333333", border_width=1, border_color="#e0e0e0")
        self.txt_log.pack(padx=20, pady=(0, 10))

        # Botón cancelar
        ctk.CTkButton(
            card, text="✖  Cancelar ejecución",
            width=180, height=34,
            fg_color="transparent", border_width=1, border_color=COLOR_ERR,
            text_color=COLOR_ERR, hover_color="#fadbd8",
            command=self._solicitar_cancelacion
        ).pack(pady=(0, 15))

    def _agregar_log(self, msg: str):
        if not hasattr(self, "txt_log"):
            return
        self.txt_log.configure(state="normal")
        # Si supera el límite, borrar el primer bloque para no saturar RAM
        if self._log_lines >= MAX_LOG_LINES:
            self.txt_log.delete("1.0", "51.0")  # borra 50 líneas del inicio
            self._log_lines -= 50
        self.txt_log.insert("end", msg + "\n")
        self._log_lines += 1
        self.txt_log.see("end")
        self.txt_log.configure(state="disabled")

    def _actualizar_barra(self, actual: int, total: int, msg: str):
        if hasattr(self, "barra") and total > 0:
            self.barra.set(actual / total)
        if hasattr(self, "lbl_progreso"):
            self.lbl_progreso.configure(text=f"{actual} / {total}  —  {msg}")

    def _solicitar_cancelacion(self):
        self._cancelar_flag.set()
        if hasattr(self, "lbl_progreso"):
            self.lbl_progreso.configure(
                text="Cancelando… finalizando el registro actual y guardando Excel")

    # ════════════════════════════════════════════════════════════════════════════
    # PANTALLA COMPLETED
    # ════════════════════════════════════════════════════════════════════════════
    def _mostrar_completed(self, reporte: Reporte):
        self._limpiar_body()

        card = ctk.CTkFrame(self.body, fg_color=COLOR_CARD, corner_radius=16, border_width=1, border_color="#e0e0e0")
        card.pack(expand=True, fill="both")

        cancelado = self._cancelar_flag.is_set()
        ctk.CTkLabel(
            card,
            text="⚠  Pipeline cancelado" if cancelado else "✔  Pipeline completado",
            font=FONT_LABEL,
            text_color=COLOR_WARN if cancelado else COLOR_OK,
        ).pack(pady=(25, 10))

        # ── Tarjetas de conteo ────────────────────────────────────────────────
        frame_stats = ctk.CTkFrame(card, fg_color="transparent")
        frame_stats.pack(pady=6)

        stats = [
            ("Procesados",  reporte.total_pendientes, COLOR_ACCENT),
            ("Completados", reporte.actualizados,     COLOR_OK),
            ("Sin ambos",   reporte.sin_ambos,        COLOR_ERR),
            ("Sin guía",    reporte.sin_guia,         COLOR_WARN),
            ("Sin factura", reporte.sin_factura,      COLOR_WARN),
            ("Lect. error", reporte.errores_lectura,  COLOR_ERR),
        ]

        for col, (titulo, valor, color) in enumerate(stats):
            f = ctk.CTkFrame(frame_stats, fg_color="#f8f9fa", border_width=1, border_color="#e0e0e0",
                             corner_radius=10, width=110, height=70)
            f.grid(row=0, column=col, padx=6, pady=4)
            f.pack_propagate(False)
            ctk.CTkLabel(f, text=str(valor), font=("Segoe UI", 20, "bold"),
                         text_color=color).pack(pady=(10, 0))
            ctk.CTkLabel(f, text=titulo, font=FONT_SMALL,
                         text_color="#666666").pack()

        # ── Tabla de observaciones ────────────────────────────────────────────
        if reporte.total_observaciones:
            titulo_obs = "Registros con observaciones"
            if reporte.total_observaciones > len(reporte.observaciones):
                titulo_obs = (
                    f"Registros con observaciones "
                    f"(mostrando {len(reporte.observaciones)} de {reporte.total_observaciones})"
                )

            ctk.CTkLabel(card, text=titulo_obs,
                         font=FONT_SMALL, text_color="#666666").pack(pady=(14, 4))

            tabla_frame = ctk.CTkScrollableFrame(
                card, width=820, height=160, fg_color="#f8f9fa", border_width=1, border_color="#e0e0e0")
            tabla_frame.pack(padx=20, pady=(0, 8))

            for col, enc in enumerate(("Referencia", "Fecha", "Observación")):
                ctk.CTkLabel(tabla_frame, text=enc, font=("Segoe UI", 11, "bold"),
                             text_color=COLOR_ACCENT).grid(
                    row=0, column=col, padx=10, pady=2, sticky="w")

            for fila_num, (ref, fecha, obs) in enumerate(
                    reporte.filas_observaciones(), start=1):
                for col, val in enumerate((ref, fecha, obs)):
                    ctk.CTkLabel(tabla_frame, text=val, font=FONT_SMALL,
                                 text_color="#333333").grid(
                        row=fila_num, column=col, padx=10, pady=1, sticky="w")

        # ── Botones ───────────────────────────────────────────────────────────
        frame_btns = ctk.CTkFrame(card, fg_color="transparent")
        frame_btns.pack(pady=(8, 18))

        ctk.CTkButton(
            frame_btns,
            text="▶  Ejecutar de nuevo",
            width=200, height=40,
            fg_color=COLOR_ACCENT, hover_color="#4255c8", text_color="white",
            font=("Segoe UI", 13, "bold"),
            # Restaura IDLE con los mismos filtros de fecha de la última ejecución
            command=lambda: self._mostrar_idle(
                desde=self._ultimo_desde,
                hasta=self._ultimo_hasta,
            )
        ).grid(row=0, column=0, padx=12)

        ctk.CTkButton(
            frame_btns,
            text="↩  Limpiar y volver",
            width=180, height=40,
            fg_color="transparent", border_width=1, border_color=COLOR_ACCENT,
            text_color=COLOR_ACCENT, hover_color="#f0f2fb",
            command=lambda: self._mostrar_idle()
        ).grid(row=0, column=1, padx=12)

    # ════════════════════════════════════════════════════════════════════════════
    # CONFIG (ventana modal)
    # ════════════════════════════════════════════════════════════════════════════
    def _abrir_config(self):
        win = ctk.CTkToplevel(self)
        win.title("Configuración — The goose Brand")
        win.geometry("680x320")
        win.resizable(False, False)
        win.configure(fg_color=COLOR_BG)
        win.grab_set()

        rutas = self.config_manager.obtener_rutas() or {}

        campos = [
            ("Excel Historial (NEW_INDIGO):", "ruta_maestro"),
            ("Ruta de búsqueda (PDFs fuente):", "ruta_busqueda"),
            ("Ruta destino (O:\\Finanzas\\...):", "ruta_destino"),
        ]

        entries: dict[str, ctk.CTkEntry] = {}
        for i, (label, key) in enumerate(campos):
            ctk.CTkLabel(win, text=label, font=FONT_SMALL, text_color="#333333").grid(
                row=i, column=0, padx=20, pady=10, sticky="w")
            e = ctk.CTkEntry(win, width=380, fg_color="#f8f9fa", border_color="#ced4da", text_color="#333333")
            valor = str(rutas.get(key, "")) if rutas else ""
            if valor and valor not in ("None", "."):
                e.insert(0, valor)
            e.grid(row=i, column=1, padx=6, pady=10)
            entries[key] = e

            def _browse(entry=e, is_file=(key == "ruta_maestro")):
                if is_file:
                    p = filedialog.askopenfilename(
                        filetypes=[("Excel", "*.xlsx")])
                else:
                    p = filedialog.askdirectory()
                if p:
                    entry.delete(0, "end")
                    entry.insert(0, p)

            ctk.CTkButton(win, text="…", width=36, fg_color=COLOR_ACCENT, hover_color="#4255c8",
                          text_color="white", command=_browse).grid(
                row=i, column=2, padx=6)

        def _guardar():
            ok = self.config_manager.guardar_config(
                ruta_maestro=entries["ruta_maestro"].get(),
                ruta_busqueda=entries["ruta_busqueda"].get(),
                ruta_destino=entries["ruta_destino"].get(),
            )
            if ok:
                messagebox.showinfo("Configuración", "Configuración guardada.")
                win.destroy()
            else:
                messagebox.showerror("Error", "No se pudo guardar la configuración.")

        ctk.CTkButton(
            win, text="Guardar", width=160, fg_color=COLOR_ACCENT, hover_color="#4255c8", text_color="white", command=_guardar
        ).grid(row=len(campos), column=1, pady=20)

    # ════════════════════════════════════════════════════════════════════════════
    # LÓGICA DE EJECUCIÓN
    # ════════════════════════════════════════════════════════════════════════════
    def _iniciar_pipeline(self):
        rutas = self.config_manager.obtener_rutas()
        if not rutas:
            messagebox.showwarning(
                "Configuración incompleta",
                "Configure las rutas en ⚙ Configuración antes de ejecutar.")
            return

        ruta_maestro  = rutas["ruta_maestro"]
        ruta_busqueda = rutas["ruta_busqueda"]
        ruta_destino  = rutas["ruta_destino"]

        if not ruta_maestro.exists():
            messagebox.showerror("Error", f"No se encontró el Excel:\n{ruta_maestro}")
            return

        # Parsear fechas opcionales
        fecha_desde = fecha_hasta = None
        txt_desde = self.entry_desde.get().strip()
        txt_hasta  = self.entry_hasta.get().strip()

        try:
            if txt_desde:
                fecha_desde = datetime.strptime(txt_desde, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Fecha inválida", "Formato esperado: YYYY-MM-DD")
            return
        try:
            if txt_hasta:
                fecha_hasta = datetime.strptime(txt_hasta, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Fecha inválida", "Formato esperado: YYYY-MM-DD")
            return

        # Guardar filtros para restaurarlos al volver con "Ejecutar de nuevo"
        self._ultimo_desde = txt_desde
        self._ultimo_hasta = txt_hasta

        # Resetear flag de cancelación ANTES de cada nueva ejecución
        self._cancelar_flag.clear()

        self._mostrar_running()
        self._agregar_log("▶ Iniciando pipeline The goose Brand…\n")

        cancelar = self._cancelar_flag  # referencia local para el hilo

        def _run():
            try:
                reporte = ejecutar_pipeline(
                    ruta_excel=ruta_maestro,
                    ruta_busqueda=ruta_busqueda,
                    ruta_destino=ruta_destino,
                    callback_progreso=lambda a, t, m: self._queue.put(
                        ("progreso", a, t, m)),
                    callback_log=lambda msg: self._queue.put(("log", msg)),
                    fecha_desde=fecha_desde,
                    fecha_hasta=fecha_hasta,
                    cancelar_flag=cancelar,
                )
            except Exception as exc:
                logger.exception("Error inesperado en el pipeline")
                from models.reporte import Reporte
                reporte = Reporte()
                self._queue.put(("log", f"❌ Error inesperado: {exc}"))
            self._queue.put(("done", reporte))

        self._pipeline_thread = threading.Thread(target=_run, daemon=True)
        self._pipeline_thread.start()

    def _procesar_cola(self):
        try:
            while True:
                item = self._queue.get_nowait()
                tipo = item[0]
                if tipo == "log":
                    self._agregar_log(item[1])
                elif tipo == "progreso":
                    self._actualizar_barra(item[1], item[2], item[3])
                elif tipo == "done":
                    self._mostrar_completed(item[1])
        except queue.Empty:
            pass
        self.after(100, self._procesar_cola)