import os
import stat
import glob
from functools import partial
from multiprocessing import Pool
import CombineHarvester.CombineTools.combine.utils as utils

DRY_RUN = False

JOB_PREFIX = """#!/bin/sh
ulimit -s unlimited
set -e
cd %(CMSSW_BASE)s/src
export SCRAM_ARCH=%(SCRAM_ARCH)s
source /cvmfs/cms.cern.ch/cmsset_default.sh
eval `scramv1 runtime -sh`
cd %(PWD)s
""" % ({
    'CMSSW_BASE': os.environ['CMSSW_BASE'],
    'SCRAM_ARCH': os.environ['SCRAM_ARCH'],
    'PWD': os.environ['PWD']
})

JOB_PREFIX_CONNECT = """#!/bin/bash
ulimit -s unlimited
set -e
export SCRAM_ARCH=%(SCRAM_ARCH)s
source /cvmfs/cms.cern.ch/cmsset_default.sh
#wget --quiet --no-check-certificate http://stash.osgconnect.net/+zflowers/cmssw_setup_connect.sh 
source cmssw_setup_connect.sh
#wget --quiet --no-check-certificate http://stash.osgconnect.net/+%(SANDBOX_PATH)s/%(SANDBOX)s
#cmssw_setup %(SANDBOX)s
#mkdir -p cmssw-tmp/%(CMSSW_VERSION)s/src/%(PATH)s/
#cd cmssw-tmp/%(CMSSW_VERSION)s/src/%(PATH)s/
cmssw_setup sandbox-CMSSW_10_6_5-6403d6f.tar.bz2
mkdir -p cmssw-tmp/CMSSW_10_6_5/src/%(PATH)s/
cp --parents %(FILE)s cmssw-tmp/CMSSW_10_6_5/src/%(PATH)s/
cd cmssw-tmp/CMSSW_10_6_5/src/%(PATH)s/
eval `scramv1 runtime -sh`

"""

CONDOR_TEMPLATE = """executable = %(EXE)s
arguments = $(ProcId)
output                = %(TASK)s.$(ClusterId).$(ProcId).out
error                 = %(TASK)s.$(ClusterId).$(ProcId).err
log                   = %(TASK)s.$(ClusterId).log

# Send the job to Held state on failure.
on_exit_hold = (ExitBySignal == True) || (ExitCode != 0)

# Periodically retry the jobs every 10 minutes, up to a maximum of 5 retries.
periodic_release =  (NumJobStarts < 3) && ((CurrentTime - EnteredCurrentStatus) > 600)

%(EXTRA)s
queue %(NUMBER)s

"""

CONNECT_TEMPLATE = """executable = %(EXE)s
universe = vanilla
use_x509userproxy = true
getenv = True 
arguments = $(ProcId)
output                = %(TASK)s.$(ClusterId).$(ProcId).out
error                 = %(TASK)s.$(ClusterId).$(ProcId).err
log                   = %(TASK)s.$(ClusterId).log

# Periodically retry the jobs every 10 minutes, up to a maximum of 5 retries.
periodic_release =  (NumJobStarts < 3) && ((CurrentTime - EnteredCurrentStatus) > 600)

preserve_relative_paths = True

transfer_input_files = /uscms/home/z374f439/nobackup/whatever_you_want/sandbox-CMSSW_10_6_5-6403d6f.tar.bz2,/uscms/home/z374f439/nobackup/whatever_you_want/cmssw_setup_connect.sh,%(DATACARD)s,%(IFILE)s
#transfer_input_files = %(DATACARD)s,%(IFILE)s
transfer_output_files = %(CMSSW_VERSION)s%(OPATH)s%(OFILE)s

request_memory = %(MEMORY)s MB
%(EXTRA)s
queue %(NUMBER)s

"""

CRAB_PREFIX = """
set -x
set -e
ulimit -s unlimited
ulimit -c 0

function error_exit
{
  if [ $1 -ne 0 ]; then
    echo "Error with exit code ${1}"
    if [ -e FrameworkJobReport.xml ]
    then
      cat << EOF > FrameworkJobReport.xml.tmp
      <FrameworkJobReport>
      <FrameworkError ExitStatus="${1}" Type="" >
      Error with exit code ${1}
      </FrameworkError>
EOF
      tail -n+2 FrameworkJobReport.xml >> FrameworkJobReport.xml.tmp
      mv FrameworkJobReport.xml.tmp FrameworkJobReport.xml
    else
      cat << EOF > FrameworkJobReport.xml
      <FrameworkJobReport>
      <FrameworkError ExitStatus="${1}" Type="" >
      Error with exit code ${1}
      </FrameworkError>
      </FrameworkJobReport>
EOF
    fi
    exit 0
  fi
}

trap 'error_exit $?' ERR
"""

CRAB_POSTFIX = """
tar -cf combine_output.tar higgsCombine*.root
rm higgsCombine*.root
"""


def run_command(dry_run, command, pre_cmd=''):
    if command.startswith('combine'):
        command = pre_cmd + command
    if not dry_run:
        print '>> ' + command
        return os.system(command)
    else:
        print '[DRY-RUN]: ' + command


class CombineToolBase:
    description = 'Base class that passes through all arguments to combine and handles job creation and submission'
    requires_root = False

    def __init__(self):
        self.job_queue = []
        self.args = None
        self.passthru = []
        self.job_mode = 'interactive'
        self.job_dir = ""
        self.prefix_file = ''
        self.input_file = ''
        self.parallel = 1
        self.merge = 1
        self.task_name = 'combine_task'
        self.dry_run = False
        self.bopts = ''  # batch submission options
        self.custom_crab = None
        self.custom_crab_post = None
        self.pre_cmd = ''
        self.crab_files = []
        self.method = ''
        self.name = None
        self.sandbox = 'sandbox-CMSSW_10_6_5-6403d6f.tar.bz2'
        self.sandbox_path = 'zflowers'
        self.make_sandbox = False

    def attach_job_args(self, group):
        group.add_argument('--job-mode', default=self.job_mode, choices=[
                           'interactive', 'script', 'lxbatch', 'SGE', 'slurm', 'condor', 'crab3', 'connect'], help='Task execution mode')
        group.add_argument('--job-dir', default=self.job_dir,
                           help='Path to directory containing job scripts and logs')
        group.add_argument('--prefix-file', default=self.prefix_file,
                           help='Path to file containing job prefix')
        group.add_argument('--input-file', default=self.input_file,
                           help='Path to input file that datacards reference (only needed with --job-mode connect)')
        group.add_argument('--sandbox', default=self.sandbox,
                           help='Name of sandbox to be used (only needed with --job-mode connect)')
        group.add_argument('--sandbox-path', default=self.sandbox_path,
                           help='Path to sandbox that is of the form "your_username/" The sandbox needs to be in some area like /stash/username/public/ with proper permissions (only needed with --job-mode connect)')
        group.add_argument('--make-sandbox', action='store_true',
                           help='Path to input file that datacards reference (only needed with --job-mode connect)')
        group.add_argument('--task-name', default=self.task_name,
                           help='Task name, used for job script and log filenames for batch system tasks')
        group.add_argument('--parallel', type=int, default=self.parallel,
                           help='Number of jobs to run in parallel [only affects interactive job-mode]')
        group.add_argument('--merge', type=int, default=self.merge,
                           help='Number of jobs to run in a single script [only affects batch submission]')
        group.add_argument('--dry-run', action='store_true',
                           help='Print commands to the screen but do not run them')
        group.add_argument('--sub-opts', default=self.bopts,
                           help='Options for batch/crab submission')
        group.add_argument('--memory', type=int,
                           help='Request memory for job [MB]')
        group.add_argument('--crab-area',
                           help='crab working area')
        group.add_argument('--custom-crab', default=self.custom_crab,
                           help='python file containing a function with name signature "custom_crab(config)" that can be used to modify the default crab configuration')
        group.add_argument('--crab-extra-files', nargs='+', default=self.crab_files,
                           help='Extra files that should be shipped to crab')
        group.add_argument('--pre-cmd', default=self.pre_cmd,
                           help='Prefix the call to combine with this string')
        group.add_argument('--custom-crab-post', default=self.custom_crab_post,
                           help='txt file containing command lines that can be used in the crab job script instead of the defaults.')

    def attach_intercept_args(self, group):
        pass

    def attach_args(self, group):
        pass

    def set_args(self, known, unknown):
        self.args = known 
        self.job_mode = self.args.job_mode
        self.job_dir = self.args.job_dir
        self.prefix_file = self.args.prefix_file
        self.input_file = self.args.input_file
        self.task_name = self.args.task_name
        self.parallel = self.args.parallel
        self.merge = self.args.merge
        self.dry_run = self.args.dry_run
        self.passthru.extend(unknown)
        self.bopts = self.args.sub_opts
        self.custom_crab = self.args.custom_crab
        self.memory = self.args.memory
        self.crab_area = self.args.crab_area
        self.crab_files = self.args.crab_extra_files
        self.pre_cmd = self.args.pre_cmd
        self.custom_crab_post = self.args.custom_crab_post
        self.method = self.args.method
        self.sandbox = self.args.sandbox
        self.sandbox_path = self.args.sandbox_path
        self.make_sandbox = self.args.make_sandbox
        try:
            if 'name' in self.args:
                self.name = self.args.name
        except:
            pass

    def put_back_arg(self, arg_name, target_name):
        if hasattr(self.args, arg_name):
            self.passthru.extend([target_name, getattr(self.args, arg_name)])
            delattr(self.args, arg_name)

    def extract_arg(self, arg, args_str):
        args_str = args_str.replace(arg+'=', arg+' ')
        args = args_str.split()
        if arg in args:
            idx = args.index(arg)
            assert idx != -1 and idx < len(args)
            val = args[idx+1]
            del args[idx:idx+2]
            return val, (' '.join(args))
        else:
            return None, args_str

    def sandbox_maker(self):
        CMSSW_VERSION = os.environ['CMSSW_VERSION']
        CMSSW_BASE = os.environ['CMSSW_BASE']
        print("Note that CMSSW Version is assumed to be: "+str(CMSSW_VERSION)+" inside of: "+str(CMSSW_BASE))
        print("Going to stash area")
        os.chdir('/stash/user/'+os.environ['USER']+'/')
        if not os.path.isdir('cmssw-sandbox'):
            print("Getting sandbox git repo")
            os.system('git clone https://github.com/CMSConnect/cmssw-sandbox')
        print("Making sandbox...")
        os.system('cmssw-sandbox/cmssw-sandbox create -a '+str(CMSSW_BASE))
        print("Setting up sandbox")
        if not os.path.isdir('public'):
            os.system('mkdir public')
            os.system('chmod 775 public/')
        sandbox = glob.glob('sandbox*'+CMSSW_VERSION+'*')[0]
        print("Assuming sandbox that was made is: "+str(sandbox))
        os.system('mv '+str(sandbox)+' public/')
        os.system('chmod 644 public/'+str(sandbox))
        self.sandbox = sandbox
        self.sandbox_path = os.environ['USER']
        os.chdir(os.environ['PWD'])

    def all_free_parameters(self, ws_file, wsp, mc, pois):
        res = []
        wsFile = ROOT.TFile.Open(file)
        w = wsFile.Get(wsp)
        FixAll(w)
        config = w.genobj(mc)
        pdfvars = config.GetPdf().getParameters(config.GetObservables())
        it = pdfvars.createIterator()
        var = it.Next()
        while var:
            if var.GetName() not in pois and (not var.isConstant()) and var.InheritsFrom("RooRealVar"):
                res.append(var.GetName())
            var = it.Next()
        return res

    def create_job_script(self, commands, script_filename, do_log = False):
        fname = script_filename
        logname = script_filename.replace('.sh', '.log')
        with open(fname, "w") as text_file:
            text_file.write(JOB_PREFIX)
            for i, command in enumerate(commands):
                tee = 'tee' if i == 0 else 'tee -a'
                log_part = '\n'
                if do_log: log_part = ' 2>&1 | %s ' % tee + logname + log_part
                if command.startswith('combine') or command.startswith('pushd'):
                    text_file.write(
                        self.pre_cmd + 'eval ' + command + log_part)
                else:
                    text_file.write(command)
        st = os.stat(fname)
        os.chmod(fname, st.st_mode | stat.S_IEXEC)
        # print JOB_PREFIX + command
        print 'Created job script: %s' % script_filename

    def run_method(self):
        print vars(self.args)
        # Put the method back in because we always take it out
        self.put_back_arg('method', '-M')
        print self.passthru
        command = 'combine ' + ' '.join(self.passthru)
        self.job_queue.append(command)
        self.flush_queue()

    def extract_workspace_arg(self, cmd_list=[]):
        for arg in ['-d', '--datacard']:
            if arg in cmd_list:
                idx = cmd_list.index(arg)
                assert idx != -1 and idx < len(cmd_list)
                return cmd_list[idx + 1]
        raise RuntimeError('The workspace argument must be specified explicity with -d or --datacard')

    def flush_queue(self):
        if self.job_mode == 'interactive':
            pool = Pool(processes=self.parallel)
            result = pool.map(
                partial(run_command, self.dry_run, pre_cmd=self.pre_cmd), self.job_queue)
        script_list = []
        if self.job_mode in ['script', 'lxbatch', 'SGE', 'slurm']:
            if self.prefix_file != '':
                if self.prefix_file.endswith('.txt'):
                  job_prefix_file = open(self.prefix_file,'r')
                else :
                  job_prefix_file = open(os.environ['CMSSW_BASE']+"/src/CombineHarvester/CombineTools/input/job_prefixes/job_prefix_"+self.prefix_file+".txt",'r')
                global JOB_PREFIX
                JOB_PREFIX=job_prefix_file.read() %({
                  'CMSSW_BASE': os.environ['CMSSW_BASE'],
                  'SCRAM_ARCH': os.environ['SCRAM_ARCH'],
                  'PWD': os.environ['PWD']
                })
                job_prefix_file.close()
        if self.job_mode in ['script', 'lxbatch', 'SGE']:
            for i, j in enumerate(range(0, len(self.job_queue), self.merge)):
                script_name = 'job_%s_%i.sh' % (self.task_name, i)
                # each job is given a slice from the list of combine commands of length 'merge'
                # we also keep track of the files that were created in case submission to a
                # batch system was also requested
                if self.job_dir:
                  if not os.path.exists(self.job_dir):
                    os.makedirs(self.job_dir)
                  script_name = os.path.join(self.job_dir,script_name)
                self.create_job_script(
                    self.job_queue[j:j + self.merge], script_name, self.job_mode == 'script')
                script_list.append(script_name)
        if self.job_mode == 'lxbatch':
            for script in script_list:
                full_script = os.path.abspath(script)
                logname = full_script.replace('.sh', '_%J.log')
                run_command(self.dry_run, 'bsub -o %s %s %s' % (logname, self.bopts, full_script))
        if self.job_mode == 'SGE':
            for script in script_list:
                full_script = os.path.abspath(script)
                logname = full_script.replace('.sh', '_%J.log')
                run_command(self.dry_run, 'qsub -o %s %s %s' % (logname, self.bopts, full_script))
        if self.job_mode == 'slurm':
            script_name = 'slurm_%s.sh' % self.task_name
            if self.job_dir:
                if not os.path.exists(self.job_dir):
                    os.makedirs(self.job_dir)
                script_name = os.path.join(self.job_dir,script_name)
            commands = []
            jobs = 0
            # each job is given a slice from the list of combine commands of length 'merge'
            for j in range(0, len(self.job_queue), self.merge):
                jobs += 1
                commands += ["if [ ${SLURM_ARRAY_TASK_ID} -eq %i ]; then\n" % jobs,
                        ]+["  %s\n" % ln for ln in self.job_queue[j:j + self.merge]]+["fi\n"]
            self.create_job_script(commands, script_name, self.job_mode == "script")
            full_script = os.path.abspath(script_name)
            logname = full_script.replace('.sh', '_%A_%a.log')
            run_command(self.dry_run, 'sbatch --array=1-%i -o %s %s %s' % (jobs, logname, self.bopts, full_script))
        if self.job_mode == 'condor':
            outscriptname = 'condor_%s.sh' % self.task_name
            subfilename = 'condor_%s.sub' % self.task_name
            print '>> condor job script will be %s' % outscriptname
            outscript = open(outscriptname, "w")
            outscript.write(JOB_PREFIX)
            jobs = 0
            wsp_files = set()
            for i, j in enumerate(range(0, len(self.job_queue), self.merge)):
                outscript.write('\nif [ $1 -eq %i ]; then\n' % jobs)
                jobs += 1
                for line in self.job_queue[j:j + self.merge]:
                    newline = self.pre_cmd + line
                    outscript.write('  ' + newline + '\n')
                outscript.write('fi')
            outscript.close()
            st = os.stat(outscriptname)
            os.chmod(outscriptname, st.st_mode | stat.S_IEXEC)
            subfile = open(subfilename, "w")
            condor_settings = CONDOR_TEMPLATE % {
              'EXE': outscriptname,
              'TASK': self.task_name,
              'EXTRA': self.bopts.decode('string_escape'),
              'NUMBER': jobs
            }
            subfile.write(condor_settings)
            subfile.close()
            run_command(self.dry_run, 'condor_submit %s' % (subfilename))
        if self.job_mode == 'connect':
            outscriptname = 'condor_%s.sh' % self.task_name
            subfilename = 'condor_%s.sub' % self.task_name
            name = 'Test'
            if self.name is not None:
                name = self.name
            if 'AsymptoticLimits' in self.method:
                for i, j in enumerate(range(0, len(self.job_queue), self.merge)):
                    for line in self.job_queue[j:j + self.merge]:
                        newline = self.pre_cmd + line
		datacard = str(self.extract_workspace_arg(newline.split())) 
		datacard_path = ''#datacard.rsplit('/',1)[0]
                if len(self.args.datacard) > 1: #do grid
			datacard_file = ''
			datacard_file_all = ''
			for d in self.args.datacard:
				datacard_file_all += d+' '
			datacard_file = 'datacards.tar.gz'
			os.system("tar -czf datacards.tar.gz "+datacard_file_all)
			datacard_file_all = datacard_file
		else:
			datacard_file = datacard
			datacard_file_all = datacard_file
            	#print 'self.args.datacard',self.args.datacard,'datacard_file:',datacard_file,'datacard_path:',datacard_path,'datacard:',datacard
	    elif 'T2W' in self.method:
                datacard = 'datacard.txt'
                datacard_file = datacard
		datacard_file_all = datacard_file
                datacard_path = ''
            elif 'Impact' in self.method:
                datacard_file = self.args.datacard
		datacard_file_all = datacard_file
                datacard_path = ''
            elif 'FitDiagnostics' in self.method:
		datacard_file = self.args.datacard[0]
		datacard_file_all = datacard_file
                datacard_path = ''
	    if self.input_file.count('../') > 3:
                for i in range(3,self.input_file.count('../')):
                    datacard_path = datacard_path + "/tmp"+str(i)+"/"
	    if 'T2W' in self.method:
                datacard_path = '/tmp1/'
            mass = ''
            if '-m' in self.passthru:
                mass = self.passthru[self.passthru.index('-m')+1]
            elif '--mass' in self.passthru:
                mass = self.passthru[self.passthru.index('--mass')+1]
            if 'MASS' in mass:
		if 'AsymptoticLimits' not in self.method: 
      	 #         mass = datacard.rsplit('/',1)[0]
      	  #        mass = mass.rsplit('/',0)[0]
      	   #       mass = mass[mass.rindex('/')+1:]
      	  		mass = os.getcwd().rsplit('/',1)[0]
		else:
			if len(self.args.datacard) > 1:
				mass = []
				for d in self.args.datacard:
					mass.append(d.rsplit('/',2)[-2])
			else:
				mass = datacard_file.rsplit('/')[-2]
			#mass = "*" if len(self.args.datacard) > 1 else datacard_file.rsplit('/')[-2] 
	    output_file = ''
            cmssw = 'cmssw-tmp/'+str(os.environ['CMSSW_VERSION'])+'/src/'
            if 'AsymptoticLimits' in self.method:
		cmssw = ''
	#	if type(mass) is list:
	#		output_file = ''
	#	#	for m in mass:
	#	#		#output_file += cmssw+datacard_path+datacard.rsplit('/',2)[0]+'/'+m+'/higgsCombine'+name+'.'+self.method+'.mH'+m+'.root,'
	#	#		output_file += cmssw+datacard_path+'higgsCombine'+name+'.'+self.method+'.mH'+m+'.root,'
	#	#	output_file = output_file[len(cmssw):-1]
	#	elif type(mass) is str and 'tar.gz' not in self.args.datacard:
	#		output_file = 'higgsCombine'+name+'.'+self.method+'.mH'+mass+'.root'
	#	else:
	#		output_file = ''
		#the FitInput file is copied to base dir, but then we move to the cmssw/CMSSW_10_6_5/src so it needs to be copied to this dir, which is done later
	#	if '/' in datacard_file: #FitInput_*.root file is transferred to execute dir, but not copied to cmssw/CMSSW_10_6_5/src dir (or the dir that the datacards are in)
	#		for i in range(datacard_file.count('/')+3):
	#			self.input_file = "../"+self.input_file
            	#print 'output_file:',output_file,'mass:',mass
	    elif 'T2W' in self.method:
                output_file = self.passthru[self.passthru.index('-o')+1]
                cmssw = ''
            elif 'Impacts' in self.method:
                if self.args.doInitialFit is True:
                    output_file = 'higgsCombine_initialFit_'+name+'.MultiDimFit.mH'+mass+'.root'
                elif self.args.doFits is True:
                    if self.args.redefineSignalPOIs is not None:
                        poiList = self.args.redefineSignalPOIs.split(',')
                    else:
                        poiList = utils.list_from_workspace(self.args.datacard, 'w', 'ModelConfig_POI')
                    paramList = self.all_free_parameters(self.args.datacard, 'w', 'ModelConfig',poiList)
                cmssw = ''
            elif 'FitDiagnostics' in self.method:
		output_file = 'fitDiagnostics'+name+'.root' 
                cmssw = ''
	    if self.make_sandbox:
                self.sandbox_maker()
            print '>> condor job script will be %s' % outscriptname
            outscript = open(outscriptname, "w")
            connect_job_prefix = JOB_PREFIX_CONNECT % {
              'CMSSW_VERSION': os.environ['CMSSW_VERSION'],
              'SCRAM_ARCH': os.environ['SCRAM_ARCH'],
              'PWD': os.environ['PWD'],
              'FILE': datacard_file_all,
              'PATH': datacard_path,
              'SANDBOX_PATH': self.sandbox_path,
              'SANDBOX': self.sandbox
            }
            outscript.write(connect_job_prefix)
            if 'AsymptoticLimits' in self.method: #copy fit input file to cmssw/CMSSW_10_6_5/src/ dir
                if len(self.args.datacard) > 1: #do grid
			outscript.write('tar -xf datacards.tar.gz\n')
		outscript.write('cp ../../../'+self.input_file+' .')
	    jobs = 0
            wsp_files = set()
            for i, j in enumerate(range(0, len(self.job_queue), self.merge)):
                outscript.write('\nif [ $1 -eq %i ]; then\n' % jobs)
                jobs += 1
                for line in self.job_queue[j:j + self.merge]:
                    newline = self.pre_cmd + line
                    outscript.write('  ' + newline + '\n')
                outscript.write('fi')
        #    if 'AsymptoticLimits' in self.method: #copy output files back to base dir
	#	outscript.write('\ncp '+output_file+' ../../../')
	    outscript.close()
	    if self.args.memory is None:
		mem = 2000
	    else:
		mem = self.args.memory
            st = os.stat(outscriptname)
            os.chmod(outscriptname, st.st_mode | stat.S_IEXEC)
            subfile = open(subfilename, "w")
            if 'T2W' in self.method:
		datacard_path = ''
 	    condor_settings = CONNECT_TEMPLATE % {
              'CMSSW_VERSION': cmssw,
              'EXE': outscriptname,
              'TASK': self.task_name,
              'EXTRA': self.bopts.decode('string_escape'),
              'MEMORY': str(mem),
	      'NUMBER': jobs,
              'DATACARD': datacard_file,
              'IFILE': self.input_file,
              'OPATH': datacard_path,
              'OFILE': output_file
            }
            subfile.write(condor_settings)
	    if 'AsymptoticLimits' in self.method:
            	#subfile.write('\npreserve_relative_paths=True')
                os.system("echo \"\nmv *AsymptoticLimits*.root ../../../ \" >> "+str(outscriptname))
	    subfile.close()
            if 'Impacts' in self.method:
                if self.args.doFits is True:
                    cmssw = ''
                    os.system("echo \"\nmv *param*.root ../../../ \" >> "+str(outscriptname))
                    os.system("echo \"\nrm ../../../sandbox* ../../../cmssw_setup* \" >> "+str(outscriptname))
                elif self.args.doInitialFit is True:
                    cmssw = ''
                    os.system("echo \"\nmv *initialFit*.root ../../../ \" >> "+str(outscriptname))
                    os.system("echo \"\nrm ../../../sandbox* ../../../cmssw_setup* \" >> "+str(outscriptname))
            if 'FitDiagnostics' in self.method:
                cmssw = ''
                os.system("echo \"\nmv *fitDiagnostics*.root ../../../ \" >> "+str(outscriptname))
            if 'T2W' in self.method:
	       cmssw = ''
	       print("here",datacard_path,output_file,self.method)  
	       os.system("echo \"\nmv "+output_file+" ../../../../ \" >> "+str(outscriptname))
	    run_command(self.dry_run, 'condor_submit %s' % (subfilename))

        if self.job_mode == 'crab3':
            #import the stuff we need
            from CRABAPI.RawCommand import crabCommand
            from httplib import HTTPException
            print '>> crab3 requestName will be %s' % self.task_name
            outscriptname = 'crab_%s.sh' % self.task_name
            print '>> crab3 script will be %s' % outscriptname
            outscript = open(outscriptname, "w")
            outscript.write(CRAB_PREFIX)
            jobs = 0
            wsp_files = set()
            for extra in self.crab_files:
                wsp_files.add(extra)
            for i, j in enumerate(range(0, len(self.job_queue), self.merge)):
                jobs += 1
                outscript.write('\nif [ $1 -eq %i ]; then\n' % jobs)
                for line in self.job_queue[j:j + self.merge]:
                    newline = line
                    if line.startswith('combine'): newline = self.pre_cmd + line.replace('combine', './combine', 1)
                    wsp = str(self.extract_workspace_arg(newline.split()))

                    newline = newline.replace(wsp, os.path.basename(wsp))
                    if wsp.startswith('root://'):
                        newline = ('./copyRemoteWorkspace.sh %s ./%s; ' % (wsp, os.path.basename(wsp))) + newline
                    else:
                        wsp_files.add(wsp)
                    outscript.write('  ' + newline + '\n')
                outscript.write('fi')
            if self.custom_crab_post is not None:
                with open(self.custom_crab_post, 'r') as postfile:
                    outscript.write(postfile.read())
            else:
                outscript.write(CRAB_POSTFIX)
            outscript.close()
            from CombineHarvester.CombineTools.combine.crab import config
            config.General.requestName = self.task_name
            config.JobType.scriptExe = outscriptname
            config.JobType.inputFiles.extend(wsp_files)
            config.Data.totalUnits = jobs
            config.Data.outputDatasetTag = config.General.requestName
            if self.memory is not None:
                config.JobType.maxMemoryMB = self.memory
            if self.crab_area is not None:
                config.General.workArea = self.crab_area
            if self.custom_crab is not None:
                d = {}
                execfile(self.custom_crab, d)
                d['custom_crab'](config)
            print config
            if not self.dry_run:
                try:
                    crabCommand('submit', config = config)
                except HTTPException, hte:
                    print hte.headers
        del self.job_queue[:]
