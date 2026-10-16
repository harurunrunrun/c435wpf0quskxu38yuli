#!/usr/bin/env python3
from collections import deque
from itertools import permutations
import json,time
start=time.time();checked=0

def greedy(seq):
 a=list(seq);answer=0
 while a:
  j=a.index(-a[0],1);answer+=j-1+(a[0]>0)
  del a[j];del a[0]
 return answer
for n in range(1,5):
 for first in range(n+1):
  seconds=n-first
  targets=set(permutations([1]*first+[2]*seconds))
  distance={tuple(v for size in target for v in (-size,size)):0 for target in targets}
  todo=deque(distance)
  while todo:
   state=todo.popleft();dist=distance[state]
   assert greedy(state)==dist,(state,greedy(state),dist)
   checked+=1
   for i in range(2*n-1):
    if state[i]==state[i+1]:continue
    next_state=state[:i]+(state[i+1],state[i])+state[i+2:]
    if next_state not in distance:distance[next_state]=dist+1;todo.append(next_state)
print(json.dumps({'shoesBalancedSignedSequencesTwoSizesLengthAtMost8':checked,'oracle':'multi-source BFS over every adjacent exchange, starting at every valid oriented-pair order','seconds':time.time()-start}))
