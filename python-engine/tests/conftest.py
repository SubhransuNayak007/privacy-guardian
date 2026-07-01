import pytest
import cv2
import numpy as np
import base64

def _encode_to_b64(img):
    _, buffer = cv2.imencode('.jpg', img)
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode('utf-8')

@pytest.fixture
def api_url():
    return "http://localhost:8000"

@pytest.fixture
def synth_generators():
    class Generators:
        @staticmethod
        def clean_image():
            img = np.ones((500, 500, 3), dtype=np.uint8) * 255
            return _encode_to_b64(img)
            
        @staticmethod
        def credit_card():
            img = np.ones((600, 1000, 3), dtype=np.uint8) * 200
            # Draw card outline
            cv2.rectangle(img, (100, 100), (900, 500), (0, 0, 0), 5)
            # Draw digits
            cv2.putText(img, "4532 1234 5678 9012", (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (0, 0, 0), 3)
            cv2.putText(img, "EXP 12/25  CVV 123", (150, 400), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 0), 2)
            return _encode_to_b64(img)
            
        @staticmethod
        def blurry_image():
            img = np.ones((500, 500, 3), dtype=np.uint8) * 128
            cv2.putText(img, "Some text", (50, 250), cv2.FONT_HERSHEY_SIMPLEX, 2.0, (0, 0, 0), 3)
            # Apply motion blur
            kernel = np.zeros((15, 15))
            kernel[7, :] = np.ones(15) / 15
            blurred = cv2.filter2D(img, -1, kernel)
            return _encode_to_b64(blurred)
            
        @staticmethod
        def dark_credit_card():
            img = np.ones((600, 1000, 3), dtype=np.uint8) * 40 # Very dark
            cv2.rectangle(img, (100, 100), (900, 500), (20, 20, 20), 5)
            cv2.putText(img, "4532 1234 5678 9012", (150, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (10, 10, 10), 3)
            return _encode_to_b64(img)
            
        @staticmethod
        def tiled_image():
            img = np.ones((2048, 2048, 3), dtype=np.uint8) * 255
            # Q1
            cv2.rectangle(img, (100, 100), (500, 300), (0, 0, 0), 5)
            # Q2
            cv2.rectangle(img, (1500, 100), (1900, 300), (0, 0, 0), 5)
            # Q3
            cv2.rectangle(img, (100, 1500), (500, 1900), (0, 0, 0), 5)
            # Q4
            cv2.rectangle(img, (1500, 1500), (1900, 1900), (0, 0, 0), 5)
            return _encode_to_b64(img)
            
        @staticmethod
        def cross_tile_image():
            img = np.ones((2048, 2048, 3), dtype=np.uint8) * 255
            # Draw a ruler across the vertical split (x=1024)
            cv2.rectangle(img, (500, 1000), (1500, 1100), (0, 0, 0), 5)
            return _encode_to_b64(img)
            
        @staticmethod
        def gun_silhouette():
            img = np.ones((500, 500, 3), dtype=np.uint8) * 255
            pts = np.array([[100, 300], [150, 200], [400, 200], [400, 250], [200, 250], [150, 400]], np.int32)
            cv2.fillPoly(img, [pts], (0, 0, 0))
            return _encode_to_b64(img)
            
        @staticmethod
        def face_image():
            img = np.ones((500, 500, 3), dtype=np.uint8) * 255
            # Draw a simple face shape
            cv2.circle(img, (250, 250), 100, (0, 0, 0), 3)
            cv2.circle(img, (210, 220), 10, (0, 0, 0), -1)
            cv2.circle(img, (290, 220), 10, (0, 0, 0), -1)
            cv2.ellipse(img, (250, 280), (40, 20), 0, 0, 180, (0, 0, 0), 3)
            return _encode_to_b64(img)

        @staticmethod
        def qrcode():
            import qrcode
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data("https://example.com")
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            img_np = np.array(img.convert('RGB'))
            return _encode_to_b64(img_np)
            
        @staticmethod
        def nsfw_breast():
            # Simplistic flesh-toned blob mock for nudenet
            img = np.ones((500, 500, 3), dtype=np.uint8) * 255
            cv2.circle(img, (250, 250), 100, (180, 210, 255), -1) # Flesh color BGR
            cv2.circle(img, (250, 250), 20, (120, 140, 220), -1) # Areola
            return _encode_to_b64(img)
            
        @staticmethod
        def tattoo():
            img = np.ones((500, 500, 3), dtype=np.uint8) * 255
            cv2.circle(img, (250, 250), 150, (180, 210, 255), -1) # Skin
            # Star tattoo
            pts = np.array([[250, 150], [270, 220], [340, 220], [280, 260], [300, 330], [250, 290], [200, 330], [220, 260], [160, 220], [230, 220]], np.int32)
            cv2.fillPoly(img, [pts], (0, 0, 0))
            return _encode_to_b64(img)

    return Generators()
