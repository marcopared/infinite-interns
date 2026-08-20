from infinite_interns.graph.state import FactoryState


def test_factory_state_contains_refs_not_blobs() -> None:
    state = FactoryState(run_id="run_1", current_commit="abc", last_green_commit="abc")
    payload = state.model_dump()
    assert "logs" not in payload
    assert "source_code" not in payload
    assert payload["run_id"] == "run_1"
