import os
OutputList = [["A1","B1","C1","D1"],["A2","B2","C2","D2"],["A3","B3","C3","D3"]]

files = [
    "cis-r1.pdf",
    "cis-r2.pdf",
    "cis-r3.pdf",
    "cis-r4.pdf",
]
KDEFolder = "KDEs"

for PromptType, outputs in enumerate(OutputList):
    print(str(PromptType) + str(outputs))
    for item, output in enumerate(outputs):
        match PromptType:
            case 0: # zero shot
                KDEFilePath = "zero"
            case 1: # few shot
                KDEFilePath = "few"
            case 2: # chain of thought
                KDEFilePath = "chain"
        KDEFilePath = os.path.join(KDEFolder, files[item].replace(".pdf", "") + " "+ KDEFilePath + " KDEs.yaml")
        with open(KDEFilePath, 'w', encoding='utf-8') as f:
            f.write(str(output))
            f.flush()

    
    