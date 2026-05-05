#ifndef CONNECTIVITY_H
#define CONNECTIVITY_H

#include <Arduino.h>
#include <HardwareSerial.h>
// Function prototypes
void initCom();
bool checkClientCon();
void clientLoop();
void sendMqttMessage(char* topic, const char* msg);
void sendCommand(uint8_t cmd);
void clearSerialInterconn();
u_char checkSerialMessage();
// External variables
extern HardwareSerial SerialInterconn;

#endif