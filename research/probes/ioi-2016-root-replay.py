from pathlib import Path
import hashlib,json,re,subprocess,tempfile
from ioi_2016_snapshot import snapshot_baseline
_snapshot_holder,BASE=snapshot_baseline()
SPECS=[('molecules','ranges',['selected-elements']),('railroad','graphs',['walk-goals']),('shortcut','graphs',['network-connection']),('paint','dp',['sequence-removals','split']),('messy','interactive-oracles',['other']),('aliens','geometry',['enclosing-regions','point-set-shapes'])]
GRAPHS=json.loads((BASE/'data/flows.json').read_text());BY={g['id']:g for g in GRAPHS}
def options(node):return node.get('options',[{'id':a,'label':{'yes':'はい','no':'いいえ','unknown':'わからない'}.get(a,a)} for a in node.get('answers',{})])
def walk(entry,choices):
    graph=BY[entry];node=next(n for n in graph['nodes'] if n['id']==graph['root']);steps=[];consumed=0;routes=[]
    while True:
        if node['type']=='route':
            key=graph['id']+'/'+node['id'];assert key not in routes;routes.append(key);graph=BY[node['graph']];node=next(n for n in graph['nodes'] if n['id']==graph['root']);continue
        if node['type']!='question' or consumed==len(choices):break
        a=choices[consumed];label=next(o['label'] for o in options(node) if o['id']==a);target=node['answers'][a]
        steps.append({'graphId':graph['id'],'nodeId':node['id'],'question':node['title'],'answer':a,'answerLabel':label,'target':target});consumed+=1;node=next(n for n in graph['nodes'] if n['id']==target)
    assert consumed==len(choices)
    reached={'graphId':graph['id'],'nodeId':node['id'],'type':node['type'],'title':node['title'],'options':options(node),'techniques':node.get('techniques',[]),'conditions':node.get('conditions',[])}
    return {'officialTaskId':entry,'entryGraphId':entry,'choices':choices,'steps':steps,'stepsSha256':hashlib.sha256(json.dumps(steps,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),'reached':reached,'routeBoundaries':routes}
records={task:walk(entry,choices) for task,entry,choices in SPECS}
for task,row in records.items():row['officialTaskId']=task

print(json.dumps(records,ensure_ascii=False,indent=2))
