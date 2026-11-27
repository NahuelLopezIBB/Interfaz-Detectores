"""Prueba rápida del puerto serie, independiente de la interfaz.

Se conecta al simulador Wokwi (RFC2217 en localhost:4000) e imprime cada línea
recibida separada por comas. Corre hasta que se lo interrumpe con Ctrl+C.
"""
import serial

ser = serial.serial_for_url("rfc2217://localhost:4000", baudrate=115200,timeout=2)
print("Conectado")
# Lectura bloqueante (timeout=2): acá no hay GUI que congelar, a diferencia
# de LectorSerie.
while True:

    print(ser.readline().decode().strip().split(","))
