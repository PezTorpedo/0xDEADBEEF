/******************************************************************************/
/*                                                                            */
/*  Description:: Log Event Response interface                                */
/*                                                                            */
/*                Signify Company Confidential.                               */
/*                Copyright (C) 2025 Signify Holding                          */
/*                All rights reserved.                                        */
/*                                                                            */
/******************************************************************************/

#pragma once

/**
 * \defgroup LogEventResponseInterface Log event response interface
 * \ingroup CallLog
 *
 * # LogEventResponseInterface
 *
 * Interface definition for log event responses. The Log call response is empty, so no arguments included.
 */

namespace LoggingClientLibrary {

class LogEventResponseInterface {
   public:
    virtual ~LogEventResponseInterface() = default;
    virtual void LogEventResponse() = 0;
};

}  // namespace LoggingClientLibrary
