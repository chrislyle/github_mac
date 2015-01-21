'''
Created on 31 Oct 2014

@author: chris
'''

import os
import sys
import platform
from manifest import Manifest
from util import Util
import traceback

class MacOSX(object):
    '''
    classdocs
    '''
    def __init__(self, root, bindir, buildversion):
        self.root = root
        self.util = Util()
        self.build_version = buildversion

        self.qtFrameworks = ['QtCore.framework' 
                     ,'QtGui.framework'
                     ,'QtHelp.framework'
                     ,'QtNetwork.framework' 
                     ,'QtScript.framework' 
                     ,'QtScriptTools.framework'
                     ,'QtSql.framework' 
                     ,'QtWebKit.framework' 
                     ,'QtXml.framework'
                     ,'QtXmlPatterns.framework']
        
        self.bundleList = ['ivnt.app'
                ,'ivnt-server-schedtool.app'
                ,'ivnt-server.app'
                ,'ivnt-agent.app'
                ,'ivntheadless.app'
                ,'licensetool.app'
                ,'regextest.app'
                ,'showsystemid.app'
                ,'testsuite.app']
        
        self.mainBundle = self.bundleList[0]
        
        self.topLevelManifests = ['ivnt-client', 'ivnt-server', 'ivnt-clientinvocationagent']

        self.bindir = bindir
        print "\nInfo: Invoked for Platform %s\n" % platform.system()
        
        self.qtPath = os.path.join(self.root, 'fixed_qt_fwks')
        #self.util.removeFile(self.qtPath)
        self.util.makeFullPath(self.qtPath)

        self.stageRoot = os.path.join(self.root, 'Stage')
        self.distRoot =  os.path.join(self.root, 'Distribution')
        self.util.makeFullPath(self.distRoot)
        self.util.makeFullPath(self.stageRoot)

        self.top_level_app = False
        self.qt_processed = False

    def copy(self, src, dest):
        # need to watch for "*.dylib" as this does not exist
        if os.path.exists(os.path.dirname(src)):
            if src.find(' ') >= 0:
                src = '"' + src + '"'
            if dest.find(' ') >= 0:
                dest = '"' + dest + '"'
            scmd = 'cp -fa %s %s' % (src, dest)
            print "COPY %s %s" % (src, dest)
            self.util.runOSCommand(scmd)
        else:
            print "\tWARNING: copy source file %s does not exist." % src

    def move(self, src, dest):
        if os.path.exists(os.path.dirname(src)):
            if src.find(' ') >= 0:
                src = '"' + src + '"'
            if dest.find(' ') >= 0:
                dest = '"' + dest + '"'    
            scmd = 'mv %s %s' % (src, dest)
            self.util.runOSCommand(scmd)
        else:
            print "\tWARNING: move source file %s does not exist." % src

        
    def symbolicLink(self, base, src, target):
        scmd = 'cd %s && ln -s %s %s' % (base, src, target)
        self.util.runOSCommand(scmd)
    
    def doNameTool(self, pathname, executable):
        if platform.system() == "Darwin":
            prefix = '@executable_path/../Frameworks/'
            lpath = pathname.strip()
            lexe = executable.strip()
            bname = lpath
            if lpath.startswith('/'):
                bname = os.path.basename(lpath)
            scmd = 'cd %s && install_name_tool -change %s %s%s %s' % (self.stagePath, lpath, prefix, bname, lexe)
            #print "\n" + scmd + "\n"
            self.util.runOSCommand(scmd)

    def stageFiles(self):
        for d in self.manifest_data.mkdirList:
            self.util.makeFullPath(d)
        for s in self.manifest_data.copyList.keys():
            print "copy: %s to %s" % (s, self.manifest_data.copyList[s])
            self.copy(s, self.manifest_data.copyList[s])

    def prepareQt(self):
        # just do this once and copy to distribution when needed
        if self.qt_processed == False and platform.system() == "Darwin":
            sCmd = 'macdeployqt %s' % os.path.join(self.bindir, self.mainBundle)
            self.util.runOSCommand(sCmd)
            for fw in self.qtFrameworks:
                self.copy(os.path.join(self.bindir, \
                    self.mainBundle, 'Contents', 'Frameworks', fw), self.qtPath)
                self.fix_QTBUG_32896(self.qtPath, fw)

        self.qt_processed = True
    
    def installQt(self, fw_dir):
        # copy the corrected qt deployment to fw_dir ...Frameworks in
        # the distribution being created
        if platform.system() == "Darwin":
            for fw in self.qtFrameworks:
                if os.path.exists(os.path.join(fw_dir, fw)):
                    self.util.removeFile(os.path.join(fw_dir, fw))
                self.copy(os.path.join(self.qtPath, fw), fw_dir)           

    def createBundle(self):
        '''
        This needs to be done so that the expected bundle format is
        present on the mac Qt has various issues with deployment
        in this version combination.
        '''
        print "Main Application: " + str(self.manifest_data.name)        
        if self.manifest_data.name == "ivnt-client":
            self.installQt(self.stagePath)
            self.copy(os.path.join(self.stagePath, '*.frameworks'), self.frameworks_dir)
            self.fixAssistant()

        self.copy(os.path.join(self.stagePath, '*.dylib'), self.frameworks_dir)
        self.copy(os.path.join(self.stagePath, '*.a'), self.frameworks_dir)
        self.copyExtraFilesToStage()
        self.connectLibsAndExecutables()     
       
        self.copy(os.path.join(self.stagePath, 'menus.xml'), self.macos_dir)
        self.copy(os.path.join(self.stagePath, '__HOME__'), self.resources_dir)
        
        self.copy(os.path.join(self.stagePath, 'StandardDemo'), self.macos_dir)
        self.copy(os.path.join(self.stagePath, 'SystemScripts'), self.macos_dir)
        self.copy(os.path.join(self.stagePath, 'metadata'), self.macos_dir)
        self.copy(os.path.join(self.root, 'ivnt/ivnt-mplste/resources/aria-logo.icns'), self.resources_dir)
        self.copy(os.path.join(self.root, 'ivnt/ivnt-mplste/resources/Info.plist'), self.contents_dir)
        
        if self.manifest_data.name == "ivnt-client":
            self.copy(os.path.join(self.stagePath, '*.xsd'), self.macos_dir)
            self.copy(os.path.join(self.stagePath, '*.xml'), self.macos_dir)
            self.copy(os.path.join(self.root, 'ivnt/StandardDemo'), self.macos_dir)
            self.copy(os.path.join(self.root, 'ivnt/SystemScripts'), self.macos_dir)
            self.copy(os.path.join(self.root, 'ivnt/iVNT/menus.xml'), self.macos_dir)
    
    def copyExtraFilesToStage(self):
        # copy xerces and XL
        self.copy(os.path.join(self.root, 'deps/xerces/lib/libxerces-c.28.dylib'), self.frameworks_dir)
        self.copy(os.path.join(self.root, 'deps/libxl/lib/libxl.dylib'), self.frameworks_dir)
        # boost
        self.copy('/usr/local/Cellar/boost/1.55.0/lib/libboost_program_options.dylib', self.frameworks_dir)
        self.copy('/usr/local/Cellar/boost/1.55.0/lib/libboost_thread-mt.dylib', self.frameworks_dir)
        self.copy('/usr/local/Cellar/boost/1.55.0/lib/libboost_regex-mt.dylib', self.frameworks_dir)
        self.copy('/usr/local/Cellar/boost/1.55.0/lib/libboost_system-mt.dylib', self.frameworks_dir)
        # log4 and protobuf
        self.copy('/usr/local/Cellar/log4cxx/0.10.0/lib/liblog4cxx.10.dylib', self.frameworks_dir)
        self.copy('/usr/local/Cellar/protobuf/2.6.0/lib/libprotobuf.9.dylib', self.frameworks_dir)
        self.copy('/usr/lib/libQtCLucene.*.dylib', self.frameworks_dir)

        self.copy(os.path.join(self.stagePath, '*.framework'), self.frameworks_dir)
    
        self.copy(os.path.join(self.bindir, self.mainBundle, 'Contents', 'MacOS', 'ivnt'), self.macos_dir)
        self.copy(os.path.join('/usr', 'bin', 'qcollectiongenerator-4.8'), os.path.join(self.macos_dir, 'qcollectiongenerator'))
        self.copy(os.path.join(self.bindir, 'help'), self.macos_dir)

    def fixAssistant(self):
        self.copy(os.path.join('/Developer', 'Applications', 'Qt', 'Assistant.app'), self.stagePath)
        self.util.runOSCommand('macdeployqt %s' % os.path.join(self.stagePath, 'Assistant.app'))
        self.copy(os.path.join(self.stagePath, 'Assistant.app', 'Contents', 'MacOS', 'Assistant'), self.macos_dir)
        
    
    def addAuxBundle(self, bundleId):
        '''
        Bundles are assumed to be in the self.bindir path
        '''        
        print "INFO: Connecting bundle %s" % bundleId
        bundle_name = bundleId
        exe_name = bundleId.split('.')[0]
        self.copy(os.path.join(self.bindir, bundle_name), self.stagePath)
        self.util.runOSCommand('macdeployqt %s' % os.path.join(self.stagePath, bundle_name))
        self.installQt(os.path.join(self.stagePath, bundle_name, 'Contents', 'Frameworks'))
        self.exeList.append(os.path.join(self.stagePath, bundle_name, 'Contents', 'MacOS', exe_name))

    def debug_printDependencies(self):
        for ei in self.exeList:
            oscmd = "otool -L %s" % ei
            self.util.runOSCommand(oscmd)


    def connectLibsAndExecutables(self):
        '''
        Runs OSX's install_name_tool on all the executables and shared libs
        otool -L <exe> will show the result of this for each binary
        '''
        self.exeList = []
        self.addAuxBundle(self.mainBundle)

        self.exeList.append(os.path.join(self.macos_dir, 'qcollectiongenerator'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtCore.framework/Versions/4/QtCore'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtGui.framework/Versions/4/QtGui'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtHelp.framework/Versions/4/QtHelp'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtNetwork.framework/Versions/4/QtNetwork'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtScript.framework/Versions/4/QtScript'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtScriptTools.framework/Versions/4/QtScriptTools'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtSql.framework/Versions/4/QtSql'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtWebKit.framework/Versions/4/QtWebKit'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtXml.framework/Versions/4/QtXml'))
        self.exeList.append(os.path.join(self.frameworks_dir, 'QtXmlPatterns.framework/Versions/4/QtXmlPatterns'))
        self.exeList.extend(self.util.listFilesMatchingSuffix(self.stagePath, '.dylib'))

        self.depsList = []
        self.depsList.append('/opt/local/lib/libxerces-c.28.dylib')
        self.depsList.append('/usr/local/lib/libboost_program_options.dylib')
        self.depsList.append('/usr/local/lib/libboost_regex-mt.dylib')
        self.depsList.append('/usr/local/lib/libboost_system-mt.dylib')
        self.depsList.append('/usr/local/lib/libboost_thread-mt.dylib')
        self.depsList.append('/usr/local/lib/liblog4cxx.10.dylib')
        self.depsList.append('/usr/local/lib/libprotobuf.9.dylib')
        self.depsList.append('/usr/local/lib/libsqlite3.0.8.6.dylib')
        self.depsList.append('QtCore.framework/Versions/4/QtCore')
        self.depsList.append('QtGui.framework/Versions/4/QtGui')
        self.depsList.append('QtHelp.framework/Versions/4/QtHelp')
        self.depsList.append('QtNetwork.framework/Versions/4/QtNetwork')
        self.depsList.append('QtScript.framework/Versions/4/QtScript')
        self.depsList.append('QtScriptTools.framework/Versions/4/QtScriptTools')
        self.depsList.append('QtSql.framework/Versions/4/QtSql')
        self.depsList.append('QtWebKit.framework/Versions/4/QtWebKit')
        self.depsList.append('QtXml.framework/Versions/4/QtXml')
        self.depsList.append('QtXmlPatterns.framework/Versions/4/QtXmlPatterns')
        self.depsList.append('libQtCLucene.4.dylib')
        self.depsList.append('libaria-common-chart.1.dylib')
        self.depsList.append('libaria-common-dobject.1.dylib')
        self.depsList.append('libaria-common-gui.1.dylib')
        self.depsList.append('libaria-common-licensing.1.dylib')
        self.depsList.append('libaria-common-script.1.dylib')
        self.depsList.append('libaria-common-sql.1.dylib')
        self.depsList.append('libaria-common-test.1.dylib')
        self.depsList.append('libaria-common-xl.1.dylib')
        self.depsList.append('libaria-common-zip.1.dylib')
        self.depsList.append('libaria-common.1.dylib')
        self.depsList.append('libcommon-parser.1.dylib')
        self.depsList.append('libga-engine.1.dylib')
        self.depsList.append('libivnt-mplste.1.dylib')
        self.depsList.append('libivnt-server-common.1.dylib')
        self.depsList.append('libivnt-server-rpcclient.1.dylib')
        self.depsList.append('libivnt-server-rpcservice.1.dylib')
        self.depsList.append('libivnt-server-rpcshared.1.dylib')
        self.depsList.append('libivnt-server-scheduler.1.dylib')
        self.depsList.append('libivnt-server-soaprpcshared.1.dylib')
        self.depsList.append('libivnt-server-soapshared.1.dylib')
        self.depsList.append('libivnt-server-userdatabase.1.dylib')
        self.depsList.append('libivnt-server-watchfolder.1.dylib')
        self.depsList.append('liblogger.1.dylib')
        self.depsList.append('libmplste-inventory-gui.1.dylib')
        self.depsList.append('libmplste-inventory-translator.1.dylib')
        self.depsList.append('libmplste-inventory.1.dylib')
        self.depsList.append('libmplste-sdfx.1.dylib')
        self.depsList.append('libprotobuf-scriptapi.1.dylib')
        self.depsList.append('libunityrpc.1.dylib')
        self.depsList.append('libsystem-performance-metric.1.dylib')
        self.depsList.append('libxl.dylib')

        for x in self.exeList:
            for p in self.depsList:
                self.util.runOSCommand('chmod 755 %s' % x)
                self.doNameTool(p, x)                

        print "INFO: Finished:" 
        self.debug_printDependencies()


    def prepareStagingDirectory(self, manifest_name, manifest_filepath):

        self.manifest_data = Manifest(manifest_filepath, self.root, self.bindir)
        
        self.packageName = manifest_name
        self.stagePath = os.path.join(self.root, 'Stage', manifest_name)
        self.util.makeFullPath(self.stagePath)

        self.frameworks_dir = os.path.join(self.stagePath,self.mainBundle, 'Contents','Frameworks')
        self.macos_dir = os.path.join(self.stagePath,self.mainBundle, 'Contents','MacOS')
        self.shared_support_dir = os.path.join(self.stagePath,self.mainBundle, 'Contents','SharedSupport')
        self.resources_dir = os.path.join(self.stagePath,self.mainBundle, 'Contents','Resources')
        self.contents_dir = os.path.join(self.stagePath,self.mainBundle, 'Contents')

        self.util.makeFullPath(self.frameworks_dir)
        self.util.makeFullPath(self.macos_dir)
        self.util.makeFullPath(self.shared_support_dir)
        self.util.makeFullPath(self.resources_dir)

        self.stageFiles()
        self.createBundle()

    def createReleaseBundles(self):
        '''
        For a mac we need to create bundles that have all the libs and overlay files 
        for each release config.
        '''
        self.createHomeConfigPostInstall()
        ret_list = {}
        for (dirpath, dirs, files) in os.walk(os.path.join(self.root, 'buildscripts', 'customer_releases')):
            for filename in files:
                if filename.endswith('.list'):
                    name = filename.replace('.list', ' ').strip()
                    ret_list[name] = os.path.join(dirpath, filename)

        for k in ret_list.keys():
            try:
                compname = []
                f = open(ret_list[k], "r")
                for l in f:
                    compname.append(l.strip())
                f.close()
            except:
                print "Error: reading distribution list %s" % k
                return False

            distdir = os.path.join(self.distRoot, k, 'Applications', 'Aria')
            self.util.makeFullPath(distdir)
            for c in compname:
                self.copy(os.path.join(self.stageRoot, c, self.mainBundle), distdir)

            self.codesign(distdir) 
            self.createInstaller(distdir, k)

        return True
    
    def codesign(self, root):
        '''
        Signs the whiole bundle, from the top level
        '''
        self.signature = 'Developer ID Application: Aria Networks Limited (39B6R4V968)'
        self.signature_installer = 'Developer ID Installer: Aria Networks Limited (39B6R4V968)'
        self.identifier = '39B6R4V968.com.aria-networks.ivnt'
        self.buildPwd = 'build'
 
        scmd = 'security unlock-keychain -p "%s" /Users/software.build/Library/Keychains/login.keychain' % \
            self.buildPwd
        self.util.runOSCommand(scmd)

        scmd = 'codesign --deep --force --verify --verbose --sign "%s" %s' % \
            (self.signature, os.path.join(root, self.mainBundle))
        self.util.runOSCommand(scmd)
        scmd = 'spctl --assess --verbose=4 --type execute %s' % \
            os.path.join(root, self.mainBundle)
        self.util.runOSCommand(scmd)

    def createInstaller(self, distdir, rel_name): 

        pkg_name = '%s.%s.pkg' % (os.path.join(distdir, rel_name), self.build_version)

        scmd = 'security unlock-keychain -p "%s" /Users/software.build/Library/Keychains/login.keychain' % self.buildPwd
        self.util.runOSCommand(scmd)

        scmd = 'pkgbuild --root %s --identifier %s --sign "%s" --scripts "%s" --ownership recommended --install-location "/" %s' % \
            (distdir, self.identifier, self.signature_installer, self.scriptPath, pkg_name)            
        self.util.runOSCommand(scmd)

        # move package into installers dir - jenkins will like this.
        self.util.makeFullPath(os.path.join(self.root, 'installers'))
        self.copy(pkg_name, os.path.join(self.root, 'installers'))

    def createHomeConfigPostInstall(self):
        '''
        This works except if the installation does not happen in the 
        path /Applications/Aria then the postinstall script will fail :-(
        
        '''
        self.scriptPath = os.path.join(self.distRoot, 'scripts')
        self.util.makeFullPath(self.scriptPath)    
        stext = "#!/bin/sh\n"
        stext += "echo $0\n"
        stext += "echo $1\n"
        stext += "cp -fa %s %s\n" % ( \
            '/Applications/Aria/ivnt.app/Contents/Resources/__HOME__/.aria-networks', \
            os.environ['HOME'])
        try:
            f = open(os.path.join(self.scriptPath, "postinstall"), "w")
            f.write(stext)
            f.close()
        except:
            print "Error: writing script"
            sys.exit()

        scmd = "chmod u+x %s" % os.path.join(self.scriptPath, "postinstall")
        self.util.runOSCommand(scmd)

        
    def fix_QTBUG_32896(self, loc, fw):
        '''
        https://bugreports.qt-project.org/browse/QTBUG-32896
        '''
        try:
            fwsplt = fw.split('.')
            self.util.removeFile(os.path.join(loc, fw, 'Resources'))
            self.util.removeFile(os.path.join(loc, fw, 'Contents'))
            self.util.removeFile(os.path.join(loc, fw, 'Headers'))
            self.util.removeFile(os.path.join(loc, fw, fwsplt[0]))
            self.util.removeFile(os.path.join(loc, fw, 'Versions', '4.0'))
            self.util.removeFile(os.path.join(loc, fw, 'Versions', 'Current'))
            self.util.removeFile(os.path.join(loc, fw, '*.prl'))
            
            self.util.makeFullPath(os.path.join(loc, fw, 'Versions', '4', 'Resources'))

            srcplist = os.path.join('/Library/Frameworks', fw, 'Contents', 'Info.plist')
            dstplist = os.path.join(loc, fw, 'Versions', '4', 'Resources', 'Info.plist')
            self.copy(srcplist, os.path.join(loc, fw, 'Versions', '4', 'Resources'))

            self.util.removeFile(os.path.join(loc, fw, 'Versions', '4', 'Headers'))
            self.util.removeFile(os.path.join(loc, fw, 'Versions', '4', fwsplt[0]))
            
            self.copy(os.path.join('/Library/Frameworks', fw, 'Versions', '4', 'Headers'),
                os.path.join(loc, fw, 'Versions', '4'))
            self.copy(os.path.join('/Library/Frameworks', fw, 'Versions', '4', fwsplt[0]),
                os.path.join(loc, fw, 'Versions', '4'))
            self.copy(os.path.join('/Library/Frameworks', fw, 'Versions', '4', 'Resources', '*.nib'),
                os.path.join(loc, fw, 'Versions', '4', 'Resources'))

            f = open(dstplist, "r")
            s = f.read()
            f.close()
            ns = s.replace('_debug', ' ').strip()
            f = open(dstplist, "w")
            f.write(ns)
            f.close()
        

            self.symbolicLink(os.path.join(loc, fw, 'Versions'), '4', 'Current')
            self.symbolicLink(os.path.join(loc, fw), os.path.join('Versions', 'Current', fwsplt[0]), fwsplt[0])
            self.symbolicLink(os.path.join(loc, fw), os.path.join('Versions', 'Current', 'Headers'), 'Headers')
            self.symbolicLink(os.path.join(loc, fw), os.path.join('Versions', 'Current', 'Resources'), 'Resources')

        except Exception as e:
            print traceback.format_exc()
            pass
        
    def createEverythingBundles(self):
        '''
        This will be on a dmg with our installer
        give the operator the ability to install ANY or ALL components
        on a mac
        '''
        config_installer = "/Users/software.build/Desktop/tools/ivnt-configure/ivnt-configure.app"
        filename = os.path.join(self.root, 'buildscripts', 'customer_releases', 'everything.install')
        try:
            components = []
            file = open(filename, "r")
            for line in file:
                components.append(line.strip())
            file.close()
        except:
            print "Error: reading distribution list %s" % filename
            return False
    
        packageData = os.path.join(self.distRoot, 'Package')
        self.util.makeFullPath(packageData)
        for component in components:
            featureSlot = os.path.join(packageData, component)
            self.util.makeFullPath(featureSlot)
            self.copy(os.path.join(self.stageRoot, component, self.mainBundle), featureSlot)
            self.codesign(featureSlot)
    
        self.copy(config_installer, self.distRoot)         
        self.createDMGInstaller(self.distRoot)
    
        return True   
    
    
    def createDMGInstaller(self, package_data):        
        
        tmp_dmg=os.path.join(self.stageRoot, 'temp.dmg')        
        pkg_name = '%s.%s' % ('ivnt-everything', self.build_version)
        pkg_path = os.path.join(package_data, pkg_name)
        dmg_name = '%s.dmg' % pkg_path
              
        scmd = 'hdiutil create -srcfolder "%s" -volname "%s" -fs HFS+ -fsargs "-c c=64,a=16,e=16" -format UDRW -size 4G "%s"' % \
            (package_data, pkg_name, tmp_dmg)
        self.util.runOSCommand(scmd)
        
        scmd = 'hdiutil convert "%s" -format UDZO -imagekey zlib-level=9 -o "%s"' % (tmp_dmg, dmg_name)
        self.util.runOSCommand(scmd)

        self.util.makeFullPath(os.path.join(self.root, 'installers'))
        self.copy(dmg_name, os.path.join(self.root, 'installers')) 
        


# macosx END.
