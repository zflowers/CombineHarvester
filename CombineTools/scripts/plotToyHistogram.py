import CombineHarvester.CombineTools.plotting as plot
import ROOT
import math
import argparse

ROOT.gROOT.SetBatch(ROOT.kTRUE)
parser = argparse.ArgumentParser()
parser.add_argument('--files', '-f', help='Name of file with the observed test statistic')
parser.add_argument('--toys', '-t', help='Name of file with the toys')
args = parser.parse_args()

obsfile = ROOT.TFile(args.files, 'r')
toyfile = ROOT.TFile(args.toys, 'r')

tree = obsfile.Get('limit')
for evt in tree:
  obs = float(evt.limit)
  mh = float(evt.mh)
tree = toyfile.Get('limit')
toys = []
pval=0.0
for evt in tree:
  toys.append(float(evt.limit))
  if (float(evt.limit)>=obs):
    pval+=1
toys = sorted(toys)
pval = pval/len(toys)

plot.ModTDRStyle(width=800, height=600, t=0.06, b=0.14, l=0.22, r=0.10)
c1=ROOT.TCanvas()
c1.SetGridx(1)
c1.SetGridy(1)

exp = ROOT.TH1F('exp', '', 100, toys[0]-((toys[-1]-toys[0])/20.0), toys[-1]+((toys[-1]-toys[0])/20.0))
for i, toy in enumerate(toys):
  exp.Fill(toy,1.0/len(toys))

exp.SetXTitle("q_{GoF}")
exp.GetXaxis().SetLabelFont(62)
exp.GetXaxis().SetTitleColor(1)
exp.GetXaxis().SetTitleOffset(1.05)
#exp.GetXaxis().SetRange(lowerBin+1, upperBin)
exp.SetYTitle("arb. unit normalized to unity")
exp.GetYaxis().SetLabelFont(62)
exp.GetYaxis().SetTitleSize(0.05)
exp.GetYaxis().SetTitleOffset(1.4)
exp.GetYaxis().SetLabelSize(0.04)
exp.SetMinimum(0)
exp.SetMaximum(1.3*exp.GetMaximum())
exp.SetLineWidth(3) 
exp.SetLineColor(ROOT.kBlack)
ROOT.gStyle.SetOptStat(0)
exp.Draw()

arr = ROOT.TArrow(obs, 0, obs, exp.GetMaximum()/6, 0.02, "<|")
arr.SetLineColor(ROOT.kRed)
arr.SetFillColor(ROOT.kRed)
#arr.SetFillStyle(1001)
arr.SetLineWidth(3)
arr.SetLineStyle(1)
arr.SetAngle(50)
arr.Draw("<|same")

leg = ROOT.TLegend(0.53, 0.79, 0.95, 0.92)
leg.SetBorderSize(0)
leg.SetFillStyle(0)
leg.SetFillColor(ROOT.kWhite)
leg.AddEntry(exp, "Expected (from toys)", "L")
leg.AddEntry(arr, "Observed", "L")
leg.Draw("same")

#label = "%s = %d GeV" % ("m_{H}", mh)
#textlabel = ROOT.TPaveText(0.18, 0.83, 0.50, 0.92, "NDC")
#textlabel.SetBorderSize(0)
#textlabel.SetFillStyle(0)
#textlabel.SetTextAlign(12)
#textlabel.SetTextSize(0.04)
#textlabel.SetTextColor(1)
#textlabel.SetTextFont(62)
#textlabel.AddText(label)
#textlabel.Draw()

pvalue = ROOT.TPaveText(0.17, 0.79, 0.49, 0.92, "NDC")#(0.18, 0.79, 0.50, 0.84, "NDC")
pvalue.SetBorderSize(0)
pvalue.SetFillStyle(0)
pvalue.SetTextAlign(12)
pvalue.SetTextSize(0.04)
pvalue.SetTextColor(1)
pvalue.SetTextFont(62)
pvalue.AddText("p-value = %0.3f" % pval)
pvalue.AddText("Number of toys: "+str(len(toys)))
pvalue.Draw()

c1.RedrawAxis()
c1.SaveAs("toy_distribution.png")
c1.SaveAs("toy_distribution.pdf")
