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
                    mismatches.append({
                        'element': key,
                        'type': 'both',
                        'name_data1': name1,
                        'name_data2': name2
                    })
            else:
                mismatches.append({
                        'element': key,
                        'type': 'data1',
                        'name_data1': name1,
                    })
    for key, value2 in data2.items():
           if key not in data1:
                if value2.get('name') is not None:
                    mismatches.append({
                        'element': key,
                        'type': 'data2',
                        'name_data2': value2.get('name'),
                    })
    if len(mismatches) == 0:
        return "NO DIFFERENCES IN REGARDS TO ELEMENT NAMES"
    return mismatches

def compRequirements(data1, data2):
    reqs1 = set()
    reqs2 = set()

    for key, value in data1.items():
        if isinstance(value, dict) and value.get('requirements'):
            for req in str(value['requirements']).split():
                reqs1.add(req.strip())

    for key, value in data2.items():
        if isinstance(value, dict) and value.get('requirements'):
            for req in str(value['requirements']).split():
                reqs2.add(req.strip())

    shared = reqs1 & reqs2
    different = (reqs1 | reqs2) - shared
    if len(different) == 0:
        return 'NO DIFFERENCES IN REGARDS TO ELEMENT REQUIREMENTS'

    return list(different)

def AllFunctions(filePath1:str, filePath2:str):
    data1, data2 = readFiles(filePath1,filePath2)
    diffElements = compElements(data1,data2)
    difRequirements = compRequirements(data1,data2)
    outputFilePath = os.path.join("TXTs",f'{Path(filePath1).stem} {Path(filePath2).stem}.txt' )
    with open(outputFilePath, 'w', encoding='utf-8') as outputFile:
        outputFile.write(str(diffElements))
        outputFile.write("\n")
        outputFile.write(str(difRequirements))

if __name__ == "__main__":
    filePath1 = os.path.join("KDEs",sys.argv[1])
    filePath2 = os.path.join("KDEs",sys.argv[2])
    data1, data2 = readFiles(filePath1,filePath2)
    diffElements = compElements(data1,data2)
    diffRequirements = compRequirements(data1,data2)
    outputFilePathElement = os.path.join("TXTs",f'{Path(filePath1).stem} {Path(filePath2).stem} elem.txt' )
    outputFilePathRequirements = os.path.join("TXTs",f'{Path(filePath1).stem} {Path(filePath2).stem} reqs.txt')
    with open(outputFilePathElement, 'w', encoding='utf-8') as outputFile:
        outputFile.write(str(diffElements))
    with open(outputFilePathRequirements, 'w', encoding='utf-8') as outputFile:
        outputFile.write(str(diffRequirements))