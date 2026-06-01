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

TaskHandle_t ButtonHandler;
TaskHandle_t ReadandSendSensorDataHandler;
// Mutex for handling button presses
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
// Function ButtonHandler - handling button events and menu state | selfchecking ESP1's health
//----------------------------------------------
void ButtonEvent(void *pvParameters)
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
// Function ReadandSendSensorData - reading sensor data and sending it out | checking serial  messages from ESP2
//------------------------------------------------------------
void ReadandSendSensorData(void *pvParameters)
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

    if (checkSendMeasurements()) // check if the flag is set to send measurements (set in the menu when entering the home tab)
    {
      resetSendMeasurements(); // reseting the flag
      sendCurrent(); // sending the current measurement
      getRpm(); // send the rpm measurement
      getTempC(); // send the temperature measurement
    }
    // send measurements every 1.3 seconds if collection is enabled
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
  // send a ping to ESP2 every 5 seconds to check if it's online
  if (millis() - lastPing > 5000)
  {
    sendCommand(0x00); // ping
    lastPing = millis();
  }
}
//------------------------------------------------------------
// Function DisplayTask - handling the display content
//------------------------------------------------------------
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
//------------------------------------------------------------
// Function StatusTask - handling the status updates
//------------------------------------------------------------
void StatusTask(void *pv)
{
  for (;;)
  {
    sendCommand(0x00); // heartbeat
    publishEsp1Status();
    vTaskDelay(pdMS_TO_TICKS(20000));
  }
}

// Setup
void setup()
{
  setCpuFrequencyMhz(240);

  Serial.begin(115200);
  // Create a queue for display messages
  displayQueue = xQueueCreate(1, sizeof(DisplayMessage));
  // Setting up the buttons with pullup/pulldown resistors
  pinMode(NEXT_PIN, INPUT_PULLUP);
  pinMode(ENTER_PIN, INPUT_PULLUP);
  pinMode(DRDY_PIN, INPUT_PULLDOWN);
  // Setting up the buttons with interrupts
  attachInterrupt(NEXT_PIN, nextOnPress, FALLING);
  attachInterrupt(ENTER_PIN, enterOnPress, FALLING);

  // Setting up the connectivity and sensors
  initCom();
  setupSensors();

  // Setting up the display
  setupDisplay();

  // Create a task that will be executed in the DisplayTask() function, with priority 1 and executed on core 0
  xTaskCreatePinnedToCore(
      DisplayTask, /* task function. */
      "DisplayTask", /* name of task. */
      4096, /* stack size of task */
      NULL, /* parameter of the task */
      1, /* priority of the task */
      NULL, /* task handle to keep track of created task */
      0); /* pin task to core 0 */

  vTaskDelay(pdMS_TO_TICKS(50));
  // Initializing the menu system
  menuInit();

  // Create a task that will be executed in the ButtonHandler() function, with priority 1 and executed on core 0
  xTaskCreatePinnedToCore(
      ButtonEvent, /* task function. */
      "ButtonHandler",   /* name of task. */
      10000,     /* stack size of task */
      NULL,      /* parameter of the task */
      1,         /* priority of the task */
      &ButtonHandler,    /* task handle to keep track of created task */
      0);        /* pin task to core 0 */
  delay(500);

  // Create a task that will be executed in the ReadandSendSensorData() function, with priority 2 and executed on core 1
  xTaskCreatePinnedToCore(
      ReadandSendSensorData, /* task function. */
      "ReadandSendSensorDataHandler",   /* name of task. */
      15000,     /* stack size of task */
      NULL,      /* parameter of the task */
      2,         /* priority of the task */
      &ReadandSendSensorDataHandler,    /* task handle to keep track of created task */
      1);        /* pin task to core 1 */
  delay(500);

  // Create a task that will be executed in the StatusTask() function, with priority 1 and executed on core 0
  xTaskCreatePinnedToCore(
      StatusTask, /* task function. */
      "StatusTask", /* name of task. */
      4096, /* stack size of task */
      NULL, /* parameter of the task */
      1, /* priority of the task */
      NULL, /* task handle to keep track of created task */
      0); /* pin task to core 0 */
}

void loop()
{
  // put your main code here, to run repeatedly:
}