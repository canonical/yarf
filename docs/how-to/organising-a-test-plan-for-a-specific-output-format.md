# Organising a test plan for a specific output format

```{note}
This guides assumes the reader has the knowledge of how to write tags and metadata in Robot Framework.
```

YARF can convert the output to supported output formats, including:

1. [Test Submission Schema](https://github.com/canonical/test-submission-schema)

## Test Submission Schema

To prepare a test plan for the test submission schema, we need to provide the following metadata and tags:
Metadata:

1. `namespace`: The namespace of YARF, defaults to `com.canonical.yarf` if it is not provided.
1. `title`: Title of the test plan.
1. `test_plan_id`: ID of the test plan.
1. `description`: Optional, description of the test plan.
1. `execution_id`: Optional, ID of the test plan execution.

Tags for each test cases in the test plan:

1. `certification_status`: The certification status of the test case.
1. `category_id`: ID of the test case category.
1. `type`: The type of the test case.

Please visit the YARF Tags documentation in the Reference section for the details of these three tags.

To add the metadata of for a test plan, we need to write an `__init__.robot` file under the test plan. For example:

```text
test_plan_X
├── __init__.robot
├── suite1.robot
├── a1.png
├── sub
│   └── a2.png
└── variants
    └── var
        ├── a1.png
        └── sub
            └── a2.png
```

<u><center>Code Snippet 1: An example of a test plan with an `__init__.robot` file</center></u>

In the `__init__.robot`, we will have the following:

```text
*** Settings ***
Metadata        namespace           com.canonical.yarf
Metadata        title               The title of the test plan
Metadata        description         A brief description of the test plan
Metadata        test_plan_id        com.canonical.test::plan_A
Metadata        execution_id        EXE_ID
```

<u><center>Code Snippet 2: An example of `__init__.robot` that contains the metadata</center></u>

In YARF, we will extract these information, convert and export the output under the `outdir`.
