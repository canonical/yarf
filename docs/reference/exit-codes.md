# Exit codes

YARF inherits some of the [exit codes from Robot Framework][rf-exit-codes]. In this document, the meaning of different error codes are listed.

| Exit Code | Description                      |
| --------- | -------------------------------- |
| 0         | All test passed.                 |
| 1 - 249   | Number of failed tests or tasks. |
| 250       | 250 or more failures.            |
| 252       | Invalid test data.               |

[rf-exit-codes]: https://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#return-codes
