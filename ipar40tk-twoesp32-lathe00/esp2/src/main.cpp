/* 
  ESP2 connected to accelerometer, gyroscope and magnetometer (MPU9250 IMU)

  For utilising the two processor cores, both are running multiple tasks:
    - Core 0: handling the display and the menu system, checking ESP1's health
    - Core 1: handling the sensor data and the communication with ESP2

*/

#include <Arduino.h>
#include "mpu9250.h"
#include "EspMQTTClient.h"
#include <Wire.h>
#include "credentials.h"
#include <ArduinoJson.hpp>
#include <ArduinoJson.h>

// MQTT topics for vibration data
#define VIBX_TOPIC "factory/lathe00/vibration/mpu9250/vibX"
#define VIBY_TOPIC "factory/lathe00/vibration/mpu9250/vibY"
#define VIBZ_TOPIC "factory/lathe00/vibration/mpu9250/vibZ"

// ESP2 Status report
#define STATUS_TOPIC "factory/lathe00/status/esp2"
unsigned long lastEsp1Response = 0;
bool esp1Online = false;

// MPU9250 I2C address and registers
#define CHUNK_SIZE 128
#define DRDY_PIN 27
#define MPU_ADDR 0x68
#define WHOAMI_REG 0x75

// Create MPU9250 instance, Serial for inter-ESP communication, and mutexes
bfs::Mpu9250 imu;
HardwareSerial SerialInterconn(2);
SemaphoreHandle_t mqttMutex;
SemaphoreHandle_t i2cMutex;

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

// Error flag bits
#define FLAG_ONLINE 0x01
#define FLAG_MQTT 0x02
#define FLAG_MPU 0x04
#define FLAG_TEMP 0x08
#define FLAG_CURRENT 0x10
#define FLAG_RPM 0x20
#define FLAG_COLLECT 0x40

// Command codes for serial communication
#define CMD_TOGGLE 0x01
#define CMD_RESTART 0x02

// Create MQTT client instance
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
// Function declarations
void collectData();
void sendJsonMessage();
void sendChunkedData();
void publishChunk(const char *topic, int16_t *data, int startIdx, int len);
void checkSystemHealth();
void checkSerialMessage();
uint8_t calcChecksum(Esp2Status &msg);
void sendStatus();
void SendMqttMessage(void *pv);
void CollectVibration(void *pv);
void SerialMessageHandler(void *pv);
void SendSensorStatus(void *pv);

// Calculate checksum for the status message
uint8_t calcChecksum(Esp2Status &msg)
{
  uint8_t *ptr = (uint8_t *)&msg;
  uint8_t sum = 0;

  for (int i = 0; i < sizeof(Esp2Status) - 1; i++)
    sum ^= ptr[i];

  return sum;
}
// Send status message to ESP1
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

// Clear any existing data in the serial buffer to avoid processing stale messages
void clearSerialInterconn()
{
  int x;
  while ((x = SerialInterconn.available()) > 0)
  {
    while (x--)
      SerialInterconn.read();
  }
}

// Interrupt Service Routine for MPU9250 Data Ready signal
void IRAM_ATTR onDataReady()
{
  READ = true;
  intCounter++;
}

// Setup function to initialize peripherals
void setup()
{
  setCpuFrequencyMhz(240);
  Serial.begin(115200);

  Wire.begin();
  Wire.setClock(400000);

  // Configure MPU9250 with I2C address and settings
  imu.Config(&Wire, bfs::Mpu9250::I2C_ADDR_PRIM);
  imu.ConfigSrd(0);
  imu.ConfigAccelRange(bfs::Mpu9250::ACCEL_RANGE_4G);

  client.enableDebuggingMessages();
  client.setKeepAlive(10);
  client.setMaxPacketSize(4096);
  client.setMqttReconnectionAttemptDelay(10000);
  client.setWifiReconnectionAttemptDelay(10000);


  // Interrupt
  pinMode(DRDY_PIN, INPUT_PULLUP);
  attachInterrupt(DRDY_PIN, onDataReady, RISING);

  // Starting serial connection between ESPs
  SerialInterconn.begin(115200, SERIAL_8N1, 16, 17);
  clearSerialInterconn();
  imu.EnableDrdyInt();
  Serial.println("IMU ready");

  // Create mutexes for MQTT and I2C access
  mqttMutex = xSemaphoreCreateMutex();
  i2cMutex = xSemaphoreCreateMutex();

  // Create a task that will be executed in the SendMqttMessage() function, with priority 2 and executed on core 1
  xTaskCreatePinnedToCore(
      SendMqttMessage, /* task function. */
      "SendMqttMessage", /* name of task. */
      8192, /* stack size of task */
      NULL, /* parameter of the task */
      2, /* priority of the task */
      NULL, /* task handle to keep track of created task */
      1); /* pin task to core 1 */

  // Create a task that will be executed in the CollectVibration() function, with priority 3 and executed on core 1
  xTaskCreatePinnedToCore(
      CollectVibration, /* task function. */
      "CollectVibration", /* name of task. */
      4096, /* stack size of task */
      NULL, /* parameter of the task */
      3, /* priority of the task */
      NULL, /* task handle to keep track of created task */
      1); /* pin task to core 1 */

  // Create a task that will be executed in the SerialMessageHandler() function, with priority 1 and executed on core 0
  xTaskCreatePinnedToCore(
      SerialMessageHandler, /* task function. */
      "SerialMessageHandler", /* name of task. */
      4096, /* stack size of task */
      NULL, /* parameter of the task */
      1, /* priority of the task */
      NULL, /* task handle to keep track of created task */
      0); /* pin task to core 0 */

  // Create a task that will be executed in the SendSensorStatus() function, with priority 1 and executed on core 0
  xTaskCreatePinnedToCore(
      SendSensorStatus, /* task function. */
      "SendSensorStatus", /* name of task. */
      4096, /* stack size of task */
      NULL, /* parameter of the task */
      1, /* priority of the task */
      NULL, /* task handle to keep track of created task */
      0); /* pin task to core 0 */
}

void loop()
{
  vTaskDelay(portMAX_DELAY);
}

void onConnectionEstablished()
{
  Serial.println("Connected to broker.");
}

// Function to collect data from MPU9250 when Data Ready signal is triggered
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
    // Semaphore 
    xSemaphoreGive(i2cMutex);
  }

  // If we've collected enough samples, disable the Data Ready interrupt and set the flag to send data
  if (idx >= sampleSize)
  {
    imu.DisableDrdyInt();
    DATA_READY = true;
  }
}

// Function to send collected data as JSON messages to MQTT broker in chunks
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

// Function to send collected data in chunks to avoid MQTT message size limits
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

// Function to check the health of the system by verifying MQTT connection and MPU9250 status
void checkSystemHealth()
{
  prevClientOk = clientOk;
  prevMpuOk = mpuOk;

  // Checking client state
  clientOk = client.isConnected();

  // Checking MPU state via WHOAMI register
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

  // If there was a change, update the state of the system
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

// Function to check for incoming serial messages from ESP1 and execute commands
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

// Function to publish a chunk of data to a specific MQTT topic as a JSON message
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

// Function to publish the system status to a specific MQTT topic as a JSON message
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

// Task function to continuously check MQTT connection and send collected data when ready
void SendMqttMessage(void *pv)
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

// Task function to continuously check for new vibration data and collect it when ready
void CollectVibration(void *pv)
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

// Task function to continuously check for incoming serial messages from ESP1 and execute commands
void SerialMessageHandler(void *pv)
{
  for (;;)
  {
    checkSerialMessage();

    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

// Task function to continuously check the health of the system and publish status updates to MQTT broker
void SendSensorStatus(void *pv)
{
  for (;;)
  {
    checkSystemHealth();
    publishSystemStatus();
    sendStatus();

    vTaskDelay(pdMS_TO_TICKS(10000));
  }
}