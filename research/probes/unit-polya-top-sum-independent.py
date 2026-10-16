#!/usr/bin/env python3
"""Actual-fence checks using integer partitions, exact label multiplicities and API-only memory."""
from pathlib import Path
from collections import Counter
from decimal import Decimal,localcontext
from fractions import Fraction
import hashlib,json,math,os,re,subprocess,tempfile,time
article=(Path(__file__).resolve().parents[2] / 'src/content/docs/techniques/polya-urn-uniform-composition-top-r-sum.mdx').read_text();cpp=re.findall(r'^```cpp\s*\n(.*?)^```\s*$',article,re.M|re.S);assert len(cpp)==1;cpp=cpp[0]
harness=r'''
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <new>
#include <iostream>
#include <string>
static bool counting=false;
static std::size_t live=0,peak=0;
struct alignas(std::max_align_t) Header {std::size_t size;bool tracked;};
[[gnu::noinline]] void* operator new(std::size_t n){auto* p=static_cast<Header*>(std::malloc(sizeof(Header)+(n?n:1)));if(!p)throw std::bad_alloc();p->size=n;p->tracked=counting;if(counting){live+=n;peak=std::max(peak,live);}return p+1;}
[[gnu::noinline]] void* operator new[](std::size_t n){return ::operator new(n);}
[[gnu::noinline]] void operator delete(void* ptr)noexcept{if(!ptr)return;auto*p=static_cast<Header*>(ptr)-1;if(p->tracked)live-=p->size;std::free(p);}
[[gnu::noinline]] void operator delete[](void*p)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete(void*p,std::size_t)noexcept{::operator delete(p);}
[[gnu::noinline]] void operator delete[](void*p,std::size_t)noexcept{::operator delete(p);}
int checks=0;
void require(bool yes){++checks;if(!yes)throw std::runtime_error("independent writer/memory check");}
struct Comma:std::numpunct<char>{char do_decimal_point()const override{return ',';}char do_thousands_sep()const override{return '.';}std::string do_grouping()const override{return "\3";}};
struct Short:std::streambuf{std::streamsize xsputn(const char*,std::streamsize n)override{return n-1;}};
struct Explodes:std::streambuf{std::streamsize xsputn(const char*,std::streamsize)override{throw std::runtime_error("custom stream failure");}};
int main(){
 counting=true;const double maximum=unit_polya::expected_top_r_unit_polya(500,500,250);counting=false;
 require(live==0);require(peak==752001*sizeof(double));require(maximum>746&&maximum<747);
 std::locale loc(std::locale::classic(),new Comma);std::ostringstream out;out.imbue(loc);out.setf(std::ios::showpos|std::ios::uppercase|std::ios::scientific);out.width(29);out.fill('@');out.precision(2);
 auto flags=out.flags();auto locale=out.getloc();unit_polya::write_expected_top_r(out,2,3,1);
 require(out.str()=="3.500000000000\n");require(out.flags()==flags);require(out.width()==29);require(out.fill()=='@');require(out.precision()==2);require(out.getloc()==locale);
 Short shortbuf;std::ostream shortstream(&shortbuf);shortstream.width(17);unit_polya::write_expected_top_r(shortstream,2,3,1);require(shortstream.bad());require(shortstream.width()==17);
 Short failbuf;std::ostream failstream(&failbuf);failstream.exceptions(std::ios::badbit);bool failed=false;try{unit_polya::write_expected_top_r(failstream,2,3,1);}catch(const std::ios_base::failure&){failed=true;}require(failed);
 Explodes exploding;std::ostream explosive(&exploding);explosive.exceptions(std::ios::badbit);failed=false;try{unit_polya::write_expected_top_r(explosive,2,3,1);}catch(const std::runtime_error& e){failed=std::string(e.what())=="custom stream failure";}require(failed);
 std::cout<<"{\"memoryWriterChecks\":"<<checks<<",\"apiOnlyPeakRequestedAllocationBytes\":"<<peak<<",\"doubleBytes\":"<<sizeof(double)<<",\"liveRequestedBytesAfterCall\":"<<live<<"}\n";
 int n,d,r;while(std::cin>>n>>d>>r)std::cout<<std::setprecision(17)<<unit_polya::expected_top_r_unit_polya(n,d,r)<<'\n';
}
'''
start=time.monotonic();requests=[];expected=[];partitions=labelled=parameter_pairs=0

def parts(total,upper=None):
 if total==0:yield ();return
 if upper is None:upper=total
 for head in range(min(total,upper),0,-1):
  for tail in parts(total-head,head):yield (head,)+tail

for d in [*range(21),25,30,35,40]:
 ns=[1,2,3,4,7,13,50,500]
 ranks={n:sorted({0,1,min(2,n),min(3,n),n//2,n-1,n}) for n in ns}
 mass={n:0 for n in ns};scores={n:[0]*len(ranks[n])for n in ns}
 falling={n:[1]for n in ns}
 for n in ns:
  for k in range(1,min(n,d)+1):falling[n].append(falling[n][-1]*(n-k+1))
 for part in parts(d):
  partitions+=1;k=len(part);divisor=math.prod(math.factorial(v)for v in Counter(part).values());prefix=[0]
  for v in part:prefix.append(prefix[-1]+v)
  for n in ns:
   if k>n:continue
   weight=falling[n][k]//divisor;assert weight*divisor==falling[n][k]
   mass[n]+=weight;labelled+=weight
   for j,r in enumerate(ranks[n]):scores[n][j]+=weight*(r+prefix[min(r,k)])
 for n in ns:
  denominator=math.comb(n+d-1,d);assert mass[n]==denominator;parameter_pairs+=1
  for j,r in enumerate(ranks[n]):requests.append((n,d,r));expected.append(Fraction(scores[n][j],denominator))
# An additional positive-only threshold formula for r=n-1: E[min x]
# = sum_t C(n+d-nt-1,d-nt)/C(n+d-1,d). No binomial inversion or peeling DP.
min_formula_cases=0
for n in [2,3,4,7,13,50,100,249,250,251,499,500]:
 for d in [n-1 if n>1 else 0,min(n,500),min(2*n,500),499,500]:
  den=math.comb(n+d-1,d);minimum=sum(math.comb(n+d-n*t-1,d-n*t)for t in range(1,d//n+1))
  requests.append((n,d,n-1));expected.append(Fraction(n+d-1)-Fraction(minimum,den));min_formula_cases+=1
with tempfile.TemporaryDirectory(prefix='flowchartcp-polya-independent-') as td:
 source=Path(td)/'probe.cpp';binary=Path(td)/'probe';source.write_text(cpp+'\n'+harness)
 subprocess.run(['g++','-std=c++20','-O2','-Wall','-Wextra','-Werror','-Wno-mismatched-new-delete',str(source),'-o',str(binary)],check=True)
 raw=subprocess.check_output([str(binary)],input=''.join(f'{n} {d} {r}\n'for n,d,r in requests),text=True)
 lines=raw.splitlines();memory=json.loads(lines[0]);values=lines[1:];assert len(values)==len(expected)
 maximum=Fraction(0);worst=None;checksum=0
 for request,want,line in zip(requests,expected,values):
  actual=Fraction.from_float(float(line));err=abs(actual-want)
  assert err<Fraction(559,10**10),request
  if err>maximum:maximum=err;worst=request
  checksum=(checksum*1000003+round(float(line)*10**6))%(1<<64)
with localcontext() as ctx:
 ctx.prec=110;u=Decimal(2)**-53;gamma=lambda m:Decimal(m)*u/(1-Decimal(m)*u)
 upper=(1+gamma(501501))*(1+u)/(1-gamma(1000))-1
 lower=1-(1-gamma(501501))*(1-u)/(1+gamma(1000))
 assert lower<=upper<Decimal('5.59e-11');assert upper*1000+Decimal('1e-12')<Decimal('1e-6')
 bound={'relativeUpper':str(upper),'relativeLowerMagnitude':str(lower),'absoluteWithSerializationUpper':str(upper*1000+Decimal('1e-12'))}
result={'articleSha256':hashlib.sha256(article.encode()).hexdigest(),'cppSha256':hashlib.sha256(cpp.encode()).hexdigest(),'method':'Nonincreasing integer partitions weighted by N!/(N-k)! / product(multiplicity!) over positive parts; literal top-r sums. No labeled weak-composition enumeration, owner-history enumeration, peeling recurrence, or inclusion-exclusion/marked-subset inversion.','integerPartitions':partitions,'parameterPairs':parameter_pairs,'expectedValueComparisons':len(requests),'additionalPositiveMinimumTailCases':min_formula_cases,'maximumExactRationalError':float(maximum),'worstParameters':worst,'checksum':str(checksum),'apiMemoryAndWriter':memory,'decimalErrorBoundRecalculation':bound,'seconds':time.monotonic()-start,'sanitizerForThisAdditionalProbe':False,'sharedOrAuthorArtifactsModified':False}
print(json.dumps(result,ensure_ascii=False,indent=2))
