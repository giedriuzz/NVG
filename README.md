# NVG Thermal Camera Controller (2-Button UI)

This project is an ESP32-C3 based controller for a UART thermal camera module. It implements a minimalist 2-button interface specifically designed for Night Vision Goggle (NVG) / Thermal monocular applications where physical space is limited.

## Hardware Setup

* **Microcontroller:** ESP32-C3 SuperMini (or similar)
* **Camera Protocol:** UCI (55 43 49...) at 115200 Baud
* **PB1 (Menu/Minus Button):** GPIO 6 (Active Low to GND)
* **PB2 (Action/Plus Button):** GPIO 2 (Active Low to GND)
* **Status LED:** GPIO 3 (Active High / PWM - connect to GND via resistor)
* **Battery Voltage Sense:** GPIO 4 (ADC1 via 10k + 10k voltage divider)
* **UART TX:** GPIO 9
* **UART RX:** GPIO 10

---

## 🇬🇧 English: Control Logic

The system is built around a state machine with 4 modes. You start in **NORMAL** mode.
Holding **PB1 (Long Press)** cycles through the modes:
`NORMAL` -> `BRIGHTNESS` -> `CONTRAST` -> `ENHANCEMENT` -> `NORMAL`

### 1. NORMAL MODE (Default)

Used for fast access to essential features during operation.

* **PB1 Short Press:** Trigger Shutter Calibration (NUC)
* **PB2 Short Press:** Cycle Electronic Zoom (1x -> 2x -> 3x -> 4x -> 8x -> 1x)
* **PB2 Long Press:** Cycle Color Palette (White Hot, Black Hot, etc.)
* **PB1 Long Press:** Enter `BRIGHTNESS` Settings Mode (LED blinks 1 time)

### 2. SETTINGS MODES (Brightness / Contrast / Enhancement)

While in any setting mode, the buttons act purely as Minus (-) and Plus (+).

* **PB1 Short Press:** Decrease Value (-)
* **PB2 Short Press:** Increase Value (+)
* **PB1 Long Press:** Save and advance to the next settings mode (or return to NORMAL).

### LED Feedback

The external LED on GPIO 3 provides tactile visual feedback when cycling modes:

* **1 Short Blink:** Entered Brightness Mode
* **2 Short Blinks:** Entered Contrast Mode
* **3 Short Blinks:** Entered Enhancement Mode
* **1 Long Solid Blink:** Returned to Normal Mode
* **Gentle Continuous Pulse (Breathing):** Low battery warning ($\le 3.40\text{ V}$)
* **Double-Blink Heartbeat:** Wi-Fi OTA Update Mode active

### 3. Wi-Fi OTA Update Mode (No Internet Required)

During normal operation, Wi-Fi is completely disabled to save battery power.
To update files (`main.py`, `camera_uci.py`, `buttons.py`, etc.) wirelessly:

1. Hold **PB2** (or both **PB1 + PB2**) while powering on the device for **1 second**.
2. The status LED will start a **double-blink heartbeat** pattern.
3. Connect with your phone or computer to the Wi-Fi network:
   * **SSID:** `NVG-OTA`
   * **Password:** `nvgupdate`
4. Open **`http://192.168.4.1`** in your web browser.
5. Select the updated `.py` files, click **Upload**, and press **Reboot** when finished. (Uploaded `.py` files are automatically checked for syntax errors before overwriting!)

---

## 🇱🇹 Lietuviškai

Šis projektas – tai ESP32-C3 paremtas valdiklis UART šiluminei kamerai. Sistemoje įdiegtas minimalistinis 2 mygtukų valdymas, specialiai pritaikytas naktinio matymo / termovizinių monokuliarų sistemoms, kur fizinė vieta mygtukams yra labai ribota.

### Aparatinė įranga (Hardware Setup)

* **Mikrovaldiklis:** ESP32-C3 SuperMini (arba panašus)
* **Kameros protokolas:** UCI (55 43 49...) su 115200 sparta (Baud)
* **PB1 (Meniu / Minuso mygtukas):** GPIO 6 (Active Low į GND)
* **PB2 (Veiksmo / Pliuso mygtukas):** GPIO 2 (Active Low į GND)
* **Būsenos LED:** GPIO 3 (Active High / PWM – prijungti per rezistorių į GND)
* **Baterijos įtampos matavimas:** GPIO 4 (ADC1 per 10k + 10k įtampos daliklį)
* **UART TX:** GPIO 9
* **UART RX:** GPIO 10

### Valdymo Logika

Sistema turi 4 režimus. Įjungus prietaisą atsiduriate **PAGRINDINIAME (NORMAL)** režime.
Ilgas **PB1** paspaudimas perjungia režimus ratu:
`PAGRINDINIS` -> `ŠVIESUMAS` -> `KONTRASTAS` -> `IŠRYŠKINIMAS` -> `PAGRINDINIS`

### 1. PAGRINDINIS REŽIMAS (Normal - Numatytasis)

Naudojamas greitam svarbiausių funkcijų pasiekimui be papildomo meniu.

* **PB1 Trumpas paspaudimas:** Sukalibruoja jutiklį / užuolaidėlę (NUC)
* **PB2 Trumpas paspaudimas:** Keičia priartinimą (1x -> 2x -> 3x -> 4x -> 8x -> 1x)
* **PB2 Ilgas paspaudimas:** Keičia spalvų paletę (White Hot -> Black Hot)
* **PB1 Ilgas paspaudimas:** Eina į `ŠVIESUMO` nustatymą (LED sumirksi 1 kartą)

### 2. NUSTATYMŲ REŽIMAI (Šviesumas / Kontrastas / Išryškinimas)

Įėjus į bet kurį nustatymų režimą, mygtukai veikia tik kaip Minusas (-) ir Pliusas (+).

* **PB1 Trumpas paspaudimas:** Sumažinti reikšmę (-)
* **PB2 Trumpas paspaudimas:** Padidinti reikšmę (+)
* **PB1 Ilgas paspaudimas:** Išsaugoti ir pereiti į kitą nustatymą (arba grįžti į Pagrindinį režimą).

### LED Indikacija

Prie GPIO 3 prijungtas išorinis LED diodas padeda orientuotis, kokiame meniu esate:

* **1 Trumpas mirksnis:** Įjungtas Šviesumo (Brightness) režimas
* **2 Trumpi mirksniai:** Įjungtas Kontrasto (Contrast) režimas
* **3 Trumpi mirksniai:** Įjungtas Išryškinimo (Enhancement) režimas
* **1 Ilgas mirksnis:** Grįžta į Pagrindinį (Normal) režimą
* **Švelnus tolygus pulsavimas („kvėpavimas“):** Senkančios baterijos įspėjimas ($\le 3.40\text{ V}$)
* **Dvigubas mirksėjimas (kas 1.2 s):** Įjungtas Wi-Fi OTA atnaujinimo režimas

### 3. Programinės įrangos atnaujinimas per Wi-Fi (OTA)

Įprasto darbo metu Wi-Fi yra visiškai išjungtas, kad neeikvotų baterijos.
Norėdami belaidžiu būdu atnaujinti failus (`main.py`, `camera_uci.py`, `buttons.py` ir kt.) neišardydami korpuso:

1. Įjunkite maitinimą laikydami nuspaustą **PB2** (arba abu **PB1 + PB2**) bent **1 sekundę**.
2. Būsenos LED pradės mirksėti **dvigubais mirksniais** – tai reiškia, kad įjungtas OTA serveris.
3. Telefonu arba kompiuteriu prisijunkite prie Wi-Fi tinklo:
   * **Pavadinimas (SSID):** `NVG-OTA`
   * **Slaptažodis:** `nvgupdate`
4. Naršyklėje atidarykite adresą **`http://192.168.4.1`**.
5. Pasirinkite atnaujintus `.py` failus, paspauskite **„Įkelti į ESP32-C3“**, o baigę – **„Perkrauti įrenginį“**. (Prieš perrašant `.py` failus, sistema automatiškai patikrina Python sintaksę, kad klaidingas failas nesugadintų valdiklio darbo.)
