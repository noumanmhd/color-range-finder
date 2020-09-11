import cv2
from detector import MaskDetector
from detector import ColorDetertor

detect_mask = MaskDetector(filename='config.csv')
detect_color = ColorDetertor(filename='config.csv')

image = cv2.imread('../images/sample.jpg')

mask = detect_mask.getMask(image)
color = detect_color.detect(image)
print('Color Status: {}'.format(color))
cv2.imshow('Mask', mask)
cv2.waitKey(0)

