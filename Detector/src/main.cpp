#include <Arduino.h>

volatile uint32_t cuentas[5];
unsigned long t_anterior = 0;
uint32_t cuentas_anterior[5];
uint tiempoActualizacion = 1000;
void IRAM_ATTR isr0();  //función que aumenta el contador cada vez que llega una cuenta
void IRAM_ATTR isr1();
void IRAM_ATTR isr2();
void IRAM_ATTR isr3();
void IRAM_ATTR isr4();

void reset();

void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);

  pinMode(32,INPUT);
  attachInterrupt(digitalPinToInterrupt(32),isr0,RISING);

  pinMode(33,INPUT);
  attachInterrupt(digitalPinToInterrupt(33),isr1,RISING);

  pinMode(34,INPUT);
  attachInterrupt(digitalPinToInterrupt(34),isr2,RISING);

  pinMode(35,INPUT);
  attachInterrupt(digitalPinToInterrupt(35),isr3,RISING);

  pinMode(25,INPUT);
  attachInterrupt(digitalPinToInterrupt(25),isr4,RISING);

  tone(26,100);
}


void loop() {
  
  if (millis()-t_anterior >= tiempoActualizacion) {
    
    t_anterior += tiempoActualizacion;
    noInterrupts();
    uint32_t copia[5];
    for (int i = 0; i<5; i++) {
      copia[i]=cuentas[i];
    }
    interrupts();
    uint32_t neto[5];
    for (int i = 0; i<5; i++) {
      neto[i] = copia[i]- cuentas_anterior[i];
      cuentas_anterior[i] = copia[i];
    }
    for (int i = 0; i<5; i++) {
      if (i!=4) {
        Serial.print(neto[i]);
        Serial.print(",");
      } else {
        Serial.println(neto[i]);
      }
    }
  }

}


void isr0() {
  cuentas[0]++;
}
void isr1() {
  cuentas[1]++;
}
void isr2() {
  cuentas[2]++;
}

void isr3() {
  cuentas[3]++;
}

void isr4() {
  cuentas[4]++;
}

void reset() {
  noInterrupts();
  for (int i = 0; i<5; i++) {
    cuentas[i] = 0;
    cuentas_anterior[i] =0;
  }
  interrupts();
}