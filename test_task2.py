import unittest
import sys
import task2Comparator
class comparator(unittest.TestCase):
    
    def testInput(self):
        correctData1 = {'element1': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element3': None, 'name': 'name1', 'requirements': 'req4 req5 req6'}
        correctData2 = {'element1': {'name': 'name4', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name3', 'requirements': 'req1 req2 req3'}, 'element3': None, 'name': 'name5', 'requirements': 'req4 req5 req6'}
        self.assertTrue(True)
        data1, data2 = task2Comparator.readFiles("yamls/sample.YAML","yamls/sample2.YAML")
        self.assertEqual(correctData1, data1)
        self.assertEqual(correctData2, data2)


if __name__ == '__operations__':
    unittest.operations()