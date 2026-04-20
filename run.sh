#!/bin/bash
# source .venv/bin/activate.fish

#put task 1 here (run this only once!)
./venv/bin/python task1Extactor.py $1 $2

#task 2
#TODO: run this three times, one for each prompt type
./.venv/bin/python task2Comparator.py $1 $2


#run task 3 three times, one for each prompt type
./.venv/bin/python task3Comparator.py 
    

