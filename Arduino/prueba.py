import serial

ser = serial.serial_for_url("rfc2217://localhost:4000", baudrate=115200,timeout=2)
print("Conectado")
while True:

    print(ser.readline().decode().strip().split(","))
