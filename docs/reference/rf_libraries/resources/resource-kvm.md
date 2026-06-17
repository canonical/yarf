# kvm

<p>Keyword definitions for specialised functionality for Keyboard, Mouse and Video-based manipulation.</p>
<p>These keywords rely on VideoInput and Hid libraries to be initialized using the Init keyword. The initialization is platform-specific.</p>

- **Type**: RESOURCE
- **Scope**: GLOBAL

## Keywords

### Click ${button} Button

<p>Click a button on the virtual pointer.</p>
<p>Embedded arguments:</p>
<ul>
<li>${button}: Button to click (LEFT|RIGHT|MIDDLE).</li>
</ul>

<hr style="border:1px solid grey">

### Click ${button} Button On ${destination}

<p>Move the virtual pointer to the destination and click the button.</p>
<p>See <a class="name" href="#move-pointer-to-destination">Move Pointer to ${destination}</a> for details.</p>
<p>Embedded arguments:</p>
<ul>
<li>${button}: Button to click (LEFT|RIGHT|MIDDLE).</li>
<li>${destination}: The template or location to click on.</li>
</ul>

<hr style="border:1px solid grey">

### Displace ${point} By (${x}, ${y})

<p>Shift a point by the specified displacements along the x and y axes.</p>
<p>Embedded arguments:</p>
<ul>
<li>${point}: Point to be displaced, as a tuple (x, y).</li>
<li>${x}: Displacement along the x-axis.</li>
<li>${y}: Displacement along the y-axis.</li>
</ul>
<p>Return: Displaced point, as a tuple (x, y) of integers.</p>

<hr style="border:1px solid grey">

### Drag And Drop On ${destination}

<p>Drag and drop the current target (where the pointer is) on a destination.</p>
<p>Embedded arguments:</p>
<ul>
<li>${destination}: Can be a string, or the path of an image template file representing</li>
</ul>
<p>the target location to drop on, or a coordinate tuple (x, y) of integers representing the absolute position to drop on. For details please see <a class="name" href="#walk-pointer-to-destination">Walk Pointer To ${destination}</a>.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| step_distance |  | 16 | POSITIONAL_OR_NAMED | No |
| delay |  | 0.01 | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Ensure ${destination} Does Not Match

<p>Ensure a given template or string doesn't match within a given timeout and number of attempts. This function is intended to be used like: "This given template or image should, by the end of this time, not be found on the screen."</p>
<p>Embedded arguments:</p>
<ul>
<li>${destination}: The template or string to match.</li>
</ul>
<p>This function ensures that the given destination is not found.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| timeout |  | 2 | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Get Center Of ${region}

<p>Get the center point of a region.</p>
<p>Embedded arguments:</p>
<ul>
<li>${region}: Rectangular region represented by a dictionary</li>
</ul>
<p>of integer values for "left", "right", "top", and "bottom" keys.</p>
<p>Return: Center of the region, as a tuple (x, y) of integers.</p>

<hr style="border:1px solid grey">

### Get Position Of ${target}

<p>Get a position from an absolute coordinate, image template, or string.</p>
<p>Embedded arguments:</p>
<ul>
<li>${target}: If ${target} is a tuple (x, y) of integers,</li>
</ul>
<p>the position will be the absolute position given by the tuple. Otherwise, if ${target} is the path of an image template file, the position will be the center of the first matching template region. ${target} can also be a string, and the position will be the center of the found text.</p>
<p>Return: Absolute position as a tuple (x, y) of integers.</p>

<hr style="border:1px solid grey">

### Move Pointer To ${destination}

<p>Move the pointer to an absolute position or image template.</p>
<p>Embedded arguments:</p>
<ul>
<li>${destination}: Where to move the pointer to. If ${destination}</li>
</ul>
<p>is a tuple (x, y) of integers, the pointer will move to the absolute position given by the tuple. Otherwise, if ${destination} is the path of an image template file, the pointer will move to the center of the first matching template region. ${destination} can also be a string, and the pointer will move to the center of the found text.</p>
<p>Return: Absolute position of the pointer after the move, as a tuple (x, y) of integers.</p>

<hr style="border:1px solid grey">

### Move Pointer To ${destination} In ${domain}

<p>Move the pointer to an absolute position or image template.</p>
<p>Embedded arguments:</p>
<ul>
<li>${destination}: Where to move the pointer to. If ${destination}</li>
</ul>
<p>is a tuple (x, y) of integers, the pointer will move to the absolute position given by the tuple. Otherwise, if ${destination} is the path of an image template file, the pointer will move to the center of the first matching template region. ${destination} can also be a string, and the pointer will move to the center of the found text.</p>
<ul>
<li>${domain}: Given region or template to search for ${destination} within.</li>
</ul>
<p>Return: Absolute position of the pointer after the move, as a tuple (x, y) of integers.</p>

<hr style="border:1px solid grey">

### Move Pointer To (${x}, ${y})

<p>Move the pointer to an absolute position.</p>
<p>Embedded arguments:</p>
<ul>
<li>${x}: Integer absolute x-coordinate to move the pointer to.</li>
<li>${y}: Integer absolute y-coordinate to move the pointer to.</li>
</ul>

<hr style="border:1px solid grey">

### Move Pointer To Proportional (${x}, ${y})

<p>Move the pointer to a destination position given as proportions to the size of the display output.</p>
<p>Embedded arguments:</p>
<ul>
<li>${x}: Output-relative x-coordinate to move the pointer to.</li>
</ul>
<p>It must be in the range 0..1, where 0 represents the left edge, and 1 represents the right edge of the output.</p>
<ul>
<li>${y}: Output-relative y-coordinate to move the pointer to.</li>
</ul>
<p>It must be in the range 0..1, where 0 represents the top edge, and 1 represents the bottom edge of the output.</p>
<p>Return: Absolute position of the pointer after the move, as a tuple (x, y) of integers.</p>

<hr style="border:1px solid grey">

### Press ${button} Button

<p>Press a button on the virtual pointer.</p>
<p>Embedded arguments:</p>
<ul>
<li>${button}: Button to press (LEFT|RIGHT|MIDDLE).</li>
</ul>

<hr style="border:1px solid grey">

### Press And Wait For Match



#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| keys-combo |  |  | POSITIONAL_OR_NAMED | Yes |
| template |  |  | POSITIONAL_OR_NAMED | Yes |
| timeout |  | 10 | POSITIONAL_OR_NAMED | No |
| tolerance |  | ${DEFAULT_TEMPLATE_MATCHING_TOLERANCE} | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Press Combo And Match

<p>If the provided template is not already matching, press a key combination until it does.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| keys-combo |  |  | POSITIONAL_OR_NAMED | Yes |
| template |  |  | POSITIONAL_OR_NAMED | Yes |
| tentatives |  | 1 | POSITIONAL_OR_NAMED | No |
| timeout |  | 2 | POSITIONAL_OR_NAMED | No |
| tolerance |  | ${DEFAULT_TEMPLATE_MATCHING_TOLERANCE} | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Press Key And Match

<p>If the provided template is not already matching, press a key until it does.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| key |  |  | POSITIONAL_OR_NAMED | Yes |
| template |  |  | POSITIONAL_OR_NAMED | Yes |
| tentatives |  | 1 | POSITIONAL_OR_NAMED | No |
| timeout |  | 2 | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Release ${button} Button

<p>Release a button on the virtual pointer.</p>
<p>Embedded arguments:</p>
<ul>
<li>${button}: Button to release (LEFT|RIGHT|MIDDLE).</li>
</ul>

<hr style="border:1px solid grey">

### Release Buttons

<p>Release all buttons on the virtual pointer.</p>

<hr style="border:1px solid grey">

### Walk Pointer To ${destination}

<p>Moves the pointer in incremental steps from the current pointer position to an absolute position or image template.</p>
<p>Embedded arguments:</p>
<ul>
<li>${destination}: Where to walk the pointer to. If ${destination}</li>
</ul>
<p>is a tuple (x, y) of integers, the pointer will walk to the absolute position given by the tuple. Otherwise, if ${destination} is the path of an image template file, the pointer will walk to the center of the first matching template region. ${destination} can also be a string, and the pointer will move to the center of the found text.</p>
<ul>
<li>${step_distance} (optional): Size of each step, in pixels.</li>
</ul>
<p>Default is 16.</p>
<ul>
<li>${delay} (optional): Time to sleep after each step, in seconds.</li>
</ul>
<p>Default is 0.01.</p>
<p>Return: Absolute position of the pointer after the walk, as a tuple (x, y) of integers.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| step_distance |  | 16 | POSITIONAL_OR_NAMED | No |
| delay |  | 0.01 | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Walk Pointer To (${x}, ${y})

<p>Move the pointer in incremental steps from the current pointer position to an absolute position.</p>
<p>Embedded arguments:</p>
<ul>
<li>${x}: Integer absolute x-coordinate to walk the pointer to.</li>
<li>${y}: Integer absolute y-coordinate to walk the pointer to.</li>
<li>${step_distance} (optional): Size of each step, in pixels.</li>
</ul>
<p>Default is 16.</p>
<ul>
<li>${delay} (optional): Time to sleep after each step, in seconds.</li>
</ul>
<p>Default is 0.01.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| step_distance |  | 16 | POSITIONAL_OR_NAMED | No |
| delay |  | 0.01 | POSITIONAL_OR_NAMED | No |
<hr style="border:1px solid grey">

### Walk Pointer To Proportional (${x}, ${y})

<p>Move the pointer in incremental steps from the current pointer position to a destination position given as proportions to the size of the display output.</p>
<p>Embedded arguments:</p>
<ul>
<li>${x}: Output-relative x-coordinate to move the pointer to.</li>
</ul>
<p>It must be in the range 0..1, where 0 represents the left edge, and 1 represents the right edge of the output.</p>
<ul>
<li>${y}: Output-relative y-coordinate to move the pointer to.</li>
</ul>
<p>It must be in the range 0..1, where 0 represents the top edge, and 1 represents the bottom edge of the output.</p>
<ul>
<li>${step_distance} (optional): maximum distance to move per step horizontally, 0 &lt; step_distance &lt;= 1</li>
<li>${delay} (optional): Time to sleep after each step, in seconds.</li>
</ul>
<p>Default is 0.01.</p>
<p>Return: Absolute position of the pointer after the walk, as a tuple (x, y) of integers.</p>

#### Positional and named arguments

| Name | Type | Default Value | Kind | Required |
| --- | --- | --- | --- | --- |
| step_distance |  | 0.01 | POSITIONAL_OR_NAMED | No |
| delay |  | 0.01 | POSITIONAL_OR_NAMED | No |
