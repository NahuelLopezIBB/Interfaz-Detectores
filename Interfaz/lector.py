import serial
import time

URL="rfc2217://localhost:4000"

class LectorSerie:
    def __init__(self,url):
        self._url=url
        self._ser = None # serial.serial_for_url(self._url,baudrate=115200,timeout=0)
        self.conectado = False
        self._ultimo_intento = 0
        self._buffer = ""
        
        

    def leer(self):
        if not self.conectado:
            tiempotranscurrido = time.monotonic() - self._ultimo_intento
            if tiempotranscurrido >= 1:
                self._conectar()
            return []
    
        
        datos = b""
        try:
            while self._ser.in_waiting:
                datos +=self._ser.read(self._ser.in_waiting)
        except (serial.SerialException, OSError):
            self._desconectar()
            return []
        lecturas= []
        nuevo=datos.decode(errors="ignore")
        self._buffer += nuevo 
        
        partes = self._buffer.split("\n")
        lineas=partes[:-1] 
        self._buffer = partes[-1]

        for linea in lineas:
            medicion = parsear(linea.strip())
            if medicion is not None:
                lecturas.append(medicion)
        
        return lecturas 

    def _desconectar(self):
        if self._ser is not None:
            try:
                self._ser.close()
                self._ser = None
                self.conectado = False
            except (serial.SerialException,OSError):
                self.conectado = False
                self._ser = None    
    def _conectar(self):
        self._ultimo_intento = time.monotonic()
        try:
            self._ser =  serial.serial_for_url(self._url,baudrate=115200,timeout=0)
            self.conectado = True 
            self._buffer= ""
        except (serial.SerialException, OSError):
            self.conectado = False
            self._ser = None
                        

        
def parsear(linea):
    splat = linea.split(",")
    if len(splat)!=7:
        return None
    try: 
        numeros = [int(num) for num in splat]
    except ValueError:
        return None
    
    return numeros[0],numeros[1], numeros[2:]





if __name__ == "__main__":
    L=LectorSerie(URL)
    while True:
        lectura=L.leer()
        if lectura != []:
            print(lectura)
        time.sleep(0.05)
        