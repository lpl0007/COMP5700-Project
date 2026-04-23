#!/bin/bash
# Run directly with the active Python interpreter.

#put task 1 here (run this only once!)
python task1Extactor.py $1 $2

#task 2
#TODO: run this three times, one for each prompt type
python task2Comparator.py $1 $2


#run task 3 three times, one for each prompt type
python task3Comparator.py 
    

