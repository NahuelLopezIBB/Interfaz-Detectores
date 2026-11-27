"""Punto de entrada de la interfaz del contador de pulsos.

Crea el lector serie, el grabador de CSV y la ventana, e inyecta los dos
primeros en la ventana (así la ventana no decide dónde se graba ni cómo se
lee el puerto).
"""
import sys
from PySide6.QtWidgets import QApplication
from lector import LectorSerie
from ventana import Ventana
from grabador import GrabadorCSV
from pathlib import Path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    # La carpeta "mediciones" va al lado del programa. Empaquetado con
    # PyInstaller (sys.frozen), __file__ apunta a la carpeta interna de
    # PyInstaller, así que se usa la carpeta del .exe; en desarrollo, la
    # del .py.
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).parent
    else:
        base = Path(__file__).parent

    carpeta = base / "mediciones"
    grabador = GrabadorCSV(carpeta)

    
    lector = LectorSerie()

    ventana = Ventana(lector,grabador)
    ventana.show()


    # Bucle de eventos de Qt; su código de salida se devuelve al sistema.
    sys.exit(app.exec())