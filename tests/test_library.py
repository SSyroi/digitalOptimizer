import unittest
from ams_optimizer.core.library import load_default_library, Library, Cell

class TestLibrary(unittest.TestCase):
    def test_load_default_library(self):
        lib = load_default_library()
        self.assertEqual(lib.name, "default_ams")
        self.assertIn("NAND2", lib.cells)
        self.assertIn("NOR3", lib.cells)
        self.assertIn("MUX2", lib.cells)
        self.assertIn("DFFR", lib.cells)

    def test_cell_evaluation(self):
        lib = load_default_library()
        nand2 = lib.get_cell("NAND2")
        self.assertFalse(nand2.evaluate({"A": True, "B": True}))
        self.assertTrue(nand2.evaluate({"A": True, "B": False}))

        mux2 = lib.get_cell("MUX2")
        self.assertTrue(mux2.evaluate({"S": False, "D0": True, "D1": False}))
        self.assertFalse(mux2.evaluate({"S": True, "D0": True, "D1": False}))

if __name__ == "__main__":
    unittest.main()

