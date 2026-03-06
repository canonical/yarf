# Interactive

<p>A class for the user to interact with the console and perform various tasks. The keywords under this class is exclusive to interactive mode.</p>
<p>Attributes: ROBOT_LIBRARY_SCOPE: Scope of the library. ROBOT_LISTENER_API_VERSION: API version for Robot Framework listeners.</p>

- **Type**: LIBRARY
- **Scope**: GLOBAL

## Keywords

### Grab Templates

<p>Grabs a screenshot and allows the user to crop and save templates.</p>
<p>Args: *names: Names of the templates to be cropped, skip this variable if there is no template names</p>
<p>Raises: ValueError: If the screenshot could not be grabbed.</p>

#### Positional and named arguments

| Name  | Type   | Default Value | Kind           | Required |
| ----- | ------ | ------------- | -------------- | -------- |
| names | string |               | VAR_POSITIONAL | No       |
