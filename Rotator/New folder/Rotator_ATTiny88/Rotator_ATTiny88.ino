
#define OFF 0
#define LEFT 1
#define RIGHT 2
#define LED_PIN 0  // Built in LED
#define MOTORPOS_PIN 10
#define MOTORNEG_PIN 11
#define WIPER_PIN A3

void motorDrive(unsigned char state){
  digitalWrite(MOTORPOS_PIN,(state==RIGHT));
  digitalWrite(MOTORNEG_PIN,(state==LEFT));
}

// the usual stuff to set up pins ...
void setup() {
  pinMode(WIPER_PIN, INPUT);
  pinMode(LED_PIN, OUTPUT);
  pinMode(MOTORPOS_PIN, OUTPUT);
  pinMode(MOTORNEG_PIN, OUTPUT);  
}

void loop() {
  
  motorDrive(OFF);
}

