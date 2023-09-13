from PySide6.Qt3DCore import Qt3DCore
from PySide6.QtCore import QUrl, QObject, Signal, Property, Qt
from PySide6.QtGui import QVector3D, QMatrix4x4
from PySide6.QtWidgets import QLayout, QWidget, QPushButton, QFileDialog, QLabel

from PySide6.Qt3DExtras import Qt3DExtras
from PySide6.Qt3DRender import Qt3DRender

from starhopper.formats.archive import AbstractFile
from starhopper.formats.mesh import mesh_to_obj
from starhopper.gui.common import tr, ColorGray
from starhopper.gui.viewers.viewer import Viewer


class ModelViewer(Viewer):
    def __init__(self, file: AbstractFile, working_area: QLayout):
        super().__init__(working_area=working_area)

        self.file = file

        # Don't show the 3D preview under Nuitka since it'll just crash for
        # who-knows-why (using the debugger just crashes it sooner)
        if "__compiled__" not in globals():
            self.preview = Qt3DExtras.Qt3DWindow()
            self.preview.defaultFrameGraph().setClearColor(ColorGray)
            self.container = QWidget.createWindowContainer(self.preview)
            self.scene = Qt3DCore.QEntity()

            camera = self.preview.camera()
            # camera.lens().setPerspectiveProjection(45, 16 / 9, 0.1, 1000)
            camera.setPosition(QVector3D(0, 0, 10))
            camera.setViewCenter(QVector3D(0, 0, 0))

            self.camera_controller = Qt3DExtras.QFirstPersonCameraController(
                self.scene
            )
            self.camera_controller.setLinearSpeed(25)
            self.camera_controller.setLookSpeed(180)
            self.camera_controller.setCamera(camera)

            self.material = Qt3DExtras.QPhongMaterial(self.scene)

            with file.open() as f:
                # For whatever reason, Qt3D doesn't like it when we pass it
                # a NamedTemporaryFile. Maybe it doesn't load until after a
                # ProcessEvents call, in which case it would already be deleted?
                # Who knows.
                # with NamedTemporaryFile("wb", suffix=".obj") as destination:
                with open("preview.obj", "wb") as destination:
                    mesh_to_obj(f, destination)
                    destination.flush()

                    # This is a hack, we should create the QGeometry directly from
                    # the .mesh rather than this export-and-import shenanigans.
                    # But, this is also just 2 lines, sooooo...
                    self.mesh = Qt3DRender.QMesh()
                    self.mesh.setSource(QUrl.fromLocalFile(destination.name))

                    self.transform = Qt3DCore.QTransform()
                    self.entity = Qt3DCore.QEntity(self.scene)
                    self.entity.addComponent(self.mesh)
                    self.entity.addComponent(self.material)
                    self.entity.addComponent(self.transform)
                    self.transform.setTranslation(QVector3D(0, 0, 0))

            self.preview.setRootEntity(self.scene)
            self.layout.insertWidget(0, self.container)
        else:
            self.warning = QLabel(
                tr(
                    "ModelViewer",
                    "3D preview is disabled under Nuitka.",
                    None,
                )
            )
            self.warning.setAlignment(Qt.AlignCenter)
            self.layout.insertWidget(0, self.warning)

        self.export_button = QPushButton(
            tr("ModelViewer", "E&xport As .obj", None)
        )
        self.export_button.clicked.connect(self.on_export)

        # self.layout.insertWidget(0, self.container)
        self.layout.insertWidget(1, self.export_button)

    def on_export(self):
        fname, _ = QFileDialog.getSaveFileName(
            self,
            tr("ModelViewer", "Export As", None),
            filter=tr("ModelViewer", "Wavefront OBJ (*.obj)", None),
        )

        if not fname:
            return

        with open(fname, "wb") as f:
            with self.file.open() as source:
                mesh_to_obj(source, f)
