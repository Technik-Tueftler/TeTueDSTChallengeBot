watcher
==========================

.. automodule:: src.tetue_generic.watcher
    :members:
    :exclude-members: WatcherConfiguration


Initialization function
=======================
The initialization process is performed by the :func:`src.tetue_generic.watcher.init` function. This function performs the following tasks:

Procedure for the initialization process
----------------------------------------

   1. Removes existing loggers
   2. Adds a method for the new log level
   3. Configures file output with rotation
   4. Configures console output with color

Log levels
----------
The following log levels are available:

   * TRACE
   * DEBUG
   * INFO
   * SUCCESS
   * WARNING
   * ERROR
   * CRITICAL
