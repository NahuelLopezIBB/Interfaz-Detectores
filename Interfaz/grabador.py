"""Grabación de las mediciones en archivos CSV."""
import csv
from datetime import datetime,timedelta
from pathlib import Path

class GrabadorCSV:
    """Escribe cada medición recibida como una fila de un CSV.

    Formato pensado para Excel con configuración regional de Argentina:
    separador `;` y coma decimal. Columnas:
    `fecha_hora;t_s;intervalo_ms;CH1;CH2;CH3;CH4;CH5`.

    El ESP32 solo da un tiempo relativo (`t_ms`, su `millis()`), así que la
    hora real se reconstruye anclando el primer `t_ms` a la hora de la PC.
    Si `t_ms` decrece (el ESP32 se reinició) se vuelve a anclar.

    Atributos públicos:
        carpeta: carpeta donde se crean los CSV.
        nombre, ruta: nombre y ruta completa del último CSV abierto (None
            si todavía no se abrió ninguno).
    """
    def __init__(self,carpeta):
        """Prepara el grabador sin abrir ningún archivo.

        Args:
            carpeta: ruta (str o Path) de la carpeta de mediciones. Se crea si
                no existe (solo el último nivel).
        """
        self.carpeta = Path(carpeta)
        self.carpeta.mkdir(exist_ok=True)
        self.nombre = None
        self.ruta = None
        self._archivo = None
        self._escritor = None
        # Ancla de tiempo: hora de la PC (_t0_pc) que corresponde al t_ms del
        # ESP32 _t0_esp. Con ella, fecha_hora = _t0_pc + (t_ms - _t0_esp).
        self._t0_pc = None
        self._t0_esp= None
        # t_ms de la fila anterior, para detectar un reinicio del ESP32.
        self._t_ms_anterior = None
        # fecha_hora de la primera fila; t_s se mide desde acá.
        self._inicio = None




    def abrir(self):
        """Crea un CSV nuevo con nombre `medicion_AAAA-MM-DD_HH-MM-SS.csv` y
        escribe el encabezado.

        Efectos: asigna `nombre`, `ruta`, el archivo y el escritor, y reinicia
        el ancla de tiempo para que la primera fila defina el nuevo origen.
        """
        inicio = datetime.now()
        self.nombre = inicio.strftime("medicion_%Y-%m-%d_%H-%M-%S.csv")
        self.ruta = self.carpeta / self.nombre


        # newline="" es lo que pide el módulo csv (si no, en Windows quedan
        # líneas en blanco intercaladas).
        self._archivo = open(self.ruta, "w",newline="",encoding="utf-8")
        self._escritor = csv.writer(self._archivo,delimiter=";")
        self._escritor.writerow(["fecha_hora","t_s","intervalo_ms","CH1","CH2","CH3","CH4","CH5"])
        self._archivo.flush()
        
        self._t0_esp = None
        self._t0_pc = None
        self._t_ms_anterior = None
        self._inicio = None

    
        
    def escribir(self,medicion):
        """Agrega una fila al CSV. No hace nada si no hay archivo abierto.

        Args:
            medicion: tupla `(t_ms, intervalo_ms, [c0..c4])` como la devuelve
                `parsear()` en `lector.py`.

        Efectos: puede (re)anclar el tiempo, fija `_inicio` en la primera
        fila, actualiza `_t_ms_anterior` y hace flush del archivo.
        """
        if self._archivo is None:
            return
        
        t_ms,intervalo,cuentas = medicion

        
        # Primera fila, o t_ms retrocedió (el ESP32 se reinició y millis()
        # volvió a 0): se ancla t_ms a la hora actual de la PC.
        if self._t0_esp is None or t_ms < self._t_ms_anterior:
            self._t0_esp = t_ms
            self._t0_pc = datetime.now()

        
        delta_ms=t_ms - self._t0_esp
        fecha_hora = self._t0_pc + timedelta(milliseconds=delta_ms)
        if self._inicio is None:
            self._inicio = fecha_hora
        
        # t_s se calcula desde fecha_hora (y no desde t_ms) para que siga
        # creciendo después de un re-anclaje. Las pausas y reinicios aparecen
        # como saltos en t_s; el tiempo efectivamente medido es la suma de
        # intervalo_ms.
        t_s = (fecha_hora - self._inicio).total_seconds()

        # Coma decimal para Excel en configuración regional de Argentina.
        fila = [fecha_hora.strftime("%Y-%m-%d %H:%M:%S"), f"{t_s:.3f}".replace(".",",")
                , intervalo, *cuentas]

        # flush en cada fila: si el programa se cierra mal no se pierden datos.
        self._escritor.writerow(fila)
        self._archivo.flush()
        self._t_ms_anterior = t_ms
        
    def cerrar(self):
        """Cierra el CSV abierto, si hay uno. Se puede llamar varias veces."""
        if self._archivo is not None:
            self._archivo.close()
            self._escritor = None
            self._archivo = None

    def esta_abierto(self):
        """Devuelve True si hay un CSV abierto (una medición en curso o en pausa)."""
        return self._archivo is not None


# Prueba manual: simula un reinicio del ESP32 (t_ms que retrocede) para
# verificar el re-anclaje de la hora.
if __name__ == "__main__":
    import time
    g= GrabadorCSV()
    g.abrir()
    g.escribir((1000, 250, [25, 0, 0, 0, 0]))
    g.escribir((1250, 250, [26, 0, 0, 0, 0]))
    time.sleep(2)                                # simula el tiempo que tarda en reiniciarse
    g.escribir((300, 250, [24, 0, 0, 0, 0]))     # t_ms más chico: reinicio
    g.escribir((550, 250, [25, 0, 0, 0, 0]))
    g.cerrar()