import re


"""
task specification for JEDI

"""
class JediTaskSpec(object):
    # attributes
    attributes = (
        'jediTaskID','taskName','status','userName',
        'creationDate','modificationTime','startTime','endTime',
        'frozenTime','prodSourceLabel','workingGroup','vo','coreCount',
        'taskType','processingType','taskPriority','currentPriority',
        'architecture','transUses','transHome','transPath','lockedBy',
        'lockedTime','termCondition','splitRule','walltime','walltimeUnit',
        'outDiskCount','outDiskUnit','workDiskCount','workDiskUnit',
        'ramCount','ramUnit','ioIntensity','ioIntensityUnit',
        'workQueue_ID','progress','failureRate','errorDialog',
        'reqID','oldStatus','cloud','site','countryGroup'
        )
    # attributes which have 0 by default
    _zeroAttrs = ()
    # attributes to force update
    _forceUpdateAttrs = ('lockedBy','lockedTime')
    # mapping between sequence and attr
    _seqAttrMap = {}
    # limit length
    _limitLength = {'errorDialog' : 255}
    # tokens for split rule
    splitRuleToken = {
        'allowEmptyInput'    : 'AE',
        'disableAutoRetry'   : 'DR',
        'nEventsPerWorker'   : 'ES',
        'firstEvent'         : 'FT',
        'groupBoundaryID'    : 'GB',
        'instantiateTmplSite': 'IA',
        'instantiateTmpl'    : 'IT',
        'useLocalIO'         : 'LI',
        'limitedSites'       : 'LS',
        'loadXML'            : 'LX',
        'nMaxFilesPerJob'    : 'MF',
        'nEventsPerJob'      : 'NE',
        'nFilesPerJob'       : 'NF',
        'nGBPerJob'          : 'NG',
        'pfnList'            : 'PL',
        'randomSeed'         : 'RS',
        'useBuild'           : 'UB',
        'usePrePro'          : 'UP',
        'mergeOutput'        : 'MO',
        }
    # enum for preprocessing
    enum_toPreProcess = '1'
    enum_preProcessed = '2'
    # enum for limited sites
    enum_limitedSites = {'1' : 'inc',
                         '2' : 'exc',
                         '3' : 'incexc'}



    # constructor
    def __init__(self):
        # install attributes
        for attr in self.attributes:
            if attr in self._zeroAttrs:
                object.__setattr__(self,attr,0)
            else:
                object.__setattr__(self,attr,None)
        # map of changed attributes
        object.__setattr__(self,'_changedAttrs',{})
        # template to generate job parameters
        object.__setattr__(self,'jobParamsTemplate','')
        # associated datasets
        object.__setattr__(self,'datasetSpecList',[])


    # override __setattr__ to collecte the changed attributes
    def __setattr__(self,name,value):
        oldVal = getattr(self,name)
        object.__setattr__(self,name,value)
        newVal = getattr(self,name)
        # collect changed attributes
        if oldVal != newVal or name in self._forceUpdateAttrs:
            self._changedAttrs[name] = value


    # copy old attributes
    def copyAttributes(self,oldTaskSpec):
        for attr in self.attributes + ('jobParamsTemplate',):
            if 'Time' in attr:
                continue
            if 'Date' in attr:
                continue
            if attr in ['progress','failureRate','errorDialog',
                        'status','oldStatus','lockedBy']:
                continue
            self.__setattr__(attr,getattr(oldTaskSpec,attr))
            
        
    # reset changed attribute list
    def resetChangedList(self):
        object.__setattr__(self,'_changedAttrs',{})


    # reset changed attribute
    def resetChangedAttr(self,name):
        try:
            del self._changedAttrs[name]
        except:
            pass


    # force update
    def forceUpdate(self,name):
        if name in self.attributes:
            self._changedAttrs[name] = getattr(self,name)
        
    
    # return map of values
    def valuesMap(self,useSeq=False,onlyChanged=False):
        ret = {}
        for attr in self.attributes:
            # use sequence
            if useSeq and self._seqAttrMap.has_key(attr):
                continue
            # only changed attributes
            if onlyChanged:
                if not self._changedAttrs.has_key(attr):
                    continue
            val = getattr(self,attr)
            if val == None:
                if attr in self._zeroAttrs:
                    val = 0
                else:
                    val = None
            # truncate too long values
            if self._limitLength.has_key(attr):
                if val != None:
                    val = val[:self._limitLength[attr]]
            ret[':%s' % attr] = val
        return ret


    # pack tuple into TaskSpec
    def pack(self,values):
        for i in range(len(self.attributes)):
            attr= self.attributes[i]
            val = values[i]
            object.__setattr__(self,attr,val)


    # return column names for INSERT
    def columnNames(cls,prefix=None):
        ret = ""
        for attr in cls.attributes:
            if prefix != None:
                ret += '{0}.'.format(prefix)
            ret += '{0},'.format(attr)
        ret = ret[:-1]
        return ret
    columnNames = classmethod(columnNames)


    # return expression of bind variables for INSERT
    def bindValuesExpression(cls,useSeq=True):
        ret = "VALUES("
        for attr in cls.attributes:
            if useSeq and cls._seqAttrMap.has_key(attr):
                ret += "%s," % cls._seqAttrMap[attr]
            else:
                ret += ":%s," % attr
        ret = ret[:-1]
        ret += ")"            
        return ret
    bindValuesExpression = classmethod(bindValuesExpression)

    
    # return an expression of bind variables for UPDATE to update only changed attributes
    def bindUpdateChangesExpression(self):
        ret = ""
        for attr in self.attributes:
            if self._changedAttrs.has_key(attr):
                ret += '%s=:%s,' % (attr,attr)
        ret  = ret[:-1]
        ret += ' '
        return ret



    # get the max size per job if defined
    def getMaxSizePerJob(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['nGBPerJob']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                nGBPerJob = int(tmpMatch.group(1)) * 1024 * 1024 * 1024
                return nGBPerJob
        return None    



    # get the maxnumber of files per job if defined
    def getMaxNumFilesPerJob(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['nMaxFilesPerJob']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return int(tmpMatch.group(1))
        return None    




    # get the number of files per job if defined
    def getNumFilesPerJob(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['nFilesPerJob']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return int(tmpMatch.group(1))
        return None    
        


    # get the number of events per job if defined
    def getNumEventsPerJob(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['nEventsPerJob']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return int(tmpMatch.group(1))
        return None    
        


    # get offset for random seed
    def getRndmSeedOffset(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['randomSeed']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return int(tmpMatch.group(1))
        return 0



    # get offset for first event
    def getFirstEventOffset(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['firstEvent']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return int(tmpMatch.group(1))
        return 0



    # grouping with boundaryID
    def useGroupWithBoundaryID(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['groupBoundaryID']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                gbID = int(tmpMatch.group(1))
                # 1 : input - can split,    output - free
                # 2 : input - can split,    output - mapped with provenanceID
                # 3 : input - cannot split, output - free
                # 4 : input - cannot split, output - mapped with provenanceID
                #
                # * rule for master
                # 1 : can split. one boundayID per sub chunk
                # 2 : cannot split. one boundayID per sub chunk
                # 3 : cannot split. multiple boundayIDs per sub chunk
                #
                # * rule for secodary
                # 1 : must have same boundayID. cannot split 
                #
                retMap = {}
                if gbID in [1,2]:
                    retMap['inSplit'] = 1
                else:
                    retMap['inSplit'] = 2
                if gbID in [1,3]:
                    retMap['outMap'] = False
                else:
                    retMap['outMap'] = True
                retMap['secSplit'] = None
                return retMap
        return None



    # use build 
    def useBuild(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['useBuild']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # use only limited sites
    def useLimitedSites(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['limitedSites']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # set limited sites
    def setLimitedSites(self,policy):
        tag = None
        for tmpIdx,tmpPolicy in self.enum_limitedSites.iteritems():
            if policy == tmpPolicy:
                tag = tmpIdx
                break
        # not found
        if tag == None:
            return
        # set
        if self.splitRule == None:
            # new
            self.splitRule = self.splitRuleToken['limitedSites']+'='+tag
        else:
            # append
            self.splitRule += ','+self.splitRuleToken['limitedSites']+'='+tag



    # use local IO
    def useLocalIO(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['useLocalIO']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # use Event Service
    def useEventService(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['nEventsPerWorker']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # get the number of events per worker for Event Service
    def getNumEventsPerWorker(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['nEventsPerWorker']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return int(tmpMatch.group(1))
        return None    



    # disable automatic retry
    def disableAutoRetry(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['disableAutoRetry']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # allow empty input
    def allowEmptyInput(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['allowEmptyInput']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # use PFN list
    def useListPFN(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['pfnList']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # set preprocessing
    def setPrePro(self):
        if self.splitRule == None:
            # new
            self.splitRule = self.splitRuleToken['usePrePro']+'='+self.enum_toPreProcess
        else:
            # append
            self.splitRule += ','+self.splitRuleToken['usePrePro']+'='+self.enum_toPreProcess



    # use preprocessing
    def usePrePro(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['usePrePro']+'=(\d+)',self.splitRule)
            if tmpMatch != None and tmpMatch.group(1) == self.enum_toPreProcess:
                return True
        return False



    # set preprocessed
    def setPreProcessed(self):
        if self.splitRule == None:
            # new
            self.splitRule = self.splitRuleToken['usePrePro']+'='+self.enum_preProcessed
        else:
            tmpMatch = re.search(self.splitRuleToken['usePrePro']+'=(\d+)',self.splitRule)
            if tmpMatch == None:
                # append
                self.splitRule += ','+self.splitRuleToken['usePrePro']+'='+self.enum_preProcessed
            else:
                # replace
                self.splitRule = re.sub(self.splitRuleToken['usePrePro']+'=(\d+)',
                                        self.splitRuleToken['usePrePro']+'='+self.enum_preProcessed,
                                        self.splitRule)
        return



    # check preprocessed
    def checkPreProcessed(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['usePrePro']+'=(\d+)',self.splitRule)
            if tmpMatch != None and tmpMatch.group(1) == self.enum_preProcessed:
                return True
        return False



    # instantiate template datasets
    def instantiateTmpl(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['instantiateTmpl']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # instantiate template datasets at site
    def instantiateTmplSite(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['instantiateTmplSite']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # merge output
    def mergeOutput(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['mergeOutput']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # use random seed
    def useRandomSeed(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['randomSeed']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False



    # get the size of workDisk in bytes
    def getWorkDiskSize(self):
        tmpSize = self.workDiskCount
        if tmpSize == None:
            return 0
        if self.workDiskUnit == 'GB':
            tmpSize = tmpSize * 1024 * 1024 * 1024
            return tmpSize
        if self.workDiskUnit == 'MB':
            tmpSize = tmpSize * 1024 * 1024
            return tmpSize
        return tmpSize



    # get the size of outDisk in bytes
    def getOutDiskSize(self):
        tmpSize = self.outDiskCount
        if tmpSize == None:
            return 0
        if self.outDiskUnit == 'GB':
            tmpSize = tmpSize * 1024 * 1024 * 1024
            return tmpSize
        if self.outDiskUnit == 'MB':
            tmpSize = tmpSize * 1024 * 1024
            return tmpSize
        return tmpSize



    # return list of status to update contents
    def statusToUpdateContents(cls):
        return ['defined','pending']
    statusToUpdateContents = classmethod(statusToUpdateContents)



    # set task status on hold
    def setOnHold(self):
        # change status
        if self.status in ['ready','running','merging','scouting','defined',
                           'topreprocess','preprocessing']:
            self.oldStatus = self.status
            self.status = 'pending'


    # return list of status to reject external changes
    def statusToRejectExtChange(cls):
        return ['finished','done','prepared','broken','aborted','failed','aborting','finishing']
    statusToRejectExtChange = classmethod(statusToRejectExtChange)



    # return list of status for retry
    def statusToRetry(cls):
        return ['finished','failed']
    statusToRetry = classmethod(statusToRetry)



    # return list of status for incexec
    def statusToIncexec(cls):
        return ['done'] + cls.statusToRetry()
    statusToIncexec = classmethod(statusToIncexec)



    # return list of status for Job Generator
    def statusForJobGenerator(cls):
        return ['ready','running','scouting','topreprocess','preprocessing']
    statusForJobGenerator = classmethod(statusForJobGenerator)



    # return mapping of command and status
    def commandStatusMap(cls):
        return {'kill' : {'doing': 'aborting',
                          'done' : 'aborted'},
                'finish' : {'doing': 'finishing',
                            'done' : 'prepared'},
                'retry' : {'doing': 'toretry',
                           'done' : 'ready'},
                'incexec' : {'doing': 'toincexec',
                           'done' : 'rerefine'},
                }
    commandStatusMap = classmethod(commandStatusMap)



    # set task status to active
    def setInActive(self):
        # change status
        if self.status == 'pending':
            self.status = self.oldStatus
            self.oldStatus = None
            self.errorDialog = None
        # reset error dialog    
        self.setErrDiag(None)
            
            
    # set error dialog
    def setErrDiag(self,diag,append=False):
        # set error dialog
        if append == True and self.errorDialog != None:
            self.errorDialog = "{0} {1}".format(self.errorDialog,diag)
        elif append == None:
            # keep old log
            if self.errorDialog == None:
                self.errorDialog = diag
        else:
            self.errorDialog = diag
        

        
    # use loadXML
    def useLoadXML(self):
        if self.splitRule != None:
            tmpMatch = re.search(self.splitRuleToken['loadXML']+'=(\d+)',self.splitRule)
            if tmpMatch != None:
                return True
        return False
