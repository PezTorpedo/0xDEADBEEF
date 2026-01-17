/******************************************************************************/
/*                                                                            */
/*  Description:: Logging Client                                              */
/*                                                                            */
/*                Signify Company Confidential.                               */
/*                Copyright (C) 2025 Signify Holding                          */
/*                All rights reserved.                                        */
/*                                                                            */
/******************************************************************************/

#pragma once

#include <gmock/gmock.h>
#include "logeventresponseinterface.h"

namespace LoggingClientLibrary {

class MockLogEventResponse : public LogEventResponseInterface {
   public:
    MOCK_METHOD(void, LogEventResponse, (), (override));
};
}  // namespace LoggingClientLibrary
