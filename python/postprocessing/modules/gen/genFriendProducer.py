import ROOT
ROOT.PyConfig.IgnoreCommandLineOptions = True

from PhysicsTools.NanoAODTools.postprocessing.framework.datamodel import Collection 
from PhysicsTools.NanoAODTools.postprocessing.framework.eventloop import Module

class genFriendProducer(Module):
    def __init__(self):
        self.vars = ("pt","eta","phi","mass","pdgId")
    def beginJob(self):
        pass
    def endJob(self):
        pass
    def beginFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        self.out = wrappedOutputTree
        self.out.branch("nGenTop" , "I")
        self.out.branch("nGenFwdQ" , "I")
        for V in self.vars:
            self.out.branch("GenTop_"+V,  "F", lenVar="nGenTop")
            self.out.branch("GenFwdQ_"+V, "F", lenVar="nGenFwdQ")
    def endFile(self, inputFile, outputFile, inputTree, wrappedOutputTree):
        pass

    def getGenTops(self):
        tops = []
        for p in self.genParts:
            if abs(p.pdgId)!=6 : continue
            ## bit 7 is p.isHardProcess
            if (p.statusFlags>>7)&1 != 1: continue
            top = ROOT.TLorentzVector()
            top.SetPtEtaPhiM(p.pt, p.eta, p.phi, p.mass if p.mass >= 0. else 0.)
            tops.append( [top, p.pdgId] )
            break ## take the first ?
        tops.sort(key = lambda x: x[0].Pt(), reverse=True )
        return tops

    def getOutgoingQuark(self):
        fwdqs = []
        for p in self.genParts:
            if abs(p.pdgId)>5 : continue
            ## bit 7 is p.isHardProcess
            if (p.statusFlags>>7)&1 != 1: continue
            ## status 23 is outgoing particle
            if (p.status)!=23: continue
            fwdq = ROOT.TLorentzVector()
            fwdq.SetPtEtaPhiM(p.pt, p.eta, p.phi, p.mass if p.mass >= 0. else 0.)
            fwdqs.append( [fwdq, p.pdgId] )
            break ## take the first?
        fwdqs.sort(key = lambda x: x[0].Pt(), reverse=True )
        return fwdqs

    def analyze(self, event):
        """process event, return True (go to next module) or False (fail, go to next event)"""
        self.genParts = Collection(event, "GenPart")

        ## GEN tops
        genTopCollection = self.getGenTops()
        if len(genTopCollection):
            self.out.fillBranch("nGenTop", len(genTopCollection))
            retT={}
            retT["pt"]    = [ top[0].Pt()  for top in genTopCollection ]
            retT["eta"]   = [ top[0].Eta() for top in genTopCollection ]
            retT["phi"]   = [ top[0].Phi() for top in genTopCollection ]
            retT["pdgId"] = [ top[1]       for top in genTopCollection ]
            retT["mass"]  = [ top[0].M() if top[0].M() >= 0. else 0. for top in genTopCollection ]
            for V in self.vars:
                self.out.fillBranch("GenTop_"+V, retT[V])

        ## GEN outgoing particles
        genFwdQCollection = self.getOutgoingQuark()
        if len(genFwdQCollection):
            self.out.fillBranch("nGenFwdQ", len(genFwdQCollection))
            retT={}
            retT["pt"]    = [ top[0].Pt()  for top in genFwdQCollection ]
            retT["eta"]   = [ top[0].Eta() for top in genFwdQCollection ]
            retT["phi"]   = [ top[0].Phi() for top in genFwdQCollection ]
            retT["pdgId"] = [ top[1]       for top in genFwdQCollection ]
            retT["mass"]  = [ top[0].M() if top[0].M() >= 0. else 0. for top in genFwdQCollection ]
            for V in self.vars:
                self.out.fillBranch("GenFwdQ_"+V, retT[V])
        
            
        return True


# define modules using the syntax 'name = lambda : constructor' to avoid having them loaded when not needed

genFriends = lambda : genFriendProducer() 
 
