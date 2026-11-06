import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from update_av042_references import prepare_update,REFERENCES,FILES,NEW_IDS

OLD='a'*40;NEW='b'*40
def fixture():
    url=f'https://github.com/Technoetic/agentic-vault/blob/{OLD}/README.md#L1'
    row={'file':'README.md','line':1,'url':url,'excerpt':'Prior exact citation'}
    source={'id':'github:example/prior','kind':'project','title':'Prior','url':'https://github.com/example/prior',
            'year':None,'keys':['github:example/prior'],'aliases':[],'tags':[],
            'uses':[{'plugin':'agentic-vault','role':'reference','evidence':[row]}]}
    registry={'schemaVersion':1,'updatedAt':'old','snapshots':{'agentic-vault':{'version':'v0.41.0','commit':OLD}},'sources':[source]}
    artwork={'count':1,'assets':[{'sourceId':source['id'],'sha256':'imagehash','prompt':'original prompt',
        'generationEvidenceUrls':['historical-url'],'evidenceUrls':[url],'currentEvidenceUrls':[url]}]}
    texts={file:[] for file in FILES};texts['README.md']=['inserted','Prior exact citation']
    for i,ref in enumerate(REFERENCES):
        texts[FILES[0]].append('[reference]('+ref[3]+')')
        if i in (1,2,4):texts[FILES[{1:1,2:2,4:3}[i]]].append('[guide]('+ref[3]+')')
    return registry,artwork,texts

class AV042Tests(unittest.TestCase):
    def prepare(self,registry,art,texts):return prepare_update(registry,art,texts.__getitem__,NEW,'v0.42.0',updated_at='fixed')
    def test_exact_lines_all_five_identities_eight_citations_and_no_image_fabrication(self):
        registry,art,texts=fixture();before=copy.deepcopy((registry,art))
        revised,images,summary=self.prepare(registry,art,texts)
        self.assertEqual((registry,art),before)
        self.assertEqual(set(summary['addedSourceIds']),NEW_IDS)
        self.assertEqual(summary['counts']['citations'],9)
        self.assertEqual(images['count'],1)
        self.assertEqual(len(images['assets']),1)
        old=art['assets'][0];new=images['assets'][0]
        for field in ('sha256','prompt','generationEvidenceUrls'):self.assertEqual(old[field],new[field])
        self.assertEqual(new['currentEvidenceUrls'],[f'https://github.com/Technoetic/agentic-vault/blob/{NEW}/README.md#L2'])
        dvc=next(s for s in revised['sources'] if s['id']=='github:treeverse/dvc')
        self.assertIn('github:iterative/dvc',dvc['keys'])
        self.assertIn('83878269',dvc['note']);self.assertIn('Already researched',dvc['note'])
    def test_repeat_is_idempotent_and_preserves_historical_artwork(self):
        revised,images,_=self.prepare(*fixture())
        again,art,_=self.prepare(revised,images,fixture()[2])
        self.assertEqual(again,revised);self.assertEqual(art,images)
    def test_ambiguous_prior_excerpt_or_missing_new_evidence_fails_without_mutation(self):
        for kind in ('prior','new'):
            r,a,t=fixture();before=copy.deepcopy((r,a))
            if kind=='prior':t['README.md']=['no match']
            else:t[FILES[0]]=[]
            with self.assertRaises(ValueError):self.prepare(r,a,t)
            self.assertEqual((r,a),before)
    def test_unknown_artwork_active_evidence_is_rejected(self):
        r,a,t=fixture();a['assets'][0]['currentEvidenceUrls']=[f'https://github.com/Technoetic/agentic-vault/blob/{OLD}/missing.md#L1']
        with self.assertRaises(ValueError):self.prepare(r,a,t)
    def test_dvc_former_identity_requires_review_instead_of_duplicate_card(self):
        r,a,t=fixture();r['sources'][0].update(id='github:iterative/dvc',keys=['github:iterative/dvc'],url='https://github.com/iterative/dvc')
        with self.assertRaisesRegex(ValueError,'merge'):self.prepare(r,a,t)
    def test_wrong_tag_or_non_sha_cannot_prepare(self):
        r,a,t=fixture()
        for commit,tag in [('master','v0.42.0'),(NEW,'v0.41.0')]:
            with self.assertRaises(ValueError):prepare_update(r,a,t.__getitem__,commit,tag)

    def test_complete_current_registry_repins_every_av_citation_and_preserves_all_art_history(self):
        registry=json.loads((ROOT/'data/registry.source.json').read_text(encoding='utf-8'))
        art=json.loads((ROOT/'docs/card-artwork-unique-prompts.json').read_text(encoding='utf-8'))
        # Keep this regression about the prior citations after a future real
        # apply too. New-reference idempotence is checked separately above;
        # truncated stored excerpts cannot reconstruct full new URL lines.
        registry['sources']=[s for s in registry['sources'] if s['id'] not in NEW_IDS]
        # Synthetic exact-blob reader built from committed excerpts; no fake public
        # registry is written and no local unpublished plugin tree is required.
        texts={file:[] for file in FILES};prior=[]
        for source in registry['sources']:
            for use in source['uses']:
                if use['plugin']!='agentic-vault':continue
                for row in use['evidence']:
                    prior.append(row);lines=texts.setdefault(row['file'],[])
                    lines.extend(['']*max(0,row['line']-len(lines)))
                    excerpt=row['excerpt']+('#' if len(row['excerpt'])==220 else '')
                    self.assertIn(lines[row['line']-1],('',excerpt))
                    lines[row['line']-1]=excerpt
        for index,ref in enumerate(REFERENCES):
            for file in [FILES[0]]+([FILES[{1:1,2:2,4:3}[index]]] if index in (1,2,4) else []):
                if not any(ref[3] in line for line in texts[file]):texts[file].append('[new]('+ref[3]+')')
        revised,images,summary=self.prepare(registry,art,texts)
        self.assertEqual(summary['priorAgenticVaultCitations'],len(prior))
        self.assertEqual(len(images['assets']),len(art['assets']))
        for old,new in zip(art['assets'],images['assets']):
            self.assertEqual({k:v for k,v in old.items() if k not in ('evidenceUrls','currentEvidenceUrls')},
                             {k:v for k,v in new.items() if k not in ('evidenceUrls','currentEvidenceUrls')})
        def sxc(data):return [(s['id'],u) for s in data['sources'] for u in s['uses'] if u['plugin']=='semantic-crosscheck']
        self.assertEqual(sxc(registry),sxc(revised))
        self.assertEqual(registry['snapshots']['semantic-crosscheck'],revised['snapshots']['semantic-crosscheck'])

if __name__=='__main__':unittest.main()
