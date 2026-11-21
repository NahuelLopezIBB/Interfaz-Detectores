import serial

ser = serial.serial_for_url("rfc2217://localhost:4000", baudrate=115200,timeout=2)
print("Conectado")
while True:
    inp = input("Set estado:")
    inp = inp + '\n'
    ser.write(inp.encode())

    print(ser.readline().decode().strip())
