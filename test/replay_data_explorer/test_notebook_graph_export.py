import json
from pathlib import Path
from types import SimpleNamespace


NOTEBOOK_PATH = (
    Path(__file__).parents[2]
    / "src"
    / "replay_data_explorer"
    / "replay_data_explorer.ipynb"
)


class RecordingGraphExporter:
    def __init__(self) -> None:
        self.saved: list[tuple[object, str]] = []

    def save_as_png(self, figure: object, graph_name: str) -> None:
        self.saved.append((figure, graph_name))


def get_export_cell_source() -> str:
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        if (
            "config.graph_export_config.enable_png_export" in source
            and "_exportable_graphs_deferred.items()" in source
        ):
            return source
    raise AssertionError("Notebook graph export cell was not found")


def test_notebook_skips_deferred_graph_creation_when_png_export_is_disabled() -> None:
    exporter = RecordingGraphExporter()

    def fail_if_called() -> None:
        raise AssertionError("Deferred graph should not be created when export is disabled")

    namespace = {
        "config": SimpleNamespace(
            graph_export_config=SimpleNamespace(enable_png_export=False)
        ),
        "_exportable_graphs_deferred": {
            "deferred": (fail_if_called, [], {}),
        },
        "_exportable_graphs": {},
        "graph_exporter": exporter,
    }

    exec(compile(get_export_cell_source(), "notebook-export-cell", "exec"), namespace)

    assert exporter.saved == []


def test_notebook_preserves_exports_when_png_export_is_enabled() -> None:
    exporter = RecordingGraphExporter()
    namespace = {
        "config": SimpleNamespace(
            graph_export_config=SimpleNamespace(enable_png_export=True)
        ),
        "_exportable_graphs_deferred": {
            "deferred": (lambda: "created", [], {}),
        },
        "_exportable_graphs": {
            "existing": "kept",
        },
        "graph_exporter": exporter,
    }

    exec(compile(get_export_cell_source(), "notebook-export-cell", "exec"), namespace)

    assert exporter.saved == [("created", "deferred"), ("kept", "existing")]
