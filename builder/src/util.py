import os
import errno
import sys
import subprocess
import shutil
import platform
import traceback


class Util:
    '''
    X platform utils
    '''
    
    def __init__(self):
        '''
        '''
    def copy(self, src, dest):
        try:
            shutil.copy(src, dest)
        except Exception as e:
            print traceback.format_exc()
            pass

    def move(self, src, dest):
        try:
            shutil.move(src, dest)
        except Exception as e:
            print traceback.format_exc()
            pass

    def removeFile(self, name):
        if os.path.exists(name):
            try:
                if os.path.isdir(name):
                    if os.path.islink(name):
                        os.remove(name)
                    else:
                        shutil.rmtree(name)
                else:             
                    os.remove(name)                
            except Exception as e:
                print traceback.format_exc()
                pass

    def makeFullPath(self, pathname):        
        '''
        Make a path - any depth - ignore existance
        '''
        try:
            os.makedirs(pathname)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(pathname):
                pass
        except Exception as ex:
                print >> sys.stderr, 'ERROR: makeFullPath exception number : %d, description: %s, path %s' % \
                     (ex.errno, ex.strerror, pathname)
                pass
        
    def runOSCommand(self, cmd):
        '''
        Run os task to completion check return but ignore output.
        '''
        retcode = 0
        try:
            retcode = subprocess.call(cmd, shell=True)
            if retcode != 0:
                print >> sys.stderr, 'WARNING: runOSCommand returned: %d, command %s' % \
                    (retcode, cmd)
                return
    
        except Exception as e:
            print >> sys.stderr, 'ERROR: runOSCommand exception number : %d, retcode %d, description: %s, command %s' % \
                (e.errno, retcode, e.strerror, cmd)
            pass

    def execOSCommand(self, cmd):
        '''
        Run os task to completion check return but ignore output.
        '''
        retlines = []
        try:
            retlines = subprocess.Popen(cmd,
                        shell=True,
                        stdout=subprocess.PIPE).stdout.readlines()
    
        except Exception as e:
            print >> sys.stderr, 'ERROR: execOSCommand exception number : %d, retcode %s, description: %s, command %s' % \
                (e.errno, retlines[0], e.strerror, cmd)
            pass
        return retlines
      
    def listFilesMatchingSuffix(self, directory, pattern):
        tmp = []
        ret = []        
        try:
            tmp = os.listdir(directory)
            for f in tmp:
                if f.endswith(pattern):
                    ret.append(os.path.join(directory, f))
        except Exception as e:
            print traceback.format_exc()
            pass

        return ret

    def linuxDistribution(self):
        try:
            return platform.linux_distribution()
        except:
            return "N/A"
        
        
    def get_size(self, start_path = '.'):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(start_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                total_size += os.path.getsize(fp)
        return total_size   
# util END.    