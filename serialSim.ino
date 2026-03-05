int aa = 50;
#define down 0
#define up 2
void setup() {
  // put your setup code here, to run once:
  Serial.begin(9600);

pinMode(down,INPUT_PULLUP);
pinMode(up,INPUT_PULLUP);

}

void loop() {
  // put your main code here, to run repeatedly:

  if (digitalRead(down) == LOW) {
    aa--;
    delay(100);
  }
  if (digitalRead(up) == LOW) {
    aa++;
    delay(100);
  }

  Serial.println(aa);
}