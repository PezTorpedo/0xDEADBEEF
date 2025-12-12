/******************************************************************************/
/*                                                                            */
/*  Description:: Logging Client Interface                                    */
/*                                                                            */
/*                Signify Company Confidential.                               */
/*                Copyright (C) 2025 Signify Holding                          */
/*                All rights reserved.                                        */
/*                                                                            */
/******************************************************************************/

#pragma once

#include <rapidjson/document.h>
#include <string>
#include <tao/json.hpp>
#include "logeventresponseinterface.h"

/**
 * \defgroup LoggingClientInterface Logging Client interface
 * \ingroup LoggingClient
 *
 * @{
 */

namespace LoggingClientLibrary {

class LoggingClientInterface {
   public:
    /**
     * Send log event
     *
     * @param category              report category of log event
     * @param type                  report type of log event
     * @param sub_type              report sub-type of log event
     * @param event_data            event data
     * @param log_event_response    class instance implementing response interface
     * @param prio                  priority of the log message
     * @param block_for_ms          time to block for if the queue is full
     *                              0 means do not block
     *                              any other value is the time in milliseconds to block
     *                              return true if the log event was successfully sent, false otherwise
     */
    virtual bool Log(const std::string& category, const std::string& type, const std::string& sub_type,
                     const tao::json::value& event_data, LogEventResponseInterface* log_event_response, int prio = 0,
                     int block_for_ms = 0) = 0;

    /**
     * Send log event
     *
     * @param category              report category of log event
     * @param type                  report type of log event
     * @param sub_type              report sub-type of log event
     * @param event_data            event data
     * @param log_event_response    class instance implementing response interface
     * @param prio                  priority of the log message
     * @param block_for_ms          time to block for if the queue is full
     *                              0 means do not block
     *                              any other value is the time in milliseconds to block
     *                              return true if the log event was successfully sent, false otherwise
     */
    virtual bool Log(const std::string& category, const std::string& type, const std::string& sub_type,
                     const rapidjson::Value& event_data, LogEventResponseInterface* log_event_response, int prio = 0,
                     int block_for_ms = 0) = 0;

    virtual ~LoggingClientInterface() = default;
};

}  // namespace LoggingClientLibrary

/**
 * @}
 */
