# Run a robot test suite in YARF

This guide will show how to run a robot test suite using YARF.
In general, there are three steps:
1. [Prepare the test suite](#prepare-the-test-suite)
2. [Identify the platform](#identify-the-platform)
3. [Run the `yarf` command](#run-the-yarf-command)

## Prepare the test suite

First of all, we need to prepare the test suite. In terms of YARF, a test suite is defined as a directory that at least contains a `.robot` file. For example, we have a directory named `suite`:
```
suite
└── test.robot
```
This is the simplest test suite YARF will accept. A directory without a `.robot` file will result in an error.

A more comprehensive example of a test suite would be:
```
suite
├── test.robot
├── a1.png
├── sub
│   └── a2.png
└── variants
    └── var
        ├── a1.png
        └── sub
            └── a2.png
```
The `variants` directory contains modified versions of the base templates, organized in sub-directories by specific variations; this will be discussed further in another section.

## Identify the platform

We need to identify the platform that we would like to run to use YARF. The choice is different in different case, for now we are working to support the following platforms:
- Example: A hardware test fixture enabling advanced system testing. For details please visit [here](https://canonical-Example.readthedocs-hosted.com/en/latest/)
- Mir: A display server that is suitable for local development and continuous integration. For details please visit [here](https://canonical-mir.readthedocs-hosted.com/stable/)

The support for QEMU and GNOME are on the roadmap and will be added in the future, so stay tuned :).

## Run the `yarf` command

To run a test suite named `<suite>` using a given `<platform>`, the `yarf` command would be:
```
yarf --platform <platform> <path-to-test-suite>/suite
```

If the `--platform` argument is not specified, then YARF will use Example as the platform:
```
Example_IP=<Example_IP> yarf <path-to-suite>/suite
```
