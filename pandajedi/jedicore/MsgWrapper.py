import re
import time
import datetime
from pandajedi.jediconfig import jedi_config
from pandaserver.userinterface import Client
from pandacommon.pandalogger.PandaLogger import PandaLogger


class MsgWrapper:

    def __init__(self,logger,token=None,lineLimit=500,monToken=None):
        self.logger = logger
        # use timestamp as token if undefined
        if token == None:
            self.token = "<{0}>".format(datetime.datetime.utcnow().isoformat('/'))
        else:
            self.token = token
        # token for http logger
        if monToken == None:
            self.monToken = self.token
        else:
            self.monToken = monToken
        # remove <> for django
        try:
            self.monToken = re.sub('<(?P<name>[^>]+)>','\g<name>',self.monToken)
        except:
            pass
        # message buffer
        self.msgBuffer = []
        self.lineLimit = lineLimit


    def keepMsg(self,msg):
        # keep max message depth
        if len(self.msgBuffer) > self.lineLimit:
            self.msgBuffer.pop(0)
        timeNow = datetime.datetime.utcnow()
        self.msgBuffer.append('{0} : {1}'.format(timeNow.isoformat(' '),msg))


    def info(self,msg):
        msg = str(msg)
        self.logger.info(self.token + ' ' + msg)
        self.keepMsg(msg)


    def debug(self,msg):
        msg = str(msg)
        self.logger.debug(self.token + ' ' + msg)
        self.keepMsg(msg)


    def error(self,msg):
        msg = str(msg)
        self.logger.error(self.token + ' ' + msg)
        self.keepMsg(msg)


    def warning(self,msg):
        msg = str(msg)
        self.logger.warning(self.token + ' ' + msg)
        self.keepMsg(msg)


    def dumpToString(self):
        strMsg = ''
        for msg in self.msgBuffer:
            strMsg += msg
            strMsg += "\n"
        return strMsg


    def uploadLog(self,id):
        strMsg = self.dumpToString()
        s,o = Client.uploadLog(strMsg,id)
        if s != 0:
            return "failed to upload log with {0}.".format(s)
        if o.startswith('http'):
            return '<a href="{0}">log</a>'.format(o)
        return o


    # send message to logger
    def sendMsg(self,message,msgType,msgLevel='info',escapeChar=False):
        try:
            # get logger
            tmpPandaLogger = PandaLogger()
            # lock HTTP handler
            tmpPandaLogger.lock()
            tmpPandaLogger.setParams({'Type':msgType})
            # get logger
            tmpLogger = tmpPandaLogger.getHttpLogger(jedi_config.master.loggername)
            # escape special characters
            if escapeChar:
                message = message.replace('<','&lt;')
                message = message.replace('>','&gt;')
            # add message
            message = self.monToken + ' ' + message
            if msgLevel=='error':
                tmpLogger.error(message)
            elif msgLevel=='warning':
                tmpLogger.warning(message)
            elif msgLevel=='info':
                tmpLogger.info(message)
            else:
                tmpLogger.debug(message)                
            # release HTTP handler
            tmpPandaLogger.release()
        except:
            pass



    # bulk send messages to logger
    def bulkSendMsg(self,msgType,msgLevel='info',loggerName=None):
        try:
            nChunk = 20
            if loggerName == None:
                loggerName = jedi_config.master.loggername
            for iMsg,message in enumerate(self.msgBuffer):
                # get logger
                tmpPandaLogger = PandaLogger()
                # lock HTTP handler
                tmpPandaLogger.lock()
                tmpPandaLogger.setParams({'Type':msgType})
                # get logger
                tmpLogger = tmpPandaLogger.getHttpLogger(loggerName)
                # add message
                message = self.monToken + ' ' + message
                if msgLevel=='error':
                    tmpLogger.error(message)
                elif msgLevel=='warning':
                    tmpLogger.warning(message)
                elif msgLevel=='info':
                    tmpLogger.info(message)
                else:
                    tmpLogger.debug(message)                
                # release HTTP handler
                tmpPandaLogger.release()
                if (iMsg+1) % nChunk == 0:
                    time.sleep(1)
        except:
            pass
