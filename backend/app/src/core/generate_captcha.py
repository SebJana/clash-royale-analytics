import random
import string
from captcha.image import ImageCaptcha
from io import BytesIO
from .settings import settings

# Captcha alphabet is all letters and numbers
# Remove letters and digits that are prone to confusion
LETTERS = [l for l in string.ascii_letters if l not in ("O", "o", "l")]
DIGITS = [d for d in string.digits if d not in ("0", "1")]


def generate_captcha_string(length):
    """Generate a random CAPTCHA string with letters and numbers.

    Args:
        length (int): The desired length of the CAPTCHA string. Defaults to 6.

    Returns:
        str: A random string containing letters and digits.
    """
    captcha_str = ""

    for _ in range(length):
        r = random.random()
        # Use a random letter
        if r > settings.CAPTCHA_DIGIT_PERCENTAGE:
            captcha_str += random.choice(LETTERS)
        # Use a random digit
        else:
            captcha_str += random.choice(DIGITS)

    return captcha_str


def generate_captcha_image(text):
    """Generate a CAPTCHA image and return it as bytes.

    Args:
        text (str): The text to be rendered in the CAPTCHA image.

    Returns:
        bytes: The CAPTCHA image as PNG bytes.
    """
    # Create CAPTCHA generator
    image = ImageCaptcha(width=len(text) * 50, height=90)

    # Generate the image data
    data = image.generate(text)

    # Convert to bytes
    img_bytes = BytesIO()
    with data as img:
        img_bytes.write(img.read())
        img_bytes.seek(0)

    return img_bytes.getvalue()
