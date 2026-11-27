"""Lectura del puerto serie del contador (protocolo `t_ms,intervalo_ms,c0..c4`).

Diseñado para llamarse periódicamente desde el hilo de la GUI: nunca bloquea.
La lectura es no bloqueante y la conexión se intenta en un hilo aparte.
"""
import serial
import time
import threading


class LectorSerie:
    """Conexión serie con el ESP32, con lectura no bloqueante y reconexión.

    Atributos públicos:
        conectado: True mientras haya un puerto abierto y funcionando. Lo
            consulta la ventana para mostrar el estado.

    Mientras `conectado` es False y hay una URL elegida, cada llamada a
    `leer()` puede lanzar (a lo sumo una vez por segundo) un intento de
    conexión en segundo plano.
    """
    def __init__(self):
        """Crea el lector sin URL ni puerto: no se conecta hasta `set_url()`."""
        # URL de pyserial (p. ej. "COM3" o "rfc2217://localhost:4000"); None = no conectar.
        self._url=None
        self._ser = None # serial.serial_for_url(self._url,baudrate=115200,timeout=0)
        self.conectado = False
        # True mientras hay un hilo de conexión en curso: evita lanzar varios.
        self._conectando = False
        # time.monotonic() del último intento; 0 fuerza un intento inmediato.
        self._ultimo_intento = 0
        # Texto recibido después del último "\n": una línea todavía incompleta
        # que se completa con los bytes de la próxima lectura.
        self._buffer = ""
        
        

    def leer(self):
        """Lee lo disponible en el puerto y devuelve las mediciones completas nuevas.

        No bloquea. Si no está conectado, lanza un intento de conexión en un
        hilo (si pasó al menos 1 s desde el anterior y no hay otro en curso)
        y devuelve una lista vacía.

        Returns:
            Lista (posiblemente vacía) de tuplas `(t_ms, intervalo_ms, cuentas)`
            recibidas desde la llamada anterior; no es un histórico.

        Efectos: actualiza `_buffer`; ante un error del puerto se desconecta.
        """
        if self._url is None:
            return []
        if not self.conectado:
            tiempotranscurrido = time.monotonic() - self._ultimo_intento
            if tiempotranscurrido >= 1 and not self._conectando:
                # Abrir el puerto puede tardar (sobre todo RFC2217 por red):
                # se hace en un hilo para no congelar la GUI. daemon=True
                # para que no impida cerrar el programa.
                self._conectando = True
                threading.Thread(target=self._conectar,daemon=True).start()
                
            return []
    
        
        datos = b""
        # Con timeout=0 read() nunca bloquea. El while es necesario porque la
        # implementación RFC2217 de pyserial devuelve un solo byte por read().
        # Un error del puerto (p. ej. cable desconectado) se trata como
        # desconexión; la reconexión la intentan las llamadas siguientes.
        try:
            while self._ser.in_waiting:
                datos +=self._ser.read(self._ser.in_waiting)
        except (serial.SerialException, OSError):
            self._desconectar()
            return []
        lecturas= []
        nuevo=datos.decode(errors="ignore")
        self._buffer += nuevo 
        
        # Las líneas pueden llegar partidas en varias lecturas: todo lo que
        # está antes del último "\n" son líneas completas; lo que sigue queda
        # pendiente en _buffer.
        partes = self._buffer.split("\n")
        lineas=partes[:-1] 
        self._buffer = partes[-1]

        for linea in lineas:
            medicion = parsear(linea.strip())
            if medicion is not None:
                lecturas.append(medicion)
        
        return lecturas 


        

    def cerrar(self):
        """Cierra el puerto (si está abierto). No borra la URL: si sigue
        habiendo una, `leer()` volverá a intentar conectarse."""
        self._desconectar()

    def _desconectar(self):
        """Cierra el puerto ignorando errores y marca `conectado = False`.

        Los errores al cerrar se ignoran porque típicamente se llega acá
        justamente porque el puerto ya falló.
        """
        if self._ser is not None:
            try:
                self._ser.close()
                
            except (serial.SerialException,OSError):
                pass
        self._ser = None
        self.conectado = False

    def set_url(self,url):
        """Cambia el puerto a usar.

        Args:
            url: URL de pyserial (`"COM3"`, `"rfc2217://localhost:4000"`, ...)
                o None para no conectarse más (se usa al cerrar la ventana).

        Efectos: cierra la conexión actual y pone `_ultimo_intento = 0` para
        que la próxima llamada a `leer()` intente conectarse de inmediato.
        """
        self.cerrar()
        self._url = url
        self._ultimo_intento = 0

    def _conectar(self):
        """Intenta abrir el puerto de `_url`. Corre en un hilo aparte.

        El puerto se abre en una variable local y se "publica" en `self` solo
        al final, con `conectado = True` como última asignación: así el hilo
        de la GUI nunca ve `conectado` en True con `_ser` todavía sin asignar.
        Si mientras tanto el usuario cambió de puerto, el intento es obsoleto
        y se descarta. Este método nunca toca widgets de Qt (no es seguro
        desde otro hilo).

        Efectos: actualiza `_ultimo_intento`; si tiene éxito, vacía `_buffer`
        y asigna `_ser` y `conectado`; siempre libera `_conectando`.
        """
        # Se guarda la URL con la que se intenta para detectar después si
        # el usuario la cambió mientras se abría el puerto.
        url=self._url
        self._ultimo_intento = time.monotonic()
        try:
            try:
                # timeout=0: lecturas no bloqueantes (ver leer()).
                ser =  serial.serial_for_url(url,baudrate=115200,timeout=0)
            except (serial.SerialException, OSError):
                return
            if url!=self._url:
                ser.close()    
                return        
            # Se descarta cualquier resto de línea de una conexión anterior.
            self._buffer = ""
            self._ser = ser
            self.conectado = True
        finally:
            self._conectando = False        

            
def parsear(linea):
    """Convierte una línea del protocolo en una medición.

    Args:
        linea: texto sin el "\\n" final, con formato
            `t_ms,intervalo_ms,c0,c1,c2,c3,c4`.

    Returns:
        Tupla `(t_ms, intervalo_ms, [c0, c1, c2, c3, c4])` de enteros, o None
        si la línea no tiene exactamente 7 enteros. Así se descartan el texto
        de arranque del ESP32, las líneas cortadas y la basura.
    """
    splat = linea.split(",")
    if len(splat)!=7:
        return None
    try: 
        numeros = [int(num) for num in splat]
    except ValueError:
        return None
    
    return numeros[0],numeros[1], numeros[2:]




