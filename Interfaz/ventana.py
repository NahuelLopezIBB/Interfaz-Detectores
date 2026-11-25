from PySide6.QtWidgets import QWidget,QLabel,QGridLayout
from PySide6.QtCore import QTimer,Qt, QElapsedTimer

from lector import LectorSerie

ESTILO_VALOR="background-color:white;color: black; border: 1px solid black; padding: 4px; font-size: 20px; font-weight: bold;"
ESTILO_TIEMPO="background-color:grey;color: black; border: 1px solid black; padding: 6px; font-size: 20px; font-weight: bold;"
ESTILO_DESCONECTADO="background-color:red;color: white; border: 1px solid black; padding: 6px; font-size: 20px; font-weight: bold;"
ESTILO_CONECTADO="background-color:green;color: black; border: 1px solid black; padding: 6px; font-size: 20px; font-weight: bold;"
ESTILO_LABEL = "font-size: 20px; font-weight: bold;"


class Ventana(QWidget):
    def __init__(self,lector:LectorSerie):
        super().__init__()
        self.lector = lector
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
        self.cronometro = QElapsedTimer()
        
        self.acum_cuentas = [0] * 5
        self.acum_tiempo_ms = 0
        
        lbl_estado = QLabel("Estado:")
        lbl_estado.setStyleSheet(ESTILO_LABEL)
        lbl_estado.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(lbl_estado,6,2)
        self.lbl_conexion = QLabel("DESCONECTADO")
        self.lbl_conexion.setStyleSheet(ESTILO_DESCONECTADO)
        layout.addWidget(self.lbl_conexion,6,3)
        
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.actualizar)
        self.cronometro.start() 
        self.timer.start(50)




    def _crear_columna_labels(self,layout:QGridLayout,etiquetas,fila_inicio,columna):
        
        labels=[]
        for N,CH in enumerate(etiquetas):
            label=QLabel(CH,alignment=Qt.AlignCenter)
            
            layout.addWidget(label,fila_inicio+N,columna)
            labels.append(label)
        return labels

    def _crear_fila_labels(self,layout:QGridLayout,etiquetas,columna_inicio,fila):
        labels=[]
        for N,CH in enumerate(etiquetas):
            label=QLabel(CH,alignment=Qt.AlignCenter)
    
            layout.addWidget(label,fila,columna_inicio+N)
            labels.append(label)
        return labels

    def _crear_columna_valores(self,layout:QGridLayout,etiquetas,fila_inicio,columna):
        
        contadores=[]
        for N,_ in enumerate(etiquetas):
            number=QLabel("0")
            number.setStyleSheet(ESTILO_VALOR)
            layout.addWidget(number,fila_inicio+N,columna)
            contadores.append(number)
        return contadores

    def actualizar(self):
        nuevas = self.lector.leer()
        segundos_desde_inicio=self.cronometro.elapsed()//1000

        if self.lector.conectado:
            self.timer.start()
            self.lbl_conexion.setStyleSheet(ESTILO_CONECTADO)
            self.lbl_conexion.setText("CONECTADO")
        else : 
            self.timer.stop()
            self.lbl_conexion.setStyleSheet(ESTILO_DESCONECTADO)
            self.lbl_conexion.setText("DESCONECTADO")
            

        self.lbl_tiempo.setText(formatear_segundos(segundos_desde_inicio))
        if not nuevas:
            return

        for _, intervalo_ms,cuentas in nuevas:
            for N in range(len(self.acum_cuentas)):
                self.acum_cuentas[N] += cuentas[N]
            self.acum_tiempo_ms += intervalo_ms

        _,ultimo_intervalo,ultimas_cuentas = nuevas[-1]
            
        for N in range(len(self.cps_actual)):
            cps=ultimas_cuentas[N]/ultimo_intervalo*1000
                
            self.cps_actual[N].setText(f"{cps:,.0f}")
                    
            self.cuentas_totales[N].setText(f"{self.acum_cuentas[N]:,}")
                
            self.cps_promedio[N].setText(f"{self.acum_cuentas[N]/self.acum_tiempo_ms*1000:,.2f}")

    def closeEvent(self, event):
    # detener el timer y cerrar el lector
        self.timer.stop()
        self.lector._desconectar()
        super().closeEvent(event)
            


def formatear_segundos(segundos_totales):
    H,seg_restantes_de_horas = divmod(segundos_totales,3600)
    M,s = divmod(seg_restantes_de_horas,60)
    return f"{H}:{M:02d}:{s:02d}"