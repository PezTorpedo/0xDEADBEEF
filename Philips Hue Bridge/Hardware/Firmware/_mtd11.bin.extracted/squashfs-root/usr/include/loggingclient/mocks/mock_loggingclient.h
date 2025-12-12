/******************************************************************************/
/*                                                                            */
/*  Description:: Logging Client Mock                                         */
/*                                                                            */
/*                Signify Company Confidential.                               */
/*                Copyright (C) 2025 Signify Holding                          */
/*                All rights reserved.                                        */
/*                                                                            */
/******************************************************************************/

#pragma once

#include "loggingclientinterface.h"

#include <gmock/gmock.h>

namespace LoggingClientLibrary {

class MockLoggingClient : public LoggingClientInterface {
   public:
    MOCK_METHOD(bool, LogTao,
                (const std::string& category, const std::string& type, const std::string& sub_type,
                 const tao::json::value& event_data, LogEventResponseInterface* log_event_response));
    MOCK_METHOD(bool, LogRapid,
                (const std::string& category, const std::string& type, const std::string& sub_type,
                 const rapidjson::Value& event_data, LogEventResponseInterface* log_event_response));
    virtual bool Log(const std::string& category, const std::string& type, const std::string& sub_type,
                     const tao::json::value& event_data, LogEventResponseInterface* log_event_response, int prio = 0,
                     int block = 0) {
        return LogTao(category, type, sub_type, event_data, log_event_response);
    }

    virtual bool Log(const std::string& category, const std::string& type, const std::string& sub_type,
                     const rapidjson::Value& event_data, LogEventResponseInterface* log_event_response, int prio = 0,
                     int block = 0) {
        return LogRapid(category, type, sub_type, event_data, log_event_response);
    }
};
}  // namespace LoggingClientLibrary
