import numpy as np, wave
SR=44100; DUR=90.0; N=int(SR*DUR)
L=np.zeros(N); R=np.zeros(N)
BPM=100; beat=60/BPM; bar=beat*4
def f(m): return 440*2**((m-69)/12)
def add(sig, t, pan=0.5, gain=1.0):
    i=int(t*SR); j=min(N,i+len(sig))
    if i>=N: return
    s=sig[:j-i]*gain; L[i:j]+=s*np.sqrt(1-pan); R[i:j]+=s*np.sqrt(pan)
def env(n, a, d):  # attack, exp decay
    t=np.arange(n)/SR; e=np.exp(-t/d); ai=int(a*SR)
    if ai>0: e[:ai]*=np.linspace(0,1,ai)
    return e
# chords (C - G/B - Am - F) / second half (F - G - Em - Am)
prog=[[48,60,64,67,71],[47,59,62,67,74],[45,57,60,64,69],[41,57,60,65,69],
      [41,57,64,65,72],[43,59,62,67,74],[40,55,59,64,67],[45,57,60,64,72]]
nb=int(DUR/bar)+1
for b in range(nb):
    t0=b*bar; ch=prog[b%8]
    # pad
    n=int(bar*SR*1.15); t=np.arange(n)/SR
    pe=np.minimum(1,t/0.6)*np.minimum(1,np.maximum(0,(bar*1.15-t)/0.5))
    for k,m in enumerate(ch[1:]):
        fr=f(m); s=np.zeros(n)
        for det in (-0.12,0.12):
            ff=fr*2**(det/12)
            s+=np.sin(2*np.pi*ff*t)+0.25*np.sin(4*np.pi*ff*t)+0.08*np.sin(6*np.pi*ff*t)
        add(s*pe, t0, pan=0.3+0.1*k, gain=0.035)
    # bass
    if b>=2:
        for bt,ln in ((0,1.4),(2.5,0.5),(3,0.9)):
            n=int(ln*beat*SR); t=np.arange(n)/SR; fr=f(ch[0]-12+12)
            s=(np.sin(2*np.pi*fr*t)+0.3*np.sin(4*np.pi*fr*t))*env(n,0.01,0.35)
            add(s, t0+bt*beat, gain=0.16)
    # pluck arpeggio 8ths
    pat=[1,2,3,4,3,2,4,3]
    for e in range(8):
        m=ch[pat[e]]+12; n=int(0.9*SR); t=np.arange(n)/SR; fr=f(m)
        s=(np.sin(2*np.pi*fr*t)+0.35*np.sin(2*np.pi*fr*2.0*t)*np.exp(-t/0.08)+0.15*np.sin(2*np.pi*fr*3.01*t)*np.exp(-t/0.05))*env(n,0.003,0.22)
        add(s, t0+e*beat/2, pan=0.25+0.5*(e%2), gain=0.05 if b>=1 else 0.03)
    # drums (bars 4..33)
    if 4<=b<33:
        for bt in (0,2):
            n=int(0.35*SR); t=np.arange(n)/SR
            ph=2*np.pi*np.cumsum(50+90*np.exp(-t/0.03))/SR
            add(np.sin(ph)*env(n,0.001,0.12), t0+bt*beat, gain=0.32)
        if b>=8:
            rng=np.random.default_rng(b)
            for e in range(8):
                n=int(0.06*SR); nz=rng.standard_normal(n); nz=np.diff(np.concatenate([[0],nz]))
                add(nz*env(n,0.001,0.018), t0+e*beat/2, pan=0.65, gain=0.035 if e%2 else 0.018)
            for bt in (1,3):  # soft clap
                n=int(0.2*SR); nz=rng.standard_normal(n); nz=np.diff(np.concatenate([[0],nz]))
                add(nz*env(n,0.002,0.06), t0+bt*beat, pan=0.45, gain=0.05)
# whooshes at transitions
rng=np.random.default_rng(1)
for tt in (12.5,23.5,41.5,61,80):
    n=int(1.2*SR); t=np.arange(n)/SR; nz=rng.standard_normal(n)
    # crude band sweep: moving average with varying width
    out=np.zeros(n); acc=0
    a=np.exp(-2*np.pi*(300+3000*np.sin(np.pi*t/1.2))/SR)
    for i in range(n): acc=a[i]*acc+(1-a[i])*nz[i]; out[i]=acc
    e=np.sin(np.pi*np.minimum(1,t/1.2))**2
    add(out*e, tt-0.75, pan=0.5, gain=0.5)
# simple reverb
ir_n=int(1.8*SR); ir=np.random.default_rng(2).standard_normal(ir_n)*np.exp(-np.arange(ir_n)/SR/0.45); ir/=np.sqrt((ir**2).sum())
def conv(x): 
    m=len(x)+ir_n; F=1<<int(np.ceil(np.log2(m))); return np.fft.irfft(np.fft.rfft(x,F)*np.fft.rfft(ir,F),F)[:len(x)]
L=L+0.25*conv(L); R=R+0.25*conv(R)
# fades
t=np.arange(N)/SR; fade=np.minimum(1,t/1.0)*np.minimum(1,np.maximum(0,(DUR-t)/3.5))
L*=fade; R*=fade
pk=max(abs(L).max(),abs(R).max()); L/=pk/0.89; R/=pk/0.89
st=(np.stack([L,R],1)*32767).astype(np.int16)
with wave.open("bgm.wav","wb") as w: w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
print("ok")
