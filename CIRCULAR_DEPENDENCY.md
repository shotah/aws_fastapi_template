# Handling Circular Dependencies with Pydantic Models

## The Problem

When building Lambda functions with helper modules that return Pydantic models, you can encounter circular dependency issues:

```
helper.py → imports models.py (to return HelperModuleTest)
models.py → defines HelperModuleTest
app.py    → imports both helper.py and models.py
```

If `helper.py` imports from `models.py` at the module level, Python will fail to import when both modules need each other.

---

## The Solution: TYPE_CHECKING + Runtime Imports

### Pattern Overview

Use Python's `TYPE_CHECKING` constant combined with runtime imports inside functions:

1. **TYPE_CHECKING import** - For type hints only (evaluated by type checkers, not at runtime)
2. **Runtime import** - Inside the function that needs the model

---

## Example Implementation

### `src/models.py` - Define Your Models
```python
from pydantic import BaseModel

class HelperModuleTest(BaseModel):
    """Helper module test result."""
    greeting: str
    source: str
    status: str
```

### `src/helper.py` - Use TYPE_CHECKING Pattern

```python
from typing import TYPE_CHECKING

# TYPE_CHECKING is False at runtime, True during type checking
# This prevents circular imports while maintaining type safety
if TYPE_CHECKING:
    from models import HelperModuleTest  # type: ignore


class GreetingService:
    """Service class that returns Pydantic models."""

    def get_greeting_message(self, name: str = "world") -> "HelperModuleTest":
        """
        Generate a greeting message as a Pydantic model.

        Note: Return type uses string forward reference "HelperModuleTest"
        """
        # Import at runtime inside the function to avoid circular dependency
        from models import HelperModuleTest

        return HelperModuleTest(
            greeting=f"Hello, {name}!",
            source="helper module",
            status="success",
        )
```

### `src/app.py` - Use Both Modules Freely

```python
from helper import GreetingService
from models import HelloResponse, HelperModuleTest

@app.get("/hello-class")
def hello_with_class():
    # Service returns a Pydantic model directly - no circular import!
    greeting_service = GreetingService()
    greeting_model = greeting_service.get_greeting_message("Lambda")

    response = HelloResponse(
        message="hello world",
        helper_module_test=greeting_model,  # Already a Pydantic model!
    )

    return response.model_dump()
```

---

## How It Works

### 1. TYPE_CHECKING Constant

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import HelperModuleTest  # Only imported during type checking
```

- **`TYPE_CHECKING`** is `False` at runtime
- **Type checkers** (mypy, pyright) treat it as `True`
- The import inside `if TYPE_CHECKING` is **only seen by type checkers**, not Python at runtime

### 2. Forward Reference (String Type Hint)

```python
def get_greeting_message(self, name: str = "world") -> "HelperModuleTest":
    #                                                    ↑ String forward reference
```

- String type hints aren't evaluated at module load time
- Type checkers understand them thanks to the TYPE_CHECKING import
- Python ignores them at runtime

### 3. Runtime Import (Inside Function)

```python
def get_greeting_message(self, name: str = "world") -> "HelperModuleTest":
    from models import HelperModuleTest  # ← Import when function is called

    return HelperModuleTest(...)
```

- Import happens **when the function runs**, not when the module loads
- By this time, both modules are fully loaded
- No circular dependency!

---

## Alternative Solutions

### Alternative 1: Shared Models File

Move shared models to a separate file that nothing imports from:

```
src/
├── app.py          # Imports helper.py and models.py
├── helper.py       # Imports shared_models.py
└── models.py       # Imports shared_models.py
└── shared_models.py  # No imports from other modules
```

**Pros:** Clean architecture
**Cons:** More files to manage

### Alternative 2: Return Dict, Validate in App

Helper returns `dict`, app layer creates Pydantic model:

```python
# helper.py - No Pydantic imports
def get_greeting_message(name: str) -> dict:
    return {"greeting": f"Hello, {name}!", ...}

# app.py - Convert to Pydantic
from models import HelperModuleTest

greeting_data = get_greeting_message("Lambda")
greeting_model = HelperModuleTest(**greeting_data)
```

**Pros:** Simple, no circular dependency
**Cons:** Validation happens late, helper returns untyped dicts

### Alternative 3: Protocol/Abstract Base Class

Define interface without importing concrete models:

```python
# protocols.py
from typing import Protocol

class GreetingResult(Protocol):
    greeting: str
    source: str
    status: str

# helper.py
from protocols import GreetingResult

def get_greeting_message(name: str) -> GreetingResult:
    from models import HelperModuleTest
    return HelperModuleTest(...)
```

**Pros:** Type-safe interfaces
**Cons:** More complex, overkill for simple cases

---

## Comparison Matrix

| Solution | Type Safety | Complexity | When to Use |
|----------|-------------|------------|-------------|
| **TYPE_CHECKING + Runtime Import** | ✅ Full | ⭐ Low | Default choice, works everywhere |
| **Shared Models File** | ✅ Full | ⭐⭐ Medium | Large projects with clear boundaries |
| **Return Dict** | ⚠️ Partial | ⭐ Low | Simple helpers, validation not critical |
| **Protocol/ABC** | ✅ Full | ⭐⭐⭐ High | Complex systems with interface contracts |

---

## Testing the Pattern

```python
# tests/test_helper.py
from src.helper import GreetingService
from src.models import HelperModuleTest

def test_greeting_service_returns_model():
    """Test that GreetingService returns a valid Pydantic model."""
    service = GreetingService()
    result = service.get_greeting_message("Test")

    # Verify it's the correct type
    assert isinstance(result, HelperModuleTest)

    # Verify Pydantic validation worked
    assert result.greeting == "Hello, Test!"
    assert result.source == "helper module"
    assert result.status == "success"
```

---

## Common Pitfalls

### ❌ Don't: Module-Level Import

```python
# helper.py - WRONG!
from models import HelperModuleTest  # Circular import!

class GreetingService:
    def get_greeting_message(self) -> HelperModuleTest:
        return HelperModuleTest(...)
```

### ❌ Don't: Forget Forward Reference

```python
# helper.py - WRONG!
if TYPE_CHECKING:
    from models import HelperModuleTest

class GreetingService:
    def get_greeting_message(self) -> HelperModuleTest:  # NameError at runtime!
        #                                ↑ Should be "HelperModuleTest" (string)
        ...
```

### ✅ Do: TYPE_CHECKING + String Type + Runtime Import

```python
# helper.py - CORRECT!
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models import HelperModuleTest  # type: ignore

class GreetingService:
    def get_greeting_message(self) -> "HelperModuleTest":  # String!
        from models import HelperModuleTest  # Runtime import
        return HelperModuleTest(...)
```

---

## Key Takeaways

1. **Use TYPE_CHECKING imports** for type hints that would cause circular dependencies
2. **Use string forward references** for return types in function signatures
3. **Import at runtime** inside the function when you actually need the class
4. **Keep it simple** - this pattern is lightweight and doesn't require architectural changes
5. **Test thoroughly** - ensure both type checking and runtime behavior work correctly

---

## Example Endpoint

Try the example endpoint that demonstrates this pattern:

```bash
# Start local server
make start

# Test the endpoint
curl http://localhost:3000/hello-class
```

**Expected Response:**
```json
{
  "message": "hello world from class",
  "helper_module_test": {
    "greeting": "Hello, Lambda Class!",
    "source": "helper module",
    "status": "success"
  },
  "multiplication_result": 64
}
```

---

*Last Updated: October 30, 2025*
