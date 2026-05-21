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

#define ESP1_STATUS_TOPIC "factory/lathe02/status/esp1"

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


// Displayqueue from main.cpp
extern QueueHandle_t displayQueue;

//=========================
// STATE
//=========================
static MenuState currentMenu = MENU_HOME;
static int cursorIndex = 0;
MenuState getCurrentMenu() { return currentMenu; }
int getCursorIndex() { return cursorIndex; }

// Variables for handling actions in the menu
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
  // HOME TAB - only navigation, no actions
  case MENU_HOME:
    if (event == EVENT_NEXT)
      currentMenu = MENU_ERROR;

    else if (event == EVENT_ENTER)
      cursorIndex = 0;
    break;

  // ERROR TAB - only navigation, no actions
  case MENU_ERROR:
    if (event == EVENT_NEXT)
      currentMenu = MENU_SETTINGS;

    else if (event == EVENT_ENTER)
      cursorIndex = 0;
    break;

  // SETTINGS TAB - navigation and actions
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

  // SETTINGS_TOGGLE TAB - navigation and actions
  case MENU_SETTINGS_TOGGLE:
    if (event == EVENT_NEXT)
      cursorIndex = (cursorIndex + 1) % 3;

    else if (event == EVENT_ENTER)
    {
      switch (cursorIndex)
      {
      case 0:
        // toggle data collection for ESP1
        toggleEsp1();
        break;

      case 1:
        // toggle data collection for ESP2
        toggleEsp2();
        break;

      case 2:
        // back to settings menu
        currentMenu = MENU_SETTINGS;
        cursorIndex = 0;
        break;
      }
    }
    break;

  // SETTINGS_RESTART TAB - navigation and actions
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
        // back to settings menu
        currentMenu = MENU_SETTINGS;
        cursorIndex = 0;
        break;
      }
    }
    break;

  // MESSAGE TAB - only navigation, no actions
  case MENU_MESSAGE:
    // No button events are handled in this state
    break;
  }
  // After handling the event, request a display update to reflect any changes
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


bool sendMeasurements = true;
//-----------------
// HOME TAB CONTENT
//-----------------
const char *espHealth[] = {"ON", "ERR", "OFF"};
const int homeRow = 3;
const int homeCol = 3;
// home tab content is updated in the homeTab() function, but the initial state is set here
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
// Create an OLED display object connected to I2C
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

//-------------------------------
// Function for checking the state of ESP1 and ESP2 and updating the home tab content accordingly
//-------------------------------
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

  // Grid
  oled.drawLine(SCREEN_W / 3, headerHeight, SCREEN_W / 3, SCREEN_H - 1, WHITE);
  oled.drawLine(2 * SCREEN_W / 3 - 1, headerHeight, 2 * SCREEN_W / 3 - 1, SCREEN_H - 1, WHITE);
  oled.drawLine(0, headerHeight + offsetY, SCREEN_W - 1, headerHeight + offsetY, WHITE);
  updateHomeData();
  // Content
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
  // Settings main menu
  case MENU_SETTINGS:
    oled.setCursor(20, headerHeight);
    oled.print("Toggle ESP's");

    oled.setCursor(20, headerHeight + offsetY);
    oled.print("Restart ESP's");

    oled.setCursor(20, headerHeight + 2 * offsetY);
    oled.print("Back");

    drawCursor(cursorIndex);
    break;

  // Toggle submenu
  case MENU_SETTINGS_TOGGLE:
    oled.setCursor(20, headerHeight);
    oled.println("Toggle ESP1: " + esp1StateStr);

    oled.setCursor(20, headerHeight + offsetY);
    oled.println("Toggle ESP2: " + esp2StateStr);

    oled.setCursor(20, headerHeight + 2 * offsetY);
    oled.print("BACK");

    drawCursor(cursorIndex);
    break;

  // Restart submenu
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
  sendCommand(0x01); // Code for toggle
}
//-------------------------------
// Function for assembling the display content of the home tab based on the current state of ESP1
// ------------------------------
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
      index = 0; // Reset index for the next message
      Esp2Status tempMsg;
      memcpy(&tempMsg, buffer, sizeof(Esp2Status));

      if (tempMsg.checksum == calcChecksum(tempMsg))
      {
        *dest = tempMsg; // Copy the valid message to the destination
        return true;
      }
    }
  }
  // If we receive bytes but the message is not complete, we check for a timeout to reset the index
  if (index > 0 && millis() - lastByteTime > 50)
  {
    index = 0; // Timeout reset
  }
  return false;
}

// Function for updating the home tab content based on the received status message from ESP2
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

// Function for checking if ESP2 has timed out (no messages received for a certain time) and updating the home tab content accordingly
void checkEsp2Timeout()
{
  if (millis() - esp2.lastUpdate > 15000)
  {
    esp2.online = false;
    esp2.lastUpdate = 0;
  }
}

// Function for publishing ESP1's status to the MQTT broker
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