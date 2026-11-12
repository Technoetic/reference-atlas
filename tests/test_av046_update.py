import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_identity import find_matches
import update_av046_references as av046
from update_av046_references import prepare_update,edit_tests,REFERENCES,RELEASE,NEW_IDS

OLD='a'*40;NEW='b'*40
BLOB='https://github.com/Technoetic/agentic-vault/blob/'

def fixture():
    sources=[]
    for index in range(3):
        identity=f'github:example/project-{index}'
        row={'file':'README.md','line':index+1,'url':f'{BLOB}{OLD}/README.md#L{index+1}','excerpt':identity+' prior citation'}
        sources.append({'id':identity,'kind':'project','title':identity,'url':'https://github.com/example/project-'+str(index),
            'year':None,'keys':[identity],'aliases':[],'tags':[],'note':'Prior note.',
            'uses':[{'plugin':'agentic-vault','role':'reference','evidence':[row]}]})
    sxc={'file':'docs/a.md','line':1,'url':'https://github.com/Technoetic/semantic-crosscheck/blob/'+'c'*40+'/docs/a.md#L1','excerpt':'sxc'}
    sources.append({'id':'github:example/sxc','kind':'paper','title':'SXC only','url':'https://github.com/example/sxc','year':None,
        'keys':['github:example/sxc'],'aliases':[],'tags':[],'note':'SXC.','uses':[{'plugin':'semantic-crosscheck','role':'reference','evidence':[sxc]}]})
    registry={'schemaVersion':1,'updatedAt':'old','sources':sources,
              'snapshots':{'agentic-vault':{'version':'v0.45.1','commit':OLD},'semantic-crosscheck':{'version':'v0.21.1','commit':'c'*40}}}
    artwork={'count':1,'assets':[{'sourceId':sources[0]['id'],'sha256':'imagehash','prompt':'original prompt',
        'generationEvidenceUrls':['historical-url'],'evidenceUrls':[sources[0]['uses'][0]['evidence'][0]['url']],
        'currentEvidenceUrls':[sources[0]['uses'][0]['evidence'][0]['url']]}]}
    texts={'README.md':['inserted']+[s['id']+' prior citation' for s in sources[:3]]}
    for row in REFERENCES:
        for file,needle in row[9]:texts.setdefault(file,[]).append('cites '+needle)
    return registry,artwork,texts

class AV046Tests(unittest.TestCase):
    def setUp(self):
        # The fixture is small; check the logic, not the published coverage numbers.
        self.saved=(av046.BASE,av046.EXPECTED_TUPLE)
        av046.BASE={'total':4,'citations':4,'av':3};av046.EXPECTED_TUPLE=(0,6,0,7,12)
    def tearDown(self):av046.BASE,av046.EXPECTED_TUPLE=self.saved
    def prepare(self,registry,art,texts):return prepare_update(registry,art,texts.__getitem__,NEW,updated_at='fixed')

    def test_adds_three_release_cited_format_cards_and_repins_everything_else(self):
        registry,art,texts=fixture();before=copy.deepcopy((registry,art))
        revised,images,summary=self.prepare(registry,art,texts)
        self.assertEqual((registry,art),before)
        self.assertEqual(set(summary['addedSourceIds']),NEW_IDS);self.assertEqual(len(NEW_IDS),3)
        self.assertEqual(summary['remappedLines'],3)
        for source in revised['sources']:
            for use in source['uses']:
                for row in use['evidence']:
                    commit=NEW if use['plugin']=='agentic-vault' else 'c'*40
                    self.assertIn('/'+commit+'/',row['url'])
            if source['id'] in NEW_IDS:
                self.assertEqual(source['kind'],'format')
                self.assertEqual(source['uses'][0]['evidence'][0]['file'],RELEASE)
                self.assertIn('No earlier agentic-vault or semantic-crosscheck use',source['note'])
            else:self.assertIn(source['note'],('Prior note.','SXC.'))
        self.assertEqual(images['assets'][0]['evidenceUrls'],[f'{BLOB}{NEW}/README.md#L2'])
        self.assertEqual(images['assets'][0]['generationEvidenceUrls'],['historical-url'])

    def test_cited_urls_and_annex_latest_address_resolve_to_one_card(self):
        revised,_,_=self.prepare(*fixture())
        for value,identity in (('https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3/','url:https://www.unicode.org/versions/Unicode18.0.0/core-spec/chapter-3'),
                               ('https://www.unicode.org/reports/tr15/tr15-58.html','url:https://www.unicode.org/reports/tr15/tr15-58.html'),
                               ('https://www.unicode.org/reports/tr15/','url:https://www.unicode.org/reports/tr15/tr15-58.html'),
                               ('https://yaml.org/spec/1.2.2/','url:https://yaml.org/spec/1.2.2')):
            found=find_matches(revised,value)
            self.assertEqual((found['status'],[s['id'] for s in found['matches']]),('known',[identity]))

    def test_rerun_is_idempotent_and_a_changed_record_is_refused(self):
        registry,art,texts=fixture()
        once,images,_=self.prepare(registry,art,texts)
        twice,images2,summary=self.prepare(copy.deepcopy(once),copy.deepcopy(images),texts)
        self.assertEqual((twice,images2),(once,images));self.assertEqual(summary['addedSourceIds'],[])
        broken=copy.deepcopy(once);next(s for s in broken['sources'] if s['id'] in NEW_IDS)['note']='edited'
        with self.assertRaises(ValueError):self.prepare(broken,copy.deepcopy(images),texts)

    def test_missing_release_line_or_unknown_baseline_is_refused(self):
        registry,art,texts=fixture();texts[RELEASE]=['no citation']
        with self.assertRaises(ValueError):self.prepare(registry,art,texts)
        registry,art,texts=fixture();registry['snapshots']['agentic-vault']['version']='v0.44.0'
        with self.assertRaises(ValueError):self.prepare(registry,art,texts)

    def test_commit_is_required(self):
        with self.assertRaises(SystemExit) as raised:av046.main(['--plugin-root','.'])
        self.assertEqual(raised.exception.code,2)

    def test_test_edits_apply_once(self):
        texts={'tests/test_delivery.py':(ROOT/'tests/test_delivery.py').read_text(encoding='utf-8'),
               'tests/artwork-uniqueness.test.mjs':(ROOT/'tests/artwork-uniqueness.test.mjs').read_text(encoding='utf-8')}
        once,_=edit_tests(texts);twice,applied=edit_tests(once)
        self.assertEqual((twice,applied),(once,0))
        self.assertIn("('v0.46.0','v0.21.1'):(56,53,5,147,264)",once['tests/test_delivery.py'])

if __name__=='__main__':unittest.main()
