import sherpa_onnx, soundfile as sf, json, sys, numpy as np
B="/tmp/claude-0/-home-claude/345592a4-b47e-591b-b0fb-87c4679cee37/scratchpad"
M=f"{B}/models/sherpa-onnx-nemo-parakeet-tdt-0.6b-v3-int8"
rec=sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f"{M}/encoder.int8.onnx",decoder=f"{M}/decoder.int8.onnx",joiner=f"{M}/joiner.int8.onnx",tokens=f"{M}/tokens.txt",model_type="nemo_transducer",num_threads=2)
for name in sys.argv[1:]:
    a,sr=sf.read(f"{B}/reels/audio/{name}.wav",dtype="float32")
    # cut points at quietest 0.2s window near every 40s
    hop=int(0.05*sr); e=np.array([np.sqrt(np.mean(a[i:i+hop]**2)) for i in range(0,len(a)-hop,hop)])
    cuts=[0]; t=40.0
    while t < len(a)/sr-10:
        lo,hi=int((t-8)/0.05),int((t+8)/0.05); k=lo+int(np.argmin(e[lo:hi])); cuts.append(k*hop); t=k*0.05+40
    cuts.append(len(a))
    words=[]
    for s0,s1 in zip(cuts[:-1],cuts[1:]):
        s=rec.create_stream(); s.accept_waveform(sr,a[s0:s1]); rec.decode_stream(s); r=s.result
        off=s0/sr; durs=list(getattr(r,"durations",[]) or [0.08]*len(r.tokens)); cw=[]
        for tok,tt,du in zip(r.tokens,r.timestamps,durs):
            if tok.startswith(" ") or tok.startswith("▁") or not cw: cw.append([tok.strip().replace("▁",""),tt+off,tt+off+du])
            else: cw[-1][0]+=tok; cw[-1][2]=tt+off+du
        words+= [w for w in cw if w[0]]
    json.dump({"text":" ".join(w[0] for w in words),"words":words},open(f"{B}/reels/{name}.json","w"),ensure_ascii=False)
    print(name,len(words))
