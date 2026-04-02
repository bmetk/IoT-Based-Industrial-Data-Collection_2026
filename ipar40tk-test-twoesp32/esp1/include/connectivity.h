#ifndef CONNECTIVITY_H
#define CONNECTIVITY_H

#include <Arduino.h>

void initCom();
bool checkClientCon();
void clientLoop();
void sendMqttMessage(char* topic, const char* msg);
void sendSerialMessage(u_char msg);
void clearSerialInterconn();
u_char checkSerialMessage();

#endif