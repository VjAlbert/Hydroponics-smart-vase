# hydroponics-smart-vase
# DIY 3D-Printed Smart Hydroponics System

Welcome to the DIY 3D-Printed Smart Hydroponics System project! This repository contains all the necessary code and information to build your own automated hydroponics vase, monitored and controlled via a web interface and a Python GUI.

The system uses an ATmega328P (Arduino Uno/Nano) to manage sensors and the water pump, an ESP8266 for Wi-Fi connectivity and a web API, and a Python Tkinter application for user-friendly remote control and data logging.

**The 3D model for the hydroponic vase can be found here: [LINK TO YOUR 3D MODEL - e.g., Thingiverse, Printables, GrabCAD]**

## Features

*   **Water Level Monitoring:** Uses an HC-SR04 ultrasonic sensor to measure the water level in the reservoir.
*   **Soil Moisture Monitoring:** Employs an analog capacitive soil moisture sensor (or similar).
*   **Automated Pump Control:** A relay module controls a water pump based on configurable irrigation cycles.
*   **Manual Pump Override:** Turn the pump ON/OFF manually via the Python GUI.
*   **OLED Display:** An SSD1306 I2C OLED display connected to the ATmega328P shows real-time sensor data and system status.
*   **Wi-Fi Connectivity:** The ESP8266 connects to your local Wi-Fi network.
*   **Web API:** The ESP8266 hosts a simple API to fetch sensor data and send control commands.
*   **Python GUI Controller:** A Tkinter-based desktop application for:
    *   Displaying live sensor data (water level, soil moisture).
    *   Showing pump and irrigation cycle status.
    *   Setting custom irrigation cycles (pump ON duration, OFF interval).
    *   Manually controlling the pump.
    *   Managing a local database of plant profiles (plant name, insertion date, fertilizer info, preferred cycle).
    *   Exporting/Importing plant database to/from CSV.
*   **Serial Communication:** Robust serial communication between the ATmega328P and ESP8266.

## System Architecture

1.  **Sensors (HC-SR04, Soil Moisture):** Connected to the ATmega328P.
2.  **Pump & OLED Display:** Controlled by/connected to the ATmega328P.
3.  **ATmega328P (Arduino):**
    *   Reads sensor data.
    *   Controls the pump based on an automated cycle or manual commands.
    *   Displays status on the OLED screen.
    *   Communicates with the ESP8266 via serial (TX/RX).
4.  **ESP8266:**
    *   Connects to the Wi-Fi network.
    *   Communicates with the ATmega328P via serial to exchange data and commands.
    *   Hosts a web server with API endpoints for the Python GUI.
    *   Relays commands from the GUI to the ATmega328P.
5.  **Python GUI:**
    *   Runs on a computer connected to the same network.
    *   Communicates with the ESP8266's web API (HTTP GET/POST requests).
    *   Provides a user interface for monitoring and control.

## Hardware Components

*   **Microcontrollers:**
    *   1x ATmega328P based board (e.g., Arduino Uno, Arduino Nano)
    *   1x ESP8266 based board (e.g., NodeMCU, Wemos D1 Mini)
*   **Sensors:**
    *   1x HC-SR04 Ultrasonic Sensor (for water level)
    *   1x Analog Capacitive Soil Moisture Sensor (or resistive, check voltage requirements)
*   **Actuators & Display:**
    *   1x 5V Relay Module (to control the pump)
    *   1x Small 5V Water Pump
    *   1x SSD1306 I2C OLED Display (128x64 pixels)
*   **Power:**
    *   5V Power supply (ensure enough current for all components, especially the pump)
    *   3.3V power source (ESP8266, potentially some sensors - check datasheets)
*   **Miscellaneous:**
    *   Jumper wires
    *   Breadboard (optional, for prototyping)
    *   Resistors (if needed for logic level shifting between ESP8266 and ATmega328P, though direct connection often works for RX/TX if ATmega328P can tolerate 3.3V high on RX from ESP TX). **Note:** ESP8266 is NOT 5V tolerant on its RX pin. A voltage divider or logic level shifter is recommended for the ESP8266's RX pin when connected to the ATmega328P's TX pin.
    *   3D Printed Vase/Structure (Link above)
    *   Tubing for the pump

## Wiring & Connections

Refer to the `wiring_diagrams/connections.txt` file for detailed pin connections. A summary is provided below:

**1. ATmega328P (Arduino) Connections:**

*   **HC-SR04 (Ultrasonic Sensor):**
    *   `VCC` -> `5V`
    *   `TRIG` -> `Pin D9`
    *   `ECHO` -> `Pin D10`
    *   `GND` -> `GND`
*   **Soil Moisture Sensor (Analog):**
    *   `VCC` -> `5V` (or `3.3V`, check sensor specs)
    *   `AOUT` -> `Pin A0`
    *   `GND` -> `GND`
*   **Relay Module (Pump Control):**
    *   `VCC` -> `5V`
    *   `IN` -> `Pin D8`
    *   `GND` -> `GND`
    *   **Pump Wiring to Relay:**
        *   Relay `COM` -> Pump `+` (Positive)
        *   Relay `NO` (Normally Open) or `NC` (Normally Closed) -> `5V` (Pump Power Supply +). *The provided `collegamenti.txt` says "Normally closed" to 5V. This means the pump is ON when the relay coil is NOT energized. Typically, `NO` is used so the pump is OFF when the relay is not energized. Double-check your relay logic and code (`digitalWrite(PUMP_RELAY_PIN, HIGH/LOW)`).*
        *   Pump `-` (Negative) -> System `GND`
*   **OLED Display (SSD1306 I2C):**
    *   `VCC` -> `3.3V` or `5V` (check module specs)
    *   `GND` -> `GND`
    *   `SDA` -> `Pin A4` (SDA)
    *   `SCL` -> `Pin A5` (SCL)
*   **Communication with ESP8266:**
    *   `ATmega328P TX (Pin 1)` -> `ESP8266 RX` (e.g., `GPIO3/RX` on ESP8266) - **Potentially requires a voltage divider if ATmega328P TX is 5V and ESP8266 RX is not 5V tolerant.**
    *   `ATmega328P RX (Pin 0)` -> `ESP8266 TX` (e.g., `GPIO1/TX` on ESP8266)
    *   **Note:** Using Pins 0 and 1 on the ATmega328P for serial communication will interfere with USB serial communication (Serial Monitor, uploading sketches). Disconnect ESP8266 when uploading to ATmega328P.

**2. ESP8266 Connections:**

*   **Communication with ATmega328P:**
    *   `ESP8266 TX (GPIO1)` -> `ATmega328P RX (Pin 0)`
    *   `ESP8266 RX (GPIO3)` -> `ATmega328P TX (Pin 1)` (via a voltage divider: e.g., 1kΩ from ATmega TX to ESP RX, and 2kΩ from ESP RX to GND, to reduce 5V to ~3.3V).
*   **Power:**
    *   `ESP8266 VIN` -> `5V` (if your board has a 5V to 3.3V regulator) or `3.3V` -> `3.3V`
    *   `ESP8266 GND` -> `GND`
    *   Ensure a common ground (`GND`) between ATmega328P and ESP8266.

## Software Setup & Installation

**1. ATmega328P (Arduino Uno/Nano):**

*   **IDE:** Arduino IDE 1.8.x or later.
*   **Board Setup:**
    *   Select "Arduino Uno" or "Arduino Nano" from `Tools > Board`.
    *   Select the correct `Port` from `Tools > Port`.
*   **Libraries (Install via Arduino Library Manager `Sketch > Include Library > Manage Libraries...`):**
    *   `Adafruit GFX Library`
    *   `Adafruit SSD1306`
    *   `NewPing` by Tim Eckel
*   **Code:** Open `arduino_uno_firmware/arduino_uno_firmware.ino` in the Arduino IDE.
*   **Upload:** Compile and upload the sketch. (Remember to disconnect ESP8266 TX/RX from Arduino Pins 0/1 during upload if connected).

**2. ESP8266 (NodeMCU, Wemos D1 Mini, etc.):**

*   **IDE:** Arduino IDE 1.8.x or later.
*   **Board Setup (if not already done):**
    *   Add ESP8266 board support: `File > Preferences > Additional Boards Manager URLs`, add `http://arduino.esp8266.com/stable/package_esp8266com_index.json`.
    *   Go to `Tools > Board > Boards Manager...`, search for "esp8266" and install "esp8266 by ESP8266 Community".
    *   Select your specific ESP8266 board (e.g., "NodeMCU 1.0 (ESP-12E Module)") from `Tools > Board`.
    *   Configure board settings (CPU Frequency, Flash Size, Upload Speed, Port).
*   **Libraries (Install via Arduino Library Manager):**
    *   `ESP8266WiFi` (usually comes with the ESP8266 core installation)
    *   `ESP8266WebServer` (usually comes with the ESP8266 core installation)
    *   `ArduinoJson` by Benoit Blanchon (Version 6.x recommended)
*   **Code:** Open `esp8266_firmware/esp8266_firmware.ino` in the Arduino IDE.
*   **Configuration:**
    *   Modify the `ssid` and `password` variables in the sketch with your Wi-Fi credentials.
*   **Upload:** Compile and upload the sketch. The ESP8266 will attempt to connect to Wi-Fi and print its IP address to the Serial Monitor (set baud rate to 115200). Note this IP address.

**3. Python GUI Controller:**

*   **Python Version:** Python 3.7+ recommended.
*   **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
*   **Install Dependencies:**
    Navigate to the `python_gui_controller` directory in your terminal.
    If you create a `requirements.txt` file (see below), run:
    ```bash
    pip install -r requirements.txt
    ```
    Alternatively, install individually:
    ```bash
    pip install requests Pillow # Pillow for potential future image handling in Tkinter, requests is essential
    ```
    (Tkinter is usually part of the standard Python library.)
*   **Run the GUI:**
    ```bash
    python hydroponics_controller_gui.py
    ```
    The GUI will prompt you to enter the ESP8266's IP address.

**File: `python_gui_controller/requirements.txt`**
