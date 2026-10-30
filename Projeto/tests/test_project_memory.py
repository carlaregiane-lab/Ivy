import unittest

from ivy_lab.project_memory import (
    ensure_project_history,
    record_project_decision,
    record_project_event,
    render_project_decisions,
    render_project_history,
)


class ProjectMemoryTests(unittest.TestCase):
    def _legacy_project(self) -> dict:
        return {
            "id": "PRJ-001",
            "name": "Garra robótica",
            "created_at": "2026-08-09T14:00:00-03:00",
            "updated_at": "2026-08-09T15:00:00-03:00",
            "calculation_revision": 1,
            "calculation_report": {"project_id": "PRJ-001", "status": "parcial"},
            "concept_revision": 1,
            "concept_report": {
                "project_id": "PRJ-001",
                "status": "comparacao_preliminar",
            },
        }

    def test_legacy_state_is_preserved_without_inventing_events(self) -> None:
        project = self._legacy_project()

        ensure_project_history(project, timestamp="2026-08-09T16:00:00-03:00")

        self.assertEqual("ativado_em_projeto_existente", project["history_origin"])
        self.assertEqual([], project["history"])
        self.assertEqual(1, len(project["calculation_history"]))
        self.assertEqual(1, len(project["concept_history"]))
        self.assertTrue(project["calculation_history"][0]["legacy_snapshot"])
        self.assertTrue(project["concept_history"][0]["legacy_snapshot"])

    def test_events_receive_monotonic_project_revisions(self) -> None:
        project = self._legacy_project()

        first = record_project_event(
            project,
            "answers_updated",
            "Resposta 1 alterada.",
            {"changes": [{"question": 1, "before": None, "after": "caixa rígida"}]},
            timestamp="2026-08-09T16:01:00-03:00",
        )
        second = record_project_event(
            project,
            "calculation_saved",
            "Memória de cálculo revisão 2 guardada.",
            {"calculation_revision": 2, "status": "parcial"},
            timestamp="2026-08-09T16:02:00-03:00",
        )

        self.assertEqual(1, first.project_revision)
        self.assertEqual(2, second.project_revision)
        self.assertEqual("EVT-0001", first.id)
        self.assertEqual("EVT-0002", second.id)

    def test_legacy_cad_snapshot_is_preserved(self) -> None:
        project = self._legacy_project()
        project["cad_revision"] = 1
        project["cad_report"] = {
            "project_id": "PRJ-001",
            "status": "modelo_parametrico_preliminar",
        }

        ensure_project_history(project, timestamp="2026-08-09T16:00:00-03:00")
        rendered = render_project_history(project)

        self.assertEqual(1, len(project["cad_history"]))
        self.assertTrue(project["cad_history"][0]["legacy_snapshot"])
        self.assertIn("Modelos CAD preservados: 1", rendered)

    def test_decisions_have_identifier_reason_and_revision(self) -> None:
        project = self._legacy_project()

        decision, event = record_project_decision(
            project,
            "Detalhar o conceito de fuso",
            "obteve a maior pontuação preliminar",
            timestamp="2026-08-09T16:03:00-03:00",
        )
        rendered = render_project_decisions(project)

        self.assertEqual("DEC-001", decision.id)
        self.assertEqual(event.project_revision, decision.project_revision)
        self.assertIn("Detalhar o conceito de fuso", rendered)
        self.assertIn("maior pontuação preliminar", rendered)

    def test_history_renderer_shows_changes_and_artifact_counts(self) -> None:
        project = self._legacy_project()
        record_project_event(
            project,
            "answers_updated",
            "Resposta 1 alterada.",
            {
                "changes": [
                    {"question": 1, "before": "caixa lisa", "after": "caixa texturizada"}
                ]
            },
            timestamp="2026-08-09T16:04:00-03:00",
        )

        rendered = render_project_history(project)

        self.assertIn("Revisão atual do projeto: 1", rendered)
        self.assertIn("caixa lisa -> caixa texturizada", rendered)
        self.assertIn("Memórias de cálculo preservadas: 1", rendered)
        self.assertIn("Comparações de conceitos preservadas: 1", rendered)


if __name__ == "__main__":
    unittest.main()
