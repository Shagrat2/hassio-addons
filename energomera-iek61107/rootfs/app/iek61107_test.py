import unittest
import iek61107

class TestMakePack(unittest.TestCase):
    # P1 (777777)
    def test_P1(self):
        data = iek61107.makePack('P1', '(777777)')
        self.assertEqual(data, b'\x01\x50\x31\x02\x28\x37\x37\x37\x37\x37\x37\x29\x03\x21')

    # R1 SNUMB()
    def test_R1(self):
        data = iek61107.makePack('R1', 'SNUMB()')
        self.assertEqual(data, b'\x01\x52\x31\x02\x53\x4E\x55\x4D\x42\x28\x29\x03\x5E')

    # B0
    def test_B0(self):
        data = iek61107.makePack('B0', '')
        self.assertEqual(data, b'\x01\x42\x30\x03\x75')

class TestDecodePack(unittest.TestCase):

    # /?!..
    def test_init(self):
        ch, data = iek61107.decodePack(b'\x2F\x45\x4B\x54\x35\x43\x45\x31\x30\x32\x4D\x76\x30\x31\x0D\x0A')
        self.assertEqual(ch, '')
        self.assertEqual(data, '')

    # .051..
    def test_051(self):
        ch, data = iek61107.decodePack(b'\x01\x50\x30\x02\x28\x31\x35\x33\x36\x34\x34\x32\x35\x34\x29\x03\x28')
        self.assertEqual(ch, 'P0')
        self.assertEqual(data, '(153644254)')

    # \x06
    def test_06(self):
        ch, data = iek61107.decodePack(b'\x06')

        self.assertEqual(ch, '')
        self.assertEqual(data, '')

    # SNUMB()
    def test_SNUMB(self):
        ch, data = iek61107.decodePack(b'\x02\x53\x4E\x55\x4D\x42\x28\x30\x31\x30\x37\x34\x38\x31\x35\x33\x36\x34\x34\x32\x35\x34\x29\x0D\x0A\x03\x76')

        self.assertEqual(ch, '')
        self.assertEqual(data, 'SNUMB(010748153644254)')

# Executing the tests in the above test case class
if __name__ == "__main__":
  unittest.main()