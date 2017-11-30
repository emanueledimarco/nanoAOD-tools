#!/usr/bin/env python
import os
import time
import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

class PostProcessor :
    def __init__(self,outputDir,inputFiles,cut=None,branchsel=None,modules=[],compression="LZMA:9",friend=False,postfix=None,
		 jsonInput=None,noOut=False,justcount=False,provenance=False,haddFileName=None,fwkJobReport=False,eventRange=None):
	self.outputDir=outputDir
	self.inputFiles=inputFiles
	self.cut=cut
	self.modules=modules
	self.compression=compression
	self.postfix=postfix
	self.json=jsonInput
	self.noOut=noOut
	self.friend=friend
	self.justcount=justcount
        self.eventRange=eventRange
	self.provenance=provenance
	self.jobReport = JobReport() if fwkJobReport else None
	self.haddFileName=haddFileName
	if self.jobReport and not self.haddFileName :
		print "Because you requested a FJR we assume you want the final hadd. No name specified for the output file, will use tree.root"
		self.haddFileName="tree.root"
 	self.branchsel = BranchSelection(branchsel) if branchsel else None 
    def run(self) :
    	if not self.noOut:
            outpostfix = self.postfix if self.postfix != None else ("_Friend" if self.friend else "_Skim")
            if self.compression != "none":
                ROOT.gInterpreter.ProcessLine("#include <Compression.h>")
                (algo, level) = self.compression.split(":")
                compressionLevel = int(level)
                if   algo == "LZMA": compressionAlgo  = ROOT.ROOT.kLZMA
                elif algo == "ZLIB": compressionAlgo  = ROOT.ROOT.kZLIB
                else: raise RuntimeError("Unsupported compression %s" % algo)
            else:
                compressionLevel = 0 
	    print "Will write selected trees to "+self.outputDir
            if not self.justcount:
                if not os.path.exists(self.outputDir):
                    os.system("mkdir -p "+self.outputDir)
        else:
            outpostfix = ''
            compressionLevel = 0

	if self.noOut:
	    if len(self.modules) == 0: 
		raise RuntimeError("Running with --noout and no modules does nothing!")

	for m in self.modules: m.beginJob()

	fullClone = (len(self.modules) == 0)
	outFileNames=[]
        t0 = time.clock()
	totEntriesRead=0
	for fname in self.inputFiles:

	    # open input file
            fetchedfile = None
            if 'LSB_JOBID' in os.environ or 'LSF_JOBID' in os.environ:
                if fname.startswith("root://"):
                    try:
                        tmpdir = os.environ['TMPDIR'] if 'TMPDIR' in os.environ else "/tmp"
                        tmpfile =  "%s/%s" % (tmpdir, os.path.basename(fname))
                        print "xrdcp %s %s" % (fname, tmpfile)
                        os.system("xrdcp %s %s" % (fname, tmpfile))
                        if os.path.exists(tmpfile):
                            fname = tmpfile
                            fetchedfile = fname
                            print "success :-)"
                    except:
                        pass
                inFile = ROOT.TFile.Open(fname)
            elif "root://" in fname:
                ROOT.gEnv.SetValue("TFile.AsyncReading", 1);
                ROOT.gEnv.SetValue("XNet.Debug", 0); # suppress output about opening connections
                ROOT.gEnv.SetValue("XrdClientDebug.kUSERDEBUG", 0); # suppress output about opening connections
                inFile   = ROOT.TXNetFile(fname+"?readaheadsz=65535&DebugLevel=0")
                os.environ["XRD_DEBUGLEVEL"]="0"
                os.environ["XRD_DebugLevel"]="0"
                os.environ["DEBUGLEVEL"]="0"
                os.environ["DebugLevel"]="0"
            else:
                inFile = ROOT.TFile.Open(fname)

	    #get input tree
	    inTree = inFile.Get("Events")
	    totEntriesRead+=inTree.GetEntries()
	    # pre-skimming
	    elist,jsonFilter = preSkim(inTree, self.json, self.cut)
	    if self.justcount:
		print 'Would select %d entries from %s'%(elist.GetN() if elist else inTree.GetEntries(), fname)
		continue
	    else:
		print 'Pre-select %d entries out of %s '%(elist.GetN() if elist else inTree.GetEntries(),inTree.GetEntries())
		
	    if fullClone:
		# no need of a reader (no event loop), but set up the elist if available
		if elist: inTree.SetEntryList(elist)
	    else:
		# initialize reader
                if elist: inTree.SetEntryList(elist)
		inTree = InputTree(inTree, elist) 

	    # prepare output file
	    outFileName = os.path.join(self.outputDir, os.path.basename(fname).replace(".root",outpostfix+".root"))
	    outFile = ROOT.TFile.Open(outFileName, "RECREATE", "", compressionLevel)
	    outFileNames.append(outFileName)
	    if compressionLevel: outFile.SetCompressionAlgorithm(compressionAlgo)

	    # prepare output tree
	    if self.friend:
		outTree = FriendOutput(inFile, inTree, outFile)
	    else:
		outTree = FullOutput(inFile, inTree, outFile, branchSelection = self.branchsel, fullClone = fullClone, jsonFilter = jsonFilter,provenance=self.provenance)

	    # process events, if needed
	    if not fullClone:
		(nall, npass, timeLoop) = eventLoop(self.modules, inFile, outFile, inTree, outTree)
		print 'Processed %d preselected entries from %s (%s entries). Finally selected %d entries' % (nall, fname, inTree.GetEntries(), npass)
	    else:
		print 'Selected %d entries from %s' % (outTree.tree().GetEntries(), fname)

	    # now write the output
            if not self.noOut: 
                outTree.write()
	    outFile.Close()
	    print "Done %s" % outFileName
            if fetchedfile and os.path.exists(fetchedfile):
                print 'Cleaning up: removing %s'%fetchedfile
                os.system("rm %s"%fetchedfile)

	    if self.jobReport:
		self.jobReport.addInputFile(fname,nall)

	for m in self.modules: m.endJob()
	
	print  totEntriesRead/(time.clock()-t0), "Hz"


	if self.haddFileName :
		os.system("./haddnano.py %s %s" %(self.haddFileName," ".join(outFileNames))) #FIXME: remove "./" once haddnano.py is distributed with cms releases
	if self.jobReport :
		self.jobReport.addOutputFile(self.haddFileName)
		self.jobReport.save()
