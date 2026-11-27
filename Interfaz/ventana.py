"""Ventana principal: muestra tasas y totales por canal y controla la medición."""
from PySide6.QtWidgets import QWidget,QLabel,QGridLayout,QPushButton,QComboBox
from PySide6.QtCore import QTimer,Qt
from serial.tools import list_ports
from lector import LectorSerie
from grabador import GrabadorCSV
# Estilos (Qt style sheets). Siempre se fija `color` junto con
# `background-color`: con Windows en modo oscuro el texto por defecto es
# claro y quedaría ilegible sobre fondos claros.
ESTILO_VALOR="background-color:white;color: black; border: 1px solid black; padding: 4px; font-size: 20px; font-weight: bold;"
ESTILO_TIEMPO="background-color:grey;color: black; border: 1px solid black; padding: 6px; font-size: 20px; font-weight: bold;"
ESTILO_DESCONECTADO="background-color:red;color: white; border: 1px solid black; padding: 6px; font-size: 20px; font-weight: bold;"
ESTILO_CONECTADO="background-color:green;color: black; border: 1px solid black; padding: 6px; font-size: 20px; font-weight: bold;"
ESTILO_LABEL = "font-size: 20px; font-weight: bold;"


class Ventana(QWidget):
    """Ventana del contador.

    Muestra, para cada uno de los 5 canales, las cuentas por segundo promedio,
    las de la última ventana recibida y el total acumulado; además el tiempo
    medido y el estado de la conexión. Permite elegir el puerto y controlar
    la medición con los botones Iniciar / Parar / Reiniciar.

    Un QTimer de 50 ms llama a `actualizar()`, que lee el lector serie,
    acumula las mediciones (si se está midiendo) y las graba en el CSV.

    Atributos de estado:
        midiendo: True entre Iniciar y Parar/Reiniciar.
        acum_cuentas: cuentas acumuladas de cada canal.
        acum_tiempo_ms: suma de los `intervalo_ms` acumulados.
        ultima_lectura: última medición recibida, para el CPS actual.
    """
    def __init__(self,lector:LectorSerie,grabador:GrabadorCSV):
        """Arma la interfaz y arranca el timer de actualización.

        Args:
            lector: lector serie ya creado (inyectado desde main.py).
            grabador: grabador de CSV ya creado (inyectado desde main.py).
        """
        super().__init__()
        self.lector = lector
        self.grabador = grabador
        self.midiendo = False
        self.acum_cuentas = [0] * 5
        # Tiempo medido = suma de los intervalo_ms recibidos, no el reloj de
        # la PC: excluye pausas y desconexiones y no depende de la velocidad
        # de la simulación en Wokwi.
        self.acum_tiempo_ms = 0
        self.ultima_lectura = (0,0,[0] * 5)


        self.setWindowTitle("Contador")
        self.resize(800,400)
        self.setMinimumSize(600,300)
        layout = QGridLayout(self)

        self.etiquetas_canal=["CH1","CH2","CH3","CH4","CH5"]
        self._crear_columna_labels(layout,self.etiquetas_canal,1,0)

        self.etiquetas_columnas= ["Canal","CPS promedio","CPS actual","TOTAL"]
        self._crear_fila_labels(layout,self.etiquetas_columnas,0,0)

        #counters
        self.cps_promedio = self._crear_columna_valores(layout,self.etiquetas_canal,1,1)
        self.cps_actual = self._crear_columna_valores(layout,self.etiquetas_canal,1,2)
        self.cuentas_totales     = self._crear_columna_valores(layout,self.etiquetas_canal,1,3)

        #Timer
        tiempolabel=QLabel("Tiempo",alignment=Qt.AlignCenter)
        layout.addWidget(tiempolabel,6,0)
        self.lbl_tiempo=QLabel("0:00:00")
        self.lbl_tiempo.setStyleSheet(ESTILO_TIEMPO)
        layout.addWidget(self.lbl_tiempo,6,1)

        
        
        
        lbl_estado = QLabel("Estado:")
        lbl_estado.setStyleSheet(ESTILO_LABEL)
        lbl_estado.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(lbl_estado,6,2)
        self.lbl_conexion = QLabel("DESCONECTADO")
        self.lbl_conexion.setStyleSheet(ESTILO_DESCONECTADO)
        layout.addWidget(self.lbl_conexion,6,3)

        # botones
        self.btn_actualizar = self.añadir_boton(layout,"Actualizar",self.funcion_btn_actualizar,7,2)
        self.btn_conectar   = self.añadir_boton(layout,"Conectar",self.funcion_btn_conectar,7,3)
        self.btn_iniciar    = self.añadir_boton(layout,"Iniciar",self.funcion_btn_iniciar,8,1)
        self.btn_detener      = self.añadir_boton(layout,"Parar", self.funcion_btn_detener,8,2)
        self.btn_reiniciar = self.añadir_boton(layout,"Reiniciar",self.funcion_btn_reiniciar,8,3)        


        self.combo_puerto = QComboBox()
        layout.addWidget(self.combo_puerto,7,1)

        # Llena la lista de puertos al abrir la ventana.
        self.funcion_btn_actualizar()

        # 50 ms es bastante menos que la ventana del ESP32 (250 ms): la
        # interfaz se mantiene fluida y la cola del puerto no se acumula.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar)

        self.timer.start(50)

    def añadir_boton(self,layout:QGridLayout,texto,funcion,row,col):
        """Crea un botón, conecta su click a `funcion` y lo ubica en (row, col).

        Returns:
            El QPushButton creado.
        """
        boton = QPushButton(texto)
        boton.clicked.connect(funcion)
        layout.addWidget(boton,row,col)
        return boton

    def funcion_btn_iniciar(self):
        """Botón Iniciar: empieza (o reanuda) la medición.

        Solo actúa si hay conexión. Abre un CSV nuevo solo si no hay uno
        abierto: después de Parar (pausa) se sigue escribiendo en el mismo.
        """
        if not self.lector.conectado:
            return
        
        self.midiendo = True
        if self.grabador.esta_abierto():
            return    
        self.grabador.abrir()

    def funcion_btn_detener(self):
        """Botón Parar: pausa la medición. No cierra el CSV ni borra los
        acumulados, para poder reanudar con Iniciar."""
        self.midiendo = False

    def funcion_btn_reiniciar(self):
        """Botón Reiniciar: da por terminada la medición.

        Pone en cero acumulados y última lectura, refresca la pantalla, deja
        de medir y cierra el CSV (el próximo Iniciar abre uno nuevo).
        """
        
        self.acum_cuentas = [0] * 5
        self.acum_tiempo_ms = 0
        self.ultima_lectura = (0, 0, [ 0 ] * 5 )
        self.actualizar_labels()
        self.funcion_btn_detener()
        self.grabador.cerrar()


    def funcion_btn_actualizar(self):
        """Botón Actualizar: vuelve a listar los puertos serie disponibles.

        Siempre agrega al final la URL del simulador Wokwi (RFC2217 en el
        puerto 4000), que no aparece entre los puertos del sistema.
        """
        
        self.combo_puerto.clear()
        for p in list_ports.comports():
            self.combo_puerto.addItem(p.device)
        self.combo_puerto.addItem("rfc2217://localhost:4000")


    def funcion_btn_conectar(self):
        """Botón Conectar: pasa al lector el puerto elegido. La conexión
        efectiva la hace el lector en segundo plano."""
        
        url=self.combo_puerto.currentText()
        self.lector.set_url(url)

    def _crear_columna_labels(self,layout:QGridLayout,etiquetas,fila_inicio,columna):
        """Crea un QLabel por texto de `etiquetas`, uno debajo del otro,
        desde (fila_inicio, columna).

        Returns:
            Lista de los QLabel creados.
        """
        
        labels=[]
        for N,CH in enumerate(etiquetas):
            label=QLabel(CH,alignment=Qt.AlignCenter)
            
            layout.addWidget(label,fila_inicio+N,columna)
            labels.append(label)
        return labels

    def _crear_fila_labels(self,layout:QGridLayout,etiquetas,columna_inicio,fila):
        """Crea un QLabel por texto de `etiquetas`, uno al lado del otro,
        desde (fila, columna_inicio).

        Returns:
            Lista de los QLabel creados.
        """
        labels=[]
        for N,CH in enumerate(etiquetas):
            label=QLabel(CH,alignment=Qt.AlignCenter)
    
            layout.addWidget(label,fila,columna_inicio+N)
            labels.append(label)
        return labels

    def _crear_columna_valores(self,layout:QGridLayout,etiquetas,fila_inicio,columna):
        """Crea una columna de QLabel con estilo de valor (inicialmente "0"),
        uno por cada elemento de `etiquetas`, desde (fila_inicio, columna).

        Returns:
            Lista de los QLabel creados; se guardan para actualizar los valores.
        """
        
        contadores=[]
        for N,_ in enumerate(etiquetas):
            number=QLabel("0")
            number.setStyleSheet(ESTILO_VALOR)
            layout.addWidget(number,fila_inicio+N,columna)
            contadores.append(number)
        return contadores

    def actualizar(self):
        """Ciclo del timer: leer → estado de conexión → acumular → mostrar.

        Efectos: si se está midiendo y llegaron datos, suma cuentas y tiempo,
        escribe cada medición en el CSV, guarda la última y refresca la
        pantalla. Siempre actualiza el indicador de conexión.
        """
        # Se lee siempre, aunque no se esté midiendo: así se vacía la cola
        # del puerto (al reanudar no aparecen datos viejos) y el lector sigue
        # intentando reconectarse.
        nuevas = self.lector.leer()
        
        

        if self.lector.conectado:

            self.lbl_conexion.setStyleSheet(ESTILO_CONECTADO)
            self.lbl_conexion.setText("CONECTADO")
        else : 

            self.lbl_conexion.setStyleSheet(ESTILO_DESCONECTADO)
            self.lbl_conexion.setText("DESCONECTADO")
            


        # Sin datos nuevos o en pausa: lo leído se descarta.
        if not nuevas or not self.midiendo:
            return


        for medicion in nuevas:
            _, intervalo_ms,cuentas = medicion
            self.acum_tiempo_ms += intervalo_ms
                       
            for N in range(len(self.acum_cuentas)):
                self.acum_cuentas[N] += cuentas[N]
            self.grabador.escribir(medicion)            
        self.ultima_lectura = nuevas[-1]


        
        self.actualizar_labels()
        

    def actualizar_labels(self):
        """Muestra CPS actual, total y CPS promedio de cada canal, y el
        tiempo medido. No modifica el estado.

        Las divisiones están protegidas contra cero porque después de
        Reiniciar el intervalo y el tiempo acumulado valen 0.
        """
        _,ultimo_intervalo,ultimas_cuentas = self.ultima_lectura
                   
        for N in range(len(self.cps_actual)):
            cps=ultimas_cuentas[N]/ultimo_intervalo*1000 if ultimo_intervalo > 0 else 0
                        
            self.cps_actual[N].setText(f"{cps:,.0f}")
                            
            self.cuentas_totales[N].setText(f"{self.acum_cuentas[N]:,}")
            promedio = self.acum_cuentas[N]/self.acum_tiempo_ms*1000 if self.acum_tiempo_ms >0 else 0
            self.cps_promedio[N].setText(f"{promedio:,.2f}")

        segundos_desde_inicio=self.acum_tiempo_ms//1000 
        self.lbl_tiempo.setText(formatear_segundos(segundos_desde_inicio))        


    def closeEvent(self, event):
        """Al cerrar la ventana: detiene el timer, desconecta el lector y
        cierra el CSV.

        `set_url(None)` (y no solo `cerrar()`) para que el lector no intente
        reconectarse si algo vuelve a llamar a `leer()`.
        """
        # detener el timer y cerrar el lector
        self.timer.stop()
        self.lector.set_url(None)
        self.grabador.cerrar()
        super().closeEvent(event)
            

def formatear_segundos(segundos_totales):
    """Convierte una cantidad entera de segundos en el texto "H:MM:SS".

    Args:
        segundos_totales: segundos (int, no negativo).

    Returns:
        str, p. ej. 3725 -> "1:02:05".
    """
    H,seg_restantes_de_horas = divmod(segundos_totales,3600)
    M,s = divmod(seg_restantes_de_horas,60)
    return f"{H}:{M:02d}:{s:02d}"