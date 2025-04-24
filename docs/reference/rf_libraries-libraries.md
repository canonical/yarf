# Robot libraries

## Built-in Libraries

Robot Framework provides a set of standard libraries that can be used for general purpose activities, like conditionals or iterations. A detailed list and description can be found in the [official documentation](https://robotframework.org/robotframework/#standard-libraries).

## Third Party Libraries

A small set of third party libraries is included in YARF to cover common test scenarios:

- [SSH Library](https://marketsquare.github.io/SSHLibrary/SSHLibrary.html) to connect and run commands via SSH on a Device Under Test
- [RPA Framework](https://rpaframework.org/) for template matching and much more

## Custom Libraries

YARF extends Robot Framework with custom Python libraries:

```{toctree}
---
glob:
maxdepth: 1
---
rf_libraries/library-*
rf_libraries/interactive_console-*
```
