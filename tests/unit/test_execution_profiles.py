import pytest
from acid_engine.level3.execution_profile import (
    LibraryProfile, CLIProfile, DesktopProfile,
    ServiceProfile, SaaSProfile, EmbeddedProfile,
)
from acid_engine.level3.interface.contract import InterfaceContract
from acid_engine.level2.identity import ContractId, Version


def make_iface():
    return InterfaceContract(
        contract_id=ContractId("test", "app"),
        version=Version(1,0,0),
        inputs={}, outputs={}, constraints={},
    )


def test_library_profile():
    artifact = LibraryProfile().build(make_iface())
    assert "Library artifact" in artifact

def test_cli_profile():
    artifact = CLIProfile().build(make_iface())
    assert "CLI artifact" in artifact

def test_all_profiles():
    for p in [DesktopProfile(), ServiceProfile(), SaaSProfile(), EmbeddedProfile()]:
        artifact = p.build(make_iface())
        assert isinstance(artifact, str) and len(artifact) > 0