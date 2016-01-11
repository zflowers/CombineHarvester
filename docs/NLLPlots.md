Two-dimensional Negative Log Likelihood plots using MorphingMSSMUpdate {#NLLPlots}
=====================================================================================

These instruction shall elaborate how to produce MSSM model independent 2D NLL plots using the 8TeV part of the MSSM (CMS-PAS-HIG-14-029) analysis.


Creating datacards {#p1}
========================

The first step is to create the datacards, which will be used to produce the limit later on. To do this, go into the folder CombineHarvester/Run1BSMComb/ and then execute MorphingMSSMUpdate. All of the programs in the following steps also need to be executed from this folder. Also make sure that all the files have been computed beforehand:

    cd CombineHarvester/Run1BSMComb/
    MorphingMSSMUpdate -m MH

`MorphingMSSMUpdate.cpp` is set up similarly like `Example2.cpp`. More information about the datacard steps could be found in the respective example. Adding the option `-m MH` when executing MorphingMSSMUpdate is necessary to ensure that the signal types are set to only assume one single narrow resonance produced via ggH and bbH instead of distinguishing between the three neutral MSSM bosons h, A and H.
It should be mentioned that CombineHarvester needs to use specific shape-rootfiles, which have been edited to reproduce the original result, since tail-fitting is not yet included in Combine Harvester.
The output will be a set of datacards. The special point is that not for each mass a datacard is created. In contrast a workspace is given for the signals which contain all centrally produced mass hypotheses. In the calculating process the signal will be morphed to the chosen mass. If, for example, MC signal templates exist for m=100GeV and 200GeV one could still calculate limits for m=150GeV (`combine -m 150 ...`). A root file, named `htt_mssm_demo.root`, will be in the folder `output/mssm_nomodel/`. It contains the centrally available MC signals for each channel, category and mass. Per default a combined datacard `htt_mssm.txt` is created, which contains all the information of the other datacards together.


Scaling the workspace accordingly {#p2}
=======================================

The combined datacard `htt_mssm.txt` is now transfered to a MSSM model independent workspace.

    text2workspace.py -b output/mssm_nomodel/htt_mssm.txt -o output/mssm_nomodel/htt_ggH_bbH_mssm.root --default-morphing shape2 -P CombineHarvester.CombinePdfs.ModelIndependent:floatingMSSMXSHiggs

This creates a workspace `output/mssm_nomodel/htt_ggH_bbH_mssm.root` based on the combined datacard. The physic model **floatingMSSMXSHiggs** is built to split the signal into the processes ggH and bbH. By default, both ggH and bbH modes are already set in the floatingMSSMXSHiggs class, so a limit will be set on the xs*BR of the ggH as well as the bbH process. Their ranges will be changed automatically in the next step.


Calculating values {#p3}
========================

In the next step we calculate the limits.

    python ../CombineTools/scripts/combineTool.py output/mssm_nomodel/htt_ggH_bbH_mssm.root -M MultiDimFit --algo grid -m 100 --points 40000 --split-points 200 --boundlist ../CombinePdfs/scripts/mssm_ggh_bbh_boundaries.json --minimizerStrategy=0 --minimizerTolerance=0.1 --cminPreScan --freezeNuisances MH --cminFallbackAlgo "Minuit2,0:1.0" --cminFallbackAlgo "Minuit2,0:10.0" --cminFallbackAlgo "Minuit2,0:50.0" --cminFallbackAlgo "Minuit2,0:100.0" --job-mode 'lxbatch' --task-name 'multidimfit100' --sub-opts '-q 1nh'

The method used is called **MultiDimFit**. The mass for mH needs to be specified with `-m`. Next comes the amount of points that will be computed. In order to be able to do this, the option `--algo grid` needs to be set. Now the amount of points can be set with `--points`. To avoid having one single large job, the option `--split-points` should be used to set the maximum amount of points to be calculated in a single job. These points are evenly spread apart within the ranges of ggH and bbH, which are given by the json file specified in `--boundlist`. This json file contains a list of ranges for ggH and bbH depending on the mass mH. With the option `--job-mode` (along with the corresponding options `--task-name` and `--sub-opts`) we can set where to send the jobs to, such as lxbatch, NAF, crab3 or interactive.
The remaining options in the command line above which haven't been explained yet are needed in order to produce a meaningful graph. First of all, the mass which has been set to 100GeV needs to be set in place, which is why we need `--freezeNuisances MH`. The strategy and the tolerance of the minimizer **Minuit2** are set to 0 and 0.1 respectevly. The strategy can theoreticly be set to 0, 1 or 2, whereas higher values correspond to using more derivatives in the fit, which is slower but may give better results. The strategy is set to 0 here, because this way the best-fit point is calculated correctly.
It may happen quite frequently, that the computation (the minimization) for certain points fails. If this happens, the fallback algorithms `--cminFallbackAlgo` kick in. The first of these is specified with `"Minuit2,0:1.0"`. This means, that the Minuit2 minimizer is now used with the strategy 0 and a tolerance of 1. If this also fails, then the next fallback algorithm kicks in, which also has the same setting, but a higher tolerance. A higher tolerance generally means that the computation will take longer, which is the reason why we don't use a tolerance of 100 right from the start. The option `--cminPreScan` simply does a quick scan before starting with the minimization process.


Collecting the results in a single file {#p4}
=============================================

After all jobs have finished, if the option `--split-points` was used, there will now be many rootfiles with the word `POINTS` in them. We use `hadd` to collect all these rootfiles into a single file.

    hadd higgsCombine.Test.MultiDimFit.mH100.root higgsCombine.Test.POINTS.*.mH100.root


Plotting the limits {#p5}
=========================

The plotting is done be the `plotMultiDimFit.py` script.

    python ../CombineTools/scripts/plotMultiDimFit.py -f higgsCombine.Test.MultiDimFit.mH100.root

The filename after `-f` has to be the root file which was created in the previous step. `plotMultiDimFit.py` will only produce the plots as a png- and pdf file. The plotting is still work in progress.
