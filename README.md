# Yet Another Robot Framework (YARF)
YARF is a tool built upon the [Robot Framework](https://robotframework.org/) 
that allows developers to build complex visual test scenarios and bootstrap them 
locally, and then work towards automated runs in continuous integration (CI) and
use of platforms/fixtures like [Example](https://github.com/canonical/Example) 
with minimal effort. This reduces turnaround times without sacrificing quality 
and trust in the test results.


## Table of Contents
* [Installation Guide](#installation-guide)
* [Running YARF](#running-yarf)
* [Testing](#testing)


<a name="installation-guide"></a>
## Installation Guide
### Requirements
This repository requires the following dependencies
* [Python 3.10](https://www.python.org/downloads/release/python-31014/)
    - [tox](https://tox.wiki/en/latest/installation.html)
    - [virtualenv](https://virtualenv.pypa.io/en/latest/installation.html)
* [Snapcraft](https://snapcraft.io/docs/installing-snapcraft)


### Installing for contribution
1.  **Create a Python virtual environment**

    To contribute to the repository, we first create a Python virtual environment.
    To create a virtual environment we need to install the `virtualenv` package:
    ```
    python3 -m pip install virtualenv
    ```
    
    Then we create a virtual environment:
    ```
    python3 -m virtualenv venv
    ```
    
    After that, we enter the virtual environment:
    ```
    . venv/bin/activate
    ```

2.  **Installing YARF with dependencies**

    We can install YARF along with the dependencies specified in 
    `pyproject.toml` in the virtual environment using the command:
    ```
    python3 -m pip install -e .
    ```
    We can start working on the repository here.

3.  **Leaving the virtual environment**

    When we finish working with the repository and leaving the virtual environment,
    we can execute:
    ```
    deactivate
    ```

### Installing as a Snap package
1.  **Make a Snap package**

    YARF can also be delivered using Snap, to create a Snap package:
    ```
    snapcraft
    ```

2.  **Install the Snap package**

    Then we should see a `yarf_<version>_<architeccture>.snap` under 
    the repository folder. To install it use the command:
    ```
    sudo snap install yarf_{version}_{architecture}.snap --dangerous
    ```

<a name="running-yarf"></a>
## Running YARF
Please run `yarf --help` to learn more about the usage.

<a name="testing"></a>
## Testing

[tox](https://tox.wiki/) is used to automate quality control tasks in YARF, 
including:
* Linting ([ruff](https://docs.astral.sh/ruff/))
* Formatting ([black](https://black.readthedocs.io/en/stable/))
* Unit test with coverage ([pytest](https://docs.pytest.org/en/stable/))

To run the above quality control tasks, simply execute the command under 
the repository folder:
```
tox
```
