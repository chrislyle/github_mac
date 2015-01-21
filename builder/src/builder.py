#!/usr/bin/env python
# encoding: utf-8
'''
-- builder.py - build ivnt (initially on the mac)

builds ivnt for development or release purposes.

@author:     chris.lyle

@copyright:  2014 aria-networks limited. All rights reserved.

@license:    python

@contact:    chris.lyle@aria-networks.com
@deffield    updated: 2014-08-06
'''

import sys
import os
import re
import shutil
import platform
import subprocess
import multiprocessing
import traceback

from optparse import OptionParser
from xml.dom import minidom

from macosx import MacOSX
from util import Util

__all__ = []
__version__ = 0.1
__date__ = '2014-08-06'
__updated__ = '2014-08-06'

MSVC_AMD64_VARS = "C:\\Program Files (x86)\\Microsoft Visual Studio 9.0\\VC\\bin\\amd64\\vcvarsamd64.bat"

class Builder:

    def __init__(self, root, debug):
        self.root = root
        self.debug = debug
        self.util = Util()

        self.stage = os.path.join(self.root, 'Stage')
        self.dist = os.path.join(self.root, 'Distribution')

        self.bindir = os.path.join(self.root, 'bin')
        if self.debug:
            self.bindir = os.path.join(self.root, 'bind')

        self.build_version = self.getVersion()
        self.mac = MacOSX(root, self.bindir, self.build_version)
        
        

    def importDependencies(self, depsfile):
        '''
        Get dependency info and create / run svn stmts
        for each one.
        '''
        xmldoc = minidom.parse(depsfile)
        roots = xmldoc.getElementsByTagName('externals')

        for r in roots :
            svn_url = r.attributes['root'].value
            items = r.getElementsByTagName('external')
            for i in items:
                src = i.attributes['source'].value
                dest = i.attributes['dest'].value
                revision = i.attributes['revision'].value
                destfull = os.path.join(self.root, 'deps', dest)
                sCmd = "svn export %s/%s@%s --username software.build --password build %s" % (svn_url, src, revision, destfull)
                self.util.runOSCommand(sCmd)

    def getExternals(self):
        externalsFile = os.path.join(self.root, 'deps', 'linux64.xml')
        if platform.system() == "Windows":
            if platform.machine() == "AMD64":
                externalsFile = os.path.join(self.root, 'deps', 'win64.xml')
            else:
                externalsFile = os.path.join(self.root, 'deps', 'win32.xml')
        elif platform.system() == "Darwin":
            externalsFile = os.path.join(self.root, 'deps', 'macx64.xml')
        elif platform.system() == "Linux":
            externalsFile = os.path.join(self.root, 'deps', 'linux64.xml')

        self.importDependencies(externalsFile)


    def getVersion(self):
        self.major_version = 1
        self.minor_version = 0
        self.revision = 1
        self.svn_revision = 0

        ivnt_header_file = os.path.join(self.root, 'ivnt', 'ivnt-mplste', 'ivnt_version.h')
        try:
            f = open(ivnt_header_file, "r")
        except:
            print traceback.format_exc()
            return

        for l in f.readlines():
            m = re.match(r'^#define IVNT_MAJOR_NUMBER "(\S+)"$', l)
            if m:
                self.major_version = m.group(1)
                continue
            m = re.match(r'^#define IVNT_MINOR_NUMBER "(\S+)"$', l)
            if m:
                self.minor_version = m.group(1)
                continue
            m = re.match(r'^#define IVNT_REVISION_NUMBER "(\S+)"$', l)
            if m:
                self.revision = m.group(1)
                continue

        f.close()

        svn_info = subprocess.Popen("svn info " + self.root,
                        shell=True,
                        stdout=subprocess.PIPE).stdout.readlines()

        for ln in svn_info:
            m = re.match(r'^Revision: (\S+)$', ln)
            if m:
                self.svn_revision = m.group(1)
                break

        ret_version = '%s.%s.%s.%s' % (self.major_version, self.minor_version,
                                   self.revision, self.svn_revision)
        return ret_version


    def writeKickStart(self):
        '''
        Added setup_mac.sh
        '''
        if platform.system() == "Windows":
            sCmd = 'cd %s && call setup.cmd' % os.path.join(self.root, 'deps')
        elif platform.system() == "Darwin":
            sCmd = 'cd %s && ./setup_mac.sh' % os.path.join(self.root, 'deps')
        else:
            sCmd = 'cd %s && ./setup.sh' % os.path.join(self.root, 'deps')

        self.util.runOSCommand(sCmd)


    def runMake(self):
        '''
        Multi platform make.
        '''
        self.cpuCount = multiprocessing.cpu_count() * 2
        sCmd = ""
        if platform.system() == "Windows" and platform.machine() == "AMD64":
            sCmd = 'cd %s && call "%s" && %s /J %d' % (self.root,
                           MSVC_AMD64_VARS,
                           os.path.join(self.root, 'deps', 'jom', 'jom.exe'),
                           self.cpuCount)
        else:
            sCmd = "cd %s && make -j%d | grep -i error:" % (self.root, self.cpuCount)

        self.util.runOSCommand(sCmd)


    def runQmake(self):
        '''
        Bearing in mind that we do not use the deps method for osx - yet...
        '''
        self.removeMakefiles()

        if platform.system() == "Windows" or platform.system() == "Linux":
            qmakeCmd = os.path.join('deps', 'qt', 'bin', 'qmake')
            qmakeSpec = os.path.join('deps', 'qt', 'mkspecs', 'default')
        elif platform.system() == "Darwin":
            qmakeCmd = 'qmake'
            qmakeSpec = 'macx-llvm'

        proFile = os.path.join(self.root, 'ivnt.pro')

        if self.debug:
            sCmd = 'cd %s && %s -r -spec %s "CONFIG+=debug" "DEFINES+=PRODUCT_VERSION="%s"" %s' % (self.root,
                qmakeCmd,
                qmakeSpec,
                self.build_version,
                proFile)
        else:
            sCmd = 'cd %s && %s -r -spec %s "CONFIG+=release" "DEFINES+=PRODUCT_VERSION="%s"" %s' % (self.root,
                qmakeCmd,
                qmakeSpec,
                self.build_version,
                proFile)

        self.util.runOSCommand(sCmd)


    def removeMakefiles(self):
        '''
        Duplicating existing functionality X platform
        '''
        for (dirpath, dirs, files) in os.walk(self.root):
            for filename in files:
                if filename.endswith('Makefile') or \
                filename.endswith('Makefile.Release') or \
                filename.endswith('Makefile.Debug'):
                    os.remove(os.path.join(dirpath, filename))


    def getManifestList(self):
        '''
        get list of all manifests, return a dict
        '''
        man_list = {}
        for (dirpath, dirs, files) in os.walk(os.path.join(self.root, 'ivnt', 'customers')):
            for filename in files:
                if filename.endswith('.manifest'):
                    name = filename.replace('.manifest', ' ').strip()
                    man_list[name] = os.path.join(dirpath, filename)
        return man_list        


    def getProcessorInfo(self):
        '''
        May be useful
        '''
        info = ""
        if platform.system() == "Windows":
            info = platform.processor()
        elif platform.system() == "Darwin":
            info = subprocess.check_output(['/usr/sbin/sysctl', "-n", "machdep.cpu.brand_string"]).strip()
        elif platform.system() == "Linux":
            command = "cat /proc/cpuinfo"
            info = subprocess.check_output(command, shell=True).strip()
        return info


def main(argv=None):
    
    _util = Util()
        
    program_name = os.path.basename(sys.argv[0])
    program_version = "1.0.1"
    program_build_date = "%s" % __updated__

    program_version_string = '%%prog %s (%s)' % (program_version, program_build_date)
    program_usage = '''usage: %prog [options] build_root'''
    program_longdesc = '''Generic build for ivnt for Windows, Linux and OSX, can be used in jenkins -j option'''
    program_license = "Copyright (c) 2014 chris.lyle [aria-networks limited]"

    if argv is None:
        argv = sys.argv[1:]

    try:
        # setup option parser
        parser = OptionParser(version=program_version_string,
                              epilog=program_longdesc,
                              description=program_license,
                              usage=program_usage)

        parser.set_defaults(revision='HEAD', svn_url='https://synapse.aria-networks.com/svn/aria/source/ivnt/trunk')

        parser.add_option("-d", "--debug", action="store_true", dest="debug_build",
                          default=False, help="build debug version")
        parser.add_option("-c", "--clear", action="store_true", dest="clear_root",
                          default=False, help="remove destination first - if used will check out fresh copy")
        parser.add_option("-b", "--distribute-only", action="store_true", dest="distribute_only",
                          default=False, help="just distribute, does not build, signs and packages")


        parser.add_option("-r", "--revision", dest="revision", help="set svn revision [default: %default]")
        parser.add_option("-u", "--svn_url", dest="svn_url", help="set svn URL [default: %default]")


        parser.add_option("-j", "--jenkins_mode", action="store_true", dest="jenkins_mode",
                          default=False, help="just get the externals and build (run from jenkins) all other optional flags are ignored")

        # process options
        (opts, args) = parser.parse_args(argv)

        if not opts.jenkins_mode and len(args) != 1:
            parser.print_usage()
            return -1

        svnRevision = opts.revision
        clearRoot = opts.clear_root
        debug_build = opts.debug_build
        svnURL = opts.svn_url
        jenkinsMode = opts.jenkins_mode
        distribute_only = opts.distribute_only

        if jenkinsMode:
            rootDir = os.getcwd()
        else:
            rootDir = args[0]


        print "Build root is [%s]" % rootDir

        if not (jenkinsMode and distribute_only):
            if clearRoot:
                shutil.rmtree(rootDir, ignore_errors=True)
                svnCommand = 'svn co %s@%s %s' % (svnURL, svnRevision, rootDir)
            else:
                svnCommand = 'svn up %s' % (rootDir)

            _util.runOSCommand(svnCommand)

        _builder = Builder(rootDir, debug_build)

        if not distribute_only:
            if jenkinsMode or clearRoot:
                _builder.getExternals()

            _builder.depsdir = os.path.join(_builder.root, 'deps')
            _builder.writeKickStart()
            _builder.runQmake()
            _builder.runMake()
        
            if platform.system() == "Darwin":
                mlist = _builder.getManifestList()
                _builder.mac.prepareQt()         
                
                _util.removeFile(os.path.join(_builder.root, 'Stage'))
                _util.removeFile(os.path.join(_builder.root, 'Distribution'))

                # build the various manifests
                for mname in mlist.keys():
                    print "PROCESSING MANIFEST: " + mname 
                    print "PATH: " + mlist[mname]
                    _builder.mac.prepareStagingDirectory(mname, mlist[mname])

        if platform.system() == "Darwin":
            # flexible way to install any part of ivnt
            #_builder.mac.createDMGInstaller(os.path.join(_builder.root, 'Distribution'))
            _builder.mac.createEverythingBundles()


    except Exception as e:
        print traceback.format_exc()
        return 2

if __name__ == "__main__":
    sys.exit(main())

# builder END.
