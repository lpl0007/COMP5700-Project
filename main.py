import os
import sys
import subprocess

if len(sys.argv) < 3:
    raise SystemExit(
        "Usage: python task3Exectutor.py <PDF1 path> <PDF2 path>"
    )
filename1 = os.path.splitext(os.path.basename(sys.argv[1]))[0]
filename2 = os.path.splitext(os.path.basename(sys.argv[2]))[0]
print("running task 2")
subprocess.run(["python", "task2Comparator.py",filename1,filename2])
print("task 2 done, running task 3")

subprocess.run(["python", "task3Exectutor.py",f"{filename1} {filename2} elem", f"{filename1} {filename2} reqs", "kubeScape.txt"])