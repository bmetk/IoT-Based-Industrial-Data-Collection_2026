#ifndef DISPLAY_H
#define DISPLAY_H

// Display settings enum
typedef enum
{
  DISPLAY_HOME,
  DISPLAY_ERROR,
  DISPLAY_SETTINGS,
  DISPLAY_MESSAGE
} DisplayState;

// Struct for passing messages to the display task
typedef struct
{
  DisplayState state;
  char msg[32];
} DisplayMessage;

#endif