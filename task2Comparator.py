import os
import yaml
from pathlib import Path
import sys

"""
args
sys.argv[1] should be filepath1
sys.argv[2] should be filepath2
"""

def readFiles(filePath1:str, filePath2:str):
    with open(filePath1, 'r') as file1:
        data1 = yaml.safe_load(file1)
    with open(filePath2, 'r') as file2:
        data2 = yaml.safe_load(file2)
    return data1, data2

def compElements(data1, data2):
    mismatches = []
    
    for key, value1 in data1.items():
        if key in data2:
            value2 = data2[key]
            # Check if the 'name' field exists in both and differs
            if isinstance(value1, dict) and isinstance(value2, dict):
                name1 = value1.get('name')
                name2 = value2.get('name')
                if name1 is not None and name2 is not None and name1 != name2:
                    if (name1 not in mismatches):
                        mismatches.append(name1)
                    if (name2 not in mismatches):
                        mismatches.append(name2)
            else:
                mismatches.append(name1)
    for key, value2 in data2.items():
           if key not in data1:
                if value2.get('name') is not None:
                    mismatches.append(value2.get('name'))
    if len(mismatches) == 0:
        return "NO DIFFERENCES IN REGARDS TO ELEMENT NAMES"
    mismatches.sort()
    return mismatches

def compRequirements(data1, data2):
    reqs1 = []
    reqs2 = []

    for key, value in data1.items():
        if isinstance(value, dict) and value.get('requirements'):
            for req in str(value['requirements']).split():
                if req.strip() not in reqs1:
                    reqs1.append(req.strip())

    for key, value in data2.items():
        if isinstance(value, dict) and value.get('requirements'):
            for req in str(value['requirements']).split():
                if req.strip() not in reqs2:
                    reqs2.append(req.strip())

    shared = [r for r in reqs1 if r in reqs2]
    different = [r for r in reqs1 if r not in reqs2] + [r for r in reqs2 if r not in reqs1]

    if len(different) == 0:
        return 'NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS'
    different.sort()
    return different

def saveList(filePath, inputList):
    if isinstance(inputList, str):
        with open(filePath, "w") as file:
            file.write(inputList)
            return
    with open(filePath, "w") as file:
        file.write("\n".join(inputList))
    
def AllFunctions(filePath1:str, filePath2:str):
    data1, data2 = readFiles(filePath1,filePath2)
    diffElements = compElements(data1,data2)
    difRequirements = compRequirements(data1,data2)
    outputFilePath = os.path.join("TXTs",f'{Path(filePath1).stem} {Path(filePath2).stem}.txt' )



if __name__ == "__main__":
    #get data
    filePath1 = os.path.join("KDEs",sys.argv[1]+"-kdes.yaml")
    filePath2 = os.path.join("KDEs",sys.argv[2]+"-kdes.yaml")

    data1, data2 = readFiles(filePath1,filePath2)
    #compare data
    diffElements = compElements(data1,data2)
    diffRequirements = compRequirements(data1,data2)
    #save output
    outputFilePathElement = os.path.join("TXTs",f'{Path(filePath1).stem} {Path(filePath2).stem} elem.txt' )
    outputFilePathRequirements = os.path.join("TXTs",f'{Path(filePath1).stem} {Path(filePath2).stem} reqs.txt')

    saveList(outputFilePathElement,diffElements)
    saveList(outputFilePathRequirements,diffRequirements)