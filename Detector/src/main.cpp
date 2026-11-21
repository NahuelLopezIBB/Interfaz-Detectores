#include <Arduino.h>


void setup() {
  // put your setup code here, to run once:
  Serial.begin(115200);
  pinMode(13,OUTPUT);
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd == "ON") {
      digitalWrite(13,HIGH);
      Serial.println("OK");
    }
    else if (cmd == "OFF" ) {
      
      digitalWrite(13,LOW);
  } else {
    Serial.println("ERR");
  }
  }
  
  

}
