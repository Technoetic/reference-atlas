import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_identity import find_matches
import update_av046_references as av046
import update_av047_references as av047
from update_av047_references import prepare_update,edit_tests,url_lines,REFERENCES,RELEASE,SECURITY,NEW_IDS,FABLE,SKILLS

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
              'snapshots':{'agentic-vault':{'version':'v0.46.0','commit':OLD},'semantic-crosscheck':{'version':'v0.21.1','commit':'c'*40}}}
    artwork={'count':1,'assets':[{'sourceId':sources[0]['id'],'sha256':'imagehash','prompt':'original prompt',
        'generationEvidenceUrls':['historical-url'],'evidenceUrls':[sources[0]['uses'][0]['evidence'][0]['url']],
        'currentEvidenceUrls':[sources[0]['uses'][0]['evidence'][0]['url']]}]}
    texts={'README.md':['inserted']+[s['id']+' prior citation' for s in sources[:3]]}
    # Mirror the plugin's layout: the release table names the address, docs/hardening.md repeats one link
    # line before each citing sentence's closing line, SECURITY.md reports the page without its address.
    for row in REFERENCES:
        for file,needle,position in row[9]:
            lines=texts.setdefault(file,[])
            if position==-1:lines.append(f'[guide]({row[3]})')
            lines.append(('cites ' if position==0 else '')+needle)
    return registry,artwork,texts

def index_of(texts):
    return lambda url:{file:url_lines(url,lines) for file,lines in texts.items() if url_lines(url,lines)}

class AV047Tests(unittest.TestCase):
    def setUp(self):
        # The fixture is small; check the logic, not the published coverage numbers.
        self.saved=(av047.BASE,av047.EXPECTED_TUPLE)
        av047.BASE={'total':4,'citations':4,'av':3};av047.EXPECTED_TUPLE=(0,3,2,6,9)
    def tearDown(self):av047.BASE,av047.EXPECTED_TUPLE=self.saved
    def prepare(self,registry,art,texts):
        return prepare_update(registry,art,texts.__getitem__,NEW,url_index=index_of(texts),updated_at='fixed')

    def test_adds_two_release_cited_article_cards_and_repins_everything_else(self):
        registry,art,texts=fixture();before=copy.deepcopy((registry,art))
        revised,images,summary=self.prepare(registry,art,texts)
        self.assertEqual((registry,art),before)
        self.assertEqual(set(summary['addedSourceIds']),NEW_IDS);self.assertEqual(len(NEW_IDS),2)
        self.assertEqual((summary['remappedLines'],summary['priorAgenticVaultCitationsRepinned'],summary['newCitationRows']),(3,3,5))
        self.assertEqual(revised['snapshots']['agentic-vault']['version'],'v0.47.0')
        for source in revised['sources']:
            for use in source['uses']:
                for row in use['evidence']:
                    commit=NEW if use['plugin']=='agentic-vault' else 'c'*40
                    self.assertIn('/'+commit+'/',row['url'])
            if source['id'] in NEW_IDS:
                self.assertEqual((source['kind'],source['uses'][0]['role']),('article','reference'))
                self.assertEqual(source['uses'][0]['evidence'][0]['file'],RELEASE)
                self.assertIn('No earlier agentic-vault or semantic-crosscheck use',source['note'])
            else:self.assertIn(source['note'],('Prior note.','SXC.'))
        hardening=[r for s in revised['sources'] if s['id']=='url:'+FABLE for r in s['uses'][0]['evidence'] if r['file']=='docs/hardening.md']
        self.assertEqual([r['line'] for r in hardening],[2,4])
        self.assertEqual(images['assets'][0]['evidenceUrls'],[f'{BLOB}{NEW}/README.md#L2'])
        self.assertEqual(images['assets'][0]['generationEvidenceUrls'],['historical-url'])

    def test_cited_urls_resolve_to_one_card(self):
        revised,_,_=self.prepare(*fixture())
        for value,identity in ((FABLE,'url:'+FABLE),(FABLE+'/','url:'+FABLE),(FABLE+'#overview','url:'+FABLE),
                               (SKILLS,'url:'+SKILLS),(SKILLS+'/','url:'+SKILLS)):
            found=find_matches(revised,value)
            self.assertEqual((found['status'],[s['id'] for s in found['matches']]),('known',[identity]))

    def test_rerun_is_idempotent_and_a_changed_record_is_refused(self):
        registry,art,texts=fixture()
        once,images,_=self.prepare(registry,art,texts)
        twice,images2,summary=self.prepare(copy.deepcopy(once),copy.deepcopy(images),texts)
        self.assertEqual((twice,images2),(once,images));self.assertEqual(summary['addedSourceIds'],[])
        self.assertEqual((summary['remappedLines'],summary['priorAgenticVaultCitationsRepinned']),(0,3))
        broken=copy.deepcopy(once);next(s for s in broken['sources'] if s['id'] in NEW_IDS)['note']='edited'
        with self.assertRaises(ValueError):self.prepare(broken,copy.deepcopy(images),texts)

    def test_missing_release_line_or_unknown_baseline_is_refused(self):
        registry,art,texts=fixture();texts[RELEASE]=['no citation']
        with self.assertRaises(ValueError):self.prepare(registry,art,texts)
        registry,art,texts=fixture();registry['snapshots']['agentic-vault']['version']='v0.45.1'
        with self.assertRaises(ValueError):self.prepare(registry,art,texts)

    def test_rows_whose_excerpt_is_not_unique_or_gone_stop_and_are_named(self):
        registry,art,texts=fixture();texts['README.md']=texts['README.md']+['github:example/project-1 prior citation']
        texts['README.md'][3]='rewritten'
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        message=str(raised.exception)
        self.assertIn('2 agentic-vault row(s) cannot be repinned',message)
        self.assertIn('github:example/project-1 / README.md#L2: excerpt found on 2 lines',message)
        self.assertIn('github:example/project-2 / README.md#L3: excerpt found on 0 lines',message)
        registry,art,texts=fixture();del texts['README.md']
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('file missing at the new revision',str(raised.exception))

    def test_every_line_naming_a_new_address_needs_its_own_row(self):
        registry,art,texts=fixture();texts['docs/other.md']=['see https://code.claude.com/docs/en/skills#frontmatter']
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('uncovered: docs/other.md#L1',str(raised.exception))
        registry,art,texts=fixture();texts[SECURITY]=texts[SECURITY]+['(`code.claude.com/docs/en/skills`)']
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('SECURITY.md now names',str(raised.exception))
        # A longer path under the same prefix is another page, not this source.
        registry,art,texts=fixture();texts['docs/other.md']=['https://code.claude.com/docs/en/skills-reference']
        self.prepare(registry,art,texts)

    def test_a_row_expecting_the_address_on_the_line_before_is_refused_when_it_moves(self):
        registry,art,texts=fixture();lines=texts['docs/hardening.md']
        lines.insert(1,'an inserted line')
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('The address is not where the row expects it: docs/hardening.md#L3',str(raised.exception))

    def test_option_rules(self):
        for argv in (['--plugin-root','.'],
                     ['--plugin-root','.','--commit','B'*40],
                     ['--plugin-root','.','--commit',NEW,'--apply'],
                     ['--plugin-root','.','--commit',NEW,'--content-rev','HEAD'],
                     ['--plugin-root','.','--commit',NEW,'--stand-in','--public-verified']):
            with self.assertRaises(SystemExit) as raised:av047.main(argv)
            self.assertEqual(raised.exception.code,2)

    def test_test_edits_apply_once_and_keep_the_v046_edits_in_place(self):
        texts={'tests/test_delivery.py':(ROOT/'tests/test_delivery.py').read_text(encoding='utf-8'),
               'tests/artwork-uniqueness.test.mjs':(ROOT/'tests/artwork-uniqueness.test.mjs').read_text(encoding='utf-8')}
        once,_=edit_tests(texts);twice,applied=edit_tests(once)
        self.assertEqual((twice,applied),(once,0))
        self.assertIn("('v0.47.0','v0.21.1'):(56,53,7,149,269)",once['tests/test_delivery.py'])
        self.assertIn("('v0.46.0','v0.21.1'):(56,53,5,147,264)",once['tests/test_delivery.py'])
        self.assertEqual(av046.edit_tests(once),(once,0))

if __name__=='__main__':unittest.main()
