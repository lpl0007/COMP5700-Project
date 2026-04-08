import os
import yaml


def readFiles(file1:str, file2:str):
    with open(file1, 'r') as file:
        data1 = yaml.safe_load(file)
    with open(file2, 'r') as file:
        data2 = yaml.safe_load(file)
    return data1, data2

def diffElements(file1:str, file2:str):
    raise NotImplementedError
    return -1

def diffRequirements(file1:str, file2:str):
    raise NotImplementedError
    return -1

combos = [
    ["cis-r1", "cis-r1"],
    ["cis-r1", "cis-r2"],
    ["cis-r1", "cis-r3"],
    ["cis-r1", "cis-r4"],
    ["cis-r2", "cis-r2"],
    ["cis-r2", "cis-r3"],
    ["cis-r2", "cis-r4"],
    ["cis-r3", "cis-r3"],
    ["cis-r3", "cis-r4"]
]
KDEPath = "KDEs"
KDEFilePath = ""
for index, item in enumerate(combos,1):
    print(str(index) + str(item))
    for i in range(3):
        match i:
            case 0: # zero shot
                KDEFilePath = "zero"
            case 1: # few shot
                KDEFilePath = "few"
            case 2: # chain of thought
                KDEFilePath = "chain"
        
        # combine the parts to make the filepath
        path1 = os.path.join(KDEPath, item[0] + " "+ KDEFilePath + " KDEs.yaml")
        path2 = os.path.join(KDEPath, item[1] + " "+ KDEFilePath + " KDEs.yaml")
        print(path1)
        print(path2)
        data1, data2 =  readFiles(path1, path2)
        print(data1)
        print(data2)
    