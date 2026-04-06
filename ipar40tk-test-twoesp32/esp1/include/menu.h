#ifndef MENU_H
#define MENU_H

#include <Arduino.h>

void homeTab();
void errorTab();
void settingsTab();
void firstLevel();
void setupDisplay();
void drawCursor(int idx);
void resetSendMeasurements();
void updateState(char* btnId="");
void printTabHeader(String title="");
void processSerial(u_char msg);
void setErrorEnable(int index, int value);

bool checkSendMeasurements();
bool isCollectionEnabled();

String checkEsp2State();
extern Adafruit_SSD1306 oled;

// States for the menu state machine
typedef enum {
  MENU_HOME,
  MENU_ERROR,
  MENU_SETTINGS,
  MENU_SETTINGS_TOGGLE,
  MENU_SETTINGS_RESTART,
  MENU_MESSAGE
} MenuState;

// Events for the menu state machine
typedef enum {
  EVENT_NEXT,
  EVENT_ENTER,
  EVENT_NONE
} MenuEvent;

// Menu state machine variables
void menuInit();
void handleMenuEvent(MenuEvent event);
void requestDisplayUpdate();

#endif