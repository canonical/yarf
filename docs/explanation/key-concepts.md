# Key concepts

YARF automates testing of graphical user interfaces (GUI) by driving a real interface while your test defines what to check, for example, moving the pointer, typing, and matching what appears on screen. This page defines the concepts of the core features and provides an overview of how they work together.

(concept_keyword)=

## Keyword

A keyword is a single, named action or check that forms the smallest unit of a YARF test.

Keywords come from [Robot Framework](https://robotframework.org/), which YARF builds upon, and are written in a readable, near-natural-language form such as `Type String` or `Click LEFT Button On`. YARF supplements Robot Framework's built-in keywords with GUI-specific ones for controlling the pointer and keyboard and for matching what is on screen.

Keywords are the building blocks of every test: they are composed into tasks and suites during authoring, and executed against a platform at run time. Because a keyword expresses an intended action or check in readable terms, a test can describe the expected behaviour independently of its implementation on any particular display server.

(concept_test_suite)=

## Test suite

A test suite is a collection of related tasks, each a sequence of keywords, that YARF executes together as a unit.

Suites are written in Robot Framework's `.robot` and `.resource` files and represent a complete test scenario, for example, verifying that an application behaves correctly through a series of interactions.

When a suite runs, YARF executes its keywords in order against the selected {ref}`concept_platform`, and uses any {ref}`concept_metadata_and_tags` on the suite to decide which tasks are included.

(concept_platform)=

## Platform

A platform is the back end that enables YARF to observe a GUI and interact with it. Because YARF is designed to be display-server agnostic, the same test suite can run on different platforms by changing the `--platform` value at run time.

Every platform provides two capabilities:

- **video input**, which supplies a view of the current screen,
- **human interface device (HID)** control, which injects pointer and keyboard events.

YARF ships with platforms for **Mir** (suited to local development and continuous integration) and **Vnc** (suited to remote or virtualized targets), and it can be extended with additional platforms through plugins.

For details about how platforms are used and extended, see {doc}`../how-to/using-the-vnc-backend` and {doc}`../how-to/platform-plugins`.

(concept_template)=

## Template

A template is a reference image that YARF locates within the current screen to determine the target of a keyword.

Because YARF operates on a real GUI, a keyword such as "click this button" must first find its target on screen. A template is a captured region such as a button or icon that provides this reference: keywords match it against the live video input, within a configurable tolerance, before acting. When the target is text, YARF can locate it directly through optical character recognition (OCR) rather than an image.

Templates are typically captured with the `Grab Templates` keyword in the {doc}`Interactive library<../reference/rf_libraries/interactive_console/library-Interactive>`; matching behaviour is documented in the {doc}`VideoInput library<../reference/rf_libraries/libraries/library-video_input_base>`.

(concept_metadata_and_tags)=

## Metadata and tags

Metadata and tags are annotations on a suite or its tasks that configure how a test runs and which tasks are selected. Their common usage is organising and controlling large or automated test runs, where they determine which tasks execute and how the results are grouped and interpreted.

YARF extends Robot Framework's own metadata and tags with entries specific to GUI testing - for example, declaring the expected display resolutions, requiring a minimum YARF version, or classifying tasks by category, group, or certification status.

For the list of supported entries, see {doc}`../reference/yarf-metadata-and-tags`.
