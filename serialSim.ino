int aa = 50;
#define down 0
#define up 2
long randNumber;
void setup() {
  // put your setup code here, to run once:
  Serial.begin(1200);

  pinMode(down, INPUT_PULLUP);
  pinMode(up, INPUT_PULLUP);
  randomSeed(analogRead(0));
}

void loop() {
  // put your main code here, to run repeatedly:
  randNumber = random(400);
  randNumber = randNumber - 200;
  float rnd = randNumber / 100.00;

  if (digitalRead(down) == LOW) {
    aa--;
    delay(100);
  }
  if (digitalRead(up) == LOW) {
    aa++;
    delay(100);
  }
  Serial.print("ST,GS  ");
  Serial.print(aa + rnd);
  Serial.println("KG");
  
}