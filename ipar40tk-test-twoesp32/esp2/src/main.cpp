#include <Arduino.h>
#include "mpu9250.h"
#include "EspMQTTClient.h"
#include <Wire.h>
#include "credentials.h"
#include <ArduinoJson.hpp>
#include <ArduinoJson.h>

#define VIBX_TOPIC "factory/lathe01/vibration/mpu9250/vibX"
#define VIBY_TOPIC "factory/lathe01/vibration/mpu9250/vibY"
#define VIBZ_TOPIC "factory/lathe01/vibration/mpu9250/vibZ"

#define CHUNK_SIZE 128
#define DRDY_PIN 27
#define MPU_ADDR 0x68
#define WHOAMI_REG 0x75

bfs::Mpu9250 imu;
HardwareSerial SerialInterconn(2);

EspMQTTClient client(
    SSID,
    PWD,
    MQTT_ADDR,
    MQTT_USR,
    MQTT_PWD,
    "compactmaps2",
    MQTT_PORT);

static constexpr float G_MPS2 = 9.80665f;
// float accel_scale;
const int sampleSize = 1024;
bool DATA_READY = false;
volatile bool READ = false;
volatile int intCounter = 0;
bool enableCollection = false;
int idx = 0;

int16_t vRealX[sampleSize];
int16_t vRealY[sampleSize];
int16_t vRealZ[sampleSize];

bool mpuOk = true, prevMpuOk;
bool clientOk = true, prevClientOk;
bool enableDiagnostics = false;
bool stateChange = false;

void collectData();
void sendJsonMessage();
void sendChunkedData();
void publishChunk(const char *topic, int16_t *data, int startIdx, int len);
void checkSystemHealth();
void checkSerialMessage();
void sendSerialMessage();

void clearSerialInterconn()
{
  int x;
  while ((x = SerialInterconn.available()) > 0)
  {
    while (x--)
      SerialInterconn.read();
  }
}

void IRAM_ATTR onDataReady()
{
  READ = true;
  intCounter++;
}

void setup()
{
  setCpuFrequencyMhz(240);
  Serial.begin(115200);

  Wire.begin();
  Wire.setClock(400000);

  imu.Config(&Wire, bfs::Mpu9250::I2C_ADDR_PRIM);

  client.setKeepAlive(10);
  client.setMaxPacketSize(4096);
  client.setMqttReconnectionAttemptDelay(10000);
  client.setWifiReconnectionAttemptDelay(10000);

  while (!imu.Begin())
  {
    Serial.println("IMU init failed");
    delay(500);
  }

  imu.ConfigSrd(0);
  imu.ConfigAccelRange(bfs::Mpu9250::ACCEL_RANGE_4G);

  // interrupt
  pinMode(DRDY_PIN, INPUT_PULLUP);
  attachInterrupt(DRDY_PIN, onDataReady, RISING);

  // Waiting for connection
  while (!client.isConnected())
  {
    delay(200);
    client.loop();
  }

  // sending initial health
  delay(2000);

  // starting serial connection between ESPs
  SerialInterconn.begin(115200, SERIAL_8N1, 16, 17);
  clearSerialInterconn();
  sendSerialMessage();
  imu.EnableDrdyInt();
  Serial.println("IMU ready");
}

void loop()
{
  client.loop();

  if (enableCollection)
  {
    sendJsonMessage();
  }
  else
  {
    enableDiagnostics = true;
  }

  if (enableDiagnostics || !mpuOk)
  {
    checkSerialMessage();
    checkSystemHealth();
    if (stateChange)
    {
      Serial.println("Sending system health update");
      sendSerialMessage();
      stateChange = false;
    }
    client.loop();

    enableDiagnostics = false;
    imu.EnableDrdyInt();
  }

  vTaskDelay(1);
}

void onConnectionEstablished()
{
  Serial.println("Connected to broker.");
}

void collectData()
{

  if (imu.Read())
  {
    vRealX[idx] = (int16_t)(imu.accel_x_mps2() * 500);
    vRealY[idx] = (int16_t)(imu.accel_y_mps2() * 500);
    vRealZ[idx] = (int16_t)((imu.accel_z_mps2() + G_MPS2) * 500);

    idx++;
    READ = false;
  }
  else
  {
    enableDiagnostics = true;
    return;
  }

  if (idx >= sampleSize)
  {
    imu.DisableDrdyInt();
    DATA_READY = true;
  }
}

String arrayToString(float arr[])
{
  String encodedArray = "[";
  String sep = ", ";
  for (uint16_t i = 0; i < sampleSize; i++)
  {
    encodedArray += String(arr[i]);
    if (i < sampleSize - 1)
    {
      encodedArray += sep;
    }
    else
    {
      encodedArray += "]";
    }
  }

  return encodedArray;
}

void sendJsonMessage()
{
  if (READ)
  {
    collectData();
  }
  else if (DATA_READY)
  {

    imu.DisableDrdyInt();

    DATA_READY = false;
    intCounter = 0;
    READ = false;

    sendChunkedData();

    idx = 0;

    enableDiagnostics = true;
  }
}

void sendChunkedData()
{
  const int chunkSize = 128;

  for (int i = 0; i < sampleSize; i += chunkSize)
  {
    int len = min(chunkSize, sampleSize - i);

    publishChunk(VIBX_TOPIC, vRealX, i, len);
    client.loop();

    publishChunk(VIBY_TOPIC, vRealY, i, len);
    client.loop();

    publishChunk(VIBZ_TOPIC, vRealZ, i, len);
    client.loop();
  }
}

void checkSystemHealth()
{
  prevClientOk = clientOk;
  prevMpuOk = mpuOk;

  // checking client state
  clientOk = client.isConnected();

  // checking MPU state via WHOAMI register
  Wire.beginTransmission(MPU_ADDR);
  Wire.write(WHOAMI_REG);
  Wire.endTransmission(false);
  Wire.requestFrom(MPU_ADDR, 1);

  if (Wire.available())
  {
    byte val = Wire.read();
    mpuOk = true;
  }
  else
  {
    mpuOk = false;
    idx = 0;
  }

  // if there was a change, update the state of the system
  if (clientOk != prevClientOk || mpuOk != prevMpuOk)
    stateChange = true;
}

//------------------------------------------------------------
// Sending messages to ESP1
//
// Codes:
//    - ONLINE             0x01
//    - OFFLINE (error)    0x02
//    - OFFLINE (manula)   0x04
//    - MPU DOWN           0x08
//    - MPU UP             0x10
//
//------------------------------------------------------------
void sendSerialMessage()
{
  u_char msg = 0;
  Serial.println("Sending system health: ");

  if (enableCollection && clientOk)
  {
    msg += 0x01;
    Serial.print("ONLINE, ");
  }
  if (!clientOk)
  {
    msg += 0x02;
    Serial.print("OFFLINE (ERR), ");
  }
  if (!enableCollection)
  {
    msg += 0x04;
    Serial.print("OFFLINE (MANUAL), ");
  }
  if (!mpuOk)
  {
    msg += 0x08;
    Serial.print("MPU DOWN, ");
  }
  if (mpuOk)
  {
    msg += 0x10;
    Serial.print("MPU UP, ");
  }

  SerialInterconn.write(msg);
}

//----------------------------------
// Execute instructions sent by ESP1
//----------------------------------
void checkSerialMessage()
{
  if (SerialInterconn.available() > 0)
  {
    u_char msg = SerialInterconn.read();

    switch (msg)
    {
    case 0x01:
      enableCollection = !enableCollection;
      idx = 0;
      stateChange = true;
      break;

    case 0x02:
      Serial.println("Restarting ESP2");
      ESP.restart();
      break;

    default:
      break;
    }
  }
}

void publishChunk(const char *topic, int16_t *data, int startIdx, int len)
{
  StaticJsonDocument<3072> doc;
  char buffer[3072];

  doc["s"] = startIdx;
  doc["c"] = len;

  JsonArray arr = doc["d"].to<JsonArray>();

  for (int i = 0; i < len; i++)
  {
    arr.add(data[startIdx + i]);
  }

  size_t n = serializeJson(doc, buffer);

  client.publish(topic, buffer, n);
  vTaskDelay(2);
}