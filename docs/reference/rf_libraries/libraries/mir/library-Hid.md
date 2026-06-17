# Hid

<p>A Robot Framework library for interacting with virtual Wayland-based HIDs.</p>
<p>The client connects to the display upon entering the first keyword, and disconnects when the library goes out of scope.</p>
<p>If WAYLAND_DISPLAY is not defined, it defaults to 'wayland-0'.</p>
<p>Attributes: ROBOT_LISTENER_API_VERSION: Robot listener API version</p>

- **Type**: LIBRARY
- **Scope**: TEST

## Keywords

### Click Pointer Button

<p>Click pointer button.</p>
<p>Arguments: button: one of LEFT, MIDDLE, RIGHT</p>

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required |
| ------ | ------ | ------------- | ------------------- | -------- |
| button | string |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Keys Combo

<p>Press and release a combination of keys.</p>
<p>Arguments: combo: first key, or a list of keys to press at the same time. *keys: remaining keys to press.</p>
<p>Raises: AssertionError: If both combo and keys are provided.</p>

#### Positional and named arguments

| Name  | Type   | Default Value | Kind                | Required |
| ----- | ------ | ------------- | ------------------- | -------- |
| combo | None   |               | POSITIONAL_OR_NAMED | Yes      |
| keys  | string |               | VAR_POSITIONAL      | No       |

<hr style="border:1px solid grey">

### Move Pointer To Absolute

<p>Move the virtual pointer to an absolute position within the output.</p>
<p>Args: x: horizontal coordinate, 0 &lt;= x &lt;= screen width y: vertical coordinate, 0 &lt;= y &lt;= screen height</p>
<p>Raises: AssertionError: if coordinates are out of range</p>

#### Positional and named arguments

| Name | Type    | Default Value | Kind                | Required |
| ---- | ------- | ------------- | ------------------- | -------- |
| x    | integer |               | POSITIONAL_OR_NAMED | Yes      |
| y    | integer |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Move Pointer To Proportional

<p>Move the virtual pointer to a position proportional to the size of the output.</p>
<p>Args: x: horizontal coordinate, 0 &lt;= x &lt;= 1 y: vertical coordinate, 0 &lt;= y &lt;= 1</p>
<p>Raises: AssertionError: if coordinates are out of range</p>

#### Positional and named arguments

| Name | Type  | Default Value | Kind                | Required |
| ---- | ----- | ------------- | ------------------- | -------- |
| x    | float |               | POSITIONAL_OR_NAMED | Yes      |
| y    | float |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Press Pointer Button

<p>Press pointer button.</p>
<p>Arguments: button: one of LEFT, MIDDLE, RIGHT</p>

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required |
| ------ | ------ | ------------- | ------------------- | -------- |
| button | string |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Release Pointer Button

<p>Release pointer button.</p>
<p>Arguments: button: one of LEFT, MIDDLE, RIGHT</p>

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required |
| ------ | ------ | ------------- | ------------------- | -------- |
| button | string |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Release Pointer Buttons

<p>Release all pointer buttons.</p>

<hr style="border:1px solid grey">

### Type String

<p>Type a string.</p>
<p>Arguments: string: string to type.</p>

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required |
| ------ | ------ | ------------- | ------------------- | -------- |
| string | string |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Walk Pointer To Absolute

<p>Walk the virtual pointer to an absolute position within the output, maximum <span class="name">step_distance</span> at a time, with <span class="name">delay</span> seconds in between.</p>
<p>Args: x: horizontal coordinate, 0 &lt;= x &lt;= screen width y: vertical coordinate, 0 &lt;= y &lt;= screen height step_distance: maximum distance to move per step delay: delay between steps in seconds</p>
<p>Raises: AssertionError: if coordinates are out of range or if x and y are not integers</p>

#### Positional and named arguments

| Name          | Type    | Default Value | Kind                | Required |
| ------------- | ------- | ------------- | ------------------- | -------- |
| x             | integer |               | POSITIONAL_OR_NAMED | Yes      |
| y             | integer |               | POSITIONAL_OR_NAMED | Yes      |
| step_distance | float   |               | POSITIONAL_OR_NAMED | Yes      |
| delay         | float   |               | POSITIONAL_OR_NAMED | Yes      |

<hr style="border:1px solid grey">

### Walk Pointer To Proportional

<p>Walk the virtual pointer to a position proportional to the size of the output, maximum <span class="name">step_distance</span> at a time, with <span class="name">delay</span> seconds in between.</p>
<p>Args: x: horizontal coordinate, 0 &lt;= x &lt;= 1 y: vertical coordinate, 0 &lt;= y &lt;= 1 step_distance: maximum distance to move per step horizontally, 0 &lt; step_distance &lt;= 1 delay: delay between steps in seconds</p>
<p>Raises: AssertionError: if coordinates are out of range</p>

#### Positional and named arguments

| Name          | Type  | Default Value | Kind                | Required |
| ------------- | ----- | ------------- | ------------------- | -------- |
| x             | float |               | POSITIONAL_OR_NAMED | Yes      |
| y             | float |               | POSITIONAL_OR_NAMED | Yes      |
| step_distance | float |               | POSITIONAL_OR_NAMED | Yes      |
| delay         | float |               | POSITIONAL_OR_NAMED | Yes      |
