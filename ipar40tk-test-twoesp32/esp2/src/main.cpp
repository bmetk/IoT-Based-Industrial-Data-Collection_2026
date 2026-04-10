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

// ESP2 Status report
#define STATUS_TOPIC "factory/lathe01/status/esp2"
unsigned long lastEsp1Response = 0;
bool esp1Online = false;

#define CHUNK_SIZE 128
#define DRDY_PIN 27
#define MPU_ADDR 0x68
#define WHOAMI_REG 0x75

bfs::Mpu9250 imu;
HardwareSerial SerialInterconn(2);
SemaphoreHandle_t mqttMutex;
SemaphoreHandle_t i2cMutex;

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

#define FLAG_ONLINE 0x01
#define FLAG_MQTT 0x02
#define FLAG_MPU 0x04
#define FLAG_TEMP 0x08
#define FLAG_CURRENT 0x10
#define FLAG_RPM 0x20
#define FLAG_COLLECT 0x40

#define CMD_TOGGLE 0x01
#define CMD_RESTART 0x02

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
volatile bool DATA_READY = false;
volatile bool READ = false;
volatile int intCounter = 0;
bool enableCollection = true;
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
uint8_t calcChecksum(Esp2Status &msg);
void sendStatus();
void mqttTask(void *pv);
void sensorTask(void *pv);
void serialTask(void *pv);
void statusTask(void *pv);

uint8_t calcChecksum(Esp2Status &msg)
{
  uint8_t *ptr = (uint8_t *)&msg;
  uint8_t sum = 0;

  for (int i = 0; i < sizeof(Esp2Status) - 1; i++)
    sum ^= ptr[i];

  return sum;
}

void sendStatus()
{
  Esp2Status msg;

  msg.header = 0xAA;
  msg.version = 1;

  msg.flags = 0;
  if (true)
    msg.flags |= FLAG_ONLINE;
  if (clientOk)
    msg.flags |= FLAG_MQTT;
  if (mpuOk)
    msg.flags |= FLAG_MPU;
  if (true)
    msg.flags |= FLAG_TEMP;
  if (true)
    msg.flags |= FLAG_CURRENT;
  if (true)
    msg.flags |= FLAG_RPM;
  if (enableCollection)
    msg.flags |= FLAG_COLLECT;

  msg.uptime = millis();

  msg.checksum = calcChecksum(msg);

  SerialInterconn.write((uint8_t *)&msg, sizeof(msg));
  SerialInterconn.flush();
}

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

  // starting serial connection between ESPs
  SerialInterconn.begin(115200, SERIAL_8N1, 16, 17);
  clearSerialInterconn();
  imu.EnableDrdyInt();
  Serial.println("IMU ready");

  mqttMutex = xSemaphoreCreateMutex();
  i2cMutex = xSemaphoreCreateMutex();

  xTaskCreatePinnedToCore(
      mqttTask,
      "mqttTask",
      8192,
      NULL,
      2,
      NULL,
      1);

  xTaskCreatePinnedToCore(
      sensorTask,
      "sensorTask",
      4096,
      NULL,
      3,
      NULL,
      1);

  xTaskCreatePinnedToCore(
      serialTask,
      "serialTask",
      4096,
      NULL,
      1,
      NULL,
      0);

  xTaskCreatePinnedToCore(
      statusTask,
      "statusTask",
      4096,
      NULL,
      1,
      NULL,
      0);
}

void loop()
{
  vTaskDelay(portMAX_DELAY);
}

void onConnectionEstablished()
{
  Serial.println("Connected to broker.");
}

void collectData()
{
  if (xSemaphoreTake(i2cMutex, pdMS_TO_TICKS(10)))
  {
    if (imu.Read())
    {
      vRealX[idx] = (int16_t)(imu.accel_x_mps2() * 500);
      vRealY[idx] = (int16_t)(imu.accel_y_mps2() * 500);
      vRealZ[idx] = (int16_t)((imu.accel_z_mps2() + G_MPS2) * 500);

      idx++;
      READ = false;
    }
    xSemaphoreGive(i2cMutex);
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
  if (!DATA_READY)
    return;

  imu.DisableDrdyInt();

  DATA_READY = false;

  sendChunkedData();

  idx = 0;
  intCounter = 0;
  READ = false;

  imu.EnableDrdyInt();
}

void sendChunkedData()
{
  const int chunkSize = 128;

  for (int i = 0; i < sampleSize; i += chunkSize)
  {
    int len = min(chunkSize, sampleSize - i);

    publishChunk(VIBX_TOPIC, vRealX, i, len);

    publishChunk(VIBY_TOPIC, vRealY, i, len);

    publishChunk(VIBZ_TOPIC, vRealZ, i, len);
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

  if (millis() - lastEsp1Response > 30000)
  {
    esp1Online = false;
  }
}

//----------------------------------
// Execute instructions sent by ESP1
//----------------------------------
void handleCommand(uint8_t cmd)
{
  lastEsp1Response = millis();
  esp1Online = true;
  switch (cmd)
  {
  case 0x00:
    // HeartBeat
    break;
  case 0x01:
    Serial.println("Toggle collection");
    enableCollection = !enableCollection;
    break;

  case CMD_RESTART:
    Serial.println("Restarting ESP2");
    ESP.restart();
    break;
  }
}

void checkSerialMessage()
{
  static uint8_t state = 0;
  static uint8_t cmd;
  static uint8_t crc;

  while (SerialInterconn.available())
  {
    uint8_t b = SerialInterconn.read();

    switch (state)
    {
    case 0: // HEADER
      if (b == 0xAA)
        state = 1;
      break;

    case 1: // CMD
      cmd = b;
      state = 2;
      break;

    case 2: // CRC
      crc = b;

      if ((cmd ^ 0xAA) == crc) // CRC check
      {
        handleCommand(cmd);
      }

      state = 0;
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
  if (xSemaphoreTake(mqttMutex, pdMS_TO_TICKS(10)))
  {
    Serial.println("Publishing...");
    client.publish(topic, buffer, n);
    xSemaphoreGive(mqttMutex);
  }
  else
  {
    Serial.println("MQTT mutex FAIL");
  }
  vTaskDelay(pdMS_TO_TICKS(10));
}

void publishSystemStatus()
{
  StaticJsonDocument<256> doc;

  doc["esp2"] = true;
  doc["mqtt"] = clientOk;
  doc["mpu"] = mpuOk;
  doc["esp1"] = esp1Online;

  char buffer[256];
  size_t n = serializeJson(doc, buffer);

  if (xSemaphoreTake(mqttMutex, pdMS_TO_TICKS(10)))
  {
    client.publish(STATUS_TOPIC, buffer, n);
    xSemaphoreGive(mqttMutex);
  }
}

void mqttTask(void *pv)
{
  for (;;)
  {
    client.loop();

    if (enableCollection && client.isConnected())
    {
      sendJsonMessage();
    }

    vTaskDelay(pdMS_TO_TICKS(5));
  }
}

void sensorTask(void *pv)
{
  for (;;)
  {
    if (READ)
    {
      collectData();
    }

    vTaskDelay(1);
  }
}

void serialTask(void *pv)
{
  for (;;)
  {
    checkSerialMessage();

    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

void statusTask(void *pv)
{
  for (;;)
  {
    checkSystemHealth();
    publishSystemStatus();
    sendStatus();

    vTaskDelay(pdMS_TO_TICKS(10000));
  }
}