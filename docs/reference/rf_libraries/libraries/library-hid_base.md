# Hid

<p>Documentation for library <code>Hid</code>.</p>

- **Type**: LIBRARY
- **Scope**: TEST

## Keywords

### Click Pointer Button

<p>Press and release the specified pointer button.</p>

#### Return

```
None
```

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required | Documentation                 |
| ------ | ------ | ------------- | ------------------- | -------- | ----------------------------- |
| button | string |               | POSITIONAL_OR_NAMED | Yes      | either LEFT, MIDDLE or RIGHT. |

#### Example

```robotframework
Click Pointer Button    LEFT
```

<hr style="border:1px solid grey">

### Keys Combo

<p>Press and release a combination of keys.</p>

#### Return

```
None
```

#### Raises

- `AssertionError`: If both combo and keys are provided.

#### Positional and named arguments

| Name  | Type   | Default Value | Kind                | Required | Documentation                                           |
| ----- | ------ | ------------- | ------------------- | -------- | ------------------------------------------------------- |
| combo | None   |               | POSITIONAL_OR_NAMED | Yes      | first key, or a list of keys to press at the same time. |
| keys  | string |               | VAR_POSITIONAL      | No       | remaining keys to press.                                |

#### Example

```robotframework
Keys Combo    Control_L    Alt_L    Delete
${combo}=    Create List    Control_L    c
Keys Combo    ${combo}
```

<hr style="border:1px solid grey">

### Move Pointer To Absolute

<p>Move the virtual pointer to an absolute position within the output.</p>

#### Return

```
None
```

#### Raises

- `AssertionError`: if coordinates are out of range

#### Positional and named arguments

| Name | Type    | Default Value | Kind                | Required | Documentation                                   |
| ---- | ------- | ------------- | ------------------- | -------- | ----------------------------------------------- |
| x    | integer |               | POSITIONAL_OR_NAMED | Yes      | horizontal coordinate, 0 \<= x \<= screen width |
| y    | integer |               | POSITIONAL_OR_NAMED | Yes      | vertical coordinate, 0 \<= y \<= screen height  |

#### Example

```robotframework
Move Pointer To Absolute    ${640}    ${480}
```

<hr style="border:1px solid grey">

### Move Pointer To Proportional

<p>Move the virtual pointer to a position proportional to the size of the output.</p>

#### Return

```
None
```

#### Raises

- `AssertionError`: if coordinates are out of range

#### Positional and named arguments

| Name | Type  | Default Value | Kind                | Required | Documentation                        |
| ---- | ----- | ------------- | ------------------- | -------- | ------------------------------------ |
| x    | float |               | POSITIONAL_OR_NAMED | Yes      | horizontal coordinate, 0 \<= x \<= 1 |
| y    | float |               | POSITIONAL_OR_NAMED | Yes      | vertical coordinate, 0 \<= y \<= 1   |

#### Example

```robotframework
Move Pointer To Proportional    0.5    0.5
```

<hr style="border:1px solid grey">

### Press Pointer Button

<p>Press the specified pointer button.</p>

#### Return

```
None
```

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required | Documentation                 |
| ------ | ------ | ------------- | ------------------- | -------- | ----------------------------- |
| button | string |               | POSITIONAL_OR_NAMED | Yes      | either LEFT, MIDDLE or RIGHT. |

#### Example

```robotframework
Press Pointer Button    LEFT
```

<hr style="border:1px solid grey">

### Release Pointer Button

<p>Release the specified pointer button.</p>

#### Return

```
None
```

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required | Documentation                 |
| ------ | ------ | ------------- | ------------------- | -------- | ----------------------------- |
| button | string |               | POSITIONAL_OR_NAMED | Yes      | either LEFT, MIDDLE or RIGHT. |

#### Example

```robotframework
Release Pointer Button    LEFT
```

<hr style="border:1px solid grey">

### Release Pointer Buttons

<p>Release all pointer buttons.</p>

#### Return

```
None
```

#### Example

```robotframework
Release Pointer Buttons
```

<hr style="border:1px solid grey">

### Type String

<p>Type a string.</p>

#### Return

```
None
```

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required | Documentation   |
| ------ | ------ | ------------- | ------------------- | -------- | --------------- |
| string | string |               | POSITIONAL_OR_NAMED | Yes      | string to type. |

#### Example

```robotframework
Type String    hello world
```

<hr style="border:1px solid grey">

### Walk Pointer To Absolute

<p>Walk the virtual pointer to an absolute position within the output, maximum <span class="name">step_distance</span> at a time, with <span class="name">delay</span> seconds in between.</p>

#### Return

```
None
```

#### Raises

- `AssertionError`: if coordinates are out of range or if x and y are not integers

#### Positional and named arguments

| Name          | Type    | Default Value | Kind                | Required | Documentation                                   |
| ------------- | ------- | ------------- | ------------------- | -------- | ----------------------------------------------- |
| x             | integer |               | POSITIONAL_OR_NAMED | Yes      | horizontal coordinate, 0 \<= x \<= screen width |
| y             | integer |               | POSITIONAL_OR_NAMED | Yes      | vertical coordinate, 0 \<= y \<= screen height  |
| step_distance | float   |               | POSITIONAL_OR_NAMED | Yes      | maximum distance to move per step               |
| delay         | float   |               | POSITIONAL_OR_NAMED | Yes      | delay between steps in seconds                  |

#### Example

```robotframework
Walk Pointer To Absolute    ${640}    ${480}    ${10}    ${0.01}
```

<hr style="border:1px solid grey">

### Walk Pointer To Proportional

<p>Walk the virtual pointer to a position proportional to the size of the output, maximum <span class="name">step_distance</span> at a time, with <span class="name">delay</span> seconds in between.</p>

#### Return

```
None
```

#### Raises

- `AssertionError`: if coordinates are out of range

#### Positional and named arguments

| Name          | Type  | Default Value | Kind                | Required | Documentation                                                           |
| ------------- | ----- | ------------- | ------------------- | -------- | ----------------------------------------------------------------------- |
| x             | float |               | POSITIONAL_OR_NAMED | Yes      | horizontal coordinate, 0 \<= x \<= 1                                    |
| y             | float |               | POSITIONAL_OR_NAMED | Yes      | vertical coordinate, 0 \<= y \<= 1                                      |
| step_distance | float |               | POSITIONAL_OR_NAMED | Yes      | maximum distance to move per step horizontally, 0 < step_distance \<= 1 |
| delay         | float |               | POSITIONAL_OR_NAMED | Yes      | delay between steps in seconds                                          |

#### Example

```robotframework
Walk Pointer To Proportional    0.5    0.5    0.05    ${0.01}
```
