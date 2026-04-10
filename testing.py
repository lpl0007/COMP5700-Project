import unittest
import sys
import task2Comparator
class comparator(unittest.TestCase):
    
    def testInput(self):
        correctData1 = {'element1': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name1', 'requirements': 'req4 req5 req6'}}
        correctData2 = {'element1': {'name': 'name4', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name3', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name5', 'requirements': 'req4 req5 req6'}}
        self.assertTrue(True)
        data1, data2 = task2Comparator.readFiles("yamls/sample.YAML","yamls/sample2.YAML")
        self.assertEqual(correctData1, data1)
        self.assertEqual(correctData2, data2)
    def testCompareElements(self):
        Data1 = {'element1': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name1', 'requirements': 'req4 req5 req6'}}
        Data2 = {'element1': {'name': 'name4', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name3', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name5', 'requirements': 'req4 req5 req6'}}
        dif = [{'element': 'element1', 'type': 'both', 'name_data1': 'name2', 'name_data2': 'name4'}, 
        {'element': 'element2', 'type': 'both', 'name_data1': 'name2', 'name_data2': 'name3'}, 
        {'element': 'element3', 'type': 'both', 'name_data1': 'name1', 'name_data2': 'name5'}]        
        # check to make sure same data results in the same thing
        self.assertEqual("NO DIFFERENCES IN REGARDS TO ELEMENT NAMES", task2Comparator.compElements(Data1,Data1))
        #output should look like "element1:name1, name4; element2:name2, name3"
        self.assertEqual(dif, task2Comparator.compElements(Data1,Data2)) 
        


if __name__ == '__operations__':
    unittest.operations()