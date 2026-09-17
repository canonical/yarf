# VideoInput

<p>Documentation for library <code>VideoInput</code>.</p>

- **Type**: LIBRARY
- **Scope**: GLOBAL

## Keywords

### Find Cursor Position

<p>Detect the cursor in the provided image or a new screenshot.</p>
<p>Note: This keyword relies on a bundled cursor detection model, which increases the installed package size. The current model is trained for simple navigation tasks where mouse is clearly visible, and works better for the regular arrow. Use it carefully in other contexts until a more robust model is available.</p>

#### Return

```
tuple[integer, integer] | None
```

<p>(x, y) absolute pixel coordinates of the cursor, or None.</p>

#### Positional and named arguments

| Name       | Type  | Default Value | Kind                | Required | Documentation                                            |
| ---------- | ----- | ------------- | ------------------- | -------- | -------------------------------------------------------- |
| image      | None  | None          | POSITIONAL_OR_NAMED | No       | Image to search; grabs a screenshot if not provided.     |
| confidence | float | 0.85          | POSITIONAL_OR_NAMED | No       | Minimum confidence (0-1) for a detection to be accepted. |

#### Example

```robotframework
${position}=    Find Cursor Position
${position}=    Find Cursor Position    confidence=0.8
```

<hr style="border:1px solid grey">

### Find Text

<p>Find the specified text in the provided image or grab a screenshot to search from. The region can be specified directly in the robot file using <span class="name">RPA.core.geometry.to_region</span></p>

#### Return

```
list[dictionary]
```

<p>The list of matched text regions where the text was found. Each match is a dictionary with "text", "region", and "confidence".</p>

#### Positional and named arguments

| Name            | Type    | Default Value | Kind                | Required | Documentation                                                                                                                              |
| --------------- | ------- | ------------- | ------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| text            | string  |               | POSITIONAL_OR_NAMED | Yes      | text or regex to search for, use the format <span class="name">regex:\<regex-string></span> if the text we want to find is a regex.        |
| region          | None    | None          | POSITIONAL_OR_NAMED | No       | region to search for the text.                                                                                                             |
| image           | None    | None          | POSITIONAL_OR_NAMED | No       | image to search from.                                                                                                                      |
| color           | None    | None          | POSITIONAL_OR_NAMED | No       | target color of the text. If set, matched text in the wrong color will be skipped.                                                         |
| color_tolerance | integer | 20            | POSITIONAL_OR_NAMED | No       | Color tolerance threshold in %                                                                                                             |
| similarity      | None    | None          | POSITIONAL_OR_NAMED | No       | Minimum similarity percentage (0-100) for a match when using RapidOCR. If set, overrides \$\{OCR_SIMILARITY_THRESHOLD} for this call only. |
| confidence      | None    | None          | POSITIONAL_OR_NAMED | No       | Minimum confidence percentage (0-100) for a match when using RapidOCR. If set, overrides \$\{OCR_CONFIDENCE_THRESHOLD} for this call only. |

#### Example

```robotframework
${matches}=    Find Text    Continue
${matches}=    Find Text    regex:[0-9]{3}
&{region}=    Create Dictionary
...    left=0    top=0    right=800    bottom=600
${matches}=    Find Text    Continue    region=${region}
${matches}=    Find Text    Continue
...    similarity=90    confidence=70
```

<hr style="border:1px solid grey">

### Get Displays

<p>This function parses the displays metadata and returns a dictionary of display names and their respective resolutions. In the case of the camera input, this resolution will be the one used in the display the camera is pointing at.</p>

#### Return

```
list[tuple[string | None, string]]
```

<p>Dictionary of display indices or names and their respective resolutions</p>

#### Raises

- `ValueError`: if the displays metadata is not in the expected format

<hr style="border:1px solid grey">

### Get Text Position

<p>Get the center position of the best match for the specified text. The region to search can be also specified. The center position is round to the nearest integer.</p>
<p>Run with <span class="name">--debug</span> option (or YARF_LOG_LEVEL=DEBUG) to always log the image with the matched region.</p>

#### Return

```
tuple[integer, integer]
```

<p>The x and y coordinates of the center of the best match</p>

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required | Documentation                     |
| ------ | ------ | ------------- | ------------------- | -------- | --------------------------------- |
| text   | string |               | POSITIONAL_OR_NAMED | Yes      | The text to match on screen       |
| region | None   | None          | POSITIONAL_OR_NAMED | No       | The region to search for the text |

#### Example

```robotframework
${x}    ${y}=    Get Text Position    Continue
Move Pointer To Absolute    ${x}    ${y}
```

<hr style="border:1px solid grey">

### Grab Screenshot

<p>Grab and return a screenshot from the video feed.</p>

#### Return

```
PIL.Image.Image
```

<p>screenshot as an Image object</p>

#### Example

```robotframework
${image}=    Grab Screenshot
```

<hr style="border:1px solid grey">

### Log Screenshot

<p>Grab an image and add it to the HTML log.</p>

#### Return

```
None
```

#### Positional and named arguments

| Name | Type   | Default Value | Kind                | Required | Documentation                 |
| ---- | ------ | ------------- | ------------------- | -------- | ----------------------------- |
| msg  | string |               | POSITIONAL_OR_NAMED | No       | Message to log with the image |

#### Example

```robotframework
Log Screenshot    Desktop after login
```

<hr style="border:1px solid grey">

### Match

<p>Grab screenshots and compare until there's a match with the provided template or timeout.</p>

#### Return

```
list[Region]
```

<p>list of matched regions</p>

#### Positional and named arguments

| Name      | Type    | Default Value | Kind                | Required | Documentation                                                   |
| --------- | ------- | ------------- | ------------------- | -------- | --------------------------------------------------------------- |
| template  | string  |               | POSITIONAL_OR_NAMED | Yes      | path to an image file to be used as template                    |
| timeout   | integer | 10            | POSITIONAL_OR_NAMED | No       | timeout in seconds                                              |
| tolerance | float   | 0.8           | POSITIONAL_OR_NAMED | No       | The tolerance for image comparison in the compare_images method |
| region    | None    | None          | POSITIONAL_OR_NAMED | No       | the region to search for the template in                        |

#### Example

```robotframework
${regions}=    Match    ${CURDIR}/button.png
Match    ${CURDIR}/button.png    timeout=30    tolerance=0.9
```

<hr style="border:1px solid grey">

### Match All

<p>Grab screenshots and compare with the provided templates until a frame is found which matches all templates simultaneously or timeout.</p>

#### Return

```
list[dictionary]
```

<p>List of matched regions and template path matched</p>

#### Positional and named arguments

| Name      | Type     | Default Value | Kind                | Required | Documentation                                                   |
| --------- | -------- | ------------- | ------------------- | -------- | --------------------------------------------------------------- |
| templates | Sequence |               | POSITIONAL_OR_NAMED | Yes      | sequence of paths to image files to use as templates            |
| timeout   | integer  | 10            | POSITIONAL_OR_NAMED | No       | timeout in seconds                                              |
| tolerance | float    | 0.8           | POSITIONAL_OR_NAMED | No       | The tolerance for image comparison in the compare_images method |

#### Example

```robotframework
${templates}=    Create List    ${CURDIR}/ok.png    ${CURDIR}/cancel.png
${matches}=    Match All    ${templates}    timeout=30
```

<hr style="border:1px solid grey">

### Match Any

<p>Grab screenshots and compare with the provided templates until there's at least one match or timeout.</p>

#### Return

```
list[dictionary]
```

<p>list of matched regions and template path matched</p>

#### Positional and named arguments

| Name      | Type     | Default Value | Kind                | Required | Documentation                                                   |
| --------- | -------- | ------------- | ------------------- | -------- | --------------------------------------------------------------- |
| templates | Sequence |               | POSITIONAL_OR_NAMED | Yes      | sequence of paths to image files to use as templates            |
| timeout   | integer  | 10            | POSITIONAL_OR_NAMED | No       | timeout in seconds                                              |
| tolerance | float    | 0.8           | POSITIONAL_OR_NAMED | No       | The tolerance for image comparison in the compare_images method |
| region    | None     | None          | POSITIONAL_OR_NAMED | No       | the region to search for the template in                        |

#### Example

```robotframework
${templates}=    Create List    ${CURDIR}/ok.png    ${CURDIR}/cancel.png
${matches}=    Match Any    ${templates}    timeout=30
```

<hr style="border:1px solid grey">

### Match Text

<p>Wait for specified text to appear on screen and get the position of the best match. The region can be specified directly in the robot file using <span class="name">RPA.core.geometry.to_region</span>.</p>

#### Return

```
tuple[list[dictionary], Image]
```

<p>It returns a tuple with:</p>
<ul>
<li>The list of matched text regions where the text was found, sorted by confidence.</li>
<li>The image (used for debugging).</li>
</ul>
<p>Each match is a dictionary with "text", "region", and "confidence".</p>

#### Raises

- `ValueError`: If the specified text isn't found in time

#### Positional and named arguments

| Name            | Type    | Default Value | Kind                | Required | Documentation                                                                                                                              |
| --------------- | ------- | ------------- | ------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| text            | string  |               | POSITIONAL_OR_NAMED | Yes      | text or regex to match, use the format <span class="name">regex:\<regex-string></span> if the text we want to find is a regex.             |
| timeout         | integer | 10            | POSITIONAL_OR_NAMED | No       | Time to wait for the text to appear                                                                                                        |
| region          | None    | None          | POSITIONAL_OR_NAMED | No       | The region to search for the text                                                                                                          |
| color           | None    | None          | POSITIONAL_OR_NAMED | No       | The color of the searched text                                                                                                             |
| color_tolerance | integer | 20            | POSITIONAL_OR_NAMED | No       | The tolerance of the color of the searched text                                                                                            |
| similarity      | None    | None          | POSITIONAL_OR_NAMED | No       | Minimum similarity percentage (0-100) for a match when using RapidOCR. If set, overrides \$\{OCR_SIMILARITY_THRESHOLD} for this call only. |
| confidence      | None    | None          | POSITIONAL_OR_NAMED | No       | Minimum confidence percentage (0-100) for a match when using RapidOCR. If set, overrides \$\{OCR_CONFIDENCE_THRESHOLD} for this call only. |

#### Example

```robotframework
${matches}    ${image}=    Match Text    Continue
Match Text    Continue    timeout=60
${matches}    ${image}=    Match Text    Continue
...    similarity=90    confidence=70
```

<hr style="border:1px solid grey">

### Read Text

<p>Read the text from the provided image or grab a screenshot to read from.</p>

#### Return

```
string
```

<p>text read from the image</p>

#### Positional and named arguments

| Name  | Type | Default Value | Kind                | Required | Documentation           |
| ----- | ---- | ------------- | ------------------- | -------- | ----------------------- |
| image | None | None          | POSITIONAL_OR_NAMED | No       | image to read text from |

#### Example

```robotframework
${text}=    Read Text
${image}=    Grab Screenshot
${text}=    Read Text    ${image}
```

<hr style="border:1px solid grey">

### Restart Video Input

<p>Restart video stream process if needed.</p>

#### Return

```
None
```

#### Example

```robotframework
Restart Video Input
```

<hr style="border:1px solid grey">

### Set Ocr Method

<p>Set the OCR method to use.</p>

#### Return

```
None
```

#### Raises

- `ValueError`: If the specified method is not supported.

#### Positional and named arguments

| Name   | Type   | Default Value | Kind                | Required | Documentation                                        |
| ------ | ------ | ------------- | ------------------- | -------- | ---------------------------------------------------- |
| method | string | rapidocr      | POSITIONAL_OR_NAMED | No       | OCR method to use. Either "rapidocr" or "tesseract". |

#### Example

```robotframework
Set Ocr Method    tesseract
```

<hr style="border:1px solid grey">

### Start Video Input

<p>Start video stream process if needed.</p>

#### Return

```
None
```

#### Example

```robotframework
Start Video Input
```

<hr style="border:1px solid grey">

### Stop Video Input

<p>Stop video stream process if needed.</p>

#### Return

```
None
```

#### Example

```robotframework
Stop Video Input
```

<hr style="border:1px solid grey">

### Wait Still Screen

<p>Monitors the screen for a set 'duration' (e.g., 30s), checking every 'interval' (e.g., 5s). Fails if the screen is not still for still_duration.</p>

#### Return

```
None
```

#### Raises

- `TimeoutError`: If the screen does not remain still for the required still_duration within the total duration.

#### Positional and named arguments

| Name                | Type  | Default Value | Kind                | Required | Documentation                                  |
| ------------------- | ----- | ------------- | ------------------- | -------- | ---------------------------------------------- |
| duration            | float | 30.0          | POSITIONAL_OR_NAMED | No       | Total time to monitor the screen (in seconds)  |
| still_duration      | float | 10.0          | POSITIONAL_OR_NAMED | No       | Time the screen must remain still (in seconds) |
| screenshot_interval | float | 1.0           | POSITIONAL_OR_NAMED | No       | Interval between screenshots (in seconds)      |

#### Example

```robotframework
Wait Still Screen
Wait Still Screen    duration=60    still_duration=5
```
