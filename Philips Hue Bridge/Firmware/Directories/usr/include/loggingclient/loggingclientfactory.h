/******************************************************************************/
/*                                                                            */
/*  Description:: Logging Client Factory                                      */
/*                                                                            */
/*                Signify Company Confidential.                               */
/*                Copyright (C) 2025 Signify Holding                          */
/*                All rights reserved.                                        */
/*                                                                            */
/******************************************************************************/

#pragma once

#include <memory>
#include "loggingclientinterface.h"

/**
 * \defgroup LoggingClientLibrary Logging Client Library Factory
 *
 * # LoggingClientFactory
 *
 * LoggingClientFactory is the main entry point for the logging client.
 * It allows creating of the logging client.
 *
 * @{
 */
namespace LoggingClientLibrary {

class LoggingClientFactory {
   public:
    /**
     * Create a logging client.
     * @param address The address of the logging server [deprecated].
     * @param component The component name.
     * @param port The port of the logging server [deprecated].
     * @return A pointer to the logging client.
     */
    static LoggingClientInterface* Create(const std::string& address, const std::string& component, int port = 1883);
};

}  // namespace LoggingClientLibrary

/**
 * @}
 */
