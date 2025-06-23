#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <NewPing.h> // Libreria più semplice per HC-SR04

// --- Configurazione Display OLED ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET -1 // Reset pin # (or -1 if sharing Arduino reset pin)
Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- Configurazione HC-SR04 (Livello Acqua) ---
#define TRIGGER_PIN 9
#define ECHO_PIN 10
#define MAX_DISTANCE_CM 50 // Distanza massima che il sensore può misurare (regola in base al vaso)
NewPing sonar(TRIGGER_PIN, ECHO_PIN, MAX_DISTANCE_CM);
// Calibrazione livello acqua (distanza in cm dal sensore)
const int DISTANCE_EMPTY_CM = 25; // Esempio: sensore a 25cm dal fondo quando il vaso è vuoto
const int DISTANCE_FULL_CM = 5;  // Esempio: sensore a 5cm dal pelo dell'acqua quando è pieno

// --- Configurazione Sensore Umidità Suolo ---
#define SOIL_MOISTURE_PIN A0
// Calibrazione umidità (valori ADC grezzi)
const int MOISTURE_DRY_ADC = 700; // Valore ADC quando il sensore è asciutto (in aria)
const int MOISTURE_WET_ADC = 300; // Valore ADC quando il sensore è bagnato (in acqua)

// --- Configurazione Relè Pompa ---
#define PUMP_RELAY_PIN 8

// --- Variabili di Stato e Ciclo Irrigazione ---
int waterLevelPercent = 0;
int soilMoisturePercent = 0;
String ipAddress = "IP: N/A"; // Ricevuto da ESP8266

unsigned long pumpOnDurationMs = 0; // 0 significa controllo manuale o nessuna impostazione
unsigned long pumpOffIntervalMs = 1000 * 60 * 20; // Default: 20 minuti spenta (non usato se pumpOnDurationMs è 0)

unsigned long lastPumpActionTime = 0;
bool pumpIsOn = false;
bool cycleActive = false;

unsigned long lastDataSendTime = 0;
const unsigned long DATA_SEND_INTERVAL = 2000; // Invia dati all'ESP ogni 2 secondi

void setup() {
  Serial.begin(115200); // Per comunicazione con ESP8266

  // Inizializza OLED
  if (!display.begin(SSD1306_SWITCHCAPVCC, 0x3C)) { // Indirizzo I2C potrebbe essere 0x3D
    // Serial.println(F("SSD1306 allocation failed")); // Non possiamo usare Serial per debug qui
    for (;;); // Non continuare, loop infinito
  }
  display.clearDisplay();
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, 0);
  display.println("Hydroponics UNO");
  display.display();
  delay(1000);

  pinMode(PUMP_RELAY_PIN, OUTPUT);
  digitalWrite(PUMP_RELAY_PIN, LOW); // Pompa spenta all'inizio (LOW potrebbe attivare alcuni relè, verifica!)

  lastPumpActionTime = millis();
}

void loop() {
  unsigned long currentTime = millis();

  readSensors();
  updateOLED();
  handlePumpCycle(currentTime);
  handleSerialCommunication(currentTime);

  delay(100); // Breve pausa per stabilità
}

void readSensors() {
  // Lettura Livello Acqua
  delay(50); // Attendi ping (circa 29ms a ping)
  unsigned int distanceCm = sonar.ping_cm();
  if (distanceCm == 0) distanceCm = MAX_DISTANCE_CM; // Se fuori range, consideralo vuoto

  waterLevelPercent = map(distanceCm, DISTANCE_EMPTY_CM, DISTANCE_FULL_CM, 0, 100);
  waterLevelPercent = constrain(waterLevelPercent, 0, 100);

  // Lettura Umidità Suolo
  int moistureRaw = analogRead(SOIL_MOISTURE_PIN);
  soilMoisturePercent = map(moistureRaw, MOISTURE_DRY_ADC, MOISTURE_WET_ADC, 0, 100);
  soilMoisturePercent = constrain(soilMoisturePercent, 0, 100);
}

void drawBar(int x, int y, int width, int height, int percent, const char* label) {
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(x, y - 10);
  display.print(label);
  display.print(percent);
  display.print("%");

  display.drawRect(x, y, width, height, SSD1306_WHITE);
  int barWidth = map(percent, 0, 100, 0, width - 2); // -2 per i bordi
  if (percent > 0) {
    display.fillRect(x + 1, y + 1, barWidth, height - 2, SSD1306_WHITE);
  }

  // Segmenti per 20%, 50%, 80%
  int seg20 = map(20, 0, 100, 0, width - 2);
  int seg50 = map(50, 0, 100, 0, width - 2);
  int seg80 = map(80, 0, 100, 0, width - 2);

  display.drawFastVLine(x + 1 + seg20, y + 1, height - 2, SSD1306_BLACK);
  display.drawFastVLine(x + 1 + seg50, y + 1, height - 2, SSD1306_BLACK);
  display.drawFastVLine(x + 1 + seg80, y + 1, height - 2, SSD1306_BLACK);
}


void updateOLED() {
  display.clearDisplay();

  // Barra Livello Acqua (al centro)
  int barWidth = SCREEN_WIDTH - 20;
  int barHeight = 12;
  int barX = (SCREEN_WIDTH - barWidth) / 2;
  int waterBarY = 18; // Posizione Y per la barra dell'acqua
  drawBar(barX, waterBarY, barWidth, barHeight, waterLevelPercent, "H2O: ");

  // Barra Umidità Suolo (sotto quella dell'acqua)
  int moistureBarY = waterBarY + barHeight + 15; // Posizione Y per la barra dell'umidità
  drawBar(barX, moistureBarY, barWidth, barHeight, soilMoisturePercent, "Hum: ");
  
  // Visualizza IP Address (in basso)
  display.setTextSize(1);
  display.setTextColor(SSD1306_WHITE);
  display.setCursor(0, SCREEN_HEIGHT - 8); // In basso
  display.println(ipAddress);

  display.display();
}

void handlePumpCycle(unsigned long currentTime) {
  if (!cycleActive || pumpOnDurationMs == 0) { // Se ciclo non attivo o durata ON è zero
    // digitalWrite(PUMP_RELAY_PIN, LOW); // Assicura che la pompa sia spenta se non c'è ciclo
    // pumpIsOn = false; // Potrebbe essere controllata manualmente o da altra logica
    return;
  }

  if (pumpIsOn) {
    if (currentTime - lastPumpActionTime >= pumpOnDurationMs) {
      digitalWrite(PUMP_RELAY_PIN, LOW); // Spegni pompa (o HIGH se il relè è active-low)
      pumpIsOn = false;
      lastPumpActionTime = currentTime;
      // Serial.println("PUMP_OFF_CYCLE_END"); // Debug per ESP
    }
  } else { // Pompa è spenta, in attesa dell'intervallo
    if (currentTime - lastPumpActionTime >= pumpOffIntervalMs) {
      digitalWrite(PUMP_RELAY_PIN, HIGH); // Accendi pompa (o LOW se il relè è active-low)
      pumpIsOn = true;
      lastPumpActionTime = currentTime;
      // Serial.println("PUMP_ON_CYCLE_START"); // Debug per ESP
    }
  }
}

void handleSerialCommunication(unsigned long currentTime) {
  // Ricezione comandi da ESP8266
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();

    if (command.startsWith("SET_CYCLE:")) {
      // Formato: SET_CYCLE:ON_MIN,OFF_MIN
      // Esempio: SET_CYCLE:2,10 (2 minuti ON, ogni 10 minuti di OFF)
      int firstComma = command.indexOf(',');
      int secondComma = command.indexOf(',', firstComma + 1); // Non c'è una seconda virgola qui
                                                              // Correggo: la stringa è SET_CYCLE:ON_DURATION,OFF_INTERVAL
      
      String onDurationStr = command.substring(10, firstComma); // "SET_CYCLE:" ha 10 caratteri
      String offIntervalStr = command.substring(firstComma + 1);

      pumpOnDurationMs = onDurationStr.toInt() * 1000L * 60L; // Converti minuti in ms
      pumpOffIntervalMs = offIntervalStr.toInt() * 1000L * 60L; // Converti minuti in ms

      if (pumpOnDurationMs > 0 && pumpOffIntervalMs > 0) {
        cycleActive = true;
        pumpIsOn = false; // Forza lo stato iniziale a OFF, così parte con l'intervallo OFF
        digitalWrite(PUMP_RELAY_PIN, LOW); // Assicura che la pompa sia spenta
        lastPumpActionTime = currentTime; // Resetta il timer del ciclo
        Serial.print("ACK_CYCLE:");
        Serial.print(pumpOnDurationMs / (1000L * 60L));
        Serial.print(",");
        Serial.println(pumpOffIntervalMs / (1000L * 60L));
      } else {
        cycleActive = false;
        digitalWrite(PUMP_RELAY_PIN, LOW); // Spegni pompa se il ciclo non è valido
        Serial.println("ERR_CYCLE_INVALID");
      }
    } else if (command.startsWith("GET_DATA")) {
        sendDataToESP();
    } else if (command.startsWith("SET_IP:")) {
        ipAddress = command.substring(7); // "SET_IP:" ha 7 caratteri
    } else if (command.startsWith("PUMP_ON")) {
        digitalWrite(PUMP_RELAY_PIN, HIGH);
        pumpIsOn = true;
        cycleActive = false; // Controllo manuale disattiva il ciclo automatico
        Serial.println("ACK_PUMP_ON");
    } else if (command.startsWith("PUMP_OFF")) {
        digitalWrite(PUMP_RELAY_PIN, LOW);
        pumpIsOn = false;
        cycleActive = false; // Controllo manuale disattiva il ciclo automatico
        Serial.println("ACK_PUMP_OFF");
    }
  }

  // Invio dati a ESP8266 periodicamente
  if (currentTime - lastDataSendTime >= DATA_SEND_INTERVAL) {
    sendDataToESP();
    lastDataSendTime = currentTime;
  }
}

void sendDataToESP() {
    // Formato: DATA:WATER_PCT,MOISTURE_PCT,PUMP_STATUS(0 o 1),CYCLE_ACTIVE(0 o 1),ON_MIN,OFF_MIN
    Serial.print("DATA:");
    Serial.print(waterLevelPercent);
    Serial.print(",");
    Serial.print(soilMoisturePercent);
    Serial.print(",");
    Serial.print(pumpIsOn ? "1" : "0");
    Serial.print(",");
    Serial.print(cycleActive ? "1" : "0");
    Serial.print(",");
    Serial.print(pumpOnDurationMs / (1000L * 60L));
    Serial.print(",");
    Serial.println(pumpOffIntervalMs / (1000L * 60L));
}
