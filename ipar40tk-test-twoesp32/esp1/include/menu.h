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


#endif