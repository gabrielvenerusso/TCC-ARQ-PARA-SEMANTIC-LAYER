import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from mvp.analysis import requirement_results, summarize_requirements


class VersionedAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'docs').mkdir()
        (self.root / 'catalog').mkdir()
        self.write('docs/requirements.json', [
            {'id': f'R{i:02}', 'criterion': f'Critério {i}'} for i in range(1, 8)
        ])
        (self.root / 'docs/ARQUITETURA.md').write_text('Componentes e interfaces.\n', encoding='utf-8')
        self.write('catalog/original.json', {'version': '1.0.0', 'terms': ['Pedido']})
        self.write('catalog/corrigido.json', {'version': '1.1.0', 'terms': ['Pedido']})
        self.stats = {'original': {'correct': 10}, 'corrigida': {'correct': 10}}
        self.checks = {'readonly': {'passed': True}, 'inference': {'passed': True}, 'data_preserved': True}
        self.checks['mutation'] = {'ontology_changed': False, 'sparql_queries_changed': False}
        self.catalogs = {'original': {'valid': True}, 'incompativel': {'valid': False}, 'corrigida': {'valid': True}}
        self.registry = {'schema_version': 1, 'scope_id': 'synthetic-sales-orders-v1', 'source_run': 'historical-run', 'analyses': [
            self.record('R01', ['docs/ARQUITETURA.md']),
            self.record('R05', ['catalog/original.json', 'catalog/corrigido.json']),
        ]}
        self.write_registry()

    def write(self, relative, value):
        (self.root / relative).write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')

    def write_registry(self):
        self.write('docs/analises.json', self.registry)

    def record(self, rid, files):
        return {'id': rid.lower() + '-version-1', 'requirement_id': rid,
                'conclusion': 'atendido', 'method': 'análise da arquitetura' if rid == 'R01' else 'definições do domínio',
                'scope': 'cenário sintético', 'criteria': ['Responsabilidades e interfaces' if rid == 'R01' else 'Termos, relações e fórmulas'],
                'files_sha256': {path: hashlib.sha256((self.root / path).read_bytes()).hexdigest() for path in files}}

    def results(self, **kwargs):
        return {r['id']: r for r in requirement_results(
            self.stats, self.checks, self.catalogs, True, root=self.root, **kwargs)}

    def test_exact_analysis_and_functional_evidence_satisfy_all_seven(self):
        requirements = self.results()
        self.assertTrue(all(r['status'] == 'atendido' for r in requirements.values()))
        summary = summarize_requirements(list(requirements.values()))
        self.assertEqual(summary['counts']['atendido'], 7)
        self.assertTrue(summary['all_requirements_met'])
        self.assertEqual(summary['analyses'], {'R01': 'atendido', 'R05': 'atendido'})

    def test_file_existence_and_technical_success_do_not_replace_missing_analysis(self):
        (self.root / 'docs/analises.json').unlink()
        requirements = self.results()
        for rid in ['R01', 'R05']:
            self.assertEqual(requirements[rid]['status'], 'não avaliado')
            self.assertIsNone(requirements[rid]['analysis_record'])
        self.assertEqual(requirements['R05']['technical_status'], 'atendido')

    def test_modified_architecture_does_not_inherit_previous_analysis(self):
        (self.root / 'docs/ARQUITETURA.md').write_text('Outra interface.\n', encoding='utf-8')
        requirements = self.results()
        self.assertEqual(requirements['R01']['status'], 'não avaliado')
        self.assertEqual(requirements['R05']['status'], 'atendido')

    def test_either_modified_catalog_version_requires_new_analysis(self):
        for relative in ['catalog/original.json', 'catalog/corrigido.json']:
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b'\n')
                self.assertEqual(self.results()['R05']['status'], 'não avaliado')
                path.write_bytes(original)

    def test_incomplete_or_malformed_analysis_never_approves(self):
        registry_path = self.root / 'docs/analises.json'
        for text in ['{', '[]', '{"schema_version":99,"analyses":[]}',
                     json.dumps({'schema_version': 1, 'analyses': [
                         {**self.registry['analyses'][0], 'criteria': []},
                         {**self.registry['analyses'][1], 'files_sha256': {}},
                     ]})]:
            with self.subTest(text=text):
                registry_path.write_text(text, encoding='utf-8')
                requirements = self.results()
                self.assertEqual(requirements['R01']['status'], 'não avaliado')
                self.assertEqual(requirements['R05']['status'], 'não avaliado')

    def test_structural_failure_remains_visible_after_definition_analysis(self):
        for configuration in ['original', 'corrigida']:
            with self.subTest(configuration=configuration):
                self.catalogs[configuration]['valid'] = False
                requirement = self.results()['R05']
                self.assertEqual(requirement['analysis_status'], 'atendido')
                self.assertEqual(requirement['technical_status'], 'não atendido')
                self.assertEqual(requirement['status'], 'não atendido')
                self.catalogs[configuration]['valid'] = True

    def test_missing_structural_evidence_is_not_success(self):
        del self.catalogs['original']
        requirement = self.results()['R05']
        self.assertEqual(requirement['analysis_status'], 'atendido')
        self.assertEqual(requirement['technical_status'], 'não avaliado')
        self.assertEqual(requirement['status'], 'não avaliado')

    def test_no_functional_evidence_does_not_approve_functional_requirements(self):
        requirements = {r['id']: r for r in requirement_results(None, None, None, None, root=self.root)}
        self.assertEqual(requirements['R01']['status'], 'atendido')
        self.assertTrue(all(requirements[rid]['status'] == 'não avaliado'
                            for rid in ['R02', 'R03', 'R04', 'R05', 'R06', 'R07']))

    def test_known_failure_takes_precedence_over_absent_analysis(self):
        (self.root / 'docs/analises.json').unlink()
        self.catalogs['corrigida']['valid'] = False
        requirement = self.results()['R05']
        self.assertEqual(requirement['analysis_status'], 'não avaliado')
        self.assertEqual(requirement['status'], 'não atendido')

    def test_historical_artifact_root_is_compared_instead_of_current_files(self):
        snapshot = self.root / 'snapshot'
        for relative in ['docs/ARQUITETURA.md', 'catalog/original.json', 'catalog/corrigido.json']:
            target = snapshot / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((self.root / relative).read_bytes())
        (self.root / 'docs/ARQUITETURA.md').write_text('Versão posterior.', encoding='utf-8')
        self.assertEqual(self.results()['R01']['status'], 'não avaliado')
        self.assertEqual(self.results(artifact_root=snapshot)['R01']['status'], 'atendido')

    def test_conflicting_records_do_not_approve(self):
        self.registry['analyses'].append({**self.registry['analyses'][0], 'id': 'conflicting', 'conclusion': 'não atendido'})
        self.write_registry()
        self.assertEqual(self.results()['R01']['status'], 'não avaliado')

    def test_another_scope_or_method_does_not_approve(self):
        self.registry['scope_id'] = 'production'
        self.write_registry()
        self.assertEqual(self.results()['R01']['status'], 'não avaliado')
        self.registry['scope_id'] = 'synthetic-sales-orders-v1'
        self.registry['analyses'][0]['method'] = 'arquivo encontrado'
        self.write_registry()
        self.assertEqual(self.results()['R01']['status'], 'não avaliado')

    def test_recovered_answers_do_not_hide_changed_ontology_or_queries(self):
        for key in ['ontology_changed', 'sparql_queries_changed']:
            with self.subTest(key=key):
                self.checks['mutation'][key] = True
                self.assertEqual(self.results()['R07']['status'], 'não atendido')
                self.checks['mutation'][key] = False
        del self.checks['mutation']
        self.assertEqual(self.results()['R07']['status'], 'não avaliado')


if __name__ == '__main__':
    unittest.main()
