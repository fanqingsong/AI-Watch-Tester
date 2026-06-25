# SOLID Refactoring Plan for AAT Codebase

## Executive Summary

This comprehensive refactoring plan addresses SOLID principle violations found in the AAT (AI Auto Tester) codebase. The analysis reveals critical issues primarily in the `StepExecutor` class (2,610 lines, 45 methods) and registry-based plugin system.

## Analysis Summary

### Critical SOLID Violations Found

**Single Responsibility Principle (SRP)**
- `StepExecutor` class violates SRP with 45 methods handling: execution, action dispatch, screenshot management, session handling, iframe management, OCR processing, coordinate parsing, learning recording, and UI interaction
- `prompts.py` mixes prompt templates with presentation logic

**Open/Closed Principle (OCP)**  
- Hard-coded action dispatch in `StepExecutor._dispatch_action` (120+ lines of if/elif chains)
- Static registry dictionaries require modification for new plugins
- Hard-coded screenshot mode logic, synonym dictionaries, and scroll shortcuts

**Liskov Substitution Principle (LSP)**
- `DesktopEngine.screenshot()` captures full OS screen vs `WebEngine` viewport only
- `DesktopEngine.move_mouse()` coordinate system incompatibility  
- `OllamaAdapter` inherits broken `verify_step()` default implementation
- `HybridMatcher` indistinguishable error states

**Interface Segregation Principle (ISP)**
- Fat interfaces forcing implementations to depend on unused methods
- Missing capability-based interfaces for optional features

**Dependency Inversion Principle (DIP)**
- Direct registry dependencies in CLI commands
- Hard-coded library dependencies (OpenCV, Anthropic SDK)
- Concrete class coupling in `StepExecutor` constructor
- No factory patterns for complex object creation

## Refactoring Strategy

### Phase 1: SRP - Extract Action Handlers (HIGH PRIORITY)

**Target**: `StepExecutor` class reduction from 2,610 lines to ~800 lines

#### 1.1 Create Action Handler Interface
```python
# src/aat/engine/action_handlers/base.py
from abc import ABC, abstractmethod
from aat.core import StepConfig, MatchResult
from aat.engine.executor import StepExecutor

class ActionHandler(ABC):
    """Base class for action-specific handlers."""
    
    @abstractmethod
    async def execute(self, step: StepConfig, executor: StepExecutor) -> MatchResult | None:
        """Execute the action and return match result if applicable."""
        pass
    
    @abstractmethod
    def validates_action(self, action: str) -> bool:
        """Check if this handler handles the given action type."""
        pass
```

#### 1.2 Implement Concrete Action Handlers
```python
# src/aat/engine/action_handlers/navigate_handler.py
class NavigateHandler(ActionHandler):
    def validates_action(self, action: str) -> bool:
        return action == ActionType.NAVIGATE
    
    async def execute(self, step: StepConfig, executor: StepExecutor) -> MatchResult | None:
        await executor._engine.navigate(step.value or "")
        await executor._wait_for_load_state("load")
        return None

# src/aat/engine/action_handlers/click_handler.py  
class ClickAtHandler(ActionHandler):
    def validates_action(self, action: str) -> bool:
        return action == ActionType.CLICK_AT
    
    async def execute(self, step: StepConfig, executor: StepExecutor) -> MatchResult | None:
        await executor._do_click_screen(step)
        return None

# Similar handlers for: find_and_click, find_and_type, type_text, press_key, 
# assert, wait, screenshot, save_session, load_session, get_text, etc.
```

#### 1.3 Create Handler Registry
```python
# src/aat/engine/action_handlers/__init__.py
from typing import Dict

class ActionHandlerRegistry:
    _handlers: Dict[str, ActionHandler] = {}
    
    @classmethod
    def register(cls, handler: ActionHandler) -> None:
        for action in ActionType.ALL:
            if handler.validates_action(action):
                cls._handlers[action] = handler
    
    @classmethod  
    def get_handler(cls, action: str) -> ActionHandler | None:
        return cls._handlers.get(action)

# Auto-register all handlers
for handler_cls in [NavigateHandler, ClickAtHandler, FindAndClickHandler, ...]:
    ActionHandlerRegistry.register(handler_cls())
```

#### 1.4 Refactor StepExecutor
```python
# In StepExecutor._dispatch_action (reduce from 120+ lines to ~10 lines)
async def _dispatch_action(self, step: StepConfig) -> MatchResult | None:
    handler = ActionHandlerRegistry.get_handler(step.action)
    if handler is None:
        raise ValueError(f"No handler for action: {step.action}")
    return await handler.execute(step, self)
```

**Expected Impact**: 
- Reduce `StepExecutor` from 2,610 to ~800 lines
- Each handler ~100-200 lines focused on single action
- New actions added via new handlers without modifying executor

### Phase 2: OCP - Command Pattern & Extensibility (HIGH PRIORITY)

#### 2.1 Plugin Registration System
```python
# src/aat/core/plugin_registry.py
from typing import TypeVar, Type, Dict, Callable

T = TypeVar('T')

class PluginRegistry:
    """Generic plugin registry with registration decorator."""
    
    def __init__(self) -> None:
        self._plugins: Dict[str, Type] = {}
    
    def register(self, name: str) -> Callable:
        """Decorator for plugin registration."""
        def decorator(plugin_class: Type) -> Type:
            self._plugins[name] = plugin_class
            return plugin_class
        return decorator
    
    def get(self, name: str) -> Type | None:
        return self._plugins.get(name)
    
    def list_all(self) -> Dict[str, Type]:
        return self._plugins.copy()

# Usage:
adapter_registry = PluginRegistry()
engine_registry = PluginRegistry()  
matcher_registry = PluginRegistry()
reporter_registry = PluginRegistry()

# In adapter files:
@adapter_registry.register("claude")
class ClaudeAdapter(AIAdapter):
    ...

@adapter_registry.register("gemini") 
class GeminiAdapter(AIAdapter):
    ...
```

#### 2.2 Strategy Pattern for Screenshot Modes
```python
# src/aat/engine/screenshot_strategies/base.py
class ScreenshotStrategy(ABC):
    @abstractmethod
    async def should_save_before(self, step: StepConfig) -> bool:
        pass
    
    @abstractmethod
    async def should_save_after(self, step: StepConfig, result: StepResult) -> bool:
        pass

# src/aat/engine/screenshot_strategies/on_failure.py
class OnFailureStrategy(ScreenshotStrategy):
    async def should_save_before(self, step: StepConfig) -> bool:
        return False
    
    async def should_save_after(self, step: StepConfig, result: StepResult) -> bool:
        return result.status == StepStatus.FAILED

# src/aat/engine/screenshot_strategies/all.py
class AllStrategy(ScreenshotStrategy):
    async def should_save_before(self, step: StepConfig) -> bool:
        return True
    
    async def should_save_after(self, step: StepConfig, result: StepResult) -> bool:
        return True

# Registry-based strategy selection
SCREENSHOT_STRATEGIES: Dict[str, ScreenshotStrategy] = {
    "on-failure": OnFailureStrategy(),
    "all": AllStrategy(),
    "before-after": BeforeAfterStrategy(),
}
```

#### 2.3 External Configuration for Extensibility
```python
# config/synonyms.yaml
email:
  - e-mail
  - email address  
  - mail
password:
  - pass
  - pwd
  - passphrase

# config/scroll_shortcuts.yaml
down:
  x: 640
  y: 360
  delta: 500
up:
  x: 640
  y: 360
  delta: -500

# Load from config instead of hard-coded dicts
```

### Phase 3: LSP - Substitution Safety (HIGH PRIORITY)

#### 3.1 Fix Engine Contract Violations
```python
# src/aat/engine/base.py
from enum import Enum

class EngineCapability(Enum):
    VIEWPORT_SCREENSHOT = "viewport_screenshot"
    FULL_SCREEN_SCREENSHOT = "full_screen_screenshot"
    VIEWPORT_COORDINATES = "viewport_coordinates"
    SCREEN_COORDINATES = "screen_coordinates"

class BaseEngine(ABC):
    @abstractmethod
    def get_capabilities(self) -> Set[EngineCapability]:
        """Return supported capabilities for this engine."""
        pass
    
    @abstractmethod
    async def screenshot(self) -> bytes:
        """Capture screenshot. Size depends on capabilities."""
        pass

# src/aat/engine/web.py
class WebEngine(BaseEngine):
    def get_capabilities(self) -> Set[EngineCapability]:
        return {EngineCapability.VIEWPORT_SCREENSHOT, 
                EngineCapability.VIEWPORT_COORDINATES}

# src/aat/engine/desktop.py  
class DesktopEngine(BaseEngine):
    def get_capabilities(self) -> Set[EngineCapability]:
        return {EngineCapability.FULL_SCREEN_SCREENSHOT,
                EngineCapability.SCREEN_COORDINATES}
```

#### 3.2 Add AI Adapter Capability Flags
```python
# src/aat/adapters/base.py
class AIAdapter(ABC):
    @property
    def supports_vision(self) -> bool:
        """Whether this adapter supports vision/image analysis."""
        return False
    
    @property
    def supports_step_verify(self) -> bool:
        """Whether this adapter supports step verification."""
        return False
    
    async def verify_step(self, screenshot: bytes, step: StepConfig) -> dict:
        """Verify step execution from screenshot. Requires supports_vision=True."""
        if not self.supports_vision:
            raise NotImplementedError(f"{self.__class__.__name__} does not support vision")
        # Default implementation for vision-capable adapters
        pass

# src/aat/adapters/claude.py
class ClaudeAdapter(AIAdapter):
    @property
    def supports_vision(self) -> bool:
        return True
    
    @property
    def supports_step_verify(self) -> bool:
        return True

# src/aat/adapters/ollama.py  
class OllamaAdapter(AIAdapter):
    @property
    def supports_vision(self) -> bool:
        return False  # Local models typically don't support vision well
```

#### 3.3 Fix HybridMatcher Error States
```python
# src/aat/core/models.py
@dataclass
class MatchResult:
    status: Literal["matched", "not_found", "error", "misconfigured"]
    confidence: float = 0.0
    region: ScreenRegion | None = None
    error_message: str = ""

# Usage in HybridMatcher:
if not self.template_matcher or not self.ocr_matcher:
    return MatchResult(status="misconfigured", 
                       error_message="Both template and OCR matchers required")
```

### Phase 4: ISP - Interface Segregation (MEDIUM PRIORITY)

#### 4.1 Split Fat Interfaces
```python
# Before - Fat interface
class BaseEngine(ABC):
    async def navigate(self, url: str) -> None: ...
    async def screenshot(self) -> bytes: ...  
    async def find_element(self, selector: str) -> Any: ...
    async def click(self, x: int, y: int) -> None: ...
    async def type_text(self, text: str) -> None: ...
    async def get_text(self) -> str: ...

# After - Segregated interfaces
class Navigatable(ABC):
    async def navigate(self, url: str) -> None: pass

class Screenshotable(ABC):
    async def screenshot(self) -> bytes: pass

class Interactive(ABC):
    async def click(self, x: int, y: int) -> None: pass
    async def type_text(self, text: str) -> None: pass

class Searchable(ABC):
    async def find_element(self, selector: str) -> Any: pass

class TextExtractable(ABC):
    async def get_text(self) -> str: pass

# Engines compose relevant interfaces
class WebEngine(Navigatable, Screenshotable, Interactive, Searchable, TextExtractable):
    ...

class DesktopEngine(Navigatable, Screenshotable, Interactive, TextExtractable):
    pass  # Desktop doesn't support Searchable (no element selector)
```

#### 4.2 Capability-Based Interfaces
```python
# src/aat/engine/capabilities.py
class VisionEnabled(ABC):
    """Mixins for engines that support computer vision operations."""
    pass

class SessionManagement(ABC):
    """Mixins for engines that support session save/load."""
    async def save_session(self, path: Path) -> None: pass
    async def load_session(self, path: Path) -> None: pass

class FrameSupport(ABC):
    """Mixins for engines that support iframe/frame navigation."""
    async def get_frames(self) -> list[Any]: pass
    async def switch_to_frame(self, frame: Any) -> None: pass

# Usage in engines
class WebEngine(VisionEnabled, SessionManagement, FrameSupport):
    """Full-featured web engine with all capabilities."""
    pass
```

### Phase 5: DIP - Dependency Inversion (HIGH PRIORITY)

#### 5.1 Factory Pattern Implementation
```python
# src/aat/core/factories.py
class EngineFactory(ABC):
    @abstractmethod
    def create_engine(self, config: EngineConfig) -> BaseEngine:
        pass

class AIAdapterFactory(ABC):
    @abstractmethod
    def create_adapter(self, config: AIConfig) -> AIAdapter:
        pass

# Concrete factories
class PlaywrightEngineFactory(EngineFactory):
    def create_engine(self, config: EngineConfig) -> BaseEngine:
        return WebEngine(config)

class PyAutoGUIEngineFactory(EngineFactory):
    def create_engine(self, config: EngineConfig) -> BaseEngine:
        return DesktopEngine(config)

# Usage in CLI
def run_command(engine_factory: EngineFactory, adapter_factory: AIAdapterFactory, ...):
    engine = engine_factory.create_engine(config.engine)
    adapter = adapter_factory.create_adapter(config.ai)
```

#### 5.2 Library Abstractions
```python
# src/aat/ai/client.py (abstraction for AI services)
class AIClient(ABC):
    @abstractmethod
    async def generate(self, messages: list[dict]) -> str:
        pass
    
    @abstractmethod
    async def generate_vision(self, image: bytes, prompt: str) -> str:
        pass

# src/aat/ai/anthropic_client.py
class AnthropicAIClient(AIClient):
    def __init__(self, api_key: str):
        self._client = AsyncAnthropic(api_key=api_key)
    
    async def generate(self, messages: list[dict]) -> str:
        # Anthropic-specific implementation
        pass
    
    async def generate_vision(self, image: bytes, prompt: str) -> str:
        # Anthropic vision implementation
        pass

# src/aat/adapters/claude.py (refactored)
class ClaudeAdapter(AIAdapter):
    def __init__(self, config: AIConfig, client: AIClient | None = None):
        self._client = client or AnthropicAIClient(config.api_key)
```

#### 5.3 Image Processing Abstraction
```python
# src/aat/vision/processor.py
class ImageProcessor(ABC):
    @abstractmethod
    def match_template(self, template: bytes, screenshot: bytes) -> MatchResult | None:
        pass
    
    @abstractmethod
    def preprocess(self, image: bytes, method: str) -> bytes:
        pass

# src/aat/vision/opencv_processor.py
class OpenCVProcessor(ImageProcessor):
    def match_template(self, template: bytes, screenshot: bytes) -> MatchResult | None:
        # OpenCV implementation
        pass
    
    def preprocess(self, image: bytes, method: str) -> bytes:
        # OpenCV preprocessing
        pass

# Usage in matchers
class TemplateMatcher(BaseMatcher):
    def __init__(self, config: MatchingConfig, processor: ImageProcessor | None = None):
        self._processor = processor or OpenCVProcessor()
```

## Implementation Timeline

### Sprint 1: Critical SRP + OCP (Week 1-2)
1. Extract action handlers from `StepExecutor`
2. Implement action handler registry  
3. Refactor `_dispatch_action` method
4. Create plugin registration system
5. Implement screenshot strategy pattern

**Expected Results**: `StepExecutor` reduced to ~800 lines, extensible plugin system

### Sprint 2: LSP + ISP (Week 3-4)
1. Add engine capability detection
2. Fix `DesktopEngine` contract violations  
3. Add AI adapter capability flags
4. Split fat interfaces into focused ones
5. Implement capability-based mixins

**Expected Results**: Safe substitution, segregated interfaces, explicit capabilities

### Sprint 3: DIP + Integration (Week 5-6)
1. Implement factory patterns
2. Create library abstractions (AI client, image processor)
3. Refactor CLI to use factories
4. Update configuration loading
5. Comprehensive testing

**Expected Results**: Proper dependency inversion, testable architecture

## Testing Strategy

### Unit Tests
- Test each action handler independently
- Test factory pattern implementations  
- Test capability detection
- Test strategy pattern selections

### Integration Tests
- Test handler registry functionality
- Test plugin loading and registration
- Test engine substitution safety
- Test factory-based object creation

### Regression Tests
- Ensure existing functionality preserved
- Test all existing scenarios pass
- Performance benchmarks maintained

## Risk Assessment

### Low Risk
- Action handler extraction (isolated changes)
- Screenshot strategy pattern (local impact)
- Plugin registration (additive feature)

### Medium Risk  
- Factory pattern implementation (affects CLI)
- Interface segregation (requires interface updates)
- Library abstractions (dependency injection changes)

### Mitigation Strategies
- Comprehensive test coverage before changes
- Incremental refactoring with continuous testing
- Feature flags for gradual rollout
- Backward compatibility maintenance where possible

## Success Metrics

1. **Code Size**: `StepExecutor` reduced from 2,610 to <1,000 lines
2. **Complexity**: No class with >20 methods or >800 lines  
3. **Extensibility**: New plugins added without modifying core code
4. **Testability**: All components testable in isolation
5. **Performance**: No regression in execution speed
6. **Coverage**: Maintain >80% test coverage

## Conclusion

This SOLID refactoring plan addresses the core architectural issues in the AAT codebase. The phased approach allows incremental improvements while maintaining system stability. The focus on extracting action handlers from the oversized `StepExecutor` class will have the most immediate impact on maintainability and extensibility.

The combination of SRP (extraction), OCP (patterns), LSP (capabilities), ISP (segregation), and DIP (abstractions) will transform the codebase into a truly maintainable, extensible, and testable architecture suitable for long-term evolution.