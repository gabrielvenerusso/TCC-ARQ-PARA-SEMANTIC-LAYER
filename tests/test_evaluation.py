import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mvp import __main__ as mvp


class RequirementReviewTests(unittest.TestCase):
    def results(self, catalog_valid=True, **kwargs):
        stats={'original':{'correct':10},'corrigida':{'correct':10}}
        checks={'readonly':{'passed':True},'inference':{'passed':True},'data_preserved':True}
        checks['mutation']={'ontology_changed':False,'sparql_queries_changed':False}
        catalogs={'original':{'valid':True},'corrigida':{'valid':catalog_valid}}
        return {r['id']:r for r in mvp.requirement_results(stats,checks,catalogs,True,**kwargs)}

    def test_successful_technical_checks_do_not_replace_absent_analysis(self):
        requirements=self.results(analysis_path=mvp.ROOT/'absent-analysis.json')
        self.assertTrue((mvp.ROOT/'docs/ARQUITETURA.md').is_file())
        self.assertEqual(requirements['R01']['status'],'não avaliado')
        self.assertIn('responsabilidades',requirements['R01']['qualification'])
        self.assertEqual(requirements['R05']['status'],'não avaliado')
        self.assertEqual(requirements['R05']['technical_status'],'atendido')
        for rid in ['R02','R03','R04','R06','R07']:
            self.assertEqual(requirements[rid]['status'],'atendido')

    def test_invalid_catalog_is_visible_with_recorded_analysis(self):
        requirement=self.results(catalog_valid=False)['R05']
        self.assertEqual(requirement['status'],'não atendido')
        self.assertEqual(requirement['technical_status'],'não atendido')

    def test_catalog_structure_does_not_claim_definition_analysis(self):
        for name in ['original','corrigido']:
            catalog=json.loads((mvp.ROOT/f'catalog/{name}.json').read_text(encoding='utf-8'))
            columns=[{'table_name':term['table'],'column_name':column}
                     for term in catalog['terms'] for column in term['columns']]
            check=mvp.catalog_check(catalog,{'columns':columns})
            self.assertTrue(check['valid'])
            self.assertNotIn('human_review',check)
            self.assertNotIn('analysis_status',check)
            self.assertEqual(catalog['review']['record'],'docs/analises.json')


class BlockedEvaluationTests(unittest.TestCase):
    def test_bootstrap_failure_preserves_all_planned_attempts_and_clean_commit(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence=Path(temp)/'evidencias'
            run=evidence/'test-bootstrap'
            git={'commit':'a'*40,'dirty':False,'status':''}
            def capture_git():
                self.assertFalse(run.exists())
                return git
            with patch.object(mvp,'EVIDENCE',evidence), \
                 patch.dict(mvp.os.environ,{'EVIDENCE_RUN_ID':run.name,'EVIDENCE_LATEST_FILE':'latest-windows.json'}), \
                 patch.object(mvp,'git_info',side_effect=capture_git), \
                 patch.object(mvp,'bootstrap',side_effect=RuntimeError('PostgreSQL indisponível')), \
                 patch.object(mvp,'request') as request:
                self.assertEqual(mvp.evaluate(),2)
                request.assert_not_called()
            records=json.loads((run/'records.json').read_text(encoding='utf-8'))
            summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
            self.assertEqual(len(records),30)
            self.assertEqual(len({r['execution_id'] for r in records}),30)
            self.assertTrue(all(r['status']=='blocked' and r['phase']=='bootstrap' and
                                r['query_executed'] is False and r['git_commit']==git['commit']
                                for r in records))
            self.assertEqual(summary['queries_executed'],0)
            self.assertEqual(summary['git'],git)
            self.assertFalse(summary['protocol_passed'])
            requirements=json.loads((run/'requirements.json').read_text(encoding='utf-8'))
            self.assertEqual(requirements,mvp.requirement_results(None,None,None,None))
            self.assertTrue(all(r['status']=='não avaliado' for r in requirements if r['id']!='R01'))
            self.assertEqual(summary['requirements']['analyses'],
                             {r['id']:r['analysis_status'] for r in requirements if r['id'] in ['R01','R05']})
            manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
            for relative,digest in manifest['files_sha256'].items():
                self.assertEqual(mvp.digest(run/relative),digest)
            self.assertIn('PostgreSQL indisponível',(run/'relatorio.html').read_text(encoding='utf-8'))
            self.assertNotIn('pendente_revisao_humana',(run/'relatorio.html').read_text(encoding='utf-8'))
            self.assertIn('não avaliado',(run/'relatorio.html').read_text(encoding='utf-8'))
            self.assertIn('bootstrap.log',manifest['files_sha256'])
            self.assertTrue((evidence/'latest-windows.json').is_file())
            self.assertFalse((evidence/'latest.json').exists())

    def test_run_id_cannot_escape_evidence_root(self):
        for run_id in ['../escape','..','a/b','a\\b']:
            with self.subTest(run_id=run_id), \
                 patch.dict(mvp.os.environ,{'EVIDENCE_RUN_ID':run_id}), \
                 patch.object(mvp,'bootstrap') as bootstrap:
                with self.assertRaises(ValueError):
                    mvp.evaluate()
                bootstrap.assert_not_called()

    def test_invalid_latest_filename_fails_before_creating_evidence(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence=Path(temp)/'evidencias'
            with patch.object(mvp,'EVIDENCE',evidence), \
                 patch.dict(mvp.os.environ,{'EVIDENCE_LATEST_FILE':'../latest.json'}), \
                 patch.object(mvp,'bootstrap') as bootstrap:
                with self.assertRaises(ValueError):
                    mvp.evaluate()
                bootstrap.assert_not_called()
                self.assertFalse(evidence.exists())

    def test_existing_run_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            evidence=Path(temp)
            run=evidence/'existing'
            run.mkdir()
            marker=run/'marker.txt'
            marker.write_text('original',encoding='utf-8')
            with patch.object(mvp,'EVIDENCE',evidence), \
                 patch.dict(mvp.os.environ,{'EVIDENCE_RUN_ID':run.name}), \
                 patch.object(mvp,'git_info',return_value={}), \
                 patch.object(mvp,'bootstrap') as bootstrap:
                with self.assertRaises(FileExistsError):
                    mvp.evaluate()
                bootstrap.assert_not_called()
            self.assertEqual(marker.read_text(encoding='utf-8'),'original')


class EvidenceVerificationTests(unittest.TestCase):
    def test_supplemental_manifest_checks_host_logs_and_original_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            data=folder/'records.json'
            data.write_text('[]\n',encoding='utf-8')
            mvp.dump(folder/'manifest.json',{'files_sha256':{'records.json':mvp.digest(data)}})
            log=folder/'compose.log'
            log.write_text('completed\n',encoding='utf-8')
            mvp.dump(folder/'host-manifest.json',{'files_sha256':{
                'manifest.json':mvp.digest(folder/'manifest.json'),'compose.log':mvp.digest(log)}})
            self.assertTrue(mvp.verify_evidence(folder)['valid'])
            log.write_text('changed\n',encoding='utf-8')
            self.assertEqual(mvp.verify_evidence(folder)['invalid'],['compose.log'])
            (folder/'manifest.json').write_text('{"files_sha256":{}}',encoding='utf-8')
            self.assertEqual(mvp.verify_evidence(folder)['invalid'],['compose.log','manifest.json'])


if __name__=='__main__':
    unittest.main()
