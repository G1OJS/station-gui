const int MotorA = 10;
const int MotorB = 9;
const int RxAnt = 4;
const int MainAnt = 3;
const int TIMEOUT = 60000;

unsigned int CurrStep = 500;
int TargetStep;
String cmd = "";

void setup() {
  Serial.begin(9600);
  pinMode(MotorA, OUTPUT);
  pinMode(MotorB, OUTPUT);
  pinMode(RxAnt, OUTPUT);
  pinMode(MainAnt, OUTPUT);
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
      tuneToStep();
    }
    if (cmd_ == 'M') {digitalWrite(MainAnt, (cmd.charAt(1) == 'L') );}
    if (cmd_ == 'R') {digitalWrite(RxAnt, (cmd.charAt(1) == 'M') );}
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

void tuneToStep() {
  if (CurrStep < TargetStep) {
    moveToTarget(true);
  } else {
    const int reverse = 5;
    TargetStep -= reverse;
    moveToTarget(false);
    delay(250);
    TargetStep += reverse;
    moveToTarget(true);
  }
  printReady();
}

void moveToTarget(bool directionUp) {
  int PWM = 120;
  int power = 0;
  int lastStep = CurrStep;
  unsigned long t0 = millis();
  while (true) {
    getAndPrintCurrStep();
    bool fast = (CurrStep > TargetStep) || (CurrStep < TargetStep - 20);
    if (fast) {
      power = 255;
    } else {
      if (abs(CurrStep - lastStep) < 1) {
        if (PWM < 250) PWM++;
      } else {
        if (PWM > 120) PWM--;
      }
      power = PWM;
    }
    lastStep = CurrStep;
    // Drive motor
    if (CurrStep != TargetStep) {
      analogWrite(directionUp ? MotorA : MotorB, power);
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
