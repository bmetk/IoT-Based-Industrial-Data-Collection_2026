#ifndef MENU_H
#define MENU_H

#include <Arduino.h>
#include <Adafruit_SSD1306.h>

// Function prototypes
void homeTab();
void errorTab();
void settingsTab();
void publishEsp1Status();
void setupDisplay();
void drawCursor(int idx);
void resetSendMeasurements();
void updateState(const char* btnId="");
void printTabHeader(String title="");
void processSerial(u_char msg);
void setErrorEnable(int index, int value);
void updateHomeData();
void checkEsp2Timeout();

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

// State variables for the menu
struct Esp2State
{
  bool online;
  bool mqttOk;
  bool mpuOk;
  bool tempOk;
  bool currentOk;
  bool rpmOk;
  bool collecting;

  unsigned long lastUpdate;
};

// Serial message structure for communication between ESPs
#pragma pack(push, 1)
struct Esp2Status
{
  uint8_t header; // 0xAA
  uint8_t version;

  uint8_t flags;

  uint32_t uptime;

  uint8_t checksum;
};
#pragma pack(pop)

// Menu state machine variables
void menuInit();
void menuLoop();
void handleMenuEvent(MenuEvent event);
void requestDisplayUpdate();
MenuState getCurrentMenu();
int getCursorIndex();
void updateEsp2(Esp2Status msg);
bool readStatus(Esp2Status *dest);

// Error handling variables
#define FLAG_ONLINE 0x01
#define FLAG_MQTT 0x02
#define FLAG_MPU 0x04
#define FLAG_TEMP 0x08
#define FLAG_CURRENT 0x10
#define FLAG_RPM 0x20
#define FLAG_COLLECT 0x40

#define CMD_TOGGLE   0x01
#define CMD_RESTART  0x02
// External variables
extern Esp2State esp2;

#endif