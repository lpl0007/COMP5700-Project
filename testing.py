import unittest
import sys
import task2Comparator
import task3Exectutor
class comparator(unittest.TestCase):
    
    def testInput(self):
        correctData1 = {'element1': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name1', 'requirements': 'req4 req5 req6'}}
        correctData2 = {'element1': {'name': 'name4', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name3', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name5', 'requirements': 'req4 req7 req6'}}
        self.assertTrue(True)
        data1, data2 = task2Comparator.readFiles("KDEs/sample.yaml","KDEs/sample2.yaml")
        self.assertEqual(correctData1, data1)
        self.assertEqual(correctData2, data2)
    def testCompareElements(self):
        Data1 = {'element1': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name1', 'requirements': 'req4 req5 req6'}}
        Data2 = {'element1': {'name': 'name4', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name3', 'requirements': 'req1 req2 req3'}, 'element3': {'name': 'name5', 'requirements': 'req4 req5 req6'}}
        dif = ['name1','name2','name3','name4','name5']       
        # check to make sure same data results in the same thing
        self.assertEqual("NO DIFFERENCES IN REGARDS TO ELEMENT NAMES", task2Comparator.compElements(Data1,Data1))
        #output should look like "element1:name1, name4; element2:name2, name3"
        self.assertEqual(dif, task2Comparator.compElements(Data1,Data2)) 
    def testCompareRequirements(self):
            Data1 = {'element1': {'name': 'name2', 'requirements': 'req1 req2 req3'}, 'element2': {'name': 'name2', 'requirements': 'req1 req90 req3'}, 'element3': {'name': 'name1', 'requirements': 'req4 req5 req6'}}
            Data2 = {'element1': {'name': 'name4', 'requirements': 'req1 req4 req8'}, 'element2': {'name': 'name3', 'requirements': 'req9 req10 req11'}, 'element3': {'name': 'name5', 'requirements': 'req4 req5 req6'}}
            dif = ['req90', 'req10', 'req9', 'req2', 'req11', 'req3', 'req8']
            # check to make sure same data results in the same thing
            self.assertEqual("NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS", task2Comparator.compRequirements(Data1,Data1))
            #output should look like "element1:name1, name4; element2:name2, name3"
            self.assertCountEqual(dif, task2Comparator.compRequirements(Data1,Data2))
class exectutor(unittest.TestCase):
    #TODO: implement the test cases based off what the prof says
    def testInputReadFile(self):
        elements = ["name1","name2","name2","name3","name4","name5"]
        self.assertEqual(elements,task3Exectutor.readFile("TXTs/sample sample2 elem.txt"))

if __name__ == '__operations__':
    unittest.operations()