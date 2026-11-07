import copy,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from reference_identity import find_matches
from update_av043_references import prepare_update,REFERENCES,EXISTING,RELEASE,NEW_IDS,PRIOR_USE_IDS

OLD='a'*40;NEW='b'*40
BLOB='https://github.com/Technoetic/agentic-vault/blob/'
def card(identity,url,file,line):
    row={'file':file,'line':line,'url':f'{BLOB}{OLD}/{file}#L{line}','excerpt':identity+' prior citation'}
    return {'id':identity,'kind':'project','title':identity,'url':url,'year':None,'keys':[identity],
            'aliases':[],'tags':[],'note':'Prior note.','uses':[{'plugin':'agentic-vault','role':'reference','evidence':[row]}]}
def fixture():
    sources=[card('github:git/git','https://github.com/git/git','README.md',1),
             card('github:python/cpython','https://github.com/python/cpython','README.md',2)]
    registry={'schemaVersion':1,'updatedAt':'old','sources':sources,
              'snapshots':{'agentic-vault':{'version':'v0.42.0','commit':OLD}}}
    artwork={'count':2,'assets':[{'sourceId':s['id'],'sha256':'imagehash','prompt':'original prompt',
        'generationEvidenceUrls':['historical-url'],'evidenceUrls':[s['uses'][0]['evidence'][0]['url']],
        'currentEvidenceUrls':[s['uses'][0]['evidence'][0]['url']]} for s in sources]}
    texts={'README.md':['inserted']+[s['id']+' prior citation' for s in sources]}
    for cites in [row[10] for row in REFERENCES]+[row[4] for row in EXISTING]:
        for file,needle in cites:texts.setdefault(file,[]).append('[source]('+needle+')')
    return registry,artwork,texts

class AV043Tests(unittest.TestCase):
    def prepare(self,registry,art,texts):return prepare_update(registry,art,texts.__getitem__,NEW,'v0.43.0',updated_at='fixed')
    def test_every_new_identity_is_release_cited_without_image_fabrication(self):
        registry,art,texts=fixture();before=copy.deepcopy((registry,art))
        revised,images,summary=self.prepare(registry,art,texts)
        self.assertEqual((registry,art),before)
        self.assertEqual(set(summary['addedSourceIds']),NEW_IDS)
        self.assertEqual(len(NEW_IDS),22)
        self.assertEqual(summary['uncommissionedSourceIds'],sorted(NEW_IDS))
        self.assertEqual(summary['counts']['citations'],2+sum(len(r[10]) for r in REFERENCES)+sum(len(r[4]) for r in EXISTING))
        self.assertEqual({a['sourceId'] for a in images['assets']},{a['sourceId'] for a in art['assets']})
        for source in revised['sources']:
            if source['id'] in NEW_IDS:
                self.assertEqual(source['uses'][0]['evidence'][0]['file'],RELEASE)
                self.assertTrue(source['uses'][0]['evidence'][0]['url'].startswith(BLOB+NEW+'/'))
    def test_prior_use_and_rejected_sources_keep_their_stated_relationship(self):
        revised,_,_=self.prepare(*fixture())
        by_id={s['id']:s for s in revised['sources']}
        self.assertEqual(len(PRIOR_USE_IDS),5)
        for identity in NEW_IDS:
            self.assertEqual('not a new discovery' in by_id[identity]['note'],identity in PRIOR_USE_IDS)
        self.assertEqual(by_id['github:logpai/drain3']['uses'][0]['role'],'background')
        self.assertIn('rejected',by_id['github:logpai/drain3']['note'])
        self.assertEqual(by_id['github:manuelschipper/nah']['uses'][0]['role'],'background')
        self.assertIn('Nothing was taken',by_id['github:manuelschipper/nah']['note'])
    def test_renamed_repository_and_git_manual_pages_resolve_to_one_card(self):
        revised,_,_=self.prepare(*fixture())
        for value,identity in (('https://github.com/steveyegge/beads','github:gastownhall/beads'),
                               ('https://github.com/gastownhall/beads/tree/v1.3.4','github:gastownhall/beads'),
                               ('https://git-scm.com/docs/git-update-ref','github:git/git'),
                               ('https://git-scm.com/docs/git-worktree','github:git/git'),
                               ('https://github.com/git/git/blob/fb25501/Documentation/git-config.adoc','github:git/git')):
            found=find_matches(revised,value)
            self.assertEqual((found['status'],[s['id'] for s in found['matches']]),('known',[identity]))
        beads=next(s for s in revised['sources'] if s['id']=='github:gastownhall/beads')
        self.assertIn('1074561042',beads['note'])
    def test_existing_cards_gain_uses_and_keep_artwork_history(self):
        registry,art,texts=fixture()
        revised,images,summary=self.prepare(registry,art,texts)
        self.assertEqual(summary['addedUsesOnExistingSources'],8)
        self.assertEqual(sum(s['id'] in {r[0] for r in EXISTING} for s in revised['sources']),2)
        by_id={s['id']:s for s in revised['sources']}
        git=by_id['github:git/git'];self.assertEqual(len(git['uses'][0]['evidence']),8)
        self.assertEqual(git['uses'][0]['evidence'][0]['line'],2)
        self.assertTrue(git['note'].startswith('Prior note. '))
        for old,new in zip(art['assets'],images['assets']):
            for field in ('sha256','prompt','generationEvidenceUrls'):self.assertEqual(old[field],new[field])
            current=[row['url'] for row in by_id[new['sourceId']]['uses'][0]['evidence']]
            self.assertEqual(new['evidenceUrls'],current);self.assertEqual(new['currentEvidenceUrls'],current)
    def test_repeat_is_idempotent(self):
        revised,images,_=self.prepare(*fixture())
        again,art,summary=self.prepare(revised,images,fixture()[2])
        self.assertEqual(again,revised);self.assertEqual(art,images)
        self.assertEqual((summary['addedSourceIds'],summary['addedUsesOnExistingSources']),([],0))
    def test_ambiguous_prior_excerpt_or_missing_new_evidence_fails_without_mutation(self):
        for kind in ('prior','new'):
            r,a,t=fixture();before=copy.deepcopy((r,a))
            if kind=='prior':t['README.md']=['no match']
            else:t[RELEASE]=[line for line in t[RELEASE] if '2606.22528' not in line]
            with self.assertRaises(ValueError):self.prepare(r,a,t)
            self.assertEqual((r,a),before)
    def test_new_citation_on_two_lines_is_refused(self):
        r,a,t=fixture();t[RELEASE].append('[again](https://arxiv.org/abs/2606.22528)')
        with self.assertRaisesRegex(ValueError,'one exact line'):self.prepare(r,a,t)
    def test_former_beads_identity_requires_review_instead_of_duplicate_card(self):
        r,a,t=fixture();r['sources'][0].update(id='github:steveyegge/beads',keys=['github:steveyegge/beads'],
            title='Beads',url='https://github.com/steveyegge/beads')
        a['assets'][0]['sourceId']='github:steveyegge/beads'
        with self.assertRaisesRegex(ValueError,'merge'):self.prepare(r,a,t)
    def test_unknown_artwork_active_evidence_is_rejected(self):
        r,a,t=fixture();a['assets'].append({'sourceId':'github:example/other','evidenceUrls':[f'{BLOB}{OLD}/missing.md#L1'],
            'currentEvidenceUrls':[f'{BLOB}{OLD}/missing.md#L1']});a['count']=3
        with self.assertRaises(ValueError):self.prepare(r,a,t)
    def test_wrong_tag_or_non_sha_cannot_prepare(self):
        r,a,t=fixture()
        for commit,tag in [('master','v0.43.0'),(NEW,'v0.42.0')]:
            with self.assertRaises(ValueError):prepare_update(r,a,t.__getitem__,commit,tag)

if __name__=='__main__':unittest.main()
