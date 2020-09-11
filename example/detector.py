import cv2
import csv


class Detector(object):
    def __init__(self, filename='config.csv'):
        self.readConfig(filename)
        self.printConfig()

    def readConfig(self, filename):
        names = ["SN", "Name", "Value"]
        with open(filename, newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            value = []
            for row in reader:
                value.append(row[names[2]])
            lh = int(value[0])
            hh = int(value[1])
            ls = int(value[2])
            hs = int(value[3])
            lv = int(value[4])
            hv = int(value[5])
            self.blur = (value[6].lower() in ['true', '1'])
            self.k_size = int(value[7].split('x')[0])
            self.erode = (value[8].lower() in ['true', '1'])
            self.erode_i = int(value[9])
            self.dilate = (value[10].lower() in ['true', '1'])
            self.dilate_i = int(value[11])
            self.invert = (value[12].lower() in ['true', '1'])

            self.lower_range = (lh, ls, lv)
            self.upper_range = (hh, hs, hv)

    def printConfig(self):
        print('Lower Range: {}'.format(self.lower_range))
        print('Higher Range: {}'.format(self.upper_range))
        print('Blur: {}'.format(self.blur))
        if self.blur:
            print('Kernel Size: {}'.format(self.k_size))
        print('Erode: {}'.format(self.erode))
        if self.erode:
            print('Erode Iterations: {}'.format(self.erode_i))
        print('Dilate: {}'.format(self.dilate))
        if self.dilate:
            print('Dilate Iterations: {}'.format(self.dilate_i))
        print('Invert Mask: {}'.format(self.invert))


class MaskDetector(Detector):
    def getMask(self, frame):
        '''Return Mask'''
        if self.blur:
            frame = cv2.GaussianBlur(frame, (self.k_size, self.k_size), 0)
        frame = cv2.cvtColor(frame.copy(), cv2.COLOR_BGR2HSV)

        mask = cv2.inRange(frame, self.lower_range, self.upper_range)
        if self.erode:
            mask = cv2.erode(mask, None, iterations=self.erode_i)
        if self.dilate:
            mask = cv2.dilate(mask, None, iterations=self.dilate_i)
        if self.invert:
            mask = 255 - mask
        return mask


class ColorDetertor(MaskDetector):
    @staticmethod
    def grab_contours(cnts):
        if len(cnts) == 2:
            cnts = cnts[0]
        elif len(cnts) == 3:
            cnts = cnts[1]
        return cnts

    def detect(self, frame):
        mask = self.getMask(frame)
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                cv2.CHAIN_APPROX_SIMPLE)
        cnts = self.grab_contours(cnts)
        return (len(cnts) > 0)
