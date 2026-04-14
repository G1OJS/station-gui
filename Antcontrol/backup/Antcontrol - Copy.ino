#define LoopPos A0;
const int LoopMotorA = 10;
const int LoopMotorB = 9;

const int RxAnt = 4;
const int MainAnt = 3;
const int TIMEOUT = 60000;

unsigned int CurrStep_Loop = 500;
int TargetStep_Loop;
String cmd = "";

void setup() {
  Serial.begin(9600);
  pinMode(LoopMotorA, OUTPUT);
  pinMode(LoopMotorB, OUTPUT);
  pinMode(RxAnt, OUTPUT);
  pinMode(MainAnt, OUTPUT);
  getAndPrintCurrStep_Loop();
  printReady();
}

void LoopMotor_stop(){
  digitalWrite(LoopMotorA, LOW);
  digitalWrite(LoopMotorB, LOW);
}

void loop() {
  
  if (readSerialCommand()) {
    char cmd_ = cmd.charAt(0);
    if (cmd_ == 'T') {  //T = Tune to
      TargetStep_Loop = cmd.substring(1).toInt();
      Serial.print("Tune to: "); Serial.println(TargetStep_Loop);
      tuneLoopToStep();
    }
    if (cmd_ == 'M') {digitalWrite(MainAnt, (cmd.charAt(1) == 'L') );}
    if (cmd_ == 'R') {digitalWrite(RxAnt, (cmd.charAt(1) == 'M') );}
    if (cmd_ == 'Q') {getAndPrintCurrStep_Loop();}
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

void getAndPrintCurrStep_Loop() {
  CurrStep_Loop = analogRead(LoopPos);
  Serial.print("CurrStep_Loop ");
  Serial.println(CurrStep_Loop);
}

void printReady() {
  Serial.println();
  Serial.print("READY ");
}
