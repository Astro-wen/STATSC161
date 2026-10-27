"""Figures for the market calibration study. Run after scripts/build_market_sample.py.

    python scripts/make_market_figures.py
"""
from pathlib import Path
import pandas as pd, numpy as np, matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt, statsmodels.api as sm, warnings; warnings.filterwarnings('ignore')
from scipy.special import logit
ROOT=Path(__file__).resolve().parents[1]
OUT=str(ROOT/'reports'/'figures')+'/'
INK='#0b0b0b'; INK2='#52514e'; MUTED='#8a8984'; GRID='#e6e5e1'; SURF='#fcfcfb'
CAT={'Politics':'#2a78d6','Technology':'#eb6834','Entertainment':'#1baf7a','Economy':'#eda100'}
plt.rcParams.update({'figure.facecolor':SURF,'axes.facecolor':SURF,'axes.edgecolor':GRID,'axes.labelcolor':INK2,'xtick.color':INK2,'ytick.color':INK2,
 'font.size':11,'axes.titlesize':13,'axes.titleweight':'bold','axes.titlecolor':INK,'axes.grid':True,'grid.color':GRID,'grid.linewidth':0.8,
 'axes.spines.top':False,'axes.spines.right':False,'legend.frameon':False,'savefig.dpi':200,'savefig.bbox':'tight'})
s=pd.read_parquet(ROOT/'data'/'processed'/'market_sample.parquet'); d=s[s.has_price].copy()
rng=np.random.default_rng(0)
bins=np.array([0,.02,.05,.1,.2,.35,.5,.65,.8,.9,.95,.98,1.0001])
def binned(g,B=300):
    g=g.assign(b=np.digitize(g.p_last,bins)-1)
    ev=g.event_slug.values; u=np.unique(ev); idx={e:np.where(ev==e)[0] for e in u}
    base=g.groupby('b').agg(n=('y','size'),p=('p_last','mean'),w=('y','mean'))
    bs=[]
    for _ in range(B):
        r=np.concatenate([idx[e] for e in rng.choice(u,len(u))]); bs.append(g.iloc[r].groupby('b').y.mean())
    bs=pd.concat(bs,axis=1); base['lo']=bs.quantile(.025,axis=1); base['hi']=bs.quantile(.975,axis=1); return base
# F1 calibration 24h pooled
g=d[d.horizon_h==24]; c=binned(g)
fig,(ax,axh)=plt.subplots(2,1,figsize=(6.2,6.6),gridspec_kw={'height_ratios':[4,1]},sharex=True)
ax.plot([0,1],[0,1],color=MUTED,lw=1,ls=(0,(4,3)),label='Perfect calibration')
ax.fill_between(c.p,c.lo,c.hi,color=CAT['Politics'],alpha=.15,lw=0,label='95% CI (event bootstrap)')
ax.plot(c.p,c.w,color=CAT['Politics'],lw=2,marker='o',ms=6,mec=SURF,mew=1.5,label='Observed Yes rate')
ax.set_ylabel('Share that resolved Yes'); ax.set_title(f'Prices 24h before close vs. outcomes\n{len(g):,} markets, {g.event_slug.nunique():,} events, Jun to Oct 2026',loc='left')
ax.legend(loc='upper left',fontsize=10,labelcolor=INK2); ax.set_xlim(0,1); ax.set_ylim(0,1)
axh.hist(g.p_last,bins=50,color=MUTED,edgecolor=SURF,linewidth=0.5); axh.set_yscale('log'); axh.set_xlabel('Market price of Yes, 24h before close'); axh.set_ylabel('Markets (log)')
fig.savefig(OUT+'fig1_calibration_24h.png'); plt.close()
# F2 by category small multiples
fig,axs=plt.subplots(1,4,figsize=(13,3.6),sharey=True)
for ax,(cat,col) in zip(axs,CAT.items()):
    gg=g[g.category==cat]; cc=binned(gg,200)
    ax.plot([0,1],[0,1],color=MUTED,lw=1,ls=(0,(4,3)))
    ax.fill_between(cc.p,cc.lo,cc.hi,color=col,alpha=.18,lw=0); ax.plot(cc.p,cc.w,color=col,lw=2,marker='o',ms=5,mec=SURF,mew=1.2)
    ax.set_title(f'{cat}\n{len(gg):,} markets, Brier {((gg.p_last-gg.y)**2).mean():.3f}',loc='left',fontsize=11); ax.set_xlim(0,1); ax.set_ylim(0,1); ax.set_xlabel('Price 24h before close')
axs[0].set_ylabel('Share resolved Yes'); fig.savefig(OUT+'fig2_calibration_by_category.png'); plt.close()
# F3 Brier by horizon x category
fig,ax=plt.subplots(figsize=(7.2,4.2))
H=[6,24,72,168]; lab_y={}
for cat,col in CAT.items():
    v=[((x.p_last-x.y)**2).mean() for h in H for x in [d[(d.horizon_h==h)&(d.category==cat)]]]
    ax.plot(H,v,color=col,lw=2,marker='o',ms=7,mec=SURF,mew=1.5); lab_y[cat]=v[0]
ys=sorted(lab_y.items(),key=lambda kv:kv[1]); placed=[]
for cat,y in ys:
    y2=max([y]+[p+0.0042 for p in placed]); placed.append(y2)
    ax.annotate(cat,(6,y),xytext=(5.2,y2),textcoords='data',va='center',ha='left',color=INK2,fontsize=10)
ax.set_xscale('log'); ax.set_xticks(H); ax.set_xticklabels(['6h','24h','3d','7d']); ax.minorticks_off(); ax.set_xlim(200,3.2)
ax.set_ylabel('Brier score (lower is better)'); ax.set_xlabel('Time before the market closed'); ax.set_ylim(0,None)
ax.set_title('Prices get more accurate as resolution approaches',loc='left'); fig.savefig(OUT+'fig3_brier_by_horizon.png'); plt.close()
# F4 slope by month
d['lp']=logit(d.p_last.clip(.005,.995)); d['month']=d.resolved_at.dt.strftime('%b')
rows=[]
for mth,gm in d[d.horizon_h==24].groupby(d.resolved_at.dt.to_period('M')):
    m=sm.GLM(gm.y,sm.add_constant(gm[['lp']]),family=sm.families.Binomial()).fit(cov_type='cluster',cov_kwds={'groups':pd.factorize(gm.event_slug)[0]})
    rows.append((mth.strftime('%b'),m.params['lp'],m.bse['lp'],len(gm)))
r=pd.DataFrame(rows,columns=['m','b','se','n'])
fig,ax=plt.subplots(figsize=(6.6,4)); x=np.arange(len(r))
ax.axhline(1,color=MUTED,lw=1,ls=(0,(4,3))); ax.errorbar(x,r.b,yerr=1.96*r.se,fmt='o',color=CAT['Politics'],ms=8,mec=SURF,mew=1.5,elinewidth=2,capsize=0)
ax.set_xticks(x); ax.set_xticklabels([f'{a}\nn={n:,}' for a,n in zip(r.m,r.n)]); ax.set_ylabel('Calibration slope (1 = calibrated)')
ax.text(1.55,0.82,'Above 1: prices too timid (longshots overpriced)\nBelow 1: prices overconfident',color=INK2,fontsize=9,va='top',ha='left')
ax.set_title('The bias is small and moves around month to month',loc='left'); fig.savefig(OUT+'fig4_slope_by_month.png'); plt.close()
# F5 model vs market
R=pd.read_csv(ROOT/'reports'/'tables'/'model_results.csv'); R=R[(R.subset=='all prices')&(R.model!='Market price')&(R.horizon!='pooled')]
fig,ax=plt.subplots(figsize=(6.6,4)); labels=['6h','24h','3d','7d']
for k,(mdl,col,off) in enumerate([('Logistic recalibration',CAT['Politics'],-0.12),('Gradient boosting',CAT['Technology'],0.12)]):
    q=R[R.model==mdl]; xx=np.arange(4)+off
    ax.errorbar(xx,q.dBrier*1000,yerr=[(q.dBrier-q.dBrier_lo)*1000,(q.dBrier_hi-q.dBrier)*1000],fmt='o',color=col,ms=8,mec=SURF,mew=1.5,elinewidth=2,label=mdl)
ax.axhline(0,color=INK2,lw=1); ax.set_xticks(range(4)); ax.set_xticklabels(labels); ax.set_xlabel('Time before close')
ax.set_ylabel('Brier vs. market price (x1000)\nabove 0 = worse than the market'); ax.legend(loc='upper left',labelcolor=INK2)
ax.set_title('Out of sample, neither model beats the price',loc='left'); fig.savefig(OUT+'fig5_models_vs_market.png'); plt.close()
print('figures written to', OUT)
