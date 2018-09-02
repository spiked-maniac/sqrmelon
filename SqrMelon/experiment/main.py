import functools
from experiment.demomodel import DemoModel
from experiment.modelbase import UndoableModel
from view3d import View3D
from experiment.scenelist import SceneList
from qtutil import *
from experiment.curvemodel import HermiteCurve, HermiteKey, ELoopMode
from experiment.model import Clip, Event, Shot
from experiment.timelineview import TimelineView
from experiment.timer import Time
from experiment.widgets import CurveUI, ClipUI, ShotManager, EventManager
from experiment.projectutil import settings
from experiment.camerawidget import Camera


def evalCamera(camera, model, timer):
    __, anim = model.evaluate(timer.time)
    camera.setData(anim.get('uOrigin.x', 0.0), anim.get('uOrigin.y', 0.0), anim.get('uOrigin.z', 0.0), anim.get('uAngles.x', 0.0), anim.get('uAngles.y', 0.0), anim.get('uAngles.z', 0.0))


def eventChanged(iterSelectedRows, curveUI):
    for event in iterSelectedRows():
        curveUI.setEvent(event.data(Qt.UserRole + 1))
        return
    curveUI.setEvent(None)


def run():
    app = QApplication([])
    settings().setValue('currentproject', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'defaultproject'))

    # these elements are pretty "global" in that they are referenced by most widgets
    undoStack = QUndoStack()
    timer = Time()
    demoModel = DemoModel(timer, undoStack)

    # main widgets
    undoView = QUndoView(undoStack)
    shotManager = ShotManager(undoStack, demoModel, timer)

    def iterItemRows(model):
        for row in xrange(model.rowCount()):
            yield model.index(row, 0).data(Qt.UserRole + 1)

    clipsModel = UndoableModel(undoStack)
    iterClips = functools.partial(iterItemRows, clipsModel)

    eventManager = EventManager(undoStack, demoModel, timer, iterClips)
    clips = ClipUI(clipsModel, undoStack, demoModel, timer, eventManager.view.selectionChange, eventManager.firstSelectedEvent)
    sceneList = SceneList(timer, clips.createClip, demoModel.addShot)
    curveUI = CurveUI(timer, clips.manager.selectionChange, clips.manager.firstSelectedItem, eventManager.firstSelectedEventWithClip, undoStack)
    eventTimeline = TimelineView(timer, undoStack, demoModel, (shotManager.view.selectionModel(), eventManager.view.selectionModel()))
    camera = Camera()

    # the 3D view is the only widget that references other widgets
    view = View3D(camera, demoModel, timer)

    # set up main window and dock widgets
    mainWindow = QMainWindowState(settings())
    mainWindow.setDockNestingEnabled(True)
    mainWindow.createDockWidget(undoView)
    mainWindow.createDockWidget(clips)
    mainWindow.createDockWidget(curveUI)
    mainWindow.createDockWidget(shotManager, name='Shots')
    mainWindow.createDockWidget(eventManager, name='Events')
    mainWindow.createDockWidget(eventTimeline)
    mainWindow.createDockWidget(sceneList)
    mainWindow.createDockWidget(camera)
    mainWindow.createDockWidget(view)

    # set up menu actions & shortcuts
    menuBar = QMenuBar()
    mainWindow.setMenuBar(menuBar)

    editMenu = menuBar.addMenu('Edit')

    undo = undoStack.createUndoAction(editMenu, '&Undo ')
    editMenu.addAction(undo)
    undo.setShortcut(QKeySequence(QKeySequence.Undo))
    undo.setShortcutContext(Qt.ApplicationShortcut)

    redo = undoStack.createRedoAction(editMenu, '&Redo ')
    editMenu.addAction(redo)
    redo.setShortcut(QKeySequence(QKeySequence.Redo))
    redo.setShortcutContext(Qt.ApplicationShortcut)

    keyCamera = editMenu.addAction('&Key camera')
    keyCamera.setShortcut(QKeySequence(Qt.Key_K))
    keyCamera.setShortcutContext(Qt.ApplicationShortcut)

    toggleCamera = editMenu.addAction('&Toggle camera control')
    toggleCamera.setShortcut(QKeySequence(Qt.Key_T))
    toggleCamera.setShortcutContext(Qt.ApplicationShortcut)

    resetCamera = editMenu.addAction('Snap came&ra to animation')
    resetCamera.setShortcuts(QKeySequence(Qt.Key_R))
    resetCamera.setShortcutContext(Qt.ApplicationShortcut)

    # add test content
    clip0 = Clip('Clip 0', undoStack)
    clip0.curves.appendRow(HermiteCurve('uOrigin.x', ELoopMode.Clamp, [HermiteKey(0.0, 0.0, 0.0, 0.0), HermiteKey(4.0, 1.0, 1.0, 1.0)]).items)
    clip0.curves.appendRow(HermiteCurve('uFlash', ELoopMode.Clamp, [HermiteKey(0.0, 1.0, 1.0, 1.0), HermiteKey(1.0, 0.0, 0.0, 0.0)]).items)

    clip1 = Clip('Clip 1', undoStack)
    clip1.curves.appendRow(HermiteCurve('uOrigin.x', ELoopMode.Clamp, [HermiteKey(2.0, 0.0, 0.0, 0.0), HermiteKey(3.0, 1.0, 0.0, 0.0)]).items)
    clip1.curves.appendRow(HermiteCurve('uOrigin.y', ELoopMode.Clamp, [HermiteKey(0.0, 0.0, 1.0, 1.0), HermiteKey(1.0, 1.0, 1.0, 1.0)]).items)

    demoModel.appendRow(Shot('New Shot', 'example', 0.0, 4.0, 0).items)

    demoModel.appendRow(Event('New event', clip0, 0.0, 4.0, 1.0, 0.0, 2).items)
    demoModel.appendRow(Event('New event', clip0, 0.0, 1.0, 1.0, 0.0, 1).items)
    demoModel.appendRow(Event('New event', clip1, 1.0, 2.0, 0.5, 0.0, 1).items)
    demoModel.appendRow(Event('New event', clip0, 2.0, 4.0, 0.25, 0.0, 1).items)

    clips.manager.model().appendRow(clip0.items)
    clips.manager.model().appendRow(clip1.items)

    # Fix widgets after content change
    eventTimeline.frameAll()
    shotManager.view.updateSections()
    eventManager.view.updateSections()

    # connection widgets together
    # changing the model contents seems to mess with the column layout stretch
    demoModel.rowsInserted.connect(shotManager.view.updateSections)
    demoModel.rowsInserted.connect(eventManager.view.updateSections)
    demoModel.rowsRemoved.connect(shotManager.view.updateSections)
    demoModel.rowsRemoved.connect(eventManager.view.updateSections)

    demoModel.dataChanged.connect(curveUI.view.repaint)

    eventManager.view.selectionChange.connect(functools.partial(eventChanged, eventManager.view.selectionModel().selectedRows, curveUI))
    camera.requestAnimatedCameraPosition.connect(functools.partial(evalCamera, camera, demoModel, timer))

    # when animating, the camera will see about animation
    # if it is not set to follow animation it will do nothing
    # else it will emit requestAnimatedCameraPosition, so that the internal state will match
    timer.changed.connect(camera.followAnimation)

    # when the camera is changed  through flying (WASD, Mouse) or through the input widgets, it will emit an edited event, signaling repaint
    camera.edited.connect(view.repaint)
    # when the time changes, the camera is connected first so animation is applied, then we still have to manually trigger a repaint here
    timer.changed.connect(view.repaint)

    keyCamera.triggered.connect(functools.partial(curveUI.keyCamera, camera))
    toggleCamera.triggered.connect(camera.toggle)
    resetCamera.triggered.connect(camera.copyAnim)

    mainWindow.show()
    # makes sure qt cleans up & python stops after closing the main window; https://stackoverflow.com/questions/39304366/qobjectstarttimer-qtimer-can-only-be-used-with-threads-started-with-qthread
    mainWindow.setAttribute(Qt.WA_DeleteOnClose)

    app.exec_()


if __name__ == '__main__':
    run()
