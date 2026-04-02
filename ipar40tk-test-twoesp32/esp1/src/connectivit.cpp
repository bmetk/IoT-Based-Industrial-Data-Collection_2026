#include <Arduino.h>
#include <EspMQTTClient.h>
#include <credentials.h>
#include <HardwareSerial.h>

HardwareSerial SerialInterconn(2);

//------------------------
// Creating the ESP client
//------------------------
EspMQTTClient client {
  SSID,
  PWD,
  MQTT_ADDR,
  MQTT_USR,
  MQTT_PWD,
  "compactmaps1",
  MQTT_PORT
};



void onConnectionEstablished(){
  Serial.println("ESP ONLINE");
}



void clearSerialInterconn() {
  int x;
  while ((x = SerialInterconn.available()) > 0)
  {
     while (x--) SerialInterconn.read();
  }
}


//------------------------------------
// Initializing communication channels
//------------------------------------
void initCom(){
  // configuring the client
  client.enableDebuggingMessages();
  client.setKeepAlive(10);
  client.setMaxPacketSize(20000);
  client.setMqttReconnectionAttemptDelay(10000);
  client.setWifiReconnectionAttemptDelay(10000);

  // Serial communication between esps
  SerialInterconn.begin(115200, SERIAL_8N1, 16, 17);
  clearSerialInterconn();
}



bool checkClientCon(){
  return client.isConnected();
}
bool checkWifiCon(){
  return client.isWifiConnected();
}
void clientLoop() {
  client.loop();
}



void sendMqttMessage(char* topic, const char* msg){
  client.publish(topic, msg);
}



void sendSerialMessage(u_char msg) {
  SerialInterconn.write(msg);
  //Serial.print("Message sent: 0x"); Serial.println(msg, HEX);
}



u_char checkSerialMessage() {
  if(SerialInterconn.available() > 0) {
    u_char msg = SerialInterconn.read();
    return msg;
  }
  else
    return 0;
}