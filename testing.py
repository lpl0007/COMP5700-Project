import unittest
import sys
import tempfile
import os
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
    def testInputReadFile(self):
        elements = ["name1","name2","name2","name3","name4","name5"]
        self.assertEqual(elements,task3Exectutor.readFile("TXTs/sample sample2 elem.txt"))

    def testDetermineDifferenceControlsNoDifferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            elements_path = os.path.join(temp_dir, "elements.txt")
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            output_path = os.path.join(temp_dir, "controls.txt")

            with open(elements_path, "w", encoding="utf-8") as f:
                f.write("NO DIFFERENCES IN REGARDS TO ELEMENT NAMES\n")
            with open(requirements_path, "w", encoding="utf-8") as f:
                f.write("NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS\n")

            result = task3Exectutor.determine_difference_controls(
                elements_path, requirements_path, output_path
            )
            self.assertEqual(["NO DIFFERENCES FOUND"], result)
            self.assertEqual(["NO DIFFERENCES FOUND"], task3Exectutor.readFile(output_path))

    def testDetermineDifferenceControlsWithDifferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            elements_path = os.path.join(temp_dir, "elements.txt")
            requirements_path = os.path.join(temp_dir, "requirements.txt")
            output_path = os.path.join(temp_dir, "controls.txt")

            with open(elements_path, "w", encoding="utf-8") as f:
                f.write("privileged container\n")
            with open(requirements_path, "w", encoding="utf-8") as f:
                f.write("service account token\n")

            result = task3Exectutor.determine_difference_controls(
                elements_path, requirements_path, output_path
            )
            self.assertIn("C-0057: Privileged container", result)
            self.assertIn(
                "C-0190: Ensure that Service Account Tokens are only mounted where necessary",
                result,
            )

    def testCompareTwoTextFilesAndMapControlsNoDifferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            txt_path_1 = os.path.join(temp_dir, "left.txt")
            txt_path_2 = os.path.join(temp_dir, "right.txt")
            output_path = os.path.join(temp_dir, "controls.txt")

            with open(txt_path_1, "w", encoding="utf-8") as f:
                f.write("resource cpu request\n")
                f.write("service account token\n")
            with open(txt_path_2, "w", encoding="utf-8") as f:
                f.write("resource cpu request\n")
                f.write("service account token\n")

            result = task3Exectutor.compare_two_text_files_and_map_controls(
                txt_path_1, txt_path_2, output_path
            )

            self.assertEqual(["NO DIFFERENCES FOUND"], result)
            self.assertEqual(["NO DIFFERENCES FOUND"], task3Exectutor.readFile(output_path))

    def testCompareTwoTextFilesAndMapControlsWithDifferences(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            txt_path_1 = os.path.join(temp_dir, "left.txt")
            txt_path_2 = os.path.join(temp_dir, "right.txt")
            output_path = os.path.join(temp_dir, "controls.txt")

            with open(txt_path_1, "w", encoding="utf-8") as f:
                f.write("privileged container\n")
            with open(txt_path_2, "w", encoding="utf-8") as f:
                f.write("service account token\n")

            result = task3Exectutor.compare_two_text_files_and_map_controls(
                txt_path_1, txt_path_2, output_path
            )

            self.assertIn("C-0057: Privileged container", result)
            self.assertIn(
                "C-0190: Ensure that Service Account Tokens are only mounted where necessary",
                result,
            )

if __name__ == '__operations__':
    unittest.operations()
