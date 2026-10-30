import tempfile
import unittest
from pathlib import Path

from ivy_lab.assistant import IvyAssistant


class IvyAssistantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.memory_path = Path(self.temporary.name) / "ivy_memory.json"
        self.assistant = IvyAssistant(mode="demo", memory_path=self.memory_path)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _prepare_advanced_project(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica elétrica de dois dedos para caixas "
            "plásticas entre 40 e 90 mm de largura, com massa máxima de 1,5 kg, elevá-las "
            "30 cm em até 2 segundos, realizar 12 ciclos por minuto, com fonte de 12 V, "
            "estrutura em PETG, orçamento de R$ 600 e trabalho próximo a pessoas."
        )
        self.assistant.respond(
            "A resposta 3 é a fonte fornece 10 A continuamente e 15 A de pico; "
            "a resposta 4 é opera 8 horas por dia; "
            "a resposta 5 é coeficiente de atrito 0,4; "
            "a resposta 6 é fator de segurança 2,5."
        )
        self.assistant.respond("Faça os cálculos do projeto.")

    def test_creator_introduction_is_conversation_not_project(self) -> None:
        reply = self.assistant.respond("Olá Ivy, eu sou seu criador. Prazer em conhecer você.")

        self.assertIn("Vou lembrar que você criou a Ivy", reply.text)
        self.assertNotIn("BRIEFING DE REQUISITOS", reply.text)
        self.assertTrue(self.memory_path.exists())

    def test_task_is_saved_and_listed(self) -> None:
        added = self.assistant.respond("/tarefa revisar o projeto da garra")
        listed = self.assistant.respond("/tarefas")

        self.assertIn("Tarefa 1 adicionada", added.text)
        self.assertIn("revisar o projeto da garra", listed.text)

    def test_note_is_saved(self) -> None:
        reply = self.assistant.respond("/nota usar uma carga de referência de 500 g")

        self.assertIn("Anotado localmente", reply.text)
        self.assertIn("500 g", self.assistant.respond("/notas").text)

    def test_project_command_calls_engineering_module(self) -> None:
        reply = self.assistant.respond("/projeto garra robótica para levantar 500 gramas")

        self.assertIn("BRIEFING DE REQUISITOS", reply.text)
        self.assertIn("0,5 kg", reply.text)
        self.assertIn("PRJ-001", reply.text)

    def test_natural_language_creates_project_without_command(self) -> None:
        reply = self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 500 gramas."
        )

        self.assertIn("BRIEFING DE REQUISITOS", reply.text)
        self.assertIn("0,5 kg", reply.text)
        self.assertIn("PRJ-001", reply.text)

    def test_project_is_persisted_and_recovered_after_restart(self) -> None:
        self.assistant.respond("/projeto garra robótica para levantar 500 gramas")

        restarted = IvyAssistant(mode="demo", memory_path=self.memory_path)
        summary = restarted.respond("/projeto atual")

        self.assertIn("PRJ-001", summary.text)
        self.assertIn("Garra robótica", summary.text)
        self.assertIn("0/", summary.text)

    def test_numbered_project_answers_are_saved(self) -> None:
        request = (
            "/projeto Preciso desenvolver uma garra robótica elétrica de dois dedos para "
            "caixas plásticas entre 40 e 90 mm de largura, com massa máxima de 1,5 kg, elevá-las "
            "30 cm em até 2 segundos, a 12 ciclos por minuto, com 12 V e PETG, "
            "próxima a pessoas."
        )
        self.assistant.respond(request)

        saved = self.assistant.respond(
            "/responder 1: 100 mm de altura, rígida e seca; 2: apenas a elevação"
        )
        summary = self.assistant.respond("/projeto atual")

        self.assertIn("Respostas 1, 2 guardadas", saved.text)
        self.assertIn("2/7 respondidas", summary.text)
        self.assertIn("100 mm de altura", summary.text)
        self.assertNotIn("1. Quais são", summary.text.split("PERGUNTAS PENDENTES")[-1])

    def test_natural_language_saves_numbered_answers(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 500 gramas."
        )

        saved = self.assistant.respond(
            "A resposta 1 é uma caixa rígida; a resposta 2 é abertura de 40 a 90 mm."
        )

        self.assertIn("Respostas 1, 2 guardadas", saved.text)

    def test_invalid_project_answer_number_is_rejected(self) -> None:
        self.assistant.respond("/projeto garra robótica para levantar 500 gramas")

        reply = self.assistant.respond("/responder 99: resposta inválida")

        self.assertIn("pergunta 99", reply.text)
        self.assertIn("perguntas de 1 a", reply.text)

    def test_multiple_projects_can_be_listed_and_selected(self) -> None:
        self.assistant.respond("/projeto garra robótica para levantar 500 gramas")
        self.assistant.respond("/projeto mecanismo para abrir uma porta")

        listed = self.assistant.respond("/projetos")
        selected = self.assistant.respond("/usar projeto 1")
        current = self.assistant.respond("/projeto atual")

        self.assertIn("PRJ-001", listed.text)
        self.assertIn("PRJ-002", listed.text)
        self.assertIn("PRJ-001", selected.text)
        self.assertIn("PRJ-001", current.text)

    def test_natural_project_question_does_not_create_duplicate(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 500 gramas."
        )

        current = self.assistant.respond("Como está o projeto?")
        listed = self.assistant.respond("Mostre meus projetos.")

        self.assertIn("IVY — PROJETO ATIVO", current.text)
        self.assertIn("PRJ-001", current.text)
        self.assertNotIn("PRJ-002", listed.text)

    def test_calculation_is_saved_and_recovered_after_restart(self) -> None:
        request = (
            "/projeto garra robótica elétrica de dois dedos para caixas plásticas "
            "entre 40 e 90 mm de largura, massa máxima de 1,5 kg, elevá-las 30 cm em "
            "até 2 segundos, realizar 12 ciclos por minuto, fonte de 12 V, estrutura em PETG, "
            "orçamento de R$ 600 e trabalho próximo a pessoas"
        )
        self.assistant.respond(request)
        self.assistant.respond(
            "/responder 3: fonte de 12 V fornece 10 A continuamente e 15 A de pico; "
            "4: opera 8 horas por dia, vida útil de 1.000.000 de ciclos e manutenção a cada 100.000 ciclos; "
            "5: coeficiente de atrito 0,4; 6: fator de segurança 2,5"
        )

        calculated = self.assistant.respond("/calcular")
        restarted = IvyAssistant(mode="demo", memory_path=self.memory_path)
        recovered = restarted.respond("/calculos")

        self.assertIn("MEMÓRIA DE CÁLCULO", calculated.text)
        self.assertIn("CALC-GRIP-001", calculated.text)
        self.assertIn("Revisão 1", calculated.text)
        self.assertIn("CALC-GRIP-001", recovered.text)
        self.assertIn("Revisão 1", recovered.text)

    def test_natural_language_calculates_and_recalls_without_commands(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 1,5 kg por 30 cm em 2 segundos."
        )

        calculated = self.assistant.respond("Faça os cálculos do projeto.")
        recalled = self.assistant.respond("Mostre o último cálculo.")

        self.assertIn("MEMÓRIA DE CÁLCULO", calculated.text)
        self.assertIn("CÁLCULO GUARDADO", calculated.text)
        self.assertIn("MEMÓRIA GUARDADA", recalled.text)

    def test_calculation_runs_automatic_independent_verification(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 1,5 kg por 30 cm em 2 segundos."
        )

        calculated = self.assistant.respond("Faça os cálculos do projeto.")
        project = self.assistant.memory.active_project()

        self.assertIn("VERIFICAÇÃO AUTOMÁTICA", calculated.text)
        self.assertEqual(1, project["verification_revision"])
        self.assertEqual(1, len(project["verification_history"]))
        self.assertFalse(project["verification_stale"])

    def test_natural_verification_is_saved_and_recalled_after_restart(self) -> None:
        self._prepare_advanced_project()

        verified = self.assistant.respond("Verifique o projeto.")
        restarted = IvyAssistant(mode="demo", memory_path=self.memory_path)
        recalled = restarted.respond("Mostre a última verificação.")

        self.assertIn("VERIFICAÇÃO INDEPENDENTE", verified.text)
        self.assertIn("VERIFICAÇÃO GUARDADA", verified.text)
        self.assertIn("consistente_com_alertas", recalled.text)
        self.assertIn("Segurança validada: não", recalled.text)

    def test_answer_change_marks_verification_as_stale(self) -> None:
        self._prepare_advanced_project()

        self.assistant.respond("A resposta 1 é uma caixa rígida e seca.")
        recalled = self.assistant.respond("Mostre a verificação.")

        self.assertIn("verificação está desatualizada", recalled.text)
        self.assertIn("Peça uma nova verificação", recalled.text)

    def test_verification_versions_are_never_overwritten(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")
        self.assistant.respond("Verifique o projeto novamente.")

        project = self.assistant.memory.active_project()

        self.assertEqual(3, project["verification_revision"])
        self.assertEqual(3, len(project["verification_history"]))
        self.assertEqual([1, 2, 3], [item["revision"] for item in project["verification_history"]])

    def test_natural_language_manages_notes_and_tasks(self) -> None:
        note = self.assistant.respond("Anote que precisamos validar o atrito.")
        task = self.assistant.respond("Crie uma tarefa para revisar o mecanismo.")

        self.assertIn("Anotado localmente", note.text)
        self.assertIn("Tarefa 1 adicionada", task.text)
        self.assertIn("validar o atrito", self.assistant.respond("Mostre minhas notas.").text)
        self.assertIn("revisar o mecanismo", self.assistant.respond("Mostre minhas tarefas.").text)

    def test_new_answer_marks_saved_calculation_as_stale(self) -> None:
        self.assistant.respond(
            "/projeto garra robótica para levantar 1,5 kg por 30 cm em 2 segundos"
        )
        self.assistant.respond("/calcular")

        self.assistant.respond("/responder 1: caixa rígida")
        recovered = self.assistant.respond("/calculos")

        self.assertIn("desatualizada", recovered.text)
        self.assertIn("Peça para eu refazer os cálculos", recovered.text)

    def test_natural_language_compares_and_recalls_concepts(self) -> None:
        self._prepare_advanced_project()

        compared = self.assistant.respond("Compare os mecanismos da garra.")
        restarted = IvyAssistant(mode="demo", memory_path=self.memory_path)
        recalled = restarted.respond("Mostre os conceitos.")

        self.assertIn("COMPARAÇÃO DE CONCEITOS", compared.text)
        self.assertIn("CONCEPT-SCREW-001", compared.text)
        self.assertIn("COMPARAÇÃO GUARDADA", compared.text)
        self.assertIn("Revisão 1", recalled.text)
        self.assertIn("CONCEPT-RACK-001", recalled.text)

    def test_concept_comparison_requires_current_calculation(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 1,5 kg."
        )

        reply = self.assistant.respond("Compare os mecanismos.")

        self.assertIn("Ainda não há uma memória de cálculo", reply.text)
        self.assertIn("faça os cálculos", reply.text)

    def test_new_answer_marks_saved_concepts_as_stale(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")

        self.assistant.respond("A resposta 1 é uma caixa rígida e seca.")
        recovered = self.assistant.respond("Mostre os conceitos.")

        self.assertIn("comparação está desatualizada", recovered.text)
        self.assertIn("Refaça os cálculos e a comparação", recovered.text)

    def test_recalculation_marks_existing_concepts_as_stale(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")

        self.assistant.respond("Refaça os cálculos.")
        summary = self.assistant.respond("Como está o projeto?")

        self.assertIn("Comparação de conceitos: revisão 1, desatualizada", summary.text)

    def test_natural_history_is_persisted_and_recalled_after_restart(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 500 gramas."
        )
        self.assistant.respond("A resposta 1 é uma caixa rígida.")

        restarted = IvyAssistant(mode="demo", memory_path=self.memory_path)
        history = restarted.respond("Mostre o histórico do projeto.")

        self.assertIn("HISTÓRICO DO PROJETO", history.text)
        self.assertIn("R1", history.text)
        self.assertIn("Projeto criado", history.text)
        self.assertIn("R2", history.text)
        self.assertIn("Pergunta 1", history.text)
        self.assertIn("caixa rígida", history.text)

    def test_calculation_and_concept_versions_are_never_overwritten(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")
        self.assistant.respond("Refaça os cálculos.")
        self.assistant.respond("Compare os mecanismos novamente.")

        project = self.assistant.memory.active_project()

        self.assertEqual(2, project["calculation_revision"])
        self.assertEqual(2, len(project["calculation_history"]))
        self.assertEqual(2, project["concept_revision"])
        self.assertEqual(2, len(project["concept_history"]))
        self.assertEqual([1, 2], [item["revision"] for item in project["calculation_history"]])
        self.assertEqual([1, 2], [item["revision"] for item in project["concept_history"]])

    def test_natural_decision_is_saved_and_listed_after_restart(self) -> None:
        self.assistant.respond(
            "Preciso desenvolver uma garra robótica para levantar 500 gramas."
        )

        saved = self.assistant.respond(
            "Registre a decisão de detalhar o conceito de fuso porque obteve a maior pontuação."
        )
        restarted = IvyAssistant(mode="demo", memory_path=self.memory_path)
        listed = restarted.respond("Mostre as decisões do projeto.")

        self.assertIn("DEC-001", saved.text)
        self.assertIn("detalhar o conceito de fuso", listed.text)
        self.assertIn("obteve a maior pontuação", listed.text)
        self.assertIn("R2", listed.text)

    def test_cad_requires_a_current_concept_comparison(self) -> None:
        self._prepare_advanced_project()

        reply = self.assistant.respond("Crie o modelo CAD da garra.")

        self.assertIn("Antes do CAD preciso comparar os mecanismos", reply.text)
        self.assertIsNone(self.assistant.memory.active_project()["cad_report"])

    def test_natural_language_generates_cad_and_runs_verification(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")

        generated = self.assistant.respond("Crie o modelo CAD da garra.")
        project = self.assistant.memory.active_project()

        self.assertIn("MODELO CAD PARAMÉTRICO", generated.text)
        self.assertIn("CAD GUARDADO", generated.text)
        self.assertIn("VERIFICAÇÃO AUTOMÁTICA", generated.text)
        self.assertEqual(1, project["cad_revision"])
        self.assertEqual(1, len(project["cad_history"]))
        self.assertEqual(4, len(project["cad_report"]["artifacts"]))
        self.assertFalse(project["cad_report"]["fabrication_approved"])
        self.assertIn(
            "modelo CAD paramétrico",
            project["verification_report"]["checked_artifacts"],
        )
        self.assertEqual(0, project["verification_report"]["error_count"])

    def test_cad_is_recalled_after_restart(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")
        self.assistant.respond("Gere o modelo CAD.")

        restarted = IvyAssistant(mode="demo", memory_path=self.memory_path)
        recalled = restarted.respond("Mostre o último CAD.")

        self.assertIn("MODELO CAD PARAMÉTRICO", recalled.text)
        self.assertIn("Revisão 1", recalled.text)
        self.assertIn("stl_preview", recalled.text)
        self.assertIn("Fabricação aprovada: não", recalled.text)

    def test_answer_change_marks_saved_cad_as_stale(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")
        self.assistant.respond("Crie o modelo CAD.")

        self.assistant.respond("A resposta 1 é uma caixa rígida, seca e reforçada.")
        recalled = self.assistant.respond("Mostre o CAD.")

        self.assertIn("CAD está desatualizado", recalled.text)
        self.assertTrue(self.assistant.memory.active_project()["cad_stale"])

    def test_cad_revisions_are_preserved_without_overwrite(self) -> None:
        self._prepare_advanced_project()
        self.assistant.respond("Compare os mecanismos da garra.")
        self.assistant.respond("Crie o modelo CAD.")
        self.assistant.respond("Gere o modelo CAD novamente.")

        project = self.assistant.memory.active_project()
        paths = [item["report"]["output_directory"] for item in project["cad_history"]]

        self.assertEqual(2, project["cad_revision"])
        self.assertEqual([1, 2], [item["revision"] for item in project["cad_history"]])
        self.assertNotEqual(paths[0], paths[1])
        self.assertTrue(paths[0].endswith("rev-001"))
        self.assertTrue(paths[1].endswith("rev-002"))

    def test_exit_ends_session(self) -> None:
        reply = self.assistant.respond("/sair")

        self.assertTrue(reply.should_exit)


if __name__ == "__main__":
    unittest.main()
