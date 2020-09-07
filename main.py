#!/usr/bin/env python3
import sys
import cv2
import csv
import numpy as np

from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog
from PyQt5.QtGui import QIcon

from PyQt5 import QtCore
from PyQt5 import QtWidgets
from PyQt5 import QtGui
import about 
import widget 


class Ui(QtWidgets.QWidget):
    def __init__(self):
        super(Ui, self).__init__()
        ui = widget.Ui_Form()
        ui.setupUi(self)
        self.setFixedSize(self.size())
        self.show()


class AboutWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super(AboutWindow, self).__init__()
        ui = about.Ui_MainWindow()
        ui.setupUi(self)
        self.setFixedSize(self.size())
        self.setWindowTitle("About")
        self.hide()


class CaptureFrame(QtCore.QObject):
    image_data = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, camera_port=0, parent=None):
        super().__init__(parent)
        self.port = camera_port
        self.camera = None
        self.timer = QtCore.QBasicTimer()
        self.image_path = 'images/sample.jpg'
        self.video = False
        self.start_recording()

    def start_recording(self):
        self.timer.start(0, self)

    def open_camera(self):
        self.camera = cv2.VideoCapture(self.port)

    def timerEvent(self, event):
        if event.timerId() != self.timer.timerId():
            return
        if self.video:
            if self.camera is None:
                self.open_camera()
            elif not self.camera.isOpened():
                self.camera.open(self.port)
            read, data = self.camera.read()
            if read:
                data = cv2.flip(data, 1)
        else:
            if self.camera is not None:
                if self.camera.isOpened():
                    self.camera.release()
            data = cv2.imread(self.image_path)
            read = True
        if read:
            data = resize(data, height=480)
            data = resize(data, width=540)
            self.image_data.emit(data)

def resize(image, width=None, height=None, inter=cv2.INTER_AREA):
    # initialize the dimensions of the image to be resized and
    # grab the image size
    dim = None
    (h, w) = image.shape[:2]

    # if both the width and height are None, then return the
    # original image
    if width is None and height is None:
        return image

    # check to see if the width is None
    if width is None:
        # calculate the ratio of the height and construct the
        # dimensions
        r = height / float(h)
        dim = (int(w * r), height)

    # otherwise, the height is None
    else:
        # calculate the ratio of the width and construct the
        # dimensions
        r = width / float(w)
        dim = (width, int(h * r))

    # resize the image
    resized = cv2.resize(image, dim, interpolation=inter)

    # return the resized image
    return resized

class VideoStream(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = QtGui.QImage()
        self._red = (0, 0, 255)
        self._width = 2
        self._min_size = (30, 30)

    def image_data_slot(self, image_data):
        self.image = self.get_qimage(image_data)
        if self.image.size() != self.size():
            self.setFixedSize(self.image.size())
        self.update()

    @staticmethod
    def get_qimage(image: np.ndarray):
        height, width, colors = image.shape
        bytesPerLine = 3 * width
        QImage = QtGui.QImage

        image = QImage(image.data,
                       width,
                       height,
                       bytesPerLine,
                       QImage.Format_RGB888)

        image = image.rgbSwapped()
        return image

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.drawImage(0, 0, self.image)
        self.image = QtGui.QImage()


class ColorDetector(VideoStream):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.lowHue = 0
        self.lowSat = 0
        self.lowVal = 0
        self.highHue = 359
        self.highSat = 255
        self.highVal = 255
        self.erode = False
        self.dilate = False
        self.blur = False
        self.invert = False
        self.show = False
        self.k_size = 11
        self.erode_i = 1
        self.dilate_i = 1

    def mask_frame(self, frame):
        image = frame.copy()
        lower_range = (self.lowHue, self.lowSat, self.lowVal)
        upper_range = (self.highHue, self.highSat, self.highVal)
        if self.blur:
            frame = cv2.GaussianBlur(frame, (self.k_size, self.k_size), 0)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(frame, lower_range, upper_range)

        if self.erode:
            mask = cv2.erode(mask, None, iterations=self.erode_i)
        if self.dilate:
            mask = cv2.dilate(mask, None, iterations=self.dilate_i)
        if self.invert:
            mask = 255 - mask
        if not self.show:
            mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        if self.show:
            mask_inv = cv2.bitwise_not(mask)
            rows, cols, channels = image.shape
            image = image[0:rows, 0:cols]
            masked = cv2.bitwise_or(image, image, mask=mask)
            masked = masked[0:rows, 0:cols]
            not_masked = cv2.bitwise_or(mask, mask, mask=mask_inv)
            not_masked = np.stack((not_masked,) * 3, axis=-1)
            mask = masked + not_masked
        return mask

    def image_data_slot(self, image_data):
        mask = self.mask_frame(image_data)
        self.image = self.get_qimage(mask)
        if self.image.size() != self.size():
            self.setFixedSize(self.image.size())
        self.update()


class MainWidget(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.line_num = 0
        self.video_stream = VideoStream()
        self.color_detector = ColorDetector()
        self.about_window = AboutWindow()

        self.capture_frame = CaptureFrame()

        video_data_slot = self.video_stream.image_data_slot
        color_data_slot = self.color_detector.image_data_slot
        self.capture_frame.image_data.connect(video_data_slot)
        self.capture_frame.image_data.connect(color_data_slot)

        layout = QtWidgets.QVBoxLayout()

        capture_layout = QtWidgets.QVBoxLayout()
        capture_text = QtWidgets.QLabel("Capture")
        capture_text.setAlignment(QtCore.Qt.AlignCenter)

        capture_layout.addWidget(capture_text)
        capture_layout.addWidget(self.video_stream)

        color_layout = QtWidgets.QVBoxLayout()

        color_text = QtWidgets.QLabel("Mask")
        color_text.setAlignment(QtCore.Qt.AlignCenter)

        color_layout.addWidget(color_text)
        color_layout.addWidget(self.color_detector)

        video_layout = QtWidgets.QHBoxLayout()
        video_layout.addLayout(capture_layout)
        video_layout.addLayout(color_layout)

        grid = QtWidgets.QGridLayout()

        grid.addLayout(video_layout, 0, 2)
        grid.setRowStretch(1, 2)
        box = Ui()
        self.lh = box.findChild(QtWidgets.QSlider, 'lowHueSlider')
        self.lh.valueChanged.connect(self.low_hue)

        self.hh = box.findChild(QtWidgets.QSlider, 'highHueSlider')
        self.hh.valueChanged.connect(self.high_hue)

        self.ls = box.findChild(QtWidgets.QSlider, 'lowSatSlider')
        self.ls.valueChanged.connect(self.low_sat)

        self.hs = box.findChild(QtWidgets.QSlider, 'highSatSlider')
        self.hs.valueChanged.connect(self.high_sat)

        self.lv = box.findChild(QtWidgets.QSlider, 'lowValSlider')
        self.lv.valueChanged.connect(self.low_val)

        self.hv = box.findChild(QtWidgets.QSlider, 'highValSlider')
        self.hv.valueChanged.connect(self.high_val)

        self.blur = box.findChild(QtWidgets.QCheckBox, 'blur_check')
        self.blur.clicked.connect(self.blur_check)

        self.k_size = box.findChild(QtWidgets.QSlider, 'kSlider')
        self.k_size.valueChanged.connect(self.ksize_val)

        self.invert = box.findChild(QtWidgets.QCheckBox, 'invert_check')
        self.invert.clicked.connect(self.invert_check)

        self.erode = box.findChild(QtWidgets.QCheckBox, 'erode_check')
        self.erode.clicked.connect(self.erode_check)

        self.dilate = box.findChild(QtWidgets.QCheckBox, 'dilate_check')
        self.dilate.clicked.connect(self.dilate_check)

        self.show_mask = box.findChild(QtWidgets.QCheckBox, 'showmask_check')
        self.show_mask.clicked.connect(self.showmask_check)

        self.erode_spinbox = box.findChild(QtWidgets.QSpinBox, 'spinBox_erode')
        self.erode_spinbox.valueChanged.connect(self.spinbox_erode)

        self.dilate_spinbox = box.findChild(QtWidgets.QSpinBox, 'spinBox_dilate')
        self.dilate_spinbox.valueChanged.connect(self.spinbox_dilate)

        box.move(100, 100)
        options_layout = QtWidgets.QHBoxLayout()
        options_layout.addWidget(box)

        grid.addLayout(options_layout, 2, 2)

        layout.addLayout(grid)
        buttons_layout = QtWidgets.QHBoxLayout()
        video_button = QtWidgets.QPushButton('Start Camera', self)
        video_button.setToolTip('Live Video Stream')
        video_button.move(100, 100)
        video_button.clicked.connect(self.video_click)

        image_button = QtWidgets.QPushButton('Open Image', self)
        image_button.setToolTip('Open an Image')
        image_button.move(100, 100)
        image_button.clicked.connect(self.image_click)

        about_button = QtWidgets.QPushButton('About', self)
        about_button.setToolTip('About')
        about_button.move(100, 150)
        about_button.clicked.connect(self.about_click)

        buttons_layout.addWidget(video_button)
        buttons_layout.addWidget(image_button)
        buttons_layout.addWidget(about_button)

        layout.addLayout(buttons_layout)

        csv_layout = QtWidgets.QHBoxLayout()
        
        start_button = QtWidgets.QPushButton('SAVE Configurations', self)
        start_button.setToolTip('Export Configurations')
        start_button.move(100, 70)
        start_button.clicked.connect(self.save_click)

        csv_layout.addWidget(start_button)

        load_button = QtWidgets.QPushButton('Load Configurations', self)
        load_button.setToolTip('Import Configurations')
        load_button.move(100, 70)
        load_button.clicked.connect(self.load_click)

        csv_layout.addWidget(load_button)
        layout.addLayout(csv_layout)
        
        self.setLayout(layout)

    def low_hue(self, value):
        self.color_detector.lowHue = value

    def high_hue(self, value):
        self.color_detector.highHue = value

    def low_sat(self, value):
        self.color_detector.lowSat = value

    def high_sat(self, value):
        self.color_detector.highSat = value

    def low_val(self, value):
        self.color_detector.lowVal = value

    def high_val(self, value):
        self.color_detector.highVal = value

    def blur_check(self, value):
        self.color_detector.blur = value

    def ksize_val(self, value):
        if value % 2 == 0:
            value = value + 1
            self.k_size.setValue(value)
        self.color_detector.k_size = value

    def invert_check(self, value):
        self.color_detector.invert = value

    def erode_check(self, value):
        self.color_detector.erode = value

    def dilate_check(self, value):
        self.color_detector.dilate = value

    def spinbox_dilate(self, value):
        self.color_detector.dilate_i = value

    def spinbox_erode(self, value):
        self.color_detector.erode_i = value

    def showmask_check(self, value):
        self.color_detector.show = value

    def video_click(self):
        self.capture_frame.video = True

    def about_click(self):
        self.about_window.show()

    def image_click(self):
        filename = self.openFileNameDialog()
        if filename:
            self.capture_frame.image_path = filename
            self.capture_frame.video = False

    def save_click(self):
        filename = self.saveFileDialog()
        if filename:
            with open(filename, 'w', newline='') as file:
                writer = csv.writer(file)
                self.line_num = 0
                writer.writerow(["SN", "Name", "Value"])
                writer.writerow([self.line_print(), "Low Hue",
                                 self.color_detector.lowHue])
                writer.writerow([self.line_print(), "High Hue",
                                 self.color_detector.highHue])
                writer.writerow(
                    [self.line_print(), "Low Saturation", self.color_detector.lowSat])
                writer.writerow(
                    [self.line_print(), "High Saturation", self.color_detector.highSat])
                writer.writerow(
                    [self.line_print(), "Low Value", self.color_detector.lowVal])
                writer.writerow(
                    [self.line_print(), "High Value", self.color_detector.highVal])
                writer.writerow(
                    [self.line_print(), "Gaussian Blur", self.color_detector.blur])
                
                writer.writerow([self.line_print(), "Kernel Size",
                                    str(self.color_detector.k_size) + 'x' + str(self.color_detector.k_size)])
                writer.writerow(
                    [self.line_print(), "Remove Erodes", self.color_detector.erode])
                
                writer.writerow(
                    [self.line_print(), "Remove Erodes Iterations", self.color_detector.erode_i])
                writer.writerow(
                    [self.line_print(), "Dilate Mask", self.color_detector.dilate])

                writer.writerow(
                    [self.line_print(), "Dilate Iterations", self.color_detector.dilate_i])
                writer.writerow(
                    [self.line_print(), "Invert Mask", self.color_detector.invert])
                writer.writerow(
                    [self.line_print(), "Show Masked Image", self.color_detector.show])

    def load_click(self):
        filename = self.loadFileDialog()
        names = ["SN", "Name", "Value"]
        if filename:
            with open(filename, newline='') as csvfile:
                reader = csv.DictReader(csvfile)
                value = []
                for row in reader:
                    value.append(row[names[2]])
                self.lh.setValue(int(value[0]))
                self.hh.setValue(int(value[1]))
                self.ls.setValue(int(value[2]))
                self.hs.setValue(int(value[3]))
                self.lv.setValue(int(value[4]))
                self.hv.setValue(int(value[5]))
                self.blur.setChecked(value[6].lower() in ['true', '1'])
                self.color_detector.blur = (value[6].lower() in ['true', '1'])
                self.k_size.setValue(int(value[7].split('x')[0]))
                self.erode.setChecked(value[8].lower() in ['true', '1'])
                self.color_detector.erode = (value[8].lower() in ['true', '1'])
                self.erode_spinbox.setValue(int(value[9]))
                self.dilate.setChecked(value[10].lower() in ['true', '1'])
                self.color_detector.dilate = (value[10].lower() in ['true', '1'])
                self.dilate_spinbox.setValue(int(value[11]))
                self.invert.setChecked(value[12].lower() in ['true', '1'])
                self.color_detector.invert = (value[12].lower() in ['true', '1'])
                self.show_mask.setChecked(value[13].lower() in ['true', '1'])
                self.color_detector.show = (value[13].lower() in ['true', '1'])
        else:
            obj.setCheckable()
    def saveFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Configurations", "config.csv",
                                                   "CSV Files (*.csv)", options=options)
        if file_name:
            return file_name

    def loadFileDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Configurations", "config.csv",
                                                   "CSV Files (*.csv)", options=options)
        if file_name:
            print(file_name)
            return file_name

    def openFileNameDialog(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        file_name, _ = QFileDialog.getOpenFileName(self, "Open Image", "",
                                                   "All Files (*);;Image Files (*.jpg,*.jpeg,*.png)", options=options)
        if file_name:
            return file_name

    def line_print(self):
        self.line_num += 1
        return self.line_num


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = QtWidgets.QMainWindow()
    window.setStyleSheet(open("layouts/style.qss").read())
    # window.setWindowState(QtCore.Qt.WindowMaximized)
    window.setFixedSize(1104,614)
    qtRectangle = window.frameGeometry()
    centerPoint = QtWidgets.QDesktopWidget().availableGeometry().center()
    qtRectangle.moveCenter(centerPoint)
    window.move(qtRectangle.topLeft())
    window.setWindowIcon(QtGui.QIcon('images/icon.png'))
    widget = MainWidget()
    window.setWindowTitle("Color Mask Range Detector")
    window.setCentralWidget(widget)
    window.show()
    sys.exit(app.exec_())
