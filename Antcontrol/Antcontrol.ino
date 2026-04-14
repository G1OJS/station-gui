#define LoopPos A0
#define LoopMotorA 10
#define LoopMotorB 9
#define RotatorPos A3
#define RotatorMotorA 11
#define RotatorMotorB 8
#define RxAnt 4
#define MainAnt 3

const int TIMEOUT = 60000;

unsigned int CurrStep_Loop = 500;
int TargetStep_Loop;
unsigned int CurrStep_Rotator = 500;
int TargetStep_Rotator;
String cmd = "";

void setup() {
  Serial.begin(9600);
  pinMode(LoopMotorA, OUTPUT);
  pinMode(LoopMotorB, OUTPUT);
  pinMode(RxAnt, OUTPUT);
  pinMode(MainAnt, OUTPUT);
  LoopMotor_stop();
  RotatorMotor_stop();
  getAndPrintCurrStep_Loop();
  getAndPrintCurrStep_Rotator();
  printReady();
}

void LoopMotor_stop(){
  digitalWrite(LoopMotorA, LOW);
  digitalWrite(LoopMotorB, LOW);
}

void RotatorMotor_stop(){
  digitalWrite(RotatorMotorA, LOW);
  digitalWrite(RotatorMotorB, LOW);
}

void loop() {
  
  if (readSerialCommand()) {
    char cmd_ = cmd.charAt(0);
    if (cmd_ == 'T') {  //T = Tune to
      TargetStep_Loop = cmd.substring(1).toInt();
      Serial.print("Tune to step: "); Serial.println(TargetStep_Loop);
      tuneLoopToStep();
    }
    if (cmd_ == 'M') {digitalWrite(MainAnt, (cmd.charAt(1) == 'L') );}
    if (cmd_ == 'R') {digitalWrite(RxAnt, (cmd.charAt(1) == 'M') );}
    if (cmd == 'QL') {getAndPrintCurrStep_Loop();}
    if (cmd == 'QR') {getAndPrintCurrStep_Rotator();}
    if (cmd_ == 'P') {
      TargetStep_Rotator = cmd.substring(1).toInt();
      Serial.print("Rotate to step: "); Serial.println(TargetStep_Rotator);
      rotateToStep();
    }
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

void tuneLoopToStep() {
  if (CurrStep_Loop < TargetStep_Loop) {
    moveLoopToTarget(true);
  } else {
    const int reverse = 5;
    TargetStep_Loop -= reverse;
    moveLoopToTarget(false);
    delay(250);
    TargetStep_Loop += reverse;
    moveLoopToTarget(true);
  }
  printReady();
}

void moveLoopToTarget(bool directionUp) {
  int PWM = 120;
  int power = 0;
  int lastStep = CurrStep_Loop;
  unsigned long t0 = millis();
  while (true) {
    getAndPrintCurrStep_Loop();
    bool fast = (CurrStep_Loop > TargetStep_Loop) || (CurrStep_Loop < TargetStep_Loop - 20);
    if (fast) {
      power = 255;
    } else {
      if (abs(CurrStep_Loop - lastStep) < 1) {
        if (PWM < 250) PWM++;
      } else {
        if (PWM > 120) PWM--;
      }
      power = PWM;
    }
    lastStep = CurrStep_Loop;
    // Drive LoopMotor
    if (CurrStep_Loop != TargetStep_Loop) {
      analogWrite(directionUp ? LoopMotorA : LoopMotorB, power);
      analogWrite(directionUp ? LoopMotorB : LoopMotorA, 0);
    }
    // Break conditions
    if ((CurrStep_Loop >= TargetStep_Loop && directionUp) ||
        (CurrStep_Loop <= TargetStep_Loop && !directionUp) ||
        (millis() - t0 > TIMEOUT)) {
      break;
    }
  }
  LoopMotor_stop();
}

void rotateToStep() {
  unsigned long t0 = millis();
  bool directionUp = (TargetStep_Rotator > CurrStep_Rotator);
  while (true) {
    delay(100);
    getAndPrintCurrStep_Rotator();
    if (CurrStep_Rotator != TargetStep_Rotator) {
      analogWrite(directionUp ? RotatorMotorA : RotatorMotorB, 255);
      analogWrite(directionUp ? RotatorMotorB : RotatorMotorA, 0);
    }
    // Break conditions
    if ((CurrStep_Rotator >= TargetStep_Rotator && directionUp) ||
        (CurrStep_Rotator <= TargetStep_Rotator && !directionUp) ||
        (millis() - t0 > TIMEOUT)) {
      break;
    }
  }
  RotatorMotor_stop();
}

void getAndPrintCurrStep_Loop() {
  CurrStep_Loop = analogRead(LoopPos);
  Serial.print("CurrStepLoop ");
  Serial.println(CurrStep_Loop);
}

void getAndPrintCurrStep_Rotator() {
  CurrStep_Rotator = analogRead(RotatorPos);
  Serial.print("CurrStepRotator ");
  Serial.println(CurrStep_Rotator);
}

void printReady() {
  Serial.println();
  Serial.print("READY ");
}
