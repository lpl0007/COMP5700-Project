import os
import yaml


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

if __name__ == "__main__":
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
        