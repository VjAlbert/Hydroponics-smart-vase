#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ArduinoJson.h>
// Non includere FS.h e SD.h se non usi la SD card

// --- Configurazione WiFi ---
const char* ssid = "Your SSID"; 
const char* password = "Your Password"; 

// --- Configurazione Server Web ---
ESP8266WebServer server(80);

// --- Variabili Globali per i dati dei sensori e stato ---
// Queste verranno popolate dai dati ricevuti dall'UNO
int espWaterLevel = 0;
int espSoilMoisture = 0;
bool espPumpStatus = false; // Stato attuale della pompa come riportato dall'UNO
bool espCycleActive = false; // Se un ciclo è attivo sull'UNO
unsigned long espPumpOnMinutes = 0; // Durata ON del ciclo attuale sull'UNO
unsigned long espPumpOffMinutes = 0; // Intervallo OFF del ciclo attuale sull'UNO

String espIpAddress = "N/A";

// Non c'è più DB_FILE_PATH

void setup() {
  Serial.begin(115200); // Comunicazione con ATmega328P e Monitor Seriale per debug ESP
  delay(100);
  Serial.println("\nESP8266 Hydroponics System (No SD-DB Mode)");

  // Non c'è più l'inizializzazione della SD Card

  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi ");
  int wifi_retries = 0;
  while (WiFi.status() != WL_CONNECTED && wifi_retries < 30) {
    delay(500);
    Serial.print(".");
    wifi_retries++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println(" Connected!");
    espIpAddress = WiFi.localIP().toString();
    Serial.print("IP Address: ");
    Serial.println(espIpAddress);
    // Invia l'IP all'ATmega328P
    Serial.print("SET_IP:"); 
    Serial.println(espIpAddress);
  } else {
    Serial.println(" Failed to connect to WiFi.");
    espIpAddress = "WiFi Err";
    Serial.print("SET_IP:");
    Serial.println(espIpAddress);
  }

  // --- Definizione Endpoints Server Web ---
  server.on("/data", HTTP_GET, handleGetData);
  server.on("/set_cycle", HTTP_POST, handleSetCycle);
  server.on("/pump_on", HTTP_POST, handlePumpOn);
  server.on("/pump_off", HTTP_POST, handlePumpOff);
  // Rimuovi gli endpoint /get_db, /save_db, /export_db

  server.onNotFound([]() {
    server.send(404, "text/plain", "Not found");
  });

  server.begin();
  Serial.println("HTTP server started");

  // Richiedi subito i dati all'UNO per inizializzare gli stati
  Serial.println("GET_DATA"); 
}

void loop() {
  server.handleClient();
  handleUnoSerial(); 
  delay(10); 
}

void handleUnoSerial() {
  if (Serial.available() > 0) { 
    String unoResponse = Serial.readStringUntil('\n');
    unoResponse.trim();
    
    // Debug opzionale (attenzione se Serial è usata per comunicazione con UNO)
    // USBSerial.print("ESP received from UNO: "); USBSerial.println(unoResponse);

    if (unoResponse.startsWith("DATA:")) {
      String payload = unoResponse.substring(5);
      int parts[6]; 
      int partIdx = 0;
      int lastCommaIdx = -1;
      int currentCommaIdx = -1;

      for (int i = 0; i < 5; i++) { 
          currentCommaIdx = payload.indexOf(',', lastCommaIdx + 1);
          if (currentCommaIdx == -1) break; 
          parts[partIdx++] = payload.substring(lastCommaIdx + 1, currentCommaIdx).toInt();
          lastCommaIdx = currentCommaIdx;
      }
      if (partIdx < 6) { 
        parts[partIdx++] = payload.substring(lastCommaIdx + 1).toInt();
      }

      if (partIdx == 6) { 
          espWaterLevel = parts[0];
          espSoilMoisture = parts[1];
          espPumpStatus = (parts[2] == 1);
          espCycleActive = (parts[3] == 1);
          espPumpOnMinutes = parts[4]; // Riceve lo stato attuale del ciclo dall'UNO
          espPumpOffMinutes = parts[5];
      }
    } else if (unoResponse.startsWith("ACK_CYCLE:")) {
        // L'UNO ha confermato il nuovo ciclo. Aggiorna le variabili locali dell'ESP.
        String payload = unoResponse.substring(10); // "ACK_CYCLE:"
        int commaIdx = payload.indexOf(',');
        if (commaIdx != -1) {
            espPumpOnMinutes = payload.substring(0, commaIdx).toInt();
            espPumpOffMinutes = payload.substring(commaIdx + 1).toInt();
            espCycleActive = true; // Il ciclo è ora attivo con questi parametri
            espPumpStatus = false; // Quando un ciclo viene settato, la pompa è inizialmente off (in attesa dell'intervallo)
            Serial.println("ESP: UNO confirmed new cycle. Local ESP state updated.");
        }
    } else if (unoResponse.startsWith("ACK_PUMP_ON")) {
        espPumpStatus = true;
        espCycleActive = false; // Il controllo manuale disattiva il ciclo
        Serial.println("ESP: UNO confirmed pump ON. Local ESP state updated.");
    } else if (unoResponse.startsWith("ACK_PUMP_OFF")) {
        espPumpStatus = false;
        // Se il ciclo era attivo, lo rimane. Spegnere manualmente la pompa non disattiva il ciclo sull'UNO,
        // ma per coerenza sull'ESP, se la pompa è spenta manualmente, consideriamo il ciclo non dominante in quel momento.
        // Tuttavia, l'UNO potrebbe riaccenderla al prossimo intervallo.
        // Per ora, seguiamo lo stato della pompa.
        Serial.println("ESP: UNO confirmed pump OFF. Local ESP state updated.");
    } else if (unoResponse.startsWith("ERR_")) {
        Serial.print("ESP received error from UNO: "); Serial.println(unoResponse);
    }
  }
}

void handleGetData() {
  // Richiedi dati aggiornati all'UNO prima di rispondere per avere lo stato più recente
  // Questo è importante perché lo stato del ciclo/pompa sull'ESP è solo una copia
  // di ciò che l'UNO riporta.
  Serial.println("GET_DATA"); 
  delay(200); // Dai tempo all'UNO di rispondere e a handleUnoSerial di processare

  StaticJsonDocument<256> doc; 
  doc["water_level"] = espWaterLevel;
  doc["soil_moisture"] = espSoilMoisture;
  doc["pump_status"] = espPumpStatus;
  doc["cycle_active"] = espCycleActive;
  doc["pump_on_min"] = espPumpOnMinutes;
  doc["pump_off_min"] = espPumpOffMinutes;
  doc["ip_address"] = espIpAddress; 

  String output;
  serializeJson(doc, output);
  server.send(200, "application/json", output);
}

void handleSetCycle() {
  if (server.hasArg("plain") == false) {
    server.send(400, "text/plain", "Body not received");
    return;
  }
  String body = server.arg("plain");
  StaticJsonDocument<128> doc;
  DeserializationError error = deserializeJson(doc, body);

  if (error) {
    server.send(400, "text/plain", "JSON parse error");
    return;
  }

  int onMin = doc["on_min"];
  int offMin = doc["off_min"];

  if (onMin > 0 && offMin > 0) {
    String commandToUno = "SET_CYCLE:" + String(onMin) + "," + String(offMin);
    Serial.println(commandToUno); // Invia comando all'UNO
    // L'ESP aggiornerà le sue variabili espPumpOnMinutes, ecc., quando riceverà ACK_CYCLE dall'UNO
    server.send(200, "text/plain", "Cycle command sent to UNO. Waiting for ACK from UNO.");
  } else {
    server.send(400, "text/plain", "Invalid cycle parameters.");
  }
}

void handlePumpOn() {
  Serial.println("PUMP_ON"); // Invia comando all'UNO
  server.send(200, "text/plain", "Pump ON command sent to UNO.");
}

void handlePumpOff() {
  Serial.println("PUMP_OFF"); // Invia comando all'UNO
  server.send(200, "text/plain", "Pump OFF command sent to UNO.");
}

