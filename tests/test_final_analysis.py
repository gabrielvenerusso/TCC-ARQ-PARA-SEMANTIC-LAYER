import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from mvp import __main__ as mvp
from mvp.final_analysis import analyze_run
from mvp.reporting import render_report


class FinalAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name)/'analysis'
        pointer = json.loads((mvp.ROOT/'evidencias/latest-windows.json').read_text(encoding='utf-8-sig'))
        self.source = mvp.ROOT/'evidencias'/pointer['run_id']

    def hashes(self, folder):
        return {p.relative_to(folder).as_posix(): mvp.digest(p) for p in folder.rglob('*') if p.is_file()}

    def test_consolidation_preserves_source_and_never_executes_queries(self):
        before = self.hashes(self.source)
        pointer_before = mvp.digest(mvp.ROOT/'evidencias/latest-windows.json')
        with patch.object(mvp, 'connect') as connect, patch.object(mvp, 'request') as request:
            result = analyze_run(self.source, self.output, root=mvp.ROOT)
            connect.assert_not_called()
            request.assert_not_called()
        self.assertEqual(before, self.hashes(self.source))
        self.assertEqual(pointer_before, mvp.digest(mvp.ROOT/'evidencias/latest-windows.json'))
        self.assertEqual(result['requirements']['counts']['atendido'], 7)
        self.assertEqual(result['attempts'], 30)
        self.assertEqual(result['recorded_tests']['count'], 15)
        self.assertEqual(result['recorded_tests']['result'], 'aprovados')
        self.assertTrue(result['controlled_schema_block'])
        self.assertEqual(result['queries_executed_by_analysis'], 0)
        self.assertEqual(result['discrepancies'], [])
        self.assertTrue(mvp.verify_evidence(self.output)['valid'])
        page = (self.output/'relatorio.html').read_text(encoding='utf-8')
        self.assertIn('7 de 7 requisitos atendidos', page)
        self.assertIn('Foram alteradas 3 regras', page)
        self.assertIn('15 testes automatizados', page)
        self.assertNotIn('pendente_revisao_humana', page)
        self.assertIn('<details>', page)
        self.assertIn('não executou novas consultas', page)
        from html.parser import HTMLParser
        from urllib.parse import unquote
        class Links(HTMLParser):
            def handle_starttag(inner, tag, attrs):
                for name, value in attrs:
                    if name == 'href':
                        self.assertTrue((self.output/unquote(value)).is_file(), value)
        Links().feed(page)

    def test_missing_analysis_keeps_requirements_unevaluated_in_html_and_json(self):
        result = analyze_run(self.source, self.output, root=mvp.ROOT,
                             analysis_path=Path(self.temp.name)/'missing.json')
        self.assertEqual(result['requirements']['counts']['atendido'], 5)
        self.assertEqual(result['requirements']['counts']['não avaliado'], 2)
        page = (self.output/'relatorio.html').read_text(encoding='utf-8')
        self.assertIn('2 não avaliados', page)
        self.assertNotIn('7 de 7', page)

    def test_source_and_existing_output_cannot_be_overwritten(self):
        for output in [self.source, self.source/'analysis', mvp.ROOT/'evidencias'/'new-analysis']:
            with self.subTest(output=output), self.assertRaises(ValueError):
                analyze_run(self.source, output, root=mvp.ROOT)
        self.output.mkdir()
        marker = self.output/'marker'
        marker.write_text('preserve')
        with self.assertRaises(FileExistsError):
            analyze_run(self.source, self.output, root=mvp.ROOT)
        self.assertEqual(marker.read_text(), 'preserve')

    def test_integrity_failure_prevents_consolidation(self):
        copied = Path(self.temp.name)/'source'
        shutil.copytree(self.source, copied)
        (copied/'records.json').write_text('[]', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'Integridade'):
            analyze_run(copied, self.output, root=mvp.ROOT)
        self.assertFalse(self.output.exists())

    def test_derived_manifest_detects_changes_in_linked_original(self):
        copied = Path(self.temp.name)/'source'
        shutil.copytree(self.source, copied)
        analyze_run(copied, self.output, root=mvp.ROOT)
        (copied/'records.json').write_text('[]', encoding='utf-8')
        result = mvp.verify_evidence(self.output)
        self.assertFalse(result['valid'])
        self.assertIn('source/records.json', result['invalid'])

    def test_render_keeps_catalog_failure_visible_and_escapes_errors(self):
        stats = {name: {'total': 10, 'correct': 10, 'incorrect': 0, 'blocked': 0, 'error': 0}
                 for name in ['original', 'corrigida']}
        checks = {'readonly': {'passed': True}, 'inference': {'passed': True}, 'data_preserved': True,
                  'mutation': {'ontology_changed': False, 'sparql_queries_changed': False}}
        requirements = mvp.requirement_results(stats, checks, {'original': {'valid': True}, 'corrigida': {'valid': False}}, True)
        summary = {'configurations': stats, 'run_id': 'test', 'timestamp': 'recorded', 'git': {},
                   'protocol_passed': False, 'traceability_complete': True, 'error': '<script>failure</script>'}
        self.output.mkdir()
        render_report(self.output, summary, [], requirements)
        page = (self.output/'relatorio.html').read_text(encoding='utf-8')
        self.assertIn('não atendido', page)
        self.assertIn('Validade estrutural do catálogo', page)
        self.assertIn('&lt;script&gt;failure&lt;/script&gt;', page)
        self.assertNotIn('<script>', page)


if __name__ == '__main__':
    unittest.main()
