#ifndef MEASUREMENT_H
#define MEASUREMENT_H

enum RpmStatus
{
    RPM_OK,
    RPM_NO_ROTATION,
    RPM_SENSOR_FAULT
};

enum CurrentStatus {
    CURRENT_OK,
    CURRENT_NO_LOAD,
    CURRENT_SENSOR_FAULT
};

void setupSensors();
void getCurrent();
void sendCurrent();
void setRPMTime();
void getRpm();
void getTempC();
bool checkTempSensor();
RpmStatus checkRpmSensor();
CurrentStatus checkCurrentSensor();
const char* rpmStatusToString(RpmStatus status);
const char* currentStatusToString(CurrentStatus status);

#endif