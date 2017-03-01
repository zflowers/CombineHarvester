#!/usr/bin/env python
import CombineHarvester.CombineTools.plotting as plot
import ROOT
import argparse

# This script may be used to produce plots showing the differences between the calculating of
# two different model dependent limits. As input, this script requires two root files produced
# with the HybridNewGrid or the AsymptoticGrid method of combineTool.py. The paths to these
# root files need to be given using the --fileone and --filetwo arguments. In addition,
# --nameone and --nametwo are used to name the methods with which root files were produced. Make
# sure these names are not too long. --shortnameone and --shortnametwo are the abbreviations
# used in the output filenames. --testtype should be set to either MSSMvsSM or MSSMvsBG,
# depending on the performed test. --dataset may be used to include an extension in the outpu filenames.

# After executing this script, a number of images are created.
# The image with 'AllLimits' shows the observed and expected limits.
# The image with 'ObsRatio' shows the difference of the observed CLs values, as well as the
# observed exclusion limits.
# The image with 'ExpRatio' shows the difference of the expected CLs values, as well as the
# expected exclusion limits.
# The image with 'SigmaBands' shows the expected limits, as well as the error bands. Here the
# result set in --fileone is displayed in blue contours and the result set in --filetwo is
# displayed in red bands.
# The images with 'CLsObs...' and 'CLsExp...' show only the corresponding CLs values along
# with the corresponding limit.
# The images with 'CLsX.Y' show the trend of the observed and expected CLs values at
# mA=X from tanb=1..Y. Near line 700, different values for X and Y may be edited. IMPORTANT: These
# plots assume that the binning of tanb is in steps of 1 from 1 to 30 and in steps of 2 from 30 to 60.

ROOT.PyConfig.IgnoreCommandLineOptions = True
ROOT.gROOT.SetBatch(ROOT.kTRUE)

parser = argparse.ArgumentParser(
    formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument(
    '--output', '-o', default='limit_grid_output', help="""Name of the output
    plot without file extension""")
parser.add_argument(
    '--contours', default='exp0,obs,exp-2,exp-1,exp+1,exp+2', help="""List of
    contours to plot. These must correspond to the names of the TGraph2D
    objects in the input file""")
parser.add_argument(
    '--bin-method', default='BinEdgeAligned', help="""One of BinEdgeAligned or
    BinCenterAligned. See plotting.py documentation for details.""")
parser.add_argument(
    '--CL', default=0.95, help="""Confidence level for contours""")
parser.add_argument(
    '--x-title', default='m_{A} (GeV)', help="""Title for the x-axis""")
parser.add_argument(
    '--y-title', default='tan#beta', help="""Title for the y-axis""")
parser.add_argument(
    '--cms-sub', default='Internal', help="""Text below the CMS logo""")
parser.add_argument(
    '--scenario', default='', help="""Scenario name to be drawn in top
    left of plot""")
parser.add_argument(
    '--title-right', default='', help="""Right header text above the frame""")
parser.add_argument(
    '--title-left', default='', help="""Left header text above the frame""")
parser.add_argument(
    '--logy', action='store_true', help="""Draw y-axis in log scale""")
parser.add_argument(
    '--logx', action='store_true', help="""Draw x-axis in log scale""")
parser.add_argument(
    '--force-x-width', type=float, default=None, help="""Use this x bin width in
    BinCenterAligned mode""")
parser.add_argument(
    '--force-y-width', type=float, default=None, help="""Use this y bin width in
    BinCenterAligned mode""")
parser.add_argument(
    '--hist', default=None, help="""Draw this TGraph2D as a histogram with
    COLZ""")
parser.add_argument(
    '--model', default='', help="""Model""")

parser.add_argument('--fileone', '-fa', help='Input root file 1')
parser.add_argument('--filetwo', '-fb', help='Input root file 2')
parser.add_argument('--nameone', help='Name of root file 1')
parser.add_argument('--nametwo', help='Name of root file 2')
parser.add_argument('--shortnameone', default='', help='Abbreviation of root file 1 (optional)')
parser.add_argument('--shortnametwo', default='', help='Abbreviation of root file 2 (optional)')
parser.add_argument('--testtype', help='Name of test (MSSMvsSM or MSSMvsBG)')
parser.add_argument('--dataset', help='Filename extension of output (optional)')
args = parser.parse_args()

def GetXsBr(xs, br, xv, yv):
  return xsbrfile.Get(xs).GetBinContent(xsbrfile.Get(xs).GetXaxis().FindBin(xv), xsbrfile.Get(xs).GetYaxis().FindBin(yv)) * xsbrfile.Get(br).GetBinContent(xsbrfile.Get(br).GetXaxis().FindBin(xv), xsbrfile.Get(br).GetYaxis().FindBin(yv))

plot.ModTDRStyle(r=0.06 if args.hist is None else 0.17, l=0.12)
ROOT.gStyle.SetNdivisions(510, 'XYZ')
plot.SetBirdPalette()

print args.fileone
print args.filetwo
file1 = ROOT.TFile(args.fileone)
file2 = ROOT.TFile(args.filetwo)
types = args.contours.split(',')
CL = 1 - args.CL

nameone = args.nameone
nametwo = args.nametwo
shortnameone = args.shortnameone
if shortnameone == '': shortnameone = nameone
shortnametwo = args.shortnametwo
if shortnametwo == '': shortnametwo = nametwo
dataset = args.dataset
testtype = args.testtype+" test"

print shortnameone
print shortnametwo
print dataset
print testtype
dataset=dataset+"_"

# Object storage
graphs1 = {c: file1.Get(c) for c in types}
graphs2 = {c: file2.Get(c) for c in types}
if "Asymp" not in shortnameone:
  protograph = graphs1
else:
  protograph = graphs2
hists1 = {}
hists2 = {}
contours1 = {}
contours2 = {}

h_proto = plot.TH2FromTGraph2D(protograph[types[0]], method=args.bin_method, force_x_width=args.force_x_width, force_y_width=args.force_y_width)
h_axis = h_proto
h_axis = plot.TH2FromTGraph2D(protograph[types[0]])

# Fill TH2s by interpolating the TGraph2Ds, then extract contours
for c in types:
  print 'Filling histo for %s' % c
  hists1[c] = h_proto.Clone(c)
  hists2[c] = h_proto.Clone(c)
  plot.fillTH2(hists1[c], graphs1[c], 1)
  plot.fillTH2(hists2[c], graphs2[c], 1)
  contours1[c] = plot.contourFromTH2(hists1[c], CL, 5, frameValue=1)
  contours2[c] = plot.contourFromTH2(hists2[c], CL, 5, frameValue=1)

ratiomin = -0.2
obsratio = h_proto.Clone()
expratio = h_proto.Clone()
clsobsa = h_proto.Clone()
clsobsb = h_proto.Clone()
clsexpa = h_proto.Clone()
clsexpb = h_proto.Clone()
for i in xrange(1, obsratio.GetNbinsX() + 1):
  for j in xrange(1, obsratio.GetNbinsY() + 1):
    obsratio.SetBinContent(i, j, hists1['obs'].GetBinContent(i,j) - hists2['obs'].GetBinContent(i,j))
    if obsratio.GetBinContent(i, j)<ratiomin: obsratio.SetBinContent(i, j, ratiomin+0.001)
    expratio.SetBinContent(i, j, hists1['exp0'].GetBinContent(i,j) - hists2['exp0'].GetBinContent(i,j))
    if expratio.GetBinContent(i, j)<ratiomin: expratio.SetBinContent(i, j, ratiomin+0.001)
    clsobsa.SetBinContent(i, j, hists1['obs'].GetBinContent(i,j))
    clsobsb.SetBinContent(i, j, hists2['obs'].GetBinContent(i,j))
    clsexpa.SetBinContent(i, j, hists1['exp0'].GetBinContent(i,j))
    clsexpb.SetBinContent(i, j, hists2['exp0'].GetBinContent(i,j))

if args.model != '':
  if args.model == 'mhmodp' or args.scenario == 'mhmodp': xsbrfilename = 'mhmodp_mu200_13TeV.root'
  elif args.model == 'hmssm' or args.scenario == 'hMSSM': xsbrfilename = 'hMSSM_13TeV.root'
  else: xsbrfilename = args.model
  xsbr = h_proto.Clone()
  xsbrfile = ROOT.TFile('../../auxiliaries/models/'+xsbrfilename)
  for i in xrange(1, xsbr.GetNbinsX() + 1):
    for j in xrange(1, xsbr.GetNbinsY() + 1):
      xxsbr = xsbr.GetXaxis().GetBinCenter(i)
      yxsbr = xsbr.GetYaxis().GetBinCenter(j)
      content = GetXsBr('xs_gg_h', 'br_h_tautau', xxsbr, yxsbr)
      content += GetXsBr('xs_bb4F_h', 'br_h_tautau', xxsbr, yxsbr)
      content = GetXsBr('xs_gg_H', 'br_H_tautau', xxsbr, yxsbr)
      content += GetXsBr('xs_bb4F_H', 'br_H_tautau', xxsbr, yxsbr)
      content = GetXsBr('xs_gg_A', 'br_A_tautau', xxsbr, yxsbr)
      content += GetXsBr('xs_bb4F_A', 'br_A_tautau', xxsbr, yxsbr)
      xsbr.SetBinContent(i, j, content)

# Setup the canvas: we'll use a two pad split, with a small top pad to contain
# the CMS logo and the legend
canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()


if 'obs' in contours1:
  for i, gr in enumerate(contours1['obs']):
    plot.Set(gr, LineColor=ROOT.kBlack, LineWidth=1)
    gr.Draw('LSAME')
if 'obs' in contours2:
  for i, gr in enumerate(contours2['obs']):
    plot.Set(gr, LineColor=ROOT.kRed, LineWidth=1)
    gr.Draw('LSAME')

if 'exp0' in contours1:
  for i, gr in enumerate(contours1['exp0']):
    plot.Set(gr, LineColor=ROOT.kGray+2, LineStyle=2, LineWidth=1)
    gr.Draw('LSAME')
if 'exp0' in contours2:
  for i, gr in enumerate(contours2['exp0']):
    plot.Set(gr, LineColor=ROOT.kRed-7, LineStyle=2, LineWidth=1)
    gr.Draw('LSAME')
   

# We just want the top pad to look like a box, so set all the text and tick
# sizes to zero
pads[0].cd()
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

# Draw the legend in the top TPad
legend = ROOT.TLegend(0.19 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 0.99 - ROOT.gPad.GetRightMargin(), 0.99 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=2, Header='#bf{%.0f%% CL Excluded:}' % (args.CL*100.))
if 'obs' in contours1:
  legend.AddEntry(contours1['obs'][0], "Observed "+nameone, "L")
if 'obs' in contours2:
  legend.AddEntry(contours2['obs'][0], "Observed "+nametwo, "L")
if 'exp0' in contours1:
  legend.AddEntry(contours1['exp0'][0], "Expected "+nameone, "L")
if 'exp0' in contours2:
  legend.AddEntry(contours2['exp0'][0], "Expected "+nametwo, "L")


legend.Draw()

# Draw logos and titles
#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

# Redraw the frame because it usually gets covered by the filled areas
pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

# Draw the scenario label
latex = ROOT.TLatex()
latex.SetNDC()
latex.SetTextSize(0.04)
latex.DrawLatex(0.155, 0.75, args.scenario)
latex.DrawLatex(0.155, 0.70, testtype)

canv.SaveAs("TwoLimits_AllLimits_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()

if 'exp-2' in contours2:
  for i, gr in enumerate(contours2['exp-2']):
    plot.Set(gr, FillColor=ROOT.kRed-10, FillStyle=1001)
    gr.Draw('FSAME')
if 'exp-1' in contours2:
  for i, gr in enumerate(contours2['exp-1']):
    plot.Set(gr, FillColor=ROOT.kRed-7, FillStyle=1001)
    gr.Draw('FSAME')
if 'exp0' in contours2:
  for i, gr in enumerate(contours2['exp0']):
    plot.Set(gr, LineColor=ROOT.kRed+2, LineStyle=1, LineWidth=3, FillColor=ROOT.kRed-9, FillStyle=1001)
    gr.Draw('LSAME')
if 'exp+1' in contours2:
  for i, gr in enumerate(contours2['exp+1']):
    plot.Set(gr, FillColor=ROOT.kRed-10, FillStyle=1001)
    gr.Draw('FSAME')
if 'exp+2' in contours2:
  for i, gr in enumerate(contours2['exp+2']):
    plot.Set(gr, FillColor=10, FillStyle=1001)
    gr.Draw('FSAME')

if 'exp-2' in contours1:
  for i, gr in enumerate(contours1['exp-2']):
    plot.Set(gr, LineColor=ROOT.kAzure+7, LineStyle=1, LineWidth=2)
    gr.Draw('LSAME')
if 'exp-1' in contours1:
  for i, gr in enumerate(contours1['exp-1']):
    plot.Set(gr, LineColor=ROOT.kBlue, LineStyle=1, LineWidth=2)
    gr.Draw('LSAME')
if 'exp0' in contours1:
  for i, gr in enumerate(contours1['exp0']):
    plot.Set(gr, LineColor=ROOT.kBlue+2, LineStyle=2, LineWidth=2)
    gr.Draw('LSAME')
if 'exp+1' in contours1:
  for i, gr in enumerate(contours1['exp+1']):
    plot.Set(gr, LineColor=ROOT.kBlue, LineStyle=1, LineWidth=2)
    gr.Draw('LSAME')
if 'exp+2' in contours1:
  for i, gr in enumerate(contours1['exp+2']):
    plot.Set(gr, LineColor=ROOT.kAzure+7, LineStyle=1, LineWidth=2)
    gr.Draw('LSAME')

pads[0].cd()
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

legend = ROOT.TLegend(0.19 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 0.99 - ROOT.gPad.GetRightMargin(), 0.99 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=3, Header='#bf{Contours of expected error bands}')
if 'exp0' in contours1:
  legend.AddEntry(contours1['exp0'][0], nameone + " Exp.", "L")
  legend.AddEntry(contours1['exp-1'][0], nameone + " #pm 1#sigma", "L")
  legend.AddEntry(contours1['exp-2'][0], nameone + " #pm 2#sigma", "L")
if 'exp0' in contours2:
  legend.AddEntry(contours2['exp0'][0], nametwo + " Exp.", "L")
  legend.AddEntry(contours2['exp-1'][0], nametwo + " #pm 1#sigma", "F")
  legend.AddEntry(contours2['exp-2'][0], nametwo + " #pm 2#sigma", "F")

legend.Draw()

#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

latex.DrawLatex(0.155, 0.75, args.scenario)
latex.DrawLatex(0.155, 0.70, testtype)

canv.SaveAs("TwoLimits_SigmaBands_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.GetXaxis().SetLabelSize(0.035)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()

pads[1].SetRightMargin(0.15)
clsobsa.SetMaximum(1.5)
clsobsa.SetMinimum(-0.001)
clsobsa.SetContour(25)
clsobsa.Draw("COLZ SAME")

if 'obs' in contours1:
  for i, gr in enumerate(contours1['obs']):
    plot.Set(gr, LineColor=ROOT.kRed, LineWidth=2)
    gr.Draw('LSAME')

pads[0].cd()
pads[0].SetRightMargin(0.10)
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

legend = ROOT.TLegend(0.25 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 0.99 - ROOT.gPad.GetRightMargin(), 0.99 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=1, Header='#bf{Observed CL_{s} from '+nameone+'}')
if 'obs' in contours1:
  legend.AddEntry(contours1['obs'][0], nameone + " observed %.0f%% CL Excluded" % (args.CL*100.), "L")

legend.Draw()

#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

lx1 = ROOT.TLatex(2260,42,"CLs")
lx1.SetTextAngle(270)
lx1.SetTextSize(0.04)
latex.SetTextColor(ROOT.kGray)
latex.DrawLatex(0.155, 0.70, args.scenario)
latex.DrawLatex(0.155, 0.65, testtype)
latex.DrawLatex(0.155, 0.75, nameone)
lx1.Draw()

canv.SaveAs("TwoLimits_CLsObs"+shortnameone+"_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.GetXaxis().SetLabelSize(0.035)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()

pads[1].SetRightMargin(0.15)
clsobsb.SetMaximum(1.5)
clsobsb.SetMinimum(-0.001)
clsobsb.SetContour(25)
clsobsb.Draw("COLZ SAME")

if 'obs' in contours2:
  for i, gr in enumerate(contours2['obs']):
    plot.Set(gr, LineColor=ROOT.kRed, LineWidth=2)
    gr.Draw('LSAME')

pads[0].cd()
pads[0].SetRightMargin(0.10)
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

legend = ROOT.TLegend(0.25 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 0.99 - ROOT.gPad.GetRightMargin(), 0.99 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=1, Header='#bf{Observed CL_{s} from '+nametwo+'}')
if 'obs' in contours2:
  legend.AddEntry(contours2['obs'][0], nametwo + " observed %.0f%% CL Excluded" % (args.CL*100.), "L")

legend.Draw()

#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

latex.DrawLatex(0.155, 0.70, args.scenario)
latex.DrawLatex(0.155, 0.65, testtype)
latex.DrawLatex(0.155, 0.75, nametwo)
lx1.Draw()

canv.SaveAs("TwoLimits_CLsObs"+shortnametwo+"_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.GetXaxis().SetLabelSize(0.035)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()

pads[1].SetRightMargin(0.15)
clsexpa.SetMaximum(1.5)
clsexpa.SetMinimum(-0.001)
clsexpa.SetContour(25)
clsexpa.Draw("COLZ SAME")

if 'exp0' in contours1:
  for i, gr in enumerate(contours1['exp0']):
    plot.Set(gr, LineColor=ROOT.kRed, LineStyle=1, LineWidth=2)
    gr.Draw('LSAME')

pads[0].cd()
pads[0].SetRightMargin(0.10)
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

legend = ROOT.TLegend(0.25 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 0.99 - ROOT.gPad.GetRightMargin(), 0.99 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=1, Header='#bf{Expected CL_{s} from '+nameone+'}')
if 'exp0' in contours1:
  legend.AddEntry(contours1['exp0'][0], nameone + " expected %.0f%% CL Excluded" % (args.CL*100.), "L")

legend.Draw()

#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

latex.DrawLatex(0.155, 0.70, args.scenario)
latex.DrawLatex(0.155, 0.65, testtype)
latex.DrawLatex(0.155, 0.75, nameone)
lx1.Draw()

canv.SaveAs("TwoLimits_CLsExp"+shortnameone+"_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.GetXaxis().SetLabelSize(0.035)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()

pads[1].SetRightMargin(0.15)
clsexpb.SetMaximum(1.5)
clsexpb.SetMinimum(-0.001)
clsexpb.SetContour(25)
clsexpb.Draw("COLZ SAME")

if 'exp0' in contours2:
  for i, gr in enumerate(contours2['exp0']):
    plot.Set(gr, LineColor=ROOT.kRed, LineStyle=1, LineWidth=2)
    gr.Draw('LSAME')

pads[0].cd()
pads[0].SetRightMargin(0.10)
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

legend = ROOT.TLegend(0.25 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 0.99 - ROOT.gPad.GetRightMargin(), 0.99 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=1, Header='#bf{Expected CL_{s} from '+nametwo+'}')
if 'exp0' in contours2:
  legend.AddEntry(contours2['exp0'][0], nametwo + " expected %.0f%% CL Excluded" % (args.CL*100.), "L")

legend.Draw()

#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

latex.DrawLatex(0.155, 0.70, args.scenario)
latex.DrawLatex(0.155, 0.65, testtype)
latex.DrawLatex(0.155, 0.75, nametwo)
lx1.Draw()

canv.SaveAs("TwoLimits_CLsExp"+shortnametwo+"_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.GetXaxis().SetLabelSize(0.035)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()

pads[1].SetRightMargin(0.18)
obsratio.SetMaximum(-1*ratiomin)
obsratio.SetMinimum(ratiomin)
obsratio.SetContour(25)
obsratio.Draw("COLZ SAME")

if 'obs' in contours1:
  for i, gr in enumerate(contours1['obs']):
    plot.Set(gr, LineColor=ROOT.kBlack, LineWidth=3)
    gr.Draw('LSAME')
if 'obs' in contours2:
  for i, gr in enumerate(contours2['obs']):
    plot.Set(gr, LineColor=ROOT.kRed, LineWidth=3, LineStyle=2)
    gr.Draw('LSAME')

pads[0].cd()
pads[0].SetRightMargin(0.13)
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

legend = ROOT.TLegend(0.28 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 1.00 - ROOT.gPad.GetRightMargin(), 0.995 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=1, Header='#bf{Difference of observed CL_{s}}')
if 'obs' in contours1:
  legend.AddEntry(contours1['obs'][0], nameone + " observed %.0f%% CL Excluded" % (args.CL*100.), "L")
if 'obs' in contours2:
  legend.AddEntry(contours2['obs'][0], nametwo + " observed %.0f%% CL Excluded" % (args.CL*100.), "L")

legend.Draw()

#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

latex.SetTextColor(ROOT.kBlack)
latex.DrawLatex(0.155, 0.75, args.scenario)
latex.DrawLatex(0.155, 0.70, testtype)

lxx3 = ROOT.TLatex(2400,52,"CLs_{"+shortnameone+"} - CLs_{"+shortnametwo+"}")
lxx3.SetTextAngle(270)
lxx3.SetTextSize(0.04)
lxx3.Draw()

canv.SaveAs("TwoLimits_ObsRatio_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

canv = ROOT.TCanvas(args.output, args.output)
pads = plot.TwoPadSplit(0.8, 0, 0)
pads[1].cd()
h_axis.GetXaxis().SetTitle(args.x_title)
h_axis.GetYaxis().SetTitle(args.y_title)
h_axis.GetXaxis().SetLabelSize(0.035)
h_axis.Draw()

pads[1].SetLogy(args.logy)
pads[1].SetLogx(args.logx)
pads[1].SetTickx()
pads[1].SetTicky()

pads[1].SetRightMargin(0.18)
expratio.SetMaximum(-1*ratiomin)
expratio.SetMinimum(ratiomin)
expratio.SetContour(25)
expratio.Draw("COLZ SAME")

if 'exp0' in contours1:
  for i, gr in enumerate(contours1['exp0']):
    plot.Set(gr, LineColor=ROOT.kBlack, LineWidth=3, LineStyle=1)
    gr.Draw('LSAME')
if 'exp0' in contours2:
  for i, gr in enumerate(contours2['exp0']):
    plot.Set(gr, LineColor=ROOT.kRed, LineWidth=3, LineStyle=2)
    gr.Draw('LSAME')

pads[0].cd()
pads[0].SetRightMargin(0.13)
h_top = h_axis.Clone()
plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
h_top.Draw()

legend = ROOT.TLegend(0.28 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 1.00 - ROOT.gPad.GetRightMargin(), 0.995 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
plot.Set(legend, NColumns=1, Header='#bf{Difference of expected CL_{s}}')
if 'exp0' in contours1:
  legend.AddEntry(contours1['exp0'][0], nameone + " expected %.0f%% CL Excluded" % (args.CL*100.), "L")
if 'exp0' in contours2:
  legend.AddEntry(contours2['exp0'][0], nametwo + " expected %.0f%% CL Excluded" % (args.CL*100.), "L")

legend.Draw()

#plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
plot.DrawTitle(pads[0], args.title_right, 3)
plot.DrawTitle(pads[0], args.title_left, 1)

pads[1].cd()
pads[1].GetFrame().Draw()
pads[1].RedrawAxis()

latex.DrawLatex(0.155, 0.75, args.scenario)
latex.DrawLatex(0.155, 0.70, testtype)

lxx3.Draw()

canv.SaveAs("TwoLimits_ExpRatio_"+dataset+shortnameone+"_"+shortnametwo+".png")
canv.Close()

######################

tanbl = [30,  30,  60,  60,  60,  60,   60] # <----------- Edit values here
mal =   [400, 500, 400, 500, 850, 1000, 1600]
for j,ma in enumerate(mal):
  tanb = tanbl[j]
  obsacls = ROOT.TH1F('obsacls', '', 60, 0, 60)
  obsbcls = ROOT.TH1F('obsbcls', '', 60, 0, 60)
  expacls = ROOT.TH1F('expacls', '', 60, 0, 60)
  expbcls = ROOT.TH1F('expbcls', '', 60, 0, 60)
  const005 = ROOT.TF1('const005', '0.05', -5, 65)

  for i in xrange(1,30+1):
    obsacls.SetBinContent(i,hists1['obs'].GetBinContent(hists1['obs'].GetXaxis().FindBin(ma),i-1))
    obsbcls.SetBinContent(i,hists2['obs'].GetBinContent(hists2['obs'].GetXaxis().FindBin(ma),i-1))
    expacls.SetBinContent(i,hists1['exp0'].GetBinContent(hists1['exp0'].GetXaxis().FindBin(ma),i-1))
    expbcls.SetBinContent(i,hists2['exp0'].GetBinContent(hists2['exp0'].GetXaxis().FindBin(ma),i-1))
  if tanb>30:
    for i in xrange(31,45+1):
      obsacls.SetBinContent(2*i-30,hists1['obs'].GetBinContent(hists1['obs'].GetXaxis().FindBin(ma),i-1))
      obsbcls.SetBinContent(2*i-30,hists2['obs'].GetBinContent(hists2['obs'].GetXaxis().FindBin(ma),i-1))
      expacls.SetBinContent(2*i-30,hists1['exp0'].GetBinContent(hists1['exp0'].GetXaxis().FindBin(ma),i-1))
      expbcls.SetBinContent(2*i-30,hists2['exp0'].GetBinContent(hists2['exp0'].GetXaxis().FindBin(ma),i-1))

      obsacls.SetBinContent(2*i-31,(obsacls.GetBinContent(2*i-30)+obsacls.GetBinContent(2*i-32))/2.0)
      obsbcls.SetBinContent(2*i-31,(obsbcls.GetBinContent(2*i-30)+obsbcls.GetBinContent(2*i-32))/2.0)
      expacls.SetBinContent(2*i-31,(expacls.GetBinContent(2*i-30)+expacls.GetBinContent(2*i-32))/2.0)
      expbcls.SetBinContent(2*i-31,(expbcls.GetBinContent(2*i-30)+expbcls.GetBinContent(2*i-32))/2.0)


#---

  canv = ROOT.TCanvas(args.output, args.output)
  pads = plot.TwoPadSplit(0.8, 0, 0)
  pads[1].cd()
  h_top = h_axis.Clone()
  obsacls.GetXaxis().SetTitle(args.y_title)
  obsacls.GetYaxis().SetTitle("CL_{s}")
  obsacls.GetXaxis().SetLabelSize(0.035)

  pads[1].SetLogy(1)
  pads[1].SetLogx(0)
  pads[1].SetTickx()
  pads[1].SetTicky()

  obsacls.GetXaxis().SetRangeUser(1,tanb)
  obsacls.GetYaxis().SetRangeUser(0.0035+min(obsacls.GetMinimum(),obsbcls.GetMinimum(),expacls.GetMinimum(),expbcls.GetMinimum()),3*max(obsacls.GetMaximum(),obsbcls.GetMaximum(),expacls.GetMaximum(),expbcls.GetMaximum()))

  plot.Set(obsacls, LineColor=ROOT.kBlack, LineWidth=3, LineStyle=1)
  obsacls.Draw('L')
  plot.Set(obsbcls, LineColor=ROOT.kRed+1, LineWidth=3, LineStyle=1)
  obsbcls.Draw('LSAME')
  plot.Set(expacls, LineColor=ROOT.kGray, LineWidth=3, LineStyle=2)
  expacls.Draw('LSAME')
  plot.Set(expbcls, LineColor=ROOT.kRed-7, LineWidth=3, LineStyle=2)
  expbcls.Draw('LSAME')
  plot.Set(const005, LineColor=ROOT.kBlue, LineWidth=2, LineStyle=2)
  const005.Draw('LSAME')

  pads[0].cd()
  h_top = h_axis.Clone()
  plot.Set(h_top.GetXaxis(), LabelSize=0, TitleSize=0, TickLength=0)
  plot.Set(h_top.GetYaxis(), LabelSize=0, TitleSize=0, TickLength=0)
  h_top.Draw()

  legend = ROOT.TLegend(0.19 - ROOT.gPad.GetRightMargin(), 0.86 - ROOT.gPad.GetTopMargin(), 0.99 - ROOT.gPad.GetRightMargin(), 0.99 - ROOT.gPad.GetTopMargin(), '', 'NBNDC')
  plot.Set(legend, NColumns=2, Header='#bf{CL_{s} values at m_{A}='+str(ma)+' GeV}')
  legend.AddEntry(obsacls, "Observed "+nameone, "L")
  legend.AddEntry(obsbcls, "Observed "+nametwo, "L")
  legend.AddEntry(expacls, "Expected "+nameone, "L")
  legend.AddEntry(expbcls, "Expected "+nametwo, "L")

  legend.Draw()

  #plot.DrawCMSLogo(pads[0], 'CMS', args.cms_sub, 11, 0.045, 0.15, 1.0, '', 1.0)
  plot.DrawTitle(pads[0], args.title_right, 3)
  plot.DrawTitle(pads[0], args.title_left, 1)

  pads[1].cd()
  pads[1].GetFrame().Draw()
  pads[1].RedrawAxis()

  latex.DrawLatex(0.645, 0.75, args.scenario)
  latex.DrawLatex(0.645, 0.70, testtype)
  latex005 = ROOT.TLatex(0, 0.05, "0.05")
  latex005.SetTextAlign(32)
  latex005.SetTextSize(0.04)
  latex005.Draw()

  canv.SaveAs("TwoLimits_CLs"+str(ma)+"."+str(tanb)+"_"+dataset+shortnameone+"_"+shortnametwo+".png")
  obsacls.Delete()
  obsbcls.Delete()
  expacls.Delete()
  expbcls.Delete()
  const005.Delete()
  canv.Close()

exit()
