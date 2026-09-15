from acid_engine.level0.ai_reference import AIReferenceView
from acid_engine.level0.human_readable import HumanReadableView
from acid_engine.level0.live_code import LiveCodeView
from acid_engine.level2.identity import ContractId
from acid_engine.level2.specification import Specification
from acid_engine.level3.graph.model import DependencyGraph
from acid_engine.level3.script.module import ScriptModule


def test_live_code_view():
    view = LiveCodeView(lambda x: x + 1)
    assert view(5) == 6

def test_human_readable_script():
    script = ScriptModule(
        contract_id=ContractId("test", "demo"),
        version=..., input_type="int", output_type="int",
        specification=Specification(), implementation=lambda x: x, name="demo"
    )
    hr = HumanReadableView()
    text = hr.render(script)
    assert "Specification" in text
    assert "Input: int" in text
    assert "Implementation" in text

def test_human_readable_graph():
    g = DependencyGraph()
    g.add_node("A")
    g.add_node("B")
    g.add_edge("A", "B")
    hr = HumanReadableView()
    text = hr.render(g)
    assert "A → B" in text

def test_ai_reference_view():
    ref = AIReferenceView(ContractId("ns", "name"))
    desc = ref.describe()
    assert desc["contract_id"] == "ns/name"

def test_in_memory_data_plane():
    from acid_engine.level1.data_plane import InMemoryDataPlane
    dp = InMemoryDataPlane()
    dp.store("k", b"val")
    assert dp.exists("k")
    assert dp.load("k") == b"val"