#include <Arduino.h>
#include <cmath>
#include <Adafruit_MLX90614.h>
#include <connectivity.h>
#include <measurement.h>

#define TEMP_TOPIC "factory/lathe01/temperature/mlx90614/tempC"
#define RPM_TOPIC "factory/lathe01/speed/m0c70t3/rpm"
#define AMP_TOPIC "factory/lathe01/current/zmct103c/amp"

// Optocoupler
#define OPTO_PIN 36
#define HOLE_COUNT 6 // number of holes on the disk
// Current meter
#define PHASE1_PIN 32
#define PHASE2_PIN 33
#define PHASE3_PIN 35
#define OFFSET_PIN 34

Adafruit_MLX90614 mlx = Adafruit_MLX90614();
bool mlxOk = false;

unsigned long currentTime = 0;
unsigned long previousTime = 0;

hw_timer_t *timer = NULL;

// measurement variables
const double resistor = 150.0; // 150 Ohm resistor connected to each coil
float rpm = 0;
volatile int holes;

void getCurrent();
unsigned long lastHoleTime = 0;
const unsigned long RPM_TIMEOUT = 2000;
// interrupt routine for rpm measurement
void IRAM_ATTR countHoles()
{
    holes++;
    lastHoleTime = millis();
}
void IRAM_ATTR onTimer()
{
    getCurrent();
}

const char* rpmStatusToString(RpmStatus status)
{
    switch (status)
    {
        case RPM_OK: return "ok";
        case RPM_NO_ROTATION: return "no_rotation";
        case RPM_SENSOR_FAULT: return "sensor_fault";
        default: return "unknown";
    }
}

const char* currentStatusToString(CurrentStatus status)
{
    switch (status)
    {
        case CURRENT_OK: return "ok";
        case CURRENT_NO_LOAD: return "no_load";
        case CURRENT_SENSOR_FAULT: return "sensor_fault";
        default: return "unknown";
    }
}

//---------------------
// Initializing sensors
//---------------------
void setupSensors()
{
    // Current meter setup
    pinMode(PHASE1_PIN, INPUT);
    pinMode(PHASE2_PIN, INPUT);
    pinMode(PHASE3_PIN, INPUT);
    pinMode(OFFSET_PIN, INPUT);

    // pinMode(21, INPUT_PULLUP);
    // pinMode(22, INPUT_PULLUP);

    // Optocoupler setup
    pinMode(OPTO_PIN, INPUT_PULLUP);
    attachInterrupt(OPTO_PIN, countHoles, FALLING);
    previousTime = millis();

    // Temperature sensor setup
    int retry = 0;
    while (retry < 10)
    {
        if (mlx.begin())
        {
            break; // Break out of the loop if initialization succeeds
        }
        retry++;
        delay(200);
    }

    // timer generating interrupts for current readings
    timer = timerBegin(0, 80, true);
    timerAttachInterrupt(timer, &onTimer, true);
    timerAlarmWrite(timer, 5000, true);
    timerAlarmEnable(timer);
}

void setRPMTime()
{
    previousTime = millis();
}

double phase1sum = 0;
double phase2sum = 0;
double phase3sum = 0;
int measurementCount = 0;

double getRMS(double squaredSum)
{
    double meanSquared = squaredSum / static_cast<double>(measurementCount);
    double rms = sqrt(meanSquared);

    return rms;
}
//----------------------------------------------------------
// Function for checking the state of the temperature sensor
//----------------------------------------------------------
bool checkTempSensor()
{
    if (mlx.readAmbientTempC() > -10000)
    {
        return true;
    }
    else
    {
        mlx.begin();
        return false;
    }
}

RpmStatus checkRpmSensor()
{
    unsigned long now = millis();

    if ((now - lastHoleTime) < RPM_TIMEOUT)
    {
        return RPM_OK;
    }

    if (getRMS(phase1sum) < 0.5) // finomhangold
    {
        return RPM_SENSOR_FAULT;
    }

    return RPM_NO_ROTATION;
}

CurrentStatus checkCurrentSensor()
{
    if (measurementCount < 10)
        return CURRENT_SENSOR_FAULT;

    double rms1 = getRMS(phase1sum);
    double rms2 = getRMS(phase2sum);
    double rms3 = getRMS(phase3sum);

    if (isnan(rms1) || isnan(rms2) || isnan(rms3))
        return CURRENT_SENSOR_FAULT;

    if (rms1 < 0.05 && rms2 < 0.05 && rms3 < 0.05)
        return CURRENT_NO_LOAD;

    return CURRENT_OK;
}

//------------------------------------------------------------------
// Measurement functions for rpm, current draw and motor temperature
//------------------------------------------------------------------
const int sampleSize = 120;
double phase1Arr[sampleSize];
double phase2Arr[sampleSize];
double phase3Arr[sampleSize];

double p1A = 0;
double p2A = 0;
double p3A = 0;

// current
double readVoltage(int pin)
{
    return ((double(analogRead(pin)) * 3.3) / 4095.0);
}

double voltsToAmps(double voltage, double offset)
{
    voltage -= offset;

    if (voltage < 0)
    {
        voltage *= -1;
    }

    return (voltage / resistor) * 1000.0;
}

/*void getCurrent(){
    double offset = readVoltage(OFFSET_PIN);
    double phase_1 = voltsToAmps(readVoltage(PHASE1_PIN), offset);
    double phase_2 = voltsToAmps(readVoltage(PHASE2_PIN), offset);
    double phase_3 = voltsToAmps(readVoltage(PHASE3_PIN), offset);

    String current = String(phase_1) + ";" + String(phase_2) + ";" + String(phase_3);
    sendMqttMessage(AMP_TOPIC, current.c_str());
}

void getCurrent() {
    if(measurementCount < sampleSize) {
        double offset = readVoltage(OFFSET_PIN);
        phase1Arr[measurementCount] = voltsToAmps(readVoltage(PHASE1_PIN), offset);
        phase2Arr[measurementCount] = voltsToAmps(readVoltage(PHASE2_PIN), offset);
        phase3Arr[measurementCount] = voltsToAmps(readVoltage(PHASE3_PIN), offset);
        measurementCount++;
    }
}*/

void getCurrent()
{
    double offset = readVoltage(OFFSET_PIN);
    p1A = voltsToAmps(readVoltage(PHASE1_PIN), offset);
    p2A = voltsToAmps(readVoltage(PHASE2_PIN), offset);
    p3A = voltsToAmps(readVoltage(PHASE3_PIN), offset);
    phase1sum += p1A * p1A;
    phase2sum += p2A * p2A;
    phase3sum += p3A * p3A;
    measurementCount++;
}


void sendCurrent()
{
    timerAlarmDisable(timer);
    char buffer[64];
    snprintf(buffer, sizeof(buffer), "[%.2f, %.2f, %.2f]", getRMS(phase1sum), getRMS(phase2sum), getRMS(phase3sum));
    // String current = "[" + String(getRMS(phase1sum)) + ", " + String(getRMS(phase2sum)) + ", " + String(getRMS(phase3sum)) + "]";
    // Serial.print("Current:   "); Serial.print(current); Serial.print("         Measurements:    "); Serial.println(measurementCount);
    sendMqttMessage(AMP_TOPIC, buffer);
    phase1sum = 0;
    phase2sum = 0;
    phase3sum = 0;
    measurementCount = 0;
    timerAlarmEnable(timer);
}

// RPM measurement
void getRpm()
{
    currentTime = millis();
    rpm = (static_cast<float>(holes) / static_cast<float>(HOLE_COUNT)) * 60.0 / ((currentTime - previousTime) / 1000.0);
    previousTime = currentTime;
    Serial.print("Interrupts:   ");
    Serial.print(holes);
    Serial.print("     RPM:   ");
    Serial.println(rpm);
    holes = 0;
    sendMqttMessage(RPM_TOPIC, String(rpm).c_str());
}

// Temperature measurement
void getTempC()
{
    mlxOk = mlx.begin();
    double tempC = mlx.readObjectTempC();
    if (!mlxOk || isnan(tempC) || tempC < -40 || tempC > 300)
    {
        sendMqttMessage(TEMP_TOPIC, "-100");
    }
    else
    {
        char buf[16];
        snprintf(buf, sizeof(buf), "%.2f", tempC);
        sendMqttMessage(TEMP_TOPIC, buf);
    }
}
