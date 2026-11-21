#!/usr/bin/env python3
"""x86js.py - static recompiler: objdump (intel) listing of the original's code -> JavaScript (web/js/plastik-d.gen.mjs).
Only the instruction subset scene D needs (integer + x87).  Usage: x86js.py OUT.mjs LISTING.dis... -- ENTRY...   (see re/NOTES.md)
Registers/flags/x87 stack are module globals, memory is one flat DataView (rt.mjs).  x87 ops are decoded from the opcode bytes, not the text
(objdump's fsub/fdiv mnemonics are reversed in some forms).  Natives (calls we do not translate) are named in NATIVE."""
import re,sys
NATIVE={0x51c7a:'f[S.sp]=Math.trunc(f[S.sp]);',0x51cad:'R.n_fpatan();',0x51e3c:'R.n_present();',0x29c20:'',0x2accc:'S.blk(edi);',0x3d220:'eax=R.n_pos();',
  # scene A: fmod(x,y) wrapper around fprem; keyboard port read (no key); debug printf; memset(eax,dl,ebx)
  0x54b14:'f[S.sp+1]=f[S.sp]%f[S.sp+1];S.sp++;',0x52134:'R.n_copy(eax,edx,ebx);',   # memcpy(dst=eax,src=edx,n=ebx) (rep movsd+movsb)
  0x536e9:'eax=0;',0x536f1:'eax=R.n_sprintf(rd32(esp),rd32(esp+4),esp+8);',0x28028:'R.n_blend(eax,ebx,ecx,edx,rd32(esp));esp=(esp+4)|0;',0x536d1:'R.n_fill(edx&255,eax,ebx);edx=Math.imul(edx&255,0x01010101);'}   # call+ret net zero: no esp change
R32=['eax','ecx','edx','ebx','esp','ebp','esi','edi']
R16={'ax':'eax','cx':'ecx','dx':'edx','bx':'ebx','si':'esi','di':'edi','bp':'ebp','sp':'esp'}
R8L={'al':'eax','cl':'ecx','dl':'edx','bl':'ebx'}; R8H={'ah':'eax','ch':'ecx','dh':'edx','bh':'ebx'}
ins={}
BIN=None
def parse(lines,over=True):
    last=None
    for l in lines:
        p=l.rstrip('\n').split('\t')
        if len(p)>=3 and re.match(r'\s*[0-9a-f]+:',p[0]):
            a=int(p[0].strip().rstrip(':'),16); last=a if (over or a not in ins) else None
            if last is None: continue
            t=p[2].split(); m=t[0]; o=''.join(p[2].split(None,1)[1:]).split('#')[0].strip() if len(t)>1 else ''
            ins[a]=[bytes.fromhex(p[1].strip().replace(' ','')),m,o]
        elif len(p)==2 and last in ins and re.match(r'\s*[0-9a-f]+:',p[0]): ins[last][0]+=bytes.fromhex(p[1].strip().replace(' ',''))
def ensure(a):   # disassemble from a (a listing made from offset 0 loses sync inside data islands: re-sync at every entry/target we reach)
    if a in ins or BIN is None: return
    import subprocess
    r=subprocess.run(['objdump','-D','-b','binary','-m','i386','-M','intel','--adjust-vma=0','--start-address=%d'%a,'--stop-address=%d'%(a+0x1000),BIN],capture_output=True,text=True).stdout
    before=set(ins); parse(r.split('\n'),over=False)
    new=sorted(set(ins)-before)
    if new and new[-1]+len(ins[new[-1]][0])>=a+0x1000: del ins[new[-1]]   # only an instruction reaching the stop address may be cut by it
for fn in sys.argv[2:sys.argv.index('--')]:
    if fn.endswith('.bin'): BIN=fn
    else: parse(open(fn))
class Nxt:
    def __getitem__(s,a): return a+len(ins[a][0])
    def get(s,a,d=None): return a+len(ins[a][0]) if a in ins else d
nxt=Nxt()
def num(s): return int(s,16) if s.lower().startswith('0x') else int(s)
def memexpr(s):   # [..] or ds:0x..  -> JS address expression
    m=re.search(r'ds:(0x[0-9a-f]+)',s)
    if m: return m.group(1)
    m=re.search(r'\[(.*)\]',s); terms=re.findall(r'([+-]?)([a-z0-9*]+)',m.group(1)); out=[]
    for sg,t in terms:
        sg=sg or '+'
        if '*' in t: r,sc=t.split('*'); e='(%s*%s)'%(r,sc)
        else: e=t
        out.append(sg+e)
    return '('+''.join(out).lstrip('+')+'|0)'
SZ={'BYTE':8,'WORD':16,'DWORD':32,'QWORD':64}
def opnd(s,size=None):
    """-> (kind,expr,size,assign-format) ; kind reg/mem/imm"""
    s=s.strip()
    m=re.match(r'(BYTE|WORD|DWORD|QWORD) PTR (.*)',s)
    if m: return ('mem',memexpr(m.group(2)),SZ[m.group(1)])
    if s in R32: return ('reg',s,32)
    if s in R16: return ('reg',s,16)
    if s in R8L or s in R8H: return ('reg',s,8)
    if re.match(r'^-?(0x[0-9a-f]+|\d+)$',s): return ('imm',str(num(s)),size or 32)
    if s.startswith('[') or 'ds:' in s: return ('mem',memexpr(s),size or 32)
    raise Exception('operand '+s)
def get(o):
    k,e,sz=o
    if k=='imm': return e
    if k=='mem': return {8:'rd8(%s)',16:'rd16(%s)',32:'rd32(%s)'}[sz]%e
    if e in R32: return e
    if e in R16: return '(%s&0xffff)'%R16[e]
    if e in R8L: return '(%s&0xff)'%R8L[e]
    return '((%s>>8)&0xff)'%R8H[e]
def put(o,v):
    k,e,sz=o
    if k=='mem': return {8:'wr8(%s,%s);',16:'wr16(%s,%s);',32:'wr32(%s,%s);'}[sz]%(e,v)
    if e in R32: return '%s=(%s)|0;'%(e,v)
    if e in R16: r=R16[e]; return '%s=(%s&~0xffff)|((%s)&0xffff);'%(r,r,v)
    if e in R8L: r=R8L[e]; return '%s=(%s&~0xff)|((%s)&0xff);'%(r,r,v)
    r=R8H[e]; return '%s=(%s&~0xff00)|(((%s)&0xff)<<8);'%(r,r,v)
def sx(v,sz): return '(%s)'%v if sz==32 else ('((%s)<<%d>>%d)'%(v,32-sz,32-sz))
def zx(v,sz): return '(%s)'%v if sz==32 else '((%s)&%s)'%(v,hex((1<<sz)-1))
COND={'e':'zf','ne':'!zf','l':'(sf!==of)','ge':'(sf===of)','le':'(zf||sf!==of)','g':'(!zf&&sf===of)','b':'cf','ae':'!cf','be':'(cf||zf)','a':'(!cf&&!zf)','s':'sf','ns':'!sf','z':'zf','nz':'!zf','c':'cf','nc':'!cf','p':'pf','np':'!pf','pe':'pf','po':'!pf'}
def fl(sz,res,cfe='0',ofe='0'):   # flags from a result expression (already computed into t)
    sh=sz-1
    return 'zf=(%s)===0;sf=((%s)>>>%d&1)===1;cf=%s;of=%s;'%(zx('t',sz) if sz<32 else 't',zx('t',sz) if sz<32 else 't',sh,cfe,ofe)
def gen(a):
    b,m,o=ins[a]; n=nxt[a]; ops=[x.strip() for x in re.split(r',(?![^\[]*\])',o)] if o else []
    if b[0]>=0xd8 and b[0]<=0xdf: return fpu(a,b,m,o)
    if len(ops)==2 and m not in('lea','movzx','movsx'):   # a bare memory operand takes the size of the register operand
        for i in (0,1):
            r=ops[1-i]; w=32 if r in R32 else 16 if r in R16 else 8 if (r in R8L or r in R8H) else 0
            if w and 'PTR' not in ops[i] and ('ds:' in ops[i] or ops[i].startswith('[')): ops[i]={8:'BYTE',16:'WORD',32:'DWORD'}[w]+' PTR '+ops[i]
    if m in('push','pop') and ops[0] in('ds','fs','gs','es'): return 'esp=(esp-4)|0;wr32(esp,0x860);' if m=='push' else 'esp=(esp+4)|0;'
    if m=='mov' and ops[1] in('ds','es','fs','gs','ss'): d=opnd(ops[0]); return put(d,'0x860')
    if m=='fstsw': return 'eax=(eax&~0xffff)|S.fsw;' if ops[0]=='ax' else 'wr16(%s,S.fsw);'%memexpr(ops[0])
    if m=='mov' and ops[0]=='es': return ''
    if m=='mov':
        d=opnd(ops[0]); s=opnd(ops[1],d[2]); return put(d,get(s))
    if m in('movzx','movsx'):
        d=opnd(ops[0]); s=opnd(ops[1]); return put(d,get(s) if m=='movzx' else sx(get(s),s[2]))
    if m=='lea': d=opnd(ops[0]); return put(d,memexpr(ops[1]))
    if m in('add','sub','cmp','and','or','xor','test','adc','sbb'):
        d=opnd(ops[0]); s_=opnd(ops[1],d[2]); sz=d[2]; mk=hex((1<<sz)-1); sb=sz-1
        r='a_=(%s)>>>0;b_=(%s)>>>0;'%(get(d) if sz==32 else get(d),get(s_) if s_[0]!='imm' else str(int(get(s_))&((1<<sz)-1)))
        if sz<32: r='a_=%s;b_=%s;'%(get(d),get(s_) if s_[0]!='imm' else str(int(get(s_))&((1<<sz)-1)))
        if m in('add','adc'):
            c='(cf?1:0)' if m=='adc' else '0'; r+='q_=a_+b_+%s;t=%s;cf=q_>%s;of=(((a_^t)&(b_^t))>>>%d&1)===1;'%(c,'q_|0' if sz==32 else 'q_&'+mk,mk,sb)
        elif m in('sub','cmp','sbb'):
            c='(cf?1:0)' if m=='sbb' else '0'; r+='q_=a_-b_-%s;t=%s;cf=q_<0;of=(((a_^b_)&(a_^t))>>>%d&1)===1;'%(c,'q_|0' if sz==32 else 'q_&'+mk,sb)
        else:
            op={'and':'&','or':'|','xor':'^','test':'&'}[m]; r+='t=(a_%sb_)%s;cf=false;of=false;'%(op,'|0' if sz==32 else '&'+mk)
        r+='zf=(t%s)===0;sf=((t>>>%d)&1)===1;'%('' if sz==32 else '&'+mk,sb)
        if m not in('cmp','test'): r+=put(d,'t')
        return r
    if m in('inc','dec'):
        d=opnd(ops[0]); sz=d[2]; op='+' if m=='inc' else '-'
        return 'a_=%s;t=(a_%s1)|0;zf=%s===0;sf=((%s)>>>%d&1)===1;of=%s;'%(zx(get(d),sz),op,zx('t',sz),zx('t',sz),sz-1,'a_===%s'%('0x7fffffff' if m=='inc' else '-0x80000000') if sz==32 else 'false')+put(d,'t')
    if m=='not': d=opnd(ops[0]); return put(d,'~'+get(d))
    if m in('ror','rol'):
        d=opnd(ops[0]); k=num(ops[1])&31; sz=d[2]
        if sz!=32 or not k: raise Exception('rot')
        v=get(d); return put(d,'(%s>>>%d|%s<<%d)'%(v,k,v,32-k) if m=='ror' else '(%s<<%d|%s>>>%d)'%(v,k,v,32-k))   # flags not modelled (only used as a byte shuffle here)
    if m=='neg': d=opnd(ops[0]); sz=d[2]; return 'a_=%s;t=(-a_)|0;cf=a_!==0;of=false;zf=t===0;sf=t<0;'%get(d)+put(d,'t')
    if m in('shl','shr','sar'):
        d=opnd(ops[0]); sz=d[2]; c=ops[1]; k=str(num(c)) if re.match(r'^(0x)?[0-9a-f]+$',c) else None
        if k is None and c=='cl' and sz==32:   # variable count: flags untouched when the count is 0
            v=get(d); sh={'shl':'(a_<<k_)|0','shr':'(a_>>>k_)|0','sar':'(a_>>k_)|0'}[m]; cfx={'shl':'(a_>>>(32-k_))&1','shr':'(a_>>>(k_-1))&1','sar':'(a_>>(k_-1))&1'}[m]
            return '{const k_=ecx&31;if(k_){a_=%s;t=%s;cf=(%s)===1;zf=t===0;sf=t<0;of=false;%s}}'%(v,sh,cfx,put(d,'t'))
        if k is None: raise Exception('shift by '+c)
        k=int(k)&31
        if not k: return ''
        v=get(d)
        if m=='shl': r='a_=%s;t=(a_<<%d)|0;cf=((a_>>>%d)&1)===1;'%(v,k,32-k)
        elif m=='shr': r='a_=%s;t=(a_>>>%d)|0;cf=((a_>>>%d)&1)===1;'%(zx(v,sz),k,k-1)
        else: r='a_=%s;t=(a_>>%d)|0;cf=((a_>>%d)&1)===1;'%(sx(v,sz),k,k-1)
        return r+'zf=%s===0;sf=((%s)>>>%d&1)===1;of=false;'%(zx('t',sz),zx('t',sz),sz-1)+put(d,'t')
    if m=='imul':
        d=opnd(ops[0])
        if len(ops)==2: s=opnd(ops[1]); return put(d,'Math.imul(%s,%s)'%(get(d),get(s)))
        if len(ops)==3: s=opnd(ops[1]); i=opnd(ops[2]); return put(d,'Math.imul(%s,%s)'%(get(s),i[1]))
        s=opnd(ops[0]); return 'a_=%s;t=Math.imul(eax,a_);q_=R.imulhi(eax,a_);cf=of=q_!==(t>>31);edx=q_;eax=t;'%get(s)
    if m=='cdq': return 'edx=eax>>31;'
    if m=='div': s=opnd(ops[0]); return 'a_=%s>>>0;b_=edx>>>0;if(b_<0x200000){t=b_*4294967296+(eax>>>0);q_=Math.floor(t/a_);r_=t-q_*a_;if(r_<0){q_--;r_+=a_;}else if(r_>=a_){q_++;r_-=a_;}}else{t=(BigInt(b_)<<32n)|BigInt(eax>>>0);q_=Number(t/BigInt(a_));r_=Number(t%%BigInt(a_));}eax=q_|0;edx=r_|0;'%get(s)
    if m=='sete' or m.startswith('set') and m[3:] in COND: d=opnd(ops[0]); return put(d,'(%s?1:0)'%COND[m[3:]])
    if m in('rep','repnz') and o.startswith('movs DWORD'): return 't=ecx>>>0;R.n_copy(edi,esi,t*4);esi=(esi+t*4)|0;edi=(edi+t*4)|0;ecx=0;'
    if m in('rep','repnz') and o.startswith('movs BYTE'): return 't=ecx>>>0;R.n_copy(edi,esi,t);esi=(esi+t)|0;edi=(edi+t)|0;ecx=0;'
    if m=='repnz' and o.startswith('scas al'): return 'for(;ecx!==0;){t=R.m8[edi]-(eax&255);edi=(edi+1)|0;ecx=(ecx-1)|0;if(t===0)break;}zf=t===0;'
    if m=='int' and ops[0]=='0x21': return "b_=(eax>>8)&255;if(b_===0x2c){S.clk=(S.clk|0)+1;t=Math.floor(S.clk/10);ecx=(10<<8)|((Math.floor(t/6000))%60);edx=((Math.floor(t/100)%60)<<8)|(t%100);}else if(b_===0x2a){ecx=1997;edx=(4<<8)|4;eax=(eax&~0xffff)|0x2a05;}else throw new Error('int21 '+b_.toString(16));"
    if m=='idiv': s=opnd(ops[0]); return 'q_=Math.trunc((edx*4294967296+(eax>>>0))/%s);r_=(edx*4294967296+(eax>>>0))-q_*%s;eax=q_|0;edx=r_|0;'%(get(s),get(s))
    if m=='push': s=opnd(ops[0]); return 'r_=%s;esp=(esp-4)|0;wr32(esp,r_);'%get(s)   # value first: push [esp+x] addresses the old esp
    if m=='pop': d=opnd(ops[0]); return 'a_=rd32(esp);esp=(esp+4)|0;'+put(d,'a_')
    if m=='pusha': return 't=esp;'+''.join('esp=(esp-4)|0;wr32(esp,%s);'%('t' if r=='esp' else r) for r in R32)
    if m=='popa': return ''.join('esp=(esp+4)|0;'+('' if r=='esp' else '%s=rd32(esp-4);'%r) for r in reversed(R32))
    if m=='pushaw': return 'esp=(esp-16)|0;wr16(esp+14,eax);wr16(esp+12,ecx);wr16(esp+10,edx);wr16(esp+8,ebx);wr16(esp+6,esp);wr16(esp+4,ebp);wr16(esp+2,esi);wr16(esp,edi);'
    if m=='popaw': return 'edi=(edi&~0xffff)|rd16(esp);esi=(esi&~0xffff)|rd16(esp+2);ebp=(ebp&~0xffff)|rd16(esp+4);ebx=(ebx&~0xffff)|rd16(esp+8);edx=(edx&~0xffff)|rd16(esp+10);ecx=(ecx&~0xffff)|rd16(esp+12);eax=(eax&~0xffff)|rd16(esp+14);esp=(esp+16)|0;'
    if m=='rep' and o.startswith('stos BYTE'): return 't=ecx>>>0;R.n_fill(eax&255,edi,t);edi=(edi+t)|0;ecx=0;'
    if m=='movs' and o.startswith('DWORD'): return 'wr32(edi,rd32(esi));esi=(esi+4)|0;edi=(edi+4)|0;'
    if m=='rep' and o.startswith('stos WORD'): return 't=ecx>>>0;if(t){if(edi&1){for(;t>0;t--){wr16(edi,eax&0xffff);edi=(edi+2)|0;}}else{new Uint16Array(R.buf,edi,t).fill(eax&0xffff);edi=(edi+t*2)|0;}}ecx=0;'   # direction flag clear
    if m=='sahf': return 'pf=(eax>>10&1)===1;cf=(eax>>8&1)===1;zf=(eax>>14&1)===1;sf=(eax>>15&1)===1;'
    if m=='fwait': return ''
    if m=='clc': return 'cf=false;'
    if m=='cmc': return 'cf=!cf;'
    if m=='cld': return ''
    if m in('rcl','rcr') and ops[1]=='1': d=opnd(ops[0]); sz=d[2]; v=get(d); return ('a_=%s;t=((a_<<1)|(cf?1:0));cf=((a_>>>%d)&1)===1;'%(v,sz-1) if m=='rcl' else 'a_=%s;t=(a_>>>1)|(cf?%d:0);cf=(a_&1)===1;'%(zx(v,sz),1<<(sz-1)))+put(d,'t')
    if m=='xchg': d=opnd(ops[0]); s=opnd(ops[1],d[2]); return 't=%s;'%get(d)+put(d,get(s))+put(s,'t')
    if m=='lods': return 'eax=(eax&~0xff)|R.m8[esi];esi=(esi+1)|0;'
    if m=='nop' or m=='xchg' and ops[0]==ops[1]: return ''
    if m=='jmp': return 'pc=%s;continue;'%hex(num(ops[0].split()[0]))
    if m.startswith('j') and m[1:] in COND: return 'if(%s){pc=%s;continue;}'%(COND[m[1:]],hex(num(ops[0].split()[0])))
    if m=='call' and not re.match(r'^(0x)?[0-9a-f]+$',o.split()[0]):   # indirect: through FT (every generated function), so the targets must be extra entries
        tg='rd32(%s)'%memexpr(o) if 'PTR' in o else o.strip()
        return 'esp=(esp-4)|0;(FT[%s]||R.bad(%s))();'%(tg,tg)
    if m=='call':
        t=num(ops[0].split()[0]); return NATIVE[t] if t in NATIVE else 'esp=(esp-4)|0;f_%x();'%t
    if m=='ret': k=num(ops[0]) if ops else 0; return 'esp=(esp+%d)|0;return;'%(4+k)
    raise Exception('unhandled %s %s @%x'%(m,o,a))
def fpu(a,b,m,o):
    r=fpu_(a,b,m,o)
    return re.sub(r'(?<![A-Za-z_.])sp(?![A-Za-z_])','S.sp',r).replace('eax=(eax&~0xffff)|fsw;','eax=(eax&~0xffff)|S.fsw;').replace('S.sp++','S.sp+=S.sp<8')   # popping an empty stack stays empty (x87 underflow; F's 0x3d56c pops 4 extra values every frame)
def fpu_(a,b,m,o):
    o0=b[0]; mod=b[1]>>6; reg=(b[1]>>3)&7; i=b[1]&7
    mem=re.search(r'(BYTE|WORD|DWORD|QWORD|TBYTE) PTR (.*)',o)
    if mod!=3:
        ad=memexpr(mem.group(2)); ar={0xd8:('rdf32',32),0xdc:('rdf64',64),0xd9:('rdf32',32),0xdd:('rdf64',64),0xdb:('rd32',32),0xdf:('rd16',16),0xda:('rd32',32),0xde:('rd16',16)}[o0]
        arith=['add','mul','com','comp','sub','subr','div','divr']
        if o0 in(0xd8,0xdc):
            rd='%s(%s)'%(ar[0],ad)
            if reg in(2,3): return 'fp_com(%s);'%rd+('sp++;' if reg==3 else '')
            return 'fp_%s(%s);'%(arith[reg],rd)
        if o0==0xd9:
            if reg==0: return 'fpush(rdf32(%s));'%ad
            if reg==2: return 'wrf32(%s,f[sp]);'%ad
            if reg==3: return 'wrf32(%s,f[sp]);sp++;'%ad
            if reg==5: return ''  # fldcw: CW is constant in our model (0x127f; frndint is native)
            if reg==7: return 'wr16(%s,0x127f);'%ad
        if o0==0xdd:
            if reg==0: return 'fpush(rdf64(%s));'%ad
            if reg==2: return 'wrf64(%s,f[sp]);'%ad
            if reg==3: return 'wrf64(%s,f[sp]);sp++;'%ad
            if reg==7: return 'wr16(%s,S.fsw);'%ad
        if o0==0xdb:
            if reg==0: return 'fpush(rd32(%s)|0);'%ad
            if reg in(2,3): return 'wr32(%s,fist(f[sp]));%s'%(ad,'sp++;' if reg==3 else '')
            if reg==5: return 'fpush(R.rdf80(%s));'%ad
        if o0==0xdf and reg==0: return 'fpush(sx16(rd16(%s)));'%ad
        if o0==0xdf and reg==7: return 'wrf64i(%s,f[sp]);sp++;'%ad   # fistp qword
        raise Exception('fpu mem %x /%d %s @%x'%(o0,reg,o,a))
    arith=['add','mul','com','comp','sub','subr','div','divr']
    if o0==0xd8: return 'fp_%s_st(%d);'%(arith[reg],i) if reg not in(2,3) else ('fp_com_st(%d);'%i if reg==2 else 'fp_com_st(%d);sp++;'%i)
    if o0==0xdc:   # st(i) = st(i) op st0 ; reg 4/5 and 6/7 swapped vs d8
        nm={0:'add',1:'mul',4:'subr',5:'sub',6:'divr',7:'div'}[reg]; return 'fp_%s_to(%d);'%(nm,i)
    if o0==0xde:
        if reg==3 and i==1: return 'fp_com_st(1);sp+=2;'
        nm={0:'add',1:'mul',4:'subr',5:'sub',6:'divr',7:'div'}[reg]; return 'fp_%s_to(%d);sp++;'%(nm,i)
    if o0==0xd9:
        if reg==0: return 'fpush(f[sp+%d]);'%i
        if reg==1: return 'fxch(%d);'%i
        t={(4,0):'f[sp]=-f[sp];',(4,1):'f[sp]=Math.abs(f[sp]);',(5,0):'fpush(1);',(5,6):'fpush(0);',(7,2):'f[sp]=Math.sqrt(f[sp]);',(7,6):'f[sp]=Math.sin(f[sp]);',(7,7):'f[sp]=Math.cos(f[sp]);',(7,4):'f[sp]=Math.trunc(f[sp]);',(4,4):'R.fp_com(0);',(5,3):'fpush(Math.PI);',(6,2):'f[sp]=Math.tan(f[sp]);fpush(1);S.fsw&=~0x400;',(7,0):'f[sp]=f[sp]%f[sp+1];S.fsw&=~0x400;'}
        if (reg,i) in t: return t[(reg,i)]
        raise Exception('fpu d9 %x %x @%x'%(reg,i,a))
    if o0==0xdd:
        if reg==3: return 'f[sp+%d]=f[sp];sp++;'%i
        if reg==2: return 'f[sp+%d]=f[sp];'%i
    if o0==0xdf and b[1]==0xe0: return 'eax=(eax&~0xffff)|fsw;'
    raise Exception('fpu reg %x %x @%x %s'%(o0,b[1],a,o))
FW={'add','sub','cmp','and','or','xor','test','neg','shl','shr','sar'}   # overwrite all flags we model
FR={'adc','sbb','rcl','rcr','cmc','sahf_','lahf','pushf'}
def live(a,depth=60):
    """may the flags set by the instruction at a be read before being overwritten?  (conservative: unknown -> True)"""
    a=nxt.get(a)
    while depth>0 and a in ins:
        m=ins[a][1]; depth-=1
        if m.startswith('j') and m[1:] in COND: return True
        if m in FR or m.startswith('set') or m.startswith('cmov'): return True
        if m=='jmp': a=num(ins[a][2].split()[0]); continue
        if m in('ret','call'): return False
        if m in FW: return False
        a=nxt.get(a)
    return True
def strip(code):
    code=re.sub(r'(?<![A-Za-z_.])(?:cf|of|zf|sf)=[^;]*;','',code)
    for v in ('a_','b_'):   # operand temporaries only the flags used
        if not re.search(r'(?<![A-Za-z_])%s(?!=)'%v,code): code=re.sub(r'(?<![A-Za-z_])%s=[^;]*;'%v,'',code)
    return code
def reach(entry):
    seen=set(); todo=[entry]; calls=set()
    while todo:
        a=todo.pop()
        ensure(a)
        while a in ins and a not in seen:
            seen.add(a); b,m,o=ins[a]
            if m=='call':
                if re.match(r'^(0x)?[0-9a-f]+$',o.split()[0]):
                    t=num(o.split()[0])
                    if t not in NATIVE: calls.add(t)
            if m=='jmp' or (m.startswith('j') and m[1:] in COND):
                todo.append(num(o.split()[0])); ensure(todo[-1])
            if m=='jmp' or m=='ret': break
            a=nxt[a]; ensure(a)
    return sorted(seen),calls
# INLINE: native code placed at an instruction of a recompiled function; (js, pc to continue at).  Hand ports of hot loops, checked by the frame diffs.
INLINE={0x2884c:('{const m=R.m8,dv=R.dv;let b0=0;for(let n=ecx;n>0;n--){b0=m[edi];eax=(dv.getUint16(ebp+m[edi+1]*2,true)<<16)|dv.getUint16(ebp+b0*2,true);dv.setInt32(esi,eax,true);esi=(esi+4)|0;edi=(edi+2)|0;}ebx=b0;ecx=0;zf=true;sf=false;cf=false;of=false;}',0x2886b),
  0x26eb3:('{const m=R.m8,dv=R.dv;let b0=0;for(let n=ecx;n>0;n--){b0=m[edi];eax=(dv.getUint16(ebp+m[edi+1]*2,true)<<16)|dv.getUint16(ebp+b0*2,true);dv.setInt32(esi,eax,true);esi=(esi+4)|0;edi=(edi+2)|0;}ebx=b0;ecx=0;zf=true;sf=false;cf=false;of=false;}',0x26ed2),
  0x29225:('{const m=R.m8,dv=R.dv;let b0=0;for(let n=ecx;n>0;n--){b0=m[edi];eax=(dv.getUint16(ebp+m[edi+1]*2,true)<<16)|dv.getUint16(ebp+b0*2,true);dv.setInt32(esi,eax,true);esi=(esi+4)|0;edi=(edi+2)|0;}ebx=b0;ecx=0;zf=true;sf=false;cf=false;of=false;}',0x29244),
  0x29866:('{const m=R.m8,dv=R.dv;let b0=0;for(let n=ecx;n>0;n--){b0=m[edi];eax=(dv.getUint16(ebp+m[edi+1]*2,true)<<16)|dv.getUint16(ebp+b0*2,true);dv.setInt32(esi,eax,true);esi=(esi+4)|0;edi=(edi+2)|0;}ebx=b0;ecx=0;zf=true;sf=false;cf=false;of=false;}',0x29885),
  # F: clamp-to-byte pass (running 16-bit sum of words -> byte, saturating at 255), then the two-pixel palette lookup through a 64K word table
  0x2256d:('{const dv=R.dv,m=R.m8,eu=eax&~0xffff;let ax=eax&0xffff;for(;;){ax=(ax+dv.getUint16(esi,true))&0xffff;ebx=eu|ax;if((ebx>>8)&255)ebx=255;m[edi]=ebx&255;esi=(esi+2)|0;edi=(edi+1)|0;ecx=(ecx-1)|0;if(ecx===0)break;}eax=eu|ax;zf=true;sf=false;of=false;}',0x22585),
  0x225bf:('{const dv=R.dv,m=R.m8;let hi=0,lo=0,bx=ebx&0xffff;for(;;){bx=m[esi+1]|(m[ebp+1]<<8);hi=dv.getUint16(0xcfe080+bx*2,true);bx=m[esi]|(m[ebp]<<8);lo=dv.getUint16(0xcfe080+bx*2,true);dv.setInt32(edi,(hi<<16)|lo,true);edi=(edi+4)|0;esi=(esi+2)|0;ebp=(ebp+2)|0;ecx=(ecx-2)|0;if(ecx===0)break;}ebx=(ebx&~0xffff)|bx;eax=(hi<<16)|lo;zf=true;sf=false;cf=false;of=false;}',0x225ed),
  # 0x3d7c1: textured scanline loop (two 16.16-ish packed coordinates, 16-bit texel copy), ecx runs from -n to 0
  0x3d7c1:('{const m=R.dv,A=rd32(0xebe928),B=rd32(0xebe930);let dx=0;for(;;){eax=(eax+A)|0;ebx=(ebx+B)|0;ebp>>>=16;eax&=0xf8077fff;ebx&=0x7f87fff;ecx=(ecx+1)|0;dx=m.getUint16(esi+ebp*2,true);ebp=(eax+ebx)|0;m.setUint16(edi+ecx*2,dx,true);if(ecx===0)break;}edx=(edx&~0xffff)|dx;zf=true;sf=false;of=false;}',0x3d7e9),
  # 0x5227c inner loop: anti-aliased line, two saturating byte adds per step (coverage = top byte of the 16.16 accumulator edx)
  0x52c04:('{const m=R.m8,A=rd32(0x124db54),B=rd32(0x124db50);let cl=0,v=0;for(;;){cl=edx>>>24;v=m[edi+esi]+m[0x124d750+cl];m[edi+esi]=v>255?255:v;cl=~cl&255;v=m[edi]+m[0x124d750+cl];m[edi]=v>255?255:v;ebp=(ebp-1)|0;if(ebp<0)break;edi=(edi+A)|0;v=(edx>>>0)+(B>>>0);edx=v|0;if(v>4294967295)edi=(edi+esi)|0;}ecx=cl;}',0x52c45)}
import os
if os.environ.get('PURE'): INLINE={}; NATIVE.pop(0x28028,None)   # PURE=1: recompile everything (used to trace which pages a scene reads)
MISS=[]
CHUNK=int(os.environ.get('CHUNK','500'))
def main():
    ents=[int(x,16) for x in sys.argv[sys.argv.index('--')+1:]]
    funcs=[]; todo=list(ents); done=set()
    out=["// GENERATED by re/x86js.py from the original PLASTIK.EXE code.  Do not edit.\nimport * as R from './x86rt.mjs';\nconst {rd8,rd16,rd32,wr8,wr16,wr32,rdf32,rdf64,wrf32,wrf64,wrf64i,f,fpush,fxch,fist,sx16,fp_add,fp_mul,fp_sub,fp_subr,fp_div,fp_divr,fp_com,fp_add_st,fp_mul_st,fp_sub_st,fp_subr_st,fp_div_st,fp_divr_st,fp_com_st,fp_add_to,fp_mul_to,fp_sub_to,fp_subr_to,fp_div_to,fp_divr_to}=R;\nconst S=R.S;let eax=0,ecx=0,edx=0,ebx=0,esp=0,ebp=0,esi=0,edi=0,cf=false,zf=false,sf=false,of=false,pf=false,a_=0,b_=0,t=0,q_=0,r_=0;\n// sp (x87 stack pointer) lives in S.sp: use accessor shims\n"]
    body=[]
    while todo:
        e=todo.pop()
        if e in done: continue
        done.add(e); s,c=reach(e); todo+=list(c)
        lab=set()
        for a in s:
            m=ins[a][1]
            if m=='jmp' or (m.startswith('j') and m[1:] in COND): lab.add(num(ins[a][2].split()[0]))
        CH=300 if len(s)>CHUNK else 0   # huge functions are split into chunks: TurboFan refuses to optimise a function over ~60 KB of bytecode (registers are module-level, so chunks share them)
        L=['export function f_%x(pc0){let pc=pc0||%s;for(;;){switch(pc){'%(e,hex(e))] if not CH else []
        K=0
        for i,a in enumerate(s):
            if CH and i%CH==0:
                if i: L.append("pc=%s;continue;default:return pc}}}"%hex(a))
                L.append('function c_%x_%d(pc){for(;;){switch(pc){'%(e,i//CH)); K+=1
            if a in INLINE: L.append('case %s:/*inline native*/ %spc=%s;continue;'%(hex(a),INLINE[a][0],hex(INLINE[a][1])))
            try: g=gen(a) if (ins[a][1] not in FW|{'inc','dec','adc','sbb','imul'} or live(a)) else strip(gen(a))
            except Exception as ex:   # survey mode: keep going, report every unsupported instruction at the end
                MISS.append((e,a,ins[a][1],ins[a][2],str(ex))); g='throw new Error("unsupported %x %s %s");'%(a,ins[a][1],ins[a][2].replace('"',"'"))
            if CH: g=g.replace('return;','return -1;')
            L.append('case %s:/*%s %s*/ %s'%(hex(a),ins[a][1],ins[a][2],g))
            if nxt[a] not in s and ins[a][1] not in('ret','jmp'): L.append('pc=%s;continue;'%hex(nxt[a]))
        if CH:
            L.append("default:return pc}}}")
            L.append('export function f_%x(pc){pc=pc||%s;for(;;){pc='%(e,hex(e))+''.join('pc<%s?c_%x_%d(pc):'%(hex(s[(k+1)*CH]),e,k) for k in range(K-1))+'c_%x_%d(pc);if(pc<0)return;}}'%(e,K-1))
        else: L.append('default:throw new Error("pc "+pc.toString(16))}}}')
        body.append('\n'.join(L))
    FTs='const FT={'+','.join('%s:f_%x'%(hex(e),e) for e in sorted(done))+'};'
    open(sys.argv[1],'w').write(''.join(out)+'\n'.join(body)+'\n'+FTs+'\nexport function setRegs(o){({eax,ecx,edx,ebx,esp,ebp,esi,edi}=o);}\nexport function getRegs(){return {eax,ecx,edx,ebx,esp,ebp,esi,edi};}\n')
    import collections
    print('%d functions, %d unsupported instructions'%(len(done),len(MISS)),file=sys.stderr)
    for k,v in collections.Counter((m,x.split()[0] if x else '') for _,_,m,x,_ in MISS).most_common(): print(' ',k,v,file=sys.stderr)
main()
