import sys
from PySide6.QtWidgets import QApplication
from lector import LectorSerie
from ventana import Ventana


URL="rfc2217://localhost:4000"



if __name__ == "__main__":
    app = QApplication(sys.argv)
    lector = LectorSerie(URL)
    ventana = Ventana(lector)
    ventana.show()
    # crear el lector y la ventana, y mostrar la ventana con .show()

    sys.exit(app.exec())