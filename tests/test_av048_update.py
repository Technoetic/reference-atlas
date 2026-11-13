import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_identity import canonical_key,find_matches
import update_av046_references as av046
import update_av047_references as av047
import update_av048_references as av048
from update_av048_references import (prepare_update,edit_tests,identities_on,naming_lines,REFERENCES,RELEASE,GUIDE,
    METADATA_TEST,NEW_IDS,BUILD_PLUGINS,HOOKS,DISCOVERY,PLUGINS,RULES,PERMISSIONS,PERMISSIONS_COMMAND,SETTINGS,
    CLI_REFERENCE,SKILLS,FAQ,AGY_CLI,WAZA,SUPERPOWERS)

OLD='a'*40;NEW='b'*40
BLOB='https://github.com/Technoetic/agentic-vault/blob/'
PAGES=(BUILD_PLUGINS,HOOKS,DISCOVERY,PLUGINS,RULES,PERMISSIONS,PERMISSIONS_COMMAND,SETTINGS,CLI_REFERENCE,SKILLS,FAQ)

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
              'snapshots':{'agentic-vault':{'version':'v0.47.0','commit':OLD},'semantic-crosscheck':{'version':'v0.21.1','commit':'c'*40}}}
    artwork={'count':1,'assets':[{'sourceId':sources[0]['id'],'sha256':'imagehash','prompt':'original prompt',
        'generationEvidenceUrls':[sources[0]['uses'][0]['evidence'][0]['url']],'evidenceUrls':[sources[0]['uses'][0]['evidence'][0]['url']],
        'currentEvidenceUrls':[sources[0]['uses'][0]['evidence'][0]['url']]}]}
    texts={'README.md':['inserted']+[s['id']+' prior citation' for s in sources[:3]]}
    # Mirror the plugin's layout: the release table lists the eleven pages on one row and each repository on its own
    # row; the guide lists the pages (Plugins and Rules, Settings and CLI reference, Skills and FAQ share a line; the
    # /permissions command page follows the Permissions page) and the CLI repository; the metadata test pins the link
    # text of the three repositories.
    texts[RELEASE]=['# v0.48.0','| '+'·'.join(f'[page]({url})' for url in PAGES)+' | official docs |',
                    f'| [cli]({AGY_CLI}) | changelog |',f'| [waza]({WAZA}) | subfolder install |',f'| [sp]({SUPERPOWERS}) | layout |']
    texts[GUIDE]=['# guide',f'[a]({BUILD_PLUGINS}),',f'[b]({HOOKS}),',f'[c]({DISCOVERY}),',f'[d]({PLUGINS}), [e]({RULES}),',
                  f'[f]({PERMISSIONS}),',f'[`/permissions` command]({PERMISSIONS_COMMAND}),',
                  f'[g]({SETTINGS}), [h]({CLI_REFERENCE}),',f'[i]({SKILLS}), [j]({FAQ}),',
                  f'[k]({AGY_CLI}) read on the same day']
    texts[METADATA_TEST]=['class T:']+[f'    self.assertIn("]({url})", rows[{index}])' for index,url in enumerate((AGY_CLI,WAZA,SUPERPOWERS),1)]
    return registry,artwork,texts

def index_of(texts):
    def index(url):
        identity=canonical_key(url)['key']
        return {file:naming_lines(identity,lines) for file,lines in texts.items() if naming_lines(identity,lines)}
    return index

class AV048Tests(unittest.TestCase):
    def setUp(self):
        # The fixture is small; check the logic, not the published coverage numbers.
        self.saved=(av048.BASE,av048.EXPECTED_TUPLE)
        av048.BASE={'total':4,'citations':4,'av':3};av048.EXPECTED_TUPLE=(0,6,11,18,30)
    def tearDown(self):av048.BASE,av048.EXPECTED_TUPLE=self.saved
    def prepare(self,registry,art,texts):
        return prepare_update(registry,art,texts.__getitem__,NEW,url_index=index_of(texts),updated_at='fixed')

    def test_adds_fourteen_release_cited_cards_and_repins_everything_else(self):
        registry,art,texts=fixture();before=copy.deepcopy((registry,art))
        revised,images,summary=self.prepare(registry,art,texts)
        self.assertEqual((registry,art),before)
        self.assertEqual(set(summary['addedSourceIds']),NEW_IDS);self.assertEqual(len(NEW_IDS),14)
        self.assertEqual(NEW_IDS,{'url:'+url for url in PAGES}|{'github:google-antigravity/antigravity-cli','github:tw93/waza',
                                                               'github:obra/superpowers'})
        self.assertEqual((summary['remappedLines'],summary['priorAgenticVaultCitationsRepinned'],summary['newCitationRows']),(3,3,26))
        self.assertEqual(revised['snapshots']['agentic-vault']['version'],'v0.48.0')
        kinds={}
        for source in revised['sources']:
            for use in source['uses']:
                for row in use['evidence']:
                    commit=NEW if use['plugin']=='agentic-vault' else 'c'*40
                    self.assertIn('/'+commit+'/',row['url'])
            if source['id'] in NEW_IDS:
                kinds[source['kind']]=kinds.get(source['kind'],0)+1
                self.assertEqual(source['uses'][0]['role'],'reference')
                self.assertEqual(source['uses'][0]['evidence'][0]['file'],RELEASE)
                self.assertIn('No earlier agentic-vault or semantic-crosscheck use',source['note'])
            else:self.assertIn(source['note'],('Prior note.','SXC.'))
        self.assertEqual(kinds,{'article':11,'project':3})
        self.assertEqual(summary['citedAddressLines'][FAQ],[f'{GUIDE}#L9',f'{RELEASE}#L2'])
        self.assertEqual(summary['citedAddressLines'][PLUGINS],[f'{GUIDE}#L5',f'{RELEASE}#L2'])
        self.assertEqual(summary['citedAddressLines'][RULES],[f'{GUIDE}#L5',f'{RELEASE}#L2'])
        # /docs/permissions and /docs/cli/commands/permissions are two pages; neither line is the other's.
        self.assertEqual(summary['citedAddressLines'][PERMISSIONS],[f'{GUIDE}#L6',f'{RELEASE}#L2'])
        self.assertEqual(summary['citedAddressLines'][PERMISSIONS_COMMAND],[f'{GUIDE}#L7',f'{RELEASE}#L2'])
        self.assertEqual(summary['citedAddressLines'][CLI_REFERENCE],[f'{GUIDE}#L8',f'{RELEASE}#L2'])
        self.assertEqual(summary['citedAddressLines'][AGY_CLI],[f'{GUIDE}#L10',f'{RELEASE}#L3'])
        self.assertEqual(summary['citedAddressLines'][WAZA],[f'{RELEASE}#L4'])
        self.assertEqual(summary['testLinesNotCited'][WAZA],[f'{METADATA_TEST}#L3'])
        self.assertEqual(sum(len(v) for v in summary['testLinesNotCited'].values()),3)
        self.assertEqual(sum(len(v) for v in summary['generatedCopyLines'].values()),0)
        self.assertEqual(images['assets'][0]['evidenceUrls'],[f'{BLOB}{NEW}/README.md#L2'])
        self.assertEqual(images['assets'][0]['generationEvidenceUrls'],[f'{BLOB}{OLD}/README.md#L1'])

    def test_cited_addresses_resolve_to_one_card(self):
        revised,_,_=self.prepare(*fixture())
        cases=[(url+suffix,'url:'+url) for url in PAGES for suffix in ('','/','#section')]
        cases+=[(AGY_CLI,'github:google-antigravity/antigravity-cli'),(WAZA,'github:tw93/waza'),
                ('https://github.com/TW93/WAZA/tree/v3.42.0/plugins/waza','github:tw93/waza'),
                (SUPERPOWERS+'.git','github:obra/superpowers')]
        for value,identity in cases:
            found=find_matches(revised,value)
            self.assertEqual((found['status'],[s['id'] for s in found['matches']]),('known',[identity]))

    def test_card_notes_say_where_each_fact_comes_from(self):
        # Statements the release note row does not make are attributed, and "this repository" is agentic-vault.
        notes={row[0]:row[8] for row in REFERENCES}
        faq=notes['url:'+FAQ]
        self.assertIn('for that reason no agent-run agy check was made. The guide (docs/antigravity.md) adds that the '
                      "plugin's skills, hooks and Jarvis bridge do not run agy.",faq)
        self.assertNotIn('check was made, and the plugin',faq)
        cli=notes['github:google-antigravity/antigravity-cli']
        self.assertIn('as read on 2026-11-13 at main 87bd973; the catalog update resolved that commit through the GitHub '
                      'API on 2026-11-13 as 87bd97327a72d62d553c3aede8cf77752ae4c59a ("Update CHANGELOG.md for 1.5.7").',cli)
        self.assertNotIn('87bd973 (87bd973',cli)
        waza=notes['github:tw93/waza']
        self.assertIn("the same method installed agentic-vault's own /tree/v0.45.1 address at that tag",waza)
        self.assertNotIn("this repository's /tree/v0.45.1",waza)
        superpowers=notes['github:obra/superpowers']
        self.assertIn('Hooks and commands are central to agentic-vault itself: adding an Antigravity manifest at the '
                      "agentic-vault root made agy 1.5.7 turn off",superpowers)
        self.assertIn("agentic-vault's root AGENTS.md left a validator warning",superpowers)
        self.assertNotIn('central to this plugin',superpowers)

    def test_rerun_is_idempotent_and_a_changed_record_is_refused(self):
        registry,art,texts=fixture()
        once,images,_=self.prepare(registry,art,texts)
        twice,images2,summary=self.prepare(copy.deepcopy(once),copy.deepcopy(images),texts)
        self.assertEqual((twice,images2),(once,images));self.assertEqual(summary['addedSourceIds'],[])
        self.assertEqual((summary['remappedLines'],summary['priorAgenticVaultCitationsRepinned'],summary['repinnedRowsTotal']),(0,3,29))
        broken=copy.deepcopy(once);next(s for s in broken['sources'] if s['id'] in NEW_IDS)['note']='edited'
        with self.assertRaises(ValueError):self.prepare(broken,copy.deepcopy(images),texts)

    def test_missing_release_line_or_unknown_baseline_is_refused(self):
        registry,art,texts=fixture();texts[RELEASE]=['no citation']
        with self.assertRaises(ValueError):self.prepare(registry,art,texts)
        registry,art,texts=fixture();registry['snapshots']['agentic-vault']['version']='v0.46.0'
        with self.assertRaises(ValueError):self.prepare(registry,art,texts)
        registry,art,texts=fixture();registry['sources'][0]['uses'][0]['evidence'].append(
            {**registry['sources'][0]['uses'][0]['evidence'][0]})
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

    def test_every_line_naming_a_new_source_needs_its_own_row(self):
        for line,where in ((f'see {HOOKS}#events','hooks'),
                           ('installed from github.com/tw93/Waza/tree/main/plugins/waza','tw93/Waza'),
                           ('antigravity.google/docs/faq.','docs/faq'),
                           ('antigravity.google/docs/cli/commands/permissions/ (scopes)','docs/cli/commands/permissions'),
                           (f'`{SKILLS}`','docs/skills'),
                           ('https://github.com/TW93/WAZA','tw93/Waza')):
            registry,art,texts=fixture();texts['docs/other.md']=['intro',line]
            with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
            self.assertIn('uncovered: docs/other.md#L2',str(raised.exception));self.assertIn(where,str(raised.exception))
        # A longer path under a page is another page, a shorter one is no listed page, and the schema address is no
        # listed source.
        registry,art,texts=fixture()
        texts['docs/other.md']=[HOOKS+'-reference',PERMISSIONS+'/advanced','https://antigravity.google/docs/cli',
                                'https://antigravity.google/schemas/v1/plugin.json',
                                '# (https://antigravity.google/docs/<page>).',
                                'self.assertIn(f"](https://antigravity.google/docs/{page})", rows[0])']
        self.prepare(registry,art,texts)
        registry,art,texts=fixture();texts[GUIDE][2]='hooks without an address'
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('New citation needs one exact line: docs/antigravity.md',str(raised.exception))

    def test_a_generated_copy_is_reported_only_when_it_equals_the_cited_line(self):
        registry,art,texts=fixture();texts['antigravity/'+GUIDE]=list(texts[GUIDE])
        _,_,summary=self.prepare(registry,art,texts)
        self.assertEqual(summary['generatedCopyLines'][FAQ],[f'antigravity/{GUIDE}#L9'])
        self.assertEqual(summary['generatedCopyLines'][PERMISSIONS_COMMAND],[f'antigravity/{GUIDE}#L7'])
        self.assertEqual(sum(len(v) for v in summary['generatedCopyLines'].values()),12)
        registry,art,texts=fixture();texts['antigravity/'+GUIDE]=list(texts[GUIDE]);texts['antigravity/'+GUIDE][2]+=' (changed)'
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('uncovered: antigravity/docs/antigravity.md#L3',str(raised.exception))
        registry,art,texts=fixture();texts['antigravity/'+GUIDE]=['inserted']+texts[GUIDE]
        with self.assertRaises(ValueError):self.prepare(registry,art,texts)
        registry,art,texts=fixture();texts['antigravity/'+RELEASE]=list(texts[RELEASE])
        self.prepare(registry,art,texts)

    def test_only_listed_test_lines_may_name_a_source_without_a_row(self):
        registry,art,texts=fixture();texts['tests/test_other.py']=[f'URL = "{WAZA}"']
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('uncovered: tests/test_other.py#L1',str(raised.exception))
        registry,art,texts=fixture();texts[METADATA_TEST].append(texts[METADATA_TEST][2])
        with self.assertRaises(ValueError) as raised:self.prepare(registry,art,texts)
        self.assertIn('A listed test line is not unique',str(raised.exception))
        registry,art,texts=fixture();del texts[METADATA_TEST]
        _,_,summary=self.prepare(registry,art,texts)
        self.assertEqual(sum(len(v) for v in summary['testLinesNotCited'].values()),0)

    def test_identities_on_reads_addresses_with_or_without_scheme(self):
        self.assertEqual(identities_on('see antigravity.google/docs/faq.'),{'url:'+FAQ})
        self.assertEqual(identities_on(f'<{HOOKS}/>, `{DISCOVERY}`'),{'url:'+HOOKS,'url:'+DISCOVERY})
        self.assertEqual(identities_on('www.github.com/obra/superpowers/blob/main/README.md'),{'github:obra/superpowers'})
        self.assertNotIn('url:'+PLUGINS,identities_on(BUILD_PLUGINS))
        self.assertEqual(identities_on(f'[`/permissions` command]({PERMISSIONS_COMMAND}),'),{'url:'+PERMISSIONS_COMMAND})
        self.assertEqual(identities_on(f'[g]({SETTINGS}), [h]({CLI_REFERENCE}),'),{'url:'+SETTINGS,'url:'+CLI_REFERENCE})
        self.assertEqual(identities_on('superpowers:subagent-driven-development'),set())

    def test_option_rules(self):
        for argv in (['--plugin-root','.'],
                     ['--plugin-root','.','--commit','B'*40],
                     ['--plugin-root','.','--commit',NEW,'--apply'],
                     ['--plugin-root','.','--commit',NEW,'--content-rev','HEAD'],
                     ['--plugin-root','.','--commit',NEW,'--stand-in','--public-verified']):
            with self.assertRaises(SystemExit) as raised:av048.main(argv)
            self.assertEqual(raised.exception.code,2)

    def test_artwork_paths_accept_the_current_card_names_and_nothing_else(self):
        for good in ('media/cards/card-001.webp','media/cards/card-149-v2.webp','media/cards/card-150-stryker-js-v024.webp',
                     'media/cards/card-151-mutation-testing-elements-v024.webp'):
            self.assertTrue(av048.ARTWORK_PATH.fullmatch(good),good)
        for bad in ('media/cards/card-150-Stryker.webp','media/cards/../card-150.webp','media/card-150.webp',
                    'media/cards/card-15.webp','media/cards/card-150-.webp','media/cards/card-150.png',
                    '/media/cards/card-150.webp','media/cards/card-150.v2.webp'):
            self.assertFalse(av048.ARTWORK_PATH.fullmatch(bad),bad)
        art=json.loads((ROOT/'docs/card-artwork-unique-prompts.json').read_text(encoding='utf-8'))
        self.assertTrue(all(av048.ARTWORK_PATH.fullmatch(asset['output']) for asset in art['assets']))

    def test_test_edits_apply_once_and_keep_the_earlier_edits_in_place(self):
        files=('tests/test_delivery.py','tests/artwork-uniqueness.test.mjs','tests/test_sxc024_update.py')
        texts={file:(ROOT/file).read_text(encoding='utf-8') for file in files}
        once,_=edit_tests(texts);twice,applied=edit_tests(once)
        self.assertEqual((twice,applied),(once,0))
        delivery=once['tests/test_delivery.py']
        self.assertIn('(0,3,11,14,26)',delivery)
        # The v0.48.0 line follows the semantic-crosscheck v0.24.0 line; the earlier lines stay, in order.
        self.assertIn("    ('v0.47.0','v0.21.1'):(56,53,7,149,269),\n    ('v0.47.0','v0.24.0'):(56,53,7,153,277),\n"
                      "    ('v0.48.0','v0.24.0'):(56,56,18,167,303),\n",delivery)
        self.assertIn("('v0.46.0','v0.21.1'):(56,53,5,147,264)",delivery)
        for identity in NEW_IDS:self.assertIn(f"'{identity}'",once['tests/artwork-uniqueness.test.mjs'])
        self.assertIn("self.skipTest('The live catalog is past the agentic-vault v0.47.0 snapshot",
                      once['tests/test_sxc024_update.py'])
        # The earlier helpers read the artwork test from its pre-commissioning fixture.
        earlier={'tests/test_delivery.py':delivery,'tests/artwork-uniqueness.test.mjs':
                 (ROOT/'tests/fixtures/artwork-v047-before-commissioning.mjs.txt').read_text(encoding='utf-8')}
        self.assertEqual(av047.edit_tests(earlier),(earlier,0))
        self.assertEqual(av046.edit_tests(earlier),(earlier,0))

if __name__=='__main__':unittest.main()
