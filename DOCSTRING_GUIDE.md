# Google-Style Docstring Guide for CurveEditor

This guide defines the documentation standards for the CurveEditor project using Google-style docstrings.

## Module Docstrings

Every Python file should start with a module-level docstring:

```python
"""Brief one-line description of the module.

Longer description of the module's purpose, functionality, and any
important notes about its usage or implementation details.

Example:
    Basic usage example if applicable::

        from module import SomeClass
        instance = SomeClass()
        result = instance.method()

Attributes:
    MODULE_CONSTANT (type): Description of module-level constants.
    module_variable (type): Description of module-level variables.

Todo:
    * Future improvements or known issues
    * Another todo item

"""
```

## Class Docstrings

```python
class ExampleClass:
    """Brief one-line description of the class.

    Longer description of the class purpose and behavior.
    Include any important implementation details or usage notes.

    Attributes:
        public_attribute (type): Description of the attribute.
        another_attribute (type): Description of another attribute.

    Example:
        Basic usage example::

            instance = ExampleClass(param1="value")
            result = instance.method()

    Note:
        Any important notes about the class behavior or limitations.

    """
```

## Function/Method Docstrings

```python
def example_function(param1: str, param2: int = 0) -> bool:
    """Brief one-line description of the function.

    Longer description if needed, explaining the function's behavior,
    algorithm, or any important details.

    Args:
        param1: Description of the first parameter.
        param2: Description of the second parameter. Defaults to 0.

    Returns:
        Description of the return value, including type and meaning.
        For complex returns, use multiple lines:

        A tuple containing:
            - item1 (type): Description
            - item2 (type): Description

    Raises:
        ValueError: Description of when this error is raised.
        TypeError: Description of when this error is raised.

    Example:
        Usage example::

            result = example_function("test", 42)
            if result:
                print("Success!")

    Note:
        Any important notes about the function.

    """
```

## Protocol Docstrings

```python
class ServiceProtocol(Protocol):
    """Protocol defining the interface for service implementations.

    This protocol ensures that all service implementations provide
    the required methods and attributes for the application.

    Required Methods:
        method_name: Brief description of what implementers must provide.

    Required Attributes:
        attribute_name (type): Description of required attribute.

    """
```

## Special Sections

### Args Section
- List each parameter on its own line
- Include type information in the function signature, not in the docstring
- Describe default values in the description

### Returns Section
- Describe what the function returns
- For None returns, simply write "None" or omit the section
- For complex returns, break down the structure

### Raises Section
- List each exception type that can be raised
- Include the conditions under which it's raised

### Example Section
- Provide practical usage examples
- Use `::` after "Example" for proper formatting
- Indent code blocks with 4 spaces

### Note Section
- Include important information about behavior
- Warnings about deprecated features
- Performance considerations

### Todo Section
- List planned improvements
- Known issues to be addressed
- Use asterisk (*) for bullet points

## Best Practices

1. **Be Concise**: The first line should be a brief summary that fits on one line.

2. **Be Complete**: Document all public APIs (classes, methods, functions).

3. **Be Consistent**: Use the same style throughout the project.

4. **Type Hints**: Use type annotations in signatures, not in docstrings.

5. **Examples**: Include examples for complex functionality.

6. **Update Documentation**: Keep docstrings updated when code changes.

7. **Private Members**: Optionally document private methods/attributes if complex.

8. **Property Docstrings**: Document properties like regular attributes:
   ```python
   @property
   def value(self) -> int:
       """The current value of the widget."""
       return self._value
   ```

9. **Static/Class Methods**: Document like regular methods but note their special nature if relevant.

10. **Inherited Methods**: Only document if behavior differs from parent class.
