# InsertTrack class for 3DEqualizer4
# 
# Inserts, prepends or appends part of a 2D tracking curve into the gap of another 2D tracking curve. And more.
# Wolfgang Niedermeier 2012
# 
# 3DE4.script.hide: true
#
# v1.2 fixed bug with single end keyframes not connected to tracked frames on either side
# v1.1 shuffled a few things around to fix a minor bug
# v1.0 first release


import tde4
import copy
import sys


class CancelException(Exception):
    pass


class InsertTrack(object):
    '''Inserts part of a 2D tracking curve into the gap of another 2D tracking curve. And more.
    
    v1.2 fixed bug with single end keyframes not connected to tracked frames on either side
    v1.1 shuffled a few things around to fix a minor bug
    v1.0 first release
    '''


    def __init__(self):
        self.version = '1.2'
        self.pg = None              # tde4 pointgroup
        self.p_list = []            # tde4 pointlist
        self.p_list_avrg = []       # list of points to be averaged
        self.cam = None             # tde4 camera
        self.nfr = 0                # tde4 number of frames
        self.name = ''              # tde4 point name
        self.frame = 1              # tde4 current frame
        self.select_curve = []      # 2D tracking data, not yet assigned to target or source
        self.target_point = None    # tde4 point
        self.target_curve = []      # 2D tracking data
        self.source_point = None    # tde4 point
        self.source_curve = []      # 2D tracking data
        self.target_status = []     # tde4 pointStatus2D
        self.range = []             # start/end of section (frame)
        self.keylist = []           # frames where source and target overlap
        self.averaged_point = None  # point object averaged tracking data gets written to


 
    def _setEnv(self):
        self.pg = tde4.getCurrentPGroup()
        self.p_list = tde4.getPointList(self.pg, True)
        self.cam = tde4.getCurrentCamera()
        self.nfr = tde4.getCameraNoFrames(self.cam)
        self.frame = tde4.getCurrentFrame(self.cam)


    def evalSelection(self):
        try:
            print '--------------- insert track v%s ---------------'%self.version
            self._setEnv()
            tde4.pushPointsToUndoStack()
            # A) nothing selected
            if self.p_list == []:
                raise CancelException('ERROR: invalid input (no points selected)')
            # B) selection is one point
            elif len(self.p_list) == 1:
                print 'one point selected'
                self.source_point = self.p_list[0]
                self.target_point = self.p_list[0]
                self.target_curve = tde4.getPointPosition2DBlock(self.pg, self.target_point, self.cam, 1, self.nfr)
                if self.target_curve[self.frame-1] != [-1, -1]:
                    raise CancelException('ERROR: invalid input (curve already has tracking data at current frame)')
                else:
                    print 'target: "' + tde4.getPointName(self.pg, self.target_point) + '"'
                    print 'source: reeling in target'
                    self.source_curve = []
                    for i in range(1, self.nfr+1):
                        try:
                            self.source_curve.append(tde4.calcPointBackProjection2D(self.pg, self.source_point, self.cam, i, True))
                        except:
                            self.source_curve.append([-1, -1])
            # C) two or more points selected
            else:
                if len(self.p_list) == 2:
                    print '2 points selected'
                else:
                    print 'multiple points selected'
                # separate target curve from source curve(s)
                self.p_list_avrg = []
                for i in range(len(self.p_list)):
                    self.select_curve = tde4.getPointPosition2DBlock(self.pg, self.p_list[i], self.cam, 1, self.nfr)
                    if self.select_curve[self.frame-1] == [-1, -1]:
                        self.target_point = self.p_list[i]
                        self.target_curve = tde4.getPointPosition2DBlock(self.pg, self.target_point, self.cam, 1, self.nfr)
                        #self._readStatus()
                    else:
                        self.p_list_avrg.append(self.p_list[i])
                #
                # 1) none of the selected points has tracking data at current frame throws exception
                if len(self.p_list_avrg) == 0:
                    #self._restorePointListTrackingDirection()
                    raise CancelException('ERROR: invalid input (none of the selected points has tracking data at current frame)')
                # 2) special: all points have tracking data at current frame: create a new point with averaged track
                if len(self.p_list_avrg) > 1 and self.target_point == None:
                    self._averagePointList()
                    self.averaged_point = tde4.createPoint(self.pg)
                    tde4.setPointName(self.pg, self.averaged_point, 'avrg_01')
                    print 'creating new point:\n    "' + tde4.getPointName(self.pg, self.averaged_point) + '"' 
                    tde4.setPointPosition2DBlock(self.pg, self.averaged_point, self.cam, 1, self.source_curve)
                    #self._restorePointListTrackingDirection()
                    self._deselectAllPoints()
                    tde4.setPointSelectionFlag(self.pg, self.averaged_point, True)
                    raise CancelException('done.')

                print 'target: "' + tde4.getPointName(self.pg, self.target_point) + '"'
                # 3) two or more points selected, standard insert
                if len(self.p_list) == 2:
                    self.source_point = self.p_list_avrg[0]
                    self.source_curve = tde4.getPointPosition2DBlock(self.pg, self.source_point, self.cam, 1, self.nfr)
                    print 'source: "' + tde4.getPointName(self.pg, self.source_point) + '"'
                elif len(self.p_list) > 2:
                    self._averagePointList()
            # find the framerange that is to be inserted and go from there
            self._setRange()
        except CancelException, e:
            print e


    def _setRange(self):
        '''sets the framerange where the insert happens'''
        # seek valid curve start to the left of current frame (timeline)
        self.keylist = []
        self.range = []
        for i in range(self.frame, 0, -1):
            if self.target_curve[i-1] != [-1, -1]:
                self.range.append(i+1)
                if self.source_curve[i-1] != [-1, -1]:
                    xys = self.source_curve[i-1]
                    xyt = self.target_curve[i-1]
                    xyo = [xyt[0] - xys[0], xyt[1] - xys[1]]
                    self.keylist.append([i, xyo]) # [frame, offset]
                break
            # in case left boundary is first frame:
            if i == 1 and self.target_curve[i-1] == [-1, -1]:
                self.range.append(i)
        # seek valid curve start to the right of current frame (timeline)
        for i in range(self.frame, self.nfr+1):
            if self.target_curve[i-1] != [-1, -1]:
                self.range.append(i-1)
                if self.source_curve[i-1] != [-1, -1]:
                    xys = self.source_curve[i-1]
                    xyt = self.target_curve[i-1]
                    xyo = [xyt[0] - xys[0], xyt[1] - xys[1]]
                    self.keylist.append([i, xyo]) # [frame, offset]
                break
            # in case left boundary is last frame:
            if i == self.nfr and self.target_curve[i-1] == [-1, -1]:
                self.range.append(i)
        # catch invalid user input
        if len(self.p_list) > 1:
            if self.keylist == []:
                raise CancelException('ERROR: selection has no overlap.')
        print 'section:', self.range
        self._printKeylist()        
        # type of insert (offset or deform)
        if len(self.keylist) == 0:
            self._insertSection()
        elif len(self.keylist) == 1:
            self._offsetCurve()
        elif len(self.keylist) == 2:
            self._deformCurve()


    def _averagePointList(self):
        '''creates averaged curve from all points in self.p_list_avrg'''
        print 'averaging', len(self.p_list_avrg), 'source points:'
        for p in self.p_list_avrg:
            print '    "' + tde4.getPointName(self.pg, p) + '"'
        a = tde4.getPointPosition2DBlock(self.pg, self.p_list_avrg[0], self.cam, 1, self.nfr)
        # point loop
        for i in range(1, len(self.p_list_avrg)):
            b = tde4.getPointPosition2DBlock(self.pg, self.p_list_avrg[i], self.cam, 1, self.nfr)
            # frame loop: add up coordinates of all points
            for n in range(self.nfr):
                if -1 not in (a[n][0], b[n][0]):
                    a[n][0] += b[n][0]  # X
                    a[n][1] += b[n][1]  # Y
                else:
                    a[n] = [-1, -1] 
        # frame loop: divide coordiantes by number of points
        for n in range(self.nfr):
            if -1 not in a[n]:
                a[n][0] /= len(self.p_list_avrg)  # X
                a[n][1] /= len(self.p_list_avrg)  # Y
        self.source_curve = copy.deepcopy(a)


    def _readStatus(self):
        self.target_status = []
        for i in range(self.nfr):
            self.target_status.append(tde4.getPointStatus2D(self.pg, self.target_point, self.cam, i+1))


    def _deselectAllPoints(self):
        p_list = tde4.getPointList(self.pg, False)
        for p in p_list:
            tde4.setPointSelectionFlag(self.pg, p, False)


    def _printKeylist(self):
        '''prints a simplified (keys only) version of the current keylist'''
        k = []
        for i in self.keylist:
            k.append(i[0])
        print 'overlap:', k


    def _offsetCurve(self):
        for i in range(self.nfr):
            if self.source_curve[i] != [-1, -1]:
                self.source_curve[i][0] += self.keylist[0][1][0]
                self.source_curve[i][1] += self.keylist[0][1][1]
        self._insertSection()


    def _deformCurve(self):
        # linear interpolation segment loop
        for i in range(len(self.keylist)-1):
            # segment start(0)/end(1) (frame)
            f0 = self.keylist[i][0]
            f1 = self.keylist[i+1][0]
            # segment start/end offset(o) for in between interpolation
            xo0 = self.keylist[i][-1][0]
            yo0 = self.keylist[i][-1][1]
            xo1 = self.keylist[i+1][-1][0]
            yo1 = self.keylist[i+1][-1][1]
            # frame loop for in between frames
            for f in range(f0, f1):
                # calc interpolated(I) offset at frame
                xoI = (xo0 + ((f - f0) * ((xo1 - xo0) / (f1 - f0))))
                yoI = (yo0 + ((f - f0) * ((yo1 - yo0) / (f1 - f0))))
                # update target curve
                if not -1 in self.source_curve[f-1]:
                    self.source_curve[f-1][0] += xoI
                    self.source_curve[f-1][1] += yoI
        self._insertSection()


    def _insertSection(self):
        self._readStatus()
        # copy section from modified source to target
        for i in range(self.range[0], self.range[1]+1):
            self.target_curve[i-1] = self.source_curve[i-1]
        tde4.setPointPosition2DBlock(self.pg, self.target_point, self.cam, 1, self.target_curve)
        # restore some of the original curve settings
        for i in range(self.nfr):
            if self.target_status[i] == 'POINT_KEYFRAME':
                tde4.setPointStatus2D(self.pg, self.target_point, self.cam, i+1, 'POINT_KEYFRAME')
        # mark borders of section with keyframes
        if self.range[0] != 1:
            if self.target_curve[self.range[0]-1] != [-1, -1]:
                # forward tracking mode
                if tde4.getPointTrackingDirection(self.pg, self.target_point) != 'TRACKING_BW':
                    tde4.setPointStatus2D(self.pg, self.target_point, self.cam, self.range[0]-1, 'POINT_KEYFRAME')
        if self.range[1] != self.nfr:
            if self.target_curve[self.range[1]-1] != [-1, -1]:
                # backward tracking mode
                if tde4.getPointTrackingDirection(self.pg, self.target_point) == 'TRACKING_BW':
                    tde4.setPointStatus2D(self.pg, self.target_point, self.cam, self.range[1]+1, 'POINT_KEYFRAME')
        
        # make the target point the selected one
        self._deselectAllPoints()
        tde4.setPointSelectionFlag(self.pg, self.target_point, True)
        print 'done.'
