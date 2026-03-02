# VideoInput

<p>This class provides the Mir-driven implementation for video interactions and assertions.</p>
<p>Attributes: ROBOT_LISTENER_API_VERSION: API version for Robot Framework listeners.</p>

- **Type**: LIBRARY
- **Scope**: GLOBAL

## Keywords

### Find Text

<p>Find the specified text in the provided image or grab a screenshot to search from. The region can be specified directly in the robot file using <span class="name">RPA.core.geometry.to_region</span></p>
<p>Args: text: text or regex to search for, use the format <span class="name">regex:&lt;regex-string&gt;</span> if the text we want to find is a regex. region: region to search for the text. image: image to search from.</p>
<p>Returns: The list of matched text regions where the text was found. Each match is a dictionary with "text", "region", and "confidence".</p>

### Return

{'name': 'List', 'typedoc': 'list', 'nested': [{'name': 'dict', 'typedoc': 'dictionary', 'nested': [], 'union': False}], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| text | string |  | POSITIONAL_OR_NAMED | Yes |
| region | None | None | POSITIONAL_OR_NAMED | No |
| image | None | None | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Get Text Position

<p>Get the center position of the best match for the specified text. The region to search can be also specified. The center position is round to the nearest integer.</p>
<p>Run with <span class="name">--debug</span> option (or YARF_LOG_LEVEL=DEBUG) to always log the image with the matched region.</p>
<p>Args: text: The text to match on screen region: The region to search for the text Returns: The x and y coordinates of the center of the best match</p>

### Return

{'name': 'tuple', 'typedoc': 'tuple', 'nested': [{'name': 'int', 'typedoc': 'integer', 'nested': [], 'union': False}, {'name': 'int', 'typedoc': 'integer', 'nested': [], 'union': False}], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| text | string |  | POSITIONAL_OR_NAMED | Yes |
| region | None | None | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Grab Screenshot

<p>Grabs the current frame through screencopy.</p>
<p>Returns: Pillow Image of the frame</p>

### Return

{'name': 'Image', 'typedoc': None, 'nested': [], 'union': False}

<hr style="border:1px solid grey">

### Log Screenshot

<p>Grab an image and add it to the HTML log.</p>
<p>Args: msg: Message to log with the image</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| msg | string |  | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Match

<p>Grab screenshots and compare until there's a match with the provided template or timeout.</p>
<p>Args: template: path to an image file to be used as template timeout: timeout in seconds tolerance: The tolerance for image comparison in the compare_images method region: the region to search for the template in Returns: list of matched regions</p>

### Return

{'name': 'List', 'typedoc': 'list', 'nested': [{'name': 'Region', 'typedoc': None, 'nested': [], 'union': False}], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| template | string |  | POSITIONAL_OR_NAMED | Yes |
| timeout | integer | 10 | POSITIONAL_OR_NAMED | No |
| tolerance | float | 0.8 | POSITIONAL_OR_NAMED | No |
| region | None | None | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Match All

<p>Grab screenshots and compare with the provided templates until a frame is found which matches all templates simultaneously or timeout.</p>
<p>Args: templates: sequence of paths to image files to use as templates timeout: timeout in seconds tolerance: The tolerance for image comparison in the compare_images method</p>
<p>Returns: List of matched regions and template path matched</p>

### Return

{'name': 'List', 'typedoc': 'list', 'nested': [{'name': 'dict', 'typedoc': 'dictionary', 'nested': [], 'union': False}], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| templates | Sequence |  | POSITIONAL_OR_NAMED | Yes |
| timeout | integer | 10 | POSITIONAL_OR_NAMED | No |
| tolerance | float | 0.8 | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Match Any

<p>Grab screenshots and compare with the provided templates until there's at least one match or timeout.</p>
<p>Args: templates: sequence of paths to image files to use as templates timeout: timeout in seconds tolerance: The tolerance for image comparison in the compare_images method region: the region to search for the template in</p>
<p>Returns: list of matched regions and template path matched</p>

### Return

{'name': 'List', 'typedoc': 'list', 'nested': [{'name': 'dict', 'typedoc': 'dictionary', 'nested': [], 'union': False}], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| templates | Sequence |  | POSITIONAL_OR_NAMED | Yes |
| timeout | integer | 10 | POSITIONAL_OR_NAMED | No |
| tolerance | float | 0.8 | POSITIONAL_OR_NAMED | No |
| region | None | None | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Match Text

<p>Wait for specified text to appear on screen and get the position of the best match. The region can be specified directly in the robot file using <span class="name">RPA.core.geometry.to_region</span>.</p>
<p>Args: text: text or regex to match, use the format <span class="name">regex:&lt;regex-string&gt;</span> if the text we want to find is a regex. timeout: Time to wait for the text to appear region: The region to search for the text color: The color of the searched text color_tolerance: The tolerance of the color of the searched text Returns: It returns a tuple with:</p>
<ul>
<li>The list of matched text regions where the text was found, sorted by confidence.</li>
<li>The image (used for debugging). Each match is a dictionary with "text", "region", and "confidence".</li>
</ul>
<p>Raises: ValueError: If the specified text isn't found in time</p>

### Return

{'name': 'tuple', 'typedoc': 'tuple', 'nested': [{'name': 'list', 'typedoc': 'list', 'nested': [{'name': 'dict', 'typedoc': 'dictionary', 'nested': [], 'union': False}], 'union': False}, {'name': 'Image', 'typedoc': None, 'nested': [], 'union': False}], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| text | string |  | POSITIONAL_OR_NAMED | Yes |
| timeout | integer | 10 | POSITIONAL_OR_NAMED | No |
| region | None | None | POSITIONAL_OR_NAMED | No |
| color | None | None | POSITIONAL_OR_NAMED | No |
| color_tolerance | integer | 20 | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Read Text

<p>Read the text from the provided image or grab a screenshot to read from.</p>
<p>Args: image: image to read text from</p>
<p>Returns: text read from the image</p>

### Return

{'name': 'str', 'typedoc': 'string', 'nested': [], 'union': False}

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| image | None | None | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Restart Video Input

<p>Restart video stream process if needed.</p>

<hr style="border:1px solid grey">

### Set Ocr Method

<p>Set the OCR method to use.</p>
<p>Args: method: OCR method to use. Either "rapidocr" or "tesseract".</p>
<p>Raises: ValueError: If the specified method is not supported.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| method | string | rapidocr | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Start Video Input

<p>Connect to the display.</p>

<hr style="border:1px solid grey">

### Stop Video Input

<p>Disconnect from the display.</p>

<hr style="border:1px solid grey">

### Wait Still Screen

<p>Monitors the screen for a set 'duration' (e.g., 30s), checking every 'interval' (e.g., 5s). Fails if the screen is not still for still_duration.</p>
<p>Args: duration: Total time to monitor the screen (in seconds) still_duration: Time the screen must remain still (in seconds) screenshot_interval: Interval between screenshots (in seconds)</p>
<p>Raises: TimeoutError: If the screen does not remain still for the required still_duration within the total duration.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| duration | float | 30.0 | POSITIONAL_OR_NAMED | No |
| still_duration | float | 10.0 | POSITIONAL_OR_NAMED | No |
| screenshot_interval | float | 1.0 | POSITIONAL_OR_NAMED | No |
