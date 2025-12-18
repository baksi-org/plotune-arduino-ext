const int tempPin = A0;
const int voltagePin = A2;
const int speedPin = A4;

void setup() {
  Serial.begin(9600);
}

void loop() {
  int tempRaw = analogRead(tempPin);
  int voltageRaw = analogRead(voltagePin);
  int speedRaw = analogRead(speedPin);

  float temp = map(tempRaw, 0, 1023, 0, 25);
  float voltage = map(voltageRaw, 0, 1023, 0, 400);
  float speed = map(speedRaw, 0, 1023, 0, 100);

  unsigned long ts = millis();

  Serial.print("temperature,"); Serial.print(temp); Serial.print(","); Serial.println(ts);
  Serial.print("voltage,"); Serial.print(voltage); Serial.print(","); Serial.println(ts);
  Serial.print("speed,"); Serial.print(speed); Serial.print(","); Serial.println(ts);

  delay(500);
}
