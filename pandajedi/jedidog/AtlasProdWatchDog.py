import re
import sys
import traceback

from pandajedi.jedicore import JediCoreUtils
from pandajedi.jedicore.MsgWrapper import MsgWrapper
from WatchDogBase import WatchDogBase
from pandajedi.jediconfig import jedi_config
from pandajedi.jedibrokerage import AtlasBrokerUtils

from pandaserver.dataservice import DataServiceUtils

# logger
from pandacommon.pandalogger.PandaLogger import PandaLogger
logger = PandaLogger().getLogger(__name__.split('.')[-1])



# watchdog for ATLAS production
class AtlasProdWatchDog (WatchDogBase):

    # constructor
    def __init__(self,ddmIF,taskBufferIF):
        WatchDogBase.__init__(self,ddmIF,taskBufferIF)



    # main
    def doAction(self):
        try:
            # get logger
            tmpLog = MsgWrapper(logger)
            tmpLog.debug('start')
            # action for priority boost
            self.doActionForPriorityBoost(tmpLog)
            # action for reassign
            self.doActionForReassgin(tmpLog)
            # action for throttled
            self.doActionForThrottled(tmpLog)
            # action for high prio pending
            for minPriority,timeoutVal in [(950,10),
                                           (900,30),
                                           ]:
                self.doActionForHighPrioPending(tmpLog,minPriority,timeoutVal)
            # action to set scout job data w/o scouts
            self.doActionToSetScoutJobData(tmpLog)
        except:
            errtype,errvalue = sys.exc_info()[:2]
            tmpLog.error('failed with {0}:{1} {2}'.format(errtype.__name__,errvalue,
                                                          traceback.format_exc()))
        # return
        tmpLog.debug('done')
        return self.SC_SUCCEEDED
    


    # action for priority boost
    def doActionForPriorityBoost(self,gTmpLog):
        # get work queue mapper
        workQueueMapper = self.taskBufferIF.getWorkQueueMap()
        # get list of work queues
        workQueueList = workQueueMapper.getQueueListWithVoType(self.vo,self.prodSourceLabel)
        # loop over all work queues
        for workQueue in workQueueList:
            gTmpLog.debug('start workQueue={0}'.format(workQueue.queue_name))
            # get tasks to be boosted
            taskVarList = self.taskBufferIF.getTasksWithCriteria_JEDI(self.vo,self.prodSourceLabel,['running'],
                                                                      taskCriteria={'workQueue_ID':workQueue.queue_id},
                                                                      datasetCriteria={'masterID':None,'type':['input','pseudo_input']},
                                                                      taskParamList=['jediTaskID','taskPriority','currentPriority'],
                                                                      datasetParamList=['nFiles','nFilesUsed','nFilesTobeUsed',
                                                                                        'nFilesFinished','nFilesFailed'])
            boostedPrio = 900
            toBoostRatio = 0.95 
            for taskParam,datasetParam in taskVarList:
                jediTaskID = taskParam['jediTaskID']
                taskPriority = taskParam['taskPriority']
                currentPriority = taskParam['currentPriority']
                # high enough
                if currentPriority >= boostedPrio:
                    continue
                nFiles = datasetParam['nFiles']
                nFilesFinished = datasetParam['nFilesFinished']
                nFilesFailed = datasetParam['nFilesFailed']
                gTmpLog.info('jediTaskID={0} nFiles={1} nFilesFinishedFailed={2}'.format(jediTaskID,nFiles,nFilesFinished+nFilesFailed))
                try:
                    if float(nFilesFinished+nFilesFailed) / float(nFiles) >= toBoostRatio:
                        gTmpLog.info('>>> boost jediTaskID={0}'.format(jediTaskID))
                        self.taskBufferIF. changeTaskPriorityPanda(jediTaskID,boostedPrio)
                except:
                    pass


        
    # action for reassignment
    def doActionForReassgin(self,gTmpLog):
        # get DDM I/F
        ddmIF = self.ddmIF.getInterface(self.vo)
        # get site mapper
        siteMapper = self.taskBufferIF.getSiteMapper()
        # get tasks to get reassigned
        taskList = self.taskBufferIF.getTasksToReassign_JEDI(self.vo,self.prodSourceLabel)
        gTmpLog.debug('got {0} tasks to reassign'.format(len(taskList)))
        for taskSpec in taskList:
            tmpLog = MsgWrapper(logger,'<jediTaskID={0}'.format(taskSpec.jediTaskID))
            tmpLog.debug('start to reassign')
            # DDM backend
            ddmBackEnd = taskSpec.getDdmBackEnd()
            # get datasets
            tmpStat,datasetSpecList = self.taskBufferIF.getDatasetsWithJediTaskID_JEDI(taskSpec.jediTaskID,['output','log'])
            if tmpStat != True:
                tmpLog.error('failed to get datasets')
                continue
            # update DB
            if not taskSpec.useWorldCloud():
                # update cloudtasks
                tmpStat = self.taskBufferIF.setCloudTaskByUser('jedi',taskSpec.jediTaskID,taskSpec.cloud,'assigned',True)
                if tmpStat != 'SUCCEEDED':
                    tmpLog.error('failed to update CloudTasks')
                    continue
                # check cloud
                if not siteMapper.checkCloud(taskSpec.cloud):
                    tmpLog.error("cloud={0} doesn't exist".format(taskSpec.cloud))
                    continue
            else:
                # re-run task brokerage
                if taskSpec.nucleus in [None,'']:
                    taskSpec.status = 'assigning'
                    taskSpec.oldStatus = None
                    taskSpec.setToRegisterDatasets()
                    self.taskBufferIF.updateTask_JEDI(taskSpec,{'jediTaskID':taskSpec.jediTaskID},
                                                      setOldModTime=True)
                    tmpLog.debug('set task.status={0} to trigger task brokerage again'.format(taskSpec.status))
                    continue
                # get nucleus
                nucleusSpec = siteMapper.getNucleus(taskSpec.nucleus)
                if nucleusSpec == None:
                    tmpLog.error("nucleus={0} doesn't exist".format(taskSpec.nucleus))
                    continue
                # set nucleus
                retMap = {taskSpec.jediTaskID: AtlasBrokerUtils.getDictToSetNucleus(nucleusSpec,datasetSpecList)}
                tmpRet = self.taskBufferIF.setCloudToTasks_JEDI(retMap)
            # get T1/nucleus
            if not taskSpec.useWorldCloud():
                t1SiteName = siteMapper.getCloud(taskSpec.cloud)['dest']
            else:
                t1SiteName = nucleusSpec.getOnePandaSite()
            t1Site = siteMapper.getSite(t1SiteName)
            # loop over all datasets
            isOK = True
            for datasetSpec in datasetSpecList:
                tmpLog.debug('dataset={0}'.format(datasetSpec.datasetName))
                if DataServiceUtils.getDistributedDestination(datasetSpec.storageToken) != None:
                    tmpLog.debug('skip {0} is distributed'.format(datasetSpec.datasetName))
                    continue
                # get location
                location = siteMapper.getDdmEndpoint(t1Site.sitename,datasetSpec.storageToken)
                # make subscription
                try:
                    tmpLog.debug('registering subscription to {0} with backend={1}'.format(location,
                                                                                           ddmBackEnd))
                    tmpStat = ddmIF.registerDatasetSubscription(datasetSpec.datasetName,location,
                                                                'Production Output',asynchronous=True)
                    if tmpStat != True:
                        tmpLog.error("failed to make subscription")
                        isOK = False
                        break
                except:
                    errtype,errvalue = sys.exc_info()[:2]
                    tmpLog.warning('failed to make subscription with {0}:{1}'.format(errtype.__name__,errvalue))
                    isOK = False
                    break
            # succeeded
            if isOK:    
                # activate task
                if taskSpec.oldStatus in ['assigning','exhausted',None]:
                    taskSpec.status = 'ready'
                else:
                    taskSpec.status = taskSpec.oldStatus
                taskSpec.oldStatus = None
                self.taskBufferIF.updateTask_JEDI(taskSpec,{'jediTaskID':taskSpec.jediTaskID},
                                                  setOldModTime=True)
                tmpLog.debug('finished to reassign')



    # action for throttled tasks
    def doActionForThrottled(self,gTmpLog):
        # release tasks 
        nTasks = self.taskBufferIF.releaseThrottledTasks_JEDI(self.vo,self.prodSourceLabel)
        gTmpLog.debug('released {0} tasks'.format(nTasks))
        nTasks = self.taskBufferIF.throttleTasks_JEDI(self.vo,self.prodSourceLabel,
                                                      jedi_config.watchdog.waitForThrottled)
        gTmpLog.debug('throttled {0} tasks'.format(nTasks))



    # action for high priority pending tasks
    def doActionForHighPrioPending(self,gTmpLog,minPriority,timeoutVal):
        timeoutForPending = None
        if hasattr(jedi_config.watchdog,'timeoutForPendingVoLabel'):
            timeoutForPending = JediCoreUtils.getConfigParam(jedi_config.watchdog.timeoutForPendingVoLabel,self.vo,self.prodSourceLabel)
        if timeoutForPending == None:
            timeoutForPending = jedi_config.watchdog.timeoutForPending
        timeoutForPending = int(timeoutForPending)
        tmpRet = self.taskBufferIF.reactivatePendingTasks_JEDI(self.vo,self.prodSourceLabel,
                                                               timeoutVal,timeoutForPending,
                                                               minPriority=minPriority)
        if tmpRet == None:
            # failed                                                                                                             
            gTmpLog.error('failed to reactivate high priority (>{0}) tasks'.format(minPriority))
        else:
            gTmpLog.info('reactivated high priority (>{0}) {1} tasks'.format(minPriority,tmpRet))



    # action to set scout job data w/o scouts
    def doActionToSetScoutJobData(self,gTmpLog):
        tmpRet = self.taskBufferIF.setScoutJobDataToTasks_JEDI(self.vo,self.prodSourceLabel)
        if tmpRet == None:
            # failed                                                                                                             
            gTmpLog.error('failed to set scout job data')
        else:
            gTmpLog.info('set scout job data successfully')
