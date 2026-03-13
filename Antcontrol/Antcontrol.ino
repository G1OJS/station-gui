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
    if (cmd_ == 'B') { 
      Serial.print("Remove backlash to: "); Serial.println(TargetStep);
      remove_backlash();
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
  moveToTarget(CurrStep < TargetStep);
  printReady();
}

void remove_backlash() {
  if (CurrStep < TargetStep) {
    Serial.println("TUNING UP");
    moveToTarget(true);
  } else {
    const int reverse = 5;
    TargetStep -= reverse;
    Serial.println("TUNING DOWN");
    moveToTarget(false);
    delay(250);
    TargetStep += reverse;
    Serial.println("TUNING UP (fine)");
    moveToTarget(true);
  }
  printReady();
}

void moveToTarget(bool directionUp) {
  int PWM = 150;
  int lastStep = CurrStep;
  unsigned long t0 = millis();
  motor_stop();
  while (true) {
    getAndPrintCurrStep();
    // Adjust speed
    if (abs(CurrStep - lastStep) < 1) {
      if (PWM < 250) PWM++;
    } else {
      if (PWM > 150) PWM--;
    }
    lastStep = CurrStep;
    // Drive motor
    if (CurrStep != TargetStep) {
      int power = (abs(CurrStep - TargetStep) > 20 || !directionUp) ? 255 : PWM;
      analogWrite(directionUp ? MotorA : MotorB, power);
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
  Serial.println();
  Serial.print("CurrStep ");
  Serial.println(CurrStep);
}

void printReady() {
  Serial.println();
  Serial.print("READY ");
  Serial.println(CurrStep);
}
