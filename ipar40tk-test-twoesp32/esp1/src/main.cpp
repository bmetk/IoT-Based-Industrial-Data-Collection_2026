/*

  This version runs 3 sensors, a display and navigation buttons

  The sensors are:
    - optocouler
    - temperature sensor
    - current meter

  The current diplay is a 0.92" 128x64 oled display.

  The two navigation buttons are:
    - Next: going to the next possinle state
    - Select: entering a new state/calling a function

  To utilise the two cores, both are running a task:
    - Task 1: display, mqtt etc.
    - Task 2: data collection

*/

#include <Arduino.h>
#include <menu.h>
#include <measurement.h>
#include <connectivity.h>
#include <parameters.h>
#include <display.h>

////////////////////////////////////////////////////////////////////////////////////////
//
//    Constants / Definitions
//
////////////////////////////////////////////////////////////////////////////////////////

TaskHandle_t Task1;
TaskHandle_t Task2;
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

volatile bool nextPressed = false;
volatile bool enterPressed = false;
unsigned long buttonTime = 0;
unsigned long lastButtonTime = 0;
const int debounceInteval = 250;
unsigned long previousMillis;
const unsigned int measurementInterval = 1300;

// Queue for display messages
QueueHandle_t displayQueue;

////////////////////////////////////////////////////////////////////////////////////////
//
//    Function definitions
//
////////////////////////////////////////////////////////////////////////////////////////

//-----------------------
// Checking ESP1's health
//-----------------------
bool prevClientCon = false, prevTemp = false;
bool clientCon = false, temp = false;

void checkEsp1Health()
{
  clientCon = checkClientCon();
  temp = checkTempSensor();

  if (clientCon)
  {
    setErrorEnable(0, 0);
  }
  else
  {
    setErrorEnable(0, 1);
  }
  if (temp)
  {
    setErrorEnable(3, 0);
  }
  else
  {
    setErrorEnable(3, 1);
  }
  static unsigned long lastUpdate = 0;

  if ((prevClientCon != clientCon || prevTemp != temp) &&
      millis() - lastUpdate > 500)
  {
    lastUpdate = millis();
  }
}

//------------------------
// Handling button presses
//------------------------
volatile uint32_t lastInterruptTimeNext = 0;

void IRAM_ATTR nextOnPress()
{
  uint32_t now = millis();

  if (now - lastInterruptTimeNext > pdMS_TO_TICKS(120))
  {
    portENTER_CRITICAL_ISR(&mux);
    nextPressed = true;
    portEXIT_CRITICAL_ISR(&mux);

    lastInterruptTimeNext = now;
  }
}

volatile uint32_t lastInterruptTimeEnter = 0;

void IRAM_ATTR enterOnPress()
{
  uint32_t now = millis();

  if (now - lastInterruptTimeEnter > pdMS_TO_TICKS(120))
  {
    portENTER_CRITICAL_ISR(&mux);
    enterPressed = true;
    portEXIT_CRITICAL_ISR(&mux);

    lastInterruptTimeEnter = now;
  }
}

//----------------------------------------------
// Function for Task1 - handling the menu system
//----------------------------------------------
void Task1code(void *pvParameters)
{
  for (;;)
  {
    bool localNext = false;
    bool localEnter = false;

    portENTER_CRITICAL(&mux);
    localNext = nextPressed;
    nextPressed = false;
    localEnter = enterPressed;
    enterPressed = false;
    portEXIT_CRITICAL(&mux);

    if (localNext)
    {
      handleMenuEvent(EVENT_NEXT);
    }
    else if (localEnter)
    {
      handleMenuEvent(EVENT_ENTER);
    }

    menuLoop();

    checkEsp1Health();

    vTaskDelay(pdMS_TO_TICKS(20));
  }
}

//------------------------------------------------------------
// Function for Task2 - reading sensor data and sending it out
//------------------------------------------------------------
void Task2code(void *pvParameters)
{
  previousMillis = millis();
  clearSerialInterconn();
  delay(200);
  setRPMTime();
  Esp2Status incomingData;
  for (;;)
  {
    clientLoop();
    if (readStatus(&incomingData))
    {
      updateEsp2(incomingData);
      setErrorEnable(4, 0);
      setErrorEnable(5, (incomingData.flags & FLAG_MPU) ? 0 : 1);
    }
    else
    {
      checkEsp2Timeout();
      if (!esp2.online)
      {
        setErrorEnable(4, 1); // Ha timeout volt, jelezzük a hibát!
        setErrorEnable(5, 1); // Mivel nincs adat, az ACCEL is hiba
      }
    }

    if (checkSendMeasurements())
    {                          // check if acceleration data is ready
      resetSendMeasurements(); // reseting the flag
      sendCurrent();
      getRpm();
      getTempC();
      // sendCommand(0x01);
    }
    // check if acceleration data is ready
    if (millis() - previousMillis > measurementInterval && isCollectionEnabled())
    {
      sendCurrent();
      getRpm();
      getTempC();

      previousMillis = millis();
    }
    vTaskDelay(10);
  }
  static unsigned long lastPing = 0;

  if (millis() - lastPing > 5000)
  {
    sendCommand(0x00); // ping
    lastPing = millis();
  }
}

void DisplayTask(void *pvParameters)
{
  DisplayMessage msg;

  for (;;)
  {
    if (xQueueReceive(displayQueue, &msg, portMAX_DELAY))
    {
      oled.clearDisplay();

      switch (msg.state)
      {
      case DISPLAY_HOME:
        homeTab();
        break;

      case DISPLAY_ERROR:
        errorTab();
        break;

      case DISPLAY_SETTINGS:
        settingsTab();
        break;

      case DISPLAY_MESSAGE:
        oled.setCursor(10, 30);
        oled.print(msg.msg);
        break;
      }

      oled.display();
    }
  }
}

void statusTask(void *pv)
{
  for (;;)
  {
    sendCommand(0x00); // heartbeat
    publishEsp1Status();
    vTaskDelay(pdMS_TO_TICKS(20000));
  }
}

//    Setup
void setup()
{
  setCpuFrequencyMhz(240);

  Serial.begin(115200);
  // Create a queue for display messages
  displayQueue = xQueueCreate(1, sizeof(DisplayMessage));

  pinMode(NEXT_PIN, INPUT_PULLUP);
  pinMode(ENTER_PIN, INPUT_PULLUP);
  pinMode(DRDY_PIN, INPUT_PULLDOWN);

  attachInterrupt(NEXT_PIN, nextOnPress, FALLING);
  attachInterrupt(ENTER_PIN, enterOnPress, FALLING);

  // starting up the sensors and the wireless connection
  initCom();
  setupSensors();

  // setting up the display
  setupDisplay();

  xTaskCreatePinnedToCore(
      DisplayTask,
      "DisplayTask",
      4096,
      NULL,
      1,
      NULL,
      0);

  vTaskDelay(pdMS_TO_TICKS(50));
  menuInit();

  // create a task that will be executed in the Task1code() function, with priority 1 and executed on core 0
  xTaskCreatePinnedToCore(
      Task1code, /* Task function. */
      "Task1",   /* name of task. */
      10000,     /* Stack size of task */
      NULL,      /* parameter of the task */
      1,         /* priority of the task */
      &Task1,    /* Task handle to keep track of created task */
      0);        /* pin task to core 0 */
  delay(500);

  // create a task that will be executed in the Task2code() function, with priority 1 and executed on core 1
  xTaskCreatePinnedToCore(
      Task2code, /* Task function. */
      "Task2",   /* name of task. */
      15000,     /* Stack size of task */
      NULL,      /* parameter of the task */
      2,         /* priority of the task */
      &Task2,    /* Task handle to keep track of created task */
      1);        /* pin task to core 1 */
  delay(500);

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
  // put your main code here, to run repeatedly:
}