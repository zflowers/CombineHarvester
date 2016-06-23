import ROOT
from ROOT import TMath
import math
import os
from math import floor
import CombineHarvester.CombineTools.plotting as plot
import argparse

def DrawCMSLogo(pad, cmsText, extraText):
    pad.cd()
    cmsTextSize=0.8
    cmsTextFont = 62
    extraTextFont = 52
    lumiTextOffset = 0.2
    extraOverCmsTextSize = 0.76
    l = pad.GetLeftMargin()
    t = pad.GetTopMargin()
    r = pad.GetRightMargin()
    b = pad.GetBottomMargin()
    latex = ROOT.TLatex()
    latex.SetNDC()
    latex.SetTextAngle(0)
    latex.SetTextColor(ROOT.kBlack)
    extraTextSize = extraOverCmsTextSize * cmsTextSize
    pad_ratio = (float(pad.GetWh()) * pad.GetAbsHNDC()) / \
        (float(pad.GetWw()) * pad.GetAbsWNDC())
    if (pad_ratio < 1.):
        pad_ratio = 1.
    latex.SetTextFont(cmsTextFont)
    latex.SetTextAlign(11)
    latex.SetTextSize(cmsTextSize * t * pad_ratio)
    latex.DrawLatex(l/4, 1 - t + lumiTextOffset * t, cmsText)
    posX_ = l/4 + 0.15 * (1 - l - r)
    posY_ = 1 - t + lumiTextOffset * t
    latex.SetTextFont(extraTextFont)
    latex.SetTextSize(extraTextSize * t * pad_ratio)
    latex.SetTextAlign(11)
    latex.DrawLatex(posX_, posY_, extraText)

#ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(ROOT.kTRUE)
parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('files', help='Input root files containing HypoTestResult objects (no option prefix needed)', nargs='*')
parser.add_argument('--name', '-n', help='Appendix on the output name', default="")
parser.add_argument('--alt', help='Name for the alternative hypothesis', default="S+B")
parser.add_argument('--null', help='Name for the null hypothesis', default="B")
parser.add_argument('--bin_number', '-bins', help='Set the number of bins', default=120)
parser.add_argument('--expected', '-exp', help='Fix q_obs to a different value so CLb = 0.5', action='store_true')
parser.add_argument('--logx', '-logx', help='Draw x-axis in log scale', action='store_true')
parser.add_argument('--no_asymp', help='Show only toy distribution', action='store_true')
parser.add_argument('--show_diff', help='Make a plot of the difference between Asymptotic and LHC toy based test statistic', action='store_true')
parser.add_argument('--display', '-d', help='Display plots right when they are done', action='store_true')
args = parser.parse_args()


AsympOnLHC = not args.no_asymp
if AsympOnLHC:
  # Insert output from combine here #<----------------------------------------------
  # The value for x needs to be the value for x (or other POI) where it says 'NLL at global minimum of data'
  # The other 5 values need to be taken from where it says 'At x = 1.000000:'
  x = 0.0950627
  qmu = 8.61385
  qA = 10.65273
  clsb = 0.00167
  clb = 0.62889
  cls = 0.00265
  # TODO: Somehow write numbers to json, so they can be read more easily?

results = []
for file in args.files:
  found_res = False
  f = ROOT.TFile(file)
  ROOT.gDirectory.cd('toys')
  for key in ROOT.gDirectory.GetListOfKeys():
    if ROOT.gROOT.GetClass(key.GetClassName()).InheritsFrom(ROOT.RooStats.HypoTestResult.Class()):
      results.append(ROOT.gDirectory.Get(key.GetName()))
      found_res = True
  f.Close()
  if not found_res:
    print '>> Warning, did not find a HypoTestResult object in file %s' % file
  if (len(results)) > 1:
    for r in results[1:]:
      results[0].Append(r)
  ntoys = min(results[0].GetNullDistribution().GetSize(), results[0].GetAltDistribution().GetSize())
  if ntoys == 0:
    print '>> Warning, HypoTestResult from file(s) %s does not contain any toy results, did something go wrong in your fits?' % '+'.join(args.files)
result=results[0]

alt_label = args.alt
null_label = args.null

filename = args.files[0]
aw = filename.find(".mA")
if aw != -1:
  aw += 4
  bw = aw
  while not filename[bw] == ".":
    bw += 1
  maval = filename[aw:bw]
else:
  maval = ""

aw = filename.find(".tanb")
if aw != -1:
  aw += 6
  bw = aw
  while not filename[bw] == ".":
    bw += 1
  tanbval = filename[aw:bw]
else:
  tanbval = ""

name = ''
if args.name != '': name = args.name
if maval != '' and tanbval != '':
  if name != '': name += '_'
  name += 'mA'+maval+'_'+'tanb'+tanbval
if name == '': name = 'plot'
if args.expected: name += '_exp'

null_vals = [toy * 2. for toy in result.GetNullDistribution().GetSamplingDistribution()]
alt_vals = [toy * 2. for toy in result.GetAltDistribution().GetSamplingDistribution()]
val_obs = result.GetTestStatisticData() * 2.

if args.expected:
  null_vals.sort()
  val_obs = null_vals[int(min(floor(0.5 * len(null_vals) +0.5), len(null_vals)-1))]#null_vals[len(null_vals)/2]
  result.SetTestStatisticData(val_obs/2)

if len(null_vals) == 0 or len(alt_vals) == 0:
  print '>> Error in PlotTestStat for %s, null and/or alt distributions are empty'
  exit()
plot.ModTDRStyle()
canv = ROOT.TCanvas(name, name)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
min_val = min(min(alt_vals), min(null_vals))
max_val = max(max(alt_vals), max(null_vals))
#min_plot_range = min_val - 0.05 * (max_val - min_val)
min_plot_range = 0.
pads[1].SetLogy(True)
if args.logx:
  pads[1].SetLogx(True)
max_plot_range = max_val + 0.05 * (max_val - min_val)

if AsympOnLHC:
  if args.expected:
    eN = ROOT.Math.normal_quantile(0.5, 1.0)
    clb = 0.5
    clsb = ROOT.Math.normal_cdf_c(math.sqrt(qA)-eN, 1.)
    cls = clsb * 2
    qmu = qA

  TotalToysSB=result.GetAltDistribution().GetSize()
  TotalToysB=result.GetNullDistribution().GetSize()

  # The rate by how much the asymptotic distribution needs to be scaled depends on the bin width, so the maximum plot range.
  # But the maximum plot range also depends on how high the asymptotic distribution is.
  # It's enough to go through this iteratively twice.
  for i in range (2):
    test1 = ROOT.TF1("f1","[0]/(2*sqrt(2*TMath::Pi()*[1]))*(TMath::Exp(-1/(8*[1])*(x+[1])*(x+[1])))",qA,max_plot_range*9999)
    test2 = ROOT.TF1("f2","[0]/(sqrt(8*TMath::Pi()*[3]))*(TMath::Exp(-1/(8*[3])*(x-(([1]*[1]-2*[4]*[1])/([2]*[2])))*(x-(([1]*[1]-2*[4]*[1])/([2]*[2])))))",qA,max_plot_range*9999)
    test1.SetParameter(0,TotalToysSB)
    test1.FixParameter(1,qA)
    test2.SetParameter(0,TotalToysB)
    test2.SetParameter(1,x)
    test2.SetParameter(2,x/math.sqrt(qA))
    test2.FixParameter(3,qA)
    test2.SetParameter(4,0)
    mult1 = 1.0
    while test1.Eval(mult1*qA) > 0.8 :
      mult1 +=0.1
    mult2 = 1
    while test2.Eval(mult2*qA) > 0.8:
      mult2 +=0.1
    mult = max(mult1, mult2)
    if mult*qA > max_val: max_plot_range = mult*qA + 0.05 * (max_val - min_val)
    TotalToysSB=result.GetAltDistribution().GetSize()*(max_plot_range-min_plot_range)/args.bin_number
    TotalToysB=result.GetNullDistribution().GetSize()*(max_plot_range-min_plot_range)/args.bin_number    

hist_null = ROOT.TH1F('null', 'null', args.bin_number, min_plot_range, max_plot_range)
hist_alt = ROOT.TH1F('alt', 'alt', args.bin_number, min_plot_range, max_plot_range)
for val in null_vals: hist_null.Fill(val)
for val in alt_vals: hist_alt.Fill(val)
hist_alt.SetLineColor(ROOT.TColor.GetColor(4, 4, 255))
hist_alt.SetFillColor(plot.CreateTransparentColor(ROOT.TColor.GetColor(4, 4, 255), 0.4))
hist_alt.GetXaxis().SetTitle('-2 #times ln(^{}L_{%s}/^{}L_{%s})' % (alt_label, null_label))
hist_alt.GetYaxis().SetTitle('Pseudo-experiments')
hist_alt.SetMinimum(0.8)
hist_alt.Draw()
hist_null.SetLineColor(ROOT.TColor.GetColor(252, 86, 11))
hist_null.SetFillColor(plot.CreateTransparentColor(ROOT.TColor.GetColor(254, 195, 40), 0.4))
hist_null.Draw('SAME')
histmax = hist_alt.GetMaximum()
obs = ROOT.TArrow(val_obs, 0, val_obs, histmax * 0.01, 0.05 , '<-|')
obs.SetLineColor(ROOT.kRed)
obs.SetLineWidth(3)
obs.Draw()
#plot.FixTopRange(pads[1], plot.GetPadYMax(pads[1]), 0.25)
leg = ROOT.TLegend(0.76-ROOT.gPad.GetRightMargin(), 0.78-ROOT.gPad.GetTopMargin(), 0.98-ROOT.gPad.GetRightMargin(), 0.98-ROOT.gPad.GetTopMargin(), '', 'NBNDC')
leg.AddEntry(hist_alt, alt_label, 'F')
leg.AddEntry(hist_null, null_label, 'F')
if args.expected:
  leg.AddEntry(obs, 'Expected', 'L')
else:
  leg.AddEntry(obs, 'Observed', 'L')
pads[0].cd()
pt_l1 = ROOT.TPaveText(0.33, 0.72, 0.43, 0.78, 'NDCNB')
pt_l1.AddText('Model:')
pt_l1.AddText('Toys:')
plot.Set(pt_l1, TextAlign=11, TextFont=62, BorderSize=0)
pt_l1.Draw()
pt_la = ROOT.TPaveText(0.20, 0.80, 0.30, 0.95, 'NDCNB')
pt_la.AddText('')
pt_la.AddText('CLs+b:')
pt_la.AddText('CLb:')
pt_la.AddText('CLs:')
if args.expected:
  pt_la.AddText('q_exp:')
else:
  pt_la.AddText('q_obs:')
plot.Set(pt_la, TextAlign=11, TextFont=62, BorderSize=0)
pt_la.Draw()
if AsympOnLHC:
  pt_t1 = ROOT.TPaveText(0.35, 0.92, 0.54, 0.95, 'NDCNB')
  pt_t2 = ROOT.TPaveText(0.55, 0.92, 0.74, 0.95, 'NDCNB')
  pt_t3 = ROOT.TPaveText(0.75, 0.92, 0.94, 0.95, 'NDCNB')
  pt_t1.AddText('Toy based')
  pt_t2.AddText('Asymptotic formula')
  pt_t3.AddText('Asymptotic integral')
  plot.Set(pt_t1, TextAlign=11, TextFont=62, BorderSize=0)
  pt_t1.Draw()
  plot.Set(pt_t2, TextAlign=11, TextFont=62, BorderSize=0)
  pt_t2.Draw()
  plot.Set(pt_t3, TextAlign=11, TextFont=62, BorderSize=0)
  pt_t3.Draw()
pt_r1 = ROOT.TPaveText(0.41, 0.72, 0.71, 0.78, 'NDCNB')
pt_r1.AddText('%s [%s = %s, %s = %s]' % ('m_{h}^{mod+}', 'mA', maval, 'tanb', tanbval))
pt_r1.AddText('%i (%s) + %i (%s)' % (result.GetNullDistribution().GetSize(), null_label, result.GetAltDistribution().GetSize(), alt_label))
plot.Set(pt_r1, TextAlign=11, TextFont=42, BorderSize=0)
pt_r1.Draw()
pt_b1 = ROOT.TPaveText(0.35, 0.80, 0.54, 0.92, 'NDCNB')
pt_b1.AddText('%.3f #pm %.3f' % (result.CLsplusb(), result.CLsplusbError()))
pt_b1.AddText('%.3f #pm %.3f' % (result.CLb(), result.CLbError()))
pt_b1.AddText('%.3f #pm %.3f' % (result.CLs(), result.CLsError()))
pt_b1.AddText('%.5f' % (val_obs))
plot.Set(pt_b1, TextAlign=11, TextFont=42, BorderSize=0)
pt_b1.Draw()
if AsympOnLHC:
  pt_b2 = ROOT.TPaveText(0.55, 0.83, 0.74, 0.92, 'NDCNB')
  pt_b2.AddText('%.3f' % (clsb))
  pt_b2.AddText('%.3f' % (clb))
  pt_b2.AddText('%.3f' % (cls))
  pt_b3 = ROOT.TPaveText(0.75, 0.83, 0.94, 0.92, 'NDCNB')
  pt_b4 = ROOT.TPaveText(0.64, 0.80, 0.83, 0.83, 'NDCNB')
  pt_b4.AddText('%.5f' % (qmu))
  plot.Set(pt_b2, TextAlign=11, TextFont=42, BorderSize=0)
  pt_b2.Draw()
  plot.Set(pt_b4, TextAlign=11, TextFont=42, BorderSize=0)
  pt_b4.Draw()
DrawCMSLogo(pads[0], 'CMS', "(private work)")
pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()
if AsympOnLHC:

  f1 = ROOT.TF1("f1","(x<=[1])*[0]/(2*sqrt(2*TMath::Pi()*x))*(TMath::Exp(-1/2*x)) + (x>[1])*[0]/(2*sqrt(2*TMath::Pi()*[1]))*(TMath::Exp(-1/(8*[1])*(x+[1])*(x+[1])))",0,max_plot_range)
  f1.SetParameter(0,TotalToysSB)
  f1.FixParameter(1,qA)

  f2 = ROOT.TF1("f2","(x<=[3])*[0]/(2*sqrt(2*TMath::Pi()*x))*(TMath::Exp(-1/2*(sqrt(x)-(([1]-[4])/[2]))*(sqrt(x)-(([1]-[4])/[2])))) + (x>[3])*[0]/(sqrt(8*TMath::Pi()*[3]))*(TMath::Exp(-1/(8*[3])*(x-(([1]*[1]-2*[4]*[1])/([2]*[2])))*(x-(([1]*[1]-2*[4]*[1])/([2]*[2])))))",0,max_plot_range)

  f2.SetParameter(0,TotalToysB)
  f2.SetParameter(1,x)
  f2.SetParameter(2,x/math.sqrt(qA))
  f2.FixParameter(3,qA)
  f2.SetParameter(4,0)

  #if qmu==0: qmu=0.0000000000001
  if qmu==0:
    asy_sb=0.5
    asy_b=ROOT.Math.normal_cdf(math.sqrt(qA),1)
  else:
    asy_sb=f1.Integral(qmu,max_plot_range)/TotalToysSB
    asy_b=f2.Integral(qmu,max_plot_range)/TotalToysB
  pads[0].cd()
  pt_b3.AddText('%.3f' % (asy_sb))
  pt_b3.AddText('%.3f' % (asy_b))
  pt_b3.AddText('%.3f' % (asy_sb/asy_b))
  plot.Set(pt_b3, TextAlign=11, TextFont=42, BorderSize=0)
  pt_b3.Draw()
  pads[1].cd()

  hist_alt.SetMaximum(histmax*2)
  if args.logx: hist_alt.GetXaxis().SetRange(hist_alt.GetXaxis().FindBin((max_plot_range-min_plot_range)/args.bin_number *0.9),hist_alt.GetNbinsX())

  obs2 = ROOT.TArrow(qmu, 0, qmu, histmax * 0.015, 0.05 , '<-|')
  obs2.SetLineColor(ROOT.kGreen+2)
  obs2.SetLineWidth(3)
  obs2.Draw()
  leg.AddEntry(f1, alt_label+' Asymptotic', 'L')
  leg.AddEntry(f2, null_label+' Asymptotic', 'L')
  if args.expected:
    leg.AddEntry(obs2, 'Asymp Expected', 'L')
  else:
    leg.AddEntry(obs2, 'Asymp Observed', 'L')

  f1.SetLineWidth(3)
  f1.SetLineColor(ROOT.kBlue)
  f1.Draw("same")
  f2.SetLineWidth(3)
  f2.SetLineColor(ROOT.kOrange+7)
  f2.Draw("same")
leg.Draw()
canv.SaveAs("AsympOnLHC_"+name+".png")
if args.display: os.system("display AsympOnLHC_"+name+".png &")

if args.show_diff and AsympOnLHC:
  sbdiff = ROOT.TH1F('sbdiff', 'sbdiff', args.bin_number, min_plot_range, max_plot_range)
  bdiff = ROOT.TH1F('bdiff', 'bdiff', args.bin_number, min_plot_range, max_plot_range)
  sbdiffone = f1.Eval(hist_alt.GetBinCenter(1))-hist_alt.GetBinContent(1)
  bdiffone = f2.Eval(hist_null.GetBinCenter(1))-hist_null.GetBinContent(1)
  sbdifftotal = sbdiffone
  bdifftotal = bdiffone
  for i in xrange(2,args.bin_number+1):
    sbdiffval = f1.Eval(hist_alt.GetBinCenter(i))-hist_alt.GetBinContent(i)
    bdiffval = f2.Eval(hist_null.GetBinCenter(i))-hist_null.GetBinContent(i)
    sbdifftotal += sbdiffval
    bdifftotal += bdiffval
    sbdiff.SetBinContent(i,sbdiffval)
    bdiff.SetBinContent(i,bdiffval)
  maxdiff = max(max(sbdiff.GetMaximum(),bdiff.GetMaximum()),-1*min(sbdiff.GetMinimum(),bdiff.GetMinimum()))
  sbdiff.SetMaximum(maxdiff)
  bdiff.SetMaximum(maxdiff)
  sbdiff.SetMinimum(-1*maxdiff)
  bdiff.SetMinimum(-1*maxdiff)
  canv2 = ROOT.TCanvas(name+'_diff', name+'_diff')
  pads2 = plot.TwoPadSplit(0.8, 0, 0)
  pads2[1].cd()
  sbdiff.SetLineColor(ROOT.TColor.GetColor(4, 4, 255))
  sbdiff.SetFillColor(plot.CreateTransparentColor(ROOT.TColor.GetColor(4, 4, 255), 0.4))
  sbdiff.GetXaxis().SetTitle('-2 #times ln(^{}L_{%s}/^{}L_{%s})' % (alt_label, null_label))
  sbdiff.GetYaxis().SetTitle('Diff.  Asymp. - Toys')
  bdiff.SetLineColor(ROOT.TColor.GetColor(252, 86, 11))
  bdiff.SetFillColor(plot.CreateTransparentColor(ROOT.TColor.GetColor(254, 195, 40), 0.4))
  sbdiff.Draw()
  bdiff.Draw("same")

  pads2[0].cd()
  leg2 = ROOT.TLegend(0.82-ROOT.gPad.GetRightMargin(), 0.76-ROOT.gPad.GetTopMargin(), 0.98-ROOT.gPad.GetRightMargin(), 0.83-ROOT.gPad.GetTopMargin(), '', 'NBNDC')
  leg2.AddEntry(sbdiff, alt_label, 'F')
  leg2.AddEntry(bdiff, null_label, 'F')
  leg2.Draw()
  pt_diff1 = ROOT.TPaveText(0.15, 0.82, 0.52, 0.95, 'NDCNB')
  pt_diff1.AddText(alt_label+'-diff. at q=0: %.2f ' % (sbdiffone))
  pt_diff1.AddText(null_label+'-diff. at q=0: %.2f ' % (bdiffone))
  pt_diff1.Draw()
  pt_diff2 = ROOT.TPaveText(0.58, 0.82, 0.95, 0.95, 'NDCNB')
  pt_diff2.AddText('Total '+alt_label+'-diff.: %.2f ' % (sbdifftotal))
  pt_diff2.AddText('Total '+null_label+'-diff.: %.2f ' % (bdifftotal))
  pt_diff2.Draw()
  canv2.SaveAs("AsympOnLHCDiff_"+name+".png")
  if args.display: os.system("display AsympOnLHCDiff_"+name+".png &")
