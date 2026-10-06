import pytest

from packages.domain.models import ToolDefinition, ToolRisk
from packages.tools.registry import ToolAlreadyRegisteredError, ToolNotFoundError, ToolRegistry


def make_tool(tool_id="browser_click", risk=ToolRisk.LOW):
    return ToolDefinition(
        tool_id=tool_id,
        name=tool_id.replace("_", " ").title(),
        description="Test tool",
        input_schema={},
        output_schema={},
        risk_level=risk,
    )


def test_register_and_get_tool():
    registry = ToolRegistry()
    tool = make_tool()
    registry.register(tool)
    assert registry.get("browser_click") == tool


def test_duplicate_tool_registration_is_rejected():
    registry = ToolRegistry([make_tool()])
    with pytest.raises(ToolAlreadyRegisteredError):
        registry.register(make_tool())


def test_missing_tool_is_rejected():
    registry = ToolRegistry()
    with pytest.raises(ToolNotFoundError):
        registry.get("does_not_exist")


def test_registry_listing_is_read_only():
    registry = ToolRegistry([make_tool(), make_tool("ocr_extract")])
    assert [tool.tool_id for tool in registry.list()] == ["browser_click", "ocr_extract"]
