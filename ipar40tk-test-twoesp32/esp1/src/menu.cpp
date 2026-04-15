#include <Arduino.h>
#include <menu.h>
#include <parameters.h>
#include <measurement.h>
#include <connectivity.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>
#include <display.h>
#include <ArduinoJson.hpp>
#include <ArduinoJson.h>
#include <connectivity.h>

//////////////////////////////////////////////////////////////////////////////////////
//
//    Constants / Definitions
//
//////////////////////////////////////////////////////////////////////////////////////
void toggleEsp1();
void toggleEsp2();
const char *ok(bool v);

uint8_t calcChecksum(Esp2Status &msg);

#define ESP1_STATUS_TOPIC "factory/lathe01/status/esp1"

Esp2State esp2;

uint8_t calcChecksum(Esp2Status &msg)
{
  uint8_t *ptr = (uint8_t *)&msg;
  uint8_t sum = 0;

  for (int i = 0; i < sizeof(Esp2Status) - 1; i++)
    sum ^= ptr[i];

  return sum;
}

const char *ok(bool v)
{
  return v ? "OK" : "ERR";
}

// New menu start
//  Display queue kívülről jön (main.cpp)
extern QueueHandle_t displayQueue;

//=========================
// STATE
//=========================
static MenuState currentMenu = MENU_HOME;
static int cursorIndex = 0;
MenuState getCurrentMenu() { return currentMenu; }
int getCursorIndex() { return cursorIndex; }

// időzített eseményekhez
static unsigned long actionStart = 0;
static bool actionActive = false;

//=========================
// DISPLAY REQUEST
//=========================
void requestDisplayUpdate()
{
  DisplayMessage msg;

  switch (currentMenu)
  {
  case MENU_HOME:
    msg.state = DISPLAY_HOME;
    break;

  case MENU_ERROR:
    msg.state = DISPLAY_ERROR;
    break;

  case MENU_SETTINGS:
  case MENU_SETTINGS_TOGGLE:
    msg.state = DISPLAY_SETTINGS;
    break;
  case MENU_SETTINGS_RESTART:
    msg.state = DISPLAY_SETTINGS;
    break;

  case MENU_MESSAGE:
    msg.state = DISPLAY_MESSAGE;
    strcpy(msg.msg, "Working...");
    break;
  }

  xQueueSend(displayQueue, &msg, 0);
}

//=========================
// INIT
//=========================
void menuInit()
{
  currentMenu = MENU_HOME;
  cursorIndex = 0;
  requestDisplayUpdate();
}

//=========================
// EVENT HANDLER
//=========================
void handleMenuEvent(MenuEvent event)
{
  switch (currentMenu)
  {
  //----------------------------------
  case MENU_HOME:
    if (event == EVENT_NEXT)
      currentMenu = MENU_ERROR;

    else if (event == EVENT_ENTER)
      cursorIndex = 0;
    break;

  //----------------------------------
  case MENU_ERROR:
    if (event == EVENT_NEXT)
      currentMenu = MENU_SETTINGS;

    else if (event == EVENT_ENTER)
      cursorIndex = 0;
    break;

  //----------------------------------
  case MENU_SETTINGS:
    if (event == EVENT_NEXT)
      cursorIndex = (cursorIndex + 1) % 3;

    else if (event == EVENT_ENTER)
    {
      switch (cursorIndex)
      {
      case 0:
        currentMenu = MENU_SETTINGS_TOGGLE;
        cursorIndex = 0;
        break;
      case 1:
        currentMenu = MENU_SETTINGS_RESTART;
        cursorIndex = 0;
        break;
      case 2:
        currentMenu = MENU_HOME;
        cursorIndex = 0;
        break;
      }
    }
    break;

  //----------------------------------
  case MENU_SETTINGS_TOGGLE:
    if (event == EVENT_NEXT)
      cursorIndex = (cursorIndex + 1) % 3;

    else if (event == EVENT_ENTER)
    {
      switch (cursorIndex)
      {
      case 0:
        toggleEsp1();
        break;

      case 1:
        toggleEsp2();
        break;

      case 2:
        currentMenu = MENU_SETTINGS;
        cursorIndex = 0;
        break;
      }
    }
    break;

  //----------------------------------
  case MENU_SETTINGS_RESTART:
    if (event == EVENT_NEXT)
      cursorIndex = (cursorIndex + 1) % 3;

    else if (event == EVENT_ENTER)
    {
      switch (cursorIndex)
      {
      case 0:
        // ESP1 restart
        ESP.restart();
        break;

      case 1:
        // ESP2 restart
        sendCommand(CMD_RESTART);
        currentMenu = MENU_MESSAGE;
        actionStart = millis();
        actionActive = true;
        break;

      case 2:
        currentMenu = MENU_SETTINGS;
        cursorIndex = 0;
        break;
      }
    }
    break;

  //----------------------------------
  case MENU_MESSAGE:
    // No button events are handled in this state
    break;
  }

  requestDisplayUpdate();
}

//=========================
// NON-BLOCKING ACTION HANDLER
//=========================
void menuLoop()
{
  if (actionActive && millis() - actionStart > 2000)
  {
    actionActive = false;
    currentMenu = MENU_SETTINGS;
    requestDisplayUpdate();
  }
}
// New menu end
//------------------------------------------------------------------
//  NAVIGATION
//
//  The menu system uses a finite state state machine, where
//  the current state is stored in an array. The first element
//  corresponds to the highest menu level and the last to the lowest.
//------------------------------------------------------------------

bool sendMeasurements = true;

//-----------------
// HOME TAB CONTENT
//-----------------
const char *espHealth[] = {"ON", "ERR", "OFF"};
const int homeRow = 3;
const int homeCol = 3;
// String espStatus[2][2] = {{espHealth[0], espHealth[0]},
//                         {espHealth[0], espHealth[0]}};
String homeContent[homeRow][homeCol] = {{"", "ONLINE", "SENSOR"},
                                        {"ESP 1", espHealth[0], espHealth[0]},
                                        {"ESP 2", espHealth[0], espHealth[0]}};

//-----------------------------------------------------------
// ERRORS TAB CONTENT
//
// possible errors: online(1-1) + sensors(3-1) = 6;
// if an error exists, the corresponding state is set to 1
//-----------------------------------------------------------
const int errorCount = 6;
const String errorContent[errorCount] = {"ESP1 CON",
                                         "CURRENT",
                                         "OPTO",
                                         "THERMO",
                                         "ESP2 CON",
                                         "ACCEL"};
const String noErrors = "NO ERRORS";
int errorEnable[errorCount] = {1, 0, 0, 1, 1, 1};

//---------------------------------------
// SETTINGS TAB CONTENT
//
// manual settings for the ESP-s:
//    - toggle online/offline state
//        - 2 sub-settings for both ESP-s
//    - restart ESP
//        - 2 sub-settings for both ESP-s
//---------------------------------------
const int settingsRow = 2;
const int settingsCol = 3;
const String settingsContent[settingsRow][settingsCol] = {{"TOGGLE ONLINE", "TOGGLE ESP1", "TOGGLE ESP2"},
                                                          {"RESTART MCU", "RESTART ESP1", "RESTART ESP2"}};
const String settingsSubmenu[settingsRow] = {"TOGGLE", "RESTART"};

//----------------------------
// Flags
//----------------------------
bool enableDataCollection = true;

//-----------------------------------------------
// create an OLED display object connected to I2C
//-----------------------------------------------
Adafruit_SSD1306 oled(SCREEN_W, SCREEN_H, &Wire, -1);

//////////////////////////////////////////////////////////////////////////////////////
//
//  Setup
//
//////////////////////////////////////////////////////////////////////////////////////

void setupDisplay()
{
  oled.begin(SSD1306_SWITCHCAPVCC, DISP_ADDR);
  delay(2000);
  oled.clearDisplay();

  oled.drawBitmap(33, 0, bmetk_bmp, BMETK_WIDTH, BMETK_HEIGHT, WHITE);
  delay(3000);
  oled.clearDisplay();

  oled.setTextSize(textSize);
  oled.setTextColor(WHITE);
}

//////////////////////////////////////////////////////////////////////////////////////
//
//    Function definitions
//
//////////////////////////////////////////////////////////////////////////////////////

//----------------------------------------------
//  Checking and setting measurement sync flag
//----------------------------------------------
bool checkSendMeasurements()
{
  return sendMeasurements;
}

void resetSendMeasurements()
{
  sendMeasurements = false;
}

String checkEsp2State()
{
  return homeContent[2][1];
}

bool isCollectionEnabled()
{
  return enableDataCollection;
}

void setErrorEnable(int index, int value)
{
  errorEnable[index] = value;
}

//------------------------------------------------------------
// Checks Serial2 for messages and updates content accordingly
//
// Codes:
//    - ONLINE             0x01
//    - OFFLINE (error)    0x02
//    - OFFLINE (manula)   0x04
//    - MPU DOWN           0x08
//    - MPU UP             0x10
//
//------------------------------------------------------------
u_char prevMsg = 0;

//-------------------------------
// Prints the current tabs header
//-------------------------------
void printTabHeader(String title)
{
  oled.setCursor(0, 0);
  oled.fillRect(0, 0, SCREEN_W - 1, textHeight + 2 * padding, WHITE);
  oled.setCursor(padding, padding);
  oled.setTextColor(BLACK);
  oled.print(title);
  oled.setTextColor(WHITE);
}

void updateHomeData()
{
  /*
   * Displays general information about the microcontrollers.
   * Upon entering, you can view detailed info on each ESP.
   */
  for (int i = 0; i < errorCount; i++)
  {
    if (errorEnable[i] != 0)
    {
      if (i == 0)
      {
        homeContent[1][1] = espHealth[1];
      }
      if (i >= 1 && i <= 3)
      {
        homeContent[1][2] = espHealth[1];
      }
    }
  }
  if (errorEnable[0] == 0 && homeContent[1][1] != espHealth[2])
  {
    homeContent[1][1] = espHealth[0];
  }
  if (errorEnable[1] == 0 && errorEnable[2] == 0 && errorEnable[3] == 0)
  {
    homeContent[1][2] = espHealth[0];
  }

  if (!esp2.online)
  {
    homeContent[2][1] = espHealth[2]; // OFF
    homeContent[2][2] = espHealth[2]; // OFF
  }
  else
  {
    // ONLINE / MQTT
    homeContent[2][1] = esp2.mqttOk ? espHealth[0] : espHealth[1];

    // SENSOR
    homeContent[2][2] = esp2.mpuOk ? espHealth[0] : espHealth[1];

    // COLLECTIN OFF
    if (!esp2.collecting)
    {
      homeContent[2][1] = espHealth[2]; // OFF
    }
  }
}

//-----------------------------------------------
// Assembles the Home tab with up to date content
//-----------------------------------------------
void homeTab()
{
  oled.clearDisplay();
  printTabHeader("HOME");

  // grid
  oled.drawLine(SCREEN_W / 3, headerHeight, SCREEN_W / 3, SCREEN_H - 1, WHITE);
  oled.drawLine(2 * SCREEN_W / 3 - 1, headerHeight, 2 * SCREEN_W / 3 - 1, SCREEN_H - 1, WHITE);
  oled.drawLine(0, headerHeight + offsetY, SCREEN_W - 1, headerHeight + offsetY, WHITE);
  updateHomeData();
  // content
  for (int i = 0; i < homeRow; i++)
  {
    for (int j = 0; j < homeCol; j++)
    {
      int x = j * offsetX + 2 * textSize;
      int y = i * (offsetY + 2 * textSize) + headerHeight;

      oled.setCursor(x, y);
      oled.print(homeContent[i][j]);
    }
  }
  // renderEsp2();
}

//------------------------------------------------------
// Assembles the Error tab's content with current issues
//------------------------------------------------------
void errorTab()
{
  oled.clearDisplay();
  printTabHeader("ERRORS");

  int spacing = 0;
  int x = textWidth + padding;
  int y = 0;
  int errorNumber = 0;

  for (int i = 0; i < errorCount; i++)
    if (errorEnable[i])
      errorNumber++;

  if (errorNumber == 0)
  {
    oled.setCursor(padding, SCREEN_H - 1 - textHeight);
    oled.print(noErrors);
    return;
  }

  oled.drawLine(SCREEN_W / 2 - 1, headerHeight, SCREEN_W / 2 - 1, SCREEN_H - 1, WHITE);

  for (int i = 0; i < errorCount; i++)
  {
    if (errorEnable[i])
    {
      y = spacing * (offsetY + padding) + headerHeight;

      oled.setCursor(x, y);
      oled.print(errorContent[i]);

      spacing++;

      if (i == 3)
      {
        x += SCREEN_W / 2 - 1;
        spacing = 0;
      }
    }
  }
}

//------------------------------------------------------
// Prints the Settings tab and it's submenus accordingly
//------------------------------------------------------
extern MenuState currentMenu;
extern int cursorIndex;

void settingsTab()
{
  oled.clearDisplay();
  printTabHeader("SETTINGS");
  MenuState state = getCurrentMenu();
  int cursor = getCursorIndex();
  String esp1StateStr = enableDataCollection ? "ON" : "OFF";
  String esp2StateStr = esp2.collecting ? "ON" : "OFF";
  switch (state)
  {
  //----------------------------------
  case MENU_SETTINGS:
    oled.setCursor(20, headerHeight);
    oled.print("Toggle ESP's");

    oled.setCursor(20, headerHeight + offsetY);
    oled.print("Restart ESP's");

    oled.setCursor(20, headerHeight + 2 * offsetY);
    oled.print("Back");

    drawCursor(cursorIndex);
    break;

  //----------------------------------
  case MENU_SETTINGS_TOGGLE:
    oled.setCursor(20, headerHeight);
    oled.println("Toggle ESP1: " + esp1StateStr);

    oled.setCursor(20, headerHeight + offsetY);
    oled.println("Toggle ESP2: " + esp2StateStr);

    oled.setCursor(20, headerHeight + 2 * offsetY);
    oled.print("BACK");

    drawCursor(cursorIndex);
    break;

  //----------------------------------
  case MENU_SETTINGS_RESTART:
    oled.setCursor(20, headerHeight);
    oled.print("Restart ESP1");

    oled.setCursor(20, headerHeight + offsetY);
    oled.print("Restart ESP2");

    oled.setCursor(20, headerHeight + 2 * offsetY);
    oled.print("BACK");

    drawCursor(cursorIndex);
    break;
  }
}

//-------------------------------------------------------------------------
// Draws the cursor in front of the current line (only after entering menu)
//-------------------------------------------------------------------------
void drawCursor(int idx)
{
  oled.fillRect(0, headerHeight, textWidth - 1, SCREEN_H - 1, BLACK);

  oled.setCursor(0, idx * (offsetY + padding) + headerHeight);
  oled.print(">");
}

//----------------------------------------------------------
// Toggle measurement collection and publishing for each esp
//----------------------------------------------------------
void toggleEsp1()
{
  enableDataCollection = !enableDataCollection;

  if (!enableDataCollection)
  {
    homeContent[1][1] = espHealth[2]; // OFF
  }
  else
  {
    homeContent[1][1] = espHealth[0]; // ON
  }
}

void toggleEsp2()
{
  /*
  - set flag to enable/disable measurements (suspend/resume task2)
  - set home tab content to ok/off
  */
  sendCommand(0x01); // code for toggle
}

bool readStatus(Esp2Status *dest)
{
  static uint8_t buffer[sizeof(Esp2Status)];
  static uint8_t index = 0;
  static unsigned long lastByteTime = 0;

  while (SerialInterconn.available())
  {
    uint8_t b = SerialInterconn.read();
    lastByteTime = millis();

    if (index == 0 && b != 0xAA)
      continue;

    buffer[index++] = b;

    if (index == sizeof(Esp2Status))
    {
      index = 0; // Kész, alaphelyzet a következőnek
      Esp2Status tempMsg;
      memcpy(&tempMsg, buffer, sizeof(Esp2Status));

      if (tempMsg.checksum == calcChecksum(tempMsg))
      {
        *dest = tempMsg; // Csak valid adatot írunk ki
        return true;
      }
    }
  }

  if (index > 0 && millis() - lastByteTime > 50)
  {
    index = 0; // Timeout reset
  }
  return false;
}

void updateEsp2(Esp2Status msg)
{
  esp2.online = msg.flags & FLAG_ONLINE;
  esp2.mqttOk = msg.flags & FLAG_MQTT;
  esp2.mpuOk = msg.flags & FLAG_MPU;
  esp2.tempOk = msg.flags & FLAG_TEMP;
  esp2.currentOk = msg.flags & FLAG_CURRENT;
  esp2.rpmOk = msg.flags & FLAG_RPM;
  esp2.collecting = msg.flags & FLAG_COLLECT;

  esp2.lastUpdate = millis();
}

void checkEsp2Timeout()
{
  if (millis() - esp2.lastUpdate > 15000)
  {
    esp2.online = false;
    esp2.lastUpdate = 0;
  }
}

void renderEsp2()
{
  oled.setCursor(0, 40);

  if (!esp2.online)
  {
    oled.print("ESP2: OFFLINE");
    return;
  }

  oled.print("ESP2: ");
  oled.print(ok(esp2.mqttOk));

  oled.setCursor(0, 50);
  oled.print("MPU: ");
  oled.print(ok(esp2.mpuOk));

  oled.setCursor(0, 60);
  oled.print("TMP: ");
  oled.print(ok(esp2.tempOk));
}

// void buildErrorList()
// {
//   errorCount = 0;

//   if (!esp2.online)
//     addError("ESP2 OFFLINE");

//   if (!esp2.mpuOk)
//     addError("ACCEL FAIL");

//   if (!esp2.tempOk)
//     addError("TEMP FAIL");
// }

void publishEsp1Status()
{
  StaticJsonDocument<256> doc;

  doc["esp1"] = true;
  doc["mqtt"] = checkClientCon();
  doc["temp"] = checkTempSensor();
  RpmStatus rpmStatus = checkRpmSensor();
  CurrentStatus currentStatus = checkCurrentSensor();
  doc["rpm"] = rpmStatusToString(rpmStatus);
  doc["current"] = currentStatusToString(currentStatus);
  doc["esp2"] = esp2.online;
  doc["esp2_collect"] = esp2.collecting;
  doc["esp2_mpu"] = esp2.mpuOk;

  char buffer[256];
  serializeJson(doc, buffer);

  sendMqttMessage(ESP1_STATUS_TOPIC, buffer);
}