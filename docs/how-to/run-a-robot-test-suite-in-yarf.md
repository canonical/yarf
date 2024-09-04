# Run a robot test suite in YARF

This guide will show how to run a robot test suite using YARF.
In general, there are three steps:

1. [Prepare the test suite](#prepare-the-test-suite)
1. [Identify the platform](#identify-the-platform)
1. [Provide the correct variant](#provide-the-correct-variant)
1. [Run the `yarf` command](#run-the-yarf-command)

## Prepare the test suite

First of all, we need to prepare the test suite. In terms of YARF, a test suite is defined as a directory that at least contains a `.robot` file. For example, we have a directory named `suite`:

```
suite
└── test.robot
```

<u><center>Code Snippet 1: An example of a simplest test suite</center></u>

This is the simplest test suite YARF will accept. A directory without a `.robot` file will result in an error. There are tag(s) that we support in YARF, for details please visit [Write a Robot File with YARF Tags](./write-a-robot-file-with-yarf-tags.md)

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

<u><center>Code Snippet 2: An example of a more comprehensive test suite</center></u>

The `variants` directory contains modified versions of the base templates, organized in sub-directories by specific variations; this will be discussed further in the section [Provide the correct variant](#provide-the-correct-variant).

## Identify the platform

We need to identify the platform that we would like to run to use YARF. The choice is different in different case, for now we are working to support the following platforms:

- Example: A hardware test fixture enabling advanced system testing. For details please visit [here](https://canonical-Example.readthedocs-hosted.com/en/latest/)
- Mir: A display server that is suitable for local development and continuous integration. For details please visit [here](https://canonical-mir.readthedocs-hosted.com/stable/)

The support for QEMU and GNOME are on the roadmap and will be added in the future, so stay tuned :).

## Provide the correct variant

A robot task can be executed on different machines and therefore we have variant assets to cater different scenarios. For this, we provide an optional argument `--variant` for the user to specify the variant they are interested to test with and automatically run the test suite with relevant assets in the `variants` directory. The variant is specified by a variant string with the format:

```
<attribute1>/<attribute2>/<attribute3>/...
```

<u><center>Code Snippet 3: Format for the variant string.</center></u>

Take example on Code Snippet 2, we can have one variant strings:

1. `var`: When running the test suite, we use `suite/variants/var/a1.png` and `suite/variants/var/sub/a2.png` instead of `suite/a1.png` and `suite/a2.png`.

```{caution}
Do not include the names of asset sub-directories (e.g. `sub` in Code Snippet 2) in variant strings because those are part of the suite's assets and are not attributes for us to select different variants. With this, we recommend adding a prefix to the asset sub-directories, like the suite name.
```

When a variant string is provided, we will search for directories that has a name matching any attributes in the variant string in the order of specificity degree. To elaborate, it is the reversed ascending sort by the number of attributes we have in the provided variant string. For example, if we have a variant string `noble/1920/x1080/ubuntu-frame`, we will we searching the directories in the following order:

```text
noble/1920/x1080/ubuntu-frame
1920/x1080/ubuntu-frame
noble/1920/x1080
x1080/ubuntu-frame
1920/x1080
noble/1920
ubuntu-frame
x1080
1920
noble
```

<u><center>Code Snippet 5: Searching order for the variant string `noble/1920/1920x1080/ubuntu-frame`</center></u>

We will always take the assets that are discovered in the first occurrence. So for instance if we have an asset name `a5.png` under the directories `noble/1920/x1080` and `x1080`, we will use the one in `noble/1920/x1080` only.

If assets need to be shared between variant directories, symbolic links may be used.

## Run the `yarf` command

To run a test suite named `<suite>` using a given `<platform>` and a `<variant>`, the `yarf` command would be:

```
yarf --variant <variant> --platform <platform> <path-to-test-suite>/suite
```

<u><center>Code Snippet 6: `yarf` command</center></u>

If the `--platform` argument is not specified, then YARF will use Example as the platform:

```
Example_IP=<Example_IP> yarf <path-to-suite>/suite
```

<u><center>Code Snippet 7: `yarf` command without `--platform` option</center></u>
