import sys
import os
import re
import util
import platform
import traceback


class Manifest(object):
    '''
    Processes data for a single ".manifest" file.
    Creates folders and copies files from source tree
    to intermediate staging area.
    
    This is currently only intended for OSX
    '''

    def __init__(self, filename, root_dir, bin_dir):
        self.mkdirList = []
        self.copyList = {}  # dict key = from, value = to
        self.filename = filename
        self.name = os.path.basename(filename).replace('.manifest', '').strip()
        self.root_dir = root_dir
        self.stage = os.path.join(self.root_dir, 'Stage', self.name)
        self.dependency = None
        self.loadFile()
        self.util = util.Util()
        self.util.removeFile(self.stage)
        self.util.makeFullPath(self.stage)
        

    def getFullFilePath(self, relname):
        thisDir = os.path.dirname(self.filename)
        thisDirUp1 = os.path.dirname(thisDir)
        thisDirUp2 = os.path.dirname(thisDirUp1)
        thisDirUp3 = os.path.dirname(thisDirUp2)
        thisDirUp4 = os.path.dirname(thisDirUp3)
        if relname.startswith('../../../..'):
            retval = relname.replace('../../../..', thisDirUp4)
        elif relname.startswith('../../..'):
            retval = relname.replace('../../..', thisDirUp3)
        elif relname.startswith('../..'):
            retval = relname.replace('../..', thisDirUp2)
        elif relname.startswith('..'):
            retval = relname.replace('..', thisDirUp1)
        elif relname.startswith('./'):
            retval = relname.replace('./', thisDir + '/')
        else:
            retval = os.path.join(thisDir, relname)

        ret = retval

        if platform.system() == "Darwin":
            ind = retval.find('.so')
            if ind >= 0:
                ret = retval[0:ind] + '*'  
        
        return ret
        
    def loadFile(self):
        '''
        Loads file and puts filesystem changing functions into datastructures
        to be processed by stageFiles
        '''
        try:
            _file = open(self.filename, 'r')
        except Exception as ex:
            print traceback.format_exc()
            raise

        try:
            for _line in _file:
                line = _line.strip() 
                if line == '' or line.startswith('#'):
                    continue
                fld = line.split(':')
                fldcount = len(fld)
                if fldcount == 3:
                    self.dependency = fld[2]
                    continue
                
                source_file = None
                dest_file = None
                
                dest_file = self.stage
                if fldcount >= 1:
                    source_file = self.getFullFilePath(fld[0])
                if fldcount >= 2:
                    dest_file = os.path.join(self.stage, fld[1])
                    if source_file == None and dest_file != None:                    
                        self.mkdirList.append(dest_file)
                    elif source_file != None and dest_file != None and re.match('.*[/|/\*]+$', dest_file) != None:
                        self.mkdirList.append(dest_file)
                
                if source_file != None:
                    self.copyList[source_file] = dest_file
            _file.close()

        except Exception as ex:
            print traceback.format_exc()
            raise

    def getDependency(self):
        return self.dependency

                
    def printActions(self):
        print "make path: " + self.stage
        for d in self.mkdirList:
            print "make path: " + d
        for s in self.copyList.keys():            
            print "copy: %s to %s" % (s, self.copyList[s])
# manifest END.    