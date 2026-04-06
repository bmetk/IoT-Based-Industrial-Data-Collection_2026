#include <Arduino.h>
#include <menu.h>
#include <parameters.h>
#include <connectivity.h>
#include <Adafruit_SSD1306.h>
#include <Adafruit_GFX.h>
#include <Wire.h>


//////////////////////////////////////////////////////////////////////////////////////
//
//    Constants / Definitions
//
//////////////////////////////////////////////////////////////////////////////////////



//------------------------------------------------------------------
// NAVIGATION
//
// The menu system uses a finite state state machine, where 
// the current state is stored in an array. The first element
// corresponds to the highest menu level and the last to the lowest.
//------------------------------------------------------------------
int currentState[4] = {0,0,0,0};
const int lastIndex = sizeof(currentState)/sizeof(currentState[0]) -1;
const String menuTabs[3] = {"HOME", "ERRORS", "SETTINGS"};
const char cursor = '>';
const String exitLevel = "BACK";
bool inSecondLevel = false;
bool inThirdLevel = false;
int prevCursorY = headerHeight;

bool sendMeasurements = false;

//-----------------
// HOME TAB CONTENT
//-----------------
const String espHealth[3] = {"OK", "ERR", "OFF"};
const int homeRow = 3;
const int homeCol = 3;
//String espStatus[2][2] = {{espHealth[0], espHealth[0]}, 
//                        {espHealth[0], espHealth[0]}};
String homeContent[homeRow][homeCol] = {{"",      "ONLINE",        "SENSOR"},
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
int errorEnable[errorCount] = {1,0,0,1,1,1};


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

void setupDisplay() {
  oled.begin(SSD1306_SWITCHCAPVCC, DISP_ADDR);
  delay(2000);
  oled.clearDisplay();

  oled.drawBitmap(33,0, bmetk_bmp, BMETK_WIDTH, BMETK_HEIGHT, WHITE);
  oled.display();
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



//--------------------------------------------------------------
// Prints the current state in the state machine (for debugging)
//--------------------------------------------------------------
void printState() {
  Serial.print("state: "); 
  Serial.print(currentState[0]); Serial.print(":"); 
  Serial.print(currentState[1]); Serial.print(":"); 
  Serial.print(currentState[2]); Serial.print(":"); 
  Serial.println(currentState[3]);
}



//-----------------------------------------------
// Updates the current state after a button press
//-----------------------------------------------
void updateState(char* btnId) {
  if(strcmp(btnId, "next") == 0) {
    if(!inSecondLevel && !inThirdLevel)
      currentState[0]++;
    else if(inSecondLevel && !inThirdLevel)
      currentState[1]++;
    else
      currentState[2]++;
  }
  else if(strcmp(btnId, "enter") == 0) {
    currentState[lastIndex]++;
  }
  firstLevel();
}


//---------------------------------------
// Creating a non-blocking delay function
//---------------------------------------
unsigned long prevMillis = 0;
void nonBlockingDelay(int interval = 2000) {
  //unsigned long currentMillis = millis();
  prevMillis = millis();

  while (millis() - prevMillis <= interval){};
} 



//----------------------------------------------
//  Checking and setting measurement sync flag
//----------------------------------------------
bool checkSendMeasurements() {
  return sendMeasurements;
}

void resetSendMeasurements() {
  sendMeasurements = false;
}

String checkEsp2State() {
  return homeContent[2][1];
}

bool isCollectionEnabled() {
  return enableDataCollection;
}

void setErrorEnable(int index, int value) {
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
void processSerial(u_char msg) {

  if(msg != 0 && msg <= 0x1F) {
    //Serial.print("Message: 0x"); Serial.println(msg, HEX);

    if(msg & 0x01) {
      homeContent[2][1] = espHealth[0];
      errorEnable[4] = 0;      
      //Serial.print(".  ONLINE");
    }
    if(msg & 0x02) {
      homeContent[2][1] = espHealth[1];
      errorEnable[4] = 1;
      //Serial.print(".  OFFLINE (ERR)");
      //Serial.println(errorEnable[4]);
    }
    if(msg & 0x04) {
      homeContent[2][1] = espHealth[2];
      errorEnable[4] = 0;
      //Serial.print(".  OFFLINE (MANUAL)");
    }
    if(msg & 0x08) {
      homeContent[2][2] = espHealth[1];
      errorEnable[5] = 1;
      //Serial.print(".  MPU DOWN");
    }
    if(msg & 0x10) {
      homeContent[2][2] = espHealth[0];
      errorEnable[5] = 0;
      //Serial.print(".  MPU UP");
    }
    //Serial.println("");
    //for(int i=0; i<errorCount; i++) {
      //Serial.print(errorEnable[i]);
      //Serial.print(", ");
    //}
    //Serial.println("");
    firstLevel();
  }
  else if(msg == 0xAA) {
    //Serial.println("Accel data ready");
    sendMeasurements = true;
  }
}



//-------------------------------
// Prints the current tabs header
//-------------------------------
void printTabHeader(String title) {
  oled.setCursor(0, 0);
  oled.fillRect(0, 0, SCREEN_W-1, textHeight+2*padding, WHITE);
  oled.setCursor(padding, padding);
  oled.setTextColor(BLACK);
  oled.print(title);
  oled.setTextColor(WHITE);
}



//-----------------------------------------------
// Assembles the Home tab with up to date content
//-----------------------------------------------
void homeTab() {
  /*
  * Displays general information about the microcontrollers.
  * Upon entering, you can view detailed info on each ESP.
  */
  for (int i=0; i<errorCount; i++) {
    if(errorEnable[i] != 0) {
      if(i==0) {
        homeContent[1][1]=espHealth[1];
      }
      if(i>=1&& i<=3) {
        homeContent[1][2]=espHealth[1];
      }
    }
  }

  if(errorEnable[0] == 0 && homeContent[1][1] != espHealth[2]) {
    homeContent[1][1] = espHealth[0];
  } 
  if(errorEnable[1] == 0 && errorEnable[2] == 0 && errorEnable[3] == 0) {
    homeContent[1][2] = espHealth[0];
  }

  // screen header
  oled.clearDisplay();
  printTabHeader(menuTabs[0]);
  
  // drawing the grid
  oled.drawLine(SCREEN_W/3,   headerHeight,    SCREEN_W/3,   SCREEN_H-1, WHITE); // vertical
  oled.drawLine(2*SCREEN_W/3-1, headerHeight,    2*SCREEN_W/3-1, SCREEN_H-1, WHITE); //vertical
  oled.drawLine(0,            headerHeight+offsetY,  SCREEN_W-1,     headerHeight+offsetY,  WHITE); // horisontal
  
  
  // content of the grid
  for(int i=0; i<homeRow; i++){
    for(int j=0; j<homeCol; j++){
      int x = j * offsetX + 2*textSize;
      int y = i * (offsetY+2*textSize) + headerHeight;
      oled.setCursor(x, y);
      oled.print(homeContent[i][j]);
    }
  }

  oled.display();
}



//------------------------------------------------------
// Assembles the Error tab's content with current issues
//------------------------------------------------------
void errorTab(/*bool nextPage*/) {
  /*
  * Lists errors regarding the ESP-s. You can cycle through
  * them and take actions to solve the issues.
  */

  // screen header
  oled.clearDisplay();
  printTabHeader(menuTabs[1]);

  bool errESP1 = false, errESP2 = false;
  int errorNumber = 0;
  int spacing = 0;
  int x = textWidth+padding;
  int y = 0;
  
  // check for errors
  for(int i=0; i<errorCount; i++){
    if(errorEnable[i] != 0) {
      errorNumber++;
      

      if(i<4) {
        errESP1 = true;
      }
      else {
        errESP2 = true;
      }
    }
  }


  if(errorNumber == 0){
    oled.setCursor(padding, SCREEN_H-1-textHeight);
    oled.print(noErrors);
  }
  else {

    // draw column divider
    oled.drawLine(SCREEN_W/2-1, headerHeight,    SCREEN_W/2-1, SCREEN_H-1, WHITE);

    for(int i=0; i<errorCount; i++) {
      y = spacing * (offsetY+padding) + headerHeight;

      if(errorEnable[i] != 0) {
        //Serial.print("Error found at index "); Serial.println(i);
        oled.setCursor(x, y);
        oled.print(errorContent[i]);
        spacing++;
      }
      if(i == 3) {
        x = x + SCREEN_W/2-1;
        spacing = 0;
      }
    }
  }
  
  oled.display();
  //Serial.println("Error page updated");
}



//------------------------------------------------------
// Prints the Settings tab and it's submenus accordingly
//------------------------------------------------------
void settingsTab() {
  /*
  * Gives the user tools for manual actions (start/stop data
  * collection, sensors, connectivity, etc.)
  */

  // screen header
  oled.clearDisplay();

  String submenu="";
  if(inThirdLevel && currentState[1] == 1)
    submenu = "/" + settingsSubmenu[0];
  else if(inThirdLevel & currentState[1] == 2)
    submenu = "/" + settingsSubmenu[1];

  printTabHeader(menuTabs[2] + submenu);

  // print settings according to current State in the state machine
  
  // settings second level
  if(currentState[2] == 0){
    for(int i=0; i<settingsRow; i++){
      oled.setCursor(textWidth+padding, i * (offsetY+padding) + headerHeight);
      oled.print(settingsContent[i][0]);
    }
  }
  

  // settings third level - toggle
  if(currentState[1] == 1 && inThirdLevel){
    for(int i=1; i<settingsCol; i++){
      oled.setCursor(textWidth+padding, (i-1) * (offsetY+padding) + headerHeight);
      oled.print(settingsContent[0][i]);
    }
  }
  // settings third level - restart
  else if(currentState[1] == 2 && inThirdLevel){
    for(int i=1; i<settingsCol; i++){
      oled.setCursor(textWidth+padding, (i-1) * (offsetY+padding) + headerHeight);
      oled.print(settingsContent[1][i]);
    }
  }

  if(inSecondLevel || inThirdLevel) {
    oled.setCursor(textWidth+padding, 2 * (offsetY+padding) + headerHeight);
    oled.print(exitLevel);
  }

  oled.display();
}




//-------------------------------------------------------------------------
// Draws the cursor in front of the current line (only after entering menu)
//-------------------------------------------------------------------------
void drawCursor(int idx){
  // deleting previous cursor
  oled.fillRect(0, headerHeight, textWidth-1, SCREEN_H-1, BLACK);
  oled.setCursor(0, idx*(offsetY+padding) + headerHeight);

  oled.print(cursor);
  oled.display();
}



//=======================================================================================
//
// This section contains the state machine logic with the correponding action's functions
//
//=======================================================================================


void secondLevel();
void thirdLevel();



//----------------------------------------------------------
// Toggle measurement collection and publishing for each esp
//----------------------------------------------------------
void toggleEsp1() {
  /*
  - set flag to enable/disable measurements (suspend/resume task2)
  - set home tab content to ok/off
  */
  if(homeContent[1][1] != espHealth[2]) {
    homeContent[1][1] = espHealth[2];
    enableDataCollection = false;
  }
  else if(homeContent[1][1] == espHealth[2]) {
    homeContent[1][1] = espHealth[0];
    enableDataCollection = true;
  }
}

void toggleEsp2() {
  /*
  - set flag to enable/disable measurements (suspend/resume task2)
  - set home tab content to ok/off
  */
  sendSerialMessage(0x01); // code for toggle
}



//------------------------------------------------------------------------------------------------------
// This is the entrypoint of the state machine. When NEXT gets pressed, it cycles through the main tabs.
// When pressing ENTER you can navigate to the available submenus.
//------------------------------------------------------------------------------------------------------
void firstLevel() {
  switch (currentState[0]){

    case 0: // show Home tab
      homeTab();
      currentState[lastIndex] = 0;
      break;
    
    case 1: // show Errors tab
      errorTab();
      currentState[lastIndex] = 0;
      break;
    
    case 2: // show Settings tab
      settingsTab();
      if(inSecondLevel)
        secondLevel();
      else if(currentState[lastIndex] != 0){
        currentState[1] = 1;
        if(!inSecondLevel)
          currentState[lastIndex] = 0;
        secondLevel();
      }
      break;
    
    default:
      currentState[0] = 0;
      firstLevel();
      break;
  }
}



//----------------------------------------------
// This is the second level for the Settings tab. When adding a second level for other tabs,
// define the states here.
//----------------------------------------------
void secondLevel() {

  // Settings
  if(currentState[0] == 2){
    inSecondLevel = true;
    settingsTab();

    switch (currentState[1]){

      case 1: // toggle options
        if(inThirdLevel)
          thirdLevel();
        else if(currentState[lastIndex] != 0) {
          currentState[2] = 1;
          if(!inThirdLevel)
            currentState[lastIndex] = 0;
          thirdLevel();
        }
        else
          drawCursor(0);
        break;

      case 2: // restart options
        if(inThirdLevel)
          thirdLevel();
        else if(currentState[lastIndex] != 0) {
          currentState[2] = 1;
          if(!inThirdLevel)
            currentState[lastIndex] = 0;
          thirdLevel();
        }
        else
          drawCursor(1);
        break;

      case 3: // back
        drawCursor(2);
        if(currentState[lastIndex] != 0) {
          currentState[1] = 0;                          
          currentState[lastIndex] = 0;                  
          inSecondLevel = false;                       
          firstLevel();
        }
        break;

      default:
        currentState[1] = 1;
        secondLevel();
        break;
    }
  }
}


//----------------------------------------------------------------------
// The third level of the state machine. Submenus for Toggle and Restart
//----------------------------------------------------------------------
void thirdLevel(){

  // Toggle online
  if(currentState[1] == 1){
    inThirdLevel = true;
    settingsTab();

    switch (currentState[2]){

      case 1: // toggle esp1
        drawCursor(0);
        if(currentState[lastIndex] != 0) {
          currentState[lastIndex] = 0;
          oled.clearDisplay();
          oled.setCursor(16,27);
          oled.print("Toggling ESP1..");
          oled.display();
          toggleEsp1();
          nonBlockingDelay(2000);
          thirdLevel();
        }
        break;

      case 2: // toggle esp2
        drawCursor(1);
        if(currentState[lastIndex] != 0) {
          currentState[lastIndex] = 0;
          oled.clearDisplay();
          oled.setCursor(16,27);
          oled.print("Toggling ESP2..");
          oled.display();
          toggleEsp2();
          nonBlockingDelay(2000);
          thirdLevel();
        };
        break;

      case 3: // back
        drawCursor(2);
        if(currentState[lastIndex] != 0) {
          
          currentState[2] = 0;
          currentState[lastIndex] = 0;
          inThirdLevel = false;
          secondLevel();
        }
        break;

      default:
        currentState[2] = 1;
        thirdLevel();
        break;
    }
  }

  // Restart ESP
  else if(currentState[1] == 2){
    inThirdLevel = true;
    settingsTab();

    switch (currentState[2]){

      case 1: // restart esp1
        drawCursor(0);
        if(currentState[lastIndex] != 0){
          currentState[lastIndex] = 0;
          oled.clearDisplay();
          oled.setCursor(16,27);
          sendSerialMessage(0x01);
          oled.print("Restarting ESP1..");
          oled.display();
          nonBlockingDelay(2000);
          ESP.restart();
        }
        break;

      case 2: // restart esp2
        drawCursor(1);
        if(currentState[lastIndex] != 0){
          currentState[lastIndex] = 0;
          oled.clearDisplay();
          oled.setCursor(16,27);
          oled.print("Restarting ESP2..");
          oled.display();
          sendSerialMessage(0x02); // code for restarting esp2
          nonBlockingDelay(2000);
          thirdLevel();
        }
        break;

      case 3: // back
        drawCursor(2);
        if(currentState[lastIndex] != 0) {
          currentState[2] = 0;
          currentState[lastIndex] = 0;
          inThirdLevel = false;
          secondLevel();
        }
        break;

      default:
        currentState[2] = 1;
        thirdLevel();
        break;
    }
  }
}