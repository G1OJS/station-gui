const int MotorA = 10;
const int MotorB = 9;
const int TIMEOUT = 60000;

unsigned int CurrStep = 500;
int TargetStep;
String cmd = "";

void setup() {
  Serial.begin(9600);
  pinMode(MotorA, OUTPUT);
  pinMode(MotorB, OUTPUT);
  getAndPrintCurrStep();
  printReady();
}

void motor_stop(){
  digitalWrite(MotorA, LOW);
  digitalWrite(MotorB, LOW);
}

void loop() {
  
  if (readSerialCommand()) {
    char cmd_ = cmd.charAt(0);
    if (cmd_ == 'T') {  //T = Tune to
      TargetStep = cmd.substring(1).toInt();
      Serial.print("Tune to: "); Serial.println(TargetStep);
      moveToTarget();
      printReady();
    }
    if (cmd_ == 'Q') {getAndPrintCurrStep();}
  }
  delay(5);
}

bool readSerialCommand() {
  if (Serial.available()) {
    cmd = Serial.readStringUntil('>');     // Read until end marker
    int start = cmd.indexOf('<');
    if (start >= 0) {
      cmd = cmd.substring(start + 1);      // Strip start marker
      cmd.trim();                          // Clean up whitespace
      return true;
    }
  }
  return false;
}

void moveToTarget() {
  unsigned long t0 = millis();
  bool directionUp = (TargetStep > CurrStep);
  while (true) {
    delay(100);
    getAndPrintCurrStep();
    if (CurrStep != TargetStep) {
      analogWrite(directionUp ? MotorA : MotorB, 255);
      analogWrite(directionUp ? MotorB : MotorA, 0);
    }
    // Break conditions
    if ((CurrStep >= TargetStep && directionUp) ||
        (CurrStep <= TargetStep && !directionUp) ||
        (millis() - t0 > TIMEOUT)) {
      break;
    }
  }
  motor_stop();
}

void getAndPrintCurrStep() {
  CurrStep = analogRead(A0);
  Serial.print("CurrStep ");
  Serial.println(CurrStep);
}

void printReady() {
  Serial.println();
  Serial.print("READY ");
}
