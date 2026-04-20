import os
def readFile(filePath):
    outputLines = []
    with open(filePath, 'r') as file:
        for line in file:
            outputLines.append(line.strip())
    return outputLines