# NVG Thermal Camera Controller (2-Button UI)

This project is an ESP32-C3 based controller for a UART thermal camera module. It implements a minimalist 2-button interface specifically designed for Night Vision Goggle (NVG) / Thermal monocular applications where physical space is limited.

## Hardware Setup

* **Microcontroller:** ESP32-C3 SuperMini (or similar)
* **Camera Protocol:** UCI (55 43 49...) at 115200 Baud
* **PB1 (Menu/Minus Button):** GPIO 6 (Active Low to GND)
* **PB2 (Action/Plus Button):** GPIO 2 (Active Low to GND)
* **Status LED:** GPIO 3 (Active High - connect to GND)
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

---

## 🇱🇹 Lietuviškai: Valdymo Logika

Šis projektas – tai ESP32-C3 paremtas valdiklis UART šiluminei kamerai. Sistemoje įdiegtas minimalistinis 2 mygtukų valdymas, specialiai pritaikytas naktinio matymo / termovizinių monokuliarų sistemoms, kur fizinė vieta mygtukams yra labai ribota.

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
