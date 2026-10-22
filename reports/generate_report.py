"""Generate a two-page reference from saved engine results; no simulated points are invented."""
from pathlib import Path
import json,math,hashlib,sys
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import HexColor,Color,white
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph,Table,TableStyle
from reportlab.graphics.shapes import Drawing,Line,String,Circle
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF

REPO=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
DATA=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).with_name('quasistatic-data.json')
OUT=Path(sys.argv[3]) if len(sys.argv)>3 else Path(__file__).with_name('微觀引擎-兩頁參考報告.pdf')
pdfmetrics.registerFont(TTFont('TC','/System/Library/Fonts/STHeiti Light.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('TCB','/System/Library/Fonts/STHeiti Medium.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('Math','/System/Library/Fonts/Supplemental/Arial Unicode.ttf'))
pdfmetrics.registerFontFamily('TC',normal='TC',bold='TCB',italic='TC',boldItalic='TCB')
GREEN=HexColor('#22694e');INK=HexColor('#18392f');MUTED=HexColor('#53635a');RULE=HexColor('#d5ddd7');PAPER=HexColor('#f1f5ef');GOLD=HexColor('#9b6b13');PURPLE=HexColor('#755196')
W,H=595.276,841.89;M=38;CW=W-2*M
source=REPO/'docs/verification/2026-10-22'
formal={k:json.loads((source/f'formal-{k}.json').read_text()) for k in ['temperature','ratio']}
old=json.loads((source/'chromium-all-evidence.json').read_text());pos=old['evidence']['positive']['points'][0]
new=json.loads(DATA.read_text());scans=new['scans']
core=__import__('re').search(r'<script id="engine-core">([\s\S]*?)</script>',(REPO/'index.html').read_text())[1]
assert hashlib.sha256(core.encode()).hexdigest()==new['coreSha256']==formal['temperature']['coreSha256']
OUT.parent.mkdir(parents=True,exist_ok=True)
c=canvas.Canvas(str(OUT),pagesize=(W,H));c.setTitle('微觀引擎：控溫、循環輸出功與準靜態條件（兩頁參考稿）');c.setAuthor('Microscopic Engine Lab | 參考稿')

def para(text,y,size=10.7,leading=15.8,x=M,width=CW,color=INK,bold=False):
 st=ParagraphStyle('p',fontName='TCB' if bold else 'TC',fontSize=size,leading=leading,textColor=color,wordWrap='CJK',spaceAfter=0)
 p=Paragraph(text,st);_,h=p.wrap(width,1000);p.drawOn(c,x,H-y-h);return y+h

def heading(n,title,y):
 c.setFillColor(GREEN);c.setFont('TCB',10);c.drawString(M,H-y-12,n)
 y=para(title,y,size=13,leading=19,x=M+25,width=CW-25,bold=True)
 return y+5

def box(text,y,height=37):
 c.setFillColor(PAPER);c.roundRect(M,H-y-height,CW,height,4,fill=1,stroke=0)
 para(text,y+7,size=10.5,leading=15.5,x=M+12,width=CW-24)
 return y+height+8

def table(rows,y,widths,heights=None):
 styles=[ParagraphStyle('cell',fontName='TC',fontSize=9.7,leading=14.3,textColor=INK,wordWrap='CJK'),ParagraphStyle('head',fontName='TCB',fontSize=9.7,leading=14.3,textColor=INK,wordWrap='CJK')]
 cells=[[Paragraph(str(v),styles[1 if i==0 else 0]) for v in row] for i,row in enumerate(rows)]
 t=Table(cells,colWidths=widths,rowHeights=heights,hAlign='LEFT')
 t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),PAPER),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),8),('RIGHTPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.4,RULE)]))
 _,h=t.wrap(CW,800);t.drawOn(c,M,H-y-h);return y+h+7

def header(page,title,sub):
 para('MICROSCOPIC ENGINE  /  熱統計物理一',31,size=9,leading=12,color=MUTED)
 para('參考稿 · 2026.10.22',31,size=9,leading=12,x=W-155,width=117,color=MUTED)
 para(title,52,size=23,leading=31,bold=True)
 para(sub,91,size=10,leading=14,color=MUTED)
 c.setStrokeColor(RULE);c.line(M,H-113,W-M,H-113)
 c.setStrokeColor(RULE);c.line(M,34,W-M,34)
 c.setFont('TC',8.4);c.setFillColor(MUTED);c.drawString(M,20,'約化單位 m = kB = 1 · w = Wout / N（每粒子每循環功）')
 c.drawRightString(W-M,20,f'{page} / 2')

def value(p):return f"{p['mean']:.3f} ± {p['ci']:.3f}"

def plot(data,x,y,width,height,title,xlabel):
 pts=data['points'];fit=data['fit'];d=Drawing(width,height)
 d.add(String(0,height-12,title,fontName='TCB',fontSize=10.5,fillColor=INK))
 lp=LinePlot();lp.x=37;lp.y=34;lp.width=width-47;lp.height=height-66
 xs=[p['x'] for p in pts];xs0=min(xs);xs1=max(xs);ymax=max(p['mean']+p['ci'] for p in pts)
 lp.data=[[(p['x'],p['mean']) for p in pts],[(xx,fit['slope']*xx+fit['intercept']) for xx in [xs0,xs1]],[(p['x'],p['theory']) for p in pts]]
 lp.joinedLines=1;lp.lines[0].strokeColor=GREEN;lp.lines[0].strokeWidth=.5
 lp.lines[1].strokeColor=PURPLE;lp.lines[1].strokeWidth=1;lp.lines[1].strokeDashArray=[3,2]
 lp.lines[2].strokeColor=GOLD;lp.lines[2].strokeWidth=.8;lp.lines[2].strokeDashArray=[1.5,2.5]
 lp.xValueAxis.valueMin=xs0-.04*(xs1-xs0);lp.xValueAxis.valueMax=xs1+.04*(xs1-xs0)
 lp.xValueAxis.valueSteps=[0,1,2,3,4] if xs1>2 else [0,.5,1,1.5]
 lp.yValueAxis.valueMin=-.12;lp.yValueAxis.valueMax=math.ceil(ymax*2)/2+.08
 lp.yValueAxis.valueSteps=[0,1,2,3] if ymax>2 else [0,.5,1,1.5,2]
 for ax in [lp.xValueAxis,lp.yValueAxis]:
  ax.strokeColor=RULE;ax.strokeWidth=.5;ax.labels.fontName='Math';ax.labels.fontSize=9;ax.labels.fillColor=MUTED;ax.labelTextFormat='%g'
 lp.yValueAxis.visibleGrid=1;lp.yValueAxis.gridStrokeColor=RULE;lp.yValueAxis.gridStrokeWidth=.3
 d.add(lp)
 xmin,xmax=lp.xValueAxis.valueMin,lp.xValueAxis.valueMax;ymin,ymax=lp.yValueAxis.valueMin,lp.yValueAxis.valueMax
 X=lambda xx:lp.x+(xx-xmin)/(xmax-xmin)*lp.width;Y=lambda yy:lp.y+(yy-ymin)/(ymax-ymin)*lp.height
 for p in pts:
  xx=X(p['x']);lo=Y(p['mean']-p['ci']);hi=Y(p['mean']+p['ci']);yy=Y(p['mean'])
  for coords in [(xx,lo,xx,hi),(xx-2,lo,xx+2,lo),(xx-2,hi,xx+2,hi)]:d.add(Line(*coords,strokeColor=GREEN,strokeWidth=.8))
  d.add(Circle(xx,yy,2,fillColor=GREEN,strokeColor=white,strokeWidth=.3))
 d.add(String(lp.x+lp.width/2,4,xlabel,fontName='Math',fontSize=10,textAnchor='middle',fillColor=INK))
 d.add(String(7,height-35,'w',fontName='Math',fontSize=11,fillColor=INK))
 renderPDF.draw(d,c,x,H-y-height)

header(1,'從熱擾動到循環輸出功','以 Langevin 熱浴建立微觀熱機，檢驗控溫、有限速率與準靜態近似。')
y=heading('01','模型、控溫與溫度的意義',125)
y=para('系統由 N 個二維、互不作用的粒子組成。基準位能為 V = κ(x − x<sub>0</sub>)²/2；x 方向為固定彈性硬牆，y 方向取週期邊界。熱浴在空間上均勻，粒子以欠阻尼 Langevin 方程演化 [1]：',y)
y=box('<font name="Math">dr = v dt， m dv = −∇V dt − γv dt + √(2γkBT<sub>b</sub>) dB， dB = √dt ξ。</font>',y+5,31)
y=para('摩擦耗散與獨立高斯噪聲共同維持熱平衡，並非逐幀重設速度。BAOAB 積分中的熱浴子步採精確 OU 更新 [2]。T<sub>b</sub> 是指定熱浴溫度；二維動能估計 T<sub>K</sub> = K/(Nk<sub>B</sub>) 會波動且包含整體漂移，非平衡時不能視為唯一的熱力學溫度。',y)
y=heading('02','循環、做功記帳與正功驗證',y+10)
y=para('固定中心時，循環依序為：固定 κ<sub>max</sub> 升溫 → 高溫降低 κ → 固定 κ<sub>min</sub> 降溫 → 低溫提高 κ。若加入中心搬運，兩個固定曲率階段分別去程與回程。對外做功定義為：',y)
y=box('<font name="Math">dW<sub>in</sub> = Σ[(x − x<sub>0</sub>)² dκ/2 − κ(x − x<sub>0</sub>) dx<sub>0</sub>]， W<sub>out</sub> = −W<sub>in</sub>。</font><br/>第一定律採 ΔE = Q<sub>in</sub> − W<sub>out</sub>；Q 由 OU 子步的動能改變獨立累積。',y+4,46)
y=para(f'<b>正功基準：</b>N=64、T<sub>H</sub>/T<sub>C</sub>=3/1、κ=1↔4、L<sub>x</sub>/L<sub>y</sub>=24/12、γ=1、dt=0.02；曲率段 30、換浴段 10，中心固定。20 次獨立重複，各先暖機 2 圈再平均 5 圈，得到 <b>w = {pos["mean"]:.4f} ± {pos["ci"]:.4f}</b>（95% CI），區間下界 1.2612 > 0，支持平均正功。η = 平均 W<sub>out</sub>/平均 Q<sub>H</sub> = {pos["eta"]:.3f}。',y)
y=heading('03','哪些操作比較接近準靜態？',y+10)
y=para('操作時間須長於位置與速度的鬆弛時間。可用 τ<sub>rel</sub>|(dκ/dt)|/κ <font name="Math">≪</font> 1 與 τ<sub>rel</sub>|(dx<sub>0</sub>/dt)|/√(T/κ) <font name="Math">≪</font> 1 作診斷。弱阱可能使位置回復較慢；但增大曲率後，欠阻尼鬆弛會受摩擦限制，不能保證「越硬越準靜態」。',y)
a,b=scans['rate'][0],scans['rate'][-1];s0,s1=scans['scale'][0],scans['scale'][-1];t0,t1=scans['translation'][0],scans['translation'][-1]
rows=[['控制變因','實際模擬結果（w ± 95% CI）','物理解讀'],['曲率段 4 → 100',f'{value(a)} → {value(b)}<br/>η：{a["eta"]:.3f} → {b["eta"]:.3f}','放慢後，功接近準靜態值 1.386；功率不必增加。'],['曲率 0.5↔2 → 2↔8',f'{value(s0)} → {value(s1)}','此範圍略有改善；欠阻尼下仍受摩擦鬆弛限制。'],['平均搬運速率 1.33 → 0.10',f'{value(t0)} → {value(t1)}','相對同時序固定阱，功差 −16.005 → −0.994；慢速損失較小。']]
y=table(rows,y+7,[126,205,CW-331])
y=para('本表 N=32、20 次獨立重複，各暖機 2 圈、記錄 5 圈；其餘同基準。尺度掃描固定曲率段 30；搬運固定距離 D=4、曲率段 30，換浴／搬運段由 3 增至 40。誤差以每次重複的圈平均估計，不把同軌跡每圈當成獨立樣本。',y,size=9.3,leading=13.3,color=MUTED)
y=para('本熱機沒有再生器；Q<sub>H</sub> 包含升溫與高溫操作時的淨吸熱，也包含 y 方向動能。放慢曲率操作不會使直接換浴成為可逆過程，因此不能直接把效率套成 Carnot 值。',y+5)
y=para('[1] Seifert, Rep. Prog. Phys. 75, 126001 (2012). <link href="https://arxiv.org/abs/1205.4176" color="#22694e">arXiv:1205.4176</link><br/>[2] Leimkuhler &amp; Matthews, J. Chem. Phys. 138, 174102 (2013). <link href="https://arxiv.org/abs/1304.3269" color="#22694e">arXiv:1304.3269</link>',y+3,size=8.3,leading=11.7,color=MUTED)
print('page1 bottom',y);assert y<795
c.showPage()
header(2,'線性關係與週期邊界','以實際循環資料作圖；理論只作比較，不作為資料生成來源。')
y=heading('04','每循環輸出功的兩個線性關係',125)
y=para('無限域諧和阱的配分函數給出 F/N = (T/2) ln κ + 與 κ 無關的項。因此固定中心、曲率段準靜態且換浴充分鬆弛時：',y)
y=box('<font name="Math">w<sub>qs</sub> = (T<sub>H</sub> − T<sub>C</sub>) ln(κ<sub>max</sub>/κ<sub>min</sub>)/2。</font>',y+4,30)
y=para('綠點與誤差棒：模擬平均與 95% CI　　紫虛線：含截距 OLS　　金虛線：模型準靜態值',y,size=8.8,leading=13,color=MUTED)
ph=180;gap=19;pw=(CW-gap)/2
plot(formal['temperature'],M,y+5,pw,ph,'A　固定 κmax/κmin = 4','ΔT = TH − TC')
plot(formal['ratio'],M+pw+gap,y+5,pw,ph,'B　固定 ΔT = 2','ln(κmax / κmin)')
y+=ph+11
fa,fb=formal['temperature']['fit'],formal['ratio']['fit']
y=table([['擬合 w = a x + b','斜率 a ± SE','截距 b','R²'],['A：x = ΔT',f'{fa["slope"]:.4f} ± {fa["slopeSE"]:.4f}',f'{fa["intercept"]:.4f}',f'{fa["r2"]:.5f}'],['B：x = ln(κmax/κmin)',f'{fb["slope"]:.4f} ± {fb["slopeSE"]:.4f}',f'{fb["intercept"]:.4f}',f'{fb["r2"]:.5f}'] ],y,[173,151,96,CW-420])
y=para('兩圖皆為硬牆、N=32、T<sub>C</sub>=1、κ<sub>min</sub>=1、固定中心、γ=1、dt=0.02、L<sub>x</sub>/L<sub>y</sub>=24/12；曲率段 100、換浴段 20。每點 20 次獨立重複，暖機 2 圈後各平均 3 圈。A 掃描 ΔT=0～4；B 固定 T<sub>H</sub>=3，掃描曲率比 1～6。',y,size=9.4,leading=13.7,color=MUTED)
y=para('理想斜率分別為 0.6931 與 1。數據支持此範圍內的近似線性；有限速率仍造成偏差，R² 高不等於已達準靜態。表中 SE 是 OLS 斜率標準誤，並非圖上 95% CI；系統總功與擬合係數須再乘 N。',y+5)
y=heading('05','Bonus：雙週期邊界的物理一致性',y+10)
y=para('把非週期諧和位能直接接起來會造成接縫問題，因此雙週期模式改用平滑週期位能；其阱底曲率仍為 κ：',y)
y=box('<font name="Math">V = κL²[1 − cos θ]/(4π²)， F<sub>x</sub> = −κL sin θ/(2π)， θ = 2π(x − x<sub>0</sub>)/L。</font>',y+4,31)
wall=next(p for p in scans['boundary'] if p['p']['L']==24 and p['p']['mode']=='wall');periodic=next(p for p in scans['boundary'] if p['p']['L']==24 and p['p']['mode']=='periodic')
y=para(f'跨界時 V、力及參數導數保持連續，回捲座標不產生額外功。以相應配分函數 Z<sub>x</sub>=∫exp(−V/T)dx 計算參考值。L=24、曲率段 100、換浴段 20 的補跑（N=32、20 次獨立重複，暖機 2 圈後記錄 5 圈）中，硬牆 w={value(wall)}，雙週期 w={value(periodic)}；其準靜態參考分別為 {wall["theory"]:.3f}、{periodic["theory"]:.3f}。兩模式全域位能也不同，不能將差異全部歸因於邊界。',y)
y=para('資料：專案 bd51397 的數值核心；既有正功／線性資料與本次補跑均使用基礎種子 20260924，原始重複及逐圈記錄隨報告保存。依「微觀引擎.pptx」第 9–11 張整理。',y+8,size=8.5,leading=12,color=MUTED)
print('page2 bottom',y);assert y<795
c.save();print(OUT)
